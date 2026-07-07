"""Cached waypoint follower for Cady's baked-map navigation."""

from __future__ import annotations

import math

import numpy as np

from cady import nav
from cady.config import NAV_STUCK_TICKS, NAV_PROGRESS_EPS, WAYPOINT_RADIUS
from cady.frame import to_map, to_world
from cady.types import Belief

Point = tuple[int, int]


def next_waypoint(
    belief: Belief,
    self_world: Point,
    goal_world: Point,
    *,
    grid: np.ndarray,
) -> Point | None:
    """Return the current cached waypoint toward ``goal_world``.

    Routes are computed in baked map coordinates and cached on ``belief`` as
    world-frame waypoints. The route is recomputed when the goal changes, no
    cached path exists, or we've made no progress for a while (a stale waypoint
    that's walled off from our current position — otherwise we'd push into the
    wall forever).
    """

    _update_stuck(belief, self_world)
    if belief.nav_stuck_ticks >= NAV_STUCK_TICKS:
        # Stalled: drop the cached path so it re-plans from where we ARE now.
        belief.nav_path = None
        belief.nav_goal = None
        belief.nav_stuck_ticks = 0

    if belief.nav_goal != goal_world or belief.nav_path is None:
        points = nav.find_path(grid, to_map(self_world), to_map(goal_world))
        if points is None:
            belief.nav_goal = goal_world
            belief.nav_path = None
            belief.nav_cursor = 0
            return None
        belief.nav_goal = goal_world
        belief.nav_path = [to_world(point) for point in points]
        belief.nav_cursor = 0

    path = belief.nav_path
    if path is None:
        return None

    while belief.nav_cursor < len(path) and _distance(self_world, path[belief.nav_cursor]) <= WAYPOINT_RADIUS:
        belief.nav_cursor += 1

    if belief.nav_cursor >= len(path):
        return goal_world
    return path[belief.nav_cursor]


def clear_navigation(belief: Belief) -> None:
    """Clear cached route state after a target is completed or abandoned."""

    belief.nav_goal = None
    belief.nav_path = None
    belief.nav_cursor = 0
    belief.nav_last_xy = None
    belief.nav_stuck_ticks = 0


def _update_stuck(belief: Belief, self_world: Point) -> None:
    """Count consecutive frames with negligible movement (stuck against a wall)."""
    last = belief.nav_last_xy
    if last is not None and _distance(last, self_world) < NAV_PROGRESS_EPS:
        belief.nav_stuck_ticks += 1
    else:
        belief.nav_stuck_ticks = 0
    belief.nav_last_xy = self_world


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


__all__ = ["Point", "clear_navigation", "next_waypoint"]
