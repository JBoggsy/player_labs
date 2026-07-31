"""Action resolution — turn an Intent + Belief into an 8-bit controller mask.

This is where the tactical design lives (§3, §5):

  * **Movement**: step toward the navigation waypoint (flow-field or A*) as a d-pad
    octant. Movement is fully decoupled from aim.
  * **Aim (the lighthouse)**: default is a sweep panning ±SWEEP_HALF_ARC across the
    *threat axis* (unit vector from us toward the enemy pedestal). A settled post
    instead dwells on its primary and shoulder baked sightlines. The moment an enemy
    is visible, either sweep aborts and aim snaps onto the nearest enemy by default,
    or fight.py's intentional scored target while firefight is enabled.
  * **Fire**: press A (edge-triggered) when an enemy is visible, the gun is ready,
    and the shot geometry clears the fire-gate (aim close enough that the shot ray
    passes through the target). Never rotate on the firing tick, so the locked aim
    is the settled one.

The rotation we command is recorded in ActionState.last_rot so belief.py can
dead-reckon the aim estimate between aim-dot reads.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ctf.beacon import fight, mapdata, nav, posts, squads
from ctf.beacon.config import (
    AIM_BRADS_TURN,
    AIM_DEADBAND,
    AIM_TURN_RATE,
    ARC_FIRE_RANGE_PX,
    ARC_IDEAL_RANGE_PX,
    ARC_MAX_WIDTH_PX,
    ARC_PURSUIT_RANGE_PX,
    BASE_FRONT_X,
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
    GRENADE_FORCE_RELEASE_TICKS,
    GRENADE_FLIGHT_TICKS,
    GRENADE_MAX_RANGE,
    GRENADE_MIN_RANGE,
    GRENADE_MIN_THROW_PX,
    GRENADE_SINGLE_HP_MAX,
    GRENADE_TEAMMATE_FRESH_TICKS,
    GRENADE_TARGET_FRESH_TICKS,
    GRENADE_THROW,
    GRID_H,
    GRID_W,
    HEARD_DUCK_FRESH_TICKS,
    HEARD_DUCK_RANGE_PX,
    HEARING,
    LEAD_AIM,
    LEAD_MIN_FRAMES,
    LEAD_TICKS,
    NAV_CELL,
    PEDESTAL,
    PEEK_DUCK,
    PEEK_DUCK_RUSH_EXEMPT_PX,
    PEEK_DUCK_SEARCH_CELLS,
    PEEK_TARGET_FRESH_TICKS,
    POST_FACING,
    POST_SCAN_DWELL_TICKS,
    POST_SETTLE_PX,
    SQUADS,
    STUCK_TICKS,
    SWEEP_HALF_ARC,
)
from ctf.beacon.types import (
    ActionState,
    Belief,
    Command,
    Enemy,
    Intent,
    PlayerTrack,
    TargetCandidate,
)
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


def _spray_target(belief: Belief) -> Enemy | None:
    """Best visible body for the immediate, live-tracking spray cone.

    Gun lead is actively harmful here: spray resolves immediately from the
    current aim, then follows that aim for four more ticks. Prefer a clear body
    already closest to the cone centre, without changing movement or item logic.
    """
    if belief.self_xy is None:
        return None
    sx, sy = belief.self_xy
    candidates = [
        enemy
        for enemy in belief.enemies
        if math.hypot(enemy.pos[0] - sx, enemy.pos[1] - sy)
        <= ARC_PURSUIT_RANGE_PX
        and mapdata.ray_clear(belief.self_xy, enemy.pos)
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


def _spray_aim_pos(
    belief: Belief,
    enemy: Enemy,
) -> tuple[int, int]:
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
    from ctf.beacon.config import MAP_H, MAP_W

    return (
        min(max(round(enemy.pos[0] + track.vel[0]), 0), MAP_W - 1),
        min(max(round(enemy.pos[1] + track.vel[1]), 0), MAP_H - 1),
    )


def _spray_contains(
    belief: Belief,
    target_pos: tuple[int, int],
) -> bool:
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
        and perpendicular
        <= forward * ARC_MAX_WIDTH_PX / (2 * ARC_FIRE_RANGE_PX)
    )


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
    """Advance the lighthouse sweep one step and return the desired aim (brads).

    Squad sectors (v19): each rank's sweep centre is offset from the threat axis
    (rank 0 on-axis, ranks 1/2 on the shoulders) so a squad covers a forward cone
    plus flanks instead of three copies of one arc."""
    post_facing = (
        POST_FACING
        and belief.post_active
        and belief.post_direction is not None
        and belief.post_settled_ticks > 0
    )
    if post_facing:
        # A post is position + a small vocabulary of useful baked sightlines.
        # Dwell on those actual corridors instead of continuously sweeping walls.
        assert belief.post_cell is not None and belief.post_direction is not None
        lanes = posts.scan_directions(belief.post_cell, belief.post_direction)
        index = (belief.tick // POST_SCAN_DWELL_TICKS + belief.seat) % len(lanes)
        belief.post_scan_direction = lanes[index]
        belief.sweep_offset = 0
        return posts.direction_to_brads(belief.post_scan_direction)

    belief.post_scan_direction = None
    axis = _threat_axis(belief)
    half_arc = SWEEP_HALF_ARC
    if SQUADS and not post_facing:
        axis = (axis + squads.sector_offset_brads(belief.seat)) % AIM_BRADS_TURN
    belief.sweep_offset += belief.sweep_dir * AIM_TURN_RATE
    if belief.sweep_offset >= half_arc:
        belief.sweep_offset = half_arc
        belief.sweep_dir = -1
    elif belief.sweep_offset <= -half_arc:
        belief.sweep_offset = -half_arc
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
    close range where the corridor is wide relative to the distance. Range itself
    is not a veto: a sufficiently well-aligned, unobstructed shot may fire anywhere
    on the map.
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


def _target_candidates(belief: Belief) -> tuple[TargetCandidate, ...]:
    """Visible gun targets with cheap per-shooter geometry for fight.py.

    The baked sightline field answers the bullet-wall question for every
    candidate without per-target raycasting. resolve_action retains one exact
    ray_clear check for the selected target before firing.
    """
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    out: list[TargetCandidate] = []
    for enemy in belief.enemies:
        aim_pos, lead = _lead_aim_pos(belief, enemy)
        want = _brads_of(aim_pos[0] - sx, aim_pos[1] - sy)
        aim_cost = abs(_brad_error(want, belief.aim_brads)) / (
            AIM_BRADS_TURN // 2
        )
        line_clear = fight.baked_line_clear(belief.self_xy, aim_pos)
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


def _fresh_heard_impact(belief: Belief) -> tuple[int, int] | None:
    """The nearest fresh heard impact within duck range (v16), or None.

    Own-fire suppression: an impact along OUR current aim ray is very likely our
    own shot landing — ducking from ourselves every time we miss would freeze the
    push. Skip impacts within the friendly-fire corridor of our aim direction."""
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
            if not nav.walkable_segment(self_xy, p):
                continue  # can't walk straight there
            if mapdata.ray_clear(p, ref) != want_los:
                continue
            d = (p[0] - self_xy[0]) ** 2 + (p[1] - self_xy[1]) ** 2
            if d < best_d:
                best_d = d
                best = p
    return best


def _has_viable_engagement(belief: Belief) -> bool:
    """Whether a visible enemy offers a clear, in-range weapon engagement.

    This deliberately ignores current aim error: turning onto a valid target is
    productive combat, not idle exposure, and safety movement must not suppress it.
    """
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
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    aim = _brads_of(threat_pos[0] - sx, threat_pos[1] - sy)
    if not mapdata.ray_clear(belief.self_xy, threat_pos):
        belief.micro = micro
        belief.heard_duck = from_heard
        return (0, aim)
    cover = _find_sidestep_cell(belief.self_xy, threat_pos, want_los=False)
    if cover is None:
        if micro not in ("cover", "base_cover"):
            return (0, aim)
        # The tiny duck search intentionally avoids long tactical detours. When
        # it finds no full ray break, fall back to the existing post vocabulary:
        # a bounded nearby fighting position with a useful lane and flank cover
        # toward this threat. This is what lets non-post objectives leave exposed
        # open ground without turning safety into a retreat across the map.
        axis = posts.threat_axis(belief, belief.self_xy, facing=threat_pos)
        post = posts.choose_post(
            belief,
            belief.self_xy,
            axis.direction,
            mode="hold",
        )
        if post is None:
            return (0, aim)
        cover = post.cell
    belief.micro = micro
    belief.heard_duck = from_heard
    return (nav.octant_toward(belief.self_xy, cover, False), aim)


def _committed_post_home(
    intent: Intent,
    belief: Belief,
) -> tuple[int, int] | None:
    if (
        intent.reason in (
            "plan_post",
            "anti_turtle_post",
            "base_caution_post",
            "order_post",
            "hold_post",
        )
        and belief.post_committed
        and belief.post_cell is not None
    ):
        return belief.post_cell
    return None


def _fresh_base_threat(belief: Belief) -> PlayerTrack | None:
    """Fresh enemy evidence still behind the defended lineup."""
    if not (belief.anti_turtle_latched or belief.base_caution_active):
        return None
    enemy_team = "blue" if belief.team == "red" else "red"
    front_x = BASE_FRONT_X[enemy_team]
    tracks = [
        track
        for track in belief.enemy_tracks
        if belief.tick - track.last_tick <= PEEK_TARGET_FRESH_TICKS
        and (
            track.pos[0] >= front_x
            if enemy_team == "blue"
            else track.pos[0] <= front_x
        )
    ]
    return max(tracks, key=lambda track: track.last_tick, default=None)


def _return_to_post(
    belief: Belief,
    home: tuple[int, int],
    aim: int | None,
) -> tuple[int, int | None]:
    """Return to the latched cover home, then stay still there."""
    assert belief.self_xy is not None
    belief.post_peek_cell = None
    if math.hypot(
        belief.self_xy[0] - home[0],
        belief.self_xy[1] - home[1],
    ) <= POST_SETTLE_PX:
        belief.micro = "post_hold"
        return (0, aim)
    belief.micro = "post_return"
    belief.post_return_ticks += 1
    return (nav.octant_toward(belief.self_xy, home, False), aim)


def _peek_from_post(
    belief: Belief,
    home: tuple[int, int],
    threat_pos: tuple[int, int],
) -> tuple[int, int | None]:
    """Move to one stable firing shoulder until contact opens or goes stale."""
    assert belief.self_xy is not None
    aim = _brads_of(
        threat_pos[0] - belief.self_xy[0],
        threat_pos[1] - belief.self_xy[1],
    )
    peek = belief.post_peek_cell
    if (
        peek is None
        or not mapdata.ray_clear(peek, threat_pos)
        or not nav.walkable_segment(home, peek)
    ):
        peek = _find_sidestep_cell(home, threat_pos, want_los=True)
        belief.post_peek_cell = peek
    if peek is None:
        return _return_to_post(belief, home, aim)
    if math.hypot(
        belief.self_xy[0] - peek[0],
        belief.self_xy[1] - peek[1],
    ) < 5.0:
        belief.micro = "post_peek_hold"
        return (0, aim)
    belief.micro = "post_peek"
    belief.post_peek_ticks += 1
    return (nav.octant_toward(belief.self_xy, peek, False), aim)


def _peek_duck_override(intent: Intent, belief: Belief) -> tuple[int, int | None] | None:
    """Threat-relative safety movement, plus the offensive peek that exits it.

    A gun-down agent ducks as before. A gun-ready agent with no viable visible
    engagement seeks/holds cover while idle on a hold, or while navigating under
    recent fire. From established cover it may still peek a remembered target so
    safety does not erase kill pressure.
    """
    assert belief.self_xy is not None and belief.team is not None
    if belief.i_carry_enemy_flag or intent.reason in (
        "carry_home",
        "clear_grenade",
        "fetch_medkit",
        "intercept_thief",
        "intercept_thief_heard",
    ):
        return None
    enemy = "blue" if belief.team == "red" else "red"
    steal = PEDESTAL[enemy]
    sx, sy = belief.self_xy
    post_home = _committed_post_home(intent, belief)
    if intent.reason == "steal" and math.hypot(steal[0] - sx, steal[1] - sy) <= PEEK_DUCK_RUSH_EXEMPT_PX:
        return None


    # A turtling or life-ahead enemy gets no reciprocal base sightline: break
    # its ray and hold rather than peeking or taking an otherwise viable shot.
    # Enemies that leave the base remain normal engagements.
    base_threat = _fresh_base_threat(belief)
    if base_threat is not None:
        return _cover_from_threat(
            belief,
            _predicted_pos(base_threat, belief.tick),
            from_heard=False,
            micro="base_cover",
        )

    if not belief.fire_ready:
        if post_home is not None:
            threat = _fresh_track(
                belief,
                DUCK_THREAT_FRESH_TICKS,
                DUCK_RANGE_PX,
            )
            if threat is None:
                aim = None
            else:
                threat_pos = _predicted_pos(threat, belief.tick)
                aim = _brads_of(threat_pos[0] - sx, threat_pos[1] - sy)
            return _return_to_post(belief, post_home, aim)
        # DUCK: gun is down and a fresh threat is near -> break its line and hold,
        # keeping the aim (vision cone) on the threat's arc. A threat is a fresh
        # SEEN track, or (v16 hearing) fresh fire LANDING near us — bullets
        # arriving here mean someone has an angle on our area even if we never
        # saw them; duck toward cover from the impact's direction.
        threat = _fresh_track(belief, DUCK_THREAT_FRESH_TICKS, DUCK_RANGE_PX)
        from_heard = False
        if threat is not None:
            tpos = _predicted_pos(threat, belief.tick)
        else:
            heard = _fresh_heard_impact(belief) if HEARING else None
            if heard is None:
                return None
            from_heard = True
            tpos = heard
        cover = _cover_from_threat(
            belief,
            tpos,
            from_heard=from_heard,
            micro="duck",
        )
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
            if (
                post_home is not None
                and math.hypot(sx - post_home[0], sy - post_home[1])
                > POST_SETTLE_PX
            ):
                # Hold the peek shoulder while aim settles and the shot winds up.
                belief.micro = "post_engage"
                return (0, None)
            return None
        threat = _fresh_track(belief, DUCK_THREAT_FRESH_TICKS, DUCK_RANGE_PX)
        tpos = (
            _predicted_pos(threat, belief.tick)
            if threat is not None
            else _nearest_enemy(belief).pos
        )
        if not mapdata.ray_clear(belief.self_xy, tpos):
            if post_home is not None:
                return _peek_from_post(belief, post_home, tpos)
            peek = _find_sidestep_cell(belief.self_xy, tpos, want_los=True)
            if peek is not None:
                belief.micro = "peek"
                return (
                    nav.octant_toward(belief.self_xy, peek, False),
                    _brads_of(tpos[0] - sx, tpos[1] - sy),
                )
        if not allow_cover:
            return None
        if post_home is not None:
            return _return_to_post(
                belief,
                post_home,
                _brads_of(tpos[0] - sx, tpos[1] - sy),
            )
        cover = _cover_from_threat(
            belief,
            tpos,
            from_heard=False,
            micro="cover",
        )
        return cover if belief.micro is not None else None

    if not belief.enemies:
        # PEEK from established cover; if the fresh track still has an open ray
        # to us, get safe first instead of standing exposed with no target.
        target = _fresh_track(belief, PEEK_TARGET_FRESH_TICKS)
        if target is None:
            heard = _fresh_heard_impact(belief) if HEARING else None
            if heard is None:
                if post_home is not None:
                    return _return_to_post(belief, post_home, None)
                return None
            if post_home is not None:
                return _return_to_post(
                    belief,
                    post_home,
                    _brads_of(heard[0] - sx, heard[1] - sy),
                )
            cover = _cover_from_threat(
                belief,
                heard,
                from_heard=True,
                micro="cover",
            )
            return cover if belief.micro is not None else None
        tpos = _predicted_pos(target, belief.tick)
        if mapdata.ray_clear(belief.self_xy, tpos):
            if not allow_cover:
                return None
            if post_home is not None:
                return _return_to_post(
                    belief,
                    post_home,
                    _brads_of(tpos[0] - sx, tpos[1] - sy),
                )
            cover = _cover_from_threat(
                belief,
                tpos,
                from_heard=False,
                micro="cover",
            )
            return cover if belief.micro is not None else None
        if post_home is not None:
            return _peek_from_post(belief, post_home, tpos)
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
    belief.heard_duck = False

    if belief.self_xy is None:  # dead / not ready — release everything
        state.a_held = False
        belief.lead_brads = 0
        belief.throw_charge_ticks = 0
        belief.throw_target = None
        belief.throw_reason = None
        belief.throw_enemy_count = 0
        belief.throw_live_target = False
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
        # Squad formation bias (v19): blend cohesion/separation into the waypoint
        # step. Exempt while carrying (run!), fetching (rejoin at the rally), or
        # chasing a dynamic target (intercept/escort override formation). v25:
        # the order-driven reasons (order_*) are included — v22-v24 never applied
        # separation to ordered movement, so squads stacked on the order point.
        if (
            intent.reason in (
                "plan_post",
                "anti_turtle_post",
                "base_caution_post",
                "order_post",
                "hold_post",
            )
            and not belief.i_carry_enemy_flag
            and not belief.post_committed
        ):
            # Posts replace cohesion with deliberate geometry, but separation
            # remains the floor while two bodies are still stacked en route.
            bias = squads.separation_bias(belief)
            if bias is not None:
                biased_waypoint = (
                    int(waypoint[0] + bias[0] * NAV_CELL * 3),
                    int(waypoint[1] + bias[1] * NAV_CELL * 3),
                )
                if nav.walkable_segment(self_xy, biased_waypoint):
                    belief.squad_cohesion_ticks += 1
                    waypoint = biased_waypoint
        elif (
            SQUADS
            and intent.reason
            in ("steal", "to_hold", "order_to_hold", "order_push", "order_hunt")
            and not belief.i_carry_enemy_flag
        ):
            bias = squads.formation_bias(belief)
            if bias is not None:
                biased_waypoint = (
                    int(waypoint[0] + bias[0] * NAV_CELL * 3),
                    int(waypoint[1] + bias[1] * NAV_CELL * 3),
                )
                if nav.walkable_segment(self_xy, biased_waypoint):
                    belief.squad_cohesion_ticks += 1
                    waypoint = biased_waypoint
        jitter = belief.nav_stuck_ticks >= STUCK_TICKS
        mask |= nav.octant_toward(self_xy, waypoint, jitter)
    elif (
        intent.kind == "hold"
        and (
            SQUADS
            or intent.reason
            in (
                "plan_post",
                "anti_turtle_post",
                "base_caution_post",
                "order_post",
                "hold_post",
            )
        )
        and not belief.i_carry_enemy_flag
        and not belief.post_committed
    ):
        # Separation while HOLDING (v25): a holding agent emits no movement, so
        # two stacked holders never unstack (FF kills at <15px, shared grenade
        # splash). Push-apart is the only movement a hold makes.
        sep = squads.separation_bias(belief)
        if sep is not None:
            step = (
                int(self_xy[0] + sep[0] * NAV_CELL * 2),
                int(self_xy[1] + sep[1] * NAV_CELL * 2),
            )
            if nav.walkable_segment(self_xy, step):
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
        else (
            selected.candidate.enemy
            if selected is not None
            else _nearest_enemy(belief)
        )
    )
    if enemy is not None:
        # Snap aim onto the target — led ahead of a moving one (v10): the windup
        # delays the bullet ~LEAD_TICKS, so aim where the target will BE.
        if belief.i_have_arc:
            # Spray is immediate and follows our live aim for five ticks. Aim at
            # the body one input-latency frame ahead; gun windup lead points the
            # narrow cone far ahead.
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
            # A spray carrier has no gun. Close locally on an already-visible,
            # unobstructed opponent until the real cone can reach; this is combat
            # footwork only, and the unchanged strategic intent resumes as soon
            # as contact leaves the bounded pursuit radius.
            rng = math.hypot(
                enemy.pos[0] - self_xy[0],
                enemy.pos[1] - self_xy[1],
            )
            if (
                ARC_IDEAL_RANGE_PX < rng <= ARC_PURSUIT_RANGE_PX
                and not belief.i_carry_enemy_flag
            ):
                belief.spray_pursuit_ticks += 1
                mask &= ~(
                    int(Button.UP)
                    | int(Button.DOWN)
                    | int(Button.LEFT)
                    | int(Button.RIGHT)
                )
                mask |= nav.octant_toward(self_xy, enemy.pos, False)
            # The gun is disabled while carrying spray: A ignites the cone.
            can_fire = (
                belief.fire_ready
                and _spray_contains(belief, aim_pos)
                and not _teammate_blocks_shot(belief, enemy.pos)
                and belief.micro != "base_cover"
            )
        else:
            # ray_clear guards the GLASS WINDOWS (GameVersion 15/16): vision passes
            # through glass but bullets don't, so a visible enemy is no longer a
            # shootable one — firing through a window is a guaranteed miss.
            otherwise_fireable = (
                belief.fire_ready
                and _fire_gate(belief, aim_pos)
                and mapdata.ray_clear(self_xy, aim_pos)
                and belief.micro != "base_cover"
            )
            teammate_blocked = (
                otherwise_fireable
                and _teammate_blocks_shot(belief, aim_pos)
            )
            if teammate_blocked and not state.a_held:
                belief.friendly_fire_suppressed += 1
            can_fire = otherwise_fireable and not teammate_blocked
        if can_fire and not state.a_held:
            # The server applies rotation before it locks a fresh A press. If one
            # five-brad step brings the target closer, turn and fire together:
            # this centres the shot without withholding a trigger. Freeze movement
            # through gun windup so the release origin stays where we aimed.
            if not belief.i_carry_enemy_flag:
                mask &= ~(int(Button.UP) | int(Button.DOWN) | int(Button.LEFT) | int(Button.RIGHT))
                state.fire_hold_ticks = FIRE_WINDUP_TICKS
            if abs(err) > AIM_TURN_RATE // 2:
                mask |= _rotation_button(err, state)
                belief.firing_turns += 1
            mask |= int(Button.A)
            state.a_held = True
            if not belief.i_have_arc:
                bucket = fight.range_bucket(
                    math.hypot(
                        enemy.pos[0] - self_xy[0],
                        enemy.pos[1] - self_xy[1],
                    )
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
            # Ducking/peeking: lay the aim on the remembered threat's arc so the
            # vision cone watches the lane (and a peek exits pre-aimed).
            target = override[1]
        else:
            # No enemy: lighthouse sweep across the threat axis.
            target = _sweep_target(belief)
        err = _brad_error(target, belief.aim_brads)
        mask |= _rotation_button(err, state)

    # --- Grenade overlay: spend the blast only where it adds tactical value ---------
    # C rides on top of the gun inputs. Flag carriers never start or release a throw.
    if (
        GRENADE_THROW
        and belief.i_have_grenade
        and (
            not belief.i_carry_enemy_flag
            or belief.throw_charge_ticks > 0
        )
    ):
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
        mate_pos = _predicted_pos(track, belief.tick + GRENADE_FLIGHT_TICKS)
        if math.hypot(mate_pos[0] - target[0], mate_pos[1] - target[1]) <= (
            GRENADE_BLAST_RADIUS + 20.0
        ):
            return False
    return True


def _post_input_aim(mask: int, belief: Belief) -> int:
    aim = belief.aim_brads
    if mask & int(Button.B):
        return (aim + AIM_TURN_RATE) % AIM_BRADS_TURN
    if mask & int(Button.SELECT):
        return (aim - AIM_TURN_RATE) % AIM_BRADS_TURN
    return aim


def _grenade_plan(belief: Belief, mask: int) -> _GrenadePlan | None:
    """Choose only targets where a grenade adds value the ordinary gun does not.

    Wall-blocked targets come first. A visible body is next only when centering the
    blast on it covers at least two enemies. Open singles are exceptional: the flag
    thief, the final enemy life, or a vulnerable unshielded target while the gun is
    cooling down. Visible plans retain the validated v48 contract: the grenade rides
    the gun's existing aim instead of stealing it.
    """
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
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
        if (
            distance_px < GRENADE_MIN_THROW_PX
            or distance_px > GRENADE_MAX_RANGE
        ):
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
        blocked = not mapdata.ray_clear(belief.self_xy, enemy.pos)
        thief = (
            belief.own_flag_stolen
            and belief.own_flag_thief_pos is not None
            and math.hypot(
                belief.own_flag_thief_pos[0] - enemy.pos[0],
                belief.own_flag_thief_pos[1] - enemy.pos[1],
            )
            <= GRENADE_BLAST_RADIUS
        )
        if blocked:
            reason, rank = "wall_blocked", 0
        elif enemy_count >= 2:
            reason, rank = "group", 1
        elif thief:
            reason, rank = "flag_thief", 2
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
        _predicted_pos(track, belief.tick + GRENADE_FLIGHT_TICKS)
        for track in fresh_tracks
    ]
    for t in belief.enemy_tracks:
        age = belief.tick - t.last_tick
        if (
            age < 0
            or age > GRENADE_TARGET_FRESH_TICKS
            or (age == 0 and belief.enemies)
        ):
            continue
        pos = _predicted_pos(t, belief.tick + GRENADE_FLIGHT_TICKS)
        if mapdata.ray_clear(belief.self_xy, pos):
            continue
        enemy_count = sum(
            math.hypot(other[0] - pos[0], other[1] - pos[1])
            <= GRENADE_BLAST_RADIUS
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
            abs(
                _brad_error(
                    _brads_of(plan.target[0] - sx, plan.target[1] - sy),
                    aim,
                )
            ),
            plan.distance_px,
        ),
    )


def _refresh_live_throw_target(
    belief: Belief,
) -> tuple[tuple[int, int], int] | None:
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
        key=lambda enemy: (
            enemy.pos[0] - belief.throw_target[0]
        ) ** 2 + (
            enemy.pos[1] - belief.throw_target[1]
        ) ** 2,
    )
    enemy_count = sum(
        math.hypot(other.pos[0] - target.pos[0], other.pos[1] - target.pos[1])
        <= GRENADE_BLAST_RADIUS
        for other in belief.enemies
    )
    return target.pos, enemy_count


def _grenade_overlay(mask: int, belief: Belief, state: ActionState) -> int:
    """Charge and release C for grenade-only-value targets.

    Prefer a fresh wall-blocked enemy, then a tight visible group. An open
    single is eligible only for the narrow finishing cases selected by
    ``_grenade_plan``. Visible targets keep the validated gun aim; hidden
    targets supply their own remembered/predicted aim.
    """
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    charging = belief.throw_charge_ticks > 0
    if charging and belief.i_carry_enemy_flag:
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
    span = max(1, GRENADE_MAX_RANGE - GRENADE_MIN_RANGE)
    charge_needed = min(
        GRENADE_CHARGE_TICKS,
        max(1, math.ceil((d - GRENADE_MIN_RANGE) / span * GRENADE_CHARGE_TICKS)),
    )
    want = _brads_of(target[0] - sx, target[1] - sy)
    err = _brad_error(want, belief.aim_brads)
    overdue = belief.throw_charge_ticks >= GRENADE_CHARGE_TICKS + GRENADE_FORCE_RELEASE_TICKS

    if not belief.enemies and not belief.throw_live_target:
        # Own the aim while charging: replace any sweep rotation with the lob bearing.
        mask &= ~(int(Button.B) | int(Button.SELECT))
        mask |= _rotation_button(err, state)

    # Rotation is applied before a C release, just as it is before an A press.
    # Judge the actual post-input bearing so the correcting turn and throw can
    # happen together instead of adding another stale-target frame.
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
        # Release: C up this tick throws along the current aim.
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
