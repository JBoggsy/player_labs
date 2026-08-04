"""Action resolution — turn an Intent + Belief into an 8-bit controller mask.

The tactical layer, ported from beacon:

  * **Movement**: step toward the navigation waypoint (flow-field for stable
    goals, A* for dynamic ones) as a d-pad octant, decoupled from aim.
  * **Aim (the lighthouse)**: default is a sweep panning ±SWEEP_HALF_ARC across
    the *threat axis* (toward the chosen steal target's pedestal). The moment an
    enemy is visible, aim snaps onto the nearest enemy — or fight.py's scored
    target while firefight is active.
  * **Fire**: press A (edge-triggered) when an enemy is visible, the gun is
    ready, and the shot geometry clears the fire-gate; never rotate on the
    firing tick; freeze movement through the windup.
  * **Peek-fire-duck micro**: spend the gun's cooldown behind a wall, pre-lay
    the aim on a blocked target while sidestepping to the cell that opens the
    line, and fire the tick the ray clears.

Beacon's post/battle-plan facing paths are gone (fixed-arena machinery); all
geometry comes from the episode WorldMap.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from paintbot.stencil import fight, nav, squads
from paintbot.stencil.config import (
    AIM_BRADS_TURN,
    AIM_DEADBAND,
    AIM_TURN_RATE,
    ARC_FIRE_RANGE_PX,
    ARC_IDEAL_RANGE_PX,
    ARC_MAX_WIDTH_PX,
    ARC_PURSUIT_RANGE_PX,
    BUTTON_C,
    CLOSE_RANGE_PX,
    DUCK_RANGE_PX,
    DUCK_THREAT_FRESH_TICKS,
    FIRE_SLACK_PX,
    FIRE_WINDUP_TICKS,
    FIREFIGHT,
    FRIENDLY_FIRE_CORRIDOR_PX,
    GRENADE_AIM_ERR_BRADS,
    GRENADE_BLAST_RADIUS,
    GRENADE_CHARGE_TICKS,
    GRENADE_FLIGHT_TICKS,
    GRENADE_FORCE_RELEASE_TICKS,
    GRENADE_MIN_RANGE,
    GRENADE_MIN_THROW_PX,
    GRENADE_SINGLE_HP_MAX,
    GRENADE_TARGET_FRESH_TICKS,
    GRENADE_TEAMMATE_FRESH_TICKS,
    GRENADE_THROW,
    HEARD_DUCK_FRESH_TICKS,
    HEARD_DUCK_RANGE_PX,
    HEARING,
    LEAD_AIM,
    LEAD_MIN_FRAMES,
    LEAD_TICKS,
    NAV_CELL,
    PEEK_DUCK,
    PEEK_DUCK_RUSH_EXEMPT_PX,
    PEEK_DUCK_SEARCH_CELLS,
    PEEK_TARGET_FRESH_TICKS,
    SQUADS,
    STUCK_TICKS,
    SWEEP_HALF_ARC,
)
from paintbot.stencil.types import (
    ActionState,
    Belief,
    Command,
    Enemy,
    Intent,
    PlayerTrack,
    TargetCandidate,
)
from players.player_sdk import Button

#: Intent reasons whose goal point is stable enough to route via a flow field.
_FLOW_REASONS = ("carry_home", "steal", "to_hold")


def _brads_of(dx: float, dy: float) -> int:
    """Aim brads for a direction (0 = east, CCW positive, screen y is down)."""
    ang = math.atan2(-dy, dx)
    return round(ang / (2 * math.pi) * AIM_BRADS_TURN) % AIM_BRADS_TURN


def _brad_error(target: int, current: int) -> int:
    """Signed shortest angular distance target-current, in [-128, 128]."""
    err = (target - current) % AIM_BRADS_TURN
    if err > AIM_BRADS_TURN // 2:
        err -= AIM_BRADS_TURN
    return err


def _nearest_enemy(belief: Belief):
    if not belief.enemies or belief.self_xy is None:
        return None
    sx, sy = belief.self_xy
    return min(belief.enemies, key=lambda e: (e.pos[0] - sx) ** 2 + (e.pos[1] - sy) ** 2)


def _clamp_to_map(belief: Belief, x: int, y: int) -> tuple[int, int]:
    wm = belief.worldmap
    if wm is None:
        return (x, y)
    return (min(max(x, 0), wm.width - 1), min(max(y, 0), wm.height - 1))


def _spray_target(belief: Belief) -> Enemy | None:
    """Best visible body for the immediate, live-tracking spray cone."""
    if belief.self_xy is None or belief.worldmap is None:
        return None
    sx, sy = belief.self_xy
    candidates = [
        enemy
        for enemy in belief.enemies
        if math.hypot(enemy.pos[0] - sx, enemy.pos[1] - sy) <= ARC_PURSUIT_RANGE_PX
        and belief.worldmap.ray_clear(belief.self_xy, enemy.pos)
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda enemy: (
            abs(
                _brad_error(
                    _brads_of(
                        _spray_aim_pos(belief, enemy)[0] - sx,
                        _spray_aim_pos(belief, enemy)[1] - sy,
                    ),
                    belief.aim_brads,
                )
            ),
            (enemy.pos[0] - sx) ** 2 + (enemy.pos[1] - sy) ** 2,
        ),
    )


def _spray_aim_pos(belief: Belief, enemy: Enemy) -> tuple[int, int]:
    """One-frame lead for observation-to-input latency, never gun windup lead."""
    track = next(
        (
            item
            for item in belief.enemy_tracks
            if item.last_tick == belief.tick and item.pos == enemy.pos
        ),
        None,
    )
    if track is None or track.vel is None:
        return enemy.pos
    return _clamp_to_map(
        belief,
        round(enemy.pos[0] + track.vel[0]),
        round(enemy.pos[1] + track.vel[1]),
    )


def _spray_contains(belief: Belief, target_pos: tuple[int, int]) -> bool:
    """Whether the current server-aim estimate contains a target centre."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    angle = belief.aim_brads / AIM_BRADS_TURN * 2 * math.pi
    ux, uy = math.cos(angle), -math.sin(angle)
    vx, vy = target_pos[0] - sx, target_pos[1] - sy
    forward = vx * ux + vy * uy
    perpendicular = abs(vx * uy - vy * ux)
    return (
        0 < forward <= ARC_FIRE_RANGE_PX
        and perpendicular <= forward * ARC_MAX_WIDTH_PX / (2 * ARC_FIRE_RANGE_PX)
    )


def _threat_axis(belief: Belief) -> int:
    """Brads toward the chosen steal target's pedestal — the sweep centre."""
    wm = belief.worldmap
    team = belief.team
    assert team is not None and belief.self_xy is not None
    if wm is None:
        return belief.aim_brads
    if belief.steal_target is not None:
        px, py = wm.pedestal(belief.steal_target)
    else:
        px, py = wm.center
    sx, sy = belief.self_xy
    if abs(px - sx) < 1 and abs(py - sy) < 1:
        return wm.spawn_aim(team)
    return _brads_of(px - sx, py - sy)


def _sweep_target(belief: Belief) -> int:
    """Advance the lighthouse sweep one step and return the desired aim (brads)."""
    axis = _threat_axis(belief)
    half_arc = SWEEP_HALF_ARC
    if SQUADS:
        axis = (axis + squads.sector_offset_brads(belief)) % AIM_BRADS_TURN
    belief.sweep_offset += belief.sweep_dir * AIM_TURN_RATE
    if belief.sweep_offset >= half_arc:
        belief.sweep_offset = half_arc
        belief.sweep_dir = -1
    elif belief.sweep_offset <= -half_arc:
        belief.sweep_offset = -half_arc
        belief.sweep_dir = 1
    return (axis + belief.sweep_offset) % AIM_BRADS_TURN


def _lead_aim_pos(belief: Belief, enemy: Enemy) -> tuple[tuple[int, int], int]:
    """Velocity-extrapolated aim point at the moment the bullet actually exists."""
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
    px, py = _clamp_to_map(
        belief,
        round(enemy.pos[0] + track.vel[0] * LEAD_TICKS),
        round(enemy.pos[1] + track.vel[1] * LEAD_TICKS),
    )
    if (px, py) == enemy.pos:
        return enemy.pos, 0
    sx, sy = belief.self_xy
    raw = _brads_of(enemy.pos[0] - sx, enemy.pos[1] - sy)
    led = _brads_of(px - sx, py - sy)
    return (px, py), _brad_error(led, raw)


def _fire_gate(belief: Belief, target_pos: tuple[int, int]) -> bool:
    """True when the current aim is close enough that a shot would hit."""
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
    """True if a visible teammate sits in the shot corridor (friendly fire is ON)."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    tx, ty = target_pos
    rng = math.hypot(tx - sx, ty - sy)
    if rng < 1:
        return False
    ux, uy = (tx - sx) / rng, (ty - sy) / rng
    for mate in belief.teammates:
        mx, my = mate.pos
        along = (mx - sx) * ux + (my - sy) * uy
        if along <= 0 or along >= rng:
            continue
        perp = abs((mx - sx) * (-uy) + (my - sy) * ux)
        if perp <= FRIENDLY_FIRE_CORRIDOR_PX:
            return True
    return False


def _target_candidates(belief: Belief) -> tuple[TargetCandidate, ...]:
    """Visible gun targets with per-shooter geometry for fight.py."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    out: list[TargetCandidate] = []
    for enemy in belief.enemies:
        aim_pos, lead = _lead_aim_pos(belief, enemy)
        want = _brads_of(aim_pos[0] - sx, aim_pos[1] - sy)
        aim_cost = abs(_brad_error(want, belief.aim_brads)) / (AIM_BRADS_TURN // 2)
        line_clear = fight.line_clear(belief, belief.self_xy, aim_pos)
        teammate_blocked = _teammate_blocks_shot(belief, aim_pos)
        out.append(
            TargetCandidate(
                enemy=enemy,
                target=fight.target_ref_for(belief, enemy),
                aim_pos=aim_pos,
                lead_brads=lead,
                distance_px=math.hypot(enemy.pos[0] - sx, enemy.pos[1] - sy),
                aim_cost=aim_cost,
                line_clear=line_clear,
                teammate_blocked=teammate_blocked,
                shootable=line_clear and not teammate_blocked,
            )
        )
    return tuple(out)


# --- Peek-fire-duck micro -------------------------------------------------------------


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


def _fresh_heard_impact(belief: Belief) -> tuple[int, int] | None:
    """The nearest fresh heard impact within duck range, skipping our own fire line."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    best: tuple[int, int] | None = None
    best_d = float(HEARD_DUCK_RANGE_PX)
    aim_rad = belief.aim_brads / AIM_BRADS_TURN * 2 * math.pi
    ux, uy = math.cos(aim_rad), -math.sin(aim_rad)
    for ev in belief.heard_events:
        if belief.tick - ev.first_tick > HEARD_DUCK_FRESH_TICKS:
            continue
        dx, dy = ev.pos[0] - sx, ev.pos[1] - sy
        d = math.hypot(dx, dy)
        if d >= best_d:
            continue
        along = dx * ux + dy * uy
        if along > 0 and abs(dx * (-uy) + dy * ux) <= 24.0:
            continue  # on our own firing line — probably our own landing
        best = ev.pos
        best_d = d
    return best


def _predicted_pos(belief: Belief, track: PlayerTrack, tick: int) -> tuple[int, int]:
    """The track's velocity-extrapolated position now (clamped to the map)."""
    if track.vel is None:
        return track.pos
    dt = tick - track.last_tick
    return _clamp_to_map(
        belief,
        round(track.pos[0] + track.vel[0] * dt),
        round(track.pos[1] + track.vel[1] * dt),
    )


def _find_sidestep_cell(
    belief: Belief, self_xy: tuple[int, int], ref: tuple[int, int], *, want_los: bool
) -> tuple[int, int] | None:
    """Nearest reachable nav cell whose centre has (True) or breaks (False)
    line-of-sight to ``ref``."""
    wm = belief.worldmap
    assert wm is not None
    gx0, gy0 = wm.cell_of(*self_xy)
    best: tuple[int, int] | None = None
    best_d = float("inf")
    r = PEEK_DUCK_SEARCH_CELLS
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            nx, ny = gx0 + dx, gy0 + dy
            if not (0 <= nx < wm.grid_w and 0 <= ny < wm.grid_h) or not wm.walkable[ny, nx]:
                continue
            p = wm.cell_center(nx, ny)
            if not wm.walkable_segment(self_xy, p):
                continue
            if wm.ray_clear(p, ref) != want_los:
                continue
            d = (p[0] - self_xy[0]) ** 2 + (p[1] - self_xy[1]) ** 2
            if d < best_d:
                best_d = d
                best = p
    return best


def _has_viable_engagement(belief: Belief) -> bool:
    """Whether a visible enemy offers a clear, in-range weapon engagement."""
    if belief.i_have_arc:
        return _spray_target(belief) is not None
    return any(candidate.shootable for candidate in _target_candidates(belief))


def _cover_from_threat(
    belief: Belief,
    threat_pos: tuple[int, int],
    *,
    from_heard: bool,
    micro: str,
) -> tuple[int, int]:
    """Hold existing cover or take the nearest sidestep that breaks the threat ray."""
    assert belief.self_xy is not None and belief.worldmap is not None
    sx, sy = belief.self_xy
    aim = _brads_of(threat_pos[0] - sx, threat_pos[1] - sy)
    if not belief.worldmap.ray_clear(belief.self_xy, threat_pos):
        belief.micro = micro
        belief.heard_duck = from_heard
        return (0, aim)
    cover = _find_sidestep_cell(belief, belief.self_xy, threat_pos, want_los=False)
    if cover is None:
        return (0, aim)
    belief.micro = micro
    belief.heard_duck = from_heard
    return (nav.octant_toward(belief.self_xy, cover, False), aim)


def _peek_duck_override(intent: Intent, belief: Belief) -> tuple[int, int | None] | None:
    """Threat-relative safety movement, plus the offensive peek that exits it."""
    assert belief.self_xy is not None and belief.team is not None
    if belief.worldmap is None:
        return None
    if belief.i_carry_heart_of is not None or intent.reason in (
        "carry_home",
        "clear_grenade",
        "fetch_medkit",
        "intercept_thief",
        "intercept_thief_heard",
    ):
        return None
    sx, sy = belief.self_xy
    if (
        intent.reason == "steal"
        and intent.point is not None
        and math.hypot(intent.point[0] - sx, intent.point[1] - sy)
        <= PEEK_DUCK_RUSH_EXEMPT_PX
    ):
        return None

    if not belief.fire_ready:
        # DUCK: gun is down and a fresh threat is near -> break its line and hold,
        # keeping the aim (vision cone) on the threat's arc.
        threat = _fresh_track(belief, DUCK_THREAT_FRESH_TICKS, DUCK_RANGE_PX)
        from_heard = False
        if threat is not None:
            tpos = _predicted_pos(belief, threat, belief.tick)
        else:
            heard = _fresh_heard_impact(belief) if HEARING else None
            if heard is None:
                return None
            from_heard = True
            tpos = heard
        cover = _cover_from_threat(belief, tpos, from_heard=from_heard, micro="duck")
        if belief.micro is None:
            return None  # no cover nearby — fight in the open as before
        return cover

    allow_cover = (
        intent.kind == "hold"
        or belief.under_fire
        or (HEARING and _fresh_heard_impact(belief) is not None)
    )

    if belief.enemies:
        if _has_viable_engagement(belief):
            return None
        threat = _fresh_track(belief, DUCK_THREAT_FRESH_TICKS, DUCK_RANGE_PX)
        tpos = (
            _predicted_pos(belief, threat, belief.tick)
            if threat is not None
            else _nearest_enemy(belief).pos
        )
        if not belief.worldmap.ray_clear(belief.self_xy, tpos):
            peek = _find_sidestep_cell(belief, belief.self_xy, tpos, want_los=True)
            if peek is not None:
                belief.micro = "peek"
                return (
                    nav.octant_toward(belief.self_xy, peek, False),
                    _brads_of(tpos[0] - sx, tpos[1] - sy),
                )
        if not allow_cover:
            return None
        cover = _cover_from_threat(belief, tpos, from_heard=False, micro="cover")
        return cover if belief.micro is not None else None

    # No visible enemies: PEEK a remembered target from cover, or get safe.
    target = _fresh_track(belief, PEEK_TARGET_FRESH_TICKS)
    if target is None:
        heard = _fresh_heard_impact(belief) if HEARING else None
        if heard is None:
            return None
        cover = _cover_from_threat(belief, heard, from_heard=True, micro="cover")
        return cover if belief.micro is not None else None
    tpos = _predicted_pos(belief, target, belief.tick)
    if belief.worldmap.ray_clear(belief.self_xy, tpos):
        if not allow_cover:
            return None
        cover = _cover_from_threat(belief, tpos, from_heard=False, micro="cover")
        return cover if belief.micro is not None else None
    aim = _brads_of(tpos[0] - sx, tpos[1] - sy)
    peek = _find_sidestep_cell(belief, belief.self_xy, tpos, want_los=True)
    if peek is None:
        return None
    belief.micro = "peek"
    if math.hypot(peek[0] - sx, peek[1] - sy) < 5.0:
        return (0, aim)  # on the peek cell; hold and let the aim settle
    return (nav.octant_toward(belief.self_xy, peek, False), aim)


def resolve_action(intent: Intent, belief: Belief, state: ActionState) -> Command:
    """Compose the controller mask for this frame."""
    mask = 0
    state.last_rot = 0
    belief.micro = None
    belief.heard_duck = False

    if belief.self_xy is None or belief.worldmap is None:
        state.a_held = False
        belief.lead_brads = 0
        belief.throw_charge_ticks = 0
        belief.throw_target = None
        belief.throw_reason = None
        belief.throw_enemy_count = 0
        belief.throw_live_target = False
        return Command(held_mask=0)

    self_xy = belief.self_xy
    wm = belief.worldmap
    carrying = belief.i_carry_heart_of is not None

    # --- Peek-fire-duck micro: may override movement + supply a desired aim ---
    override = _peek_duck_override(intent, belief) if PEEK_DUCK else None

    # --- Movement (decoupled from aim) --------------------------------------------
    # Post-trigger freeze: the bullet leaves FIRE_WINDUP_TICKS after the pull
    # from our CURRENT position along the LOCKED angle; stand still until it's out.
    freeze = state.fire_hold_ticks > 0 and not carrying
    if state.fire_hold_ticks > 0:
        state.fire_hold_ticks -= 1
    if freeze:
        pass
    elif override is not None:
        mask |= override[0]
    elif intent.kind == "navigate_to" and intent.point is not None:
        if intent.reason in _FLOW_REASONS:
            waypoint = wm.flow_waypoint(intent.point, self_xy)
        else:
            waypoint = nav.astar_waypoint(belief, self_xy, intent.point)
        nav.note_progress(belief, self_xy)
        # Squad formation bias (opt-in): blend cohesion/separation into the step.
        if (
            SQUADS
            and intent.reason
            in ("steal", "to_hold", "order_to_hold", "order_push", "order_hunt")
            and not carrying
        ):
            bias = squads.formation_bias(belief)
            if bias is not None:
                biased_waypoint = (
                    int(waypoint[0] + bias[0] * NAV_CELL * 3),
                    int(waypoint[1] + bias[1] * NAV_CELL * 3),
                )
                if wm.walkable_segment(self_xy, biased_waypoint):
                    belief.squad_cohesion_ticks += 1
                    waypoint = biased_waypoint
        jitter = belief.nav_stuck_ticks >= STUCK_TICKS
        mask |= nav.octant_toward(self_xy, waypoint, jitter)
    elif intent.kind == "hold" and not carrying:
        # Separation while HOLDING: push-apart is the only movement a hold makes
        # (stacked holders eat shared grenade splash and block each other's shots).
        sep = squads.separation_bias(belief)
        if sep is not None:
            step = (
                int(self_xy[0] + sep[0] * NAV_CELL * 2),
                int(self_xy[1] + sep[1] * NAV_CELL * 2),
            )
            if wm.walkable_segment(self_xy, step):
                belief.squad_cohesion_ticks += 1
                mask |= nav.octant_toward(self_xy, step, False)

    # --- Combat overlay: aim + fire -----------------------------------------------
    selected = (
        fight.select_target(belief, _target_candidates(belief))
        if FIREFIGHT and belief.firefight_active and not belief.i_have_arc
        else None
    )
    enemy = (
        _spray_target(belief)
        if belief.i_have_arc
        else (selected.candidate.enemy if selected is not None else _nearest_enemy(belief))
    )
    if enemy is not None:
        if belief.i_have_arc:
            aim_pos, lead = _spray_aim_pos(belief, enemy), 0
        elif selected is not None:
            aim_pos = selected.candidate.aim_pos
            lead = selected.candidate.lead_brads
        else:
            aim_pos, lead = _lead_aim_pos(belief, enemy)
        belief.lead_brads = lead
        want = _brads_of(aim_pos[0] - self_xy[0], aim_pos[1] - self_xy[1])
        err = _brad_error(want, belief.aim_brads)
        if belief.i_have_arc:
            rng = math.hypot(enemy.pos[0] - self_xy[0], enemy.pos[1] - self_xy[1])
            if ARC_IDEAL_RANGE_PX < rng <= ARC_PURSUIT_RANGE_PX and not carrying:
                belief.spray_pursuit_ticks += 1
                mask &= ~(
                    int(Button.UP)
                    | int(Button.DOWN)
                    | int(Button.LEFT)
                    | int(Button.RIGHT)
                )
                mask |= nav.octant_toward(self_xy, enemy.pos, False)
            can_fire = (
                belief.fire_ready
                and _spray_contains(belief, aim_pos)
                and not _teammate_blocks_shot(belief, enemy.pos)
            )
        else:
            # ray_clear guards the GLASS WINDOWS: vision passes through glass but
            # bullets don't — firing through a window is a guaranteed miss.
            otherwise_fireable = (
                belief.fire_ready
                and _fire_gate(belief, aim_pos)
                and wm.ray_clear(self_xy, aim_pos)
            )
            teammate_blocked = otherwise_fireable and _teammate_blocks_shot(belief, aim_pos)
            if teammate_blocked and not state.a_held:
                belief.friendly_fire_suppressed += 1
            can_fire = otherwise_fireable and not teammate_blocked
        if can_fire and not state.a_held:
            # Freeze movement through gun windup so the release origin stays put.
            if not carrying:
                mask &= ~(int(Button.UP) | int(Button.DOWN) | int(Button.LEFT) | int(Button.RIGHT))
                state.fire_hold_ticks = FIRE_WINDUP_TICKS
            if abs(err) > AIM_TURN_RATE // 2:
                mask |= _rotation_button(err, state)
                belief.firing_turns += 1
            mask |= int(Button.A)
            state.a_held = True
            if not belief.i_have_arc:
                bucket = fight.range_bucket(
                    math.hypot(enemy.pos[0] - self_xy[0], enemy.pos[1] - self_xy[1])
                )
                belief.firefight_shot_range_counts[bucket] = (
                    belief.firefight_shot_range_counts.get(bucket, 0) + 1
                )
        else:
            state.a_held = False
            mask |= _rotation_button(err, state)
    else:
        state.a_held = False
        belief.lead_brads = 0
        if override is not None and override[1] is not None:
            target = override[1]
        else:
            target = _sweep_target(belief)
        err = _brad_error(target, belief.aim_brads)
        mask |= _rotation_button(err, state)

    # --- Grenade overlay ------------------------------------------------------------
    if GRENADE_THROW and belief.i_have_grenade and (not carrying or belief.throw_charge_ticks > 0):
        mask = _grenade_overlay(mask, belief, state)
    else:
        belief.throw_charge_ticks = 0
        belief.throw_target = None
        belief.throw_reason = None
        belief.throw_enemy_count = 0
        belief.throw_live_target = False

    return Command(held_mask=int(mask) & 0xFF)


@dataclass(frozen=True)
class _GrenadePlan:
    target: tuple[int, int]
    reason: str
    enemy_count: int
    live_target: bool
    rank: int
    distance_px: float


def _blast_safe(belief: Belief, target: tuple[int, int]) -> bool:
    """Whether fresh teammate evidence keeps the predicted blast corridor clear."""
    for track in belief.teammate_tracks:
        if belief.tick - track.last_tick > GRENADE_TEAMMATE_FRESH_TICKS:
            continue
        mate_pos = _predicted_pos(belief, track, belief.tick + GRENADE_FLIGHT_TICKS)
        if math.hypot(mate_pos[0] - target[0], mate_pos[1] - target[1]) <= (
            GRENADE_BLAST_RADIUS + 20.0
        ):
            return False
    return True


def _grenade_plan(belief: Belief, mask: int) -> _GrenadePlan | None:
    """Choose only targets where a grenade adds value the ordinary gun does not."""
    assert belief.self_xy is not None and belief.worldmap is not None
    sx, sy = belief.self_xy
    wm = belief.worldmap
    plans: list[_GrenadePlan] = []
    lives_left = squads.enemy_lives_left(belief)
    live_positions = tuple(enemy.pos for enemy in belief.enemies)

    def add_plan(
        target: tuple[int, int],
        *,
        reason: str,
        enemy_count: int,
        live_target: bool,
        rank: int,
    ) -> None:
        distance_px = math.hypot(target[0] - sx, target[1] - sy)
        if distance_px < GRENADE_MIN_THROW_PX or distance_px > wm.grenade_max_range:
            return
        if not _blast_safe(belief, target):
            belief.grenade_safety_vetoes += 1
            return
        plans.append(
            _GrenadePlan(
                target=target,
                reason=reason,
                enemy_count=enemy_count,
                live_target=live_target,
                rank=rank,
                distance_px=distance_px,
            )
        )

    for enemy in belief.enemies:
        enemy_count = sum(
            math.hypot(other[0] - enemy.pos[0], other[1] - enemy.pos[1])
            <= GRENADE_BLAST_RADIUS
            for other in live_positions
        )
        blocked = not wm.ray_clear(belief.self_xy, enemy.pos)
        thief = (
            belief.own_heart_stolen
            and belief.own_heart_thief_pos is not None
            and math.hypot(
                belief.own_heart_thief_pos[0] - enemy.pos[0],
                belief.own_heart_thief_pos[1] - enemy.pos[1],
            )
            <= GRENADE_BLAST_RADIUS
        )
        if blocked:
            reason, rank = "wall_blocked", 0
        elif enemy_count >= 2:
            reason, rank = "group", 1
        elif thief:
            reason, rank = "heart_thief", 2
        elif lives_left == 1:
            reason, rank = "final_life", 3
        elif (
            not belief.fire_ready
            and not enemy.shielded
            and enemy.hp_segments is not None
            and enemy.hp_segments <= GRENADE_SINGLE_HP_MAX
        ):
            reason, rank = "cooldown_finish", 4
        else:
            continue
        add_plan(
            enemy.pos,
            reason=reason,
            enemy_count=enemy_count,
            live_target=True,
            rank=rank,
        )

    fresh_tracks = [
        track
        for track in belief.enemy_tracks
        if 0 <= belief.tick - track.last_tick <= GRENADE_TARGET_FRESH_TICKS
    ]
    predicted = [
        _predicted_pos(belief, track, belief.tick + GRENADE_FLIGHT_TICKS)
        for track in fresh_tracks
    ]
    for t in belief.enemy_tracks:
        age = belief.tick - t.last_tick
        if age < 0 or age > GRENADE_TARGET_FRESH_TICKS or (age == 0 and belief.enemies):
            continue
        pos = _predicted_pos(belief, t, belief.tick + GRENADE_FLIGHT_TICKS)
        if wm.ray_clear(belief.self_xy, pos):
            continue
        enemy_count = sum(
            math.hypot(other[0] - pos[0], other[1] - pos[1]) <= GRENADE_BLAST_RADIUS
            for other in predicted
        )
        add_plan(
            pos,
            reason="wall_blocked",
            enemy_count=enemy_count,
            live_target=False,
            rank=0,
        )

    if not plans:
        return None
    aim = _post_input_aim(mask, belief)
    return min(
        plans,
        key=lambda plan: (
            plan.rank,
            -plan.enemy_count,
            abs(_brad_error(_brads_of(plan.target[0] - sx, plan.target[1] - sy), aim)),
            plan.distance_px,
        ),
    )


def _post_input_aim(mask: int, belief: Belief) -> int:
    aim = belief.aim_brads
    if mask & int(Button.B):
        return (aim + AIM_TURN_RATE) % AIM_BRADS_TURN
    if mask & int(Button.SELECT):
        return (aim - AIM_TURN_RATE) % AIM_BRADS_TURN
    return aim


def _refresh_live_throw_target(belief: Belief) -> tuple[tuple[int, int], int] | None:
    """Keep an authorized live throw attached to the same nearby visible body."""
    assert belief.throw_target is not None
    candidates = [
        enemy
        for enemy in belief.enemies
        if math.hypot(
            enemy.pos[0] - belief.throw_target[0],
            enemy.pos[1] - belief.throw_target[1],
        )
        <= GRENADE_BLAST_RADIUS + 20.0
        and _blast_safe(belief, enemy.pos)
    ]
    if not candidates:
        return None
    target = min(
        candidates,
        key=lambda enemy: (enemy.pos[0] - belief.throw_target[0]) ** 2
        + (enemy.pos[1] - belief.throw_target[1]) ** 2,
    )
    enemy_count = sum(
        math.hypot(other.pos[0] - target.pos[0], other.pos[1] - target.pos[1])
        <= GRENADE_BLAST_RADIUS
        for other in belief.enemies
    )
    return target.pos, enemy_count


def _grenade_overlay(mask: int, belief: Belief, state: ActionState) -> int:
    """Charge and release C for grenade-only-value targets."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    carrying = belief.i_carry_heart_of is not None
    charging = belief.throw_charge_ticks > 0
    if charging and carrying:
        return mask | BUTTON_C
    plan = _grenade_plan(belief, mask)

    if not charging:
        if plan is None:
            return mask
        belief.throw_target = plan.target
        belief.throw_reason = plan.reason
        belief.throw_enemy_count = plan.enemy_count
        belief.throw_live_target = plan.live_target
        belief.grenade_target_starts[plan.reason] = (
            belief.grenade_target_starts.get(plan.reason, 0) + 1
        )
        belief.grenade_targeted_enemies += plan.enemy_count
        if plan.live_target:
            belief.visible_grenade_starts += 1
        belief.throw_charge_ticks = 1
        return mask | BUTTON_C

    if belief.throw_live_target:
        refreshed = _refresh_live_throw_target(belief)
        if refreshed is not None:
            belief.throw_target, belief.throw_enemy_count = refreshed
    elif plan is not None and plan.live_target:
        belief.throw_target = plan.target
        belief.throw_reason = plan.reason
        belief.throw_enemy_count = plan.enemy_count
        belief.throw_live_target = True
    target = belief.throw_target or (sx, sy)
    belief.throw_charge_ticks += 1
    d = math.hypot(target[0] - sx, target[1] - sy)
    max_range = belief.worldmap.grenade_max_range if belief.worldmap else 247
    span = max(1, max_range - GRENADE_MIN_RANGE)
    charge_needed = min(
        GRENADE_CHARGE_TICKS,
        max(1, math.ceil((d - GRENADE_MIN_RANGE) / span * GRENADE_CHARGE_TICKS)),
    )
    want = _brads_of(target[0] - sx, target[1] - sy)
    overdue = belief.throw_charge_ticks >= GRENADE_CHARGE_TICKS + GRENADE_FORCE_RELEASE_TICKS

    if not belief.enemies and not belief.throw_live_target:
        # Own the aim while charging: replace any sweep rotation with the lob bearing.
        err = _brad_error(want, belief.aim_brads)
        mask &= ~(int(Button.B) | int(Button.SELECT))
        mask |= _rotation_button(err, state)

    release_aim = belief.aim_brads
    if mask & int(Button.B):
        release_aim = (release_aim + AIM_TURN_RATE) % AIM_BRADS_TURN
    elif mask & int(Button.SELECT):
        release_aim = (release_aim - AIM_TURN_RATE) % AIM_BRADS_TURN
    release_err = _brad_error(want, release_aim)
    ready = (
        belief.throw_charge_ticks >= charge_needed
        and abs(release_err) <= GRENADE_AIM_ERR_BRADS
        and (not belief.enemies or belief.throw_live_target)
        and _blast_safe(belief, target)
    )
    if ready or overdue:
        reason = belief.throw_reason or "unknown"
        belief.grenade_target_releases[reason] = (
            belief.grenade_target_releases.get(reason, 0) + 1
        )
        if overdue:
            belief.grenade_force_releases += 1
        if ready and belief.throw_live_target:
            belief.visible_grenade_releases += 1
        belief.throw_charge_ticks = 0
        belief.throw_target = None
        belief.throw_reason = None
        belief.throw_enemy_count = 0
        belief.throw_live_target = False
        return mask
    return mask | BUTTON_C


def _rotation_button(err: int, state: ActionState) -> int:
    """The aim-rotation button bit to close ``err`` (deadbanded)."""
    if abs(err) <= AIM_DEADBAND:
        state.last_rot = 0
        return 0
    if err > 0:  # target is CCW of current -> rotate CCW with B
        state.last_rot = 1
        return int(Button.B)
    state.last_rot = -1  # rotate CW with Select
    return int(Button.SELECT)


__all__ = ["resolve_action"]
