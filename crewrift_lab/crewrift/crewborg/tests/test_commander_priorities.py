from __future__ import annotations

import pytest

from crewrift.crewborg.types import Belief, CommanderPriorities


def test_belief_defaults_commander_none() -> None:
    assert Belief().commander is None


def test_commander_priorities_defaults() -> None:
    priorities = CommanderPriorities()
    assert priorities.posture == "neutral"
    assert priorities.target_room is None
    assert priorities.allow_witnessed_kill is False
    assert priorities.as_of_tick == 0


def test_commander_priorities_is_frozen() -> None:
    priorities = CommanderPriorities(target_room="electrical")

    with pytest.raises(Exception):
        priorities.target_room = "medbay"
