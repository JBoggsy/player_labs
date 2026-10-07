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

from webdip_bot import config, fastadj, search_moves
from webdip_bot.dumbbot import Board, DumbBot
from webdip_bot.evaluation import evaluator
from webdip_bot.opponent_model import opponent_model

# These imports also preserve the search-module API used by Nash and diagnostics.
from webdip_bot.search_orders import _key, adjudicate, dipmap, fast_orders, order_destroy


class SearchBot:
    def __init__(self, variant, board, country, phase, turn, rng):
        self.variant, self.board, self.country, self.phase, self.turn, self.rng = (
            variant, board, country, phase, turn, rng)
        self.dumb = DumbBot(variant, board, country, phase, turn, rng)
        self.b = self.dumb.b
        self.trace = self.dumb.trace
        self.api = self.context = None
        self.memory = {}
        self.evaluator = evaluator(self)
        self.opponent_model = opponent_model(self)

    def observe(self, api, context, state):
        """Called by bot.py each phase; `state` persists across the whole game."""
        self.api, self.context = api, context
        self.memory = state.setdefault("search", {"logodds": {}, "pending": None})

    def _update_beliefs(self):
        return self.opponent_model.update_beliefs()

    def _dumb_share(self, c):
        return self.opponent_model.dumb_share(c)

    def choose(self, slots):
        self.evaluator = evaluator(self)
        self.opponent_model = opponent_model(self)
        if self.phase == "Builds" and slots and config.SEARCH_BUILDS:
            return self._search_adjustments(slots)
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

        opponents, raw_samples = self.opponent_model.sample(slots, mine)
        self.opponents = opponents
        self.sims = 0
        self._prepare_fast(mine, raw_samples)

        return search_moves.choose_movement(self, slots, mine, started)

    def _search_adjustments(self, slots):
        """Winter: pick builds/disbands by a quick search of the following spring.

        Candidates: DumbBot's own choice plus alternatives (other unit types / sites for
        builds, other unit subsets for disbands), capped at SEARCH_BUILD_CANDIDATES. Each is
        applied to a hypothetical board and scored by a reduced SearchBot run for spring.
        """
        import itertools

        started = time.monotonic()
        b = self.b
        own = [u for u in b.units if int(u["countryID"]) == self.country]
        default = self.dumb.choose(slots)
        if b.centers[self.country] < len(own):
            k = len(own) - b.centers[self.country]
            k = min(k, len(slots))
            ranked = sorted(own, key=lambda u: self.dumb.value.get(b.node(u), 0))[: k + 3]
            candidates = [[order_destroy(b, u) for u in combo] for combo in itertools.combinations(ranked, k)]
        else:
            options = b.legal.builds(self.country)
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
                self.trace["build_budget_hit"] += 1
                break
            value = self._spring_value(cand)
            if best_value is None or value > best_value:
                best, best_value = cand, value
        if best is not default:
            self.trace["build_search_changed"] += 1
        self.trace["build_candidates"] += len(candidates)
        # Fill remaining build slots with Wait exactly as DumbBot does.
        if len(best) < len(slots) and best and best[0]["type"] != "Destroy":
            best = best + [{"type": "Wait", "terrID": 0, "toTerrID": 0, "fromTerrID": 0, "viaConvoy": "No"}]
        return best

    def _spring_value(self, adjustments):
        """Static value of the spring after applying `adjustments` (reduced search)."""
        units = [dict(u) for u in self.board["units"] if not u["retreating"]]
        next_id = -1
        for o in adjustments:
            if o["type"] == "Destroy":
                units = [u for u in units if self.b.province(u["terrID"]) != o["toTerrID"]]
            elif o["type"] in ("Build Army", "Build Fleet"):
                units.append({"id": next_id, "countryID": self.country, "terrID": o["toTerrID"],
                              "type": "Army" if o["type"] == "Build Army" else "Fleet", "retreating": False})
                next_id -= 1
        unit_at = {self.b.province(u["terrID"]): u["id"] for u in units}
        terrs = [dict(t, unitID=unit_at.get(t["terrID"])) for t in self.board["territories"]]
        board = {**self.board, "units": units, "territories": terrs}
        saved = {k: getattr(config, k) for k in ("SEARCH_OPPONENT_SAMPLES", "SEARCH_SEEDS", "SEARCH_PASSES",
                                                 "SEARCH_RESTARTS", "SEARCH_ROLLOUT", "SEARCH_BUILDS")}
        config.SEARCH_OPPONENT_SAMPLES, config.SEARCH_SEEDS, config.SEARCH_PASSES = 6, 4, 1
        config.SEARCH_RESTARTS, config.SEARCH_ROLLOUT, config.SEARCH_BUILDS = 1, 0, 0
        try:
            bot = SearchBot(self.variant, board, self.country, "Diplomacy", self.turn + 1, self.rng)
            bot.memory = {"logodds": self.memory.get("logodds", {}), "pending": None}
            mine = [{"unitID": u["id"]} for u in units if int(u["countryID"]) == self.country]
            bot.choose(mine)
            return bot.trace["search_score"]
        finally:
            for k, v in saved.items():
                setattr(config, k, v)

    def _improve_for(self, c, model, units_c, base, j, models, theirs, dumb_samples, mine, our_dumb, legal):
        return self.opponent_model.improve_for(c, model, units_c, base, j, models, theirs, dumb_samples, mine, our_dumb, legal)

    def _diplomacy_adjust(self, projected, me):
        return self.evaluator.diplomacy_adjust(projected, me)

    def _remember(self, score, cand):
        return search_moves.remember(self, score, cand)

    def _ascend(self, best, best_score, started):
        return search_moves.ascend(self, best, best_score, started)

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
        return search_moves.joint_alternatives(self, mine)

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
        return self.evaluator.evaluate(ours)

    def _score_fast(self, fu, fo, units, orders, country=None, value=None, vmax=None):
        return self.evaluator.score_fast(fu, fo, units, orders, country, value, vmax)

    def _adjudicate(self, mine, sample):
        return adjudicate(self, mine, sample)

    def _score(self, g):
        return self.evaluator.score_package(g)
