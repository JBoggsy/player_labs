"""Order encoding and the package adjudicator used by search and diagnostics."""

import diplomacy

from webdip_bot import config
from webdip_bot.dipmap import POWER, DipMap

_MAPS = {}
_GAME = None


def dipmap(variant):
    key = variant["variantID"]
    if key not in _MAPS:
        _MAPS[key] = DipMap(variant["territories"])
    return _MAPS[key]


def adjudicate(bot, mine, sample):
    bot.sims += 1
    global _GAME
    if _GAME is None:
        _GAME = diplomacy.Game()  # reused: set_state fully resets it, and it is ~1/3 cheaper
    g = _GAME
    g.set_state(bot.state)
    g.set_orders(POWER[bot.country], mine)
    for power, orders in sample.items():
        g.set_orders(power, orders)
    g.process()
    return g


def order_destroy(b, u):
    p = b.province(u["terrID"])
    return {"type": "Destroy", "terrID": p, "toTerrID": p, "fromTerrID": 0, "viaConvoy": "No"}


def _key(o):
    return (o["type"], o["terrID"], o["toTerrID"], o["fromTerrID"])


def _same(a, b):
    return (a["type"], a["terrID"], a["toTerrID"], a["fromTerrID"]) == (b["type"], b["terrID"], b["toTerrID"], b["fromTerrID"])


def fast_orders(units, orders, parent):
    """webDip units + parallel movement orders -> fastadj (units, order tuples), province level.

    Convoys (SEARCH_CONVOY_APPROX, default on): a convoying fleet holds; a convoyed army move
    becomes a plain move when every fleet on its path is ordered to convoy exactly that move,
    otherwise a hold. This ignores convoy disruption by dislodging a fleet, which is fine for
    *evaluating* hypotheticals and keeps almost every simulation on the fast path (the
    package fallback was ~95% of search time against convoy-happy random opponents).
    With the approximation off, any convoy returns None (caller falls back to the package)."""
    fu, fo = [], []
    convoys = None
    for u, o in zip(units, orders):
        fu.append((int(u["countryID"]), parent[u["terrID"]], u["type"]))
        kind = o["type"]
        if kind == "Move":
            if o.get("viaConvoy") in ("Yes", True):
                if not config.SEARCH_CONVOY_APPROX:
                    return fu, None
                if convoys is None:
                    convoys = {
                        (parent[c["terrID"]], parent[c["fromTerrID"]], parent[c["toTerrID"]])
                        for c in orders if c["type"] == "Convoy"
                    }
                src, dst = parent[o["terrID"]], parent[o["toTerrID"]]
                path = (o.get("convoyPath") or [])[1:]
                if path and all((parent[f], src, dst) in convoys for f in path):
                    fo.append(("M", dst))
                else:
                    fo.append(("H",))
                continue
            fo.append(("M", parent[o["toTerrID"]]))
        elif kind == "Support hold":
            fo.append(("SH", parent[o["toTerrID"]]))
        elif kind == "Support move":
            fo.append(("SM", parent[o["fromTerrID"]], parent[o["toTerrID"]]))
        elif kind == "Convoy":
            if not config.SEARCH_CONVOY_APPROX:
                return fu, None
            fo.append(("H",))
        else:
            fo.append(("H",))
    return fu, fo
