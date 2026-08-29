#!/usr/bin/env python3
"""Build matched uniform/transition and current/temporal SFT corpora."""

from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from pathlib import Path

from actions import canonical_action_tokens
from capture_wire_observations import extract
from dataset import ActionTimeline, SFTSample, read_actions, read_maps, read_samples, write_jsonl
from observation_text import bot_semantic_observation, self_center, temporal_delta


VARIANTS = ("uniform-history4", "transition-current", "transition-history4")


def binary_ticks(path: Path) -> set[int]:
    ticks = set()
    with path.open() as source:
        for line in source:
            event = json.loads(line)
            if (
                event.get("direction") == "in"
                and event.get("type") == "binary"
                and event.get("tick") is not None
            ):
                ticks.add(int(event["tick"]))
    return ticks


def is_action_change(timeline: ActionTimeline, tick: int) -> bool:
    return canonical_action_tokens(timeline.mask_at(tick - 1)) != canonical_action_tokens(
        timeline.mask_at(tick)
    )


def round_robin(candidates: dict[str, list[int]], count: int, seed: int) -> list[tuple[str, int]]:
    rng = random.Random(seed)
    pools = []
    for trajectory in sorted(candidates):
        values = list(candidates[trajectory])
        rng.shuffle(values)
        pools.append((trajectory, values))
    selected = []
    index = 0
    while len(selected) < count and any(index < len(values) for _, values in pools):
        for trajectory, values in pools:
            if index < len(values):
                selected.append((trajectory, values[index]))
                if len(selected) == count:
                    break
        index += 1
    if len(selected) != count:
        raise ValueError(f"needed {count} candidates, found {len(selected)}")
    return selected


def build(source: Path, output: Path, *, seed: int) -> dict:
    prepared = source / "prepared"
    trajectories_root = source / "trajectories"
    provenance = json.loads((prepared / "provenance.json").read_text())
    records = {
        f"gv{item['game_version']}-{item['episode_id'][:8]}-seat{item['seat']}": item
        for item in provenance["trajectories"]
    }
    original = {
        split: read_samples(prepared / f"{split}.samples.jsonl")
        for split in ("train", "validation", "test")
    }
    uniform_targets = {
        (sample.replay_id, sample.pov, sample.observation_tick)
        for samples in original.values()
        for sample in samples
    }

    eligible: dict[tuple[str, str, str], dict[bool, dict[str, list[int]]]] = defaultdict(
        lambda: {False: defaultdict(list), True: defaultdict(list)}
    )
    timelines = {}
    for trajectory, record in records.items():
        directory = trajectories_root / trajectory
        timeline = ActionTimeline(read_actions(directory / "actions.jsonl"))
        timelines[trajectory] = timeline
        ticks = binary_ticks(directory / "wire.jsonl")
        valid_self_ticks = set()
        for snapshot in extract(
            directory / "wire.jsonl",
            game_version=record["game_version"],
            stride=1,
        ):
            try:
                self_center(snapshot)
            except ValueError:
                continue
            if snapshot.tick is not None:
                valid_self_ticks.add(snapshot.tick)
        for tick in sorted(ticks):
            if (
                tick in valid_self_ticks
                and all(tick - offset in ticks for offset in range(6))
            ):
                eligible[(record["split"], record["game_version"], trajectory)][
                    is_action_change(timeline, tick)
                ][trajectory].append(tick)

    target_counts = Counter(
        (split, sample.game_version) for split, samples in original.items() for sample in samples
    )
    transition_targets: dict[str, set[int]] = defaultdict(set)
    selection_counts = {}
    for (split, version), total in sorted(target_counts.items()):
        changed_by_trajectory: dict[str, list[int]] = {}
        held_by_trajectory: dict[str, list[int]] = {}
        for (candidate_split, candidate_version, trajectory), classes in eligible.items():
            if (candidate_split, candidate_version) == (split, version):
                changed_by_trajectory.update(classes[True])
                held_by_trajectory.update(classes[False])
        changed_count = (total + 1) // 2
        held_count = total - changed_count
        changed = round_robin(changed_by_trajectory, changed_count, seed)
        held = round_robin(held_by_trajectory, held_count, seed + 1)
        for trajectory, tick in (*changed, *held):
            transition_targets[trajectory].add(tick)
        selection_counts[f"{split}:gv{version}"] = {
            "total": total,
            "changed": changed_count,
            "held": held_count,
        }

    built_uniform = defaultdict(list)
    built_transition = defaultdict(list)
    maps = {}
    for trajectory, record in records.items():
        directory = trajectories_root / trajectory
        timeline = timelines[trajectory]
        map_items = read_maps(directory / "map.jsonl")
        if len(map_items) != 1:
            raise ValueError(f"{trajectory} does not contain exactly one map")
        map_hash, episode_map = next(iter(map_items.items()))
        maps[map_hash] = episode_map

        uniform_ticks = {
            tick
            for replay, pov, tick in uniform_targets
            if replay == record["episode_id"] and pov == record["seat"]
        }
        target_ticks = uniform_ticks | transition_targets[trajectory]
        selected_ticks = {
            tick - offset for tick in target_ticks for offset in range(6)
        }
        snapshots = extract(
            directory / "wire.jsonl",
            game_version=record["game_version"],
            stride=1,
            selected_ticks=selected_ticks,
        )
        by_tick = {snapshot.tick: snapshot for snapshot in snapshots if snapshot.tick is not None}
        for tick in sorted(target_ticks):
            required = [by_tick.get(tick - offset) for offset in range(6)]
            if any(snapshot is None for snapshot in required):
                raise ValueError(f"{trajectory} tick {tick} lacks a complete five-tick history")
            current = required[0]
            assert current is not None
            try:
                self_center(current)
            except ValueError as error:
                raise ValueError(f"{trajectory} tick {tick} has no self entity") from error
            history = []
            for offset in range(4, 0, -1):
                before = by_tick[tick - offset - 1]
                after = by_tick[tick - offset]
                history.append(
                    temporal_delta(
                        before,
                        after,
                        action_mask=timeline.mask_at(tick - offset),
                        target_tick=tick,
                    )
                )
            sample = SFTSample(
                replay_id=record["episode_id"],
                game_version=record["game_version"],
                pov=record["seat"],
                observation_tick=tick,
                action_tick=tick,
                map_hash=map_hash,
                observation=bot_semantic_observation(current).to_dict(),
                previous_mask=timeline.mask_at(tick - 1),
                target_mask=timeline.mask_at(tick),
                history=tuple(history),
            )
            split = record["split"]
            key = (record["episode_id"], record["seat"], tick)
            if key in uniform_targets:
                built_uniform[split].append(sample)
            if tick in transition_targets[trajectory]:
                built_transition[split].append(sample)

    for variant in VARIANTS:
        destination = output / variant
        destination.mkdir(parents=True, exist_ok=True)
        for split in ("train", "validation", "test"):
            temporal = built_uniform[split] if variant == "uniform-history4" else built_transition[split]
            samples = temporal if variant.endswith("history4") else [replace(item, history=()) for item in temporal]
            expected = len(original[split])
            if len(samples) != expected:
                raise ValueError(f"{variant} {split} has {len(samples)} samples, expected {expected}")
            random.Random(seed).shuffle(samples)
            write_jsonl(destination / f"{split}.samples.jsonl", samples)
            used_maps = {sample.map_hash for sample in samples}
            write_jsonl(
                destination / f"{split}.maps.jsonl",
                (maps[map_hash] for map_hash in sorted(used_maps)),
            )
        shutil.copy2(prepared / "provenance.json", destination / "source_provenance.json")

    summary = {
        "schema_version": 1,
        "source": str(source),
        "seed": seed,
        "history_ticks": 4,
        "history_max_tokens": 832,
        "transition_sampling": "50% canonical action changes, 50% held states",
        "selection_counts": selection_counts,
        "variants": VARIANTS,
    }
    (output / "experiment.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    build(args.source, args.output, seed=args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
