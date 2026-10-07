"""NashBot: regret matching over candidate plans for all seven powers (SearchBot-style).

Idea from FAIR's SearchBot (Gray et al., ICLR 2021): instead of best-responding to a
fixed opponent model, approximate an equilibrium of the one-phase game restricted to a
few candidate order sets per power, then play the best response to the opponents'
average (equilibrium) strategies.

Movement phases only; everything else delegates to SearchBot (DumbBot for retreats,
optional build search).
1. Candidates: for each power, NASH_CANDIDATES distinct DumbBot samples; for us, also
   SearchBot's own best order set (computed by the parent class).
2. Regret matching for NASH_ITERS iterations: sample a joint action from current
   strategies; for every power and every one of its candidates, adjudicate (fastadj) the
   joint action with that candidate swapped in and score it from that power's side;
   accumulate regrets. Strategies = positive-regret matching; keep running averages.
3. Our play: the candidate with the highest expected utility against opponents' average
   strategies (sampled NASH_EVAL_SAMPLES times).
"""

import time

from webdip_bot import config, fastadj
from webdip_bot.dumbbot import DumbBot
from webdip_bot.search import SearchBot, _key, fast_orders


class NashBot(SearchBot):
    def choose(self, slots):
        if self.phase != "Diplomacy" or not slots:
            return super().choose(slots)
        started = time.monotonic()
        b = self.b
        by_id = {u["id"]: u for u in b.all_units}
        mine = [by_id[s["unitID"]] for s in slots]
        # Our strongest single plan from the regular search (best response to DumbBot samples).
        searched = super().choose(slots)
        # The parent counted its chosen orders into the trace; drop those so the order-type
        # counters reflect only what NashBot finally plays.
        for o in searched:
            self.trace[o["type"]] -= 1
        self.parent = {t: b.province(t) for t in b.terr}

        powers = sorted({int(u["countryID"]) for u in b.units})
        units_of = {c: [u for u in b.units if int(u["countryID"]) == c] for c in powers}
        units_of[self.country] = mine
        models = {c: DumbBot(self.variant, self.board, c, self.phase, self.turn, self.rng, board_model=b) for c in powers}
        cands = {}
        for c in powers:
            seen, plans = set(), []
            if c == self.country:
                plans.append(searched)
                seen.add(tuple(_key(o) for o in searched))
            for _ in range(config.NASH_CANDIDATES * 3):
                if len(plans) >= config.NASH_CANDIDATES:
                    break
                p = models[c].choose([{"unitID": u["id"]} for u in units_of[c]])
                k = tuple(_key(o) for o in p)
                if k not in seen:
                    seen.add(k)
                    plans.append(p)
            cands[c] = plans
        values = {c: models[c].value for c in powers}
        vmax = {c: (max(values[c].values()) or 1.0) for c in powers}

        regrets = {c: [0.0] * len(cands[c]) for c in powers}
        avg = {c: [0.0] * len(cands[c]) for c in powers}

        def strategy(c):
            pos = [max(r, 0.0) for r in regrets[c]]
            total = sum(pos)
            return [p / total for p in pos] if total > 0 else [1.0 / len(pos)] * len(pos)

        def utilities(joint):
            """Adjudicate a joint action {power: candidate index}; return {power: utility}."""
            units, orders = [], []
            for c in powers:
                units.extend(units_of[c])
                orders.extend(cands[c][joint[c]])
            fu, fo = fast_orders(units, orders, self.parent)
            if fo is None:
                return None
            moved, dislodged = fastadj.adjudicate(fu, fo)
            self.sims += 1
            occupied, nodes, lost = {}, {c: [] for c in powers}, {c: 0 for c in powers}
            for (country, prov, utype), o, mv, dl, u, raw in zip(fu, fo, moved, dislodged, units, orders):
                if dl:
                    lost[country] += 1
                    continue
                occupied[o[1] if mv else prov] = country
                nodes[country].append((utype, raw["toTerrID"] if mv else u["terrID"]))
            counts = {}
            for t, owner in b.owner.items():
                holder = occupied.get(t, owner)
                if holder:
                    counts[holder] = counts.get(holder, 0) + 1
            total_sq = sum(v * v for v in counts.values()) or 1
            out = {}
            for c in powers:
                sc = counts.get(c, 0)
                if config.SEARCH_OBJECTIVE == "share":
                    sc = 34.0 * sc * sc / total_sq
                pos = sum(values[c].get(n, 0.0) for n in nodes[c]) / vmax[c]
                out[c] = config.SEARCH_SC_WEIGHT * sc + config.SEARCH_POS_WEIGHT * pos - config.SEARCH_DISLODGED_WEIGHT * lost[c]
            return out

        iters = 0
        for _ in range(config.NASH_ITERS):
            if time.monotonic() - started > config.SEARCH_TIME_BUDGET_S:
                self.trace["nash_budget_hit"] += 1
                break
            strat = {c: strategy(c) for c in powers}
            joint = {c: self.rng.choices(range(len(cands[c])), weights=strat[c])[0] for c in powers}
            base = utilities(joint)
            if base is None:
                continue
            for c in powers:
                for k in range(len(cands[c])):
                    if k == joint[c]:
                        u = base[c]
                    else:
                        alt = utilities({**joint, c: k})
                        if alt is None:
                            continue
                        u = alt[c]
                    regrets[c][k] += u - base[c]
                for k, p in enumerate(strat[c]):
                    avg[c][k] += p
            iters += 1

        # Best response to opponents' average strategies.
        norm = {c: [a / max(sum(avg[c]), 1e-9) for a in avg[c]] for c in powers}
        expected = [0.0] * len(cands[self.country])
        n = config.NASH_EVAL_SAMPLES
        for _ in range(n):
            joint = {c: self.rng.choices(range(len(cands[c])), weights=norm[c] if sum(norm[c]) > 0 else None)[0]
                     for c in powers if c != self.country}
            for k in range(len(cands[self.country])):
                u = utilities({**joint, self.country: k})
                if u is not None:
                    expected[k] += u[self.country] / n
        best = max(range(len(expected)), key=lambda k: expected[k])
        self.trace["nash_iters"] += iters
        self.trace["nash_choice_is_search"] += int(best == 0)
        self.trace["nash_ms"] = round((time.monotonic() - started) * 1000)
        chosen = cands[self.country][best]
        return [self.dumb._legal_or_hold(u, o) for u, o in zip(mine, chosen)]
