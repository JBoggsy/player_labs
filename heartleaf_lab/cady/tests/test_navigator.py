"""Tests for cached waypoint navigation."""

from __future__ import annotations

import numpy as np
from pytest import MonkeyPatch

from cady import navigator
from cady.types import Belief


def test_next_waypoint_routes_and_advances_cursor(monkeypatch: MonkeyPatch) -> None:
    grid = np.ones((30, 30), dtype=bool)
    calls: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def _path(_grid: np.ndarray, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
        calls.append((start, goal))
        return [start, (10, 0), goal]

    monkeypatch.setattr("cady.navigator.nav.find_path", _path)
    belief = Belief()

    assert navigator.next_waypoint(belief, (0, 0), (20, 0), grid=grid) == (10, 0)
    assert belief.nav_goal == (20, 0)
    assert belief.nav_cursor == 1
    assert calls == [((0, 0), (20, 0))]

    assert navigator.next_waypoint(belief, (10, 0), (20, 0), grid=grid) == (20, 0)
    assert belief.nav_cursor == 2
    assert calls == [((0, 0), (20, 0))]

    assert navigator.next_waypoint(belief, (20, 0), (20, 0), grid=grid) == (20, 0)
    assert belief.nav_cursor == 3


def test_next_waypoint_reroutes_when_goal_changes(monkeypatch: MonkeyPatch) -> None:
    grid = np.ones((30, 30), dtype=bool)
    calls: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def _path(_grid: np.ndarray, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
        calls.append((start, goal))
        return [start, goal]

    monkeypatch.setattr("cady.navigator.nav.find_path", _path)
    belief = Belief()

    assert navigator.next_waypoint(belief, (0, 0), (20, 0), grid=grid) == (20, 0)
    assert navigator.next_waypoint(belief, (0, 0), (0, 20), grid=grid) == (0, 20)

    assert calls == [((0, 0), (20, 0)), ((0, 0), (0, 20))]
    assert belief.nav_goal == (0, 20)


def test_next_waypoint_returns_none_when_unreachable(monkeypatch: MonkeyPatch) -> None:
    grid = np.ones((30, 30), dtype=bool)
    monkeypatch.setattr("cady.navigator.nav.find_path", lambda _grid, _start, _goal: None)
    belief = Belief()

    assert navigator.next_waypoint(belief, (0, 0), (20, 0), grid=grid) is None
    assert belief.nav_goal == (20, 0)
    assert belief.nav_path is None
    assert belief.nav_cursor == 0


def test_next_waypoint_replans_when_stuck(monkeypatch: MonkeyPatch) -> None:
    # A stale cached path aims at a waypoint we can't reach; standing still for
    # NAV_STUCK_TICKS forces a fresh find_path from our current position.
    from cady.config import NAV_STUCK_TICKS

    grid = np.ones((30, 30), dtype=bool)
    calls: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def _path(_grid, start, goal):
        calls.append((start, goal))
        return [start, (5, 5), goal]

    monkeypatch.setattr("cady.navigator.nav.find_path", _path)
    belief = Belief()

    # First call plans once.
    navigator.next_waypoint(belief, (0, 0), (20, 0), grid=grid)
    assert len(calls) == 1

    # Now stall at the SAME spot: no progress accrues, and at the threshold it
    # re-plans (a second find_path call) instead of returning the stale waypoint.
    for _ in range(NAV_STUCK_TICKS + 1):
        navigator.next_waypoint(belief, (2, 0), (20, 0), grid=grid)
    assert len(calls) >= 2  # re-planned from the stuck position
    assert calls[-1][0] == (2, 0)  # replanned from where we actually are


def test_stuck_counter_resets_on_movement(monkeypatch: MonkeyPatch) -> None:
    grid = np.ones((30, 30), dtype=bool)
    monkeypatch.setattr("cady.navigator.nav.find_path", lambda _g, s, g: [s, g])
    belief = Belief()
    navigator.next_waypoint(belief, (0, 0), (20, 0), grid=grid)
    # Moving a real distance each frame keeps stuck_ticks at 0.
    for i in range(1, 30):
        navigator.next_waypoint(belief, (i * 3, 0), (20, 0), grid=grid)
        assert belief.nav_stuck_ticks == 0
