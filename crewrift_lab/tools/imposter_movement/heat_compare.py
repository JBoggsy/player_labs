"""Occupancy heat comparison: where an imposter spends its BLIND ready time vs where
live crew actually are — "is it searching where crew ARE, or where they AREN'T?"

For each policy it accumulates two 2-D position histograms over all its imposter-games
(Playing ticks only):
  - imposter positions during ready+novis ticks (searching blind);
  - live-crew positions over the same ticks (the ground truth it should be sampling).
It renders the two heats side by side per policy and prints an **overlap scalar**
(Bhattacharyya coefficient between the normalized distributions; 1 = searching exactly
where crew are, 0 = disjoint).

Usage:
  uv run --with duckdb --with pandas --with numpy --with matplotlib python heat_compare.py \
      WH [WH2 ...] --policies crewborg-ghostnav notsus relhalpha -o /tmp/heat.png
"""

from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import movement_lib as ml

CELL = 32  # px per histogram cell


def accumulate(warehouses: list[str], policy_like: str):
    imp_h = crew_h = None
    extent = None
    game_map = None
    for wh in warehouses:
        con = ml.connect(wh)
        for g in ml.imposter_games(con, policy_like).itertuples():
            game = ml.build_imposter_game(con, g.episode_id, g.slot, g.policy_name, with_map=game_map is None)
            if game.game_map:
                game_map = game.game_map
            m = game_map or {}
            w, h = m.get("width", 1280), m.get("height", 800)
            if imp_h is None:
                nx, ny = w // CELL + 1, h // CELL + 1
                imp_h = np.zeros((ny, nx))
                crew_h = np.zeros((ny, nx))
                extent = (0, w, h, 0)
            imp = game.imp
            blind = imp[imp.ready & ~imp.crew_vis]
            np.add.at(imp_h, (blind.y // CELL, blind.x // CELL), 1)
            roles = ml.episode_players(con)
            ep_roles = roles[roles.episode_id == g.episode_id].set_index("slot")["role"]
            crew_slots = [s for s, r in ep_roles.items() if r == "crew"]
            st = game.states
            crew = st[st.slot.isin(crew_slots) & st.alive & st.ts.isin(blind.ts)]
            np.add.at(crew_h, (crew.y // CELL, crew.x // CELL), 1)
    return imp_h, crew_h, extent, game_map


def bhattacharyya(a: np.ndarray, b: np.ndarray) -> float:
    pa = a / a.sum() if a.sum() else a
    pb = b / b.sum() if b.sum() else b
    return float(np.sqrt(pa * pb).sum())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("warehouses", nargs="+")
    ap.add_argument("--policies", nargs="+", required=True, help="policy substrings, one row each")
    ap.add_argument("-o", "--out", default="/tmp/heat_compare.png")
    args = ap.parse_args()

    n = len(args.policies)
    fig, axes = plt.subplots(n, 2, figsize=(11, 3.6 * n), squeeze=False)
    for i, pol in enumerate(args.policies):
        imp_h, crew_h, extent, gmap = accumulate(args.warehouses, pol)
        if imp_h is None or imp_h.sum() == 0:
            axes[i][0].set_title(f"{pol}: no blind ready ticks found")
            continue
        ov = bhattacharyya(imp_h, crew_h)
        for ax, hist, label, cmap in (
            (axes[i][0], imp_h, "imposter (ready, blind)", "magma"),
            (axes[i][1], crew_h, "live crew (same ticks)", "viridis"),
        ):
            ax.imshow(np.sqrt(hist), extent=extent, cmap=cmap, interpolation="nearest")
            for r in (gmap or {}).get("rooms", []):
                ax.add_patch(plt.Rectangle((r["x"], r["y"]), r["w"], r["h"], fill=False, edgecolor="#ffffff40", lw=0.6))
                ax.text(r["x"] + 3, r["y"] + 12, r.get("name", ""), color="#ffffff80", fontsize=5)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f"{pol} — {label}", fontsize=8)
        axes[i][0].set_ylabel(f"overlap {ov:.2f}", fontsize=9)
        print(f"{pol}: blind ready ticks {int(imp_h.sum())}, crew-overlap (Bhattacharyya) {ov:.3f}")
    fig.tight_layout()
    fig.savefig(args.out, dpi=120, facecolor="white")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
