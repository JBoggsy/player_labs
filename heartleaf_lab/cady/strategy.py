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
    HOUSE_ENTER_MINUTES,
    INVITE_START_MINUTES,
)
from cady.types import ActionState, Belief
from players.player_sdk import BeliefSnapshot, ModeDirective

#: A host/invite directive stays valid this many ticks so a brief strategy hiccup
#: (or, later, LLM latency) never yanks us off the social plan and back. At 24 fps
#: this is a few seconds; these are stable, whole-evening commitments anyway.
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

        # Phase order: gather → invite (broadcast at our door, 3-5 PM) → host
        # (enter our house and hold, 5 PM through dinner). Inviting has to happen
        # OUTSIDE, visible at our door, BEFORE we go in — so it precedes host.
        if self._is_host_time(belief):
            return _directive("host", "house-enter cutoff reached", ttl=HOST_DIRECTIVE_TTL_TICKS)
        if self._is_invite_time(belief):
            return _directive("invite", "invite window open", ttl=HOST_DIRECTIVE_TTL_TICKS)
        return _directive("gather", "gathering food")

    def _is_invite_time(self, belief: Belief) -> bool:
        """True in the pre-dinner window (invite open → house-enter cutoff): stop
        gathering and stand at our door broadcasting invites, since only guests
        turn our food into score."""
        minutes = belief.last_time_minutes
        return minutes is not None and minutes >= INVITE_START_MINUTES

    def _is_host_time(self, belief: Belief) -> bool:
        """True at the hard house-enter cutoff: stop inviting, go inside to host
        (must be inside our own home at dinner to score)."""
        minutes = belief.last_time_minutes
        return minutes is not None and minutes >= HOUSE_ENTER_MINUTES


def _directive(mode: str, reason: str, *, ttl: int = 0) -> ModeDirective:
    return ModeDirective(mode=mode, source="strategy", reason=reason, ttl_ticks=ttl)


__all__ = ["SocialStrategy", "HOST_DIRECTIVE_TTL_TICKS"]
