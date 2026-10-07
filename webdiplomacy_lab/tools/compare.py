#!/usr/bin/env python3
"""webDiplomacy A/B adapter for the shared `coworld-ab` engine (crewrift's compare.py is the reference).

    uv run python webdiplomacy_lab/tools/compare.py BASE_DIR CAND_DIR \
        --baseline NAME:vN --candidate NAME:vM [--target score_mean] [--json out.json]

One observation = one target seat (one copy of our policy per episode, per the lab's
roster rule). Groups: `all` plus each power, because country is random per episode and
power strength dominates raw score. Both batches must be FRESH + MATCHED (same window,
same opponents, same variant); see the coworld-ab skill.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / ".claude" / "skills" / "coworld-ab" / "scripts"))
import ab_stats  # noqa: E402
from webdip_episodes import POWERS, load_dirs  # noqa: E402

METRICS = [
    ("score_mean", True, "mean", None),
    ("final_centers_mean", True, "mean", None),
    ("survival_rate", True, "rate", None),
    ("solo_rate", True, "rate", None),
    ("ops_fail_rate", False, "rate", "episodes"),
]
GROUPS = ["all", *POWERS.values()]


def load_batch(root: Path, policy: str):
    seats, statuses = load_dirs([root])
    recs = [s for s in seats if s.policy == policy and s.final_centers is not None]
    episodes = [
        {"episode_id": st["dir"], "ops_fail": st["episode_status"] in ("failed", "cancelled") or "results" in st["missing"]}
        for st in statuses
    ]
    return recs, episodes


def metric_value(recs, key):
    if not recs:
        return None
    n = len(recs)
    if key == "ops_fail_rate":
        return sum(r["ops_fail"] for r in recs) / n, n
    if key == "score_mean":
        return statistics.mean(r.score for r in recs), n
    if key == "final_centers_mean":
        return statistics.mean(r.final_centers for r in recs), n
    if key == "survival_rate":
        return sum(bool(r.survived) for r in recs) / n, n
    if key == "solo_rate":
        return sum(r.solo for r in recs) / n, n
    return None


def value_fn(recs, key):
    if key == "score_mean":
        return [r.score for r in recs]
    if key == "final_centers_mean":
        return [float(r.final_centers) for r in recs]
    return []


def by_group(recs):
    out = {g: [] for g in GROUPS}
    for r in recs:
        out["all"].append(r)
        out[r.power].append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("baseline_dir")
    ap.add_argument("candidate_dir")
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--target", default="score_mean")
    ap.add_argument("--json")
    args = ap.parse_args()
    base_recs, base_eps = load_batch(Path(args.baseline_dir), args.baseline)
    cand_recs, cand_eps = load_batch(Path(args.candidate_dir), args.candidate)
    if not base_recs or not cand_recs:
        raise SystemExit(f"no target seats: baseline {len(base_recs)}, candidate {len(cand_recs)}")
    base, cand = by_group(base_recs), by_group(cand_recs)
    base["episodes"], cand["episodes"] = base_eps, cand_eps
    deltas = ab_stats.build_deltas(base, cand, METRICS, metric_value, value_fn, GROUPS)
    print(ab_stats.render_markdown(args.baseline, args.candidate, base, cand, deltas, args.target, GROUPS, METRICS))
    if args.json:
        Path(args.json).write_text(json.dumps(ab_stats.emit_json(args.baseline, args.candidate, args.target, deltas), indent=2))


if __name__ == "__main__":
    main()
