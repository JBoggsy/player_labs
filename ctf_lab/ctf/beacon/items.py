"""Item skills: spawn belief, objective-relative convenience, and contention.

The four pickup families (RULES.md: Grenades / Med kits / Shields / Plasma arc) live at
FIXED spawn points (config mirrors sim.nim's spawn formulas), so the interesting state
is only *is it there right now*. Belief per spawn is optimistic: **present unless we
recently observed the spot empty**, in which case it backs off one respawn interval
(we can't know when it was actually taken, so the earliest it could be back is now +
respawn if it was taken the tick before we looked).

Pickup convenience is the marginal route cost of inserting the item before the bot's
current objective. A settled post gets a tighter allowance; a fresh respawn gets more
latitude for an own-side pickup before rejoining. Visible teammates provide a cheap
contention signal: yield when one has a clearly shorter route.
"""

from __future__ import annotations

import math

from ctf.beacon import mapdata, nav
from ctf.beacon.config import (
    AIM_BRADS_TURN,
    ARC_RESPAWN_TICKS,
    ARC_SPAWNS,
    CENTER_X,
    GRENADE_RESPAWN_TICKS,
    GRENADE_SPAWNS,
    ITEM_ARC_DETOUR_PX,
    ITEM_ASSIGNED_DETOUR_PX,
    ITEM_CONVENIENT_DETOUR_PX,
    ITEM_INCIDENTAL_ROUTE_PX,
    ITEM_PICKUP_RANGE,
    ITEM_POST_DETOUR_PX,
    ITEM_RESPAWN_BONUS_PX,
    ITEM_RESPAWN_INCIDENTAL_ROUTE_PX,
    ITEM_YIELD_MARGIN_PX,
    MEDKIT_CONVENIENT_DETOUR_PX,
    MEDKIT_RESPAWN_TICKS,
    MEDKIT_SPAWNS,
    SHIELD_RESPAWN_TICKS,
    SHIELD_SPAWNS,
    VISION_BUBBLE,
    VISION_CONE_HALF_DEG,
)
from ctf.beacon.types import Belief, CtfState, ItemKind, ItemOption, ItemSpawn, Team

#: A pickup sighting within this distance (px) of a spawn point confirms that spawn.
#: Spawns are "nudged to the nearest walkable floor" by the sim, so allow slack.
_SPAWN_MATCH_PX = 24.0

_RESPAWN_TICKS: dict[ItemKind, int] = {
    "grenade": GRENADE_RESPAWN_TICKS,
    "medkit": MEDKIT_RESPAWN_TICKS,
    "shield": SHIELD_RESPAWN_TICKS,
    "arc": ARC_RESPAWN_TICKS,
}


def build_spawn_table() -> list[ItemSpawn]:
    """All ten fixed spawn points, all initially believed present."""
    out: list[ItemSpawn] = []
    for pos in GRENADE_SPAWNS:
        out.append(ItemSpawn(kind="grenade", pos=pos))
    for pos in SHIELD_SPAWNS:
        out.append(ItemSpawn(kind="shield", pos=pos))
    for pos in ARC_SPAWNS:
        out.append(ItemSpawn(kind="arc", pos=pos))
    for pos in MEDKIT_SPAWNS:
        out.append(ItemSpawn(kind="medkit", pos=pos))
    return out


def _in_view(self_xy: tuple[int, int], aim_brads: int, pos: tuple[int, int]) -> bool:
    """Whether ``pos`` is inside our fog-of-war view: the omni bubble, or the aim
    cone with a wall-clear line (RULES.md: cone rides the aim, walls block)."""
    dx, dy = pos[0] - self_xy[0], pos[1] - self_xy[1]
    dist = math.hypot(dx, dy)
    if dist <= VISION_BUBBLE:
        return True
    want = math.atan2(-dy, dx) / (2 * math.pi) * AIM_BRADS_TURN
    err = abs((want - aim_brads + AIM_BRADS_TURN / 2) % AIM_BRADS_TURN - AIM_BRADS_TURN / 2)
    if err > VISION_CONE_HALF_DEG / 360.0 * AIM_BRADS_TURN:
        return False
    return mapdata.ray_clear(self_xy, pos)


def update_items(belief: Belief, percept: CtfState) -> None:
    """Fold this frame's pickup sightings into the spawn-table belief."""
    if not belief.item_spawns:
        belief.item_spawns = build_spawn_table()
    tick = belief.tick

    # Confirmations: any sighting near a spawn of the same kind marks it present.
    for kind, pos in percept.visible_items:
        for spawn in belief.item_spawns:
            if spawn.kind == kind and math.hypot(
                pos[0] - spawn.pos[0], pos[1] - spawn.pos[1]
            ) <= _SPAWN_MATCH_PX:
                spawn.present = True
                spawn.last_seen = tick
                break

    # Refutations: a spawn we can SEE but got no sighting for is empty right now.
    if belief.alive and belief.self_xy is not None:
        confirmed = {id(s) for s in belief.item_spawns if s.last_seen == tick}
        for spawn in belief.item_spawns:
            if id(spawn) in confirmed:
                continue
            if _in_view(belief.self_xy, belief.aim_brads, spawn.pos):
                spawn.present = False
                spawn.absent_until = tick + _RESPAWN_TICKS[spawn.kind]

    # Back-off expiry: an absent spawn may have refilled; turn optimistic again.
    for spawn in belief.item_spawns:
        if not spawn.present and tick >= spawn.absent_until:
            spawn.present = True


def _our_side(team: Team, pos: tuple[int, int]) -> bool:
    return pos[0] < CENTER_X if team == "red" else pos[0] > CENTER_X


def _already_have(belief: Belief, kind: ItemKind) -> bool:
    return (
        (kind == "grenade" and belief.i_have_grenade)
        or (kind == "shield" and belief.i_have_shield)
        or (kind == "arc" and belief.i_have_arc)
    )


def _legacy_assignment(belief: Belief, spawn: ItemSpawn) -> bool:
    if belief.team is None or not _our_side(belief.team, spawn.pos):
        return False
    if spawn.kind == "shield":
        return belief.seat == 2
    if spawn.kind != "grenade":
        return False
    return (
        (belief.seat == 3 and spawn.pos[1] <= 329)
        or (belief.seat == 4 and spawn.pos[1] > 329)
    )


def _threshold(
    belief: Belief,
    spawn: ItemSpawn,
    *,
    anchor_kind: str,
    respawning: bool,
) -> float:
    threshold = (
        ITEM_POST_DETOUR_PX
        if anchor_kind == "post"
        else ITEM_CONVENIENT_DETOUR_PX
    )
    if (
        anchor_kind != "post"
        and _legacy_assignment(belief, spawn)
    ):
        threshold = max(threshold, ITEM_ASSIGNED_DETOUR_PX)
    if spawn.kind == "arc":
        threshold = min(threshold, ITEM_ARC_DETOUR_PX)
    elif spawn.kind == "medkit" and anchor_kind != "post":
        threshold = MEDKIT_CONVENIENT_DETOUR_PX
    if (
        respawning
        and belief.team is not None
        and spawn.kind == "grenade"
        and not _legacy_assignment(belief, spawn)
        and _our_side(belief.team, spawn.pos)
    ):
        threshold += ITEM_RESPAWN_BONUS_PX
    return float(threshold)


def _closer_visible_teammate(
    belief: Belief,
    spawn: ItemSpawn,
    self_route_px: float,
) -> bool:
    assert belief.self_xy is not None
    for teammate in belief.teammates:
        teammate_route_px = nav.route_distance(teammate.pos, spawn.pos)
        if teammate_route_px + ITEM_YIELD_MARGIN_PX < self_route_px:
            return True
        if (
            abs(teammate_route_px - self_route_px) <= ITEM_YIELD_MARGIN_PX
            and teammate.pos < belief.self_xy
        ):
            # Stable geometric tie-break: when two nearby bots are effectively
            # equidistant, both independently choose the lexicographically
            # smaller position rather than both pursuing or both yielding.
            return True
    return False


def evaluate_fetch(
    belief: Belief,
    anchor: tuple[int, int],
    *,
    anchor_kind: str,
    respawning: bool = False,
    incidental_only: bool = False,
) -> ItemOption | None:
    """Evaluate present pickups by marginal route cost and return the best option."""
    belief.item_options = []
    belief.item_choice = None
    if belief.self_xy is None or not belief.item_spawns:
        return None

    direct_route_px = nav.route_distance(belief.self_xy, anchor)
    for spawn in belief.item_spawns:
        if not spawn.present or _already_have(belief, spawn.kind):
            continue
        if incidental_only and (
            spawn.kind != "grenade"
            or belief.team is None
            or not _our_side(belief.team, spawn.pos)
            or _legacy_assignment(belief, spawn)
        ):
            continue
        if spawn.kind == "medkit" and (
            belief.hp_pips is None or belief.hp_pips >= 3
        ):
            continue
        route_to_item_px = nav.route_distance(belief.self_xy, spawn.pos)
        route_via_item_px = route_to_item_px + nav.route_distance(spawn.pos, anchor)
        detour_px = max(0.0, route_via_item_px - direct_route_px)
        threshold_px = _threshold(
            belief,
            spawn,
            anchor_kind=anchor_kind,
            respawning=respawning,
        )
        incidental_route_limit = (
            ITEM_RESPAWN_INCIDENTAL_ROUTE_PX
            if respawning
            else ITEM_INCIDENTAL_ROUTE_PX
        )
        if incidental_only and route_to_item_px > incidental_route_limit:
            accepted, reason = False, "too_far"
        elif spawn.kind == "shield" and not _legacy_assignment(belief, spawn):
            accepted, reason = False, "tactics_not_ready"
        elif spawn.kind == "arc" and route_to_item_px > ITEM_PICKUP_RANGE:
            accepted, reason = False, "tactics_not_ready"
        elif _closer_visible_teammate(belief, spawn, route_to_item_px):
            accepted, reason = False, "closer_teammate"
        elif detour_px <= threshold_px:
            accepted, reason = True, "convenient"
        else:
            accepted, reason = False, "too_far"
        belief.item_options.append(
            ItemOption(
                spawn=spawn,
                anchor=anchor,
                anchor_kind=anchor_kind,
                route_to_item_px=route_to_item_px,
                route_via_item_px=route_via_item_px,
                direct_route_px=direct_route_px,
                detour_px=detour_px,
                threshold_px=threshold_px,
                accepted=accepted,
                reason=reason,
            )
        )
        belief.item_option_ticks[spawn.kind] = (
            belief.item_option_ticks.get(spawn.kind, 0) + 1
        )
        belief.item_reason_ticks[reason] = belief.item_reason_ticks.get(reason, 0) + 1

    if not belief.item_options:
        return None
    belief.item_opportunity_ticks += 1
    accepted = [option for option in belief.item_options if option.accepted]
    if accepted:
        belief.item_choice = min(
            accepted,
            key=lambda option: (
                option.detour_px,
                option.route_to_item_px,
                option.spawn.kind,
            ),
        )
        belief.item_fetch_ticks += 1
    else:
        belief.item_choice = min(
            belief.item_options,
            key=lambda option: (
                option.detour_px,
                option.route_to_item_px,
                option.spawn.kind,
            ),
        )
        if belief.item_choice.reason == "closer_teammate":
            belief.item_yield_ticks += 1
    return belief.item_choice


def assigned_fetch(belief: Belief) -> ItemSpawn | None:
    """Return v48's single statically assigned own-side pickup for this seat."""
    if belief.team is None or not belief.item_spawns:
        return None
    wanted: tuple[ItemKind, str] | None = {
        2: ("shield", "any"),
        3: ("grenade", "top"),
        4: ("grenade", "bottom"),
    }.get(belief.seat)
    if wanted is None:
        return None
    kind, half = wanted
    if _already_have(belief, kind):
        return None
    for spawn in belief.item_spawns:
        if (
            spawn.kind != kind
            or not _our_side(belief.team, spawn.pos)
            or (half == "top" and spawn.pos[1] > 329)
            or (half == "bottom" and spawn.pos[1] <= 329)
        ):
            continue
        return spawn if spawn.present else None
    return None


def medkit_target(
    belief: Belief,
    max_distance_px: float,
) -> ItemSpawn | None:
    """Return v48's nearest believed-present med kit when hurt."""
    if (
        belief.hp_pips is None
        or belief.hp_pips >= 3
        or belief.self_xy is None
        or not belief.item_spawns
    ):
        return None
    best: ItemSpawn | None = None
    best_distance = max_distance_px
    for spawn in belief.item_spawns:
        if spawn.kind != "medkit" or not spawn.present:
            continue
        distance = math.hypot(
            spawn.pos[0] - belief.self_xy[0],
            spawn.pos[1] - belief.self_xy[1],
        )
        if distance <= best_distance:
            best = spawn
            best_distance = distance
    return best


def arrived(self_xy: tuple[int, int], spawn: ItemSpawn) -> bool:
    return math.hypot(self_xy[0] - spawn.pos[0], self_xy[1] - spawn.pos[1]) <= ITEM_PICKUP_RANGE


__all__ = [
    "arrived",
    "assigned_fetch",
    "build_spawn_table",
    "evaluate_fetch",
    "medkit_target",
    "update_items",
]
