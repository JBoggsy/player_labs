"""Navigation over the baked grid: flow-field lookup + online A* fallback.

Two goal kinds (design §4):

  * **Fixed strategic goals** (steal the enemy flag / carry home) — read the next hop
    from the precomputed flow field. O(1), no search.
  * **Arbitrary goals** (chase a flag-carrier to a moving point) — A* on the same
    baked grid. Sub-ms on ~9k cells; cached and re-planned only on stuck / goal move.

Both return a *waypoint* (a map-space point a short way ahead); ``octant_toward``
turns a waypoint into a d-pad button mask.
"""

from __future__ import annotations

import heapq
import math

from ctf.beacon import mapdata
from ctf.beacon.config import GRID_H, GRID_W, NAV_CELL, REPLAN_GOAL_CELLS, STUCK_TICKS
from ctf.beacon.types import Belief
from players.player_sdk import Button

_SQRT2 = math.sqrt(2)


def _cell_of(x: int, y: int) -> tuple[int, int]:
    return (min(max(x // NAV_CELL, 0), GRID_W - 1), min(max(y // NAV_CELL, 0), GRID_H - 1))


def _cell_center(gx: int, gy: int) -> tuple[int, int]:
    return (gx * NAV_CELL + NAV_CELL // 2, gy * NAV_CELL + NAV_CELL // 2)


def _nearest_walkable(grid, gx: int, gy: int) -> tuple[int, int]:
    if grid[gy, gx]:
        return gx, gy
    for ring in range(1, max(GRID_W, GRID_H)):
        for dy in range(-ring, ring + 1):
            for dx in range(-ring, ring + 1):
                nx, ny = gx + dx, gy + dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H and grid[ny, nx]:
                    return nx, ny
    return gx, gy


def flow_waypoint(team: str, kind: str, self_xy: tuple[int, int]) -> tuple[int, int]:
    """Next-hop waypoint toward a fixed goal, from the baked flow field."""
    field = mapdata.flow_field(team, kind)
    grid = mapdata.walkable_grid()
    gx, gy = _nearest_walkable(grid, *_cell_of(*self_xy))
    code = int(field[gy, gx])
    if code == 0:  # at goal (or unreachable) — steer straight at the exact target
        return self_xy
    dx, dy = mapdata.NEIGHBORS[code - 1]
    return _cell_center(gx + dx, gy + dy)


def _astar(grid, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]] | None:
    """A* over grid cells; returns a list of cell centres (map coords) or None."""
    sx, sy = _nearest_walkable(grid, *_cell_of(*start))
    gx, gy = _nearest_walkable(grid, *_cell_of(*goal))
    if (sx, sy) == (gx, gy):
        return [_cell_center(gx, gy)]

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
            return [_cell_center(cx, cy) for cx, cy in path]
        if g > best.get((x, y), float("inf")):
            continue
        for i, (dx, dy) in enumerate(mapdata.NEIGHBORS):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H) or not grid[ny, nx]:
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
    grid = mapdata.walkable_grid()
    goal_cell = _cell_of(*goal)
    prev_goal_cell = _cell_of(*belief.nav_goal) if belief.nav_goal is not None else None
    goal_moved = (
        prev_goal_cell is None
        or abs(goal_cell[0] - prev_goal_cell[0]) > REPLAN_GOAL_CELLS
        or abs(goal_cell[1] - prev_goal_cell[1]) > REPLAN_GOAL_CELLS
    )

    if goal_moved or belief.nav_path is None or belief.nav_stuck_ticks >= STUCK_TICKS:
        path = _astar(grid, self_xy, goal)
        belief.nav_goal = goal
        belief.nav_path = path
        belief.nav_cursor = 0
        belief.nav_stuck_ticks = 0

    path = belief.nav_path
    if not path:
        return goal  # unroutable — steer straight and let stuck-jitter handle it

    # Advance the cursor past waypoints we've effectively reached.
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
    """A d-pad button mask stepping from ``self_xy`` toward ``waypoint``.

    When ``jitter`` (stuck), rotate the chosen octant 90° to slip off a wall corner.
    """
    dx = waypoint[0] - self_xy[0]
    dy = waypoint[1] - self_xy[1]
    if abs(dx) < 1 and abs(dy) < 1:
        return 0
    ang = math.atan2(dy, dx)  # screen space: +y is down
    if jitter:
        ang += math.pi / 2
    mask = 0
    # East/west
    if math.cos(ang) > 0.383:
        mask |= Button.RIGHT
    elif math.cos(ang) < -0.383:
        mask |= Button.LEFT
    # North/south (screen down = +y = DOWN button)
    if math.sin(ang) > 0.383:
        mask |= Button.DOWN
    elif math.sin(ang) < -0.383:
        mask |= Button.UP
    return int(mask)


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


__all__ = ["astar_waypoint", "flow_waypoint", "note_progress", "octant_toward"]
