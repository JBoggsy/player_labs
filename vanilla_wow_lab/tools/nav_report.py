#!/usr/bin/env python3
"""Score World Race episodes from their trace bundles — the nav-v2 verdict tool.

Reads nav_station / race_end / nav_state / route_planned events and prints the four
scores from the design doc:
- reachability : reachable stations arrived / reachable stations attempted
- honesty      : unreachable stations correctly failed-fast / unreachable attempted
- efficiency   : median station pace + planner-vs-walked overhead where present
- robustness   : stations that survived combat/death interruptions and still arrived

Usage: nav_report.py <episode_dir> [...] [--json]
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path


def load_trace(episode_dir: Path) -> list[dict] | None:
    bundle = episode_dir / "artifacts" / "policy_artifact_0.zip"
    if not bundle.is_file():
        return None
    with zipfile.ZipFile(bundle) as zf:
        try:
            raw = zf.read("trace.jsonl")
        except KeyError:
            return None
    return [json.loads(line) for line in io.BytesIO(raw).read().decode().splitlines() if line]


def score_episode(episode_dir: Path) -> dict | None:
    events = load_trace(episode_dir)
    if events is None:
        return None
    stations = [e for e in events if e.get("kind") == "nav_station"]
    if not stations:
        return None
    plans = [e for e in events if e.get("kind") == "route_planned"]
    end = next((e for e in events if e.get("kind") == "race_end"), {})
    return {
        "dir": episode_dir.name,
        "stations": [
            {k: s.get(k) for k in ("name", "region", "expected", "outcome", "seconds",
                                    "deaths", "combat_pauses", "replans")}
            for s in stations
        ],
        "plans": len(plans),
        "plan_statuses": sorted({p.get("status") for p in plans}),
        "summary": {k: end.get(k) for k in ("reached", "reachability", "coverage",
                                             "skipped", "honesty", "surprise_arrivals",
                                             "deaths", "combat_pauses", "replans")},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("episode_dirs", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    episodes = [row for d in args.episode_dirs if (row := score_episode(d)) is not None]
    if args.json:
        print(json.dumps(episodes, indent=1))
        return 0
    if not episodes:
        print("no world-race episodes found")
        return 1

    print(f"{'episode':<36} {'stations':>8} {'reach':>6} {'cover':>6} {'honest':>7} "
          f"{'deaths':>7} {'replans':>8}")
    for e in episodes:
        s = e["summary"]
        reach = s.get("reachability")
        cover = s.get("coverage")
        honest = s.get("honesty")
        print(
            f"{e['dir']:<36} {len(e['stations']):>8} "
            f"{('%.0f%%' % (reach * 100)) if reach is not None else '—':>6} "
            f"{('%.0f%%' % (cover * 100)) if cover is not None else '—':>6} "
            f"{('%.0f%%' % (honest * 100)) if honest is not None else '—':>7} "
            f"{s.get('deaths') or 0:>7} {s.get('replans') or 0:>8}"
        )
        if s.get("surprise_arrivals"):
            print(f"  ⚠ {s['surprise_arrivals']} adversarial station(s) unexpectedly ARRIVED")

    by_station: dict[str, dict] = defaultdict(lambda: {"attempts": 0, "arrived": 0,
                                                       "honest_fails": 0, "outcomes": []})
    for e in episodes:
        for s in e["stations"]:
            row = by_station[s["name"]]
            row["attempts"] += 1
            if s["outcome"] == "arrived":
                row["arrived"] += 1
            if s["expected"] == "unreachable" and s["outcome"] == "failed_unreachable":
                row["honest_fails"] += 1
            row["outcomes"].append(f"{s['outcome']}:{s['seconds']}s")

    print(f"\n{'station':<24} {'ok/att':>7}  outcomes")
    for name, row in sorted(by_station.items(), key=lambda kv: kv[1]["arrived"] - kv[1]["attempts"]):
        ok = row["arrived"] + row["honest_fails"]
        print(f"{name:<24} {ok}/{row['attempts']:<5}  {'; '.join(row['outcomes'][:4])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
