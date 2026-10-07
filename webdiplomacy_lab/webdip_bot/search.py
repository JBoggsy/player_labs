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

import time

import diplomacy

from webdip_bot import config
from webdip_bot.dipmap import COUNTRY, POWER, DipMap
from webdip_bot.dumbbot import DumbBot

_MAPS = {}


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

        # 1. Opponent samples (each a {power: [order strings]}).
        opponents = []
        models = {}
        for c in {int(u["countryID"]) for u in b.units} - {self.country}:
            models[c] = DumbBot(self.variant, self.board, c, self.phase, self.turn, self.rng, board_model=b)
        for _ in range(config.SEARCH_OPPONENT_SAMPLES):
            sample = {}
            for c, model in models.items():
                theirs = [{"unitID": u["id"]} for u in b.units if int(u["countryID"]) == c]
                sample[POWER[c]] = [self._dip(o) for o in model.choose(theirs)]
            opponents.append(sample)
        self.opponents = opponents
        self.sims = 0

        # 2. Seeds from DumbBot for our own power (separate instance: keeps self.trace clean).
        seeder = DumbBot(self.variant, self.board, self.country, self.phase, self.turn, self.rng, board_model=b)
        best, best_score = None, None
        for _ in range(config.SEARCH_SEEDS):
            cand = seeder.choose(slots)
            s = self._evaluate(cand)
            if best_score is None or s > best_score:
                best, best_score = cand, s
        self.trace["search_seed_score"] = round(best_score, 1)

        # 3. Coordinate ascent over each unit's legal orders.
        alternatives = [
            [o for o in b.legal.movement(u) if o["type"] != "Convoy" and o.get("viaConvoy") != "Yes"] for u in mine
        ]
        improved_any = 0
        for _ in range(config.SEARCH_PASSES):
            changed = False
            order_idx = list(range(len(mine)))
            self.rng.shuffle(order_idx)
            for i in order_idx:
                if time.monotonic() - started > config.SEARCH_TIME_BUDGET_S:
                    self.trace["search_budget_hit"] += 1
                    break
                for alt in alternatives[i]:
                    if _same(alt, best[i]):
                        continue
                    cand = best[:i] + [alt] + best[i + 1:]
                    s = self._evaluate(cand)
                    if s > best_score + 1e-9:
                        best, best_score, changed = cand, s, True
                        improved_any += 1
            if not changed:
                break
        self.trace["search_improvements"] += improved_any
        self.trace["search_sims"] += self.sims
        self.trace["search_score"] = round(best_score, 1)
        self.trace["search_ms"] = round((time.monotonic() - started) * 1000)
        return [self.dumb._legal_or_hold(u, o) for u, o in zip(mine, best)]

    def _dip(self, o):
        return self.dm.order(o, self.unit_at)

    def _evaluate(self, ours):
        mine = [self._dip(o) for o in ours]
        total = 0.0
        for sample in self.opponents:
            total += self._score(self._adjudicate(mine, sample))
        return total / len(self.opponents)

    def _adjudicate(self, mine, sample):
        self.sims += 1
        g = diplomacy.Game()
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
        sc = 0
        for t, owner in self.b.owner.items():
            occ = occupied.get(self.dm.loc[t])
            if occ == me or (occ is None and owner == self.country):
                sc += 1
        pos = 0.0
        vmax = max(self.dumb.value.values()) or 1.0
        for u in mine:
            node = ("Army" if u[0] == "A" else "Fleet", self.dm.terr[u[2:]])
            pos += self.dumb.value.get(node, 0.0) / vmax
        return config.SEARCH_SC_WEIGHT * sc + config.SEARCH_POS_WEIGHT * pos - config.SEARCH_DISLODGED_WEIGHT * dislodged


def _same(a, b):
    return (a["type"], a["terrID"], a["toTerrID"], a["fromTerrID"]) == (b["type"], b["terrID"], b["toTerrID"], b["fromTerrID"])
