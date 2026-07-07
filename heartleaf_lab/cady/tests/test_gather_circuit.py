"""Tests for Cady's baked garden circuit gather mode."""

from __future__ import annotations

from cady.config import MAX_GATHER_TICKS
from cady.frame import to_world
from cady.mapdata import GARDEN_APPROACHES, GARDEN_CIRCUIT, WALK_GRID
from cady.modes import GatherMode
from cady.types import ActionState, Belief, Garden
from pytest import MonkeyPatch


def _food_marker_at(pos: tuple[int, int]) -> tuple[Garden, ...]:
    """A visible in-range garden marker (harvesting only fires when food is seen)."""
    return (Garden(object_id=4000, pos=pos, has_food=True),)


def test_gather_mode_navigates_to_first_circuit_garden(monkeypatch: MonkeyPatch) -> None:
    target_index = GARDEN_CIRCUIT[0]
    target_world = to_world(GARDEN_APPROACHES[target_index])
    waypoint = (target_world[0] - 1, target_world[1] - 1)
    seen_goals: list[tuple[int, int]] = []

    def _next_waypoint(
        belief: Belief,
        self_xy: tuple[int, int],
        goal: tuple[int, int],
        *,
        grid: object,
    ) -> tuple[int, int]:
        del belief, self_xy
        assert grid is WALK_GRID
        seen_goals.append(goal)
        return waypoint

    monkeypatch.setattr("cady.modes.gather.navigator.next_waypoint", _next_waypoint)
    belief = Belief(self_xy=(0, 0))

    intent = GatherMode().decide(belief, ActionState())

    assert intent.kind == "navigate_to"
    assert intent.point == waypoint
    assert seen_goals == [target_world]
    assert belief.circuit_index == 0


def test_gather_mode_presses_a_and_stays_until_harvest_confirmed() -> None:
    target_index = GARDEN_CIRCUIT[0]
    target_world = to_world(GARDEN_APPROACHES[target_index])
    belief = Belief(
        self_xy=target_world,
        nav_goal=target_world,
        nav_path=[target_world],
        nav_cursor=0,
        inventory_count=0,
        food_gardens=_food_marker_at(target_world),
    )

    # In range but nothing collected yet: press A and stay on this garden.
    intent = GatherMode().decide(belief, ActionState())
    assert intent.kind == "gather_at"
    assert intent.point == target_world
    assert belief.circuit_index == 0
    assert belief.gather_active_index == target_index
    assert belief.gather_ticks == 1

    # Still nothing: keep pressing A on the same garden.
    intent = GatherMode().decide(belief, ActionState())
    assert intent.kind == "gather_at"
    assert belief.circuit_index == 0
    assert belief.gather_ticks == 2

    # Inventory rises -> pickup confirmed -> advance to the next garden.
    belief.inventory_count = 3
    GatherMode().decide(belief, ActionState())
    assert belief.circuit_index == 1
    assert belief.gather_active_index is None
    assert belief.nav_goal is None
    assert belief.nav_path is None


def test_gather_mode_times_out_and_advances_on_an_empty_garden() -> None:
    target_index = GARDEN_CIRCUIT[0]
    target_world = to_world(GARDEN_APPROACHES[target_index])
    # A marker is visible (food is there) but the pickup never registers, e.g.
    # a rival keeps taking it: give up after the timeout and move on.
    belief = Belief(
        self_xy=target_world,
        inventory_count=0,
        food_gardens=_food_marker_at(target_world),
    )

    for _ in range(MAX_GATHER_TICKS):
        GatherMode().decide(belief, ActionState())

    assert belief.circuit_index == 1
    assert belief.gather_active_index is None


def test_gather_mode_skips_a_garden_with_no_visible_food_without_pressing_a() -> None:
    # In range of the baked garden rect, but NO food marker is visible (garden
    # empty, or its radius overlaps a house). Don't press A (A on a house rect
    # would enter it) — advance to the next garden immediately.
    target_index = GARDEN_CIRCUIT[0]
    target_world = to_world(GARDEN_APPROACHES[target_index])
    belief = Belief(self_xy=target_world, inventory_count=0, food_gardens=())

    intent = GatherMode().decide(belief, ActionState())

    assert intent.kind != "gather_at"
    assert belief.circuit_index == 1
    assert belief.gather_active_index is None
