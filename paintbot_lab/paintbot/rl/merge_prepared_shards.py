#!/usr/bin/env python3
"""Convert prepared replay shards into one virtual, disk-bounded Arrow corpus."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from corpus_store import convert_split, trajectory_metadata_from_provenance


SPLITS = ("train", "validation", "test")


def write_shard_manifest(path: Path, parts: list[Path], count: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    value = {
        "schema_version": 1,
        "count": count,
        "shards": [os.path.relpath(part, path) for part in parts],
    }
    temporary = path / ".shards.json.incomplete"
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path / "shards.json")


def merge_maps(prepared_dirs: list[Path], output: Path) -> int:
    final = output / "maps.jsonl"
    if final.exists():
        unique_maps = sum(1 for _ in final.open())
    else:
        temporary = output / ".maps.jsonl.incomplete"
        seen = set()
        with temporary.open("w") as destination:
            for prepared in prepared_dirs:
                for split in SPLITS:
                    source_path = prepared / f"{split}.maps.jsonl"
                    if not source_path.exists():
                        continue
                    with source_path.open() as source:
                        for line in source:
                            map_hash = json.loads(line)["map_hash"]
                            if map_hash not in seen:
                                seen.add(map_hash)
                                destination.write(line)
        temporary.replace(final)
        unique_maps = len(seen)
    for split in SPLITS:
        split_path = output / f"{split}.maps.jsonl"
        if split_path.exists():
            split_path.unlink()
        os.link(final, split_path)
    for prepared in prepared_dirs:
        for split in SPLITS:
            (prepared / f"{split}.maps.jsonl").unlink(missing_ok=True)
        (prepared / "maps.jsonl").unlink(missing_ok=True)
    return unique_maps


def merge_shards(shards_root: Path, output: Path) -> dict:
    prepared_dirs = sorted(shards_root.glob("shard-*/prepared"))
    if not prepared_dirs:
        raise FileNotFoundError(f"no shard-*/prepared directories under {shards_root}")
    workspace = shards_root.parent
    arrow = workspace / "arrow"
    output.mkdir(parents=True, exist_ok=True)

    split_counts = {split: 0 for split in SPLITS}
    split_parts = {split: [] for split in SPLITS}
    shard_summaries = []
    total_failures = 0
    for prepared in prepared_dirs:
        shard_name = prepared.parent.name
        provenance_path = prepared / "provenance.json"
        provenance = json.loads(provenance_path.read_text())
        total_failures += len(provenance.get("failures", ()))
        shard_summary = {
            "prepared": str(prepared),
            "provenance": str(provenance_path),
            "split_counts": provenance["split_counts"],
            "trajectories": len(provenance.get("trajectories", ())),
            "failures": len(provenance.get("failures", ())),
        }
        shard_arrow = prepared.parent / "arrow"
        if provenance.get("storage") == "virtual_arrow_shards":
            for split in SPLITS:
                expected = int(provenance["split_counts"][split])
                if expected:
                    manifest = shard_arrow / split / "shards.json"
                    if not manifest.exists():
                        raise FileNotFoundError(f"missing Arrow manifest: {manifest}")
                    split_parts[split].append(shard_arrow / split)
                    split_counts[split] += expected
        else:
            manifest_path = workspace / "manifests" / f"{shard_name}.json"
            episodes = {
                item["episode_id"]: item
                for item in json.loads(manifest_path.read_text())["episodes"]
            }
            metadata = trajectory_metadata_from_provenance(episodes, provenance_path)
            for split in SPLITS:
                expected = int(provenance["split_counts"][split])
                source_path = prepared / f"{split}.samples.jsonl"
                part = arrow / "parts" / shard_name / split
                if expected:
                    if not source_path.exists() and not (part / "dataset_info.json").exists():
                        raise FileNotFoundError(
                            f"missing source and Arrow output for {shard_name} {split}"
                        )
                    actual = convert_split(source_path, part, metadata)
                    if actual != expected:
                        raise ValueError(
                            f"{shard_name} {split} Arrow count {actual} != prepared count {expected}"
                        )
                    split_parts[split].append(part)
                    split_counts[split] += actual
                    source_path.unlink(missing_ok=True)
                else:
                    source_path.unlink(missing_ok=True)
        shard_summaries.append(shard_summary)

    for split in SPLITS:
        write_shard_manifest(arrow / split, split_parts[split], split_counts[split])
    unique_maps = merge_maps(prepared_dirs, output)
    arrow_summary = {
        "schema_version": 1,
        "created_at_unix": time.time(),
        "storage": "virtual_arrow_shards",
        "split_counts": split_counts,
        "metadata_columns": [
            "changed_action",
            "game_version",
            "expert_player_id",
            "world",
        ],
    }
    (arrow / "provenance.json").write_text(json.dumps(arrow_summary, indent=2) + "\n")
    summary = {
        "schema_version": 1,
        "created_at_unix": time.time(),
        "storage": "virtual_arrow_shards",
        "split_counts": split_counts,
        "unique_maps": unique_maps,
        "failures": total_failures,
        "shards": shard_summaries,
    }
    (output / "provenance.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary = merge_shards(args.shards_root, args.out)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
