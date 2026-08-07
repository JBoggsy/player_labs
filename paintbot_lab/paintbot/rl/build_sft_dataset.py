#!/usr/bin/env python3
"""Join captured observations, an episode map, and replay actions into SFT JSONL."""

from __future__ import annotations

import argparse
from pathlib import Path

from dataset import ActionTimeline, build_samples, read_actions, read_maps, write_jsonl
from observation_text import snapshots_from_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--actions", type=Path, required=True)
    parser.add_argument("--maps", type=Path, required=True)
    parser.add_argument("--map-hash", required=True)
    parser.add_argument("--replay-id", required=True)
    parser.add_argument("--pov", type=int, required=True)
    parser.add_argument("--action-delay-ticks", type=int, default=0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    episode_maps = read_maps(args.maps)
    if args.map_hash not in episode_maps:
        parser.error(f"map hash {args.map_hash!r} is absent from {args.maps}")
    with args.snapshots.open() as source:
        snapshots = list(snapshots_from_jsonl(source))
    samples = build_samples(
        snapshots,
        ActionTimeline(read_actions(args.actions)),
        replay_id=args.replay_id,
        pov=args.pov,
        map_hash=args.map_hash,
        action_delay_ticks=args.action_delay_ticks,
    )
    write_jsonl(args.out, samples)
    print(f"wrote {len(samples)} SFT samples to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
