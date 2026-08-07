#!/usr/bin/env python3
"""Reproducible historical-replay preparation and SFT training pipeline."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import tarfile
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from dataset import ActionTimeline, build_samples, read_actions, read_maps, write_jsonl
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
    for episode in manifest.episodes:
        command.extend(("--episode", episode.episode_id))
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


def resolve_povs(spec: EpisodeSpec, metadata_path: Path) -> list[tuple[int, float, str]]:
    metadata = json.loads(metadata_path.read_text())
    agents: dict[int, tuple[float, str]] = {}
    for policy_result in metadata.get("policy_results") or ():
        policy = policy_result.get("policy") or {}
        policy_label = f"{policy.get('name', 'unknown')}:{policy.get('version', 'unknown')}"
        for agent in policy_result.get("agents") or ():
            agents[int(agent["agent_id"])] = (float(agent.get("reward", 0)), policy_label)
    if not agents:
        raise ValueError(f"{metadata_path} has no policy_results agent metadata")
    seats = (
        [max(agents, key=lambda seat: (agents[seat][0], -seat))]
        if spec.povs == "best_reward"
        else list(spec.povs)
    )
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
            run_command(["nimby", "sync", "-g", "nimby.lock"], cwd=checkout)
            for source, copied_source, binary in sources:
                shutil.copy2(source, copied_source)
                run_command(
                    [
                        "nim",
                        "c",
                        "-d:release",
                        f"--path:{checkout / 'src'}",
                        f"--out:{binary}",
                        str(copied_source),
                    ],
                    cwd=checkout,
                )
        return checkout, wire_binary, action_binary

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
    for episode in manifest.episodes:
        episode_dir = find_episode_directory(artifacts_root, episode.episode_id)
        replay = episode_dir / "replay.json"
        for seat, reward, policy in resolve_povs(episode, episode_dir / "episode.json"):
            stem = f"gv{episode.game_version}-{episode.episode_id[:8]}-seat{seat}"
            output = trajectories / stem
            output.mkdir(parents=True, exist_ok=True)
            wire = find_cached_wire(wire_cache_root, episode.episode_id, seat)
            checkout: Path | None = None
            if wire is None:
                checkout, wire_binary, action_binary = manager.binaries(episode.source_commit)
                wire = output / "wire.jsonl"
                run_command(
                    [str(wire_binary), str(replay.resolve()), str(seat), str(wire.resolve())],
                    cwd=checkout,
                )
            else:
                checkout, _, action_binary = manager.binaries(episode.source_commit)

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
            samples = build_samples(
                snapshots,
                ActionTimeline(read_actions(actions)),
                replay_id=episode.episode_id,
                pov=seat,
                map_hash=map_hash,
                action_delay_ticks=manifest.preparation.action_delay_ticks,
            )
            write_jsonl(output / "samples.jsonl", samples)
            all_samples[episode.split].extend(samples)
            all_maps[map_hash] = episode_map
            raw_entities = sum(len(snapshot.entities) for snapshot in snapshots)
            retained_entities = sum(
                len(sample.observation["entities"]) for sample in samples
            )
            records.append(
                {
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
                }
            )

    prepared = workspace / "prepared"
    prepared.mkdir(parents=True, exist_ok=True)
    split_counts = {}
    for split in ("train", "validation", "test"):
        selected = balanced_by_version_and_trajectory(
            all_samples.get(split, []),
            manifest.preparation.max_samples_per_version,
            manifest.preparation.seed,
        )
        write_jsonl(prepared / f"{split}.samples.jsonl", selected)
        used_maps = {sample.map_hash for sample in selected}
        write_jsonl(
            prepared / f"{split}.maps.jsonl",
            (all_maps[map_hash] for map_hash in sorted(used_maps)),
        )
        split_counts[split] = len(selected)
    summary = {
        "schema_version": 1,
        "created_at_unix": time.time(),
        "manifest": asdict(manifest),
        "split_counts": split_counts,
        "trajectories": records,
    }
    (prepared / "provenance.json").write_text(json.dumps(summary, indent=2) + "\n")
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
