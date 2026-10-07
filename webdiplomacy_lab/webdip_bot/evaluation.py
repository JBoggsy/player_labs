"""Position scoring and opponent-sample aggregation, with live config tunables.

Fast and package scores intentionally differ: the package path divides positional
terms individually and does not apply learned blending or diplomacy adjustments.
"""

from webdip_bot import config, fastadj, valuefn
from webdip_bot.dipmap import POWER
from webdip_bot.search_orders import adjudicate, fast_orders

_GRAPHS = {}


def _graph(variant):
    key = variant["variantID"]
    if key not in _GRAPHS:
        _GRAPHS[key] = valuefn.Graph(variant)
    return _GRAPHS[key]


class PositionEvaluator:
    def __init__(self, bot):
        self.bot = bot

    def evaluate(self, ours):
        bot = self.bot
        mu, mo = fast_orders(bot.mine_units, ours, bot.parent)
        values = []
        mine_dip = None
        for k, (units, fu, fo, raw) in enumerate(bot.fast_samples):
            if mo is not None and fo is not None and config.SEARCH_FAST_ADJ:
                values.append(self.score_fast(mu + fu, mo + fo, bot.mine_units + units, ours + raw))
                bot.sims += 1
            else:
                if mine_dip is None:
                    mine_dip = [bot.dm.order(o, bot.unit_at) for o in ours]
                values.append(self.score_package(adjudicate(bot, mine_dip, bot.opponents[k])))
                bot.trace["search_package_sims"] += 1
        mean = sum(values) / len(values)
        # Risk aversion: pull the mean toward the worst opponent sample.
        return mean - config.SEARCH_RISK * (mean - min(values))

    def score_fast(self, fu, fo, units, orders, country=None, value=None, vmax=None):
        """Static evaluation of an adjudicated outcome from `country`'s side (default: us)."""
        bot = self.bot
        me = bot.country if country is None else country
        value = bot.dumb.value if value is None else value
        vmax = bot.vmax if vmax is None else vmax
        moved, dislodged = fastadj.adjudicate(fu, fo)
        occupied = {}
        my_nodes = []
        lost = 0
        for (country, prov, utype), o, mv, dl, u, raw in zip(fu, fo, moved, dislodged, units, orders):
            if dl:
                lost += country == me
                continue
            where = o[1] if mv else prov
            occupied[where] = country
            if country == me:
                my_nodes.append((utype, raw["toTerrID"] if mv else u["terrID"]))
        counts = {}
        projected = {}
        for t, owner in bot.b.owner.items():
            holder = occupied.get(t, owner)
            projected[t] = holder
            if holder:
                counts[holder] = counts.get(holder, 0) + 1
        sc = counts.get(me, 0)
        if config.DIPLO and me == bot.country:
            sc += self.diplomacy_adjust(projected, me)
        sc = self.center_value(sc, fu, fo, moved, dislodged, units, orders, projected, me)
        if config.SEARCH_OBJECTIVE == "share":
            total = sum(v * v for v in counts.values()) or 1
            sc = 34.0 * sc * sc / total
        pos = sum(value.get(n, 0.0) for n in my_nodes) / vmax
        return config.SEARCH_SC_WEIGHT * sc + config.SEARCH_POS_WEIGHT * pos - config.SEARCH_DISLODGED_WEIGHT * lost

    def score_package(self, g):
        bot = self.bot
        me = POWER[bot.country]
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
        for t, owner in bot.b.owner.items():
            occ = occupied.get(bot.dm.loc[t])
            holder = occ if occ is not None else (POWER[owner] if owner else None)
            if holder:
                counts[holder] = counts.get(holder, 0) + 1
        sc = counts.get(me, 0)
        if config.SEARCH_OBJECTIVE == "share":
            # The league's draw score: SC^2 / sum SC^2, scaled to SC units (x34).
            total = sum(v * v for v in counts.values()) or 1
            sc = 34.0 * sc * sc / total
        pos = 0.0
        vmax = max(bot.dumb.value.values()) or 1.0
        for u in mine:
            node = ("Army" if u[0] == "A" else "Fleet", bot.dm.terr[u[2:]])
            pos += bot.dumb.value.get(node, 0.0) / vmax
        return config.SEARCH_SC_WEIGHT * sc + config.SEARCH_POS_WEIGHT * pos - config.SEARCH_DISLODGED_WEIGHT * dislodged

    def diplomacy_adjust(self, projected, me):
        """Implicit diplomacy: centres taken from a power count more if it has been hostile to
        us (grudge) and less if it has left us alone (peace), until DIPLO_STAB_YEAR."""
        bot = self.bot
        hostility = bot.memory.get("hostility", {})
        year = 1901 + bot.turn // 2
        adj = 0.0
        for t, holder in projected.items():
            if holder != me:
                continue
            prev = bot.b.owner.get(t)
            if not prev or prev == me:
                continue
            h = hostility.get(str(prev), 0.0)
            if h >= config.DIPLO_HOSTILE:
                adj += config.DIPLO_GRUDGE
            elif year < config.DIPLO_STAB_YEAR:
                adj -= config.DIPLO_PEACE
        bot.trace["diplo_evals"] += 1
        return adj

    def center_value(self, sc, fu, fo, moved, dislodged, units, orders, projected, me):
        return sc


class LearnedEvaluator(PositionEvaluator):
    def center_value(self, sc, fu, fo, moved, dislodged, units, orders, projected, me):
        bot = self.bot
        final_units = []
        for (country, prov, utype), o, mv, dl, u, raw in zip(fu, fo, moved, dislodged, units, orders):
            if not dl:
                final_units.append((country, o[1] if mv else prov, utype, raw["toTerrID"] if mv else u["terrID"]))
        predicted = valuefn.predict(_graph(bot.variant), final_units, projected, me)
        w = config.SEARCH_LEARNED_WEIGHT
        sc = (1 - w) * sc + w * predicted
        return sc


EVALUATORS = {"projected": PositionEvaluator, "learned": LearnedEvaluator}


def evaluator(bot):
    # Historically every value other than "learned" selected projected scoring.
    return EVALUATORS.get(config.SEARCH_EVAL, PositionEvaluator)(bot)
