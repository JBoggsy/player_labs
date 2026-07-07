"""Cached waypoint follower for Cady's baked-map navigation."""

from __future__ import annotations

import math

import numpy as np

from cady import nav
from cady.config import WAYPOINT_RADIUS
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
    world-frame waypoints. The route is recomputed only when the goal changes or
    no cached path exists.
    """

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


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


__all__ = ["Point", "clear_navigation", "next_waypoint"]
