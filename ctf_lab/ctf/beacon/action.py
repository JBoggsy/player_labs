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
    ARC_AIM_ERR_BRADS,
    ARC_FIRE_RANGE_PX,
    BUTTON_C,
    CLOSE_RANGE_PX,
    DUCK_RANGE_PX,
    DUCK_THREAT_FRESH_TICKS,
    FIRE_MAX_RANGE_PX,
    FIRE_SLACK_PX,
    FIRE_WINDUP_TICKS,
    FRIENDLY_FIRE_CORRIDOR_PX,
    GRENADE_AIM_ERR_BRADS,
    GRENADE_BLAST_RADIUS,
    GRENADE_CHARGE_TICKS,
    GRENADE_FORCE_RELEASE_TICKS,
    GRENADE_MAX_RANGE,
    GRENADE_MIN_RANGE,
    GRENADE_MIN_THROW_PX,
    GRENADE_TARGET_FRESH_TICKS,
    GRENADE_THROW,
    GRID_H,
    GRID_W,
    LEAD_AIM,
    LEAD_MIN_FRAMES,
    LEAD_TICKS,
    NAV_CELL,
    PEDESTAL,
    PEEK_DUCK,
    PEEK_DUCK_RUSH_EXEMPT_PX,
    PEEK_DUCK_SEARCH_CELLS,
    PEEK_TARGET_FRESH_TICKS,
    STUCK_TICKS,
    SWEEP_HALF_ARC,
)
from ctf.beacon.types import ActionState, Belief, Command, Enemy, Intent, PlayerTrack
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


def _lead_aim_pos(belief: Belief, enemy: Enemy) -> tuple[tuple[int, int], int]:
    """Where to aim at a visible enemy: its velocity-extrapolated position at the
    moment our bullet actually exists.

    The gun is hitscan but NOT instant: the aim locks at the trigger pull and the
    bullet leaves ``FIRE_WINDUP_TICKS`` later (sim.nim startFireWindup), so a strafing
    enemy is ~LEAD_TICKS * vel px away from its sighted position when the ray is
    cast. We find the enemy's track (updated to this sighting this tick), and if its
    EMA velocity rests on enough frames, aim ahead. Returns (aim_pos, lead_brads);
    lead_brads == 0 means no lead was applied (activation-traceable).
    """
    if not LEAD_AIM or belief.self_xy is None:
        return enemy.pos, 0
    track = next(
        (
            t
            for t in belief.enemy_tracks
            if t.last_tick == belief.tick and t.pos == enemy.pos
        ),
        None,
    )
    if track is None or track.vel is None or track.frames_seen < LEAD_MIN_FRAMES:
        return enemy.pos, 0
    from ctf.beacon.config import MAP_H, MAP_W

    px = min(max(round(enemy.pos[0] + track.vel[0] * LEAD_TICKS), 0), MAP_W - 1)
    py = min(max(round(enemy.pos[1] + track.vel[1] * LEAD_TICKS), 0), MAP_H - 1)
    if (px, py) == enemy.pos:
        return enemy.pos, 0
    sx, sy = belief.self_xy
    raw = _brads_of(enemy.pos[0] - sx, enemy.pos[1] - sy)
    led = _brads_of(px - sx, py - sy)
    return (px, py), _brad_error(led, raw)


def _fire_gate(belief: Belief, target_pos: tuple[int, int]) -> bool:
    """True when the current aim is close enough that a shot would hit the target.

    Uses the baseline's geometric gate: range * sin(angle_error) <= slack, i.e. the
    aim ray passes within ``FIRE_SLACK_PX`` of the target centre. A looser gate at
    close range where the corridor is wide relative to the distance; NO gate beyond
    ``FIRE_MAX_RANGE_PX`` — out there the 5-brad aim quantization alone exceeds the
    14px hit corridor, so a shot is spray, and spray is what v10's 0.23 accuracy was
    made of. Withheld shots also keep the gun ready for the next real window.
    """
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    tx, ty = target_pos
    rng = math.hypot(tx - sx, ty - sy)
    if rng < 1:
        return True
    if rng > FIRE_MAX_RANGE_PX:
        return False
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
            belief.micro = "duck"
            return (0, aim)  # already behind cover: hold still, watch the arc
        duck = _find_sidestep_cell(belief.self_xy, tpos, want_los=False)
        if duck is None:
            return None  # no cover nearby — fight in the open as before
        belief.micro = "duck"
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
        belief.micro = "peek"
        if math.hypot(peek[0] - sx, peek[1] - sy) < 5.0:
            return (0, aim)  # on the peek cell; hold and let the aim settle
        return (nav.octant_toward(belief.self_xy, peek, False), aim)

    return None


def resolve_action(intent: Intent, belief: Belief, state: ActionState) -> Command:
    """Compose the controller mask for this frame."""
    mask = 0
    state.last_rot = 0
    belief.micro = None  # set by _peek_duck_override when it engages this tick

    if belief.self_xy is None:  # dead / not ready — release everything
        state.a_held = False
        belief.lead_brads = 0
        belief.throw_charge_ticks = 0
        belief.throw_target = None
        return Command(held_mask=0)

    self_xy = belief.self_xy

    # --- Peek-fire-duck micro (v7): may override movement + supply a desired aim ---
    override = _peek_duck_override(intent, belief) if PEEK_DUCK else None

    # --- Movement (decoupled from aim) --------------------------------------------
    # "hold" emits no movement (defender sitting on its line); the combat overlay
    # below still sweeps + fires. "navigate_to" routes via the flow field for the two
    # fixed strategic goals, else A* for a dynamic point (hold approach / thief chase).
    # Post-trigger freeze (v12): the bullet leaves FIRE_WINDUP_TICKS after the pull
    # from our CURRENT position along the LOCKED angle (sim.nim applyFire), so
    # strafing through the windup displaces our own ray sideways — 5 ticks of strafe
    # is ~14px, a full hit-corridor width. Stand still until the shot is out.
    # Exempt while carrying: the carrier's life beats its marksmanship.
    freeze = state.fire_hold_ticks > 0 and not belief.i_carry_enemy_flag
    if state.fire_hold_ticks > 0:
        state.fire_hold_ticks -= 1
    if freeze:
        pass  # no movement bits this tick — let the windup release on target
    elif override is not None:
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
        # Snap aim onto the target — led ahead of a moving one (v10): the windup
        # delays the bullet ~LEAD_TICKS, so aim where the target will BE.
        aim_pos, lead = _lead_aim_pos(belief, enemy)
        belief.lead_brads = lead
        want = _brads_of(aim_pos[0] - self_xy[0], aim_pos[1] - self_xy[1])
        err = _brad_error(want, belief.aim_brads)
        if belief.i_have_arc:
            # The gun is disabled while carrying an arc: A ignites the plasma cone
            # instead. Short reach — only worth pressing with the target inside it.
            rng = math.hypot(enemy.pos[0] - self_xy[0], enemy.pos[1] - self_xy[1])
            can_fire = (
                belief.fire_ready
                and rng <= ARC_FIRE_RANGE_PX
                and abs(err) <= ARC_AIM_ERR_BRADS
                and not _teammate_blocks_shot(belief, enemy.pos)
            )
        else:
            # ray_clear guards the GLASS WINDOWS (GameVersion 15/16): vision passes
            # through glass but bullets don't, so a visible enemy is no longer a
            # shootable one — firing through a window is a guaranteed miss.
            can_fire = (
                belief.fire_ready
                and _fire_gate(belief, aim_pos)
                and mapdata.ray_clear(self_xy, aim_pos)
                and not _teammate_blocks_shot(belief, aim_pos)
            )
        if can_fire and not state.a_held:
            # Fire this tick; do NOT rotate (lock the settled aim), and freeze
            # movement through the windup so the bullet leaves from where we aimed
            # (drop any movement bits already in the mask for this tick too).
            if not belief.i_carry_enemy_flag:
                mask &= ~(int(Button.UP) | int(Button.DOWN) | int(Button.LEFT) | int(Button.RIGHT))
                state.fire_hold_ticks = FIRE_WINDUP_TICKS
            mask |= int(Button.A)
            state.a_held = True
        else:
            state.a_held = False
            mask |= _rotation_button(err, state)
    else:
        state.a_held = False
        belief.lead_brads = 0
        if override is not None and override[1] is not None:
            # Ducking/peeking: lay the aim on the remembered threat's arc so the
            # vision cone watches the lane (and a peek exits pre-aimed).
            target = override[1]
        else:
            # No enemy: lighthouse sweep across the threat axis.
            target = _sweep_target(belief)
        err = _brad_error(target, belief.aim_brads)
        mask |= _rotation_button(err, state)

    # --- Grenade overlay (v10): lob at wall-blocked remembered enemies -------------
    # Rides ON TOP of gun combat: C charges/releases independently of A, and the
    # charge only starts when no enemy is visible (the gun handles visible ones).
    if GRENADE_THROW and belief.i_have_grenade:
        mask = _grenade_overlay(mask, belief, state)
    else:
        belief.throw_charge_ticks = 0
        belief.throw_target = None

    return Command(held_mask=int(mask) & 0xFF)


def _lob_target(belief: Belief) -> tuple[int, int] | None:
    """A grenade-worthy target: the nearest FRESH, WALL-BLOCKED remembered enemy in
    throw range. Open targets belong to the gun; blocked ones are exactly what the
    over-wall lob buys. Vetoes a landing that would splash a teammate (or us)."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    best: tuple[int, int] | None = None
    best_d = float(GRENADE_MAX_RANGE)
    for t in belief.enemy_tracks:
        if belief.tick - t.last_tick > GRENADE_TARGET_FRESH_TICKS:
            continue
        pos = _predicted_pos(t, belief.tick)
        d = math.hypot(pos[0] - sx, pos[1] - sy)
        if d < GRENADE_MIN_THROW_PX or d > best_d:
            continue
        if mapdata.ray_clear(belief.self_xy, pos):
            continue  # open line: the gun handles it
        splash = GRENADE_BLAST_RADIUS + 20.0
        if any(
            math.hypot(m.pos[0] - pos[0], m.pos[1] - pos[1]) <= splash
            for m in belief.teammates
        ):
            continue
        best = pos
        best_d = d
    return best


def _grenade_overlay(mask: int, belief: Belief, state: ActionState) -> int:
    """The C-button charge/release state machine, riding on top of gun combat.

    Charge only starts when no enemy is visible (the gun owns visible fights); once
    charging, C stays held while the aim lays onto the lob bearing, and releases when
    the charge matches the throw distance and the aim has settled. A charge that
    can't settle force-releases after a grace period — the sim throws on ANY C
    release, so carrying a charge forever would waste the grenade anyway.
    """
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    charging = belief.throw_charge_ticks > 0

    if not charging:
        if belief.enemies:  # gun fight in progress — don't start a lob
            belief.throw_target = None
            return mask
        target = _lob_target(belief)
        belief.throw_target = target
        if target is None:
            return mask
        belief.throw_charge_ticks = 1
        return mask | BUTTON_C

    target = belief.throw_target or (sx, sy)
    belief.throw_charge_ticks += 1
    d = math.hypot(target[0] - sx, target[1] - sy)
    span = max(1, GRENADE_MAX_RANGE - GRENADE_MIN_RANGE)
    charge_needed = min(
        GRENADE_CHARGE_TICKS,
        max(1, math.ceil((d - GRENADE_MIN_RANGE) / span * GRENADE_CHARGE_TICKS)),
    )
    want = _brads_of(target[0] - sx, target[1] - sy)
    err = _brad_error(want, belief.aim_brads)
    overdue = belief.throw_charge_ticks >= GRENADE_CHARGE_TICKS + GRENADE_FORCE_RELEASE_TICKS

    if not belief.enemies:
        # Own the aim while charging: replace any sweep rotation with the lob bearing.
        mask &= ~(int(Button.B) | int(Button.SELECT))
        mask |= _rotation_button(err, state)

    ready = belief.throw_charge_ticks >= charge_needed and abs(err) <= GRENADE_AIM_ERR_BRADS
    if (ready and not belief.enemies) or overdue:
        # Release: C up this tick throws along the current aim.
        belief.throw_charge_ticks = 0
        belief.throw_target = None
        return mask
    return mask | BUTTON_C


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
