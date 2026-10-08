"""Standard Diplomacy notation ("A PAR - BUR", "F NTH S A YOR - NWY") for the LLM, and a
board summary. Parsing never guesses: a written order is matched against the unit's legal
orders rendered in the same notation."""

import re

from webdip_bot.dipmap import COUNTRY, POWER


def _norm(text):
    text = text.upper().replace("->", "-").replace("–", "-").replace(" VIA", "")
    text = re.sub(r"\s*-\s*", " - ", text)
    return re.sub(r"\s+", " ", text).strip()


def _no_coast(text):
    return re.sub(r"/[NSEW]C", "", text)


class Notation:
    def __init__(self, board_model, dm):
        self.b = board_model
        self.dm = dm
        self.unit_at = {}
        for u in board_model.units:
            self.unit_at[u["terrID"]] = u
            self.unit_at[board_model.province(u["terrID"])] = u

    def province_abbr(self, terr_id):
        return self.dm.loc[self.b.province(terr_id)]

    def province_id(self, abbr):
        """'GAL' or 'Galicia' -> province terrID, or None."""
        key = _no_coast(abbr.strip().upper())
        terr = self.dm.terr.get(key)
        if terr is None:
            terr = next((t for t, x in self.b.terr.items() if x["name"].upper() == abbr.strip().upper()), None)
        return None if terr is None else self.b.province(terr)

    def render(self, order):
        return self.dm.order(order, self.unit_at)

    def unit_label(self, unit):
        return self.dm.unit(unit)

    def parse(self, text):
        """'A BUD - RUM' -> (unit, webDip order dict). Raises ValueError with a reason."""
        wanted = _norm(text)
        head = wanted.split(" ")
        if len(head) < 3:
            raise ValueError(f"cannot read order {text!r}")
        prov = self.province_id(head[1])
        unit = self.unit_at.get(prov) if prov is not None else None
        if unit is None:
            raise ValueError(f"no unit at {head[1]!r} for order {text!r}")
        legal = self.b.legal.movement(unit)
        for exact in (True, False):
            for o in legal:
                try:
                    shown = _norm(self.render(o))
                except (KeyError, ValueError):
                    continue
                if shown == wanted or (not exact and _no_coast(shown) == _no_coast(wanted)):
                    return unit, o
        raise ValueError(f"{text!r} is not a legal order for {self.unit_label(unit)}")

    def power_name(self, country_id):
        return POWER[int(country_id)]

    def country_id(self, name):
        cid = COUNTRY.get(name.strip().upper())
        if cid is None:
            raise ValueError(f"unknown power {name!r}; use one of {', '.join(POWER.values())}")
        return cid

    def brief(self, me):
        """Plain-text board summary from our side."""
        b = self.b
        lines = []
        neutral = sorted(self.dm.loc[t] for t, o in b.owner.items() if o is None)
        for cid in sorted(POWER):
            centres = sorted(self.dm.loc[t] for t, o in b.owner.items() if o == cid)
            units = sorted(self.unit_label(u) for u in b.units if int(u["countryID"]) == cid)
            if not centres and not units:
                lines.append(f"{POWER[cid]}: eliminated")
                continue
            tag = " (YOU)" if cid == me else ""
            lines.append(f"{POWER[cid]}{tag}: {len(centres)} centres [{' '.join(centres)}]; units: {', '.join(units) or 'none'}")
        lines.append(f"Neutral centres ({len(neutral)}): {' '.join(neutral)}")
        threats = []
        for t, owner in sorted(b.owner.items()):
            if owner != me:
                continue
            enemies = sorted({POWER[int(u["countryID"])] for n in b.reached_by.get(t, ())
                              for u in b.units if b.node(u) == n and int(u["countryID"]) != me})
            if enemies:
                threats.append(f"{self.dm.loc[t]} (reachable by {', '.join(enemies)})")
        lines.append("Your centres within reach of foreign units: " + ("; ".join(threats) or "none"))
        return "\n".join(lines)
