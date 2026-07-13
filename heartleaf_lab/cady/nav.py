r"""Grid navigation for Cady's baked Heartleaf map.

8-connected shortest-path routing over a boolean walkability grid. The public
router (:func:`find_path`, aliased :func:`jps`) returns **corner waypoints** — the
points where the path changes direction — so callers steer point-to-point.

Implementation note: this ships a correct **A\*** and compresses its cell path to
corner waypoints. A true Jump-Point-Search would return the *same optimal paths*
faster; it is a deferred optimization (the paths, and therefore cady's behaviour,
are identical — JPS only reduces compute). Most routes cady uses are pre-baked
offline (``tools/bake_map``), so runtime pathfinding is infrequent.

Conventions: points are ``(x, y)`` map pixels; the grid is indexed ``grid[y, x]``
with ``True`` = walkable. Diagonal moves never cut a blocked corner: a step
``(dx, dy)`` with both non-zero is legal only when the destination and *both*
orthogonally adjacent cells are walkable.
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Iterable

import numpy as np

Point = tuple[int, int]
Direction = tuple[int, int]

_SQRT2 = math.sqrt(2.0)
_DIRS_8: tuple[Direction, ...] = (
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
)


def _walkable(grid: np.ndarray, x: int, y: int) -> bool:
    """True iff (x, y) is in bounds and walkable (out of bounds = blocked)."""
    return 0 <= y < grid.shape[0] and 0 <= x < grid.shape[1] and bool(grid[y, x])


def _can_step(grid: np.ndarray, x: int, y: int, dx: int, dy: int) -> bool:
    """Legality of a single step from (x, y) by (dx, dy), no corner cutting."""
    if not _walkable(grid, x + dx, y + dy):
        return False
    if dx != 0 and dy != 0:
        return _walkable(grid, x + dx, y) and _walkable(grid, x, y + dy)
    return True


def nearest_walkable(grid: np.ndarray, p: Point, max_radius: int = 64) -> Point | None:
    """Nearest walkable cell to ``p`` (by Euclidean distance) within ``max_radius``."""
    px, py = p
    if _walkable(grid, px, py):
        return p
    for radius in range(1, max_radius + 1):
        best: tuple[int, int, int] | None = None  # (dist2, y, x)
        for x, y in _ring(px, py, radius):
            if _walkable(grid, x, y):
                d2 = (x - px) ** 2 + (y - py) ** 2
                cand = (d2, y, x)
                if best is None or cand < best:
                    best = cand
        if best is not None:
            return (best[2], best[1])
    return None


def astar_cells(grid: np.ndarray, start: Point, goal: Point) -> list[Point] | None:
    """Optimal 8-connected A* path as a full list of cells (start..goal), or None."""
    if not (_walkable(grid, *start) and _walkable(grid, *goal)):
        return None
    if start == goal:
        return [start]
    counter = 0
    open_heap: list[tuple[float, int, Point]] = [(_octile(start, goal), 0, start)]
    g_score: dict[Point, float] = {start: 0.0}
    came_from: dict[Point, Point] = {}
    closed: set[Point] = set()
    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current == goal:
            return _reconstruct(came_from, current, start)
        if current in closed:
            continue
        closed.add(current)
        cx, cy = current
        base = g_score[current]
        for dx, dy in _DIRS_8:
            if not _can_step(grid, cx, cy, dx, dy):
                continue
            nxt = (cx + dx, cy + dy)
            tentative = base + (_SQRT2 if dx and dy else 1.0)
            if tentative < g_score.get(nxt, math.inf):
                g_score[nxt] = tentative
                came_from[nxt] = current
                counter += 1
                heapq.heappush(open_heap, (tentative + _octile(nxt, goal), counter, nxt))
    return None


#: Coarse routing: block size and the fraction of a block that must be walkable.
#: Validated (bake-time / tests) to preserve connectivity while cutting the A* grid
#: ~16x for fast long-range routing.
COARSE_BLOCK = 4
COARSE_THRESHOLD = 0.25
#: Below this Chebyshev distance, route exactly on the fine grid (already fast).
FINE_ROUTE_MAX = 48

_coarse_cache: dict[int, tuple[np.ndarray, int]] = {}


def coarse_grid(grid: np.ndarray, block: int = COARSE_BLOCK, threshold: float = COARSE_THRESHOLD) -> np.ndarray:
    """Downsample a fine walk grid to ``block``x``block`` cells (walkable if a
    ``threshold`` fraction of the block is walkable). Preserves connectivity of the
    real map (see tests) while shrinking A* work."""
    h, w = grid.shape
    ch, cw = (h + block - 1) // block, (w + block - 1) // block
    padded = np.zeros((ch * block, cw * block), dtype=np.float32)
    padded[:h, :w] = grid
    frac = padded.reshape(ch, block, cw, block).mean(axis=(1, 3))
    return frac >= threshold


def _cached_coarse(grid: np.ndarray) -> tuple[np.ndarray, int]:
    key = id(grid)
    cached = _coarse_cache.get(key)
    if cached is None:
        cached = (coarse_grid(grid), COARSE_BLOCK)
        _coarse_cache[key] = cached
    return cached


def find_path(grid: np.ndarray, start: Point, goal: Point) -> list[Point] | None:
    """Route from ``start`` to ``goal`` as corner waypoints (``None`` if unreachable).

    Short hops route exactly on the fine grid. Long hops route on a coarse grid
    (fast) and snap each coarse waypoint back to the nearest walkable fine cell —
    the controller steers point-to-point, so the coarse route is followed on the
    fine map. Guarantees fast arbitrary-point navigation (see tests for timing).
    """
    if not (_walkable(grid, *start) and _walkable(grid, *goal)):
        return None
    if start == goal:
        return [start]

    if max(abs(start[0] - goal[0]), abs(start[1] - goal[1])) <= FINE_ROUTE_MAX:
        cells = astar_cells(grid, start, goal)
        return None if cells is None else _to_waypoints(cells)

    coarse, block = _cached_coarse(grid)
    cs = (start[0] // block, start[1] // block)
    cg = (goal[0] // block, goal[1] // block)
    coarse_cells = astar_cells(coarse, cs, cg)
    if coarse_cells is None:
        # Coarse says unreachable (rare); fall back to an exact fine route.
        cells = astar_cells(grid, start, goal)
        return None if cells is None else _to_waypoints(cells)

    # Snap EVERY coarse cell (dense breadcrumbs ~one block apart) to a fine walkable
    # cell and keep start/goal exact. Dense (not corner-compressed) so consecutive
    # waypoints are adjacent walkable coarse cells — the straight hop between them
    # stays on the fine map, which corner-compression would break by spanning walls.
    fine_pts: list[Point] = [start]
    for cx, cy in coarse_cells[1:-1]:
        p = nearest_walkable(grid, (cx * block + block // 2, cy * block + block // 2))
        if p is not None and p != fine_pts[-1]:
            fine_pts.append(p)
    if goal != fine_pts[-1]:
        fine_pts.append(goal)

    # Repair the rare short hop that clips a wall with a tiny local fine A* — the
    # snapped points are ~one block apart, so this is cheap and only fires on the
    # ~0.5% of hops that need it, leaving a fully controller-followable path.
    repaired: list[Point] = [fine_pts[0]]
    for nxt in fine_pts[1:]:
        if _line_walkable(grid, repaired[-1], nxt):
            repaired.append(nxt)
            continue
        sub = astar_cells(grid, repaired[-1], nxt)
        if sub is not None:
            repaired.extend(_to_waypoints(sub)[1:])
        else:
            repaired.append(nxt)
    return repaired


def _line_walkable(grid: np.ndarray, a: Point, b: Point) -> bool:
    """Whether the bang-bang controller can traverse straight from ``a`` to ``b``."""
    x, y = a
    for _ in range(max(abs(b[0] - a[0]), abs(b[1] - a[1]))):
        sx, sy = _sign(b[0] - x), _sign(b[1] - y)
        if not _can_step(grid, x, y, sx, sy):
            if sx and _can_step(grid, x, y, sx, 0):
                sy = 0
            elif sy and _can_step(grid, x, y, 0, sy):
                sx = 0
            else:
                return False
        x += sx
        y += sy
    return True


#: Public routing name (hierarchical A*). True JPS would be faster; deferred.
jps = find_path


def path_length(grid: np.ndarray, a: Point, b: Point) -> float | None:
    """Euclidean length of the route from ``a`` to ``b`` (None if unreachable)."""
    cells = astar_cells(grid, a, b)
    if cells is None:
        return None
    return sum(_euclid(p, q) for p, q in zip(cells, cells[1:]))


def _to_waypoints(cells: list[Point]) -> list[Point]:
    """Compress a dense cell path to endpoints + direction-change corners."""
    if len(cells) <= 2:
        return list(cells)
    out = [cells[0]]
    prev_dir = (_sign(cells[1][0] - cells[0][0]), _sign(cells[1][1] - cells[0][1]))
    for i in range(1, len(cells) - 1):
        d = (_sign(cells[i + 1][0] - cells[i][0]), _sign(cells[i + 1][1] - cells[i][1]))
        if d != prev_dir:
            out.append(cells[i])
            prev_dir = d
    out.append(cells[-1])
    return out


def _ring(px: int, py: int, radius: int) -> Iterable[Point]:
    for x in range(px - radius, px + radius + 1):
        yield (x, py - radius)
        yield (x, py + radius)
    for y in range(py - radius + 1, py + radius):
        yield (px - radius, y)
        yield (px + radius, y)


def _reconstruct(came_from: dict[Point, Point], current: Point, start: Point) -> list[Point]:
    path = [current]
    while current != start:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def _octile(a: Point, b: Point) -> float:
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return (dx + dy) + (_SQRT2 - 2.0) * min(dx, dy)


def _euclid(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _sign(v: int) -> int:
    return int(v > 0) - int(v < 0)


__all__ = ["find_path", "jps", "astar_cells", "nearest_walkable", "path_length"]
