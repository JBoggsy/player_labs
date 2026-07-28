"""Covered sightlines near tactical waypoints.

A post is a nav-cell-centred position plus the direction it exists to watch.
Waypoints remain the plan's search centres; this module uses the baked sightline
field, live danger/tracks, teammate K claims, and stance intent to choose the
nearby ground worth fighting from.

Runtime selection performs bounded array lookups over roughly 600 cells. It never
casts rays: the offline bake is the single source for both forward reach and
directional flank cover. Geometry mirrors ``sim.nim`` through ``bake_map.py``;
direction 0 is east and indices advance counter-clockwise on screen.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

from ctf.beacon import mapdata
from ctf.beacon.config import (
    GRID_H,
    GRID_W,
    NAV_CELL,
    PEDESTAL,
    POST_CLAIM_TTL_TICKS,
    POST_COVER_CAP_PX,
    POST_COVER_WEIGHT,
    POST_DANGER_GRADIENT_MIN,
    POST_DANGER_GRADIENT_PX,
    POST_DANGER_WEIGHT,
    POST_ENEMY_OCCUPIED_PX,
    POST_FLANK_DIRECTION_OFFSET,
    POST_MIN_COVER_SCORE,
    POST_MIN_DWELL_TICKS,
    POST_MIN_REACH_PX,
    POST_MIN_SCORE,
    POST_MIN_SEPARATION_PX,
    POST_REACH_WEIGHT,
    POST_REEVALUATE_TICKS,
    POST_SEARCH_RADIUS_PX,
    POST_SETTLE_PX,
    POST_STANCE_WEIGHT,
    POST_SWITCH_MARGIN,
    POST_THREAT_FRESH_TICKS,
    POST_THREAT_HYSTERESIS_DIRECTIONS,
    SIGHTLINE_BRADS_PER_DIRECTION,
    SIGHTLINE_CAP_PX,
    SIGHTLINE_DIRECTIONS,
    SIGHTLINE_DISTANCE_UNIT_PX,
    STUCK_TICKS,
)
from ctf.beacon.types import Belief

PostMode = Literal["push", "hold"]


@dataclass(frozen=True)
class ThreatAxis:
    """One quantised threat bearing and the live/prior source that selected it."""

    direction: int
    source: str


@dataclass(frozen=True)
class Post:
    """One selected fighting position and its traceable score decomposition."""

    cell: tuple[int, int]
    direction: int
    score: float
    reach: float
    cover: float
    stance: float
    danger: float
    claim_source: str


@dataclass(frozen=True)
class _Candidate:
    cell: tuple[int, int]
    score: float
    reach: float
    cover: float
    stance: float
    danger: float


def direction_to_brads(direction: int) -> int:
    """Convert a 32-way direction to aim brads."""
    return (direction % SIGHTLINE_DIRECTIONS) * SIGHTLINE_BRADS_PER_DIRECTION


def sightline(cell: tuple[int, int], direction: int) -> int:
    """Baked free distance from ``cell`` along ``direction``, in map pixels."""
    gx = min(max(cell[0] // NAV_CELL, 0), GRID_W - 1)
    gy = min(max(cell[1] // NAV_CELL, 0), GRID_H - 1)
    units = mapdata.sightline_field()[direction % SIGHTLINE_DIRECTIONS, gy, gx]
    return int(units) * SIGHTLINE_DISTANCE_UNIT_PX


def cover_toward(cell: tuple[int, int], threat_direction: int) -> float:
    """Directional flank cover in [0, 1] for a threat bearing.

    A useful post has a long ray ALONG the threat bearing but a short ray on at
    least one ±45° flank: a nearby wall to duck behind, rather than a wall
    directly between the bot and the lane it needs to watch.
    """
    left = sightline(cell, threat_direction + POST_FLANK_DIRECTION_OFFSET)
    right = sightline(cell, threat_direction - POST_FLANK_DIRECTION_OFFSET)
    nearest = min(left, right, POST_COVER_CAP_PX)
    return 1.0 - nearest / POST_COVER_CAP_PX


def _direction_toward(origin: tuple[int, int], target: tuple[int, int]) -> int:
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    angle = math.atan2(-dy, dx)
    return round(angle / (2 * math.pi) * SIGHTLINE_DIRECTIONS) % SIGHTLINE_DIRECTIONS


def _danger_gradient(belief: Belief, center: tuple[int, int]) -> tuple[float, float]:
    if belief.danger is None:
        return (0.0, 0.0)
    radius = max(POST_DANGER_GRADIENT_PX // NAV_CELL, 1)
    gx = min(max(center[0] // NAV_CELL, 0), GRID_W - 1)
    gy = min(max(center[1] // NAV_CELL, 0), GRID_H - 1)
    west = float(belief.danger[gy, max(gx - radius, 0)])
    east = float(belief.danger[gy, min(gx + radius, GRID_W - 1)])
    north = float(belief.danger[max(gy - radius, 0), gx])
    south = float(belief.danger[min(gy + radius, GRID_H - 1), gx])
    return (east - west, south - north)


def threat_axis(
    belief: Belief,
    center: tuple[int, int],
    *,
    facing: tuple[int, int] | None = None,
) -> ThreatAxis:
    """Choose live enemy evidence over plan/pedestal priors, then quantise it.

    Same-team E shouts already fold into enemy tracks. U shouts deliberately do
    not become bearings: they contain the friendly under-fire position, not the
    shooter, and influence this choice only through their danger stamp.
    """
    fresh_tracks = [
        track
        for track in belief.enemy_tracks
        if belief.tick - track.last_tick <= POST_THREAT_FRESH_TICKS
    ]
    if fresh_tracks:
        track = min(
            fresh_tracks,
            key=lambda item: (
                -item.last_tick,
                (item.pos[0] - center[0]) ** 2 + (item.pos[1] - center[1]) ** 2,
            ),
        )
        return ThreatAxis(_direction_toward(center, track.pos), "enemy_track")

    danger_dx, danger_dy = _danger_gradient(belief, center)
    if math.hypot(danger_dx, danger_dy) >= POST_DANGER_GRADIENT_MIN:
        target = (
            round(center[0] + danger_dx * POST_DANGER_GRADIENT_PX),
            round(center[1] + danger_dy * POST_DANGER_GRADIENT_PX),
        )
        return ThreatAxis(_direction_toward(center, target), "danger_gradient")

    if facing is not None and facing != center:
        return ThreatAxis(_direction_toward(center, facing), "plan_facing")

    team = belief.team
    assert team is not None
    enemy = "blue" if team == "red" else "red"
    return ThreatAxis(_direction_toward(center, PEDESTAL[enemy]), "enemy_pedestal")


def _candidate_arrays(
    belief: Belief,
    center: tuple[int, int],
    threat_direction: int,
    mode: PostMode,
) -> tuple[np.ndarray, ...]:
    walkable = mapdata.walkable_grid()
    field = mapdata.sightline_field()
    center_gx = min(max(center[0] // NAV_CELL, 0), GRID_W - 1)
    center_gy = min(max(center[1] // NAV_CELL, 0), GRID_H - 1)
    radius_cells = math.ceil(POST_SEARCH_RADIUS_PX / NAV_CELL)

    grid_y, grid_x = np.mgrid[
        max(0, center_gy - radius_cells) : min(GRID_H, center_gy + radius_cells + 1),
        max(0, center_gx - radius_cells) : min(GRID_W, center_gx + radius_cells + 1),
    ]
    cell_x = grid_x * NAV_CELL + NAV_CELL // 2
    cell_y = grid_y * NAV_CELL + NAV_CELL // 2
    distance_sq = (cell_x - center[0]) ** 2 + (cell_y - center[1]) ** 2
    valid = walkable[grid_y, grid_x] & (distance_sq <= POST_SEARCH_RADIUS_PX**2)

    grid_x = grid_x[valid]
    grid_y = grid_y[valid]
    cell_x = cell_x[valid]
    cell_y = cell_y[valid]
    distance_sq = distance_sq[valid]

    reach_px = (
        field[threat_direction, grid_y, grid_x].astype(np.float32)
        * SIGHTLINE_DISTANCE_UNIT_PX
    )
    reach = np.minimum(reach_px, SIGHTLINE_CAP_PX) / SIGHTLINE_CAP_PX
    flank_left = (
        field[
            (threat_direction + POST_FLANK_DIRECTION_OFFSET) % SIGHTLINE_DIRECTIONS,
            grid_y,
            grid_x,
        ].astype(np.float32)
        * SIGHTLINE_DISTANCE_UNIT_PX
    )
    flank_right = (
        field[
            (threat_direction - POST_FLANK_DIRECTION_OFFSET) % SIGHTLINE_DIRECTIONS,
            grid_y,
            grid_x,
        ].astype(np.float32)
        * SIGHTLINE_DISTANCE_UNIT_PX
    )
    flank = np.minimum(np.minimum(flank_left, flank_right), POST_COVER_CAP_PX)
    cover = 1.0 - flank / POST_COVER_CAP_PX

    angle = 2 * math.pi * threat_direction / SIGHTLINE_DIRECTIONS
    ux, uy = math.cos(angle), -math.sin(angle)
    stance = np.clip(
        ((cell_x - center[0]) * ux + (cell_y - center[1]) * uy)
        / POST_SEARCH_RADIUS_PX,
        -1.0,
        1.0,
    )
    if mode == "hold":
        stance = -stance

    if belief.danger is None:
        danger = np.zeros(reach.shape, dtype=np.float32)
    else:
        danger = belief.danger[grid_y, grid_x].astype(np.float32)
    score = (
        POST_REACH_WEIGHT * reach
        + POST_COVER_WEIGHT * cover
        + POST_STANCE_WEIGHT * stance
        - POST_DANGER_WEIGHT * danger
    )
    qualifies = (
        (reach_px >= POST_MIN_REACH_PX)
        & (cover >= POST_MIN_COVER_SCORE)
        & (score >= POST_MIN_SCORE)
    )
    return (
        grid_x[qualifies],
        grid_y[qualifies],
        cell_x[qualifies],
        cell_y[qualifies],
        distance_sq[qualifies],
        score[qualifies],
        reach[qualifies],
        cover[qualifies],
        stance[qualifies],
        danger[qualifies],
    )


def _ranked_candidates(
    belief: Belief,
    center: tuple[int, int],
    threat_direction: int,
    mode: PostMode,
) -> list[_Candidate]:
    (
        grid_x,
        grid_y,
        cell_x,
        cell_y,
        distance_sq,
        score,
        reach,
        cover,
        stance,
        danger,
    ) = _candidate_arrays(belief, center, threat_direction, mode)
    order = np.lexsort((grid_x, grid_y, distance_sq, -cover, -reach, -score))
    return [
        _Candidate(
            cell=(int(cell_x[i]), int(cell_y[i])),
            score=float(score[i]),
            reach=float(reach[i]),
            cover=float(cover[i]),
            stance=float(stance[i]),
            danger=float(danger[i]),
        )
        for i in order
    ]


def _near(a: tuple[int, int], b: tuple[int, int], radius: int) -> bool:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 < radius * radius


def _within(a: tuple[int, int], b: tuple[int, int], radius: int) -> bool:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= radius * radius


def choose_post(
    belief: Belief,
    center: tuple[int, int],
    threat_direction: int,
    *,
    mode: PostMode,
) -> Post | None:
    """Choose the best distinct post not owned by a lower seat or teammate.

    Greedy 56px non-maximum suppression defines the ranked post vocabulary
    before live exclusions. Exact-cell claims would merely move a pile onto
    adjacent 8px cells, so both K claims and visible teammates reserve the full
    separation radius.
    """
    ranked: list[tuple[int, int]] = []
    displaced_by: str | None = None
    lower_claims = [
        claim
        for seat, claim in belief.post_claims.items()
        if seat < belief.seat and belief.tick - claim.tick <= POST_CLAIM_TTL_TICKS
    ]
    teammates = [teammate.pos for teammate in belief.teammates]
    enemies = [enemy.pos for enemy in belief.enemies]

    for candidate in _ranked_candidates(belief, center, threat_direction, mode):
        if any(_near(candidate.cell, prior, POST_MIN_SEPARATION_PX) for prior in ranked):
            continue
        ranked.append(candidate.cell)

        claim = next(
            (
                item
                for item in lower_claims
                if _near(candidate.cell, item.cell, POST_MIN_SEPARATION_PX)
            ),
            None,
        )
        if claim is not None:
            displaced_by = displaced_by or f"heard_K:{claim.seat}"
            continue
        if any(_near(candidate.cell, pos, POST_MIN_SEPARATION_PX) for pos in teammates):
            displaced_by = displaced_by or "visible_teammate"
            continue
        if any(_near(candidate.cell, pos, POST_ENEMY_OCCUPIED_PX) for pos in enemies):
            displaced_by = displaced_by or "visible_enemy"
            continue
        return Post(
            cell=candidate.cell,
            direction=threat_direction,
            score=candidate.score,
            reach=candidate.reach,
            cover=candidate.cover,
            stance=candidate.stance,
            danger=candidate.danger,
            claim_source=displaced_by or "uncontested",
        )
    return None


def _direction_delta(a: int, b: int) -> int:
    delta = abs((a - b) % SIGHTLINE_DIRECTIONS)
    return min(delta, SIGHTLINE_DIRECTIONS - delta)


def _current_post_invalid(belief: Belief) -> bool:
    if belief.post_cell is None:
        return True
    if belief.nav_stuck_ticks >= STUCK_TICKS:
        return True
    gx = belief.post_cell[0] // NAV_CELL
    gy = belief.post_cell[1] // NAV_CELL
    if not mapdata.walkable_grid()[gy, gx]:
        return True
    for seat, claim in belief.post_claims.items():
        if (
            seat < belief.seat
            and belief.tick - claim.tick <= POST_CLAIM_TTL_TICKS
            and _near(belief.post_cell, claim.cell, POST_MIN_SEPARATION_PX)
        ):
            return True
    if any(
        _near(belief.post_cell, teammate.pos, POST_MIN_SEPARATION_PX)
        for teammate in belief.teammates
    ):
        return True
    return any(
        _near(belief.post_cell, enemy.pos, POST_ENEMY_OCCUPIED_PX)
        for enemy in belief.enemies
    )


def _set_post(
    belief: Belief,
    post: Post,
    axis: ThreatAxis,
    center: tuple[int, int],
    mode: PostMode,
    context: str,
) -> None:
    changed = belief.post_cell != post.cell or belief.post_direction != post.direction
    belief.post_cell = post.cell
    belief.post_direction = post.direction
    belief.post_center = center
    belief.post_mode = mode
    belief.post_context = context
    belief.post_score = post.score
    belief.post_reach = post.reach
    belief.post_cover = post.cover
    belief.post_stance = post.stance
    belief.post_danger = post.danger
    belief.post_threat_source = axis.source
    belief.post_claim_source = post.claim_source
    belief.post_selected_tick = belief.tick
    belief.post_last_evaluated_tick = belief.tick
    belief.post_settled_ticks = 0
    if changed:
        belief.sweep_offset = 0


def _clear_post(belief: Belief, claim_source: str | None = None) -> None:
    belief.post_active = False
    belief.post_cell = None
    belief.post_direction = None
    belief.post_center = None
    belief.post_mode = None
    belief.post_context = None
    belief.post_score = None
    belief.post_reach = None
    belief.post_cover = None
    belief.post_stance = None
    belief.post_danger = None
    belief.post_threat_source = None
    belief.post_claim_source = claim_source
    belief.post_selected_tick = -1
    belief.post_last_evaluated_tick = belief.tick
    belief.post_settled_ticks = 0


def _activate_post(belief: Belief) -> None:
    belief.post_active = True
    assert belief.self_xy is not None and belief.post_cell is not None
    if _within(belief.self_xy, belief.post_cell, POST_SETTLE_PX):
        belief.post_settled_ticks += 1
        belief.post_ticks_total += 1
    else:
        belief.post_settled_ticks = 0


def resolve_post_target(
    belief: Belief,
    center: tuple[int, int],
    *,
    mode: PostMode,
    context: str,
    facing: tuple[int, int] | None = None,
) -> Post | None:
    """Maintain one latched post; dwell and hysteresis affect re-selection only."""
    if belief.self_xy is None:
        _clear_post(belief)
        return None

    axis = threat_axis(belief, center, facing=facing)
    same_objective = (
        belief.post_center == center
        and belief.post_mode == mode
        and belief.post_context == context
    )
    invalid = _current_post_invalid(belief) if same_objective else True

    if not same_objective or invalid:
        selected = choose_post(belief, center, axis.direction, mode=mode)
        if selected is None:
            _clear_post(belief, "spread_fallback")
            return None
        _set_post(belief, selected, axis, center, mode, context)
        _activate_post(belief)
        return selected

    assert belief.post_cell is not None and belief.post_direction is not None
    _activate_post(belief)
    can_reconsider = (
        belief.post_settled_ticks >= POST_MIN_DWELL_TICKS
        and belief.tick - belief.post_last_evaluated_tick >= POST_REEVALUATE_TICKS
        and _direction_delta(axis.direction, belief.post_direction)
        >= POST_THREAT_HYSTERESIS_DIRECTIONS
    )
    if can_reconsider:
        belief.post_last_evaluated_tick = belief.tick
        selected = choose_post(belief, center, axis.direction, mode=mode)
        if selected is not None:
            current = next(
                (
                    candidate
                    for candidate in _ranked_candidates(
                        belief,
                        center,
                        axis.direction,
                        mode,
                    )
                    if candidate.cell == belief.post_cell
                ),
                None,
            )
            current_score = current.score if current is not None else -math.inf
            if (
                selected.cell == belief.post_cell
                or selected.score >= current_score + POST_SWITCH_MARGIN
            ):
                _set_post(belief, selected, axis, center, mode, context)

    return Post(
        cell=belief.post_cell,
        direction=belief.post_direction,
        score=float(belief.post_score or 0.0),
        reach=float(belief.post_reach or 0.0),
        cover=float(belief.post_cover or 0.0),
        stance=float(belief.post_stance or 0.0),
        danger=float(belief.post_danger or 0.0),
        claim_source=belief.post_claim_source or "uncontested",
    )


__all__ = [
    "Post",
    "PostMode",
    "ThreatAxis",
    "choose_post",
    "cover_toward",
    "direction_to_brads",
    "resolve_post_target",
    "sightline",
    "threat_axis",
]
