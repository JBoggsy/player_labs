"""Tests for Cady mode selection and mode decisions."""

from __future__ import annotations

from cady.config import HOME_RADIUS
from cady.modes import GatherMode, HostMode, IdleMode
from cady.strategy import ClockStrategy
from cady.types import ActionState, Belief, Garden


def _garden(object_id: int, pos: tuple[int, int]) -> Garden:
    return Garden(object_id=object_id, pos=pos, has_food=True)


def test_strategy_selects_idle_when_self_unresolved() -> None:
    directive = ClockStrategy().select(Belief(self_xy=None))

    assert directive.mode == "idle"


def test_strategy_selects_gather_before_cutoff_with_food() -> None:
    directive = ClockStrategy().select(
        Belief(self_xy=(0, 0), last_time_minutes=300, food_gardens=(_garden(4000, (10, 0)),))
    )

    assert directive.mode == "gather"


def test_strategy_selects_host_after_cutoff() -> None:
    directive = ClockStrategy().select(
        Belief(self_xy=(0, 0), last_time_minutes=560, food_gardens=(_garden(4000, (10, 0)),))
    )

    assert directive.mode == "host"


def test_strategy_selects_host_before_cutoff_when_no_food_visible() -> None:
    directive = ClockStrategy().select(Belief(self_xy=(0, 0), last_time_minutes=300, food_gardens=()))

    assert directive.mode == "host"


def test_gather_mode_picks_nearest_food_garden() -> None:
    intent = GatherMode().decide(
        Belief(
            self_xy=(0, 0),
            food_gardens=(
                _garden(4000, (100, 0)),
                _garden(4001, (10, 0)),
            ),
        ),
        ActionState(),
    )

    assert intent.kind == "gather_at"
    assert intent.point == (10, 0)


def test_gather_mode_idles_without_self_or_food() -> None:
    assert GatherMode().decide(Belief(self_xy=None, food_gardens=(_garden(4000, (10, 0)),)), ActionState()).kind == "idle"
    assert GatherMode().decide(Belief(self_xy=(0, 0), food_gardens=()), ActionState()).kind == "idle"


def test_host_mode_navigates_to_home_anchor_when_far() -> None:
    intent = HostMode().decide(Belief(self_xy=(0, 0), home_anchor=(100, 0)), ActionState())

    assert intent.kind == "navigate_to"
    assert intent.point == (100, 0)


def test_host_mode_holds_inside_home_radius() -> None:
    intent = HostMode().decide(Belief(self_xy=(HOME_RADIUS, 0), home_anchor=(0, 0)), ActionState())

    assert intent.kind == "hold"


def test_host_mode_idles_without_home_anchor() -> None:
    assert HostMode().decide(Belief(self_xy=(0, 0), home_anchor=None), ActionState()).kind == "idle"


def test_idle_mode_returns_idle_intent() -> None:
    assert IdleMode().decide(Belief(self_xy=(0, 0)), ActionState()).kind == "idle"
