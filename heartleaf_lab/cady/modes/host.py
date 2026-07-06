"""Host mode: return to the recorded home anchor and hold there."""

from __future__ import annotations

from cady.config import HOME_RADIUS_SQ
from cady.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode


class HostMode(Mode[Belief, ActionState, Intent]):
    """Navigate to the morning anchor used as v1's home/hosting position."""

    name = "host"
    params_type = EmptyModeParams

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        if belief.self_xy is None or belief.home_anchor is None:
            return Intent(kind="idle")
        if _dist2(belief.self_xy, belief.home_anchor) <= HOME_RADIUS_SQ:
            return Intent(kind="hold")
        return Intent(kind="navigate_to", point=belief.home_anchor)


def _dist2(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


__all__ = ["HostMode"]
