"""Clock-driven deterministic mode selection for Cady."""

from __future__ import annotations

from cady.config import GATHER_CUTOFF_MINUTES
from cady.types import ActionState, Belief
from players.player_sdk import BeliefSnapshot, ModeDirective


class ClockStrategy:
    """Select Idle, ExitHouse, Gather, or Host from current belief."""

    def decide(self, snapshot: BeliefSnapshot[Belief, ActionState]) -> ModeDirective:
        """StrategyRunner entry point."""

        with snapshot.read() as memory:
            return self.select(memory.belief)

    def select(self, belief: Belief) -> ModeDirective:
        """Return the directive Cady should run for this belief."""

        if belief.self_xy is None:
            return ModeDirective(mode="idle", source="strategy", reason="self unresolved")
        if belief.map_context == "home":
            return ModeDirective(mode="exit_house", source="strategy", reason="inside home")
        before_cutoff = belief.last_time_minutes is None or belief.last_time_minutes < GATHER_CUTOFF_MINUTES
        if before_cutoff:
            return ModeDirective(mode="gather", source="strategy", reason="before gather cutoff")
        return ModeDirective(mode="host", source="strategy", reason="host cutoff reached")


__all__ = ["ClockStrategy"]
