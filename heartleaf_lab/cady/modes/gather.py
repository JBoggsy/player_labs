"""Gather mode: move toward the nearest visible food garden."""

from __future__ import annotations

from cady.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode


class GatherMode(Mode[Belief, ActionState, Intent]):
    """Select the nearest currently visible food marker."""

    name = "gather"
    params_type = EmptyModeParams

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        if belief.self_xy is None or not belief.food_gardens:
            return Intent(kind="idle")
        garden = min(belief.food_gardens, key=lambda item: _dist2(belief.self_xy, item.pos))
        return Intent(kind="gather_at", point=garden.pos)


def _dist2(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


__all__ = ["GatherMode"]
