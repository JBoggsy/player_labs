"""Navigation over the episode WorldMap: flow-field lookup + online A* fallback.

Two goal kinds:

  * **Stable strategic goals** (steal a heart / carry home / defend) — read the
    next hop from a per-goal flow field the WorldMap computes lazily (one
    Dijkstra per goal per episode).
  * **Arbitrary goals** (chase a carrier to a moving point) — A* on the same
    grid; cached and re-planned only on stuck / goal move.

Both return a *waypoint* (a map-space point a short way ahead); ``octant_toward``
turns a waypoint into a d-pad button mask. All map facts come from
``belief.worldmap`` — nothing here is module-cached.
"""

from __future__ import annotations

import heapq
import math

from paintbot.stencil.config import NAV_CELL, REPLAN_GOAL_CELLS, STUCK_TICKS
from paintbot.stencil.types import Belief
from paintbot.stencil.worldmap import NEIGHBORS, WorldMap
from players.player_sdk import Button

_SQRT2 = math.sqrt(2)


def flow_waypoint(wm: WorldMap, goal: tuple[int, int], self_xy: tuple[int, int]) -> tuple[int, int]:
    """Next-hop waypoint toward a stable goal, from the map's cached flow field."""
    return wm.flow_waypoint(goal, self_xy)


def route_distance(wm: WorldMap, start: tuple[int, int], goal: tuple[int, int]) -> float:
    """Shortest static-map walking distance in pixels between two map points."""
    return wm.route_distance(start, goal)


def walkable_segment(wm: WorldMap, start: tuple[int, int], end: tuple[int, int]) -> bool:
    return wm.walkable_segment(start, end)


def _astar(wm: WorldMap, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]] | None:
    """A* over grid cells; returns a list of cell centres (map coords) or None."""
    grid = wm.walkable
    sx, sy = wm.nearest_walkable(*wm.cell_of(*start))
    gx, gy = wm.nearest_walkable(*wm.cell_of(*goal))
    if (sx, sy) == (gx, gy):
        return [wm.cell_center(gx, gy)]

    def h(x, y):
        return math.hypot(x - gx, y - gy)

    open_pq = [(h(sx, sy), 0.0, sx, sy)]
    came: dict[tuple[int, int], tuple[int, int]] = {}
    best = {(sx, sy): 0.0}
    while open_pq:
        _, g, x, y = heapq.heappop(open_pq)
        if (x, y) == (gx, gy):
            path = [(x, y)]
            while (x, y) in came:
                x, y = came[(x, y)]
                path.append((x, y))
            path.reverse()
            return [wm.cell_center(cx, cy) for cx, cy in path]
        if g > best.get((x, y), float("inf")):
            continue
        for dx, dy in NEIGHBORS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < wm.grid_w and 0 <= ny < wm.grid_h) or not grid[ny, nx]:
                continue
            if dx != 0 and dy != 0 and not (grid[y, nx] and grid[ny, x]):
                continue  # no diagonal squeeze through a wall corner
            step = _SQRT2 if (dx and dy) else 1.0
            ng = g + step
            if ng < best.get((nx, ny), float("inf")):
                best[(nx, ny)] = ng
                came[(nx, ny)] = (x, y)
                heapq.heappush(open_pq, (ng + h(nx, ny), ng, nx, ny))
    return None


def astar_waypoint(belief: Belief, self_xy: tuple[int, int], goal: tuple[int, int]) -> tuple[int, int]:
    """Next waypoint toward an arbitrary goal, with a cached, stuck-aware path."""
    wm = belief.worldmap
    assert wm is not None
    goal_cell = wm.cell_of(*goal)
    prev_goal_cell = wm.cell_of(*belief.nav_goal) if belief.nav_goal is not None else None
    goal_moved = (
        prev_goal_cell is None
        or abs(goal_cell[0] - prev_goal_cell[0]) > REPLAN_GOAL_CELLS
        or abs(goal_cell[1] - prev_goal_cell[1]) > REPLAN_GOAL_CELLS
    )

    if goal_moved or belief.nav_path is None or belief.nav_stuck_ticks >= STUCK_TICKS:
        path = _astar(wm, self_xy, goal)
        belief.nav_goal = goal
        belief.nav_path = path
        belief.nav_cursor = 0
        belief.nav_stuck_ticks = 0

    path = belief.nav_path
    if not path:
        return goal  # unroutable — steer straight and let stuck-jitter handle it

    while belief.nav_cursor < len(path) - 1 and _dist(self_xy, path[belief.nav_cursor]) < NAV_CELL:
        belief.nav_cursor += 1
    return path[belief.nav_cursor]


def note_progress(belief: Belief, self_xy: tuple[int, int]) -> None:
    """Update the stuck counter from real movement since last frame."""
    if belief.nav_last_xy is not None and _dist(self_xy, belief.nav_last_xy) < 1.0:
        belief.nav_stuck_ticks += 1
    else:
        belief.nav_stuck_ticks = 0
    belief.nav_last_xy = self_xy


def octant_toward(self_xy: tuple[int, int], waypoint: tuple[int, int], jitter: bool) -> int:
    """A d-pad button mask stepping from ``self_xy`` toward ``waypoint``."""
    dx = waypoint[0] - self_xy[0]
    dy = waypoint[1] - self_xy[1]
    if abs(dx) < 1 and abs(dy) < 1:
        return 0
    ang = math.atan2(dy, dx)  # screen space: +y is down
    if jitter:
        ang += math.pi / 2
    mask = 0
    if math.cos(ang) > 0.383:
        mask |= Button.RIGHT
    elif math.cos(ang) < -0.383:
        mask |= Button.LEFT
    if math.sin(ang) > 0.383:
        mask |= Button.DOWN
    elif math.sin(ang) < -0.383:
        mask |= Button.UP
    return int(mask)


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


__all__ = [
    "astar_waypoint",
    "flow_waypoint",
    "note_progress",
    "octant_toward",
    "route_distance",
    "walkable_segment",
]
