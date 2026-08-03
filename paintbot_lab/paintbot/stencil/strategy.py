"""The priority ladder — choose ONE navigation objective per tick.

Combat and aim are NOT a rung here; they ride as an overlay in action.py. The
ladder only decides *where to move*. Beacon's battle-plan/POI/post rungs are
gone (they were drawings on the fixed CTF arena); what remains is the proven
core, with every geometric anchor derived from the episode WorldMap:

  carry home > rejoin > intercept thief > escort carrier > clear grenade >
  fetch medkit/items > squad order (off by default) > convert hunt > the
  static role split (defenders hold derived chokes; attackers steal the
  chosen target heart).

Returns an Intent plus the flow goal to use (a stable point routed via the
map's flow fields, or None for A* to a dynamic point).
"""

from __future__ import annotations

import math

from paintbot.stencil import items, squads
from paintbot.stencil.config import (
    GRENADE_WARN_CLEAR_PX,
    HOLD_ARRIVE_PX,
    ITEMS,
    MEDKIT_CONVENIENT_DETOUR_PX,
    ORDER_TTL_TICKS,
    SQUAD_COMMAND,
    SQUADS,
)
from paintbot.stencil.types import Belief, Intent


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def decide_objective(belief: Belief) -> tuple[Intent, tuple[int, int] | None]:
    """Pick the single movement objective. Returns (intent, flow_goal)."""
    team = belief.team
    wm = belief.worldmap
    assert team is not None
    if wm is None:
        # No world model yet (init snapshot incomplete): hold still.
        return Intent(kind="hold", reason="no_worldmap"), None

    # Squad command upkeep: refresh presence; leaders run the rule engine.
    if SQUAD_COMMAND:
        squads.update_presence(belief)
        squads.lead_squad(belief)

    # Rung 1 (everyone): carrying an enemy heart -> run it home. A carried heart
    # is an elimination one delivery away, and dying returns it instantly.
    if belief.i_carry_heart_of is not None:
        home = wm.capture_point(team)
        return Intent(kind="navigate_to", point=home, reason="carry_home"), home

    # Rung 1.5 (respawn discipline, off by default with SQUAD_COMMAND).
    if SQUAD_COMMAND and belief.rejoin_until >= 0 and belief.self_xy is not None:
        if belief.tick >= belief.rejoin_until or squads.in_squad_contact(belief):
            belief.rejoin_until = -1
            belief.rejoin_point = None
        elif belief.rejoin_point is not None:
            belief.rejoin_ticks += 1
            if _dist(belief.self_xy, belief.rejoin_point) > 40:
                return Intent(kind="navigate_to", point=belief.rejoin_point, reason="rejoin"), None
            return Intent(kind="hold", reason="rejoin_hold"), None

    # Rung 2 (everyone): our heart is stolen and we have a thief fix -> intercept.
    # Killing the carrier returns the heart instantly; this is the anti-elimination
    # play. Our OWN eyes first, else a teammate's T shout.
    if belief.own_heart_stolen:
        if belief.own_heart_thief_pos is not None:
            return Intent(kind="navigate_to", point=belief.own_heart_thief_pos, reason="intercept_thief"), None
        if belief.thief_fix is not None:
            return Intent(kind="navigate_to", point=belief.thief_fix[0], reason="intercept_thief_heard"), None

    # Rung 3 (attackers): a TEAMMATE is carrying a stolen enemy heart -> escort it.
    # Sight-based fix first (the heart sprite rides the carrier); else the
    # carrier's C heartbeat, projected one step along its shouted heading octant.
    if belief.role == "attacker" and belief.i_carry_heart_of is None:
        carried_fix: tuple[int, int] | None = None
        for color, state in belief.hearts.items():
            if color == team or color in belief.hearts_retired:
                continue
            if not state.planted and state.carried_pos is not None:
                carried_fix = state.carried_pos
                break
        if carried_fix is not None:
            return Intent(kind="navigate_to", point=carried_fix, reason="escort_carrier"), None
        if belief.carrier_fix is not None:
            (cx, cy), octant, heard_tick = belief.carrier_fix
            dt = min(belief.tick - heard_tick, 48)
            ang = octant * math.pi / 4
            px = int(cx + math.cos(ang) * 1.9 * dt)  # ~70% of max speed while carrying
            py = int(cy - math.sin(ang) * 1.9 * dt)
            return Intent(kind="navigate_to", point=(px, py), reason="escort_carrier_heard"), None

    # Rung 3.4: a teammate shouted a grenade landing near us -> step clear.
    if belief.self_xy is not None:
        for gpos, _t in belief.grenade_warnings:
            d = _dist(belief.self_xy, gpos)
            if d < GRENADE_WARN_CLEAR_PX:
                dx = belief.self_xy[0] - gpos[0]
                dy = belief.self_xy[1] - gpos[1]
                n = max(d, 1.0)
                flee = (
                    int(belief.self_xy[0] + dx / n * GRENADE_WARN_CLEAR_PX),
                    int(belief.self_xy[1] + dy / n * GRENADE_WARN_CLEAR_PX),
                )
                return Intent(kind="navigate_to", point=flee, reason="clear_grenade"), None

    # Rung 3.5: med kits when hurt; other pickups only when genuinely convenient
    # relative to the current objective anchor.
    if belief.self_xy is not None and ITEMS:
        kit = items.medkit_target(belief, MEDKIT_CONVENIENT_DETOUR_PX)
        if kit is not None:
            return Intent(kind="navigate_to", point=kit.pos, reason="fetch_medkit"), None
        anchor, anchor_kind = _item_anchor(belief)
        choice = items.evaluate_fetch(belief, anchor, anchor_kind=anchor_kind)
        if choice is not None and choice.accepted:
            return Intent(kind="navigate_to", point=choice.spawn.pos, reason="fetch_item"), None

    # Rung 4: obey the squad order when one is live (off by default).
    if SQUAD_COMMAND and belief.order is not None and belief.self_xy is not None:
        goal, opos, set_tick = belief.order
        if belief.tick - set_tick > ORDER_TTL_TICKS:
            if squads.wipe_in_reach(belief):
                belief.order = ("T", squads.convert_hunt_point(belief), belief.tick)
                belief.order_source = "convert"
            else:
                belief.order = ("H", squads.decay_hold_point(belief), belief.tick)
                belief.order_source = "decay"
            goal, opos, set_tick = belief.order
        if goal in ("H", "S", "P"):
            opos = squads.spread_point(belief, opos)
        if goal in ("H", "S"):
            if _dist(belief.self_xy, opos) <= HOLD_ARRIVE_PX * 2:
                return Intent(kind="hold", reason="order_hold"), None
            return Intent(kind="navigate_to", point=opos, reason="order_to_hold"), None
        if goal == "P":
            if _dist(belief.self_xy, opos) <= HOLD_ARRIVE_PX * 2:
                return Intent(kind="hold", reason="order_push_arrived"), None
            return Intent(kind="navigate_to", point=opos, reason="order_push"), None
        if goal == "T":
            return Intent(kind="navigate_to", point=opos, reason="order_hunt"), None
        if goal == "F":
            steal = _steal_goal(belief)
            if steal is not None:
                return Intent(kind="navigate_to", point=steal, reason="steal"), steal

    # Rung 3.8: the CONVERT TRIGGER, standalone (always on). The scoreboard is
    # fog-independent and identical for every agent; when the weakest enemy
    # team's wipe is in reach, everyone hunts the freshest enemy evidence.
    if squads.wipe_in_reach(belief) and belief.self_xy is not None:
        hunt_point = squads.convert_hunt_point(belief)
        if not belief.converting:
            belief.converting = True
            belief.convert_events += 1
        return Intent(kind="navigate_to", point=hunt_point, reason="convert_hunt"), None
    belief.converting = False

    # Rung 5: the static role split.
    if belief.role == "defender" and belief.hold_point is not None:
        if belief.self_xy is not None and _dist(belief.self_xy, belief.hold_point) <= HOLD_ARRIVE_PX:
            return Intent(kind="hold", reason="hold_line"), None
        return Intent(kind="navigate_to", point=belief.hold_point, reason="to_hold"), belief.hold_point

    # Attackers: push the chosen target heart.
    steal = _steal_goal(belief)
    if steal is None:
        # No live enemy heart (endgame oddity): hunt the freshest evidence.
        return Intent(
            kind="navigate_to",
            point=squads.convert_hunt_point(belief),
            reason="hunt_fallback",
        ), None
    if SQUADS and _should_wait(belief):
        belief.squad_wait_ticks += 1
        return Intent(kind="hold", reason="squad_rally"), None
    return Intent(kind="navigate_to", point=steal, reason="steal"), steal


def _steal_goal(belief: Belief) -> tuple[int, int] | None:
    """Where the chosen target heart currently rests, if any target is live."""
    wm = belief.worldmap
    if wm is None or belief.steal_target is None:
        return None
    target = belief.steal_target
    state = belief.hearts.get(target)
    if state is not None and state.planted and state.pos is not None:
        return state.pos
    return wm.pedestal(target)


def _item_anchor(belief: Belief) -> tuple[tuple[int, int], str]:
    """Current non-emergency objective used to price a pickup detour."""
    if (
        belief.order is not None
        and belief.tick - belief.order[2] <= ORDER_TTL_TICKS
    ):
        return belief.order[1], "order"
    if belief.role == "defender" and belief.hold_point is not None:
        return belief.hold_point, "role"
    steal = _steal_goal(belief)
    if steal is not None:
        return steal, "role"
    wm = belief.worldmap
    assert wm is not None
    return wm.center, "role"


def _should_wait(belief: Belief) -> bool:
    """Attacker rally gating (off by default; kept for A/B parity with beacon)."""
    return False


__all__ = ["decide_objective"]
