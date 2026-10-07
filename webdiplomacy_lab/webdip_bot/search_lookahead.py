"""Winter adjustment search and spring-to-autumn rollout on shared bot state."""

import time

from webdip_bot import config, fastadj
from webdip_bot.dumbbot import Board, DumbBot
from webdip_bot.search_orders import fast_orders, order_destroy


def search_adjustments(bot, slots):
    """Winter: pick builds/disbands by a quick search of the following spring.

    Candidates: DumbBot's own choice plus alternatives (other unit types / sites for
    builds, other unit subsets for disbands), capped at SEARCH_BUILD_CANDIDATES. Each is
    applied to a hypothetical board and scored by a reduced SearchBot run for spring.
    """
    import itertools

    started = time.monotonic()
    b = bot.b
    own = [u for u in b.units if int(u["countryID"]) == bot.country]
    default = bot.dumb.choose(slots)
    if b.centers[bot.country] < len(own):
        k = len(own) - b.centers[bot.country]
        k = min(k, len(slots))
        ranked = sorted(own, key=lambda u: bot.dumb.value.get(b.node(u), 0))[: k + 3]
        candidates = [[order_destroy(b, u) for u in combo] for combo in itertools.combinations(ranked, k)]
    else:
        options = b.legal.builds(bot.country)
        sites = {}
        for o in options:
            sites.setdefault(b.province(o["toTerrID"]), []).append(o)
        k = min(len(slots), len(sites))
        candidates = []
        for chosen_sites in itertools.combinations(sorted(sites), k):
            for combo in itertools.product(*(sites[x] for x in chosen_sites)):
                candidates.append(list(combo))
        if not candidates:
            return default
    candidates = [default] + [c for c in candidates if c != default]
    candidates = candidates[: config.SEARCH_BUILD_CANDIDATES]
    best, best_value = default, None
    for cand in candidates:
        if time.monotonic() - started > config.SEARCH_TIME_BUDGET_S:
            bot.trace["build_budget_hit"] += 1
            break
        value = spring_value(bot, cand)
        if best_value is None or value > best_value:
            best, best_value = cand, value
    if best is not default:
        bot.trace["build_search_changed"] += 1
    bot.trace["build_candidates"] += len(candidates)
    # Fill remaining build slots with Wait exactly as DumbBot does.
    if len(best) < len(slots) and best and best[0]["type"] != "Destroy":
        best = best + [{"type": "Wait", "terrID": 0, "toTerrID": 0, "fromTerrID": 0, "viaConvoy": "No"}]
    return best


def spring_value(bot, adjustments):
    """Static value of the spring after applying `adjustments` (reduced search)."""
    from webdip_bot.search import SearchBot

    units = [dict(u) for u in bot.board["units"] if not u["retreating"]]
    next_id = -1
    for o in adjustments:
        if o["type"] == "Destroy":
            units = [u for u in units if bot.b.province(u["terrID"]) != o["toTerrID"]]
        elif o["type"] in ("Build Army", "Build Fleet"):
            units.append({"id": next_id, "countryID": bot.country, "terrID": o["toTerrID"],
                          "type": "Army" if o["type"] == "Build Army" else "Fleet", "retreating": False})
            next_id -= 1
    unit_at = {bot.b.province(u["terrID"]): u["id"] for u in units}
    terrs = [dict(t, unitID=unit_at.get(t["terrID"])) for t in bot.board["territories"]]
    board = {**bot.board, "units": units, "territories": terrs}
    saved = {k: getattr(config, k) for k in ("SEARCH_OPPONENT_SAMPLES", "SEARCH_SEEDS", "SEARCH_PASSES",
                                             "SEARCH_RESTARTS", "SEARCH_ROLLOUT", "SEARCH_BUILDS")}
    config.SEARCH_OPPONENT_SAMPLES, config.SEARCH_SEEDS, config.SEARCH_PASSES = 6, 4, 1
    config.SEARCH_RESTARTS, config.SEARCH_ROLLOUT, config.SEARCH_BUILDS = 1, 0, 0
    try:
        next_bot = SearchBot(bot.variant, board, bot.country, "Diplomacy", bot.turn + 1, bot.rng)
        next_bot.memory = {"logodds": bot.memory.get("logodds", {}), "pending": None}
        mine = [{"unitID": u["id"]} for u in units if int(u["countryID"]) == bot.country]
        next_bot.choose(mine)
        return next_bot.trace["search_score"]
    finally:
        for k, v in saved.items():
            setattr(config, k, v)


def rollout_rerank(bot, finals, mine, started):
    """Spring only: re-rank the top distinct ascent results by a simulated autumn.

    For each candidate and opponent sample: adjudicate spring (fastadj), drop dislodged
    units, let every power (us included) play DumbBot in autumn, adjudicate, and count
    the resulting supply centres. Combined with the static score as a tie-breaker.
    """
    pool = finals[: config.SEARCH_ROLLOUT_POOL]
    n = min(config.SEARCH_ROLLOUT_SAMPLES, len(bot.fast_samples))
    best, best_value = pool[0][1], None
    for static, cand in pool:
        mu, mo = fast_orders(bot.mine_units, cand, bot.parent)
        if mo is None:
            continue
        total, count = 0.0, 0
        for units, fu, fo, raw in bot.fast_samples[:n]:
            if fo is None:
                continue
            if time.monotonic() - started > config.SEARCH_TIME_BUDGET_S:
                bot.trace["rollout_budget_hit"] += 1
                break
            total += rollout(bot, mu + fu, mo + fo, bot.mine_units + units, cand + raw)
            count += 1
        if not count:
            continue
        value = total / count + config.SEARCH_ROLLOUT_STATIC_WEIGHT * static
        if best_value is None or value > best_value:
            best, best_value = cand, value
    if best is not pool[0][1]:
        bot.trace["rollout_changed_choice"] += 1
    bot.trace["rollouts"] += 1
    return best


def rollout(bot, fu, fo, units, orders):
    moved, dislodged = fastadj.adjudicate(fu, fo)
    new_units = []
    for (country, prov, utype), o, mv, dl, u, raw in zip(fu, fo, moved, dislodged, units, orders):
        if dl:
            continue
        new_units.append({"id": u["id"], "countryID": country, "type": utype,
                          "terrID": raw["toTerrID"] if mv else u["terrID"], "retreating": False})
    unit_at = {bot.parent[u["terrID"]]: u["id"] for u in new_units}
    terrs = [{"terrID": t, "ownerCountryID": (bot.b.status.get(t) or {}).get("ownerCountryID") or 0,
              "unitID": unit_at.get(t), "standoff": False, "occupiedFromTerrID": None}
             for t, x in bot.b.terr.items() if x["coast"] != "Child"]
    board = {"units": new_units, "territories": terrs}
    model = Board(bot.variant, board)
    fall = []
    for c in {u["countryID"] for u in new_units}:
        theirs = [u for u in new_units if u["countryID"] == c]
        next_bot = DumbBot(bot.variant, board, c, "Diplomacy", bot.turn + 1, bot.rng, board_model=model)
        fall.extend(zip(theirs, next_bot.choose([{"unitID": u["id"]} for u in theirs])))
    fu2, fo2 = fast_orders([u for u, _ in fall], [o for _, o in fall], bot.parent)
    if fo2 is None:
        return 0.0
    moved2, dislodged2 = fastadj.adjudicate(fu2, fo2)
    occupied = {}
    for (country, prov, _), o, mv, dl in zip(fu2, fo2, moved2, dislodged2):
        if not dl:
            occupied[o[1] if mv else prov] = country
    sc = sum(1 for t, owner in bot.b.owner.items() if occupied.get(t, owner) == bot.country)
    return config.SEARCH_SC_WEIGHT * sc

