"""Golden behaviour contract for the search bots (Kissinger and friends).

Records the exact orders a policy chooses on a fixed set of real positions with fixed
seeds and no time budget, and checks that the current code reproduces them bit for bit.
Any refactor or port of the search must pass `check` unchanged.

Run inside the player image (needs players.legal_orders and diplomacy):
    docker run --rm --platform linux/amd64 -v $PWD/webdiplomacy_lab:/lab \
      --entrypoint /opt/.venv/bin/python webdip-bot:TAG -m webdip_bot.golden check /lab/webdip_bot/tests/golden.json
    ... -m webdip_bot.golden record /lab/local_runs /lab/webdip_bot/tests/golden.json   # (re)create

Cases cover movement phases (several turns, powers, unit counts), three opponent-belief
states (empty prior, all-competent, all-random) and winter builds. Policies: kissinger,
machiavelli (level 0) and the plain DumbBot fallback for builds.
"""

import glob
import json
import random
import sys

POLICIES = ["kissinger", "machiavelli"]
BELIEFS = {
    "prior": None,
    "competent": 8.0,
    "random": -8.0,
}


def _board(variant, units, centers):
    parent = {t["id"]: t["coastParentID"] for t in variant["territories"]}
    unit_at = {parent[u["terrID"]]: u["id"] for u in units}
    owner = {c["terrID"]: c["countryID"] for c in centers}
    terrs = [
        {"terrID": t["id"], "ownerCountryID": owner.get(t["id"], 0), "unitID": unit_at.get(t["id"]),
         "standoff": False, "occupiedFromTerrID": None}
        for t in variant["territories"] if t["coast"] != "Child"
    ]
    return {"units": units, "territories": terrs}


_DEFAULTS = None


def _choose(policy, variant, case):
    from webdip_bot import config
    from webdip_bot.bot import policy_class

    global _DEFAULTS
    if _DEFAULTS is None:
        _DEFAULTS = {k: v for k, v in vars(config).items() if k.isupper()}
    for k, v in _DEFAULTS.items():  # policies mutate the config module: reset per case
        setattr(config, k, list(v) if isinstance(v, list) else v)
    cls = policy_class(policy)
    config.SEARCH_TIME_BUDGET_S = 1e9  # determinism: never stop on wall clock
    board = _board(variant, case["units"], case["centers"])
    rng = random.Random(case["seed"])
    bot = cls(variant, board, case["country"], case["phase"], case["turn"], rng)
    lo = BELIEFS[case["belief"]]
    if hasattr(bot, "memory"):
        bot.memory = {"logodds": {str(c): lo for c in range(1, 8)} if lo is not None else {}, "pending": None}
    return bot.choose(case["slots"])


def _signature(orders):
    return [[o["type"], o.get("terrID"), o.get("toTerrID"), o.get("fromTerrID"), str(o.get("viaConvoy"))] for o in orders]


def _cases(root):
    paths = sorted(glob.glob(f"{root}/*/*/replay"))
    picked = [paths[i] for i in range(0, len(paths), max(1, len(paths) // 4))][:4]
    variant = None
    cases = []
    for k, path in enumerate(picked):
        frames = json.load(open(path))
        variant = frames[-1]["variant"]
        phases = frames[-1]["history"]["phases"]
        movement = [p for p in phases if p["phase"] == "Diplomacy" and p["units"]]
        for ph in [movement[i] for i in (0, 3, 8, 13) if i < len(movement)]:
            units = [{"id": i + 1, "countryID": u["countryID"], "type": u["type"], "terrID": u["terrID"],
                      "retreating": False} for i, u in enumerate(ph["units"]) if not u.get("retreating")]
            countries = sorted({u["countryID"] for u in units})
            for country in countries[k % 2::3]:
                slots = [{"unitID": u["id"]} for u in units if u["countryID"] == country]
                for belief in BELIEFS:
                    cases.append({"kind": "movement", "phase": "Diplomacy", "turn": ph["turn"], "country": country,
                                  "units": units, "centers": ph["centers"], "slots": slots, "belief": belief,
                                  "seed": 1000 * k + ph["turn"] * 10 + country})
        builds = [p for p in phases if p["phase"] == "Builds" and p["units"]]
        for ph in builds[:2]:
            units = [{"id": i + 1, "countryID": u["countryID"], "type": u["type"], "terrID": u["terrID"],
                      "retreating": False} for i, u in enumerate(ph["units"]) if not u.get("retreating")]
            for country in range(1, 8):
                n_units = sum(u["countryID"] == country for u in units)
                n_centers = sum(c["countryID"] == country for c in ph["centers"])
                delta = n_centers - n_units
                if delta:
                    cases.append({"kind": "builds", "phase": "Builds", "turn": ph["turn"], "country": country,
                                  "units": units, "centers": ph["centers"], "belief": "prior",
                                  "slots": [{"unitID": None}] * min(abs(delta), 3), "seed": 7 * country + ph["turn"]})
    return variant, cases


def record(root, out):
    variant, cases = _cases(root)
    for case in cases:
        case["expected"] = {p: _signature(_choose(p, variant, case)) for p in POLICIES}
    json.dump({"variant": variant, "policies": POLICIES, "cases": cases}, open(out, "w"))
    print(json.dumps({"recorded": len(cases), "out": out}))


def check(path):
    data = json.load(open(path))
    bad = 0
    for i, case in enumerate(data["cases"]):
        for p in data["policies"]:
            got = _signature(_choose(p, data["variant"], case))
            if got != case["expected"][p]:
                bad += 1
                if bad <= 5:
                    print(f"MISMATCH case {i} ({case['kind']} t{case['turn']} c{case['country']} {case['belief']}) {p}")
    total = len(data["cases"]) * len(data["policies"])
    print(json.dumps({"checked": total, "mismatches": bad}))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    if sys.argv[1] == "record":
        record(sys.argv[2], sys.argv[3])
    else:
        check(sys.argv[2])
