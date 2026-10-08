"""Movement seeds, joint alternatives, ascent and mixed selection on shared bot state."""

import time

from webdip_bot import config, search_lookahead
from webdip_bot.dumbbot import DumbBot
from webdip_bot.search_orders import _key, _same


def choose_movement(bot, slots, mine, started):
    seeds = seed_plans(bot, slots)

    # 3. Coordinate ascent over each unit's legal orders, from the best few seeds.
    bot.joints = joint_alternatives(bot, mine)
    bot.top_seen = []
    bot.improved_any = 0
    finals = []
    seen = set()
    for score, cand in seeds[: config.SEARCH_RESTARTS]:
        score, cand = ascend(bot, cand, score, started)
        key = tuple(_key(o) for o in cand)
        if key not in seen:
            seen.add(key)
            finals.append((score, cand))
    finals.sort(key=lambda x: -x[0])
    best_score, best = finals[0]
    if config.SEARCH_SOFTMAX_T > 0:
        best_score, best = select_mixed(bot, finals)
    improved_any = bot.improved_any
    if config.SEARCH_ROLLOUT and bot.turn % 2 == 0:
        # Pool: distinct ascent results plus the best distinct plans seen along the way.
        pool, keys = list(finals), {tuple(_key(o) for o in c) for _, c in finals}
        for sc, c in sorted(bot.top_seen, key=lambda x: -x[0]):
            k = tuple(_key(o) for o in c)
            if k not in keys:
                keys.add(k)
                pool.append((sc, c))
        pool.sort(key=lambda x: -x[0])
        if len(pool) > 1:
            best = search_lookahead.rollout_rerank(bot, pool, mine, started)
    bot.trace["search_improvements"] += improved_any
    bot.trace["search_sims"] += bot.sims
    bot.trace["search_score"] = round(best_score, 1)
    bot.trace["search_ms"] = round((time.monotonic() - started) * 1000)
    return [bot.dumb._legal_or_hold(u, o) for u, o in zip(mine, best)]


def seed_plans(bot, slots):
    # 2. Seeds from DumbBot for our own power (separate instance: keeps bot.trace clean).
    seeder = DumbBot(bot.variant, bot.board, bot.country, bot.phase, bot.turn, bot.rng, board_model=bot.b)
    seeds = []
    for _ in range(config.SEARCH_SEEDS):
        cand = seeder.choose(slots)
        if bot.press:
            cand = constrain(bot, cand)
        seeds.append((bot.evaluator.evaluate(cand), cand))
    seeds.sort(key=lambda x: -x[0])
    bot.trace["search_seed_score"] = round(seeds[0][0], 1)
    return seeds


def forbidden(bot, o):
    """A move or supported move into a province the press policy rules out (DMZ, ally centre)."""
    into = bot.press.get("forbid_into") if bot.press else None
    return bool(into) and o["type"] in ("Move", "Support move") and bot.b.province(o["toTerrID"]) in into


def constrain(bot, cand):
    """Apply pinned (promised) orders, and turn forbidden orders into holds."""
    out = []
    for i, o in enumerate(cand):
        if i in bot.pinned:
            o = bot.pinned[i]
        elif forbidden(bot, o):
            o = {"type": "Hold", "terrID": o["terrID"], "toTerrID": 0, "fromTerrID": 0, "viaConvoy": "No"}
            bot.trace["press_forbidden_seed_order"] += 1
        out.append(o)
    return out


def select_mixed(bot, finals):
    # Mixed strategy: sample among the best distinct plans seen, weighted by
    # exp(score / T). Harder for best-responding opponents to anticipate.
    import math

    pool, keys = list(finals), {tuple(_key(o) for o in c) for _, c in finals}
    for sc, c in sorted(bot.top_seen, key=lambda x: -x[0]):
        k = tuple(_key(o) for o in c)
        if k not in keys:
            keys.add(k)
            pool.append((sc, c))
    pool = sorted(pool, key=lambda x: -x[0])[: config.SEARCH_SOFTMAX_POOL]
    top = pool[0][0]
    weights = [math.exp((sc - top) / config.SEARCH_SOFTMAX_T) for sc, _ in pool]
    pick = bot.rng.choices(range(len(pool)), weights=weights)[0]
    best_score, best = pool[pick]
    bot.trace["mixed_pick_not_best"] += int(pick != 0)
    return best_score, best


def remember(bot, score, cand):
    """Keep the best few plans evaluated during the ascent (rollout re-rank pool)."""
    top = bot.__dict__.setdefault("top_seen", [])
    if len(top) < config.SEARCH_ROLLOUT_POOL * 2:
        top.append((score, cand))
    else:
        worst = min(range(len(top)), key=lambda i: top[i][0])
        if score > top[worst][0]:
            top[worst] = (score, cand)


def ascend(bot, best, best_score, started):
    for _ in range(config.SEARCH_PASSES):
        changed = False
        order_idx = list(range(len(best)))
        bot.rng.shuffle(order_idx)
        for i in order_idx:
            if time.monotonic() - started > config.SEARCH_TIME_BUDGET_S:
                bot.trace["search_budget_hit"] += 1
                return best_score, best
            for joint in bot.joints[i]:
                if all(_same(o, best[k]) for k, o in joint.items()):
                    continue
                cand = [joint.get(k, o) for k, o in enumerate(best)]
                s = bot.evaluator.evaluate(cand)
                remember(bot, s, cand)
                if s > best_score + 1e-9:
                    best, best_score, changed = cand, s, True
                    bot.improved_any += 1
                    if len(joint) > 1:
                        bot.trace["search_joint_improvement"] += 1
                    if len(joint) > 2:
                        bot.trace["search_triple_improvement"] += 1
        if not changed:
            break
    return best_score, best


def joint_alternatives(bot, mine):
    """Per primary unit i: list of {unit index: order} changes to try together.

    Singles: every legal non-convoy order of unit i. With SEARCH_PAIRS: unit i's move
    to X plus a support of that move by another of our units (a supported attack only
    pays off when both units change together, which single-unit ascent cannot find).
    With SEARCH_CONVOYS: army i's convoyed move plus the Convoy orders of the fleets on
    its path, when all of them are ours.
    """
    b = bot.b
    legal = [b.legal.movement(u) for u in mine]
    index_at = {b.province(u["terrID"]): k for k, u in enumerate(mine)}
    joints = []
    for i, u in enumerate(mine):
        here = b.province(u["terrID"])
        options = [{i: o} for o in legal[i] if o["type"] != "Convoy" and o.get("viaConvoy") != "Yes"]
        for o in legal[i]:
            if o["type"] != "Move":
                continue
            target = b.province(o["toTerrID"])
            if o.get("viaConvoy") == "Yes":
                if not config.SEARCH_CONVOYS:
                    continue
                path = o.get("convoyPath") or []
                fleets = [index_at.get(t) for t in path[1:]]
                if not fleets or None in fleets:
                    continue
                joint = {i: o}
                for k in fleets:
                    convoy = next((c for c in legal[k] if c["type"] == "Convoy" and c["fromTerrID"] == here
                                   and b.province(c["toTerrID"]) == target), None)
                    if convoy is None:
                        break
                    joint[k] = convoy
                else:
                    options.append(joint)
                    bot.trace["search_convoy_options"] += 1
                continue
            if not config.SEARCH_PAIRS:
                continue
            supporters = []
            for k, other in enumerate(legal):
                if k == i:
                    continue
                support = next((c for c in other if c["type"] == "Support move" and c["toTerrID"] == target
                                and c["fromTerrID"] == here), None)
                if support is not None:
                    options.append({i: o, k: support})
                    supporters.append((k, support))
            if config.SEARCH_TRIPLES:
                # Move with two supports: strength 3 breaks a supported hold.
                for a in range(len(supporters)):
                    for c2 in range(a + 1, len(supporters)):
                        (k1, s1), (k2, s2) = supporters[a], supporters[c2]
                        options.append({i: o, k1: s1, k2: s2})
                        bot.trace["search_triple_options"] += 1
        if bot.press:
            kept = [j for j in options
                    if not any(forbidden(bot, o) or (k in bot.pinned and not _same(o, bot.pinned[k])) for k, o in j.items())]
            bot.trace["press_pruned_alternatives"] += len(options) - len(kept)
            options = kept
        joints.append(options)
    return joints
