#!/usr/bin/env python3
"""Measure mixed-era observation lengths with the pinned Qwen tokenizer."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

from observation_text import (
    ObservationSnapshot,
    bot_semantic_observation,
    serialize_observation,
    snapshots_from_jsonl,
)


MODEL_ID = "Qwen/Qwen3-0.6B-Base"
MODEL_REVISION = "da87bfb608c14b7cf20ba1ce41287e8de496c0cd"
REQUIRED_ERAS = ("gv01-16", "gv17-24", "gv25-30", "gv31-35", "gv36+")


def era_for(game_version: str) -> str:
    try:
        version = int(game_version)
    except ValueError as error:
        raise ValueError(f"non-numeric CTF GameVersion {game_version!r}") from error
    if version <= 16:
        return "gv01-16"
    if version <= 24:
        return "gv17-24"
    if version <= 30:
        return "gv25-30"
    if version <= 35:
        return "gv31-35"
    return "gv36+"


def load_snapshots(paths: Iterable[Path]) -> list[ObservationSnapshot]:
    snapshots = []
    for path in paths:
        with path.open() as handle:
            snapshots.extend(snapshots_from_jsonl(handle))
    return snapshots


def percentile(values: list[int], probability: float) -> int:
    if not values:
        raise ValueError("cannot summarize an empty sample")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def summarize(values: list[int]) -> dict[str, int | float]:
    return {
        "count": len(values),
        "min": min(values),
        "median": percentile(values, 0.5),
        "p90": percentile(values, 0.9),
        "p99": percentile(values, 0.99),
        "max": max(values),
        "mean": round(sum(values) / len(values), 2),
    }


def evenly_sample_by_version(
    snapshots: list[ObservationSnapshot], samples_per_version: int
) -> list[ObservationSnapshot]:
    grouped: dict[str, list[ObservationSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.game_version].append(snapshot)

    sampled = []
    ordered_groups = sorted(grouped.items(), key=lambda item: int(item[0]))
    for version, version_snapshots in ordered_groups:
        if len(version_snapshots) < samples_per_version:
            raise ValueError(
                f"GameVersion {version} has {len(version_snapshots)} observations; "
                f"need {samples_per_version}"
            )
        sampled.extend(
            version_snapshots[index * len(version_snapshots) // samples_per_version]
            for index in range(samples_per_version)
        )
    return sampled


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshots", type=Path, nargs="+")
    parser.add_argument("--samples-per-version", type=int, default=1_000)
    parser.add_argument(
        "--entity-view",
        choices=("bot-semantic", "all-labels"),
        default="bot-semantic",
        help="Entity view to measure (default: bot-semantic)",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.samples_per_version < 100:
        parser.error(
            "--samples-per-version must be at least 100 for a meaningful p99"
        )

    available_snapshots = load_snapshots(args.snapshots)
    if not available_snapshots:
        parser.error("the corpus contains no observations")
    present_eras = {
        era_for(snapshot.game_version) for snapshot in available_snapshots
    }
    missing_eras = set(REQUIRED_ERAS) - present_eras
    if missing_eras:
        parser.error(
            "mixed-era corpus is incomplete; missing "
            + ", ".join(sorted(missing_eras))
        )
    try:
        snapshots = evenly_sample_by_version(
            available_snapshots, args.samples_per_version
        )
    except ValueError as error:
        parser.error(str(error))

    tokenizer_path = hf_hub_download(
        repo_id=MODEL_ID,
        filename="tokenizer.json",
        revision=MODEL_REVISION,
    )
    tokenizer = Tokenizer.from_file(tokenizer_path)
    by_era: dict[str, list[int]] = defaultdict(list)
    by_version: dict[str, list[int]] = defaultdict(list)
    paired_view_by_era: dict[str, list[int]] = defaultdict(list)
    excluded_counts_by_era: dict[str, list[int]] = defaultdict(list)
    all_lengths = []
    paired_view_lengths = []
    largest_observation: dict[str, object] | None = None
    for snapshot in snapshots:
        bot_snapshot = bot_semantic_observation(snapshot)
        bot_length = len(
            tokenizer.encode(
                serialize_observation(bot_snapshot), add_special_tokens=False
            ).ids
        )
        all_labels_length = len(
            tokenizer.encode(
                serialize_observation(snapshot, include_human_visuals=True),
                add_special_tokens=False,
            ).ids
        )
        if args.entity_view == "bot-semantic":
            length = bot_length
            paired_view_length = all_labels_length
        else:
            length = all_labels_length
            paired_view_length = bot_length
        excluded_count = len(snapshot.entities) - len(bot_snapshot.entities)
        all_lengths.append(length)
        paired_view_lengths.append(paired_view_length)
        era = era_for(snapshot.game_version)
        by_era[era].append(length)
        paired_view_by_era[era].append(paired_view_length)
        excluded_counts_by_era[era].append(excluded_count)
        by_version[snapshot.game_version].append(length)
        if largest_observation is None or length > largest_observation["tokens"]:
            largest_observation = {
                "game_version": snapshot.game_version,
                "frame": snapshot.frame,
                "source": snapshot.source,
                "tokens": length,
                "paired_view_tokens": paired_view_length,
                "entities": len(snapshot.entities),
                "bot_semantic_entities": len(bot_snapshot.entities),
                "excluded_human_visual_entities": excluded_count,
            }

    era_stats = {era: summarize(by_era[era]) for era in REQUIRED_ERAS}
    global_stats = summarize(all_lengths)
    passes = global_stats["max"] <= 16_384 and all(
        stats["p99"] <= 8_192 for stats in era_stats.values()
    )
    report = {
        "model": MODEL_ID,
        "revision": MODEL_REVISION,
        "special_tokens_added": False,
        "entity_view": args.entity_view,
        "excluded_human_visual_label_families": [
            "fog",
            "splatter *",
            "hit splat *",
            "damage pop *",
        ],
        "available_observations": len(available_snapshots),
        "sampled_observations": len(snapshots),
        "samples_per_game_version": args.samples_per_version,
        "decision": "confirmed" if passes else "refuted",
        "decision_rule": "every era p99 <= 8192 and global max <= 16384",
        "global": global_stats,
        "by_era": era_stats,
        "by_game_version": {
            version: summarize(lengths)
            for version, lengths in sorted(
                by_version.items(), key=lambda item: int(item[0])
            )
        },
        "diagnostics_not_used_for_decision": {
            "largest_observation": largest_observation,
            "excluded_human_visual_entity_count_by_era": {
                era: summarize(excluded_counts_by_era[era])
                for era in REQUIRED_ERAS
            },
            "paired_entity_view": (
                "all-labels"
                if args.entity_view == "bot-semantic"
                else "bot-semantic"
            ),
            "paired_entity_view_by_era": {
                era: summarize(paired_view_by_era[era]) for era in REQUIRED_ERAS
            },
            "paired_entity_view_global": summarize(paired_view_lengths),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if passes else 1


if __name__ == "__main__":
    raise SystemExit(main())
