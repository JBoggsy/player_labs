#!/usr/bin/env python3
"""Gods of the Arena A/B adapter for the shared `coworld-ab` engine.

Diffs a BASELINE and a CANDIDATE policy version across two matched, fresh, same-window
experience requests and delegates statistics, verdicts, and rendering to `ab_stats`.

Unit and grouping. The class per seat is fixed (seat 0 is always the Death Knight, seat
5 always the Vanguard Knight), and one policy usually holds several seats in one episode.
The unit is therefore one observation per EPISODE per GROUP: seats of the same group in
one episode are averaged before any test, so a game is never counted twice in a group.
`--group` picks the split: `class` (ten groups, the honest split, needs large batches),
`role` (the five farm-priority tiers of docs/roles.md), `team` (red/blue), or `all`
(one group, the coarse "did it move overall" view). Under the coarser splits a rate
metric becomes the within-episode fraction of the policy's seats and is tested as a mean.

Sources. `win` and `total_xp` come from results.json for every seat. `level` comes from
the game log's `heroes:` line for every seat. Last hits, hero kills, tower kills and
deaths come from the policy's own `LH` telemetry and exist only for seats that print it
(see policy/README.md); a version without telemetry reports those metrics as n/a.

Caveat on win rate. When the policy sits on both teams of one episode (the usual
experience-request fill), the seat's team win is partly decided by its own copies on
the other side. Read `xp_mean` and the farm metrics as the per-seat signal; treat
`win_rate` as a team outcome.

Usage:
  uv run python gods_of_the_arena_lab/tools/compare.py BASE_DIR CAND_DIR \
      --baseline james-botts-gota:v1 --candidate james-botts-gota:v2 \
      --target last_hits_per_1k_ticks [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gota_episodes import (CLASS_NAMES, ROLE_NAMES, ROLE_OF_CLASS, EpisodeRecord, Seat,  # noqa: E402
                           load_batch, own_seats, parse_spec)

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / ".claude" / "skills" / "coworld-ab" / "scripts"))
import ab_stats  # noqa: E402

# (key, higher_is_better, kind, applies_to_group). Class-grouped metrics have group None.
METRICS = [
    ("win_rate", True, "rate", None),
    ("xp_mean", True, "mean", None),
    ("xp_per_1k_ticks", True, "mean", None),
    ("level_mean", True, "mean", None),
    ("last_hits_mean", True, "mean", None),
    ("last_hits_per_1k_ticks", True, "mean", None),
    ("no_last_hit_rate", False, "rate", None),
    ("hero_kills_mean", True, "mean", None),
    ("tower_kills_mean", True, "mean", None),
    ("deaths_mean", False, "mean", None),
    ("vm_error_rate", False, "rate", None),
    ("ops_fail_rate", False, "rate", "episodes"),
    ("draw_rate", False, "rate", "episodes"),
    # Game length: for a policy that loses quickly, a longer game means its team held
    # out longer. Reread this direction once the policy is winning games.
    ("ticks_mean", True, "mean", "episodes"),
]
def metrics_for(grouping: str) -> list[tuple]:
    """Seat-level rates stay Fisher-tested rates only when each episode contributes one seat
    per group (`class`); averaged over several seats they are fractions, tested as means."""
    if grouping == "class":
        return METRICS
    return [(key, hib, "mean" if kind == "rate" and group is None else kind, group)
            for key, hib, kind, group in METRICS]


GROUPINGS = {
    "class": (CLASS_NAMES, lambda seat: seat.hero_class),
    "role": (ROLE_NAMES, lambda seat: ROLE_OF_CLASS[seat.hero_class]),
    "team": (["red", "blue"], lambda seat: seat.team),
    "all": (["all"], lambda seat: "all"),
}


def _per_1k(value: int | None, ticks: int | None) -> float | None:
    if value is None or not ticks:
        return None
    return 1000.0 * value / ticks


def seat_value(seat: Seat, ticks: int | None, key: str) -> float | None:
    """One seat's value for a metric, or None when the source is missing."""
    telemetry = seat.telemetry
    if key == "win_rate":
        return float(seat.won)
    if key == "xp_mean":
        return None if seat.total_xp is None else float(seat.total_xp)
    if key == "xp_per_1k_ticks":
        return _per_1k(seat.total_xp, ticks)
    if key == "level_mean":
        return None if seat.level is None else float(seat.level)
    if key == "vm_error_rate":
        return None if seat.vm_error is None else float(seat.vm_error)
    if telemetry is None:
        return None
    if key == "last_hits_mean":
        return float(telemetry.last_hits)
    if key == "last_hits_per_1k_ticks":
        return _per_1k(telemetry.last_hits, ticks)
    if key == "no_last_hit_rate":
        return float(telemetry.last_hits == 0)
    if key == "hero_kills_mean":
        return float(telemetry.hero_kills)
    if key == "tower_kills_mean":
        return float(telemetry.tower_kills)
    if key == "deaths_mean":
        return float(telemetry.deaths)
    return None


def load_arm(root: Path, policy: str, version: int, grouping: str) -> tuple[dict[str, list], dict]:
    """Group one arm's seats; each group row is (seats of one episode, episode record).
    Episode-level rows go under "episodes"."""
    group_names, key_of = GROUPINGS[grouping]
    records, excluded = load_batch(root)
    groups: dict[str, list] = {name: [] for name in group_names}
    groups["episodes"] = []
    for record in records:
        seats = own_seats(record, policy, version)
        if not seats:
            excluded["target_absent"] += 1
            continue
        if not record.known:
            excluded["unknown_episode_outcome"] += 1
            continue
        groups["episodes"].append({"episode_id": record.episode_id, "ops_fail": record.ops_fail,
                                   "draw": record.draw, "ticks": record.ticks})
        if record.ops_fail:
            excluded["failed_episode_gameplay"] += 1
            continue
        per_group: dict[str, list[Seat]] = {}
        for seat in seats:
            per_group.setdefault(key_of(seat), []).append(seat)
        for name, group_seats in per_group.items():
            groups[name].append((group_seats, record))
    return groups, dict(excluded)


def value_fn(rows: list, key: str) -> list[float]:
    if key in {"ops_fail_rate", "draw_rate"}:
        return []
    if key == "ticks_mean":
        return [float(r["ticks"]) for r in rows if r.get("ticks")]
    out: list[float] = []
    for seats, record in rows:
        values = [v for v in (seat_value(seat, record.ticks, key) for seat in seats) if v is not None]
        if values:
            out.append(statistics.mean(values))
    return out


def metric_value(rows: list, key: str) -> tuple[float, int] | None:
    if not rows:
        return None
    if key == "ops_fail_rate":
        return sum(r["ops_fail"] for r in rows) / len(rows), len(rows)
    if key == "draw_rate":
        return sum(r["draw"] for r in rows) / len(rows), len(rows)
    values = value_fn(rows, key)
    return (statistics.mean(values), len(values)) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("baseline_dir", type=Path, help="Downloaded episodes of the baseline arm.")
    parser.add_argument("candidate_dir", type=Path, help="Downloaded episodes of the candidate arm.")
    parser.add_argument("--baseline", required=True, help="Baseline policy as NAME:vN.")
    parser.add_argument("--candidate", required=True, help="Candidate policy as NAME:vN.")
    parser.add_argument("--target", choices=[m[0] for m in METRICS], default="xp_mean",
                        help="Lead metric: the axis the change was meant to move.")
    parser.add_argument("--group", choices=list(GROUPINGS), default="class",
                        help="How to split the policy's seats (see the module docstring).")
    parser.add_argument("--json", type=Path, help="Also write the structured diff here.")
    args = parser.parse_args()

    base_name, base_version = parse_spec(args.baseline)
    cand_name, cand_version = parse_spec(args.candidate)
    if base_version is None or cand_version is None:
        parser.error("both policies need an exact version: name:vN")
    base, excluded_base = load_arm(args.baseline_dir, base_name, base_version, args.group)
    cand, excluded_cand = load_arm(args.candidate_dir, cand_name, cand_version, args.group)
    if not base["episodes"] or not cand["episodes"]:
        parser.error(f"no known episodes for an arm; baseline {excluded_base}, candidate {excluded_cand}")
    base_ids = {r["episode_id"] for r in base["episodes"]}
    cand_ids = {r["episode_id"] for r in cand["episodes"]}
    if base_ids & cand_ids:
        parser.error("arms share episodes; use a paired analysis for within-episode comparisons")

    groups = [g for g in GROUPINGS[args.group][0] if base[g] or cand[g]]
    metrics = metrics_for(args.group)
    deltas = ab_stats.build_deltas(base, cand, metrics, metric_value, value_fn, groups)
    print(f"Unit: one observation per episode per {args.group} group (seats averaged within an episode); "
          "verify matched roster, roles, and window separately.")
    print(f"Excluded baseline: {excluded_base}; candidate: {excluded_cand}")
    print(ab_stats.render_markdown(args.baseline, args.candidate, base, cand,
                                   deltas, args.target, groups, metrics))
    if args.json:
        report = ab_stats.emit_json(args.baseline, args.candidate, args.target, deltas)
        report.update(unit=f"episode per {args.group} group",
                      excluded_baseline=excluded_base, excluded_candidate=excluded_cand)
        args.json.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\n[wrote JSON: {args.json}]")


if __name__ == "__main__":
    main()
