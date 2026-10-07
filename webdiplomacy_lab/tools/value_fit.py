#!/usr/bin/env python3
"""Fit the learned position evaluation (webdip_bot/valuefn.py) from local replays.

    uv run python webdiplomacy_lab/tools/value_fit.py [--horizon 2] [--write]

Rows: every power at every movement phase of every local replay. Target: that power's
supply-centre count `--horizon` years later (or at game end, whichever is first). Model:
ridge regression (numpy). Prints held-out R^2 against the "current SC count" baseline
(split by game). `--write` saves weights to webdip_bot/value_weights.json.
"""

import argparse
import glob
import json
import random
import sys
from pathlib import Path

import numpy as np

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from webdip_bot.valuefn import FEATURES, Graph, features  # noqa: E402


def rows_from(path, g_cache, horizon):
    frames = json.loads(Path(path).read_text())
    last = frames[-1]
    variant = last.get("variant")
    if not variant:
        return []
    key = variant["variantID"]
    if key not in g_cache:
        g_cache[key] = Graph(variant)
    g = g_cache[key]
    supply = set(g.supply)
    phases = [ph for ph in last["history"]["phases"] if ph["phase"] == "Diplomacy" and ph["units"]]
    # SC count per power by year (post-autumn ownership = next spring's centres).
    sc_by_turn = {}
    for ph in phases:
        counts = {}
        for c in ph["centers"]:
            if c["terrID"] in supply:
                counts[c["countryID"]] = counts.get(c["countryID"], 0) + 1
        sc_by_turn[ph["turn"]] = counts
    final_turn = max(sc_by_turn)
    rows = []
    for ph in phases:
        units = [(u["countryID"], g.parent[u["terrID"]], u["type"], u["terrID"]) for u in ph["units"] if not u.get("retreating")]
        owner = {p: None for p in supply}
        for c in ph["centers"]:
            if c["terrID"] in supply:
                owner[c["terrID"]] = c["countryID"]
        target_turn = min(ph["turn"] + 2 * horizon + (1 if ph["turn"] % 2 else 0), final_turn)
        target_turn = target_turn - (target_turn % 2)  # spring entries hold post-autumn ownership
        target = sc_by_turn.get(target_turn) or sc_by_turn[final_turn]
        for power in range(1, 8):
            f = features(g, units, owner, power)
            if f[1] == 0 and f[2] == 0:
                continue
            rows.append((path, f, target.get(power, 0)))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--horizon", type=int, default=2)
    ap.add_argument("--ridge", type=float, default=1.0)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    g_cache = {}
    rows = []
    for path in sorted(glob.glob(str(LAB / "local_runs" / "*" / "*" / "replay"))):
        try:
            rows.extend(rows_from(path, g_cache, args.horizon))
        except (ValueError, KeyError):
            continue
    games = sorted({r[0] for r in rows})
    random.Random(0).shuffle(games)
    test_games = set(games[: len(games) // 5])
    X = np.array([r[1] for r in rows], dtype=float)
    y = np.array([r[2] for r in rows], dtype=float)
    test = np.array([r[0] in test_games for r in rows])

    def fit(Xtr, ytr):
        reg = args.ridge * np.eye(Xtr.shape[1])
        reg[0, 0] = 0
        return np.linalg.solve(Xtr.T @ Xtr + reg, Xtr.T @ ytr)

    w = fit(X[~test], y[~test])
    pred = X[test] @ w
    ss_tot = ((y[test] - y[test].mean()) ** 2).sum()
    r2 = 1 - ((y[test] - pred) ** 2).sum() / ss_tot
    base = X[test][:, 1]
    r2_base = 1 - ((y[test] - base) ** 2).sum() / ss_tot
    report = {"rows": len(rows), "games": len(games), "horizon_years": args.horizon,
              "r2_heldout": round(float(r2), 4), "r2_current_sc_baseline": round(float(r2_base), 4),
              "weights": {f: round(float(v), 4) for f, v in zip(FEATURES, fit(X, y))}}
    print(json.dumps(report, indent=1))
    if args.write:
        w_all = fit(X, y)
        out = LAB / "webdip_bot" / "value_weights.json"
        out.write_text(json.dumps({"features": FEATURES, "weights": [float(v) for v in w_all],
                                   "r2_heldout": report["r2_heldout"], "rows": len(rows),
                                   "horizon_years": args.horizon}, indent=1))
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
