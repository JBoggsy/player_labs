"""SearchBot: best response to a DumbBot opponent model, using a real adjudicator.

Movement phases only (retreats/builds delegate to DumbBot):
1. Opponent model: for every other power, sample M DumbBot order sets.
2. Our seeds: K DumbBot samples for our power; keep the best under the evaluation.
3. Coordinate ascent: for each of our units, try every legal non-convoy order and keep
   the one with the best mean evaluation across the M opponent samples. Repeat until no
   change or the time budget is spent.
Evaluation of an adjudicated outcome (from our side): projected supply centres (what we
would own if this were an autumn), plus a small positional term from DumbBot's node
values, minus dislodged units.
"""

import math
import time

import diplomacy

from webdip_bot import config, fastadj
from webdip_bot.dipmap import COUNTRY, POWER, DipMap
from webdip_bot.dumbbot import Board, DumbBot

_MAPS = {}
_GAME = None


def dipmap(variant):
    key = variant["variantID"]
    if key not in _MAPS:
        _MAPS[key] = DipMap(variant["territories"])
    return _MAPS[key]


class SearchBot:
    def __init__(self, variant, board, country, phase, turn, rng):
        self.variant, self.board, self.country, self.phase, self.turn, self.rng = (
            variant, board, country, phase, turn, rng)
        self.dumb = DumbBot(variant, board, country, phase, turn, rng)
        self.b = self.dumb.b
        self.trace = self.dumb.trace
        self.api = self.context = None
        self.memory = {}

    def observe(self, api, context, state):
        """Called by bot.py each phase; `state` persists across the whole game."""
        self.api, self.context = api, context
        self.memory = state.setdefault("search", {"logodds": {}, "pending": None})

    def _update_beliefs(self):
        """Score each opponent's last movement orders: DumbBot-like vs uniform-random legal.

        `pending` holds last movement phase's DumbBot samples per unit. The log-odds per
        power accumulate log(P_dumbbot(order) / P_random(order)); the opponent sample mix
        uses sigmoid(log-odds) as the DumbBot share.
        """
        pending = self.memory.get("pending")
        if not pending or self.api is None:
            return
        self.memory["pending"] = None
        ref = (self.context.get("files") or {}).get("history")
        if not ref:
            return
        history = self.api.file(ref)
        entry = next((ph for ph in history.get("phases", []) if ph["turn"] == pending["turn"] and ph["phase"] == "Diplomacy"), None)
        if entry is None:
            return
        for o in entry.get("orders") or []:
            key = str(o["terrID"])
            unit = pending["units"].get(key)
            if unit is None or int(o["countryID"]) == self.country:
                continue
            sig = (o["type"], o["toTerrID"] or 0, o["fromTerrID"] or 0)
            samples = unit["samples"]
            matches = sum(1 for x in samples if tuple(x) == sig)
            n_legal = max(unit["n_legal"], 1)
            p_dumb = 0.9 * matches / len(samples) + 0.1 / n_legal
            p_rand = 1.0 / n_legal
            c = str(o["countryID"])
            lo = self.memory["logodds"].get(c, config.OPP_PRIOR_LOGODDS) + math.log(p_dumb / p_rand)
            self.memory["logodds"][c] = max(-config.OPP_LOGODDS_CLIP, min(config.OPP_LOGODDS_CLIP, lo))

    def _dumb_share(self, c):
        if config.OPP_MODEL != "adaptive":
            return 1.0
        lo = self.memory.get("logodds", {}).get(str(c), config.OPP_PRIOR_LOGODDS)
        return 1.0 / (1.0 + math.exp(-lo))

    def choose(self, slots):
        if self.phase != "Diplomacy" or not slots:
            return self.dumb.choose(slots)
        started = time.monotonic()
        b = self.b
        dm = dipmap(self.variant)
        self.unit_at = {}
        for u in b.units:
            self.unit_at[u["terrID"]] = u
            self.unit_at[b.province(u["terrID"])] = u
        self.state = dm.state(b.all_units, b.owner, self.turn)
        self.dm = dm
        by_id = {u["id"]: u for u in b.all_units}
        mine = [by_id[s["unitID"]] for s in slots]

        # 1. Opponent samples (each a {power: [order strings]}), DumbBot or uniform-random
        # legal per power according to the adaptive belief.
        self._update_beliefs()
        opponents = []
        raw_samples = []
        models = {}
        theirs = {}
        for c in {int(u["countryID"]) for u in b.units} - {self.country}:
            models[c] = DumbBot(self.variant, self.board, c, self.phase, self.turn, self.rng, board_model=b)
            theirs[c] = [u for u in b.units if int(u["countryID"]) == c]
        legal = {u["id"]: b.legal.movement(u) for us in theirs.values() for u in us}
        dumb_samples = {c: [] for c in models}
        for _ in range(config.SEARCH_OPPONENT_SAMPLES):
            sample = {}
            raw = []
            for c, model in models.items():
                d = model.choose([{"unitID": u["id"]} for u in theirs[c]])
                dumb_samples[c].append(d)
                if self.rng.random() < self._dumb_share(c):
                    chosen = d
                else:
                    chosen = [self.rng.choice(legal[u["id"]]) for u in theirs[c]]
                    self.trace["opp_random_samples"] += 1
                sample[POWER[c]] = [self._dip(o) for o in chosen]
                raw.extend(zip(theirs[c], chosen))
            opponents.append(sample)
            raw_samples.append(raw)
        self.memory["pending"] = {
            "turn": self.turn,
            "units": {
                str(u["terrID"]): {
                    "n_legal": len(legal[u["id"]]),
                    "samples": [[d[k]["type"], d[k]["toTerrID"] or 0, d[k]["fromTerrID"] or 0] for d in dumb_samples[c]],
                }
                for c in models
                for k, u in enumerate(theirs[c])
            },
        }
        shares = [self._dumb_share(c) for c in models]
        if shares:
            self.trace["opp_dumb_share_x100"] = round(100 * sum(shares) / len(shares))
        self.opponents = opponents
        self.sims = 0
        self._prepare_fast(mine, raw_samples)

        # 2. Seeds from DumbBot for our own power (separate instance: keeps self.trace clean).
        seeder = DumbBot(self.variant, self.board, self.country, self.phase, self.turn, self.rng, board_model=b)
        seeds = []
        for _ in range(config.SEARCH_SEEDS):
            cand = seeder.choose(slots)
            seeds.append((self._evaluate(cand), cand))
        seeds.sort(key=lambda x: -x[0])
        self.trace["search_seed_score"] = round(seeds[0][0], 1)

        # 3. Coordinate ascent over each unit's legal orders, from the best few seeds.
        self.joints = self._joint_alternatives(mine)
        self.improved_any = 0
        finals = []
        seen = set()
        for score, cand in seeds[: config.SEARCH_RESTARTS]:
            score, cand = self._ascend(cand, score, started)
            key = tuple(_key(o) for o in cand)
            if key not in seen:
                seen.add(key)
                finals.append((score, cand))
        finals.sort(key=lambda x: -x[0])
        best_score, best = finals[0]
        improved_any = self.improved_any
        if config.SEARCH_ROLLOUT and self.turn % 2 == 0 and len(finals) > 1:
            best = self._rollout_rerank(finals, mine, started)
        self.trace["search_improvements"] += improved_any
        self.trace["search_sims"] += self.sims
        self.trace["search_score"] = round(best_score, 1)
        self.trace["search_ms"] = round((time.monotonic() - started) * 1000)
        return [self.dumb._legal_or_hold(u, o) for u, o in zip(mine, best)]

    def _ascend(self, best, best_score, started):
        for _ in range(config.SEARCH_PASSES):
            changed = False
            order_idx = list(range(len(best)))
            self.rng.shuffle(order_idx)
            for i in order_idx:
                if time.monotonic() - started > config.SEARCH_TIME_BUDGET_S:
                    self.trace["search_budget_hit"] += 1
                    return best_score, best
                for joint in self.joints[i]:
                    if all(_same(o, best[k]) for k, o in joint.items()):
                        continue
                    cand = [joint.get(k, o) for k, o in enumerate(best)]
                    s = self._evaluate(cand)
                    if s > best_score + 1e-9:
                        best, best_score, changed = cand, s, True
                        self.improved_any += 1
                        if len(joint) > 1:
                            self.trace["search_joint_improvement"] += 1
            if not changed:
                break
        return best_score, best

    def _rollout_rerank(self, finals, mine, started):
        """Spring only: re-rank the top distinct ascent results by a simulated autumn.

        For each candidate and opponent sample: adjudicate spring (fastadj), drop dislodged
        units, let every power (us included) play DumbBot in autumn, adjudicate, and count
        the resulting supply centres. Combined with the static score as a tie-breaker.
        """
        pool = finals[: config.SEARCH_ROLLOUT_POOL]
        n = min(config.SEARCH_ROLLOUT_SAMPLES, len(self.fast_samples))
        best, best_value = pool[0][1], None
        for static, cand in pool:
            mu, mo = fast_orders(self.mine_units, cand, self.parent)
            if mo is None:
                continue
            total, count = 0.0, 0
            for units, fu, fo, raw in self.fast_samples[:n]:
                if fo is None:
                    continue
                if time.monotonic() - started > config.SEARCH_TIME_BUDGET_S:
                    self.trace["rollout_budget_hit"] += 1
                    break
                total += self._rollout(mu + fu, mo + fo, self.mine_units + units, cand + raw)
                count += 1
            if not count:
                continue
            value = total / count + config.SEARCH_ROLLOUT_STATIC_WEIGHT * static
            if best_value is None or value > best_value:
                best, best_value = cand, value
        if best is not pool[0][1]:
            self.trace["rollout_changed_choice"] += 1
        self.trace["rollouts"] += 1
        return best

    def _rollout(self, fu, fo, units, orders):
        moved, dislodged = fastadj.adjudicate(fu, fo)
        new_units = []
        for (country, prov, utype), o, mv, dl, u, raw in zip(fu, fo, moved, dislodged, units, orders):
            if dl:
                continue
            new_units.append({"id": u["id"], "countryID": country, "type": utype,
                              "terrID": raw["toTerrID"] if mv else u["terrID"], "retreating": False})
        unit_at = {self.parent[u["terrID"]]: u["id"] for u in new_units}
        terrs = [{"terrID": t, "ownerCountryID": (self.b.status.get(t) or {}).get("ownerCountryID") or 0,
                  "unitID": unit_at.get(t), "standoff": False, "occupiedFromTerrID": None}
                 for t, x in self.b.terr.items() if x["coast"] != "Child"]
        board = {"units": new_units, "territories": terrs}
        model = Board(self.variant, board)
        fall = []
        for c in {u["countryID"] for u in new_units}:
            theirs = [u for u in new_units if u["countryID"] == c]
            bot = DumbBot(self.variant, board, c, "Diplomacy", self.turn + 1, self.rng, board_model=model)
            fall.extend(zip(theirs, bot.choose([{"unitID": u["id"]} for u in theirs])))
        fu2, fo2 = fast_orders([u for u, _ in fall], [o for _, o in fall], self.parent)
        if fo2 is None:
            return 0.0
        moved2, dislodged2 = fastadj.adjudicate(fu2, fo2)
        occupied = {}
        for (country, prov, _), o, mv, dl in zip(fu2, fo2, moved2, dislodged2):
            if not dl:
                occupied[o[1] if mv else prov] = country
        sc = sum(1 for t, owner in self.b.owner.items() if occupied.get(t, owner) == self.country)
        return config.SEARCH_SC_WEIGHT * sc

    def _joint_alternatives(self, mine):
        """Per primary unit i: list of {unit index: order} changes to try together.

        Singles: every legal non-convoy order of unit i. With SEARCH_PAIRS: unit i's move
        to X plus a support of that move by another of our units (a supported attack only
        pays off when both units change together, which single-unit ascent cannot find).
        With SEARCH_CONVOYS: army i's convoyed move plus the Convoy orders of the fleets on
        its path, when all of them are ours.
        """
        b = self.b
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
                        self.trace["search_convoy_options"] += 1
                    continue
                if not config.SEARCH_PAIRS:
                    continue
                for k, other in enumerate(legal):
                    if k == i:
                        continue
                    support = next((c for c in other if c["type"] == "Support move" and c["toTerrID"] == target
                                    and c["fromTerrID"] == here), None)
                    if support is not None:
                        options.append({i: o, k: support})
            joints.append(options)
        return joints

    def _dip(self, o):
        return self.dm.order(o, self.unit_at)

    def _prepare_fast(self, mine, raw_samples):
        """Province-level arrays for fastadj: our units first, then each sample's others."""
        parent = {t: self.b.province(t) for t in self.b.terr}
        self.parent = parent
        self.mine_units = mine
        self.fast_samples = []
        for raw in raw_samples:
            units = [u for u, _ in raw]
            fu, fo = fast_orders(units, [o for _, o in raw], parent)
            self.fast_samples.append((units, fu, fo, [o for _, o in raw]))
        self.vmax = max(self.dumb.value.values()) or 1.0

    def _evaluate(self, ours):
        mu, mo = fast_orders(self.mine_units, ours, self.parent)
        total = 0.0
        mine_dip = None
        for k, (units, fu, fo, raw) in enumerate(self.fast_samples):
            if mo is not None and fo is not None and config.SEARCH_FAST_ADJ:
                total += self._score_fast(mu + fu, mo + fo, self.mine_units + units, ours + raw)
                self.sims += 1
            else:
                if mine_dip is None:
                    mine_dip = [self._dip(o) for o in ours]
                total += self._score(self._adjudicate(mine_dip, self.opponents[k]))
                self.trace["search_package_sims"] += 1
        return total / len(self.fast_samples)

    def _score_fast(self, fu, fo, units, orders):
        moved, dislodged = fastadj.adjudicate(fu, fo)
        occupied = {}
        my_nodes = []
        lost = 0
        for (country, prov, utype), o, mv, dl, u, raw in zip(fu, fo, moved, dislodged, units, orders):
            if dl:
                lost += country == self.country
                continue
            where = o[1] if mv else prov
            occupied[where] = country
            if country == self.country:
                my_nodes.append((utype, raw["toTerrID"] if mv else u["terrID"]))
        counts = {}
        for t, owner in self.b.owner.items():
            holder = occupied.get(t, owner)
            if holder:
                counts[holder] = counts.get(holder, 0) + 1
        sc = counts.get(self.country, 0)
        if config.SEARCH_OBJECTIVE == "share":
            total = sum(v * v for v in counts.values()) or 1
            sc = 34.0 * sc * sc / total
        pos = sum(self.dumb.value.get(n, 0.0) for n in my_nodes) / self.vmax
        return config.SEARCH_SC_WEIGHT * sc + config.SEARCH_POS_WEIGHT * pos - config.SEARCH_DISLODGED_WEIGHT * lost

    def _adjudicate(self, mine, sample):
        self.sims += 1
        global _GAME
        if _GAME is None:
            _GAME = diplomacy.Game()  # reused: set_state fully resets it, and it is ~1/3 cheaper
        g = _GAME
        g.set_state(self.state)
        g.set_orders(POWER[self.country], mine)
        for power, orders in sample.items():
            g.set_orders(power, orders)
        g.process()
        return g

    def _score(self, g):
        me = POWER[self.country]
        units = g.get_state()["units"]
        occupied = {}
        mine, dislodged = [], 0
        for power, us in units.items():
            for u in us:
                if u.startswith("*"):  # dislodged: does not hold the province
                    dislodged += power == me
                    continue
                occupied[u[2:5]] = power
                if power == me:
                    mine.append(u)
        counts = {}
        for t, owner in self.b.owner.items():
            occ = occupied.get(self.dm.loc[t])
            holder = occ if occ is not None else (POWER[owner] if owner else None)
            if holder:
                counts[holder] = counts.get(holder, 0) + 1
        sc = counts.get(me, 0)
        if config.SEARCH_OBJECTIVE == "share":
            # The league's draw score: SC^2 / sum SC^2, scaled to SC units (x34).
            total = sum(v * v for v in counts.values()) or 1
            sc = 34.0 * sc * sc / total
        pos = 0.0
        vmax = max(self.dumb.value.values()) or 1.0
        for u in mine:
            node = ("Army" if u[0] == "A" else "Fleet", self.dm.terr[u[2:]])
            pos += self.dumb.value.get(node, 0.0) / vmax
        return config.SEARCH_SC_WEIGHT * sc + config.SEARCH_POS_WEIGHT * pos - config.SEARCH_DISLODGED_WEIGHT * dislodged


def _key(o):
    return (o["type"], o["terrID"], o["toTerrID"], o["fromTerrID"])


def _same(a, b):
    return (a["type"], a["terrID"], a["toTerrID"], a["fromTerrID"]) == (b["type"], b["terrID"], b["toTerrID"], b["fromTerrID"])


def fast_orders(units, orders, parent):
    """webDip units + parallel movement orders -> fastadj (units, order tuples), province level.

    Returns None for the orders if any is a Convoy / convoyed move (caller falls back)."""
    fu, fo = [], []
    for u, o in zip(units, orders):
        fu.append((int(u["countryID"]), parent[u["terrID"]], u["type"]))
        kind = o["type"]
        if kind == "Move":
            if o.get("viaConvoy") in ("Yes", True):
                return fu, None
            fo.append(("M", parent[o["toTerrID"]]))
        elif kind == "Support hold":
            fo.append(("SH", parent[o["toTerrID"]]))
        elif kind == "Support move":
            fo.append(("SM", parent[o["fromTerrID"]], parent[o["toTerrID"]]))
        elif kind == "Convoy":
            return fu, None
        else:
            fo.append(("H",))
    return fu, fo
