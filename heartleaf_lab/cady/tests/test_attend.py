"""Tests for Cady's attend mode (go to another gnome's party as a guest)."""

from __future__ import annotations

from cady.frame import to_world
from cady.mapdata import HOUSE_TARGETS
from cady.modes import AttendMode
from cady.types import ActionState, Belief

TARGET = 1  # the host's house we committed to


def test_attend_enters_host_house_on_its_footprint() -> None:
    belief = Belief(
        self_xy=to_world(HOUSE_TARGETS[TARGET]),
        own_house_index=6, committed_party_house=TARGET, map_context="main",
    )
    intent = AttendMode().decide(belief, ActionState())
    assert intent.kind == "gather_at"  # press A to enter the host's house


def test_attend_navigates_toward_host_house_when_far() -> None:
    belief = Belief(
        self_xy=to_world(HOUSE_TARGETS[3]),  # start on another walkable door
        own_house_index=6, committed_party_house=TARGET, map_context="main",
    )
    intent = AttendMode().decide(belief, ActionState())
    assert intent.kind in ("navigate_to", "gather_at")


def test_attend_holds_once_inside_a_home() -> None:
    belief = Belief(
        self_xy=(100, 60), own_house_index=6, committed_party_house=TARGET,
        map_context="home",
    )
    assert AttendMode().decide(belief, ActionState()).kind == "hold"


def test_attend_idles_without_a_committed_party() -> None:
    belief = Belief(self_xy=(400, 400), own_house_index=6,
                    committed_party_house=None, map_context="main")
    assert AttendMode().decide(belief, ActionState()).kind == "idle"
