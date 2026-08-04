"""Item skills: DISCOVERED spawn belief plus objective-relative convenience.

Beacon compiled the arena's ten fixed spawn points in; Paintbot's generator
places items per map (med kits from the terrain pass; per-team shield/spray
pickups near endzones; grenades at corners/edge-midpoints depending on layout),
so the spawn table starts EMPTY and grows from sightings: the first sighting of
a pickup registers a permanent spawn point for the episode (items respawn in
place). Belief per discovered spawn stays optimistic — present unless we
recently observed the spot empty, backing off one respawn interval.

The seat-based fixed assignments (beacon's ``assigned_fetch``) are gone: with
unknown spawn layouts there is nothing to statically assign. Pickup convenience
is the marginal route cost of inserting the item before the current objective;
visible teammates provide a cheap contention signal.
"""

from __future__ import annotations

import math

from paintbot.stencil import nav
from paintbot.stencil.config import (
    AIM_BRADS_TURN,
    ARC_RESPAWN_TICKS,
    GRENADE_RESPAWN_TICKS,
    ITEM_ARC_DETOUR_PX,
    ITEM_CONVENIENT_DETOUR_PX,
    ITEM_PICKUP_RANGE,
    ITEM_YIELD_MARGIN_PX,
    MEDKIT_CONVENIENT_DETOUR_PX,
    MEDKIT_RESPAWN_TICKS,
    SHIELD_RESPAWN_TICKS,
    VISION_BUBBLE,
    VISION_CONE_HALF_DEG,
)
from paintbot.stencil.types import Belief, ItemKind, ItemOption, ItemSpawn, PaintState

#: A pickup sighting within this distance (px) of a known spawn refreshes it
#: rather than registering a new one (the sim nudges spawns to walkable floor).
_SPAWN_MATCH_PX = 24.0

_RESPAWN_TICKS: dict[ItemKind, int] = {
    "grenade": GRENADE_RESPAWN_TICKS,
    "medkit": MEDKIT_RESPAWN_TICKS,
    "shield": SHIELD_RESPAWN_TICKS,
    "arc": ARC_RESPAWN_TICKS,
}


def _in_view(belief: Belief, pos: tuple[int, int]) -> bool:
    """Whether ``pos`` is inside our fog-of-war view: the omni bubble, or the aim
    cone with a wall-clear line."""
    assert belief.self_xy is not None and belief.worldmap is not None
    dx, dy = pos[0] - belief.self_xy[0], pos[1] - belief.self_xy[1]
    dist = math.hypot(dx, dy)
    if dist <= VISION_BUBBLE:
        return True
    want = math.atan2(-dy, dx) / (2 * math.pi) * AIM_BRADS_TURN
    err = abs(
        (want - belief.aim_brads + AIM_BRADS_TURN / 2) % AIM_BRADS_TURN
        - AIM_BRADS_TURN / 2
    )
    if err > VISION_CONE_HALF_DEG / 360.0 * AIM_BRADS_TURN:
        return False
    return belief.worldmap.ray_clear(belief.self_xy, pos)


def update_items(belief: Belief, percept: PaintState) -> None:
    """Fold this frame's pickup sightings into the discovered spawn table."""
    tick = belief.tick

    # Discoveries + confirmations: a sighting near a known spawn of the same
    # kind refreshes it; anywhere else it registers a new spawn point.
    for kind, pos in percept.visible_items:
        matched = False
        for spawn in belief.item_spawns:
            if spawn.kind == kind and math.hypot(
                pos[0] - spawn.pos[0], pos[1] - spawn.pos[1]
            ) <= _SPAWN_MATCH_PX:
                spawn.present = True
                spawn.last_seen = tick
                matched = True
                break
        if not matched:
            belief.item_spawns.append(
                ItemSpawn(kind=kind, pos=pos, present=True, last_seen=tick)
            )

    # Refutations: a spawn we can SEE but got no sighting for is empty right now.
    if belief.alive and belief.self_xy is not None and belief.worldmap is not None:
        confirmed = {id(s) for s in belief.item_spawns if s.last_seen == tick}
        for spawn in belief.item_spawns:
            if id(spawn) in confirmed:
                continue
            if _in_view(belief, spawn.pos):
                spawn.present = False
                spawn.absent_until = tick + _RESPAWN_TICKS[spawn.kind]

    # Back-off expiry: an absent spawn may have refilled; turn optimistic again.
    for spawn in belief.item_spawns:
        if not spawn.present and tick >= spawn.absent_until:
            spawn.present = True


def _already_have(belief: Belief, kind: ItemKind) -> bool:
    return (
        (kind == "grenade" and belief.i_have_grenade)
        or (kind == "shield" and belief.i_have_shield)
        or (kind == "arc" and belief.i_have_arc)
    )


def _threshold(spawn: ItemSpawn) -> float:
    if spawn.kind == "arc":
        return float(ITEM_ARC_DETOUR_PX)
    if spawn.kind == "medkit":
        return float(MEDKIT_CONVENIENT_DETOUR_PX)
    return float(ITEM_CONVENIENT_DETOUR_PX)


def _closer_visible_teammate(
    belief: Belief,
    spawn: ItemSpawn,
    self_route_px: float,
) -> bool:
    assert belief.self_xy is not None and belief.worldmap is not None
    for teammate in belief.teammates:
        teammate_route_px = nav.route_distance(belief.worldmap, teammate.pos, spawn.pos)
        if teammate_route_px + ITEM_YIELD_MARGIN_PX < self_route_px:
            return True
        if (
            abs(teammate_route_px - self_route_px) <= ITEM_YIELD_MARGIN_PX
            and teammate.pos < belief.self_xy
        ):
            # Stable geometric tie-break so two nearby bots don't both pursue.
            return True
    return False


def evaluate_fetch(
    belief: Belief,
    anchor: tuple[int, int],
    *,
    anchor_kind: str,
) -> ItemOption | None:
    """Evaluate discovered pickups by marginal route cost; return the best option."""
    belief.item_options = []
    belief.item_choice = None
    if belief.self_xy is None or belief.worldmap is None or not belief.item_spawns:
        return None
    wm = belief.worldmap

    direct_route_px = nav.route_distance(wm, belief.self_xy, anchor)
    for spawn in belief.item_spawns:
        if not spawn.present or _already_have(belief, spawn.kind):
            continue
        if spawn.kind == "medkit" and (belief.hp_pips is None or belief.hp_pips >= 3):
            continue
        route_to_item_px = nav.route_distance(wm, belief.self_xy, spawn.pos)
        route_via_item_px = route_to_item_px + nav.route_distance(wm, spawn.pos, anchor)
        detour_px = max(0.0, route_via_item_px - direct_route_px)
        threshold_px = _threshold(spawn)
        if spawn.kind == "arc" and route_to_item_px > ITEM_PICKUP_RANGE:
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


def medkit_target(belief: Belief, max_distance_px: float) -> ItemSpawn | None:
    """The nearest believed-present med kit when hurt, or None."""
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
    return (
        math.hypot(self_xy[0] - spawn.pos[0], self_xy[1] - spawn.pos[1])
        <= ITEM_PICKUP_RANGE
    )


__all__ = [
    "arrived",
    "evaluate_fetch",
    "medkit_target",
    "update_items",
]
