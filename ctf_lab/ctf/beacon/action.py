"""Action resolution — turn an Intent + Belief into an 8-bit controller mask.

This is where the tactical design lives (§3, §5):

  * **Movement**: step toward the navigation waypoint (flow-field or A*) as a d-pad
    octant. Movement is fully decoupled from aim.
  * **Aim (the lighthouse)**: default is a sweep panning ±SWEEP_HALF_ARC across the
    *threat axis* (unit vector from us toward the enemy pedestal). The moment an
    enemy is visible, the sweep aborts and aim snaps onto the nearest enemy.
  * **Fire**: press A (edge-triggered) when an enemy is visible, the gun is ready,
    and the shot geometry clears the fire-gate (aim close enough that the shot ray
    passes through the target). Never rotate on the firing tick, so the locked aim
    is the settled one.

The rotation we command is recorded in ActionState.last_rot so belief.py can
dead-reckon the aim estimate between aim-dot reads.
"""

from __future__ import annotations

import math

from ctf.beacon import nav
from ctf.beacon.config import (
    AIM_BRADS_TURN,
    AIM_DEADBAND,
    AIM_TURN_RATE,
    CLOSE_RANGE_PX,
    FIRE_SLACK_PX,
    FRIENDLY_FIRE_CORRIDOR_PX,
    PEDESTAL,
    STUCK_TICKS,
    SWEEP_HALF_ARC,
)
from ctf.beacon.types import ActionState, Belief, Command, Intent
from players.player_sdk import Button


def _brads_of(dx: float, dy: float) -> int:
    """Aim brads for a direction (0 = east, CCW positive, screen y is down)."""
    ang = math.atan2(-dy, dx)
    return round(ang / (2 * math.pi) * AIM_BRADS_TURN) % AIM_BRADS_TURN


def _brad_error(target: int, current: int) -> int:
    """Signed shortest angular distance target-current, in [-128, 128]. Positive
    means target is CCW of current (reachable by rotating CCW / button B)."""
    err = (target - current) % AIM_BRADS_TURN
    if err > AIM_BRADS_TURN // 2:
        err -= AIM_BRADS_TURN
    return err


def _nearest_enemy(belief: Belief):
    if not belief.enemies or belief.self_xy is None:
        return None
    sx, sy = belief.self_xy
    return min(belief.enemies, key=lambda e: (e.pos[0] - sx) ** 2 + (e.pos[1] - sy) ** 2)


def _threat_axis(belief: Belief) -> int:
    """Brads toward the enemy pedestal — the sweep centre. Forward while advancing,
    back across the field once we've turned for home."""
    team = belief.team
    assert team is not None and belief.self_xy is not None
    enemy = "blue" if team == "red" else "red"
    px, py = PEDESTAL[enemy]
    sx, sy = belief.self_xy
    if abs(px - sx) < 1 and abs(py - sy) < 1:
        from ctf.beacon.config import SPAWN_AIM
        return SPAWN_AIM[team]
    return _brads_of(px - sx, py - sy)


def _sweep_target(belief: Belief) -> int:
    """Advance the lighthouse sweep one step and return the desired aim (brads)."""
    axis = _threat_axis(belief)
    belief.sweep_offset += belief.sweep_dir * AIM_TURN_RATE
    if belief.sweep_offset >= SWEEP_HALF_ARC:
        belief.sweep_offset = SWEEP_HALF_ARC
        belief.sweep_dir = -1
    elif belief.sweep_offset <= -SWEEP_HALF_ARC:
        belief.sweep_offset = -SWEEP_HALF_ARC
        belief.sweep_dir = 1
    return (axis + belief.sweep_offset) % AIM_BRADS_TURN


def _fire_gate(belief: Belief, target_pos: tuple[int, int]) -> bool:
    """True when the current aim is close enough that a shot would hit the target.

    Uses the baseline's geometric gate: range * sin(angle_error) <= slack, i.e. the
    aim ray passes within ``FIRE_SLACK_PX`` of the target centre. A looser gate at
    close range where the corridor is wide relative to the distance.
    """
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    tx, ty = target_pos
    rng = math.hypot(tx - sx, ty - sy)
    if rng < 1:
        return True
    want = _brads_of(tx - sx, ty - sy)
    err = abs(_brad_error(want, belief.aim_brads))
    err_rad = err / AIM_BRADS_TURN * 2 * math.pi
    perp = rng * math.sin(err_rad)
    slack = FIRE_SLACK_PX * (2.0 if rng <= CLOSE_RANGE_PX else 1.0)
    return perp <= slack


def _teammate_blocks_shot(belief: Belief, target_pos: tuple[int, int]) -> bool:
    """True if a visible teammate sits in the shot corridor between us and the target.

    Friendly fire is ON and the shot is hitscan along the aim ray, stopping at the
    FIRST body it crosses — so a teammate closer than the target, near the ray, eats
    the bullet. Hold fire in that case (a lesson from beacon:v2's 6 FF deaths/game)."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    tx, ty = target_pos
    rng = math.hypot(tx - sx, ty - sy)
    if rng < 1:
        return False
    ux, uy = (tx - sx) / rng, (ty - sy) / rng  # unit vector toward target
    for mate in belief.teammates:
        mx, my = mate.pos
        along = (mx - sx) * ux + (my - sy) * uy  # projection onto the ray
        if along <= 0 or along >= rng:  # behind us, or beyond the target
            continue
        perp = abs((mx - sx) * (-uy) + (my - sy) * ux)  # perpendicular distance to ray
        if perp <= FRIENDLY_FIRE_CORRIDOR_PX:
            return True
    return False


def resolve_action(intent: Intent, belief: Belief, state: ActionState) -> Command:
    """Compose the controller mask for this frame."""
    mask = 0
    state.last_rot = 0

    if belief.self_xy is None:  # dead / not ready — release everything
        state.a_held = False
        return Command(held_mask=0)

    self_xy = belief.self_xy

    # --- Movement (decoupled from aim) --------------------------------------------
    # "hold" emits no movement (defender sitting on its line); the combat overlay
    # below still sweeps + fires. "navigate_to" routes via the flow field for the two
    # fixed strategic goals, else A* for a dynamic point (hold approach / thief chase).
    if intent.kind == "navigate_to":
        team = belief.team
        assert team is not None
        enemy = "blue" if team == "red" else "red"
        if intent.reason == "carry_home":
            waypoint = nav.flow_waypoint(team, "home", self_xy)
        elif intent.reason == "steal" and intent.point == PEDESTAL[enemy]:
            waypoint = nav.flow_waypoint(team, "steal", self_xy)
        else:
            waypoint = nav.astar_waypoint(belief, self_xy, intent.point or self_xy)
        nav.note_progress(belief, self_xy)
        jitter = belief.nav_stuck_ticks >= STUCK_TICKS
        mask |= nav.octant_toward(self_xy, waypoint, jitter)

    # --- Combat overlay: aim + fire -----------------------------------------------
    enemy = _nearest_enemy(belief)
    if enemy is not None:
        # Snap aim onto the target; fire when ready + gate clears.
        want = _brads_of(enemy.pos[0] - self_xy[0], enemy.pos[1] - self_xy[1])
        err = _brad_error(want, belief.aim_brads)
        can_fire = (
            belief.fire_ready
            and _fire_gate(belief, enemy.pos)
            and not _teammate_blocks_shot(belief, enemy.pos)
        )
        if can_fire and not state.a_held:
            # Fire this tick; do NOT rotate (lock the settled aim).
            mask |= int(Button.A)
            state.a_held = True
        else:
            state.a_held = False
            mask |= _rotation_button(err, state)
    else:
        state.a_held = False
        # No enemy: lighthouse sweep across the threat axis.
        target = _sweep_target(belief)
        err = _brad_error(target, belief.aim_brads)
        mask |= _rotation_button(err, state)

    return Command(held_mask=int(mask) & 0x7F)


def _rotation_button(err: int, state: ActionState) -> int:
    """The aim-rotation button bit to close ``err`` (deadbanded), and record the
    commanded rotation for dead reckoning. B = CCW (positive err), Select = CW."""
    if abs(err) <= AIM_DEADBAND:
        state.last_rot = 0
        return 0
    if err > 0:  # target is CCW of current -> rotate CCW with B
        state.last_rot = 1
        return int(Button.B)
    state.last_rot = -1  # rotate CW with Select
    return int(Button.SELECT)


__all__ = ["resolve_action"]
