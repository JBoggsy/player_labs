#!/usr/bin/env python3
"""Summarize Beacon item acquisition and contention from hosted trace artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile


def _episode_key(path: Path) -> str:
    return str(path.parent.parent)


def analyze(root: Path) -> dict[str, object]:
    artifacts = 0
    snapshots = 0
    final_counters: Counter[str] = Counter()
    choices: Counter[str] = Counter()
    accepted_choices: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    pickups: Counter[str] = Counter()
    heals = 0
    pursuits: dict[
        tuple[str, int, str, tuple[int, int]], set[str]
    ] = defaultdict(set)

    for archive in root.rglob("policy_artifact_*.zip"):
        latest: dict[str, object] | None = None
        saw_item_trace = False
        with ZipFile(archive) as zipped:
            if "telemetry.jsonl" not in zipped.namelist():
                continue
            for raw in zipped.read("telemetry.jsonl").splitlines():
                row = json.loads(raw)
                event = row.get("event")
                data = row.get("data", {})
                if event == "snapshot" and "item_opportunity_ticks" in data:
                    saw_item_trace = True
                    snapshots += 1
                    latest = data
                    choice = data.get("item_choice")
                    if choice is not None:
                        kind = choice["kind"]
                        reason = choice["reason"]
                        choices[kind] += 1
                        reasons[reason] += 1
                        if choice["accepted"]:
                            accepted_choices[kind] += 1
                            spawn = tuple(choice["spawn"])
                            key = (
                                _episode_key(archive),
                                row["tick"],
                                kind,
                                spawn,
                            )
                            pursuits[key].add(archive.name)
                elif event == "item" and data.get("have"):
                    pickups[data["kind"]] += 1
                elif event == "heal":
                    heals += 1
        if not saw_item_trace or latest is None:
            continue
        artifacts += 1
        final_counters["opportunity_ticks"] += latest["item_opportunity_ticks"]
        final_counters["fetch_ticks"] += latest["item_fetch_ticks"]
        final_counters["yield_ticks"] += latest["item_yield_ticks"]

    contested = [
        (key, agents) for key, agents in pursuits.items() if len(agents) > 1
    ]
    contested_by_kind = Counter(
        key[2] for key, _agents in contested
    )
    return {
        "traced_agent_games": artifacts,
        "snapshots": snapshots,
        "cumulative": dict(final_counters),
        "choice_ticks_by_kind": dict(choices),
        "accepted_choice_ticks_by_kind": dict(accepted_choices),
        "choice_ticks_by_reason": dict(reasons),
        "pickups_by_kind": dict(pickups),
        "medkit_heals": heals,
        "contested_item_ticks": len(contested),
        "contested_item_ticks_by_kind": dict(contested_by_kind),
        "excess_pursuer_ticks": sum(
            len(agents) - 1 for _key, agents in contested
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.artifact_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
