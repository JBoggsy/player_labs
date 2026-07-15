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

from ctf.beacon import mapdata, nav
from ctf.beacon.config import (
    AIM_BRADS_TURN,
    AIM_DEADBAND,
    AIM_TURN_RATE,
    CLOSE_RANGE_PX,
    DUCK_RANGE_PX,
    DUCK_THREAT_FRESH_TICKS,
    FIRE_SLACK_PX,
    FRIENDLY_FIRE_CORRIDOR_PX,
    GRID_H,
    GRID_W,
    NAV_CELL,
    PEDESTAL,
    PEEK_DUCK,
    PEEK_DUCK_RUSH_EXEMPT_PX,
    PEEK_DUCK_SEARCH_CELLS,
    PEEK_TARGET_FRESH_TICKS,
    STUCK_TICKS,
    SWEEP_HALF_ARC,
)
from ctf.beacon.types import ActionState, Belief, Command, Intent, PlayerTrack
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


# --- Peek-fire-duck micro (v7) --------------------------------------------------------
# The fire->duck->peek cycle (mirrors players/baseline/baseline.nim): spend the gun's
# cooldown behind a wall, pre-lay the aim on a blocked target while sidestepping to the
# cell that opens the line, and fire the tick the ray clears. Overrides MOVEMENT (and
# supplies a desired aim); the combat overlay's snap-aim/fire/FF gates are unchanged.


def _cell_center(gx: int, gy: int) -> tuple[int, int]:
    return (gx * NAV_CELL + NAV_CELL // 2, gy * NAV_CELL + NAV_CELL // 2)


def _fresh_track(belief: Belief, max_age: int, max_range: float | None = None) -> PlayerTrack | None:
    """The nearest enemy track seen within ``max_age`` ticks (and ``max_range`` px)."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    best: PlayerTrack | None = None
    best_d = float("inf") if max_range is None else max_range
    for t in belief.enemy_tracks:
        if belief.tick - t.last_tick > max_age:
            continue
        d = math.hypot(t.pos[0] - sx, t.pos[1] - sy)
        if d < best_d:
            best_d = d
            best = t
    return best


def _predicted_pos(track: PlayerTrack, tick: int) -> tuple[int, int]:
    """The track's velocity-extrapolated position now (clamped to the map)."""
    if track.vel is None:
        return track.pos
    dt = tick - track.last_tick
    from ctf.beacon.config import MAP_H, MAP_W

    x = min(max(round(track.pos[0] + track.vel[0] * dt), 0), MAP_W - 1)
    y = min(max(round(track.pos[1] + track.vel[1] * dt), 0), MAP_H - 1)
    return (x, y)


def _find_sidestep_cell(
    self_xy: tuple[int, int], ref: tuple[int, int], *, want_los: bool
) -> tuple[int, int] | None:
    """Nearest reachable nav cell whose centre has (want_los=True) or breaks
    (False) line-of-sight to ``ref``. Reachable = walkable + a clear straight
    walk from here (one sidestep, not a route). None if no cell qualifies."""
    walkable = mapdata.walkable_grid()
    gx0 = min(max(self_xy[0] // NAV_CELL, 0), GRID_W - 1)
    gy0 = min(max(self_xy[1] // NAV_CELL, 0), GRID_H - 1)
    best: tuple[int, int] | None = None
    best_d = float("inf")
    r = PEEK_DUCK_SEARCH_CELLS
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            nx, ny = gx0 + dx, gy0 + dy
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H) or not walkable[ny, nx]:
                continue
            p = _cell_center(nx, ny)
            if not mapdata.ray_clear(self_xy, p):
                continue  # can't walk straight there
            if mapdata.ray_clear(p, ref) != want_los:
                continue
            d = (p[0] - self_xy[0]) ** 2 + (p[1] - self_xy[1]) ** 2
            if d < best_d:
                best_d = d
                best = p
    return best


def _peek_duck_override(intent: Intent, belief: Belief) -> tuple[int, int | None] | None:
    """The peek/duck movement mask + desired aim for this tick, or None to fall
    through to normal navigation. Exempt while carrying (run!) and in the final
    pedestal approach (grab speed beats safety)."""
    assert belief.self_xy is not None and belief.team is not None
    if belief.i_carry_enemy_flag:
        return None
    enemy = "blue" if belief.team == "red" else "red"
    steal = PEDESTAL[enemy]
    sx, sy = belief.self_xy
    if intent.reason == "steal" and math.hypot(steal[0] - sx, steal[1] - sy) <= PEEK_DUCK_RUSH_EXEMPT_PX:
        return None

    if not belief.fire_ready:
        # DUCK: gun is down and a fresh threat is near -> break its line and hold,
        # keeping the aim (vision cone) on the threat's arc.
        threat = _fresh_track(belief, DUCK_THREAT_FRESH_TICKS, DUCK_RANGE_PX)
        if threat is None:
            return None
        tpos = _predicted_pos(threat, belief.tick)
        aim = _brads_of(tpos[0] - sx, tpos[1] - sy)
        if not mapdata.ray_clear(belief.self_xy, tpos):
            return (0, aim)  # already behind cover: hold still, watch the arc
        duck = _find_sidestep_cell(belief.self_xy, tpos, want_los=False)
        if duck is None:
            return None  # no cover nearby — fight in the open as before
        return (nav.octant_toward(belief.self_xy, duck, False), aim)

    if not belief.enemies:
        # PEEK: gun is up but the freshest track is wall-blocked -> pre-lay the aim
        # on it and sidestep to the cell that opens the line; the combat overlay
        # fires the tick it becomes visible.
        target = _fresh_track(belief, PEEK_TARGET_FRESH_TICKS)
        if target is None:
            return None
        tpos = _predicted_pos(target, belief.tick)
        if mapdata.ray_clear(belief.self_xy, tpos):
            return None  # line already open; if it were really there we'd see it
        aim = _brads_of(tpos[0] - sx, tpos[1] - sy)
        peek = _find_sidestep_cell(belief.self_xy, tpos, want_los=True)
        if peek is None:
            return None
        if math.hypot(peek[0] - sx, peek[1] - sy) < 5.0:
            return (0, aim)  # on the peek cell; hold and let the aim settle
        return (nav.octant_toward(belief.self_xy, peek, False), aim)

    return None


def resolve_action(intent: Intent, belief: Belief, state: ActionState) -> Command:
    """Compose the controller mask for this frame."""
    mask = 0
    state.last_rot = 0

    if belief.self_xy is None:  # dead / not ready — release everything
        state.a_held = False
        return Command(held_mask=0)

    self_xy = belief.self_xy

    # --- Peek-fire-duck micro (v7): may override movement + supply a desired aim ---
    override = _peek_duck_override(intent, belief) if PEEK_DUCK else None

    # --- Movement (decoupled from aim) --------------------------------------------
    # "hold" emits no movement (defender sitting on its line); the combat overlay
    # below still sweeps + fires. "navigate_to" routes via the flow field for the two
    # fixed strategic goals, else A* for a dynamic point (hold approach / thief chase).
    if override is not None:
        mask |= override[0]
    elif intent.kind == "navigate_to":
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
        if override is not None and override[1] is not None:
            # Ducking/peeking: lay the aim on the remembered threat's arc so the
            # vision cone watches the lane (and a peek exits pre-aimed).
            target = override[1]
        else:
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
