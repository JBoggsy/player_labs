"""Idle mode: hold neutral input."""

from __future__ import annotations

from cady.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode


class IdleMode(Mode[Belief, ActionState, Intent]):
    """Default safe stance while perception is not ready."""

    name = "idle"
    params_type = EmptyModeParams

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del belief, action_state
        return Intent(kind="idle")


__all__ = ["IdleMode"]
