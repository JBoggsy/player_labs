#!/usr/bin/env python3
"""Merge independently prepared replay shards into one training-ready corpus."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path


SPLITS = ("train", "validation", "test")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    prepared_dirs = sorted(args.shards_root.glob("shard-*/prepared"))
    if not prepared_dirs:
        raise FileNotFoundError(f"no shard-*/prepared directories under {args.shards_root}")
    args.out.mkdir(parents=True, exist_ok=True)

    maps: dict[str, dict] = {}
    split_counts = {}
    shard_summaries = []
    total_failures = 0
    for prepared in prepared_dirs:
        provenance_path = prepared / "provenance.json"
        provenance = json.loads(provenance_path.read_text())
        total_failures += len(provenance.get("failures", ()))
        shard_summaries.append(
            {
                "prepared": str(prepared),
                "provenance": str(provenance_path),
                "split_counts": provenance["split_counts"],
                "trajectories": len(provenance.get("trajectories", ())),
                "failures": len(provenance.get("failures", ())),
            }
        )
        for split in SPLITS:
            maps_path = prepared / f"{split}.maps.jsonl"
            if maps_path.exists():
                with maps_path.open() as source:
                    for line in source:
                        item = json.loads(line)
                        existing = maps.get(item["map_hash"])
                        if existing is not None and existing != item:
                            raise ValueError(f"conflicting map payload {item['map_hash']}")
                        maps[item["map_hash"]] = item

    for split in SPLITS:
        count = 0
        with (args.out / f"{split}.samples.jsonl").open("w") as destination:
            for prepared in prepared_dirs:
                source_path = prepared / f"{split}.samples.jsonl"
                if not source_path.exists():
                    continue
                with source_path.open() as source:
                    shutil.copyfileobj(source, destination)
                count += json.loads((prepared / "provenance.json").read_text())[
                    "split_counts"
                ][split]
        split_counts[split] = count
        with (args.out / f"{split}.maps.jsonl").open("w") as destination:
            for map_hash in sorted(maps):
                destination.write(json.dumps(maps[map_hash]) + "\n")

    summary = {
        "schema_version": 1,
        "created_at_unix": time.time(),
        "split_counts": split_counts,
        "unique_maps": len(maps),
        "failures": total_failures,
        "shards": shard_summaries,
    }
    (args.out / "provenance.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
