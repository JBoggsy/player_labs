"""Render imposter ready-windows as trajectory scenes (PNG) an agent can Read.

For each **ready window** (imposter alive+Playing+kill-ready; see movement_lib) it draws:
  - the map (rooms, tasks, vents) as underlay;
  - the imposter's path across the window, time-graded dark→bright;
  - each live crew's path across the same ticks (thin, with a dot at window END);
  - the kill (X) if the window converted, meeting/game-end otherwise;
  - a distance strip under the map: nearest-live-crew px vs tick-in-window, with
    rendered-view crew-visibility shaded, so "was anyone even nearby / on screen?"
    is answerable at a glance.

Modes:
  # the N longest victimless windows for a policy substring, one scene per cell
  uv run --with duckdb --with pandas --with numpy --with matplotlib python render_hunt.py \
      WH [WH2 ...] --policy crewborg --top 8 -o /tmp/crewborg_worst.png
  # a specific window
  ... --episode EREQ_ID --slot 3 --window 1 -o /tmp/scene.png
Sort order: --top picks by novis_ticks (blind search time) by default; --by len|ticks_to_kill.
"""

from __future__ import annotations

import argparse
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import cm

import movement_lib as ml

CREW_COLORS = ["#3a86d8", "#8a5cd8", "#2aa198", "#b58900", "#d33682", "#6c9a3f", "#c96b3c", "#5577aa"]


def draw_map(ax, m: dict) -> None:
    ax.set_facecolor("#101522")
    for r in m.get("rooms", []):
        ax.add_patch(plt.Rectangle((r["x"], r["y"]), r["w"], r["h"], fill=False, edgecolor="#8aa6cc55", lw=0.8))
        ax.text(r["x"] + 3, r["y"] + 12, r.get("name", ""), color="#aabbdd70", fontsize=6)
    for t in m.get("tasks", []):
        ax.add_patch(plt.Rectangle((t["x"] - 2, t["y"] - 2), 4, 4, color="#46d27866"))
    for v in m.get("vents", []):
        ax.add_patch(
            plt.Polygon(
                [(v["x"], v["y"] - 4), (v["x"] + 4, v["y"]), (v["x"], v["y"] + 4), (v["x"] - 4, v["y"])],
                color="#ff963c99",
            )
        )
    ax.set_xlim(0, m.get("width", 1200))
    ax.set_ylim(0, m.get("height", 800))
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")


def draw_window(ax_map, ax_strip, game: ml.ImposterGame, win_row, title_extra: str = "") -> None:
    imp, states = game.imp, game.states
    t0, t1 = int(win_row.t0), int(win_row.t1)
    draw_map(ax_map, game.game_map)

    # crew paths over the window (live crew only), dot at window end
    roles = states.groupby("slot").first()
    seg_states = states[(states.ts >= t0) & (states.ts <= t1) & states.alive]
    for i, (slot, sdf) in enumerate(seg_states.groupby("slot")):
        if slot == game.slot:
            continue
        col = CREW_COLORS[i % len(CREW_COLORS)]
        ax_map.plot(sdf.x, sdf.y, color=col, lw=0.9, alpha=0.55)
        ax_map.scatter([sdf.x.iloc[-1]], [sdf.y.iloc[-1]], s=26, color=col, zorder=4)

    # imposter path, time-graded
    seg = imp[(imp.ts >= t0) & (imp.ts <= t1)]
    n = len(seg)
    if n >= 2:
        colors = cm.plasma(np.linspace(0.15, 1.0, n - 1))
        for j in range(n - 1):
            ax_map.plot(seg.x.iloc[j : j + 2], seg.y.iloc[j : j + 2], color=colors[j], lw=2.4, zorder=5)
    ax_map.scatter([seg.x.iloc[0]], [seg.y.iloc[0]], marker="o", s=60, color="#ffd24a",
                   edgecolors="black", zorder=6, label="ready")
    ax_map.scatter([seg.x.iloc[-1]], [seg.y.iloc[-1]], marker="s", s=60, color="#ff5544",
                   edgecolors="black", zorder=6, label="end")
    if win_row.outcome == "kill" and win_row.kill_tick is not None and not pd.isna(win_row.kill_tick):
        ax_map.scatter([seg.x.iloc[-1]], [seg.y.iloc[-1]], marker="X", s=200, color="white",
                       edgecolors="black", linewidths=1.4, zorder=7)

    out = f"KILL +{int(win_row.ticks_to_kill)}t" if win_row.outcome == "kill" else win_row.outcome
    ax_map.set_title(
        f"{game.policy_name}  {game.episode_id[:13]} s{game.slot}  ready@{t0}  {int(win_row.len)}t "
        f"(novis {int(win_row.novis_ticks)}t) → {out} {title_extra}",
        color="#20293a", fontsize=7.5,
    )

    # strip: nearest-crew distance + visibility shading
    if ax_strip is not None:
        rel = seg.ts - t0
        ax_strip.plot(rel, seg.near_crew, color="#d33682", lw=1.2)
        ax_strip.fill_between(rel, 0, seg.near_crew.max() if seg.near_crew.notna().any() else 1,
                              where=seg.crew_vis, color="#46d278", alpha=0.25, linewidth=0)
        ax_strip.axhline(20, color="#ffd24a", lw=0.7, ls="--")  # kill range
        ax_strip.set_ylabel("near crew px", fontsize=6)
        ax_strip.tick_params(labelsize=6)
        ax_strip.set_xlim(0, max(int(win_row.len), 1))
        ax_strip.grid(alpha=0.2)


def find_windows(warehouses: list[str], policy_like: str, by: str) -> list[tuple]:
    """All ready windows for a policy substring across warehouses, sorted desc by `by`."""
    found = []
    for wh in warehouses:
        con = ml.connect(wh)
        for g in ml.imposter_games(con, policy_like).itertuples():
            game = ml.build_imposter_game(con, g.episode_id, g.slot, g.policy_name, with_map=True)
            win = ml.ready_windows(game)
            for row in win.itertuples():
                found.append((game, row))
    key = {"novis": "novis_ticks", "len": "len", "ticks_to_kill": "ticks_to_kill"}[by]
    found.sort(key=lambda p: (getattr(p[1], key) or 0), reverse=True)
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("warehouses", nargs="+")
    ap.add_argument("--policy", help="policy substring; picks windows across episodes")
    ap.add_argument("--top", type=int, default=6, help="how many windows to render (montage)")
    ap.add_argument("--by", default="novis", choices=["novis", "len", "ticks_to_kill"])
    ap.add_argument("--episode")
    ap.add_argument("--slot", type=int)
    ap.add_argument("--window", type=int, default=0)
    ap.add_argument("-o", "--out", default="/tmp/hunt_scenes.png")
    args = ap.parse_args()

    if args.episode is not None:
        con = ml.connect(args.warehouses[0])
        games = ml.imposter_games(con)
        row = games[(games.episode_id == args.episode) & (games.slot == args.slot)].iloc[0]
        game = ml.build_imposter_game(con, row.episode_id, int(row.slot), row.policy_name, with_map=True)
        win = ml.ready_windows(game)
        picks = [(game, list(win.itertuples())[args.window])]
    else:
        picks = find_windows(args.warehouses, args.policy, args.by)[: args.top]

    n = len(picks)
    cols = min(3, n) or 1
    rows = math.ceil(n / cols)
    fig = plt.figure(figsize=(cols * 5.2, rows * 4.6))
    gs = fig.add_gridspec(rows * 2, cols, height_ratios=[3.4, 1] * rows, hspace=0.32, wspace=0.12)
    for i, (game, wrow) in enumerate(picks):
        r, c = divmod(i, cols)
        ax_map = fig.add_subplot(gs[2 * r, c])
        ax_strip = fig.add_subplot(gs[2 * r + 1, c])
        draw_window(ax_map, ax_strip, game, wrow)
    fig.suptitle(
        f"{args.policy or picks[0][0].policy_name}: top-{n} ready windows by {args.by} "
        "(path dark→bright over time; green shade = crew in rendered view; dashed = kill range)",
        fontsize=9,
    )
    fig.savefig(args.out, dpi=115, facecolor="white", bbox_inches="tight")
    print(f"wrote {args.out} ({n} scenes)")


if __name__ == "__main__":
    main()
