"""Translate between webDiplomacy (terrIDs, order dicts) and the `diplomacy` package
(location abbreviations, order strings) so we can adjudicate hypothetical turns locally.

The mapping is derived from territory NAMES at runtime (webDip variant.json vs the
package's `map.loc_name`), so it cannot drift silently: any unmapped name raises.
"""

import diplomacy

POWER = {1: "ENGLAND", 2: "FRANCE", 3: "ITALY", 4: "GERMANY", 5: "AUSTRIA", 6: "TURKEY", 7: "RUSSIA"}
COUNTRY = {v: k for k, v in POWER.items()}

# webDip spelling -> diplomacy package spelling (upper-cased).
ALIASES = {
    "ST. PETERSBURG": "ST PETERSBURG",
    "ST. PETERSBURG (NORTH COAST)": "ST PETERSBURG (NORTH COAST)",
    "ST. PETERSBURG (SOUTH COAST)": "ST PETERSBURG (SOUTH COAST)",
    "SKAGERRACK": "SKAGERRAK",
    "HELIGOLAND BIGHT": "HELGOLAND BIGHT",
    "GULF OF LYONS": "GULF OF LYON",
    "BULGARIA (NORTH COAST)": "BULGARIA (EAST COAST)",
}

_BASE = None


def base_game():
    global _BASE
    if _BASE is None:
        _BASE = diplomacy.Game()
    return _BASE


class DipMap:
    def __init__(self, territories):
        names = base_game().map.loc_name
        self.loc = {}
        for t in territories:
            n = t["name"].upper()
            n = ALIASES.get(n, n)
            self.loc[t["id"]] = names[n]  # KeyError = a new unmapped spelling; fix ALIASES
        self.terr = {v: k for k, v in self.loc.items()}
        self.base_state = base_game().get_state()

    def unit(self, unit):
        return f'{"A" if unit["type"] == "Army" else "F"} {self.loc[unit["terrID"]]}'

    def state(self, board_units, owners, turn):
        """Package state for a movement phase. `owners`: {province terrID: countryID} for SCs."""
        units = {p: [] for p in POWER.values()}
        for u in board_units:
            if not u["retreating"]:
                units[POWER[int(u["countryID"])]].append(self.unit(u))
        centers = {p: [] for p in POWER.values()}
        for t, c in owners.items():
            if c:
                centers[POWER[c]].append(self.loc[t])
        s = dict(self.base_state)
        s.update(
            units=units,
            centers=centers,
            retreats={p: {} for p in POWER.values()},
            name=f'{"S" if turn % 2 == 0 else "F"}{1901 + turn // 2}M',
        )
        return s

    def order(self, o, unit_at):
        """webDip movement order dict -> package order string. `unit_at`: province terrID -> unit."""
        u = unit_at[o["terrID"]]
        me = self.unit(u)
        kind = o["type"]
        if kind == "Hold":
            return f"{me} H"
        if kind == "Move":
            return f"{me} - {self.loc[o['toTerrID']]}" + (" VIA" if o.get("viaConvoy") in ("Yes", True) else "")
        if kind == "Support hold":
            return f"{me} S {self.unit(unit_at[o['toTerrID']])}"
        if kind == "Support move":
            src = unit_at[o["fromTerrID"]]
            return f"{me} S {self.unit(src)} - {self.loc[o['toTerrID']][:3]}"
        if kind == "Convoy":
            src = unit_at[o["fromTerrID"]]
            return f"{me} C {self.unit(src)} - {self.loc[o['toTerrID']][:3]}"
        raise ValueError(kind)
