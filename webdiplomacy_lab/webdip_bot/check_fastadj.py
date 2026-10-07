"""Differential test: fastadj vs the `diplomacy` package on real positions + random legal orders.

Runs inside the player image (needs players.legal_orders and diplomacy):
    docker run --rm --platform linux/amd64 -v $PWD/webdiplomacy_lab/local_runs:/runs:ro \
      --entrypoint /opt/.venv/bin/python webdip-bot:TAG -m webdip_bot.check_fastadj /runs [N_PER_PHASE]
Prints mismatches and a summary; exit 1 on any mismatch.
"""

import glob
import json
import random
import sys
import time

from players.legal_orders import LegalOrders

from webdip_bot.dipmap import POWER
from webdip_bot.search import dipmap, fast_orders
from webdip_bot import fastadj
import diplomacy


def positions(root):
    for path in sorted(glob.glob(f"{root}/*/*/replay")):
        frames = json.load(open(path))
        variant = frames[-1]["variant"]
        for ph in frames[-1]["history"]["phases"]:
            if ph["phase"] == "Diplomacy" and ph["units"]:
                yield variant, ph


def board_from(variant, ph):
    units = [
        {"id": i + 1, "countryID": u["countryID"], "type": u["type"], "terrID": u["terrID"], "retreating": False}
        for i, u in enumerate(ph["units"])
        if not u.get("retreating")
    ]
    parent = {t["id"]: t["coastParentID"] for t in variant["territories"]}
    unit_at = {parent[u["terrID"]]: u["id"] for u in units}
    owner = {c["terrID"]: c["countryID"] for c in ph["centers"]}
    terrs = [
        {"terrID": t["id"], "ownerCountryID": owner.get(t["id"], 0), "unitID": unit_at.get(t["id"]),
         "standoff": False, "occupiedFromTerrID": None}
        for t in variant["territories"] if t["coast"] != "Child"
    ]
    return {"units": units, "territories": terrs, "turn": ph["turn"]}


def main():
    root = sys.argv[1]
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    rng = random.Random(0)
    n = bad = auto_disbanded = 0
    t_fast = t_pkg = 0.0
    g = diplomacy.Game()
    for variant, ph in positions(root):
        board = board_from(variant, ph)
        legal = LegalOrders(variant, board)
        dm = dipmap(variant)
        parent = {t["id"]: t["coastParentID"] for t in variant["territories"]}
        unit_at = {}
        for u in board["units"]:
            unit_at[u["terrID"]] = u
            unit_at[parent[u["terrID"]]] = u
        owners = {c["terrID"]: c["countryID"] for c in ph["centers"]}
        state = dm.state(board["units"], owners, ph["turn"])
        for _ in range(per):
            orders = []
            for u in board["units"]:
                options = [o for o in legal.movement(u) if o["type"] != "Convoy" and o.get("viaConvoy") != "Yes"]
                orders.append(rng.choice(options))
            units, tuples = fast_orders(board["units"], orders, parent)
            t0 = time.perf_counter()
            moved, dislodged = fastadj.adjudicate(units, tuples)
            t1 = time.perf_counter()
            g.set_state(state)
            by_power = {}
            for u, o in zip(board["units"], orders):
                by_power.setdefault(POWER[int(u["countryID"])], []).append(dm.order(o, unit_at))
            for p, os in by_power.items():
                g.set_orders(p, os)
            g.process()
            t2 = time.perf_counter()
            t_fast += t1 - t0
            t_pkg += t2 - t1
            # Package outcome: final province per unit and dislodged flags.
            res = g.get_state()["units"]
            pkg = set()
            for p, us in res.items():
                for s in us:
                    pkg.add((p, s.startswith("*"), s.lstrip("*")[2:5]))
            fast = set()
            for (country, prov, utype), o, mv, dl in zip(units, tuples, moved, dislodged):
                where = o[1] if mv else prov
                fast.add((POWER[country], dl, dm.loc[where][:3]))
            n += 1
            # The package disbands a dislodged unit at once when it has no retreat; ours
            # still reports it as dislodged. Only differences beyond that are mismatches.
            extra = fast - pkg
            if not (pkg - fast) and all(dl for _, dl, _ in extra):
                auto_disbanded += len(extra)
                continue
            if pkg != fast:
                bad += 1
                if bad <= 5:
                    print("MISMATCH", ph["turn"], json.dumps([dm.order(o, unit_at) for o in orders]))
                    print("  package only:", sorted(pkg - fast))
                    print("  fast only:   ", sorted(fast - pkg))
    print(json.dumps({"cases": n, "mismatches": bad, "fast_ms": round(1000 * t_fast / max(n, 1), 3),
                      "package_ms": round(1000 * t_pkg / max(n, 1), 3),
                      "auto_disbanded_dislodged": auto_disbanded}))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
