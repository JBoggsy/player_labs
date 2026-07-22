"""Item skills (v10): spawn-point belief, fetch assignment, and view-model helpers.

The four pickup families (RULES.md: Grenades / Med kits / Shields / Plasma arc) live at
FIXED spawn points (config mirrors sim.nim's spawn formulas), so the interesting state
is only *is it there right now*. Belief per spawn is optimistic: **present unless we
recently observed the spot empty**, in which case it backs off one respawn interval
(we can't know when it was actually taken, so the earliest it could be back is now +
respawn if it was taken the tick before we looked).

Single-claimant discipline: with no team radio, coordination must be deterministic
from shared knowledge — the same rule computed by every agent from (team, seat).
Each fetchable spawn on OUR side is statically assigned to exactly ONE seat
(`ITEM_SEAT_ASSIGNMENT`); everyone else ignores it, so no two agents rush one pickup.
Med kits are the exception: the sim only lets a HURT player take one (healthy players
walk over it untouched), so any hurt agent may divert — the waste case is two hurt
agents racing, which the detour cap keeps rare and cheap.

Plasma arcs are deliberately UNASSIGNED: carrying one disables the gun, which cuts
against the accuracy goal; the use logic exists (action.py) but nobody fetches one.
"""

from __future__ import annotations

import math

from ctf.beacon import mapdata
from ctf.beacon.config import (
    AIM_BRADS_TURN,
    ARC_RESPAWN_TICKS,
    ARC_SPAWNS,
    CENTER_X,
    GRENADE_RESPAWN_TICKS,
    GRENADE_SPAWNS,
    ITEM_PICKUP_RANGE,
    MEDKIT_RESPAWN_TICKS,
    MEDKIT_SPAWNS,
    SHIELD_RESPAWN_TICKS,
    SHIELD_SPAWNS,
    VISION_BUBBLE,
    VISION_CONE_HALF_DEG,
)
from ctf.beacon.types import Belief, CtfState, ItemKind, ItemSpawn, Team

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


def assigned_fetch(belief: Belief) -> ItemSpawn | None:
    """The one spawn this seat is responsible for fetching right now, or None.

    Static assignment over OUR side's fetchable spawns (all agents compute the same
    table, so each pickup has exactly one claimant):

      * our endzone **shield** -> defender seat 2 (its hold band is the closest)
      * our **top corner grenade** -> attacker seat 3
      * our **bottom corner grenade** -> attacker seat 4

    Returns None once the seat already carries that kind, or while the spawn is
    believed empty (the strategy rung then falls through to the normal role).
    """
    team = belief.team
    if team is None or not belief.item_spawns:
        return None
    wanted: tuple[ItemKind, str] | None = {
        2: ("shield", "any"),
        3: ("grenade", "top"),
        4: ("grenade", "bottom"),
    }.get(belief.seat)
    if wanted is None:
        return None
    kind, half = wanted
    if kind == "shield" and belief.i_have_shield:
        return None
    if kind == "grenade" and belief.i_have_grenade:
        return None
    for spawn in belief.item_spawns:
        if spawn.kind != kind or not _our_side(team, spawn.pos):
            continue
        if half == "top" and spawn.pos[1] > 329:
            continue
        if half == "bottom" and spawn.pos[1] <= 329:
            continue
        return spawn if spawn.present else None
    return None


def medkit_target(belief: Belief, max_detour_px: float) -> ItemSpawn | None:
    """The nearest believed-present med kit worth a detour, when we're hurt."""
    if (
        belief.hp_pips is None
        or belief.hp_pips >= 3
        or belief.self_xy is None
        or not belief.item_spawns
    ):
        return None
    sx, sy = belief.self_xy
    best: ItemSpawn | None = None
    best_d = max_detour_px
    for spawn in belief.item_spawns:
        if spawn.kind != "medkit" or not spawn.present:
            continue
        d = math.hypot(spawn.pos[0] - sx, spawn.pos[1] - sy)
        if d <= best_d:
            best_d = d
            best = spawn
    return best


def arrived(self_xy: tuple[int, int], spawn: ItemSpawn) -> bool:
    return math.hypot(self_xy[0] - spawn.pos[0], self_xy[1] - spawn.pos[1]) <= ITEM_PICKUP_RANGE


__all__ = ["arrived", "assigned_fetch", "build_spawn_table", "medkit_target", "update_items"]
