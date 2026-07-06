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
