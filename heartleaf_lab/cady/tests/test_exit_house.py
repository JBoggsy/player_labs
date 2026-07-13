"""Tests for Cady's home-interior exit mode."""

from __future__ import annotations

from cady.frame import to_world
from cady.mapdata import HOME_EXIT, HOME_WALK_GRID
from cady.modes.exit_house import ExitHouseMode
from cady.types import ActionState, Belief
from pytest import MonkeyPatch


def test_exit_house_navigates_to_home_exit_when_far(monkeypatch: MonkeyPatch) -> None:
    exit_world = to_world(HOME_EXIT)
    waypoint = (exit_world[0] - 5, exit_world[1] - 5)

    def _next_waypoint(
        belief: Belief,
        self_xy: tuple[int, int],
        goal: tuple[int, int],
        *,
        grid: object,
    ) -> tuple[int, int]:
        del belief, self_xy
        assert goal == exit_world
        assert grid is HOME_WALK_GRID
        return waypoint

    monkeypatch.setattr("cady.modes.exit_house.navigator.next_waypoint", _next_waypoint)

    intent = ExitHouseMode().decide(Belief(self_xy=(0, 0), map_context="home"), ActionState())

    assert intent.kind == "navigate_to"
    assert intent.point == waypoint


def test_exit_house_presses_at_home_exit_when_in_range() -> None:
    exit_world = to_world(HOME_EXIT)

    intent = ExitHouseMode().decide(Belief(self_xy=exit_world, map_context="home"), ActionState())

    assert intent.kind == "gather_at"
    assert intent.point == exit_world
