"""Belief update — fold a per-frame PaintState into the long-lived Belief.

The stateful parts (aim dead-reckoning, player tracks, danger field, hearing,
chat decode, firefight hysteresis) port from beacon; the paintbot-specific
additions are:

  * **Color lock** — the slot-dealt color guess is corrected by the first
    ``self <color>`` sighting; the seat/role re-derive on the lock.
  * **Multi-team hearts** — per-color heart states, our own stolen-heart fix,
    retirement detection (captured/eliminated hearts leave play), and the
    steal-target choice (nearest live enemy heart by walkable route).
  * **WorldMap-derived geometry** — the danger field sizes itself to the
    episode grid and initializes hot outside our home half; the anti-turtle
    "outside its base" test uses endzone geometry instead of BASE_FRONT_X.
"""

from __future__ import annotations

import math

import numpy as np

from paintbot.stencil import fight
from paintbot.stencil.chat import decode as chat_decode
from paintbot.stencil.config import (
    AIM_BRADS_TURN,
    AIM_RESYNC_SLACK_BRADS,
    AIM_TURN_RATE,
    CHAT,
    CHAT_BUBBLE_DEDUP_TICKS,
    CHAT_ENEMY_BUBBLE_FIX,
    CHAT_FIX_TTL_TICKS,
    DANGER_DECAY_HALF_LIFE_TICKS,
    DANGER_DIFFUSION_FACTOR,
    DANGER_STAMP_RADIUS_PX,
    GRENADE_WARN_TTL_TICKS,
    HEARD_DANGER_HEAT,
    HEARD_DANGER_RADIUS_PX,
    HEARD_MATCH_PX,
    HEARD_TTL_TICKS,
    HEARING,
    MAX_SPEED_PX_TICK,
    NAV_CELL,
    REJOIN_TIMEOUT_TICKS,
    SQUAD_COMMAND,
    TRACK_MATCH_SLACK_PX,
    TRACK_TTL_TICKS,
    TRACK_VEL_EMA,
    TRACK_VEL_MAX_GAP_TICKS,
    UNDER_FIRE_FRESH_TICKS,
    UNDER_FIRE_RANGE_PX,
)
from paintbot.stencil.items import update_items
from paintbot.stencil.types import (
    ActionState,
    Belief,
    Enemy,
    HeardImpact,
    PaintState,
    PlayerTrack,
)

#: Per-tick decay multiplier for the chosen half-life.
_DANGER_DECAY = 0.5 ** (1.0 / DANGER_DECAY_HALF_LIFE_TICKS)
#: Grid cells of danger spread owed per tick.
_SPREAD_CELLS_PER_TICK = DANGER_DIFFUSION_FACTOR * MAX_SPEED_PX_TICK / NAV_CELL
#: Stamp radius in whole cells around a visible enemy.
_STAMP_CELLS = max(DANGER_STAMP_RADIUS_PX // NAV_CELL, 1)


def update_belief(belief: Belief, percept: PaintState, action_state: ActionState, tick: int) -> None:
    """Mutate ``belief`` in place from this frame's percept."""
    belief.tick = tick
    was_alive = belief.alive
    belief.alive = percept.self_xy is not None
    if percept.self_xy is not None:
        belief.self_xy = percept.self_xy
    if not was_alive and belief.alive:
        belief.respawned_tick = tick

    # Color lock: the slot-dealt guess is corrected by the first self sighting.
    # Seat re-derives with the real color (slot mod teams gave the color; the
    # seat, slot div teams, is unchanged — only the color can be wrong).
    if (
        not belief.color_locked
        and percept.self_color is not None
        and percept.self_color != belief.team
    ):
        belief.team = percept.self_color
        belief.color_locked = True
        belief.steal_target = None  # re-choose relative to the real home
    elif percept.self_color is not None:
        belief.color_locked = True

    # Respawn discipline: on DEATH, snapshot where to regroup; on RESPAWN, enter
    # rejoin mode toward it.
    if SQUAD_COMMAND:
        from paintbot.stencil import squads as _squads

        if was_alive and not belief.alive:
            belief.rejoin_point = _squads.rejoin_target(belief)
            belief.rejoin_until = -1
        elif not was_alive and belief.alive and belief.rejoin_point is not None:
            belief.rejoin_until = tick + REJOIN_TIMEOUT_TICKS

    # Aim estimate: dead-reckon by the commanded rotation; on (re)spawn, reseed
    # to the derived spawn aim (home -> center).
    if belief.team is not None and (not was_alive and belief.alive):
        if belief.worldmap is not None:
            belief.aim_brads = belief.worldmap.spawn_aim(belief.team)
        belief.sweep_offset = 0
        belief.sweep_dir = 1
    belief.aim_brads = (belief.aim_brads + action_state.last_rot * AIM_TURN_RATE) % AIM_BRADS_TURN
    observed = percept.observed_aim
    if observed is not None:
        err = (observed - belief.aim_brads) % AIM_BRADS_TURN
        if err > AIM_BRADS_TURN // 2:
            err -= AIM_BRADS_TURN
        if abs(err) > AIM_RESYNC_SLACK_BRADS:
            # A stale/duplicated input can only move the server aim in whole
            # AIM_TURN_RATE steps; pick the nearest compatible correction.
            compatible: list[tuple[int, int]] = []
            for steps in range(-8, 9):
                candidate = (belief.aim_brads + steps * AIM_TURN_RATE) % AIM_BRADS_TURN
                candidate_err = (observed - candidate) % AIM_BRADS_TURN
                if candidate_err > AIM_BRADS_TURN // 2:
                    candidate_err -= AIM_BRADS_TURN
                if abs(candidate_err) <= AIM_RESYNC_SLACK_BRADS:
                    compatible.append((abs(steps), steps))
            if compatible:
                steps = min(compatible)[1]
                belief.aim_brads = (belief.aim_brads + steps * AIM_TURN_RATE) % AIM_BRADS_TURN
                belief.aim_resyncs += 1
        belief.prev_observed_aim = observed

    belief.fire_ready = percept.fire_ready
    belief.enemies = percept.enemies
    belief.teammates = percept.teammates

    _update_hearts(belief, percept)

    # Team scoreboard: fold monotonically per color.
    for color, score in percept.team_scores.items():
        belief.team_scores[color] = score

    # Items: our carried state is per-frame; the discovered spawn table folds
    # sightings + line-of-sight refutations in items.py.
    belief.hp_pips = percept.hp_pips
    belief.i_have_grenade = percept.i_have_grenade
    belief.i_have_shield = percept.i_have_shield
    belief.i_have_arc = percept.i_have_arc
    update_items(belief, percept)

    _update_tracks(belief.enemy_tracks, percept.enemies, tick, belief.worldmap)
    _update_tracks(belief.teammate_tracks, percept.teammates, tick, belief.worldmap)
    if HEARING:
        _update_heard(belief, percept, tick)
    _update_under_fire(belief, tick)
    if CHAT:
        _update_chat(belief, percept, tick)
    _update_danger(belief)
    fight.update_firefight(belief)


# --- Hearts --------------------------------------------------------------------------


def _update_hearts(belief: Belief, percept: PaintState) -> None:
    """Fold per-color heart states + our own carry/stolen view, and choose the
    steal target (nearest live enemy heart by walkable route)."""
    belief.hearts = percept.hearts
    belief.i_carry_heart_of = percept.i_carry_heart_of
    team = belief.team
    wm = belief.worldmap

    # Pedestal learning: a planted heart's position IS its pedestal.
    if wm is not None:
        for color, state in percept.hearts.items():
            if state.planted and state.pos is not None:
                wm.pedestals[color] = state.pos

    # Retirement: a heart with neither sprite AND an exhausted team is out of
    # play (captured -> team eliminated, or wiped -> heart retired). A missing
    # heart with a LIVE team is just carried under fog.
    if wm is not None:
        total = wm.team_total_lives()
        for color, state in percept.hearts.items():
            if color in belief.hearts_retired:
                continue
            if state.planted or state.carried_pos is not None:
                continue
            score = belief.team_scores.get(color)
            if score is not None and total - score[1] <= 0:
                belief.hearts_retired.add(color)

    # Our own heart.
    if team is not None and team in percept.hearts:
        own = percept.hearts[team]
        belief.own_heart_stolen = not own.planted and team not in belief.hearts_retired
        belief.own_heart_thief_pos = own.carried_pos if belief.own_heart_stolen else None
    else:
        belief.own_heart_stolen = False
        belief.own_heart_thief_pos = None

    # Steal target: the nearest live enemy heart by walkable route from our
    # home (stable within an episode phase; re-chosen when the current target
    # retires or was never set).
    if team is not None and wm is not None:
        if belief.steal_target is not None and belief.steal_target in belief.hearts_retired:
            belief.steal_target = None
        if belief.steal_target is None:
            candidates = [
                color
                for color in belief.colors
                if color != team and color not in belief.hearts_retired
            ]
            if candidates:
                home = wm.home_center(team)
                belief.steal_target = min(
                    candidates,
                    key=lambda color: wm.route_distance(home, wm.pedestal(color)),
                )


# --- Player tracks ------------------------------------------------------------------


def _update_tracks(
    tracks: list[PlayerTrack],
    sightings: tuple[Enemy, ...],
    tick: int,
    worldmap,
) -> None:
    """Fold this frame's sightings into ``tracks`` (mutated in place)."""
    unclaimed = set(range(len(tracks)))
    for s in sightings:
        best_i: int | None = None
        best_d2 = float("inf")
        for i in unclaimed:
            t = tracks[i]
            if (
                s.identity is not None
                and t.identity is not None
                and (s.identity != t.identity or s.color != t.color)
            ):
                continue
            if t.color != s.color and t.identity is not None:
                continue
            dt = tick - t.last_tick
            gate = dt * MAX_SPEED_PX_TICK + TRACK_MATCH_SLACK_PX
            dx = s.pos[0] - t.pos[0]
            dy = s.pos[1] - t.pos[1]
            if max(abs(dx), abs(dy)) > gate:
                continue
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_d2 = d2
                best_i = i
        if best_i is None:
            tracks.append(
                PlayerTrack(
                    pos=s.pos,
                    last_tick=tick,
                    facing=s.facing,
                    color=s.color,
                    identity=s.identity,
                    hp_segments=s.hp_segments,
                    shielded=s.shielded,
                )
            )
            continue
        unclaimed.discard(best_i)
        t = tracks[best_i]
        t.color = s.color
        if s.identity is not None:
            t.identity = s.identity
        if s.hp_segments is not None:
            t.hp_segments = s.hp_segments
        t.shielded = s.shielded
        dt = tick - t.last_tick
        if 0 < dt <= TRACK_VEL_MAX_GAP_TICKS:
            vx = (s.pos[0] - t.pos[0]) / dt
            vy = (s.pos[1] - t.pos[1]) / dt
            if t.vel is None:
                t.vel = (vx, vy)
            else:
                t.vel = (
                    t.vel[0] + (vx - t.vel[0]) * TRACK_VEL_EMA,
                    t.vel[1] + (vy - t.vel[1]) * TRACK_VEL_EMA,
                )
        elif dt > TRACK_VEL_MAX_GAP_TICKS:
            t.vel = None
        t.pos = s.pos
        t.facing = s.facing
        t.last_tick = tick
        t.frames_seen += 1
    tracks[:] = [t for t in tracks if tick - t.last_tick <= TRACK_TTL_TICKS]


# --- Hearing --------------------------------------------------------------------------


def _update_heard(belief: Belief, percept: PaintState, tick: int) -> None:
    """Fold this frame's sound-ring sightings into deduplicated heard events."""
    for kind, pos in percept.heard_impacts:
        matched = None
        for ev in belief.heard_events:
            if ev.kind == kind and max(
                abs(pos[0] - ev.pos[0]), abs(pos[1] - ev.pos[1])
            ) <= HEARD_MATCH_PX:
                matched = ev
                break
        if matched is not None:
            matched.last_tick = tick
        else:
            belief.heard_events.append(
                HeardImpact(kind=kind, pos=pos, first_tick=tick, last_tick=tick)
            )
    belief.heard_events[:] = [
        ev for ev in belief.heard_events if tick - ev.last_tick <= HEARD_TTL_TICKS
    ]


# --- Chat -----------------------------------------------------------------------------


def _update_under_fire(belief: Belief, tick: int) -> None:
    """True when a fresh heard impact landed within UNDER_FIRE_RANGE_PX of us."""
    belief.under_fire = False
    if belief.self_xy is None:
        return
    sx, sy = belief.self_xy
    for ev in belief.heard_events:
        if tick - ev.first_tick > UNDER_FIRE_FRESH_TICKS:
            continue
        if math.hypot(ev.pos[0] - sx, ev.pos[1] - sy) <= UNDER_FIRE_RANGE_PX:
            belief.under_fire = True
            return


def _update_chat(belief: Belief, percept: PaintState, tick: int) -> None:
    """Decode heard shout bubbles into belief.

    Same-team payloads are trusted protocol traffic; enemy bubbles are never
    decoded as truth, but the bubble position itself is a live enemy fix.
    """
    if belief.worldmap is None:
        return
    wm = belief.worldmap
    for team, address, text, bubble_pos in percept.heard_shouts:
        key = f"{team} {address}"
        prev = belief.chat_processed.get(key)
        if prev is not None and prev[0] == text and tick - prev[1] <= CHAT_BUBBLE_DEDUP_TICKS:
            belief.chat_processed[key] = (text, tick)
            continue
        belief.chat_processed[key] = (text, tick)

        if team != belief.team:
            if CHAT_ENEMY_BUBBLE_FIX:
                _update_tracks(
                    belief.enemy_tracks,
                    (Enemy(pos=bubble_pos, facing="left", color=team),),
                    tick,
                    wm,
                )
                belief.chat_heard_counts["enemy_bubble"] = (
                    belief.chat_heard_counts.get("enemy_bubble", 0) + 1
                )
            continue

        if text == belief.chat_last_sent_text:
            continue  # our own bubble echoing back
        msg = chat_decode(wm, text)
        if msg is None:
            continue
        belief.chat_heard_counts[msg.kind] = belief.chat_heard_counts.get(msg.kind, 0) + 1
        if msg.kind == "order":
            from paintbot.stencil import squads as _squads

            if msg.seat == _squads.leader_of(belief) and msg.seat != belief.seat:
                belief.order = (msg.goal or "H", msg.pos, tick)
                belief.order_source = "heard"
                belief.orders_heard += 1
            if msg.seat is not None:
                belief.presence[msg.seat] = tick
        elif msg.kind == "ping":
            if msg.seat is not None:
                belief.presence[msg.seat] = tick
                belief.pings_heard += 1
        elif msg.kind == "focus_claim":
            if msg.seat is not None:
                fight.receive_focus_claim(
                    belief,
                    claimant_seat=msg.seat,
                    target_identity=msg.target_identity,
                    target_cell=msg.pos,
                )
        elif msg.kind in ("enemy", "thief"):
            _update_tracks(
                belief.enemy_tracks,
                (Enemy(pos=msg.pos, facing="left"),),
                tick,
                wm,
            )
            if msg.kind == "thief":
                belief.thief_fix = (msg.pos, tick)
        elif msg.kind == "carrier":
            belief.carrier_fix = (msg.pos, msg.heading or 0, tick)
        elif msg.kind == "grenade":
            belief.grenade_warnings.append((msg.pos, tick))
        elif msg.kind == "under_fire":
            _stamp_danger_blob(belief, msg.pos, HEARD_DANGER_HEAT, HEARD_DANGER_RADIUS_PX)

    # Expiry.
    if belief.carrier_fix is not None and tick - belief.carrier_fix[2] > CHAT_FIX_TTL_TICKS:
        belief.carrier_fix = None
    if belief.thief_fix is not None and tick - belief.thief_fix[1] > CHAT_FIX_TTL_TICKS:
        belief.thief_fix = None
    belief.grenade_warnings[:] = [
        (p, t) for (p, t) in belief.grenade_warnings if tick - t <= GRENADE_WARN_TTL_TICKS
    ]


def _stamp_danger_blob(belief: Belief, pos: tuple[int, int], heat: float, radius_px: int) -> None:
    """Raise danger to at least ``heat`` in a blob around ``pos``."""
    if belief.danger is None or belief.worldmap is None:
        return
    wm = belief.worldmap
    cells = max(radius_px // NAV_CELL, 1)
    gx, gy = wm.cell_of(*pos)
    region = belief.danger[
        max(gy - cells, 0) : gy + cells + 1, max(gx - cells, 0) : gx + cells + 1
    ]
    np.maximum(region, heat, out=region)


# --- Danger field -------------------------------------------------------------------


def _init_danger(belief: Belief) -> np.ndarray:
    """Fresh danger grid: full heat on every walkable cell OUTSIDE our home half.

    "Our half" generalizes across layouts as the set of cells whose straight-line
    distance to our home centre is less than to the map centre — a crude
    Voronoi split that works for sides, corners, and plus layouts alike."""
    wm = belief.worldmap
    assert wm is not None and belief.team is not None
    hx, hy = wm.home_center(belief.team)
    cx, cy = wm.center
    ys, xs = np.mgrid[0 : wm.grid_h, 0 : wm.grid_w]
    px = xs * NAV_CELL + NAV_CELL // 2
    py = ys * NAV_CELL + NAV_CELL // 2
    ours = (px - hx) ** 2 + (py - hy) ** 2 < (px - cx) ** 2 + (py - cy) ** 2
    danger = np.ones((wm.grid_h, wm.grid_w), dtype=np.float32)
    danger[ours] = 0.0
    danger *= wm.walkable
    return danger


def _chebyshev_dilate(danger: np.ndarray) -> np.ndarray:
    """3x3 max filter — one grid ring of spread. Separable."""
    v = danger.copy()
    np.maximum(v[1:, :], danger[:-1, :], out=v[1:, :])
    np.maximum(v[:-1, :], danger[1:, :], out=v[:-1, :])
    out = v.copy()
    np.maximum(out[:, 1:], v[:, :-1], out=out[:, 1:])
    np.maximum(out[:, :-1], v[:, 1:], out=out[:, :-1])
    return out


def _update_danger(belief: Belief) -> None:
    """One tick of the danger field: decay -> spread -> stamp -> wall mask."""
    wm = belief.worldmap
    if wm is None or belief.team is None:
        return
    if belief.danger is None or belief.danger.shape != (wm.grid_h, wm.grid_w):
        belief.danger = _init_danger(belief)
    danger = belief.danger
    danger *= _DANGER_DECAY

    walkable = wm.walkable
    belief.danger_spread_carry += _SPREAD_CELLS_PER_TICK
    while belief.danger_spread_carry >= 1.0:
        danger = _chebyshev_dilate(danger) * walkable
        belief.danger_spread_carry -= 1.0

    for enemy in belief.enemies:
        gx, gy = wm.cell_of(*enemy.pos)
        danger[
            max(gy - _STAMP_CELLS, 0) : gy + _STAMP_CELLS + 1,
            max(gx - _STAMP_CELLS, 0) : gx + _STAMP_CELLS + 1,
        ] = 1.0

    heard_cells = max(HEARD_DANGER_RADIUS_PX // NAV_CELL, 1)
    for ev in belief.heard_events:
        if ev.first_tick != belief.tick:
            continue
        gx, gy = wm.cell_of(*ev.pos)
        region = danger[
            max(gy - heard_cells, 0) : gy + heard_cells + 1,
            max(gx - heard_cells, 0) : gx + heard_cells + 1,
        ]
        np.maximum(region, HEARD_DANGER_HEAT, out=region)

    danger *= walkable
    belief.danger = danger


__all__ = ["update_belief"]
