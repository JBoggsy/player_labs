"""Cross-policy imposter movement/search scoreboard.

For every imposter-game in one or more warehouses, computes per-game search metrics
(meeting-aware, Playing-only) and aggregates them per policy so "how does crewborg
hunt vs notsus/relhalpha" is one table.

Regimes per game:
  - COOLDOWN  alive, Playing, cd>0  — the approach phase (are we near crew *before* ready?)
  - READY     alive, Playing, cd==0 — split vis / novis (rendered-view crew visibility)

Usage (from this directory):
  uv run --with duckdb --with pandas --with numpy python compare_policies.py WH [WH2 ...] \
      [--min-games 3] [--csv out.csv] [--per-game out_games.csv]
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import movement_lib as ml

STATIONARY_SPEED = 0.3  # px/tick under which a tick counts as standing still
PURSUIT_CLOSING = 0.25  # px/tick of gap-shrink over which a tick counts as pursuing


def game_metrics(con, episode_id: str, slot: int, policy: str) -> dict | None:
    game = ml.build_imposter_game(con, episode_id, slot, policy)
    imp = game.imp
    win = ml.ready_windows(game)
    base = imp[imp.playing & imp.alive]
    if len(base) < 100:
        return None
    cool = base[base.cd > 0]
    ready = base[base.ready]
    novis = ready[~ready.crew_vis]
    my_kills = game.kills[game.kills.killer == slot]

    rooms = ml.room_transitions(con, episode_id, slot)
    revisits = sum(1 for i in range(2, len(rooms)) if rooms[i] == rooms[i - 2])

    def med(s):
        return float(s.median()) if len(s) else np.nan

    conv = win[win.outcome == "kill"]
    return dict(
        policy=policy,
        episode_id=episode_id,
        slot=slot,
        playing_ticks=len(base),
        kills=len(my_kills),
        first_kill_playing=int((base.ts <= my_kills.ts.min()).sum()) if len(my_kills) else np.nan,
        windows=len(win),
        win_conv_pct=100 * len(conv) / len(win) if len(win) else np.nan,
        med_window_len=med(win["len"]),
        med_ticks_to_kill=med(conv.ticks_to_kill),
        ready_ticks=len(ready),
        ready_vis_pct=100 * ready.crew_vis.mean() if len(ready) else np.nan,
        novis_near_crew=med(novis.near_crew),
        novis_closing=float(novis.closing.mean()) if len(novis) else np.nan,
        novis_pursuit_pct=100 * (novis.closing > PURSUIT_CLOSING).mean() if len(novis) else np.nan,
        novis_stationary_pct=100 * (novis.speed < STATIONARY_SPEED).mean() if len(novis) else np.nan,
        novis_same_room_pct=100 * (novis.crew_room_ct > 0).mean() if len(novis) else np.nan,
        novis_parked_pct=100 * novis.parked.mean() if len(novis) else np.nan,
        cool_vis_pct=100 * cool.crew_vis.mean() if len(cool) else np.nan,
        cool_near_crew=med(cool.near_crew),
        cool_same_room_pct=100 * (cool.crew_room_ct > 0).mean() if len(cool) else np.nan,
        room_moves_per_1k=1000 * len(rooms) / len(base),
        revisit_pct=100 * revisits / max(len(rooms) - 2, 1),
    )


def collect(warehouses: list[str]) -> pd.DataFrame:
    rows = []
    for wh in warehouses:
        con = ml.connect(wh)
        games = ml.imposter_games(con)
        for g in games.itertuples():
            m = game_metrics(con, g.episode_id, g.slot, g.policy_name)
            if m is not None:
                m["warehouse"] = wh
                rows.append(m)
    return pd.DataFrame(rows)


def aggregate(per_game: pd.DataFrame, min_games: int) -> pd.DataFrame:
    num_cols = [c for c in per_game.columns if c not in ("policy", "episode_id", "warehouse", "slot")]
    agg = per_game.groupby("policy")[num_cols].median()
    agg.insert(0, "games", per_game.groupby("policy").size())
    agg.insert(1, "kills_pg", per_game.groupby("policy").kills.mean().round(2))
    agg = agg[agg.games >= min_games]
    return agg.round(1).sort_values("kills_pg", ascending=False)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("warehouses", nargs="+")
    ap.add_argument("--min-games", type=int, default=3)
    ap.add_argument("--csv", help="write the per-policy table as CSV")
    ap.add_argument("--per-game", help="write the per-game table as CSV")
    args = ap.parse_args()

    per_game = collect(args.warehouses)
    if args.per_game:
        per_game.to_csv(args.per_game, index=False)
    agg = aggregate(per_game, args.min_games)
    pd.set_option("display.width", 250)
    print(agg.drop(columns=["kills"], errors="ignore").to_string())
    if args.csv:
        agg.to_csv(args.csv)


if __name__ == "__main__":
    main()
