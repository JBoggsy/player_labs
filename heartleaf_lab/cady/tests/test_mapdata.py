"""Tests for Cady's baked Heartleaf map data."""

from __future__ import annotations

import math

from cady import mapdata


def test_walk_grid_shape() -> None:
    assert mapdata.WALK_GRID.shape == (941, 748)
    assert mapdata.GRID_W == 748
    assert mapdata.GRID_H == 941
    assert mapdata.HOME_WALK_GRID.shape == (247, 251)
    assert mapdata.HOME_GRID_W == 251
    assert mapdata.HOME_GRID_H == 247


def test_gardens_and_houses_have_expected_counts() -> None:
    assert len(mapdata.GARDEN_RECTS) == 39
    assert len(mapdata.GARDEN_APPROACHES) == 39
    assert len(mapdata.HOUSE_RECTS) == 9
    assert len(mapdata.HOUSE_TARGETS) == 9


def test_garden_approaches_are_walkable_and_in_harvest_range() -> None:
    for rect, approach in zip(mapdata.GARDEN_RECTS, mapdata.GARDEN_APPROACHES):
        x, y = approach
        assert mapdata.WALK_GRID[y, x]
        center = _rect_center(rect)
        assert math.hypot(x - center[0], y - center[1]) <= 40.0


def test_garden_circuit_is_a_permutation() -> None:
    assert sorted(mapdata.GARDEN_CIRCUIT) == list(range(39))


def test_house_targets_are_walkable() -> None:
    for x, y in mapdata.HOUSE_TARGETS:
        assert mapdata.WALK_GRID[y, x]


def test_home_targets_are_walkable_and_exit_is_in_range() -> None:
    exit_x, exit_y = mapdata.HOME_EXIT

    assert mapdata.HOME_WALK_GRID[exit_y, exit_x]
    assert _point_rect_distance(mapdata.HOME_EXIT, mapdata.HOME_EXIT_RECT) <= 40.0
    assert len(mapdata.HOME_DINERS) == 6
    for x, y in mapdata.HOME_DINERS:
        assert mapdata.HOME_WALK_GRID[y, x]


def _rect_center(rect: tuple[int, int, int, int]) -> tuple[int, int]:
    left, top, width, height = rect
    return (left + width // 2, top + height // 2)


def _point_rect_distance(point: tuple[int, int], rect: tuple[int, int, int, int]) -> float:
    x, y = point
    left, top, width, height = rect
    right = left + width
    bottom = top + height
    dx = max(left - x, 0, x - right)
    dy = max(top - y, 0, y - bottom)
    return math.hypot(dx, dy)
