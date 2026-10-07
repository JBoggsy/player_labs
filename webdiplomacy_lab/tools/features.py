"""webDiplomacy feature adapter for the shared `coworld-hypothesis-miner` engine.

Rows are `wd.py seats --policy NAME:vN` JSONL (one per own seat). Score is the episode
score (SC²-share or solo). Power strength is the largest confound in this game, so each
power is included as a presence feature: the miner reports it, and a hypothesis that is
really "we were Russia" shows up as such instead of hiding inside a behaviour feature.

    uv run python webdiplomacy_lab/tools/wd.py seats DIRS --policy NAME:vN > rows.jsonl
    uv run python .claude/skills/coworld-hypothesis-miner/scripts/mine_hypotheses.py \
        --rows rows.jsonl --adapter webdiplomacy_lab/tools/features.py
"""

from __future__ import annotations

from variance_miner import Episode, FeatureMeta

POWERS = ["England", "France", "Italy", "Germany", "Austria", "Turkey", "Russia"]


def _meta(name, kind, blurb, hint):
    return FeatureMeta(name=name, kind=kind, blurb=blurb, change_hint=hint)


METAS = {
    "centers_1902": _meta("centers_1902", "count", "supply centres owned after autumn 1902",
                          "raise early expansion value (neutral-centre attack weight)"),
    "centers_1904": _meta("centers_1904", "count", "supply centres owned after autumn 1904",
                          "review mid-opening target choice"),
    "lost_home_by_1904": _meta("lost_home_by_1904", "presence", "fewer centres in 1904 than in 1902",
                               "raise defence weight near threatened home centres"),
    "failed_order_rate": _meta("failed_order_rate", "count", "share of non-hold orders that failed adjudication",
                               "use supports/competition more before committing a move"),
    "dislodged": _meta("dislodged", "count", "own units dislodged over the game",
                       "support-hold units under 2+ unit competition"),
    "supports_per_decision": _meta("supports_per_decision", "count", "support orders per movement decision",
                                   "tune the support thresholds in DumbBot decode"),
    "holds_per_decision": _meta("holds_per_decision", "count", "hold orders per movement decision",
                                "convert idle holds into supports or moves"),
    **{
        f"power_{p}": _meta(f"power_{p}", "presence", f"we played {p}", "power strength confound, not a policy lever")
        for p in POWERS
    },
}


def adapter(row: dict) -> Episode | None:
    cby = {int(k): v for k, v in (row.get("centers_by_year") or {}).items()}
    if row.get("final_centers") is None or 1904 not in cby:
        return None
    log = row.get("log") or {}
    trace = log.get("trace") or {}
    decisions = max(log.get("decisions") or 0, 1)
    supports = trace.get("Support move", 0) + trace.get("Support hold", 0)
    features = {
        "centers_1902": float(cby.get(1902, 0)),
        "centers_1904": float(cby.get(1904, 0)),
        "lost_home_by_1904": float(cby.get(1904, 0) < cby.get(1902, 0)),
        "failed_order_rate": row["orders_failed"] / row["orders"] if row.get("orders") else 0.0,
        "dislodged": float(row.get("dislodged", 0)),
        "supports_per_decision": supports / decisions,
        "holds_per_decision": trace.get("Hold", 0) / decisions,
        **{f"power_{p}": float(row["power"] == p) for p in POWERS},
    }
    return Episode(episode_id=f'{row["episode_id"]}:{row["slot"]}', score=float(row["score"]), features=features)
