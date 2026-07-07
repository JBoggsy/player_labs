"""Deterministic social strategy: gather, then host through dinner.

This is the deterministic *floor* of the social controller
(``docs/designs/cady-social-llm-controller.md``). It selects a mode from the
clock + our food, on the same phase skeleton the starter villager uses
(``docs/villager-dinner-attendance.md``):

    gather  →  (food-rich by 3 PM → prep at home)  →  host through dinner

An optional LLM layer will later override this per-decision; until then this
plays a competent host game on its own, and it is what ships/evals. Increment 1
covers the *host our own party* path (the scoring path: score = food × guests).
Attending someone else's party (as a guest) is added with the invite/attend
modes; a guest scores 0, so hosting is our own scoring lever.
"""

from __future__ import annotations

from cady.config import (
    HOST_PREP_MINUTES,
    HOUSE_ENTER_MINUTES,
    STRONG_HOST_FOOD,
)
from cady.types import ActionState, Belief
from players.player_sdk import BeliefSnapshot, ModeDirective

#: A host directive stays valid this many ticks so a brief strategy hiccup (or,
#: later, LLM latency) never yanks us off hosting and back. At 24 fps this is a
#: few seconds; hosting is a stable, whole-evening commitment anyway.
HOST_DIRECTIVE_TTL_TICKS = 120


class SocialStrategy:
    """Select Idle, ExitHouse, Gather, or Host from clock + food."""

    def decide(self, snapshot: BeliefSnapshot[Belief, ActionState]) -> ModeDirective:
        """StrategyRunner entry point."""

        with snapshot.read() as memory:
            return self.select(memory.belief)

    def select(self, belief: Belief) -> ModeDirective:
        """Return the directive Cady should run for this belief."""

        if belief.self_xy is None:
            return _directive("idle", "self unresolved")
        if belief.map_context == "home":
            # We can only score by hosting from inside our own home at dinner, so
            # once it's host time we WANT to be home; otherwise leave to gather.
            if self._is_host_time(belief):
                return _directive("host", "host time, stay home", ttl=HOST_DIRECTIVE_TTL_TICKS)
            return _directive("exit_house", "inside home before host time")

        if self._is_host_time(belief):
            return _directive("host", self._host_reason(belief), ttl=HOST_DIRECTIVE_TTL_TICKS)
        return _directive("gather", "gathering food")

    def _is_host_time(self, belief: Belief) -> bool:
        """True once we should stop gathering and hold our own party.

        Two triggers, whichever comes first (mirrors the villager):
        - the hard house-enter cutoff (be in position before dinner), or
        - we're already food-rich by the prep hour (no need to keep gathering).
        """
        minutes = belief.last_time_minutes
        if minutes is None:
            # No clock yet: keep gathering (the safe default before dinner).
            return False
        if minutes >= HOUSE_ENTER_MINUTES:
            return True
        if minutes >= HOST_PREP_MINUTES and belief.inventory_count >= STRONG_HOST_FOOD:
            return True
        return False

    def _host_reason(self, belief: Belief) -> str:
        minutes = belief.last_time_minutes or 0
        if minutes >= HOUSE_ENTER_MINUTES:
            return "house-enter cutoff reached"
        return f"food-rich ({belief.inventory_count}) at prep time"


def _directive(mode: str, reason: str, *, ttl: int = 0) -> ModeDirective:
    return ModeDirective(mode=mode, source="strategy", reason=reason, ttl_ticks=ttl)


__all__ = ["SocialStrategy", "HOST_DIRECTIVE_TTL_TICKS"]
