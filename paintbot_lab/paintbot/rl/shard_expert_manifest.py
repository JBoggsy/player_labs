#!/usr/bin/env python3
"""Select a coverage-balanced expert corpus and split it into resumable shards."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def stable_order(value: str, seed: int) -> bytes:
    return hashlib.sha256(f"{seed}:{value}".encode()).digest()


def coverage_keys(episode: dict[str, Any]) -> set[tuple[str, str, str]]:
    players = {
        policy["player_id"]
        for policy in episode.get("expert_policies", ())
        if policy.get("player_id")
    }
    return {
        (episode["coworld_name"], episode["game_version"], player_id)
        for player_id in players
    }


def select_episodes(
    episodes: list[dict[str, Any]], maximum: int | None, seed: int
) -> list[dict[str, Any]]:
    if maximum is None or maximum >= len(episodes):
        return episodes
    if maximum <= 0:
        raise ValueError("maximum must be positive")

    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        for key in coverage_keys(episode):
            buckets[key].append(episode)
    for bucket in buckets.values():
        bucket.sort(key=lambda item: stable_order(item["episode_id"], seed))

    selected: dict[str, dict[str, Any]] = {}
    positions = Counter()
    keys = sorted(buckets, key=lambda item: stable_order(":".join(item), seed))
    while len(selected) < maximum:
        made_progress = False
        for key in keys:
            bucket = buckets[key]
            while positions[key] < len(bucket):
                episode = bucket[positions[key]]
                positions[key] += 1
                if episode["episode_id"] not in selected:
                    selected[episode["episode_id"]] = episode
                    made_progress = True
                    break
            if len(selected) == maximum:
                break
        if not made_progress:
            break
    return sorted(selected.values(), key=lambda item: item["episode_id"])


def counts(episodes: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    experts = Counter()
    for episode in episodes:
        experts.update(
            policy["player_id"]
            for policy in episode.get("expert_policies", ())
            if policy.get("player_id")
        )
    return {
        "worlds": dict(sorted(Counter(item["coworld_name"] for item in episodes).items())),
        "game_versions": dict(
            sorted(
                Counter(item["game_version"] for item in episodes).items(),
                key=lambda item: int(item[0]),
            )
        ),
        "splits": dict(sorted(Counter(item["split"] for item in episodes).items())),
        "expert_policy_episodes": dict(sorted(experts.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--shards", type=int, default=8)
    parser.add_argument("--max-episodes", type=int)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    if args.shards <= 0:
        parser.error("--shards must be positive")

    manifest = json.loads(args.manifest.read_text())
    selected = select_episodes(manifest["episodes"], args.max_episodes, args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    shard_episodes: list[list[dict[str, Any]]] = [[] for _ in range(args.shards)]
    for episode in selected:
        shard = int.from_bytes(stable_order(episode["episode_id"], args.seed)[:8], "big")
        shard_episodes[shard % args.shards].append(episode)

    shard_paths = []
    base = {key: value for key, value in manifest.items() if key != "episodes"}
    for index, episodes in enumerate(shard_episodes):
        if not episodes:
            continue
        path = args.out / f"shard-{index:02d}.json"
        path.write_text(json.dumps({**base, "episodes": episodes}, indent=2) + "\n")
        shard_paths.append(str(path))

    summary = {
        "schema_version": 1,
        "source_manifest": str(args.manifest),
        "available_episodes": len(manifest["episodes"]),
        "selected_episodes": len(selected),
        "shards": len(shard_paths),
        "episodes_per_shard": [len(items) for items in shard_episodes if items],
        "coverage": counts(selected),
        "shard_manifests": shard_paths,
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
