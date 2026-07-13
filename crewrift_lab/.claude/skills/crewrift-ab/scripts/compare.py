#!/usr/bin/env python3
"""Crewrift A/B adapter — the game-specific half of the `crewrift-ab` skill.

This is the crewrift *adapter* for the game-agnostic `coworld-ab` engine. It owns everything
crewrift-specific — how to read a crewrift results.json/episode.json, crewrift's metrics
(win/score/tasks/kills/penalty…), and the crew/imposter grouping — and delegates ALL statistics,
verdicts, and rendering to `ab_stats` (root skill `coworld-ab`). To A/B a different game, write a
sibling adapter with that game's Rec/METRICS/by_group; the engine is shared.

Diffs a BASELINE vs a CANDIDATE policy version on role-decomposed metrics, leads with a chosen
`--target` axis, and flags whether each delta is a real move or within noise (effect size +
significance). The qualitative half — reading logs/replays for the *why* — is the agent's job. See
SKILL.md.

CRITICAL — the two batches must be FRESH + MATCHED: both versions run in the same window against
the same roster/roles/count. The league field drifts, so only a same-window head-to-head makes the
delta attributable to *your* change — "better *now*," not "better than a stale baseline."
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

# Import the shared engine from the root `coworld-ab` skill. Repo root is parents[5]:
# scripts -> crewrift-ab -> skills -> .claude -> crewrift_lab -> <repo root>.
_REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(_REPO / ".claude" / "skills" / "coworld-ab" / "scripts"))
import ab_stats  # noqa: E402


# --- per-appearance record (compact; mirrors crewrift-survey's results.json model) ---

@dataclass
class Rec:
    role: str          # "crew" | "imposter"
    score: int
    tasks: int
    kills: int
    win: bool
    vote_timeout: int
    ops_fail: bool
    penalty: int
    game_tasks_done: int
    game_tasks_total: int


def parse_spec(spec: str) -> tuple[str, int | None]:
    """'crewborg:v15' -> ('crewborg', 15); 'crewborg' -> ('crewborg', None)."""
    if ":v" in spec:
        name, v = spec.split(":v", 1)
        return name, int(v)
    return spec, None


def slot_entries(episode: dict) -> list[tuple[int, str | None, int | None]]:
    """Normalize an episode's slot->policy map to ``(position, policy_name, version)``.

    The downloader writes the raw episode record in two shapes:
    - **league** episodes: ``policy_results[]`` = ``[{position, policy:{name,version}}]``
    - **experience-request** episodes: ``participants[]`` =
      ``[{position, policy_name, version}]``

    A/B comparison runs on matched experience requests, so the ``participants`` shape is
    the common case here — both must work.
    """
    out: list[tuple[int, str | None, int | None]] = []
    policy_results = episode.get("policy_results")
    if policy_results:
        for entry in policy_results:
            pol = entry.get("policy") or {}
            if entry.get("position") is not None:
                out.append((entry["position"], pol.get("name"), pol.get("version")))
        return out
    for entry in episode.get("participants") or []:
        if entry.get("position") is not None:
            out.append((entry["position"], entry.get("policy_name"), entry.get("version")))
    return out


def load_batch(root: Path, policy: str, version: int | None) -> list[Rec]:
    """Every appearance of (policy[:version]) across the episode dirs in `root`."""
    recs: list[Rec] = []
    for ep in sorted(p for p in root.iterdir() if p.is_dir()):
        ej, rj = ep / "episode.json", ep / "results.json"
        if not (ej.exists() and rj.exists()):
            continue
        try:
            episode, results = json.loads(ej.read_text()), json.loads(rj.read_text())
        except json.JSONDecodeError:
            continue
        slots = [pos for pos, name, ver in slot_entries(episode)
                 if name == policy and (version is None or ver == version)]
        for slot in slots:
            rec = _record(results, slot)
            if rec is not None:
                recs.append(rec)
    return recs


def _record(results: dict, slot: int) -> Rec | None:
    scores = results.get("scores") or []
    if slot is None or slot >= len(scores):
        return None
    def col(k):
        a = results.get(k) or []
        return a[slot] if slot < len(a) else 0
    crew_flags = results.get("crew") or []
    tasks_arr = results.get("tasks") or []
    win = bool(col("win"))
    tasks, kills, score = int(col("tasks")), int(col("kills")), int(col("scores"))
    crew_count = sum(1 for v in crew_flags if v)
    return Rec(
        role="imposter" if col("imposter") else "crew",
        score=score, tasks=tasks, kills=kills, win=win,
        vote_timeout=int(col("vote_timeout")),
        ops_fail=bool(col("connect_timeout") or col("disconnect_timeout")),
        penalty=int(100 * win + tasks + 10 * kills - score),
        game_tasks_done=sum(int(t) for t, c in zip(tasks_arr, crew_flags) if c),
        game_tasks_total=8 * crew_count,
    )


# --- metrics: (key, higher_is_better, kind, applies_to_group) ------------------------
# kind: "rate" (fraction of appearances) or "mean" (continuous average).

METRICS = [
    ("win_rate",                True,  "rate", None),
    ("score_mean",              True,  "mean", None),
    ("tasks_mean",              True,  "mean", "crew"),
    ("kills_mean",              True,  "mean", "imposter"),
    ("penalty_mean",            False, "mean", None),
    ("no_vote_rate",            False, "rate", None),
    ("ops_fail_rate",           False, "rate", None),
    ("imposter_no_kills_rate",  False, "rate", "imposter"),
    ("crew_low_tasks_rate",     False, "rate", "crew"),
    ("crew_lost_nearly_won_rate", False, "rate", "crew"),
]
GROUPS = ["crew", "imposter"]
LOW_TASKS_ABS = 4
NEARLY_WON_FRAC = 0.85


def metric_value(recs: list[Rec], key: str) -> tuple[float, int] | None:
    """Return (value, n) for a metric over a group's records, or None if N/A."""
    if not recs:
        return None
    n = len(recs)
    if key == "win_rate":
        return sum(r.win for r in recs) / n, n
    if key == "score_mean":
        return statistics.mean(r.score for r in recs), n
    if key == "tasks_mean":
        return statistics.mean(r.tasks for r in recs), n
    if key == "kills_mean":
        return statistics.mean(r.kills for r in recs), n
    if key == "penalty_mean":
        return statistics.mean(r.penalty for r in recs), n
    if key == "no_vote_rate":
        return sum(r.vote_timeout > 0 for r in recs) / n, n
    if key == "ops_fail_rate":
        return sum(r.ops_fail for r in recs) / n, n
    if key == "imposter_no_kills_rate":
        return sum(r.kills == 0 for r in recs) / n, n
    if key == "crew_low_tasks_rate":
        return sum(r.tasks <= LOW_TASKS_ABS for r in recs) / n, n
    if key == "crew_lost_nearly_won_rate":
        return sum((not r.win) and r.game_tasks_total
                   and r.game_tasks_done / r.game_tasks_total >= NEARLY_WON_FRAC
                   for r in recs) / n, n
    return None


def value_fn(recs: list[Rec], key: str) -> list[float]:
    """Per-appearance values for a metric (for the continuous significance test)."""
    if key == "score_mean":   return [float(r.score) for r in recs]
    if key == "tasks_mean":   return [float(r.tasks) for r in recs]
    if key == "kills_mean":   return [float(r.kills) for r in recs]
    if key == "penalty_mean": return [float(r.penalty) for r in recs]
    return []


def by_group(recs: list[Rec]) -> dict[str, list[Rec]]:
    out: dict[str, list[Rec]] = {"crew": [], "imposter": []}
    for r in recs:
        out[r.role].append(r)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("baseline_dir", help="Episodes dir for the BASELINE version (matched, fresh).")
    ap.add_argument("candidate_dir", help="Episodes dir for the CANDIDATE version (matched, fresh).")
    ap.add_argument("--baseline", required=True, help="Baseline policy as NAME or NAME:vN.")
    ap.add_argument("--candidate", required=True, help="Candidate policy as NAME or NAME:vN.")
    ap.add_argument("--target", help="Lead metric (e.g. win_rate, kills_mean, imposter_no_kills_rate).")
    ap.add_argument("--json", help="Also write the structured diff here.")
    args = ap.parse_args()

    bname, bver = parse_spec(args.baseline)
    cname, cver = parse_spec(args.candidate)
    base_recs = load_batch(Path(args.baseline_dir), bname, bver)
    cand_recs = load_batch(Path(args.candidate_dir), cname, cver)
    if not base_recs:
        raise SystemExit(f"no '{args.baseline}' appearances in {args.baseline_dir}")
    if not cand_recs:
        raise SystemExit(f"no '{args.candidate}' appearances in {args.candidate_dir}")

    base, cand = by_group(base_recs), by_group(cand_recs)
    deltas = ab_stats.build_deltas(base, cand, METRICS, metric_value, value_fn, GROUPS)
    print(ab_stats.render_markdown(args.baseline, args.candidate, base, cand,
                                   deltas, args.target, GROUPS, METRICS))

    if args.json:
        Path(args.json).write_text(json.dumps(
            ab_stats.emit_json(args.baseline, args.candidate, args.target, deltas), indent=2))
        print(f"\n[wrote JSON: {args.json}]")


if __name__ == "__main__":
    main()
