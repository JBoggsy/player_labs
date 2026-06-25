"""Recon mode — pre-position on a crewmate just before the kill comes off cooldown.

Diagnosis (2026-06-25 warehouse head-to-head vs crewborg-aaln, "Aaron"): at the moment
our kill cooldown expires we have a crewmate in crewborg's view only ~53% of the time,
versus Aaron's 83% — we drift away from crew we saw earlier in the cooldown cycle, so
when we *can* kill there's no victim in hand and we dither. Recon closes that gap.

When the strategy gate sees the kill is within ``recon_window()`` ticks of ready (env
``CREWBORG_RECON_WINDOW``, default 100), it routes here instead of Search. Recon does
one thing: **beeline to the most-recently-seen crewmate** (live position when visible,
last-known position otherwise) so that the instant the cooldown clears, a victim is in
view and Hunt takes over and kills immediately.

Intentionally simple and aggressive for now — James's call is to test a short 100-tick
window and see what it does (a longer window risks the over-extension that gets Aaron
caught 39% of the time). Target selection + window live in ``strategy.opportunity``.
"""

from __future__ import annotations

from crewrift.crewborg.modes import imposter_common as ic
from crewrift.crewborg.strategy.opportunity import most_recent_victim
from crewrift.crewborg.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode, ModeParams


class ReconMode(Mode[Belief, ActionState, Intent]):
    name = "recon"
    params_type = EmptyModeParams

    def __init__(self, params: ModeParams | None = None) -> None:
        super().__init__(params)

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        target = most_recent_victim(belief)
        if target is None or ic.self_xy(belief) is None:
            # Gate only routes here when a crew has been seen; idle is a safe no-op.
            return Intent(kind="idle", reason="recon: no known crewmate to close on")
        return Intent(
            kind="navigate_to",
            point=(target.world_x, target.world_y),
            reason="recon: closing on a crewmate before the kill comes ready",
        )
