"""Synthesize the `choices`/`options`/obs that v1_logic expects from a raw cogweb view.

v1's proven logic depends on a server-provided legal-move layer (familyGrowthOk,
legalRooms, conversionOptions, foodNeededNow, ...) that the OLD coworld protocol
fed it. cogweb.player.v1 provides NONE of that — only raw state. This adapter
recomputes that layer from raw state, so farmhand can DELEGATE to v1_logic and run
v1's exact decisions (ending the reimplementation parity whack-a-mole).

Coverage: the high-impact fields that drive the dominant decisions (growth, rooms,
sowing, feeding, cards). Complex geometry (fencePlans) defaults empty for now — the
policy simply won't use that path until it's refined; everything else matches v1.
"""

from __future__ import annotations

from typing import Any

HARVEST_ROUNDS = {4, 7, 9, 11, 13, 14}
COOKERS = {  # cooker id -> per-animal food (sheep, boar, cattle)
    "hearth4": (2, 3, 4), "hearth5": (2, 3, 4), "stone_oven": (2, 3, 4),
    "clay_oven": (2, 2, 3), "fireplace2": (2, 2, 3), "fireplace3": (2, 2, 3),
    "field_cook": (2, 2, 3),
}

# Major-improvement build costs (the standard Agricola set). Used to compute the
# `affordable` flag v1 expects on each major. Cookers are the strategically
# critical ones; others get a best-effort cost (well/joinery/pottery/basketmaker).
MAJOR_COST = {
    "fireplace2": {"clay": 2}, "fireplace3": {"clay": 3},
    "hearth4": {"clay": 4}, "hearth5": {"clay": 5},
    "clay_oven": {"clay": 3, "stone": 1}, "stone_oven": {"clay": 1, "stone": 3},
    "well": {"wood": 1, "stone": 3}, "joinery": {"wood": 2, "stone": 2},
    "pottery": {"clay": 2, "stone": 2}, "basketmaker": {"reed": 2, "stone": 2},
}


def _affordable(res: dict, cost: dict) -> bool:
    return all(res.get(k, 0) >= v for k, v in cost.items())


def _empty_cells(spaces: list[dict]) -> list[int]:
    return [i for i, s in enumerate(spaces)
            if s.get("kind") == "empty" and not s.get("stable")]


def _food_needed(me: dict) -> int:
    return len(me.get("family", [])) * 2


def synth_choices(view: dict, me: dict) -> dict:
    """Build the `choices` dict v1_logic reads, from raw cogweb state."""
    spaces = me.get("spaces", [])
    res = me.get("resources", {})
    animals = me.get("animals", {})
    rooms = sum(1 for s in spaces if s.get("kind") == "room")
    family = len(me.get("family", []))
    house = me.get("houseMaterial", "wood")
    empties = _empty_cells(spaces)
    fields = [i for i, s in enumerate(spaces) if s.get("kind") == "field"]

    # Growth legality: need rooms > family (a spare bed) and family < 5.
    family_growth_ok = rooms > family and family < 5
    urgent_growth_ok = family < 5  # urgent family ignores the room requirement

    # Room build cost (wood hut → next room): 5 of house material + 2 reed.
    room_cost = {house: 5, "reed": 2}
    legal_rooms = empties if (res.get(house, 0) >= 5 and res.get("reed", 0) >= 2) else []
    legal_stables = empties if res.get("wood", 0) >= 2 else []

    # legalFields = empty non-stable cells you can PLOW into a new field (what
    # the `farmland` placement's `spaces` arg needs). Distinct from sowableFields
    # (existing empty fields ready to SOW). Conflating these dropped the spaces
    # arg and got every farmland move rejected ("spaces Required").
    legal_fields = empties
    # Sowable: empty fields (no crop growing) — for r_sow_bake.
    sowable = [i for i in fields if (spaces[i].get("cropCount", 0) == 0)]

    # Conversion options for feeding: raw grain/veg (1:1) + animals via best cooker.
    conv: list[dict] = []
    if res.get("grain", 0) > 0:
        conv.append({"via": "raw", "good": "grain", "max": res["grain"], "foodEach": 1})
    if res.get("vegetable", 0) > 0:
        conv.append({"via": "raw", "good": "vegetable", "max": res["vegetable"], "foodEach": 1})
    owned = set(me.get("majors", []) + me.get("minors", []) + me.get("occupations", []))
    cooker = next((c for c in ("hearth5", "hearth4", "stone_oven", "clay_oven",
                               "fireplace3", "fireplace2", "field_cook") if c in owned), None)
    if cooker:
        sh, bo, ca = COOKERS[cooker]
        for good, per in (("sheep", sh), ("boar", bo), ("cattle", ca)):
            if animals.get(good, 0) > 0:
                conv.append({"via": cooker, "good": good, "max": animals[good], "foodEach": per})

    return {
        "familyGrowthOk": family_growth_ok,
        "urgentGrowthOk": urgent_growth_ok,
        "legalRooms": legal_rooms,
        "legalStables": legal_stables,
        "roomCost": room_cost,
        "legalFields": legal_fields,
        "sowableFields": sowable,
        "bakeOptions": [],            # baking via ovens — refine later
        "conversionOptions": conv,
        "foodNeededNow": max(0, _food_needed(me) - res.get("food", 0)),
        "fencePlans": [],             # geometry — refine later; policy skips this path
        # v1 treats hand cards as dicts ({id, affordable}); cogweb gives id strings.
        "handOccupations": [{"id": c, "affordable": False} if isinstance(c, str) else c
                            for c in me.get("handOccupations", [])],
        "handMinors": [{"id": c, "affordable": False} if isinstance(c, str) else c
                       for c in me.get("handMinors", [])],
        "occupationCostBySpace": {},  # refine later
        # v1 expects major ENTRIES as dicts {id, affordable, prereqOk, cost}; the
        # cogweb view only gives id strings, so synthesize them with affordability.
        "majors": [
            {"id": mid, "cost": MAJOR_COST.get(mid, {}),
             "affordable": _affordable(res, MAJOR_COST.get(mid, {"__none__": 1})),
             "prereqOk": True}
            for mid in view.get("majorsAvailable", [])
        ],
    }


def synth_obs(view: dict, seat: int) -> dict:
    """Build the obs dict v1_logic's pick_best_action/decide_feeding expect."""
    me = view["players"][seat]
    # v1 reads obs["options"] as the action spaces with id/available/pile.
    options = [{"id": s["id"], "available": s.get("occupiedBy") is None,
                "pile": s.get("pile", {})} for s in view.get("actionSpaces", [])]
    return {
        "state": view,          # v1 reads obs["state"]["round"], ["players"][slot], etc.
        "slot": seat,
        "options": options,
        "choices": synth_choices(view, me),
    }
