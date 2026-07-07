"""Tests for Cady's invite mode (draw guests to our own party)."""

from __future__ import annotations

from cady.config import INVITE_HEARING_RADIUS, INVITE_MIN_INTERVAL_TICKS, PLAYER_NAMES
from cady.frame import to_world
from cady.mapdata import HOUSE_TARGETS
from cady.modes import InviteMode
from cady.types import ActionState, Belief, Gnome

OWN = 6  # our house index for these tests


def _at_own_door(**overrides) -> Belief:
    belief = Belief(
        self_xy=to_world(HOUSE_TARGETS[OWN]),
        own_house_index=OWN,
        map_context="main",
    )
    for key, value in overrides.items():
        setattr(belief, key, value)
    return belief


def _nearby_gnome() -> Gnome:
    x, y = to_world(HOUSE_TARGETS[OWN])
    return Gnome(index=0, pos=(x + 20, y), facing="south")  # well within earshot


def _far_gnome() -> Gnome:
    x, y = to_world(HOUSE_TARGETS[OWN])
    return Gnome(index=0, pos=(x + INVITE_HEARING_RADIUS + 50, y), facing="south")


def test_invite_broadcasts_when_someone_is_in_earshot() -> None:
    belief = _at_own_door(gnomes=(_nearby_gnome(),))
    intent = InviteMode().decide(belief, ActionState())

    assert intent.chat is not None
    assert f"{PLAYER_NAMES[OWN]}'s house" in intent.chat  # names OUR house
    assert len(intent.chat) <= 48


def test_invite_stays_silent_with_nobody_near() -> None:
    belief = _at_own_door(gnomes=(_far_gnome(),))
    intent = InviteMode().decide(belief, ActionState())

    assert intent.chat is None


def test_invite_rate_limits_broadcasts() -> None:
    belief = _at_own_door(gnomes=(_nearby_gnome(),))
    state = ActionState()

    first = InviteMode().decide(belief, state)
    assert first.chat is not None
    assert state.invite_cooldown == INVITE_MIN_INTERVAL_TICKS

    # Immediately after, we hold the line rather than re-broadcasting every tick.
    second = InviteMode().decide(belief, state)
    assert second.chat is None


def test_invite_holds_at_own_door() -> None:
    belief = _at_own_door(gnomes=())
    intent = InviteMode().decide(belief, ActionState())
    assert intent.kind == "hold"


def test_invite_idles_without_own_house() -> None:
    belief = Belief(self_xy=(100, 100), own_house_index=None, map_context="main")
    assert InviteMode().decide(belief, ActionState()).kind == "idle"


def test_invite_does_not_count_self_as_earshot() -> None:
    # The only visible gnome is us (index == own_house_index) → nobody to invite.
    x, y = to_world(HOUSE_TARGETS[OWN])
    belief = _at_own_door(gnomes=(Gnome(index=OWN, pos=(x, y), facing="south"),))
    assert InviteMode().decide(belief, ActionState()).chat is None
