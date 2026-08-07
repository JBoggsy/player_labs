#!/usr/bin/env python3
"""Deduplicate maps and sample a balanced cross-era SFT corpus."""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path

from dataset import read_maps, read_samples, write_jsonl


def balanced_samples(
    paths: list[Path],
    per_version: int,
    seed: int,
    excluded: set[tuple[str, int, int]] | None = None,
):
    excluded = excluded or set()
    by_version = defaultdict(list)
    for path in paths:
        for sample in read_samples(path):
            if (sample.replay_id, sample.pov, sample.observation_tick) in excluded:
                continue
            by_version[sample.game_version].append(sample)
    if len(by_version) < 2:
        raise ValueError("a cross-era corpus requires at least two GameVersions")
    rng = random.Random(seed)
    selected = []
    for version in sorted(by_version, key=int):
        candidates = by_version[version]
        rng.shuffle(candidates)
        selected.extend(candidates[:per_version])
    rng.shuffle(selected)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, nargs="+", required=True)
    parser.add_argument("--maps", type=Path, nargs="+", required=True)
    parser.add_argument("--exclude-samples", type=Path, nargs="*")
    parser.add_argument("--per-version", type=int, default=25)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--samples-out", type=Path, required=True)
    parser.add_argument("--maps-out", type=Path, required=True)
    args = parser.parse_args()
    if args.per_version <= 0:
        parser.error("--per-version must be positive")

    excluded = set()
    for path in args.exclude_samples or ():
        excluded.update(
            (sample.replay_id, sample.pov, sample.observation_tick)
            for sample in read_samples(path)
        )
    samples = balanced_samples(args.samples, args.per_version, args.seed, excluded)
    maps = {}
    for path in args.maps:
        maps.update(read_maps(path))
    missing = {sample.map_hash for sample in samples} - maps.keys()
    if missing:
        parser.error(f"selected samples reference missing maps: {sorted(missing)}")
    write_jsonl(args.samples_out, samples)
    write_jsonl(args.maps_out, (maps[map_hash] for map_hash in sorted(maps)))
    versions = sorted({sample.game_version for sample in samples}, key=int)
    print(f"wrote {len(samples)} samples across GameVersions {versions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
