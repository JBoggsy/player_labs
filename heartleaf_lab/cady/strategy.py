"""Clock-driven deterministic mode selection for Cady."""

from __future__ import annotations

from cady.config import GATHER_CUTOFF_MINUTES
from cady.types import ActionState, Belief
from players.player_sdk import BeliefSnapshot, ModeDirective


class ClockStrategy:
    """Select Idle, Gather, or Host from current belief."""

    def decide(self, snapshot: BeliefSnapshot[Belief, ActionState]) -> ModeDirective:
        """StrategyRunner entry point."""

        with snapshot.read() as memory:
            return self.select(memory.belief)

    def select(self, belief: Belief) -> ModeDirective:
        """Return the directive Cady should run for this belief."""

        if belief.self_xy is None:
            return ModeDirective(mode="idle", source="strategy", reason="self unresolved")
        before_cutoff = belief.last_time_minutes is None or belief.last_time_minutes < GATHER_CUTOFF_MINUTES
        if before_cutoff and belief.food_gardens:
            return ModeDirective(mode="gather", source="strategy", reason="food visible before cutoff")
        return ModeDirective(mode="host", source="strategy", reason="host cutoff reached or no food visible")


__all__ = ["ClockStrategy"]
