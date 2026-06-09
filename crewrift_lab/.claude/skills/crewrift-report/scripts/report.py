#!/usr/bin/env python3
"""Tier-1 structured report over a set of Crewrift episodes.

Reads downloaded episode artifacts (``episode.json`` + ``results.json`` per episode
directory), locates the target policy's slot(s), and produces a role-decomposed
report that flags "interesting" episodes — score outliers, role-objective failures,
voting pathologies, and operational failures. This is the cheap, deterministic core
of the loop's Report step: it needs no replay parsing (that's Tier 2 /
``profile_replay.py``).

Input is a directory of episodes as written by the ``coworld-episode-artifacts``
downloader (one subdir per episode). See the skill's SKILL.md for the full workflow.

Scoring model (Crewrift, from the game sim): a slot's score =
``100*win + 1*tasks + 10*kills - penalties`` (penalties: -10 per missed vote, -1 per
idle-with-tasks interval). So ``penalty_points = 100*win + tasks + 10*kills - score``
is the points bled to penalties — a derived behavioral signal. results.json gives the
totals; profile_replay.py itemizes the penalties from the replay.
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass, field, asdict
from pathlib import Path


# --- data model -------------------------------------------------------------------

@dataclass
class Record:
    """One (episode, slot) appearance of the target policy."""
    episode_dir: str
    episode_id: str
    slot: int
    name: str
    version: int | None
    role: str                  # "imposter" | "crew"
    score: int
    tasks: int
    kills: int
    win: bool
    vote_players: int
    vote_skip: int
    vote_timeout: int
    connect_timeout: int
    disconnect_timeout: int
    penalty_points: int        # derived: points lost to penalties (idle + missed votes)
    opponents: list[str]       # other slots' policy names
    game_tasks_done: int       # tasks completed across all crew slots
    game_tasks_total: int      # 8 * crew_count
    game_won_by: str           # "crew" | "imposter" | "unknown"
    flags: list[str] = field(default_factory=list)


# --- loading ----------------------------------------------------------------------

def load_episode(ep_dir: Path) -> tuple[dict, dict] | None:
    """Return (episode_json, results_json) for an episode dir, or None if incomplete."""
    ej, rj = ep_dir / "episode.json", ep_dir / "results.json"
    if not (ej.exists() and rj.exists()):
        return None
    try:
        return json.loads(ej.read_text()), json.loads(rj.read_text())
    except json.JSONDecodeError:
        return None


def slots_for_policy(episode: dict, policy: str, version: int | None) -> list[tuple[int, str | None]]:
    """Slots (position, version) where the target policy plays in this episode."""
    out = []
    for entry in episode.get("policy_results") or []:
        pol = entry.get("policy") or {}
        name = pol.get("name")
        ver = pol.get("version")
        if name == policy and (version is None or ver == version):
            pos = entry.get("position")
            if pos is not None:
                out.append((pos, ver))
    return out


def opponents_for(episode: dict, slot: int) -> list[str]:
    names = []
    for entry in episode.get("policy_results") or []:
        if entry.get("position") != slot:
            pol = entry.get("policy") or {}
            if pol.get("name"):
                names.append(pol["name"])
    return names


def build_record(ep_dir: Path, episode: dict, results: dict, slot: int, version: int | None) -> Record | None:
    """Extract the target policy's per-episode record from the results arrays."""
    def col(key: str, default=0):
        arr = results.get(key) or []
        return arr[slot] if slot < len(arr) else default

    n = len(results.get("scores") or [])
    if slot >= n:
        return None

    crew_flags = results.get("crew") or []
    imp_flags = results.get("imposter") or []
    tasks_arr = results.get("tasks") or []
    win_arr = results.get("win") or []

    role = "imposter" if col("imposter") else "crew"
    score = int(col("scores"))
    tasks = int(col("tasks"))
    kills = int(col("kills"))
    win = bool(col("win"))
    penalty = int(100 * win + tasks + 10 * kills - score)

    crew_count = sum(1 for v in crew_flags if v)
    game_tasks_done = sum(int(t) for t, c in zip(tasks_arr, crew_flags) if c)
    # Winner side: any crew slot with win -> crew won; any imposter slot with win -> imposters.
    won_by = "unknown"
    for j, w in enumerate(win_arr):
        if w:
            won_by = "imposter" if (j < len(imp_flags) and imp_flags[j]) else "crew"
            break

    return Record(
        episode_dir=ep_dir.name,
        episode_id=str(episode.get("id", "")),
        slot=slot,
        name=str(col("names", "")),
        version=version,
        role=role,
        score=score,
        tasks=tasks,
        kills=kills,
        win=win,
        vote_players=int(col("vote_players")),
        vote_skip=int(col("vote_skip")),
        vote_timeout=int(col("vote_timeout")),
        connect_timeout=int(col("connect_timeout")),
        disconnect_timeout=int(col("disconnect_timeout")),
        penalty_points=penalty,
        opponents=opponents_for(episode, slot),
        game_tasks_done=game_tasks_done,
        game_tasks_total=8 * crew_count,
        game_won_by=won_by,
    )


# --- statistics -------------------------------------------------------------------

def robust_z(x: float, values: list[float]) -> float:
    """Median/MAD-based z-score (0 if no spread). Robust to outliers + small n."""
    if len(values) < 3:
        return 0.0
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values])
    if mad == 0:
        return 0.0
    return 0.6745 * (x - med) / mad


def dist_summary(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 2),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "std": round(statistics.pstdev(values), 2) if len(values) > 1 else 0.0,
    }


# --- flagging ---------------------------------------------------------------------

# Robust-z threshold for score outliers, and the "nearly won" task-fraction cutoff.
Z_OUTLIER = 2.0
NEARLY_WON_FRAC = 0.85
LOW_TASKS_ABS = 4   # crewmate task count at/below this is "low" (of 8)


def flag_records(records: list[Record]) -> dict[str, list[Record]]:
    """Attach .flags to each record and return a category -> [records] index."""
    cats: dict[str, list[Record]] = {}

    def add(cat: str, rec: Record):
        rec.flags.append(cat)
        cats.setdefault(cat, []).append(rec)

    by_role = {"crew": [], "imposter": []}
    for r in records:
        by_role[r.role].append(r)

    for role, recs in by_role.items():
        scores = [r.score for r in recs]
        for r in recs:
            z = robust_z(r.score, scores)
            if z <= -Z_OUTLIER:
                add("score_low", r)
            elif z >= Z_OUTLIER:
                add("score_high", r)

    for r in records:
        # Operational failures — kept strictly separate from behavior.
        if r.connect_timeout or r.disconnect_timeout:
            add("operational_failure", r)
        # Voting: the hard -10 for not voting.
        if r.vote_timeout:
            add("no_vote_penalty", r)
        # Points bled to penalties beyond missed votes (idle-with-tasks, etc.).
        if r.penalty_points - 10 * r.vote_timeout >= 2:
            add("penalty_leak", r)

        if r.role == "imposter":
            if r.kills == 0:
                add("imposter_no_kills", r)
            if not r.win:
                add("imposter_lost", r)
            if r.win and r.kills == 0:
                add("imposter_won_no_kills", r)   # interesting positive: won by vote play
        else:  # crew
            if r.tasks <= LOW_TASKS_ABS:
                add("crew_low_tasks", r)
            if (not r.win and r.game_tasks_total
                    and r.game_tasks_done / r.game_tasks_total >= NEARLY_WON_FRAC):
                add("crew_lost_nearly_won", r)   # the "should've been a win" game

    return cats


# --- rendering --------------------------------------------------------------------

CATEGORY_BLURB = {
    "score_low": "Scored far below this role's norm (robust z ≤ -2) — what went wrong?",
    "score_high": "Scored far above the norm — a positive exemplar to learn from.",
    "crew_lost_nearly_won": "Crew loss with tasks ≈ complete — the most informative failures.",
    "imposter_no_kills": "Imposter with 0 kills — failed the core objective.",
    "imposter_lost": "Imposter that lost the game.",
    "imposter_won_no_kills": "Imposter won WITHOUT killing (vote manipulation) — study it.",
    "crew_low_tasks": f"Crewmate completed ≤{LOW_TASKS_ABS}/8 tasks — low contribution.",
    "no_vote_penalty": "Missed a vote (−10 each) — never abstain; skip is free.",
    "penalty_leak": "Bled points to penalties (idle-with-tasks, etc.) beyond missed votes.",
    "operational_failure": "Connect/disconnect timeout (−100) — an OPS failure, not strategy.",
}

# Order categories from most-actionable to least for the report.
CATEGORY_ORDER = [
    "crew_lost_nearly_won", "score_low", "imposter_no_kills", "imposter_lost",
    "no_vote_penalty", "penalty_leak", "crew_low_tasks", "operational_failure",
    "imposter_won_no_kills", "score_high",
]


def fmt_record_line(r: Record) -> str:
    bits = [f"score={r.score}", f"tasks={r.tasks}"]
    if r.role == "imposter":
        bits.append(f"kills={r.kills}")
    bits.append("WIN" if r.win else "loss")
    if r.vote_timeout:
        bits.append(f"missed_votes={r.vote_timeout}")
    if r.penalty_points:
        bits.append(f"penalty_pts={r.penalty_points}")
    return f"  - `{r.episode_dir}` [{r.role}] " + " ".join(bits)


def render_markdown(policy: str, version: int | None, records: list[Record],
                    cats: dict[str, list[Record]], top: int, n_episodes: int) -> str:
    lines: list[str] = []
    vlabel = f":v{version}" if version is not None else ""
    lines.append(f"# Crewrift report — `{policy}{vlabel}`")
    lines.append("")
    lines.append(f"{len(records)} appearances across {n_episodes} episodes "
                 f"({sum(r.role=='crew' for r in records)} crew, "
                 f"{sum(r.role=='imposter' for r in records)} imposter).")
    if len(records) < 20:
        lines.append("")
        lines.append("> ⚠ Small sample — treat distributions and outliers as directional, "
                     "not conclusive. Pull more episodes for firm claims.")
    lines.append("")

    # Role-decomposed distribution (mandatory split: the two roles are different policies).
    lines.append("## Distribution by role")
    lines.append("")
    lines.append("| role | n | win% | score med (mean) | score min/max | tasks med | kills med |")
    lines.append("| --- | ---: | ---: | --- | --- | ---: | ---: |")
    for role in ("crew", "imposter"):
        recs = [r for r in records if r.role == role]
        if not recs:
            continue
        sc = dist_summary([r.score for r in recs])
        winp = round(100 * sum(r.win for r in recs) / len(recs))
        tmed = statistics.median([r.tasks for r in recs])
        kmed = statistics.median([r.kills for r in recs])
        lines.append(f"| {role} | {sc['n']} | {winp}% | {sc['median']} ({sc['mean']}) "
                     f"| {sc['min']}/{sc['max']} | {tmed} | {kmed} |")
    lines.append("")

    # Interesting episodes, by category.
    lines.append("## Interesting episodes")
    lines.append("")
    any_cat = False
    for cat in CATEGORY_ORDER:
        recs = cats.get(cat)
        if not recs:
            continue
        any_cat = True
        # Rank: low score ascending; high score descending; else by penalty/severity.
        if cat == "score_high" or cat == "imposter_won_no_kills":
            recs = sorted(recs, key=lambda r: -r.score)
        else:
            recs = sorted(recs, key=lambda r: r.score)
        shown = recs[:top]
        lines.append(f"### {cat}  ({len(recs)})")
        lines.append(f"_{CATEGORY_BLURB.get(cat, '')}_")
        for r in shown:
            lines.append(fmt_record_line(r))
        if len(recs) > top:
            lines.append(f"  - … and {len(recs) - top} more")
        lines.append("")
    if not any_cat:
        lines.append("_No flagged episodes — the policy played within its norms across the batch._")
        lines.append("")

    # Drill-in pointer.
    lines.append("## Next: drill into flagged episodes")
    lines.append("")
    lines.append("For any `episode_dir` above, get the objective event timeline (killed-vs-ejected, "
                 "vote correctness, score breakdown, unusual-event profile):")
    lines.append("")
    lines.append("```sh")
    lines.append("scripts/profile_replay.py <episodes_dir>/<episode_dir> --policy " + policy + vlabel)
    lines.append("```")
    lines.append("")
    lines.append("Then read the policy's own logs at the tick of interest for the *why* "
                 "(crewborg: `crewrift/crewborg/docs/trace-logs.md`).")
    return "\n".join(lines)


# --- main -------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episodes_dir", help="Directory of downloaded episodes (one subdir each).")
    ap.add_argument("--policy", required=True, help="Target policy name (e.g. crewborg).")
    ap.add_argument("--version", type=int, default=None, help="Restrict to this policy version.")
    ap.add_argument("--top", type=int, default=6, help="Episodes listed per category (default 6).")
    ap.add_argument("--json", help="Also write the full machine-readable report here.")
    args = ap.parse_args()

    root = Path(args.episodes_dir)
    if not root.is_dir():
        ap.error(f"not a directory: {root}")

    records: list[Record] = []
    n_episodes = 0
    skipped = 0
    for ep_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        loaded = load_episode(ep_dir)
        if loaded is None:
            continue
        episode, results = loaded
        slots = slots_for_policy(episode, args.policy, args.version)
        if not slots:
            continue
        n_episodes += 1
        for slot, ver in slots:
            rec = build_record(ep_dir, episode, results, slot, ver)
            if rec is not None:
                records.append(rec)
            else:
                skipped += 1

    if not records:
        raise SystemExit(
            f"No episodes with policy '{args.policy}'"
            + (f":v{args.version}" if args.version is not None else "")
            + f" found under {root}. (Did the downloader write episode.json + results.json?)")

    cats = flag_records(records)
    report = render_markdown(args.policy, args.version, records, cats, args.top, n_episodes)
    print(report)

    if args.json:
        payload = {
            "policy": args.policy,
            "version": args.version,
            "n_episodes": n_episodes,
            "records": [asdict(r) for r in records],
            "categories": {c: [r.episode_dir for r in rs] for c, rs in cats.items()},
        }
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\n[wrote JSON: {args.json}]")


if __name__ == "__main__":
    main()
