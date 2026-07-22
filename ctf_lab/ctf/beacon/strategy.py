"""The priority ladder — choose ONE navigation objective per tick (v2, role-aware).

Combat and aim are NOT a rung here; they ride as an overlay in action.py (sweep the
threat axis, snap-and-fire on any visible enemy). The ladder only decides *where to
move*. See design §5, and TENTATIVE_LESSONS (games are decided by wipe → defense wins).

Returns an Intent plus the flow-field kind to use ("steal" / "home" / None for A*).
"""

from __future__ import annotations

import math

from ctf.beacon import items, squads
from ctf.beacon.config import (
    GRENADE_WARN_CLEAR_PX,
    HOLD_ARRIVE_PX,
    ITEM_DETOUR_PX,
    ITEMS,
    MEDKIT_DETOUR_PX,
    PEDESTAL,
    SQUADS,
)
from ctf.beacon.types import Belief, Intent


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def decide_objective(belief: Belief) -> tuple[Intent, str | None]:
    """Pick the single movement objective. Returns (intent, flow_kind)."""
    team = belief.team
    assert team is not None
    enemy = "blue" if team == "red" else "red"

    # Rung 1 (everyone): carrying the enemy flag -> run it home. A carried flag is a
    # win one delivery away, and dying returns it instantly. Overrides role.
    if belief.i_carry_enemy_flag:
        return Intent(kind="navigate_to", point=None, reason="carry_home"), "home"

    # Rung 2 (everyone): our flag is stolen and we have a thief fix -> intercept.
    # Killing the carrier returns the flag instantly; this is the anti-capture play.
    # The fix is our OWN eyes first, else a teammate's T shout (v18) — chat turns a
    # personal sighting into a team-wide manhunt.
    if belief.own_flag_stolen:
        if belief.own_flag_thief_pos is not None:
            return Intent(kind="navigate_to", point=belief.own_flag_thief_pos, reason="intercept_thief"), None
        if belief.thief_fix is not None:
            return Intent(kind="navigate_to", point=belief.thief_fix[0], reason="intercept_thief_heard"), None

    # Rung 3 (attackers): a TEAMMATE is carrying our stolen enemy flag -> escort it.
    # Sight-based fix first (the flag sprite rides the carrier); else the carrier's
    # C heartbeat (v18) — projected one step along its shouted heading octant, so a
    # fogged carrier still gathers its escorts. Attackers converge and move home
    # WITH it — the fix for "grabs the flag but dies before delivery".
    if belief.role == "attacker" and not belief.i_carry_enemy_flag and not belief.enemy_flag_on_pedestal:
        if belief.enemy_flag_pos is not None:
            return Intent(kind="navigate_to", point=belief.enemy_flag_pos, reason="escort_carrier"), None
        if belief.carrier_fix is not None:
            (cx, cy), octant, heard_tick = belief.carrier_fix
            dt = min(belief.tick - heard_tick, 48)
            ang = octant * math.pi / 4
            px = int(cx + math.cos(ang) * 1.9 * dt)  # ~70% of max speed while carrying
            py = int(cy - math.sin(ang) * 1.9 * dt)
            return Intent(kind="navigate_to", point=(px, py), reason="escort_carrier_heard"), None

    # Rung 3.4 (v18): a teammate shouted a grenade landing near us -> step clear.
    # The blast (52px) hurts teammates; the warning names the landing cell.
    if belief.self_xy is not None:
        for gpos, _t in belief.grenade_warnings:
            d = _dist(belief.self_xy, gpos)
            if d < GRENADE_WARN_CLEAR_PX:
                # Flee directly away from the landing point.
                dx = belief.self_xy[0] - gpos[0]
                dy = belief.self_xy[1] - gpos[1]
                n = max(d, 1.0)
                flee = (
                    int(belief.self_xy[0] + dx / n * GRENADE_WARN_CLEAR_PX),
                    int(belief.self_xy[1] + dy / n * GRENADE_WARN_CLEAR_PX),
                )
                return Intent(kind="navigate_to", point=flee, reason="clear_grenade"), None

    # Rung 3.5 (items, v10): fetch pickups when nothing flag-urgent is happening
    # (carry / intercept / escort all returned above). Two cases, both detour-capped
    # so a fetch never drags an agent across the map:
    #   * hurt + a med kit in reach -> heal (any seat; the sim only lets a HURT
    #     player take a kit, so a healthy teammate racing it wastes nothing);
    #   * this seat's statically-assigned pickup (single-claimant: the assignment
    #     is a pure function of seat, so exactly one agent claims each item).
    if ITEMS and belief.self_xy is not None:
        kit = items.medkit_target(belief, MEDKIT_DETOUR_PX)
        if kit is not None:
            return Intent(kind="navigate_to", point=kit.pos, reason="fetch_medkit"), None
        assigned = items.assigned_fetch(belief)
        if assigned is not None and _dist(belief.self_xy, assigned.pos) <= ITEM_DETOUR_PX:
            return Intent(kind="navigate_to", point=assigned.pos, reason="fetch_item"), None

    # Rung 4: role split.
    if belief.role == "defender" and belief.hold_point is not None:
        # Hold cover on our turf: the enemy dies attacking us (we respawn close),
        # and our flag stops being undefended. Once at the hold point, stop
        # advancing (A* returns ~self) and let the combat overlay work the lane.
        if belief.self_xy is not None and _dist(belief.self_xy, belief.hold_point) <= HOLD_ARRIVE_PX:
            return Intent(kind="hold", reason="hold_line"), None
        return Intent(kind="navigate_to", point=belief.hold_point, reason="to_hold"), None

    # Attackers (and defenders with no hold point): push the enemy flag — in a
    # WAVE (v19): hold at the rally line until enough squadmates are near, so the
    # push isn't a dribble of solo attackers (h006's blitz and focusfire's turtle
    # both farm those). Timeout-capped; carriers/intercepts never reach here.
    if SQUADS and squads.should_wait_for_squad(belief):
        belief.squad_wait_ticks += 1
        return Intent(kind="hold", reason="squad_rally"), None
    return Intent(kind="navigate_to", point=PEDESTAL[enemy], reason="steal"), "steal"


__all__ = ["decide_objective"]
