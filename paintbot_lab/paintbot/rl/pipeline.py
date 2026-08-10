#!/usr/bin/env python3
"""Reproducible historical-replay preparation and SFT training pipeline."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
import time
from collections import defaultdict
from dataclasses import asdict, replace
from pathlib import Path

from dataset import (
    ActionTimeline,
    build_samples,
    read_actions,
    read_maps,
    read_samples,
    write_jsonl,
)
from observation_text import temporal_delta
from pipeline_manifest import EpisodeSpec, PipelineManifest, load_manifest


RL_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = RL_ROOT.parents[2]
ARTIFACT_DOWNLOADER = (
    REPOSITORY_ROOT
    / ".claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py"
)


def run_command(command: list[str], *, cwd: Path | None = None) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def download(manifest: PipelineManifest, workspace: Path, *, elevated: bool) -> Path:
    """Download only replay and result metadata through the shared lab tool."""
    if not ARTIFACT_DOWNLOADER.exists():
        raise FileNotFoundError(f"artifact downloader not found: {ARTIFACT_DOWNLOADER}")
    output = workspace / "raw"
    episode_ids = [episode.episode_id for episode in manifest.episodes]
    for start in range(0, len(episode_ids), 100):
        command = [
            sys.executable,
            str(ARTIFACT_DOWNLOADER),
            "--out",
            str(output),
            "--no-logs",
            "--no-artifacts",
            "--no-results",
        ]
        if elevated:
            command.append("--elevated")
        for episode_id in episode_ids[start : start + 100]:
            command.extend(("--episode", episode_id))
        run_command(command, cwd=REPOSITORY_ROOT)
    return output


def find_episode_directory(artifacts_root: Path, episode_id: str) -> Path:
    matches = []
    for metadata_path in artifacts_root.rglob("episode.json"):
        try:
            if str(json.loads(metadata_path.read_text()).get("id")) == episode_id:
                matches.append(metadata_path.parent)
        except (json.JSONDecodeError, OSError):
            continue
    if len(matches) != 1:
        raise ValueError(
            f"expected one artifact directory for {episode_id}, found {len(matches)}"
        )
    replay = matches[0] / "replay.json"
    if not replay.exists():
        raise FileNotFoundError(f"downloaded episode has no replay: {replay}")
    return matches[0]


def index_episode_directories(artifacts_root: Path) -> dict[str, Path]:
    """Index a large artifact tree once instead of rescanning it per replay."""
    indexed: dict[str, Path] = {}
    duplicates = set()
    for metadata_path in artifacts_root.rglob("episode.json"):
        try:
            episode_id = str(json.loads(metadata_path.read_text())["id"])
        except (KeyError, json.JSONDecodeError, OSError):
            continue
        if episode_id in indexed:
            duplicates.add(episode_id)
        indexed[episode_id] = metadata_path.parent
    if duplicates:
        raise ValueError(f"duplicate artifact directories for episodes: {sorted(duplicates)}")
    return indexed


def resolve_povs(spec: EpisodeSpec, metadata_path: Path) -> list[tuple[int, float, str]]:
    metadata = json.loads(metadata_path.read_text())
    agents: dict[int, tuple[float, str]] = {}
    policy_agents: dict[str, list[int]] = {}
    for policy_result in metadata.get("policy_results") or ():
        policy = policy_result.get("policy") or {}
        policy_label = f"{policy.get('name', 'unknown')}:{policy.get('version', 'unknown')}"
        policy_version_id = str(policy.get("id", ""))
        for agent in policy_result.get("agents") or ():
            seat = int(agent["agent_id"])
            agents[seat] = (float(agent.get("reward", 0)), policy_label)
            policy_agents.setdefault(policy_version_id, []).append(seat)
    if not agents:
        raise ValueError(f"{metadata_path} has no policy_results agent metadata")
    if spec.povs == "best_reward":
        seats = [max(agents, key=lambda seat: (agents[seat][0], -seat))]
    elif spec.povs == "expert_policies":
        seats = []
        for policy_version_id in spec.expert_policy_version_ids:
            candidates = sorted(policy_agents.get(policy_version_id, ()))
            if not candidates:
                raise ValueError(
                    f"episode {spec.episode_id} has no agents for expert policy "
                    f"{policy_version_id}"
                )
            seats.extend(candidates[: spec.max_povs_per_policy])
    else:
        seats = list(spec.povs)
    resolved = []
    for seat in seats:
        if seat not in agents:
            raise ValueError(f"episode {spec.episode_id} has no seat {seat}")
        reward, policy = agents[seat]
        if spec.minimum_reward is not None and reward < spec.minimum_reward:
            raise ValueError(
                f"episode {spec.episode_id} seat {seat} reward {reward} is below "
                f"minimum_reward {spec.minimum_reward}"
            )
        resolved.append((seat, reward, policy))
    return resolved


class SourceManager:
    def __init__(
        self,
        repository: str,
        workspace: Path,
        existing_source_root: Path | None,
    ) -> None:
        self.repository = repository
        self.workspace = workspace.resolve() / "sources"
        self.existing_source_root = (
            existing_source_root.resolve() if existing_source_root is not None else None
        )
        self._binary_cache: dict[str, tuple[Path, Path, Path]] = {}

    def checkout(self, commit: str) -> Path:
        existing = self._existing_checkout(commit)
        if existing is not None:
            return existing
        repository = self.workspace / "repository"
        checkout = self.workspace / "worktrees" / commit[:12]
        if not repository.exists():
            repository.parent.mkdir(parents=True, exist_ok=True)
            run_command(
                [
                    "git",
                    "clone",
                    "--filter=blob:none",
                    "--no-checkout",
                    self.repository,
                    str(repository),
                ]
            )
        run_command(["git", "fetch", "origin", commit], cwd=repository)
        if not checkout.exists():
            checkout.parent.mkdir(parents=True, exist_ok=True)
            run_command(
                ["git", "worktree", "add", "--detach", str(checkout), commit], cwd=repository
            )
        actual = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=checkout, text=True
        ).strip()
        if actual != commit:
            raise ValueError(f"source checkout {checkout} is {actual}, expected {commit}")
        return checkout

    def binaries(self, commit: str) -> tuple[Path, Path, Path]:
        if commit in self._binary_cache:
            return self._binary_cache[commit]
        checkout = self.checkout(commit)
        generated = checkout / ".paintbot_rl"
        wire_binary = generated / "extract_replay_wire"
        action_binary = generated / "extract_replay_actions"
        sources = (
            (
                RL_ROOT / "extract_replay_wire.nim",
                checkout / "paintbot_rl_extract_replay_wire.nim",
                wire_binary,
            ),
            (
                RL_ROOT / "extract_replay_actions.nim",
                checkout / "paintbot_rl_extract_replay_actions.nim",
                action_binary,
            ),
        )
        generated.mkdir(parents=True, exist_ok=True)
        needs_compile = any(
            not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime
            for source, _, binary in sources
        )
        if needs_compile:
            # The exact checkout's nimby.lock is part of replay provenance.
            nimby_lock = Path.home() / ".nimby" / "paintbot-rl-sync.lock"
            nimby_lock.parent.mkdir(parents=True, exist_ok=True)
            with nimby_lock.open("w") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                run_command(["nimby", "sync", "-g", "nimby.lock"], cwd=checkout)
                for source, copied_source, binary in sources:
                    shutil.copy2(source, copied_source)
                    run_command(
                        [
                            "nim",
                            "c",
                            "-d:release",
                            f"--nimcache:{generated / ('nimcache-' + binary.name)}",
                            f"--path:{checkout / 'src'}",
                            f"--out:{binary}",
                            str(copied_source),
                        ],
                        cwd=checkout,
                    )
        binaries = (checkout, wire_binary, action_binary)
        self._binary_cache[commit] = binaries
        return binaries

    def _existing_checkout(self, commit: str) -> Path | None:
        if self.existing_source_root is None:
            return None
        for candidate in self.existing_source_root.iterdir():
            if not candidate.is_dir():
                continue
            try:
                actual = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=candidate, text=True
                ).strip()
            except subprocess.CalledProcessError:
                continue
            if actual == commit:
                return candidate
        return None


def find_cached_wire(root: Path | None, episode_id: str, seat: int) -> Path | None:
    if root is None:
        return None
    matches = list(root.rglob(f"*{episode_id[:8]}*seat{seat}.jsonl"))
    if len(matches) > 1:
        raise ValueError(f"ambiguous cached wire for {episode_id} seat {seat}: {matches}")
    return matches[0] if matches else None


def add_temporal_history(
    samples,
    *,
    wire: Path,
    game_version: str,
    timeline: ActionTimeline,
    history_ticks: int,
    extract,
):
    """Attach bounded past-only deltas to already aligned, strided samples."""
    if history_ticks == 0:
        return samples
    target_ticks = {sample.observation_tick for sample in samples}
    selected_ticks = {
        tick - offset
        for tick in target_ticks
        for offset in range(history_ticks + 2)
        if tick - offset >= 0
    }
    snapshots = extract(
        wire,
        game_version=game_version,
        stride=1,
        selected_ticks=selected_ticks,
    )
    by_tick = {snapshot.tick: snapshot for snapshot in snapshots if snapshot.tick is not None}
    temporal_samples = []
    for sample in samples:
        tick = sample.observation_tick
        if any(tick - offset not in by_tick for offset in range(history_ticks + 2)):
            continue
        history = []
        for offset in range(history_ticks, 0, -1):
            history.append(
                temporal_delta(
                    by_tick[tick - offset - 1],
                    by_tick[tick - offset],
                    action_mask=timeline.mask_at(tick - offset),
                    target_tick=tick,
                )
            )
        temporal_samples.append(replace(sample, history=tuple(history)))
    return temporal_samples


def prepare(
    manifest: PipelineManifest,
    workspace: Path,
    *,
    artifacts_root: Path,
    existing_source_root: Path | None,
    wire_cache_root: Path | None,
) -> dict:
    from capture_wire_observations import extract

    manager = SourceManager(manifest.source_repository, workspace, existing_source_root)
    trajectories = workspace / "trajectories"
    all_samples: dict[str, list] = defaultdict(list)
    all_maps = {}
    records = []
    failures = []
    artifact_directories = index_episode_directories(artifacts_root)
    for episode in manifest.episodes:
        try:
            episode_dir = artifact_directories[episode.episode_id]
            replay = episode_dir / "replay.json"
            if not replay.exists():
                raise FileNotFoundError(f"downloaded episode has no replay: {replay}")
            resolved_povs = resolve_povs(episode, episode_dir / "episode.json")
        except Exception as error:
            if not manifest.preparation.continue_on_error:
                raise
            failures.append({"episode_id": episode.episode_id, "error": str(error)})
            continue
        for seat, reward, policy in resolved_povs:
            stem = f"gv{episode.game_version}-{episode.episode_id[:8]}-seat{seat}"
            output = trajectories / stem
            output.mkdir(parents=True, exist_ok=True)
            record_path = output / "trajectory.json"
            try:
                if record_path.exists():
                    record = json.loads(record_path.read_text())
                    samples = (
                        read_samples(output / "samples.jsonl")
                        if manifest.preparation.balance_versions
                        else []
                    )
                    episode_maps = read_maps(output / "map.jsonl")
                    if len(episode_maps) != 1:
                        raise ValueError(f"expected one map in {output / 'map.jsonl'}")
                    map_hash, episode_map = next(iter(episode_maps.items()))
                else:
                    wire = find_cached_wire(wire_cache_root, episode.episode_id, seat)
                    checkout: Path | None = None
                    if wire is None:
                        checkout, wire_binary, action_binary = manager.binaries(
                            episode.source_commit
                        )
                        wire = output / "wire.jsonl"
                        run_command(
                            [
                                str(wire_binary),
                                str(replay.resolve()),
                                str(seat),
                                str(wire.resolve()),
                            ],
                            cwd=checkout,
                        )
                    else:
                        checkout, _, action_binary = manager.binaries(
                            episode.source_commit
                        )

                    actions = output / "actions.jsonl"
                    run_command(
                        [
                            str(action_binary),
                            str(replay.resolve()),
                            episode.game_version,
                            str(seat),
                            str(actions.resolve()),
                        ],
                        cwd=checkout,
                    )
                    snapshots_path = output / "observations.jsonl"
                    map_path = output / "map.jsonl"
                    snapshots = extract(
                        wire,
                        game_version=episode.game_version,
                        stride=manifest.preparation.stride,
                        map_out=map_path,
                    )
                    write_jsonl(snapshots_path, snapshots)
                    episode_maps = read_maps(map_path)
                    if len(episode_maps) != 1:
                        raise ValueError(f"expected one map in {map_path}")
                    map_hash, episode_map = next(iter(episode_maps.items()))
                    timeline = ActionTimeline(read_actions(actions))
                    samples = build_samples(
                        snapshots,
                        timeline,
                        replay_id=episode.episode_id,
                        pov=seat,
                        map_hash=map_hash,
                        action_delay_ticks=manifest.preparation.action_delay_ticks,
                    )
                    samples = add_temporal_history(
                        samples,
                        wire=wire,
                        game_version=episode.game_version,
                        timeline=timeline,
                        history_ticks=manifest.preparation.history_ticks,
                        extract=extract,
                    )
                    write_jsonl(output / "samples.jsonl", samples)
                    raw_entities = sum(len(snapshot.entities) for snapshot in snapshots)
                    retained_entities = sum(
                        len(sample.observation["entities"]) for sample in samples
                    )
                    record = {
                        "episode_id": episode.episode_id,
                        "game_version": episode.game_version,
                        "source_commit": episode.source_commit,
                        "split": episode.split,
                        "seat": seat,
                        "policy": policy,
                        "reward": reward,
                        "observations": len(snapshots),
                        "samples": len(samples),
                        "raw_entities": raw_entities,
                        "retained_entities": retained_entities,
                        "wire_source": str(wire),
                        "map_hash": map_hash,
                        "trajectory": stem,
                    }
                    record_path.write_text(json.dumps(record, indent=2) + "\n")
                record["expert_player_id"] = (
                    episode.expert_player_id(policy)
                    if episode.expert_players
                    else policy
                )
                record["world"] = episode.coworld_name
                if not manifest.preparation.retain_intermediates:
                    for intermediate in ("wire.jsonl", "actions.jsonl", "observations.jsonl"):
                        (output / intermediate).unlink(missing_ok=True)
                if manifest.preparation.balance_versions:
                    all_samples[episode.split].extend(samples)
                all_maps[map_hash] = episode_map
                records.append(record)
            except Exception as error:
                if not manifest.preparation.continue_on_error:
                    raise
                failures.append(
                    {
                        "episode_id": episode.episode_id,
                        "seat": seat,
                        "game_version": episode.game_version,
                        "source_commit": episode.source_commit,
                        "error": str(error),
                    }
                )

    if (
        manifest.preparation.prune_trajectory_artifacts_after_prepare
        and not manifest.preparation.balance_versions
    ):
        return prepare_large_arrow_corpus(manifest, workspace, records, failures, all_maps)

    prepared = workspace / "prepared"
    prepared.mkdir(parents=True, exist_ok=True)
    split_counts = {}
    for split in ("train", "validation", "test"):
        if manifest.preparation.balance_versions:
            selected = balanced_by_version_and_trajectory(
                all_samples.get(split, []),
                manifest.preparation.max_samples_per_version,
                manifest.preparation.seed,
            )
            write_jsonl(prepared / f"{split}.samples.jsonl", selected)
            used_maps = {sample.map_hash for sample in selected}
            split_counts[split] = len(selected)
        else:
            split_records = [record for record in records if record["split"] == split]
            samples_path = prepared / f"{split}.samples.jsonl"
            count = 0
            with samples_path.open("w") as destination:
                for record in split_records:
                    source_path = trajectories / record["trajectory"] / "samples.jsonl"
                    with source_path.open() as source:
                        shutil.copyfileobj(source, destination)
                    count += int(record["samples"])
            used_maps = {record["map_hash"] for record in split_records}
            split_counts[split] = count
        write_jsonl(
            prepared / f"{split}.maps.jsonl",
            (all_maps[map_hash] for map_hash in sorted(used_maps)),
        )
    summary = {
        "schema_version": 1,
        "created_at_unix": time.time(),
        "manifest": asdict(manifest),
        "split_counts": split_counts,
        "trajectories": records,
        "failures": failures,
    }
    (prepared / "provenance.json").write_text(json.dumps(summary, indent=2) + "\n")
    if manifest.preparation.prune_trajectory_artifacts_after_prepare:
        for record in records:
            trajectory = trajectories / record["trajectory"]
            (trajectory / "samples.jsonl").unlink(missing_ok=True)
            (trajectory / "map.jsonl").unlink(missing_ok=True)
    print(json.dumps({"prepared": str(prepared), "split_counts": split_counts}, indent=2))
    return summary


def prepare_large_arrow_corpus(
    manifest: PipelineManifest,
    workspace: Path,
    records: list[dict],
    failures: list[dict],
    all_maps: dict,
    *,
    trajectories_per_part: int = 512,
) -> dict:
    """Convert bounded trajectory groups to Arrow before discarding their JSON."""
    from corpus_store import convert_split
    from merge_prepared_shards import write_shard_manifest

    trajectories = workspace / "trajectories"
    prepared = workspace / "prepared"
    arrow = workspace / "arrow"
    staging = arrow / "staging"
    prepared.mkdir(parents=True, exist_ok=True)
    staging.mkdir(parents=True, exist_ok=True)
    split_counts = {}
    for split in ("train", "validation", "test"):
        split_records = [record for record in records if record["split"] == split]
        parts = []
        count = 0
        for part_number, start in enumerate(range(0, len(split_records), trajectories_per_part)):
            part_records = split_records[start : start + trajectories_per_part]
            part = arrow / "parts" / split / f"part-{part_number:05d}"
            source_path = staging / f"{split}-part-{part_number:05d}.samples.jsonl"
            expected = sum(int(record["samples"]) for record in part_records)
            if not (part / "dataset_info.json").exists():
                with source_path.open("w") as destination:
                    for record in part_records:
                        trajectory_samples = (
                            trajectories / record["trajectory"] / "samples.jsonl"
                        )
                        if not trajectory_samples.exists():
                            raise FileNotFoundError(
                                f"missing unconverted trajectory samples: {trajectory_samples}"
                            )
                        with trajectory_samples.open() as source:
                            shutil.copyfileobj(source, destination)
            metadata = {
                (record["episode_id"], int(record["seat"])): {
                    "expert_player_id": record["expert_player_id"],
                    "world": record["world"],
                }
                for record in part_records
            }
            actual = convert_split(source_path, part, metadata)
            if actual != expected:
                raise ValueError(
                    f"{split} Arrow part {part_number} count {actual} != {expected}"
                )
            parts.append(part)
            count += actual
            source_path.unlink(missing_ok=True)
            for record in part_records:
                (trajectories / record["trajectory"] / "samples.jsonl").unlink(
                    missing_ok=True
                )
        write_shard_manifest(arrow / split, parts, count)
        split_counts[split] = count

    maps_path = prepared / "maps.jsonl"
    if not maps_path.exists():
        temporary = prepared / ".maps.jsonl.incomplete"
        write_jsonl(temporary, (all_maps[map_hash] for map_hash in sorted(all_maps)))
        temporary.replace(maps_path)
    for split in ("train", "validation", "test"):
        split_maps = prepared / f"{split}.maps.jsonl"
        if split_maps.exists():
            split_maps.unlink()
        os.link(maps_path, split_maps)

    summary = {
        "schema_version": 1,
        "created_at_unix": time.time(),
        "manifest": asdict(manifest),
        "storage": "virtual_arrow_shards",
        "split_counts": split_counts,
        "trajectories": records,
        "failures": failures,
    }
    (arrow / "provenance.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "storage": "virtual_arrow_shards",
                "split_counts": split_counts,
            },
            indent=2,
        )
        + "\n"
    )
    (prepared / "provenance.json").write_text(json.dumps(summary, indent=2) + "\n")
    for record in records:
        trajectory = trajectories / record["trajectory"]
        (trajectory / "map.jsonl").unlink(missing_ok=True)
    print(json.dumps({"prepared": str(prepared), "split_counts": split_counts}, indent=2))
    return summary


def balanced_by_version_and_trajectory(samples, cap: int | None, seed: int):
    """Equalize eras, then round-robin replays so long episodes cannot dominate."""
    by_version = defaultdict(lambda: defaultdict(list))
    for sample in samples:
        by_version[sample.game_version][(sample.replay_id, sample.pov)].append(sample)
    if not by_version:
        return []
    target_per_version = min(
        sum(len(trajectory) for trajectory in trajectories.values())
        for trajectories in by_version.values()
    )
    if cap is not None:
        target_per_version = min(target_per_version, cap)
    selected = []
    rng = random.Random(seed)
    for version in sorted(by_version, key=int):
        trajectories = list(by_version[version].values())
        for trajectory in trajectories:
            rng.shuffle(trajectory)
        version_samples = []
        index = 0
        while any(index < len(trajectory) for trajectory in trajectories):
            for trajectory in trajectories:
                if index < len(trajectory):
                    version_samples.append(trajectory[index])
                    if len(version_samples) >= target_per_version:
                        break
            if len(version_samples) >= target_per_version:
                break
            index += 1
        selected.extend(version_samples)
    rng.shuffle(selected)
    return selected


def train_stage(manifest: PipelineManifest, workspace: Path, *, resume_from: Path | None) -> None:
    from training import train

    prepared = workspace / "prepared"
    config = manifest.training
    train(
        prepared / "train.samples.jsonl",
        prepared / "train.maps.jsonl",
        workspace / "checkpoint",
        validation_samples_path=prepared / "validation.samples.jsonl",
        validation_maps_path=prepared / "validation.maps.jsonl",
        tuning=config.tuning,
        epochs=config.epochs,
        batch_size=config.batch_size,
        gradient_accumulation=config.gradient_accumulation,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        warmup_ratio=config.warmup_ratio,
        max_text_tokens=config.max_text_tokens,
        max_history_tokens=config.max_history_tokens,
        mixed_precision=config.mixed_precision,
        action_change_weight=config.action_change_weight,
        seed=config.seed,
        resume_from=resume_from,
    )


def evaluate_stage(manifest: PipelineManifest, workspace: Path) -> None:
    prepared = workspace / "prepared"
    checkpoint = workspace / "checkpoint"
    for split in ("validation", "test"):
        samples = prepared / f"{split}.samples.jsonl"
        maps = prepared / f"{split}.maps.jsonl"
        if not samples.exists() or samples.stat().st_size == 0:
            continue
        run_command(
            [
                sys.executable,
                str(RL_ROOT / "evaluate_sft.py"),
                "--checkpoint",
                str(checkpoint),
                "--samples",
                str(samples),
                "--maps",
                str(maps),
                "--max-text-tokens",
                str(manifest.training.max_text_tokens),
                "--out",
                str(checkpoint / f"{split}_evaluation.json"),
            ],
            cwd=RL_ROOT,
        )


def bundle(workspace: Path, output: Path) -> None:
    prepared = workspace / "prepared"
    if not (prepared / "provenance.json").exists():
        raise FileNotFoundError("prepare the dataset before bundling it")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        archive.add(prepared, arcname="prepared")
    print(f"wrote GPU-ready dataset bundle to {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage", choices=("download", "prepare", "train", "evaluate", "all", "bundle")
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--artifacts-root", type=Path)
    parser.add_argument("--existing-source-root", type=Path)
    parser.add_argument("--wire-cache-root", type=Path)
    parser.add_argument("--elevated", action="store_true")
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--bundle-out", type=Path)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    args.workspace = args.workspace.resolve()
    args.workspace.mkdir(parents=True, exist_ok=True)

    artifacts_root = (args.artifacts_root or args.workspace / "raw").resolve()
    if args.stage in {"download", "all"}:
        print("Downloading Coworld episode artifacts for the declared manifest.", flush=True)
        artifacts_root = download(manifest, args.workspace, elevated=args.elevated)
    if args.stage in {"prepare", "all"}:
        prepare(
            manifest,
            args.workspace,
            artifacts_root=artifacts_root,
            existing_source_root=args.existing_source_root,
            wire_cache_root=args.wire_cache_root,
        )
    if args.stage in {"train", "all"}:
        train_stage(manifest, args.workspace, resume_from=args.resume_from)
    if args.stage in {"evaluate", "all"}:
        evaluate_stage(manifest, args.workspace)
    if args.stage == "bundle":
        bundle(args.workspace, args.bundle_out or args.workspace.with_suffix(".tar.gz"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
