"""Tests for Cady mode selection and mode decisions."""

from __future__ import annotations

from cady.config import HOME_RADIUS
from cady.modes import HostMode, IdleMode
from cady.strategy import ClockStrategy
from cady.types import ActionState, Belief
from pytest import MonkeyPatch


def test_strategy_selects_idle_when_self_unresolved() -> None:
    directive = ClockStrategy().select(Belief(self_xy=None))

    assert directive.mode == "idle"


def test_strategy_selects_gather_before_cutoff_without_visible_food() -> None:
    directive = ClockStrategy().select(Belief(self_xy=(0, 0), last_time_minutes=300, food_gardens=()))

    assert directive.mode == "gather"


def test_strategy_selects_host_after_cutoff() -> None:
    directive = ClockStrategy().select(Belief(self_xy=(0, 0), last_time_minutes=560, food_gardens=()))

    assert directive.mode == "host"


def test_strategy_selects_gather_when_time_is_unknown() -> None:
    directive = ClockStrategy().select(Belief(self_xy=(0, 0), last_time_minutes=None, food_gardens=()))

    assert directive.mode == "gather"


def test_host_mode_navigates_to_home_anchor_waypoint_when_far(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("cady.modes.host.navigator.next_waypoint", lambda belief, self_xy, goal: (20, 0))
    intent = HostMode().decide(Belief(self_xy=(0, 0), home_anchor=(100, 0)), ActionState())

    assert intent.kind == "navigate_to"
    assert intent.point == (20, 0)


def test_host_mode_holds_inside_home_radius() -> None:
    intent = HostMode().decide(Belief(self_xy=(HOME_RADIUS, 0), home_anchor=(0, 0)), ActionState())

    assert intent.kind == "hold"


def test_host_mode_idles_without_home_anchor() -> None:
    assert HostMode().decide(Belief(self_xy=(0, 0), home_anchor=None), ActionState()).kind == "idle"


def test_idle_mode_returns_idle_intent() -> None:
    assert IdleMode().decide(Belief(self_xy=(0, 0)), ActionState()).kind == "idle"
