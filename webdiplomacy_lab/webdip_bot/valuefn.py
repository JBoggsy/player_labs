"""Learned position evaluation: features of a power's position -> predicted future centres.

`features(graph, units, owner, power)` is pure Python over webDip variant data (no
players/diplomacy imports) so the same code builds the training set offline
(`tools/value_fit.py`) and evaluates positions inside the search. Weights live in
`value_weights.json` next to this file (written by value_fit.py).

Position: `units` = list of (countryID, province, unit_type, terrID); `owner` = {SC
province: countryID or None}.
"""

import json
from pathlib import Path

FEATURES = [
    "bias", "sc", "units", "reach_unowned", "reach_neutral", "threatened_own", "undefended_own",
    "enemy_neighbors", "max_enemy_sc", "sc_x_units", "frontier_units",
]


class Graph:
    def __init__(self, variant):
        self.terr = {t["id"]: t for t in variant["territories"]}
        self.parent = {t["id"]: t["coastParentID"] for t in variant["territories"]}
        self.reach = {}
        for t in variant["territories"]:
            for utype in ("Army", "Fleet"):
                self.reach[(utype, t["id"])] = {
                    self.parent[e["id"]] for e in t["coastalBorders"] if e[utype.lower()]
                }
        self.supply = [t["id"] for t in variant["territories"] if t["supply"] and t["coast"] != "Child"]


def features(g, units, owner, power):
    mine = [u for u in units if u[0] == power]
    enemy = [u for u in units if u[0] != power]
    my_reach = set()
    for u in mine:
        my_reach |= g.reach.get((u[2], u[3]), set())
    enemy_reach = {}
    for u in enemy:
        for p in g.reach.get((u[2], u[3]), set()):
            enemy_reach.setdefault(p, set()).add(u[0])
    occupied = {u[1]: u[0] for u in units}
    sc_counts = {}
    for p, o in owner.items():
        if o:
            sc_counts[o] = sc_counts.get(o, 0) + 1
    sc = sc_counts.get(power, 0)
    own = [p for p, o in owner.items() if o == power]
    reach_unowned = sum(1 for p in owner if owner[p] != power and p in my_reach)
    reach_neutral = sum(1 for p in owner if not owner[p] and p in my_reach)
    threatened = sum(1 for p in own if p in enemy_reach)
    undefended = sum(1 for p in own if p in enemy_reach and occupied.get(p) != power and p not in my_reach)
    neighbors = set()
    frontier = 0
    for u in mine:
        touching = {c for p in g.reach.get((u[2], u[3]), set()) for c in enemy_reach.get(p, ())}
        neighbors |= touching
        frontier += bool(touching)
    max_enemy = max((v for k, v in sc_counts.items() if k != power), default=0)
    return [1.0, sc, len(mine), reach_unowned, reach_neutral, threatened, undefended,
            len(neighbors), max_enemy, sc * len(mine) / 34.0, frontier]


_WEIGHTS = None


def weights():
    global _WEIGHTS
    if _WEIGHTS is None:
        path = Path(__file__).with_name("value_weights.json")
        _WEIGHTS = json.loads(path.read_text())["weights"] if path.exists() else None
    return _WEIGHTS


def predict(g, units, owner, power):
    w = weights()
    f = features(g, units, owner, power)
    return sum(a * b for a, b in zip(w, f))
