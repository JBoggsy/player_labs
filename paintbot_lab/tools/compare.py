#!/usr/bin/env python3
"""Compare matched Paintbot batches with one independent observation per episode.

Select exact immutable policy
version IDs. Batches must match game/config, roster, seats and time window; this
reader does not establish experimental matching. Inspect traces before interpreting
why a delta occurred. Per-seat combat means describe only the selected policy.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from event_warehouse import _load_episode_meta

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / ".claude/skills/coworld-ab/scripts"))
import ab_stats

METRICS = [
    ("win_rate", True, "rate", None),
    ("score_mean", True, "mean", None),
    ("kills_per_seat", True, "mean", None),
    ("deaths_per_seat", False, "mean", None),
    ("captures_per_seat", True, "mean", None),
]


def load_batch(root: Path, version_id: str) -> tuple[dict, dict]:
    groups, excluded, seen = defaultdict(list), defaultdict(int), set()
    paths = [root / "episode.json"] if (root / "episode.json").exists() else sorted(root.rglob("episode.json"))
    for path in paths:
        meta = _load_episode_meta(path.parent)
        episode = json.loads(path.read_text())
        eid = meta["episode"]["episode_id"]
        if eid in seen:
            raise ValueError(f"duplicate episode: {eid}")
        seen.add(eid)
        selected = [row for row in meta["slots"] if row["policy_version_id"] == version_id]
        if not selected:
            excluded["target_absent"] += 1
            continue
        winner = meta["episode"]["winner"]
        if winner is None:
            excluded["incomplete_or_missing_outcome"] += 1
            continue
        colors = {row["team"] for row in selected}
        if len(colors) != 1 or None in colors:
            raise ValueError(f"{eid}: selected policy must occupy exactly one known team")
        team = next(iter(colors))
        row = {"episode_id": eid, "win_rate": float(winner == team)}
        for metric, source in [("score_mean", "score"), ("kills_per_seat", "kills"),
                               ("deaths_per_seat", "deaths"), ("captures_per_seat", "captures")]:
            values = [slot[source] for slot in selected]
            row[metric] = statistics.mean(values) if all(value is not None for value in values) else None
        # Each team result repeats across its seats; append exactly once per episode.
        group = f"{episode.get('coworld_version')} / {episode.get('variant_name')} / {team}"
        groups[group].append(row)
    return dict(groups), dict(excluded)


def value_fn(rows, key):
    return [row[key] for row in rows if row[key] is not None]


def metric_value(rows, key):
    values = value_fn(rows, key)
    return (statistics.mean(values), len(values)) if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_dir", type=Path)
    parser.add_argument("candidate_dir", type=Path)
    parser.add_argument("--baseline", required=True, help="Immutable policy_version_id")
    parser.add_argument("--candidate", required=True, help="Immutable policy_version_id")
    parser.add_argument("--target", choices=[metric[0] for metric in METRICS], default="win_rate")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    base, excluded_base = load_batch(args.baseline_dir, args.baseline)
    cand, excluded_cand = load_batch(args.candidate_dir, args.candidate)
    if not base or not cand:
        parser.error("both batches must contain completed episodes for the selected version")
    base_ids = {row["episode_id"] for rows in base.values() for row in rows}
    cand_ids = {row["episode_id"] for rows in cand.values() for row in rows}
    if base_ids & cand_ids:
        parser.error("arms share episodes; use a paired analysis for within-episode comparisons")
    groups = sorted(base.keys() | cand.keys())
    deltas = ab_stats.build_deltas(base, cand, METRICS, metric_value, value_fn, groups)
    print("Unit: episode; verify matched roster/config/time window separately.")
    print(f"Excluded baseline: {excluded_base}; candidate: {excluded_cand}")
    print(ab_stats.render_markdown(args.baseline, args.candidate, base, cand,
                                   deltas, args.target, groups, METRICS))
    if args.json:
        report = ab_stats.emit_json(args.baseline, args.candidate, args.target, deltas)
        report.update(unit="episode", excluded_baseline=excluded_base, excluded_candidate=excluded_cand)
        args.json.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
