"""Tests for Cady grid navigation."""

from __future__ import annotations

import numpy as np

from cady.nav import jps, nearest_walkable

Point = tuple[int, int]


def test_jps_finds_path_around_wall() -> None:
    grid = np.ones((8, 8), dtype=bool)
    grid[:, 3] = False
    grid[4, 3] = True

    path = jps(grid, (1, 1), (6, 1))

    assert path is not None
    assert path[0] == (1, 1)
    assert path[-1] == (6, 1)
    assert _path_is_legal(grid, path)


def test_jps_returns_none_when_goal_is_walled_off() -> None:
    grid = np.ones((5, 5), dtype=bool)
    goal = (2, 2)
    for x in range(1, 4):
        for y in range(1, 4):
            if (x, y) != goal:
                grid[y, x] = False

    assert jps(grid, (0, 0), goal) is None


def test_jps_does_not_cut_blocked_diagonal_corner() -> None:
    grid = np.ones((4, 4), dtype=bool)
    grid[1, 0] = False

    path = jps(grid, (0, 0), (3, 3))

    assert path is not None
    assert _path_is_legal(grid, path)
    assert path[:2] != [(0, 0), (3, 3)]


def test_nearest_walkable_returns_self_when_walkable() -> None:
    grid = np.ones((3, 3), dtype=bool)

    assert nearest_walkable(grid, (1, 1)) == (1, 1)


def test_nearest_walkable_returns_a_walkable_cell() -> None:
    grid = np.zeros((5, 5), dtype=bool)
    grid[1, 3] = True
    grid[4, 4] = True

    point = nearest_walkable(grid, (2, 2))

    assert point == (3, 1)
    assert point is not None
    assert grid[point[1], point[0]]


def _path_is_legal(grid: np.ndarray, path: list[Point]) -> bool:
    for start, end in zip(path, path[1:]):
        x, y = start
        dx = _sign(end[0] - start[0])
        dy = _sign(end[1] - start[1])
        while (x, y) != end:
            if not _can_step(grid, (x, y), dx, dy):
                return False
            x += dx
            y += dy
    return True


def _can_step(grid: np.ndarray, point: Point, dx: int, dy: int) -> bool:
    x, y = point
    nx = x + dx
    ny = y + dy
    if not (0 <= ny < grid.shape[0] and 0 <= nx < grid.shape[1] and grid[ny, nx]):
        return False
    if dx != 0 and dy != 0:
        return bool(grid[y, nx] and grid[ny, x])
    return True


def _sign(value: int) -> int:
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0
