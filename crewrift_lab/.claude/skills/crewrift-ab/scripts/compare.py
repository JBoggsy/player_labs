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
from collections import Counter
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
    penalty: int
    game_tasks_done: int
    game_tasks_total: int
    episode_id: str = ""


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


def load_batch(root: Path, policy: str, version: int | None) -> tuple[list[Rec], list[dict], dict]:
    """Read gameplay seats, independent episode failures, and explicit exclusions."""
    if version is None:
        raise ValueError("A/B requires an exact policy version: name:vN")
    recs, outcomes, excluded = [], [], Counter()
    seen = set()
    for ep in sorted(p for p in root.iterdir() if p.is_dir()):
        ej, rj = ep / "episode.json", ep / "results.json"
        if not ej.exists():
            excluded["missing_episode_metadata"] += 1
            continue
        try:
            episode = json.loads(ej.read_text())
            if not isinstance(episode, dict):
                raise ValueError("expected a JSON object")
        except ValueError as exc:
            raise ValueError(f"Invalid episode metadata in {ej}: {exc}") from exc
        eid = episode.get("id")
        if not eid or eid in seen:
            raise ValueError(f"Missing or duplicate episode ID in {ep}")
        seen.add(eid)
        slots = [pos for pos, name, ver in slot_entries(episode)
                 if name == policy and ver == version]
        if not slots:
            excluded["target_absent"] += 1
            continue
        try:
            results = json.loads(rj.read_text()) if rj.exists() else {}
        except ValueError:
            results = {}
        if not isinstance(results, dict):
            results = {}
        timeout_arrays = [results.get(key) for key in ("connect_timeout", "disconnect_timeout")]
        seat_count = max(pos for pos, _, _ in slot_entries(episode)) + 1
        has_ops_evidence = all(isinstance(values, list) and len(values) >= seat_count
                               for values in timeout_arrays)
        failed = bool(episode.get("status") in {"failed", "cancelled"}
                      or episode.get("error_type") or episode.get("failed_policy_index") is not None
                      or episode.get("failed_agent_index") is not None
                      or any(any(values) for values in timeout_arrays if isinstance(values, list)))
        # Missing results alone are not proof of a crash. Status/error metadata
        # still establish failures when no role or gameplay result was produced.
        known = failed or (has_ops_evidence and episode.get("status") in {"completed", None})
        if known:
            outcomes.append({"episode_id": eid, "ops_fail": failed})
        else:
            excluded["unknown_episode_outcome"] += 1
            continue
        if failed:
            excluded["failed_episode_gameplay"] += 1
            continue
        episode_records = [rec for slot in slots if (rec := _record(results, slot)) is not None]
        if len(episode_records) != len(slots):
            excluded["incomplete_target_seat_results"] += 1
            continue
        roles = [rec.role for rec in episode_records]
        if len(roles) != len(set(roles)):
            raise ValueError(f"{eid}: multiple target seats in one role; use an episode-aggregated analysis")
        for rec in episode_records:
            rec.episode_id = eid
        recs.extend(episode_records)
    return recs, outcomes, dict(excluded)


def _record(results: dict, slot: int) -> Rec | None:
    scores = results.get("scores") or []
    if slot is None or slot < 0 or slot >= len(scores):
        return None
    def col(k):
        a = results.get(k) or []
        return a[slot] if slot < len(a) else 0
    if any(slot >= len(results.get(key) or []) for key in ("win", "tasks", "kills")):
        return None
    if bool(col("imposter")) == bool(col("crew")):
        return None  # Unknown/contradictory role is not implicitly crew.
    crew_flags = results.get("crew") or []
    tasks_arr = results.get("tasks") or []
    win = bool(col("win"))
    tasks, kills, score = int(col("tasks")), int(col("kills")), int(col("scores"))
    crew_count = sum(1 for v in crew_flags if v)
    return Rec(
        role="imposter" if col("imposter") else "crew",
        score=score, tasks=tasks, kills=kills, win=win,
        vote_timeout=int(col("vote_timeout")),
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
    ("ops_fail_rate",           False, "rate", "episodes"),
    ("imposter_no_kills_rate",  False, "rate", "imposter"),
    ("crew_low_tasks_rate",     False, "rate", "crew"),
    ("crew_lost_nearly_won_rate", False, "rate", "crew"),
]
GROUPS = ["crew", "imposter"]
LOW_TASKS_ABS = 4
NEARLY_WON_FRAC = 0.85


def metric_value(recs: list[Rec], key: str) -> tuple[float, int] | None:
    """Return (value, n) for a metric over a group's records, or None if N/A."""
    if key == "ops_fail_rate":
        return (sum(r["ops_fail"] for r in recs) / len(recs), len(recs)) if recs else None
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
    if key == "ops_fail_rate":
        return []
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
    ap.add_argument("--baseline", required=True, help="Baseline policy as NAME:vN.")
    ap.add_argument("--candidate", required=True, help="Candidate policy as NAME:vN.")
    ap.add_argument("--target", help="Lead metric (e.g. win_rate, kills_mean, imposter_no_kills_rate).")
    ap.add_argument("--json", help="Also write the structured diff here.")
    args = ap.parse_args()

    bname, bver = parse_spec(args.baseline)
    cname, cver = parse_spec(args.candidate)
    if bver is None or cver is None:
        ap.error("Both policies require an exact version: name:vN")
    base_recs, base_ops, excluded_base = load_batch(Path(args.baseline_dir), bname, bver)
    cand_recs, cand_ops, excluded_cand = load_batch(Path(args.candidate_dir), cname, cver)
    if not base_ops:
        raise SystemExit(f"No known operational outcomes for {args.baseline}: {excluded_base}")
    if not cand_ops:
        raise SystemExit(f"No known operational outcomes for {args.candidate}: {excluded_cand}")

    if {r["episode_id"] for r in base_ops} & {r["episode_id"] for r in cand_ops}:
        ap.error("Arms share episodes; use a paired analysis for within-episode comparisons")
    base, cand = by_group(base_recs), by_group(cand_recs)
    base["episodes"], cand["episodes"] = base_ops, cand_ops
    print(f"Excluded baseline: {excluded_base}; candidate: {excluded_cand}")
    deltas = ab_stats.build_deltas(base, cand, METRICS, metric_value, value_fn, GROUPS)
    print(ab_stats.render_markdown(args.baseline, args.candidate, base, cand,
                                   deltas, args.target, GROUPS, METRICS))

    if args.json:
        report = ab_stats.emit_json(args.baseline, args.candidate, args.target, deltas)
        report.update(excluded_baseline=excluded_base, excluded_candidate=excluded_cand)
        Path(args.json).write_text(json.dumps(report, indent=2))
        print(f"\n[wrote JSON: {args.json}]")


if __name__ == "__main__":
    main()
