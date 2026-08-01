#!/usr/bin/env python3
"""Score waypoint-race episodes from their trace bundles.

Reads each episode dir's policy_artifact_0.zip → trace.jsonl, extracts race events
(race_start / race_leg / race_leg_skipped / race_lap / session_end), and prints a
per-episode and per-waypoint scoreboard: completion rate, laps, yards/second, and the
slowest/failing waypoints — the signal that drives the race-efficiency iteration loop.

Usage:
  race_report.py <episode_dir> [<episode_dir> ...] [--json]
  race_report.py vanilla_wow_lab/episode_data/20260721T2*  --json
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
    race = {
        "dir": episode_dir.name,
        "course": None,
        "legs": [],
        "skips": [],
        "laps": 0,
        "summary": None,
    }
    for e in events:
        kind = e.get("kind")
        if kind == "race_start":
            race["course"] = [c["name"] for c in e.get("course", [])]
        elif kind == "race_leg":
            race["legs"].append(
                {k: e.get(k) for k in ("name", "seconds", "yards", "attempts")}
            )
        elif kind == "race_leg_skipped":
            race["skips"].append({"name": e.get("name"), "attempts": e.get("attempts")})
        elif kind == "race_lap":
            race["laps"] = max(race["laps"], e.get("lap", 0))
        elif kind == "session_end":
            race["summary"] = e.get("summary")
    return race


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("episode_dirs", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    episodes = []
    for d in args.episode_dirs:
        row = score_episode(d)
        if row is not None and row["course"] is not None:
            episodes.append(row)
        elif row is not None:
            print(f"note: {d.name} has a trace but no race events (wrong policy?)", file=sys.stderr)

    if args.json:
        print(json.dumps(episodes, indent=1))
        return 0
    if not episodes:
        print("no race episodes found")
        return 1

    # per-episode scoreboard
    print(f"{'episode':<36} {'laps':>4} {'legs':>5} {'DNF':>4} {'cmpl%':>6} {'yd/s':>6}")
    for e in episodes:
        s = e["summary"] or {}
        rate = s.get("completion_rate")
        print(
            f"{e['dir']:<36} {e['laps']:>4} {len(e['legs']):>5} {len(e['skips']):>4} "
            f"{(rate * 100 if rate is not None else 0):>5.0f}% "
            f"{s.get('yards_per_second') or 0:>6}"
        )

    # per-waypoint difficulty
    by_wp: dict[str, dict] = defaultdict(lambda: {"completed": 0, "skipped": 0, "seconds": [], "yards": [], "attempts": []})
    for e in episodes:
        for leg in e["legs"]:
            wp = by_wp[leg["name"]]
            wp["completed"] += 1
            wp["seconds"].append(leg["seconds"])
            wp["yards"].append(leg["yards"])
            wp["attempts"].append(leg["attempts"])
        for skip in e["skips"]:
            by_wp[skip["name"]]["skipped"] += 1

    print(f"\n{'waypoint':<22} {'ok':>3} {'DNF':>4} {'med s':>6} {'med yd':>7} {'yd/s':>6} {'max att':>8}")
    for name, wp in sorted(by_wp.items(), key=lambda kv: -kv[1]["skipped"]):
        med_s = sorted(wp["seconds"])[len(wp["seconds"]) // 2] if wp["seconds"] else 0
        med_y = sorted(wp["yards"])[len(wp["yards"]) // 2] if wp["yards"] else 0
        rate = round(med_y / med_s, 2) if med_s else "-"
        print(
            f"{name:<22} {wp['completed']:>3} {wp['skipped']:>4} {med_s:>6} {med_y:>7} "
            f"{rate:>6} {max(wp['attempts'], default=0):>8}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
