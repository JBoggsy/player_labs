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

import numpy as np

from ctf.beacon import mapdata
from ctf.beacon.config import (
    AIM_BRADS_TURN,
    AIM_TURN_RATE,
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
from ctf.beacon.types import ActionState, Belief, CtfState, Enemy, PlayerTrack

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
    if percept.observed_aim is not None:
        belief.aim_brads = percept.observed_aim
    else:
        belief.aim_brads = (belief.aim_brads + action_state.last_rot * AIM_TURN_RATE) % AIM_BRADS_TURN

    belief.fire_ready = percept.fire_ready
    belief.enemies = percept.enemies
    belief.teammates = percept.teammates
    belief.i_carry_enemy_flag = percept.i_carry_enemy_flag
    belief.enemy_flag_on_pedestal = percept.enemy_flag_on_pedestal
    belief.enemy_flag_pos = percept.enemy_flag_pos
    belief.own_flag_stolen = percept.own_flag_stolen
    belief.own_flag_thief_pos = percept.own_flag_thief_pos

    # Folded memory (not gated on yet — see module docstring). Still ticked while
    # dead so tracks age out and danger decays on schedule — but since 0.7.x death
    # no longer lifts the fog (a dead viewer sees only terrain, pedestal hearts,
    # and its own corpse), a dead frame carries no sightings: tracks just age and
    # the danger field decays/spreads without fresh stamps.
    _update_tracks(belief.enemy_tracks, percept.enemies, tick)
    _update_tracks(belief.teammate_tracks, percept.teammates, tick)
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
            tracks.append(PlayerTrack(pos=s.pos, last_tick=tick, facing=s.facing))
            continue
        unclaimed.discard(best_i)
        t = tracks[best_i]
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

    danger *= walkable  # walls never hold heat (also clears wall cells a stamp hit)
    belief.danger = danger


__all__ = ["update_belief"]
