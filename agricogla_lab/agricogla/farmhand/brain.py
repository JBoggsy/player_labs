"""farmhand decision logic — a PARAMS-weighted scorer over the agricogla view.

Pure and stateless per turn: ``Brain.decide(view, seat, rejected)`` returns a
``cogweb.player.v1`` agricogla decision (a work placement or a feeding plan). The
cogweb bridge owns the wire envelope; this module only maps a redacted ``view`` to
a legal ``decision``.

The scorer ports the prior heuristic's strategy onto the real view schema:
food-safety first, room-before-grow, grow-only-with-a-food-engine, breadth (flip
−1 categories), sow-before-bake. The weights live in PARAMS so the beam loop can
tune them. On a rejected move (our legality model disagreed with the host) we drop
to an always-legal no-arg placement rather than re-guess.

View schema (cogweb.player.v1 agricogla, verified vs the reference player):
- view["players"][seat]: {resources, animals, family[], spaces[], houseMaterial, majors[], minors[]}
- view["actionSpaces"]: [{id, occupiedBy, pile?}]
- view["round"], view["phase"] ("work" | "feeding"), view["majorsAvailable"]
- a space: {kind: "room"|"field"|"empty", crop?, cropCount?, stable?}
"""

from __future__ import annotations

from typing import Any

HARVEST_ROUNDS = {4, 7, 9, 11, 13, 14}
COOKERS = ("fireplace2", "fireplace3", "hearth4", "hearth5")

# Always-schema-legal no-arg placements on a free space (fallback order).
SAFE_NOARG = (
    "day_laborer", "fishing", "forest", "clay_pit", "reed_bank", "grain_seeds",
    "grove", "copse", "hollow", "resource_market", "traveling_players",
    "r_sheep", "r_boar", "r_cattle", "r_vegetable", "quarry_stall",
    "r_west_quarry", "r_east_quarry",
)


def _next_harvest_in(rnd: int) -> int:
    for h in sorted(HARVEST_ROUNDS):
        if h >= rnd:
            return h - rnd
    return 99


class Brain:
    def __init__(self, params: dict[str, float]) -> None:
        self.p = params

    # -- public entry ---------------------------------------------------------

    def decide(self, view: dict, seat: int, rejected: bool) -> dict:
        me = view["players"][seat]
        free = {s["id"] for s in view["actionSpaces"] if s.get("occupiedBy") is None}
        if view.get("phase") == "feeding":
            return self._feed(view, me)
        if rejected:
            return self._fallback(free)
        return self._work(view, me, free) or self._fallback(free)

    # -- work phase: score every free space, take the best -------------------

    def _work(self, view: dict, me: dict, free: set[str]) -> dict | None:
        rnd = view["round"]
        urgency = self._food_urgency(view, me)
        ctx = _Ctx(view, me, free, rnd, urgency, self.p)
        best_score = float("-inf")
        best_decision: dict | None = None
        for sid in free:
            score = ctx.score(sid)
            if score > best_score:
                built = ctx.build(sid)
                if built is not None:
                    best_score, best_decision = score, built
        return best_decision

    def _fallback(self, free: set[str]) -> dict:
        for sid in SAFE_NOARG:
            if sid in free:
                return {"action": sid}
        return {"action": next(iter(free))} if free else {"action": "day_laborer"}

    # -- feeding phase --------------------------------------------------------

    def _feed(self, view: dict, me: dict) -> dict:
        needed = self._food_needed(view, me)
        res = me.get("resources", {})
        have = res.get("food", 0)
        conversions: list[dict] = []
        # Raw crops convert 1:1; cook animals if we have a cooker (best rate first).
        for good in ("grain", "vegetable"):
            if have >= needed:
                break
            take = min(needed - have, res.get(good, 0))
            if take > 0:
                conversions.append({"via": "raw", "good": good, "count": take})
                have += take
        return {"conversions": conversions}

    # -- food model -----------------------------------------------------------

    def _food_needed(self, view: dict, me: dict) -> int:
        return len(me.get("family", [])) * 2

    def _convertible_food(self, me: dict) -> int:
        res = me.get("resources", {})
        food = res.get("food", 0) + res.get("grain", 0) + res.get("vegetable", 0)
        if any(c in me.get("majors", []) for c in COOKERS):
            a = me.get("animals", {})
            food += a.get("sheep", 0) * 2 + a.get("boar", 0) * 2 + a.get("cattle", 0) * 3
        return food

    def _food_urgency(self, view: dict, me: dict) -> int:
        harvest_in = _next_harvest_in(view["round"])
        if harvest_in > 3:
            return 0
        deficit = self._food_needed(view, me) - self._convertible_food(me)
        if deficit <= 0:
            return 0
        if harvest_in == 0:
            return 4
        return min(4, max(1, deficit // 2 + (3 - harvest_in)))


class _Ctx:
    """Per-turn scoring context. Mirrors the prior evaluate_action weights, keyed
    off PARAMS, over the real view fields."""

    def __init__(self, view, me, free, rnd, urgency, params):
        self.view, self.me, self.free = view, me, free
        self.rnd, self.urgency, self.p = rnd, urgency, params
        res = me.get("resources", {})
        self.res = res
        self.spaces = me.get("spaces", [])
        self.family = len(me.get("family", []))
        self.rooms = sum(1 for s in self.spaces if s.get("kind") == "room")
        self.fields = sum(1 for s in self.spaces if s.get("kind") == "field")
        self.house = me.get("houseMaterial", "wood")
        self.has_cooker = any(c in me.get("majors", []) for c in COOKERS)
        self.animals = me.get("animals", {})
        self.gaps = self._gaps()
        self.piles = {s["id"]: sum((s.get("pile") or {}).values())
                      for s in view["actionSpaces"]}

    def _gaps(self) -> set[str]:
        g = set()
        if self.fields < 2:
            g.add("fields")
        if self.res.get("grain", 0) + self._sown("grain") < 1:
            g.add("grain")
        if self.res.get("vegetable", 0) + self._sown("vegetable") < 1:
            g.add("vegetables")
        for a in ("sheep", "boar", "cattle"):
            if self.animals.get(a, 0) < 1:
                g.add(a)
        return g

    def _sown(self, crop: str) -> int:
        return sum(s.get("cropCount", 0) for s in self.spaces if s.get("crop") == crop)

    def _can_feed_a_grow(self) -> bool:
        # Don't grow without a real food engine (cooker + fields) — uncosted growth
        # is the #1 way to lose (STRATEGY §1.2).
        return self.has_cooker and self.fields >= 2

    def score(self, sid: str) -> float:
        p, pile = self.p, self.piles.get(sid, 0)
        if sid == "r_family_growth":
            if not self._can_feed_a_grow() or self.family >= 5 or self.rooms <= self.family:
                return -100.0
            return p["grow_safe"] if self.urgency <= 1 else p["grow_base"] - self.urgency * p["grow_urgency_penalty"]
        if sid == "r_urgent_family":
            if not self._can_feed_a_grow() or self.family >= 5:
                return -100.0
            return p["urgent_grow_safe"] if self.urgency <= 2 else p["urgent_grow_risky"]
        if sid == "farm_expansion":
            if self._room_cell() is not None and self.res.get(self.house, 0) >= 5 and self.res.get("reed", 0) >= 2:
                if self.rooms <= self.family:
                    return p["room_housebound"]
                if self.rnd <= 7:
                    return p["room_ahead"]
            return 2.0
        if sid == "r_improvement":
            return p["cooker_critical"] + self.urgency * p["cooker_urgency"] if not self.has_cooker else 15.0
        if sid == "r_renovate_improve":
            if not self.has_cooker:
                return p["renovate_cooker"] + self.urgency * 3
            return 25.0 if self.rnd >= 9 else 12.0
        if sid == "day_laborer":
            return p["day_laborer_base"] + self.urgency * p["day_laborer_urgency"]
        if sid == "fishing":
            return pile * (1.5 + self.urgency * p["fishing_urgency"])
        if sid == "forest":
            need = p["wood_need_growth"] if (self.rooms <= self.family and self.rnd <= 8) else p["wood_need_base"]
            return pile * min(3.5, need)
        if sid in ("copse", "grove"):
            return pile * (2.8 if sid == "grove" else 2.5)
        if sid in ("clay_pit", "hollow"):
            need = 3.0 if (not self.has_cooker and self.res.get("clay", 0) < 3) else 1.5
            return pile * need
        if sid == "reed_bank":
            return pile * 2.5
        if sid in ("r_west_quarry", "r_east_quarry"):
            return pile * 3.0
        if sid == "resource_market":
            return 8.0 + self.urgency * 2
        if sid == "traveling_players":
            return pile * (1.5 + self.urgency * 1.5)
        if sid == "farmland":
            if self.fields < 2:
                return p["field_first"]
            return p["field_gap"] if (self.fields < 5 and "fields" in self.gaps) else 8.0
        if sid == "grain_seeds":
            return 18.0 if (self.res.get("grain", 0) == 0 and "grain" in self.gaps) else 9.0
        if sid == "r_vegetable":
            return p["veg_gap"] if "vegetables" in self.gaps else 10.0
        if sid == "r_sow_bake":
            return 20.0 + (p["sow_per_field"] if self._empty_field() is not None else 0)
        if sid in ("r_sheep", "r_boar", "r_cattle"):
            kind = {"r_sheep": "sheep", "r_boar": "boar", "r_cattle": "cattle"}[sid]
            mult = {"r_sheep": 4.0, "r_boar": 4.5, "r_cattle": 5.0}[sid]
            breed = p["animal_breed_bonus"] if (self.animals.get(kind, 0) >= 1 and pile >= 1) else 0
            cat = p["animal_category_bonus"] if kind in self.gaps else 0
            return pile * mult + breed + cat
        if sid in ("lessons", "lessons_b"):
            return p["occupation_early"] if self.rnd <= 8 else p["occupation_late"]
        if sid == "r_redevelop":
            return p["redevelop_late"] if (self.rnd >= 12 and self.house != "stone") else 8.0
        base = 1.0
        if self.rnd >= p["late_fill_round"] and sid in ("r_fences", "farm_expansion", "farmland"):
            base += min(p["late_fill_cap"], 5.0)
        return base

    # -- decision builders (fill required args; return None if not buildable) --

    def build(self, sid: str) -> dict | None:
        if sid == "farm_expansion":
            cell = self._room_cell()
            return {"action": sid, "rooms": [cell], "stables": []} if cell is not None else None
        if sid == "farmland":
            cell = self._field_cell()
            return {"action": sid, "spaces": [cell]} if cell is not None else None
        if sid == "r_sow_bake":
            f = self._empty_field()
            return {"action": sid, "sow": [{"space": f, "crop": "grain"}], "bake": []} if f is not None else {"action": sid, "sow": [], "bake": []}
        if sid == "r_improvement":
            cooker = self._affordable_cooker()
            if not self.has_cooker and cooker:
                return {"action": sid, "improvement": {"kind": "major", "card": cooker}}
            return None  # nothing useful to buy -> let another space win
        return {"action": sid}

    def _room_cell(self) -> int | None:
        return next((i for i, s in enumerate(self.spaces) if s.get("kind") == "empty" and not s.get("stable")), None)

    def _field_cell(self) -> int | None:
        return next((i for i, s in enumerate(self.spaces) if s.get("kind") == "empty" and not s.get("stable")), None)

    def _empty_field(self) -> int | None:
        return next((i for i, s in enumerate(self.spaces) if s.get("kind") == "field" and s.get("cropCount", 0) == 0), None)

    def _affordable_cooker(self) -> str | None:
        avail = set(self.view.get("majorsAvailable", []))
        clay = self.res.get("clay", 0)
        return next((c for c, cost in (("fireplace2", 2), ("fireplace3", 3)) if c in avail and clay >= cost), None)
