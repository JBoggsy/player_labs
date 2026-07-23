"""Belief update — fold a per-frame CtfState into the long-lived Belief.

Three genuinely stateful parts:

  * **Aim estimate**: the aim-dot sprite gives an absolute read (~2 brad resolution)
    but isn't always visible, so between reads we dead-reckon by the rotation we
    commanded last frame.
  * **Player tracks**: last-seen memory of every other player (enemy AND teammate).
    Sightings are associated to tracks by a reachability gate (how far the player
    could have moved since last seen), velocity is differenced + EMA-smoothed across
    close sightings, and tracks expire ``TRACK_TTL_TICKS`` after the last sighting.
  * **Danger field**: a scalar "an enemy could be here" field over the nav grid.
    Visible enemies stamp full heat; the field spreads one grid ring every
    ``NAV_CELL / (DANGER_DIFFUSION_FACTOR * max speed)`` ticks (walls block it, and
    per-axis velocity clamping makes a Chebyshev 3x3-max dilation the right spread
    metric), and cools with an exponential half-life so old heat fades instead of
    saturating the map. Initialized hot on the enemy half, cold on ours.

Tracks and the danger field are groundwork: **nothing gates on them yet** — they are
folded and traced so we can see what beacon believes before we act on it. Flag state
stays per-frame (pedestals never fog).

Known limits (acceptable for now): kills aren't in the percept, so a dead enemy's
track lingers until TTL; and our own vision clears nothing — a swept, provably-empty
corridor keeps its danger until it decays.
"""

from __future__ import annotations

import math

import numpy as np

from ctf.beacon import mapdata
from ctf.beacon.chat import decode as chat_decode
from ctf.beacon.items import update_items
from ctf.beacon.config import (
    AIM_BRADS_TURN,
    AIM_RESYNC_SLACK_BRADS,
    AIM_TURN_RATE,
    CHAT,
    CHAT_BUBBLE_DEDUP_TICKS,
    CHAT_ENEMY_BUBBLE_FIX,
    CHAT_FIX_TTL_TICKS,
    GRENADE_WARN_TTL_TICKS,
    HEARD_DANGER_HEAT,
    HEARD_DANGER_RADIUS_PX,
    HEARD_MATCH_PX,
    HEARD_TTL_TICKS,
    HEARING,
    UNDER_FIRE_FRESH_TICKS,
    UNDER_FIRE_RANGE_PX,
    CENTER_X,
    DANGER_DECAY_HALF_LIFE_TICKS,
    DANGER_DIFFUSION_FACTOR,
    DANGER_STAMP_RADIUS_PX,
    GRID_H,
    GRID_W,
    MAX_SPEED_PX_TICK,
    NAV_CELL,
    SPAWN_AIM,
    TRACK_MATCH_SLACK_PX,
    TRACK_TTL_TICKS,
    TRACK_VEL_EMA,
    TRACK_VEL_MAX_GAP_TICKS,
)
from ctf.beacon.types import ActionState, Belief, CtfState, Enemy, HeardImpact, PlayerTrack

#: Per-tick decay multiplier for the chosen half-life.
_DANGER_DECAY = 0.5 ** (1.0 / DANGER_DECAY_HALF_LIFE_TICKS)
#: Grid cells of danger spread owed per tick.
_SPREAD_CELLS_PER_TICK = DANGER_DIFFUSION_FACTOR * MAX_SPEED_PX_TICK / NAV_CELL
#: Stamp radius in whole cells around a visible enemy.
_STAMP_CELLS = max(DANGER_STAMP_RADIUS_PX // NAV_CELL, 1)


def update_belief(belief: Belief, percept: CtfState, action_state: ActionState, tick: int) -> None:
    """Mutate ``belief`` in place from this frame's percept."""
    belief.tick = tick
    was_alive = belief.alive
    belief.alive = percept.self_xy is not None
    if percept.self_xy is not None:
        belief.self_xy = percept.self_xy

    # Aim estimate: prefer the observed aim-dot read; else dead-reckon by the rotation
    # we commanded last frame. On (re)spawn, reseed to the spawn aim.
    if belief.team is not None and (not was_alive and belief.alive):
        belief.aim_brads = SPAWN_AIM[belief.team]
        belief.sweep_offset = 0
        belief.sweep_dir = 1
    # Dead-reckon by the commanded rotation, then calibrate against the observed
    # read. Since 0.7.8 the readback is the self sprite's 16-step rotation (16-brad
    # quantization, rounds to nearest), which gives two signals:
    #   * BOUNDARY CROSSING — the exact tick the observed step CHANGES while we are
    #     rotating, the true aim is at the midpoint boundary between the two steps
    #     (new_step*16 - 8 going CCW, + 8 going CW): an absolute ±(rate/2) fix.
    #   * COARSE RESYNC — any disagreement beyond the quantization (±8) is real
    #     drift (dropped frames, server-held masks); snap to the step read.
    belief.aim_brads = (belief.aim_brads + action_state.last_rot * AIM_TURN_RATE) % AIM_BRADS_TURN
    observed = percept.observed_aim
    if observed is not None:
        if (
            belief.prev_observed_aim is not None
            and observed != belief.prev_observed_aim
            and action_state.last_rot != 0
        ):
            boundary = (observed - action_state.last_rot * 8) % AIM_BRADS_TURN
            # True aim crossed `boundary` within the last tick; it has advanced at
            # most one rotation step past it since.
            belief.aim_brads = (boundary + action_state.last_rot * (AIM_TURN_RATE // 2)) % AIM_BRADS_TURN
        else:
            err = (observed - belief.aim_brads) % AIM_BRADS_TURN
            if err > AIM_BRADS_TURN // 2:
                err -= AIM_BRADS_TURN
            if abs(err) > AIM_RESYNC_SLACK_BRADS:
                belief.aim_brads = observed
        belief.prev_observed_aim = observed

    belief.fire_ready = percept.fire_ready
    belief.enemies = percept.enemies
    belief.teammates = percept.teammates
    belief.i_carry_enemy_flag = percept.i_carry_enemy_flag
    belief.enemy_flag_on_pedestal = percept.enemy_flag_on_pedestal
    belief.enemy_flag_pos = percept.enemy_flag_pos
    belief.own_flag_stolen = percept.own_flag_stolen
    belief.own_flag_thief_pos = percept.own_flag_thief_pos

    # Items (v10): our carried state is per-frame (the overhead markers ride us);
    # the spawn table folds sightings + line-of-sight refutations in items.py.
    belief.hp_pips = percept.hp_pips
    belief.i_have_grenade = percept.i_have_grenade
    belief.i_have_shield = percept.i_have_shield
    belief.i_have_arc = percept.i_have_arc
    update_items(belief, percept)

    # Folded memory (not gated on yet — see module docstring). Still ticked while
    # dead so tracks age out and danger decays on schedule — but since 0.7.x death
    # no longer lifts the fog (a dead viewer sees only terrain, pedestal hearts,
    # and its own corpse), a dead frame carries no sightings: tracks just age and
    # the danger field decays/spreads without fresh stamps.
    _update_tracks(belief.enemy_tracks, percept.enemies, tick)
    _update_tracks(belief.teammate_tracks, percept.teammates, tick)
    if HEARING:
        _update_heard(belief, percept, tick)
    _update_under_fire(belief, tick)
    if CHAT:
        _update_chat(belief, percept, tick)
    _update_danger(belief)


# --- Player tracks ------------------------------------------------------------------


def _update_tracks(tracks: list[PlayerTrack], sightings: tuple[Enemy, ...], tick: int) -> None:
    """Fold this frame's sightings into ``tracks`` (mutated in place).

    Greedy nearest-neighbour association: a sighting claims the closest unclaimed
    track the player could actually have reached since it was last seen (per-axis
    speed clamp => Chebyshev gate). Unmatched sightings start new tracks; tracks
    unseen for ``TRACK_TTL_TICKS`` are dropped.
    """
    unclaimed = set(range(len(tracks)))
    for s in sightings:
        best_i: int | None = None
        best_d2 = float("inf")
        for i in unclaimed:
            t = tracks[i]
            # Nameplate gate (0.7.69): a badge-identified sighting never claims a
            # track KNOWN to be a different player — identity beats proximity.
            if (
                s.identity is not None
                and t.identity is not None
                and s.identity != t.identity
            ):
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
                PlayerTrack(pos=s.pos, last_tick=tick, facing=s.facing, identity=s.identity)
            )
            continue
        unclaimed.discard(best_i)
        t = tracks[best_i]
        if s.identity is not None:
            t.identity = s.identity  # sticky nameplate identity (0.7.69)
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
            t.vel = None  # a long-gap re-sighting says nothing about current motion
        t.pos = s.pos
        t.facing = s.facing
        t.last_tick = tick
        t.frames_seen += 1
    tracks[:] = [t for t in tracks if tick - t.last_tick <= TRACK_TTL_TICKS]


# --- Hearing (v16) --------------------------------------------------------------------


def _update_heard(belief: Belief, percept: CtfState, tick: int) -> None:
    """Fold this frame's sound-ring sightings into deduplicated heard events.

    A ring persists ~12 ticks at a STABLE jittered position, so the same event is
    sighted every frame it lives; a sighting within ``HEARD_MATCH_PX`` of a known
    event of the same kind refreshes that event instead of creating a new one.
    Events expire ``HEARD_TTL_TICKS`` after their ring left the frame. Note dead
    players hear nothing (the server sends no rings), so death frames just age
    events out — no special-casing needed."""
    for kind, pos in percept.heard_impacts:
        matched = None
        for ev in belief.heard_events:
            if ev.kind == kind and max(abs(pos[0] - ev.pos[0]), abs(pos[1] - ev.pos[1])) <= HEARD_MATCH_PX:
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


# --- Chat (v18) -----------------------------------------------------------------------


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


def _update_chat(belief: Belief, percept: CtfState, tick: int) -> None:
    """Decode heard shout bubbles into belief (v18).

    Same-team payloads are trusted protocol traffic: E/T refresh enemy tracks
    (phantom sightings, no velocity), U stamps come via the danger path below,
    C sets the carrier fix, G registers a keep-clear zone. Enemy bubbles are
    never decoded as truth, but the bubble position itself is a live enemy fix
    (±20px) — sighting-grade, fed to the same track fold.

    A bubble persists ~3s (≈72 frames); dedup on (sender, text) so each shout is
    processed once. Our own bubble comes back too — skip our own address by
    matching our last-sent text (we don't know our own address string).
    """
    for team, address, text, bubble_pos in percept.heard_shouts:
        prev = belief.chat_processed.get(address)
        if prev is not None and prev[0] == text and tick - prev[1] <= CHAT_BUBBLE_DEDUP_TICKS:
            belief.chat_processed[address] = (text, tick)
            continue
        belief.chat_processed[address] = (text, tick)

        if team != belief.team:
            # An enemy shouted: their payload is untrusted, their position isn't.
            if CHAT_ENEMY_BUBBLE_FIX:
                _update_tracks(
                    belief.enemy_tracks,
                    (Enemy(pos=bubble_pos, facing="left"),),
                    tick,
                )
                belief.chat_heard_counts["enemy_bubble"] = (
                    belief.chat_heard_counts.get("enemy_bubble", 0) + 1
                )
            continue

        if text == belief.chat_last_sent_text:
            continue  # our own bubble echoing back
        msg = chat_decode(text)
        if msg is None:
            continue
        belief.chat_heard_counts[msg.kind] = belief.chat_heard_counts.get(msg.kind, 0) + 1
        if msg.kind in ("enemy", "thief"):
            _update_tracks(
                belief.enemy_tracks, (Enemy(pos=msg.pos, facing="left"),), tick
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
    """Raise danger to at least ``heat`` in a blob around ``pos`` (walkable-masked
    on the next _update_danger pass)."""
    if belief.danger is None:
        return
    cells = max(radius_px // NAV_CELL, 1)
    gx = min(max(pos[0] // NAV_CELL, 0), GRID_W - 1)
    gy = min(max(pos[1] // NAV_CELL, 0), GRID_H - 1)
    region = belief.danger[
        max(gy - cells, 0) : gy + cells + 1, max(gx - cells, 0) : gx + cells + 1
    ]
    np.maximum(region, heat, out=region)


# --- Danger field -------------------------------------------------------------------


def _init_danger(team: str) -> np.ndarray:
    """Fresh danger grid: full heat on every walkable cell of the enemy half."""
    cell_x = np.arange(GRID_W, dtype=np.float32) * NAV_CELL + NAV_CELL // 2
    enemy_side = cell_x > CENTER_X if team == "red" else cell_x < CENTER_X
    danger = np.zeros((GRID_H, GRID_W), dtype=np.float32)
    danger[:, enemy_side] = 1.0
    danger *= mapdata.walkable_grid()
    return danger


def _chebyshev_dilate(danger: np.ndarray) -> np.ndarray:
    """3x3 max filter — one grid ring of spread. Separable: vertical then horizontal."""
    v = danger.copy()
    np.maximum(v[1:, :], danger[:-1, :], out=v[1:, :])
    np.maximum(v[:-1, :], danger[1:, :], out=v[:-1, :])
    out = v.copy()
    np.maximum(out[:, 1:], v[:, :-1], out=out[:, 1:])
    np.maximum(out[:, :-1], v[:, 1:], out=out[:, :-1])
    return out


def _update_danger(belief: Belief) -> None:
    """One tick of the danger field: decay -> spread -> stamp -> wall mask."""
    assert belief.team is not None
    if belief.danger is None:
        belief.danger = _init_danger(belief.team)
    danger = belief.danger
    danger *= _DANGER_DECAY

    walkable = mapdata.walkable_grid()
    belief.danger_spread_carry += _SPREAD_CELLS_PER_TICK
    while belief.danger_spread_carry >= 1.0:
        # Mask each ring so heat can't hop a thin wall across two dilations.
        danger = _chebyshev_dilate(danger) * walkable
        belief.danger_spread_carry -= 1.0

    for enemy in belief.enemies:
        gx = min(max(enemy.pos[0] // NAV_CELL, 0), GRID_W - 1)
        gy = min(max(enemy.pos[1] // NAV_CELL, 0), GRID_H - 1)
        danger[
            max(gy - _STAMP_CELLS, 0) : gy + _STAMP_CELLS + 1,
            max(gx - _STAMP_CELLS, 0) : gx + _STAMP_CELLS + 1,
        ] = 1.0

    # Heard fire stamps too (v16): weaker heat (team-anonymous — could be our own
    # fire landing) over a wider blob (±20px jitter + the shooter being somewhere
    # with LoS, not at the spot). Stamp only events FIRST heard this tick — the
    # ring persists ~12 frames and re-stamping every frame would out-shout decay.
    heard_cells = max(HEARD_DANGER_RADIUS_PX // NAV_CELL, 1)
    for ev in belief.heard_events:
        if ev.first_tick != belief.tick:
            continue
        gx = min(max(ev.pos[0] // NAV_CELL, 0), GRID_W - 1)
        gy = min(max(ev.pos[1] // NAV_CELL, 0), GRID_H - 1)
        region = danger[
            max(gy - heard_cells, 0) : gy + heard_cells + 1,
            max(gx - heard_cells, 0) : gx + heard_cells + 1,
        ]
        np.maximum(region, HEARD_DANGER_HEAT, out=region)

    danger *= walkable  # walls never hold heat (also clears wall cells a stamp hit)
    belief.danger = danger


__all__ = ["update_belief"]
