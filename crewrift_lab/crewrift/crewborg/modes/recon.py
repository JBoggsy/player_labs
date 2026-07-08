"""Recon mode — pre-position on a crewmate just before the kill comes off cooldown.

Diagnosis (2026-06-25 warehouse head-to-head vs crewborg-aaln, "Aaron"): at the moment
our kill cooldown expires we have a crewmate in crewborg's view only ~53% of the time,
versus Aaron's 83% — we drift away from crew we saw earlier in the cooldown cycle, so
when we *can* kill there's no victim in hand and we dither. Recon closes that gap.

When the strategy gate computes that the real travel time to a target has caught up
with the remaining cooldown (reworked 2026-07-06 — was a fixed ``recon_window()``
ticks-before-ready), it routes here instead of Search. Recon does one thing:
**beeline to the most ISOLATED fresh crewmate** (live position when visible,
last-known position otherwise) so that the instant the cooldown clears, a victim is
in view and Hunt takes over and kills immediately — timed to arrive right as the
cooldown clears, not early.

The selector only sends us to a sighting worth beelining to: fresh within
``recon_staleness_ticks()`` and not already checked-and-found-empty ("spent" — see
``rule_based._live_recon_target``); stale/spent sightings fall through to Search's
room-checking FSM instead. Locally we still never stand on a ghost position (the
``_abandoned`` arrival handling below) and carry a ``ParkedGuard`` as insurance
against any future zero-length-route park while kill-ready. We re-derive
``recon_target`` here (rather than caching what the selector saw) so the target
and the timing the selector computed always agree — see ``strategy.opportunity``.
"""

from __future__ import annotations

from crewrift.crewborg.agent_tracking import best_seek_point, ranked_seek_points
from crewrift.crewborg.modes import imposter_common as ic
from crewrift.crewborg.strategy.commander.bias import commander_of
from crewrift.crewborg.strategy.opportunity import RECON_REACHED_RADIUS_SQ, recon_target
from crewrift.crewborg.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode, ModeParams

# We count ourselves as having "reached" a target's last-known spot within this radius
# (px). Shared with the selector's spent-target check (strategy/opportunity.py).
REACHED_RADIUS_SQ = RECON_REACHED_RADIUS_SQ


class ReconMode(Mode[Belief, ActionState, Intent]):
    name = "recon"
    params_type = EmptyModeParams

    def __init__(self, params: ModeParams | None = None) -> None:
        super().__init__(params)
        self._abandoned: str | None = None  # a target we reached but who had already left
        self._parked_guard = ic.ParkedGuard()
        self._escape_point: ic.Point | None = None  # sticky un-park destination

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        self_xy = ic.self_xy(belief)
        if self_xy is None:
            return Intent(kind="idle", reason="recon: no self position")  # startup no-op (no camera)

        # A previously fired guard committed us to an escape point: keep walking there
        # until we arrive (or a crewmate shows up) — a one-tick escape would be no
        # escape at all, since _decide re-derives the same parked target every tick.
        if self._escape_point is not None:
            if ic.visible_crew(belief) or ic.dist2(self_xy, self._escape_point) <= REACHED_RADIUS_SQ:
                self._escape_point = None
            else:
                return Intent(kind="navigate_to", point=self._escape_point,
                              reason="recon: parked guard — moving to expected crew elsewhere")

        intent = self._decide(belief, self_xy)
        # PARKED GUARD (insurance — the selector shouldn't route a kill-ready blind
        # imposter here at all): never let a ready kill sit on a zero-length route.
        if self._parked_guard.fires(belief, self_xy, intent):
            self.emit.event(
                "parked_guard",
                {"mode": self.name, "state": "beeline", "intent": intent.kind, "reason": intent.reason},
            )
            intent = self._escape(belief, self_xy)
        return intent

    def _decide(self, belief: Belief, self_xy: ic.Point) -> Intent:
        target = self._commander_target(belief) or recon_target(belief)
        if target is not None:
            target_xy = (target.world_x, target.world_y)
            visible = target.last_seen_tick == belief.last_tick
            if visible:
                self._abandoned = None  # they're back in view — commit
                return Intent(kind="navigate_to", point=target_xy,
                              reason="recon: closing on a crewmate before the kill comes ready")
            reached = ic.dist2(self_xy, target_xy) <= REACHED_RADIUS_SQ
            if reached:
                # We walked to their last-known spot and they aren't here — abandon it (never
                # stand still on a ghost position; that was the recon-stall freeze).
                self._abandoned = target.color
            if target.color != self._abandoned:
                return Intent(kind="navigate_to", point=target_xy,
                              reason="recon: closing on a crewmate's last-known position")

        # No live/unreached target — fall back to SEARCH behaviour: head toward where crew are
        # expected. NEVER idle here (idling with no escape is the trap; see best_practices).
        seek = best_seek_point(belief)
        if seek is not None:
            return Intent(kind="navigate_to", point=ic.reachable_point(belief, seek),
                          reason="recon: no live target — seek toward expected crew")
        return Intent(kind="idle", reason="recon: no crew signal yet")  # rare: no occupancy built yet

    def _escape(self, belief: Belief, self_xy: ic.Point) -> Intent:
        """Forced un-park: abandon the current target and commit to the hottest
        occupancy point that is actually somewhere else (sticky via _escape_point)."""

        target = self._commander_target(belief) or recon_target(belief)
        if target is not None:
            self._abandoned = target.color
        for seek in ranked_seek_points(belief):
            point = ic.reachable_point(belief, seek)
            if ic.dist2(self_xy, point) > REACHED_RADIUS_SQ:
                self._escape_point = point
                return Intent(kind="navigate_to", point=point,
                              reason="recon: parked guard — moving to expected crew elsewhere")
        return Intent(kind="idle", reason="recon: parked guard fired but no crew signal to move on")

    def _commander_target(self, belief: Belief):
        cmd = commander_of(belief)
        if cmd is None or cmd.target_player is None or cmd.target_player in belief.teammate_colors:
            return None
        target = belief.roster.get(cmd.target_player)
        if target is None or target.life_status == "dead":
            return None
        return target
