"""Tests for Cady mode selection and mode decisions."""

from __future__ import annotations

from cady.config import (
    HOUSE_ENTER_MINUTES,
    INVITE_START_MINUTES,
)
from cady.frame import to_world
from cady.mapdata import HOUSE_TARGETS
from cady.modes import HostMode, IdleMode
from cady.strategy import HOST_DIRECTIVE_TTL_TICKS, SocialStrategy
from cady.types import ActionState, Belief
from pytest import MonkeyPatch


def test_strategy_selects_idle_when_self_unresolved() -> None:
    assert SocialStrategy().select(Belief(self_xy=None)).mode == "idle"


def test_strategy_exits_home_before_host_time() -> None:
    # Inside home early in the day: leave to gather.
    directive = SocialStrategy().select(
        Belief(self_xy=(0, 0), map_context="home", last_time_minutes=200)
    )
    assert directive.mode == "exit_house"


def test_strategy_stays_home_to_host_at_host_time() -> None:
    # Inside home after the house-enter cutoff: stay and host.
    directive = SocialStrategy().select(
        Belief(self_xy=(0, 0), map_context="home", last_time_minutes=HOUSE_ENTER_MINUTES)
    )
    assert directive.mode == "host"
    assert directive.ttl_ticks == HOST_DIRECTIVE_TTL_TICKS


def test_strategy_gathers_before_invite_window() -> None:
    directive = SocialStrategy().select(
        Belief(self_xy=(0, 0), last_time_minutes=INVITE_START_MINUTES - 60)
    )
    assert directive.mode == "gather"


def test_strategy_invites_in_the_pre_dinner_window() -> None:
    # From the invite window until the house-enter cutoff: broadcast invites.
    directive = SocialStrategy().select(
        Belief(self_xy=(0, 0), last_time_minutes=INVITE_START_MINUTES)
    )
    assert directive.mode == "invite"
    assert directive.ttl_ticks == HOST_DIRECTIVE_TTL_TICKS


def test_strategy_hosts_at_house_enter_cutoff() -> None:
    directive = SocialStrategy().select(
        Belief(self_xy=(0, 0), last_time_minutes=HOUSE_ENTER_MINUTES)
    )
    assert directive.mode == "host"
    assert directive.ttl_ticks == HOST_DIRECTIVE_TTL_TICKS


def test_strategy_gathers_when_time_is_unknown() -> None:
    directive = SocialStrategy().select(Belief(self_xy=(0, 0), last_time_minutes=None))
    assert directive.mode == "gather"


def test_host_mode_navigates_toward_own_house_when_far(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cady.modes.host.navigator.next_waypoint",
        lambda belief, self_xy, goal, *, grid: (20, 0),
    )
    intent = HostMode().decide(
        Belief(self_xy=(0, 0), own_house_index=0, map_context="main"), ActionState()
    )
    assert intent.kind == "navigate_to"
    assert intent.point == (20, 0)


def test_host_mode_enters_own_house_when_on_its_footprint() -> None:
    # Standing on our house target on the main map: press A to go inside.
    target_world = to_world(HOUSE_TARGETS[0])
    intent = HostMode().decide(
        Belief(self_xy=target_world, own_house_index=0, map_context="main"), ActionState()
    )
    assert intent.kind == "gather_at"
    assert intent.point == target_world


def test_host_mode_holds_once_inside_home() -> None:
    intent = HostMode().decide(
        Belief(self_xy=(100, 60), own_house_index=0, map_context="home"), ActionState()
    )
    assert intent.kind == "hold"


def test_host_mode_idles_without_house_or_anchor() -> None:
    intent = HostMode().decide(
        Belief(self_xy=(0, 0), own_house_index=None, home_anchor=None, map_context="main"),
        ActionState(),
    )
    assert intent.kind == "idle"


def test_idle_mode_returns_idle_intent() -> None:
    assert IdleMode().decide(Belief(self_xy=(0, 0)), ActionState()).kind == "idle"
