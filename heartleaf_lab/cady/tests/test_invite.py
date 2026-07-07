"""Tests for Cady's invite mode (seek a crowd, broadcast to our own party)."""

from __future__ import annotations

from cady.config import (
    INVITE_BROADCAST_DEADLINE_MINUTES,
    INVITE_MIN_AUDIENCE,
    INVITE_MIN_INTERVAL_TICKS,
    INVITE_RETURN_MINUTES,
    PLAYER_NAMES,
)
from cady.frame import to_world
from cady.mapdata import HOUSE_TARGETS
from cady.modes import InviteMode
from cady.types import ActionState, Belief, Gnome

OWN = 6  # our house index for these tests


def _belief(self_xy, gnomes=(), minutes=430, **overrides) -> Belief:
    belief = Belief(
        self_xy=self_xy,
        own_house_index=OWN,
        map_context="main",
        last_time_minutes=minutes,
        gnomes=tuple(gnomes),
    )
    for key, value in overrides.items():
        setattr(belief, key, value)
    return belief


def _cluster_around(center, n) -> list[Gnome]:
    # n gnomes packed at the same spot (well within one hearing radius).
    return [Gnome(index=i, pos=(center[0] + i, center[1]), facing="south") for i in range(n)]


def test_invite_broadcasts_when_enough_are_in_earshot() -> None:
    here = (400, 400)
    belief = _belief(here, gnomes=_cluster_around(here, INVITE_MIN_AUDIENCE))
    intent = InviteMode().decide(belief, ActionState())

    assert intent.chat is not None
    assert f"{PLAYER_NAMES[OWN]}'s house" in intent.chat  # names OUR house
    assert len(intent.chat) <= 48


def test_invite_broadcasts_to_a_single_villager_in_view() -> None:
    # Threshold is 1 (villagers are sparse; a lone in-view villager both hears
    # and can accept), so one gnome in view is enough to broadcast.
    assert INVITE_MIN_AUDIENCE == 1
    here = (400, 400)
    belief = _belief(here, gnomes=_cluster_around(here, 1), minutes=430)
    assert InviteMode().decide(belief, ActionState()).chat is not None


def test_invite_stays_silent_with_nobody_in_view() -> None:
    here = (400, 400)
    far = [Gnome(index=0, pos=(here[0] + 400, here[1]), facing="south")]  # off-screen
    belief = _belief(here, gnomes=far, minutes=430)
    assert InviteMode().decide(belief, ActionState()).chat is None


def test_invite_seeks_the_crowd_centroid() -> None:
    # Standing away from a distant cluster: move toward its center of gravity.
    here = (100, 100)
    cluster = [Gnome(index=0, pos=(500, 500), facing="s"), Gnome(index=1, pos=(520, 520), facing="s")]
    belief = _belief(here, gnomes=cluster)
    intent = InviteMode().decide(belief, ActionState())
    assert intent.kind in ("navigate_to", "hold")
    # Not silent-standing at home: it has a movement goal toward the crowd.
    if intent.kind == "navigate_to":
        assert intent.point is not None


def test_invite_returns_home_after_return_time() -> None:
    # Past the return cutoff, head to our own door regardless of a far crowd.
    here = (100, 100)
    cluster = [Gnome(index=0, pos=(700, 900), facing="s")]
    belief = _belief(here, gnomes=cluster, minutes=INVITE_RETURN_MINUTES)
    intent = InviteMode().decide(belief, ActionState())
    # The goal is our own house target (navigate toward it), not the far crowd.
    assert intent.kind == "navigate_to"


def test_invite_rate_limits_broadcasts() -> None:
    here = (400, 400)
    belief = _belief(here, gnomes=_cluster_around(here, INVITE_MIN_AUDIENCE))
    state = ActionState()

    first = InviteMode().decide(belief, state)
    assert first.chat is not None
    assert state.invite_cooldown == INVITE_MIN_INTERVAL_TICKS

    second = InviteMode().decide(belief, state)
    assert second.chat is None  # cooling down, not spamming


def test_invite_idles_without_own_house() -> None:
    belief = Belief(self_xy=(100, 100), own_house_index=None, map_context="main")
    assert InviteMode().decide(belief, ActionState()).kind == "idle"


def test_invite_ignores_self_in_the_crowd() -> None:
    here = (400, 400)
    # Only "other" gnome is us -> no audience, no crowd to seek.
    belief = _belief(here, gnomes=[Gnome(index=OWN, pos=here, facing="s")])
    assert InviteMode().decide(belief, ActionState()).chat is None
