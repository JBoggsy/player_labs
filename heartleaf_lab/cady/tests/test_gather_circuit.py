"""Tests for Cady's baked garden circuit gather mode."""

from __future__ import annotations

from cady.frame import to_world
from cady.mapdata import GARDEN_APPROACHES, GARDEN_CIRCUIT
from cady.modes import GatherMode
from cady.types import ActionState, Belief
from pytest import MonkeyPatch


def test_gather_mode_navigates_to_first_circuit_garden(monkeypatch: MonkeyPatch) -> None:
    target_index = GARDEN_CIRCUIT[0]
    target_world = to_world(GARDEN_APPROACHES[target_index])
    waypoint = (target_world[0] - 1, target_world[1] - 1)
    seen_goals: list[tuple[int, int]] = []

    def _next_waypoint(belief: Belief, self_xy: tuple[int, int], goal: tuple[int, int]) -> tuple[int, int]:
        del belief, self_xy
        seen_goals.append(goal)
        return waypoint

    monkeypatch.setattr("cady.modes.gather.navigator.next_waypoint", _next_waypoint)
    belief = Belief(self_xy=(0, 0))

    intent = GatherMode().decide(belief, ActionState())

    assert intent.kind == "navigate_to"
    assert intent.point == waypoint
    assert seen_goals == [target_world]
    assert belief.circuit_index == 0


def test_gather_mode_harvests_and_advances_when_inside_radius() -> None:
    target_index = GARDEN_CIRCUIT[0]
    target_world = to_world(GARDEN_APPROACHES[target_index])
    belief = Belief(
        self_xy=target_world,
        nav_goal=target_world,
        nav_path=[target_world],
        nav_cursor=0,
    )

    intent = GatherMode().decide(belief, ActionState())

    assert intent.kind == "gather_at"
    assert intent.point == target_world
    assert belief.circuit_index == 1
    assert belief.nav_goal is None
    assert belief.nav_path is None
    assert belief.nav_cursor == 0
