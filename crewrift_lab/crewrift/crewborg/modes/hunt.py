"""Hunt mode: kill-ready pursuit of a visible victim (imposter; design §7.2).

Selected only when the kill is ready and a non-teammate crewmate is visible.
Search owns the pre-cooldown lead window and target acquisition; Hunt owns the
actual kill-ready close/strike behavior. Hunt commits to a visible victim, leads
its motion so it closes range on a moving target, and strikes when the victim is
in range and the kill would go **unwitnessed**:

- pick the most-isolated reachable visible crewmate
  (``strategy.opportunity.select_victim``)
  and stick with it until it's killed or lost;
- navigate to its **predicted intercept** point (``strategy.trajectory``) — leading a
  moving target instead of tail-chasing its live position at equal speed;
- when within KillRange and unwitnessed → ``kill``; if a witness is near, keep
  shadowing (lie in wait) rather than blowing the kill. The urgency bar relaxes
  the witness requirement over time, so a perpetually-shadowed kill still
  eventually fires. **After our first kill the witness requirement is dropped
  entirely** (``last_kill_tick`` set ⇒ strike regardless of witnesses): banking
  the second kill is the imposter's core job and conversion beats stealth there.

Victim selection also has a local teammate-claim heuristic: if a recently seen
fellow imposter is already closer to a target, prefer another victim when one
exists.
"""

from __future__ import annotations

import math

from crewrift.crewborg.action import KILL_RANGE_SQ
from crewrift.crewborg.modes import imposter_common as ic
from crewrift.crewborg.nav import plan_route
from crewrift.crewborg.strategy.commander.bias import commander_of
from crewrift.crewborg.strategy.opportunity import (
    BASE_ISOLATION_RADIUS,
    WITNESS_WINDOW_TICKS,
    kill_urgency_ticks,
    select_victim,
    unwitnessed,
    urgency_full_ticks,
    visible_victims,
)
from crewrift.crewborg.strategy.trajectory import lead_ticks, predict
from crewrift.crewborg.types import ActionState, Belief, Intent, PlayerRecord
from players.player_sdk import EmptyModeParams, Mode, ModeParams


class HuntMode(Mode[Belief, ActionState, Intent]):
    name = "hunt"
    params_type = EmptyModeParams

    def __init__(self, params: ModeParams | None = None) -> None:
        super().__init__(params)
        self._victim_color: str | None = None  # the crewmate we have committed to hunting

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        self_xy = ic.self_xy(belief)
        if self_xy is None:
            return Intent(kind="idle", reason="no self position")

        victim = self._resolve_victim(belief)
        if victim is None:
            return Intent(kind="idle", reason="no victim to hunt")  # selector normally flips to Search/Pretend

        victim_xy = (victim.world_x, victim.world_y)
        in_range = ic.dist2(self_xy, victim_xy) <= KILL_RANGE_SQ

        # Strike when kill-ready and in range. The kill fires if it goes UNWITNESSED (the
        # normal case), OR we've already banked a kill — after our first kill the witness
        # requirement is dropped, since getting the SECOND kill is the imposter's core job
        # (2 imposters × 2 = parity, and at the 2nd ready we're usually already close to
        # crew, so conversion beats stealth; James 2026-06-26) — OR the commander's danger
        # mode explicitly allows a witnessed kill.
        cmd = commander_of(belief)
        already_killed = belief.last_kill_tick is not None
        kill_is_unwitnessed = unwitnessed(belief, victim)
        danger_witness_allowed = cmd is not None and cmd.allow_witnessed_kill
        strikes = in_range and belief.self_kill_ready and (kill_is_unwitnessed or already_killed or danger_witness_allowed)
        if belief.self_kill_ready:
            outcome = "strike" if strikes else ("wait_witness" if in_range else "approach")
            self.emit.event(
                "hunt_block",
                _hunt_block_payload(belief, victim, self_xy, in_range, outcome, kill_is_unwitnessed, already_killed),
            )
        if strikes:
            if not kill_is_unwitnessed and danger_witness_allowed:
                self.emit.event(
                    "commander_danger",
                    {
                        "lever": "allow_witnessed_kill",
                        "danger_reason": cmd.danger_reason,
                        "target_color": victim.color,
                    },
                )
            reason = (
                "striking the 2nd+ kill (witnesses ignored)"
                if already_killed and not kill_is_unwitnessed
                else "striking isolated victim"
            )
            return Intent(kind="kill", target_color=victim.color, reason=reason)

        # Otherwise close on the predicted intercept (lead a moving target) and shadow.
        # When already in range we lie in wait if a witness is near. The urgency
        # bar relaxes the witness test over time.
        intercept = predict(victim, lead_ticks(self_xy, victim_xy))
        if in_range:
            reason = "lying in wait (witness)"
        else:
            reason = "stalking the victim"
        return Intent(kind="navigate_to", point=intercept, reason=reason)

    def _resolve_victim(self, belief: Belief) -> PlayerRecord | None:
        """Keep the committed victim while visible; otherwise commit to a new visible one."""

        current = belief.roster.get(self._victim_color) if self._victim_color is not None else None
        if (
            current is not None
            and current.color not in belief.teammate_colors
            and current.life_status != "dead"
            and current.last_seen_tick == belief.last_tick
        ):
            return current
        victim = self._commander_victim(belief) or select_victim(belief)
        self._victim_color = victim.color if victim is not None else None
        return victim

    def _commander_victim(self, belief: Belief) -> PlayerRecord | None:
        cmd = commander_of(belief)
        if cmd is None or cmd.target_player is None:
            return None
        victim = next((candidate for candidate in visible_victims(belief) if candidate.color == cmd.target_player), None)
        if victim is None or belief.nav is None:
            return victim
        self_xy = ic.self_xy(belief)
        if self_xy is None or not plan_route(belief.nav, self_xy, (victim.world_x, victim.world_y)):
            return None
        return victim


def _hunt_block_payload(
    belief: Belief,
    victim: PlayerRecord,
    self_xy: tuple[int, int],
    in_range: bool,
    outcome: str,
    kill_is_unwitnessed: bool,
    already_killed: bool,
) -> dict[str, object]:
    """Per-tick (kill-ready only) strike-gate telemetry: who Hunt is committed to,
    whether the committed victim vs. some OTHER visible crew is in kill range, and
    which gate term blocked the strike — the record that separates witness-veto
    starvation from committed-victim mismatch when reading a game.
    """

    urgency = kill_urgency_ticks(belief)
    victim_xy = (victim.world_x, victim.world_y)
    witnesses = [
        {"color": other.color, "dist_to_victim": round(math.dist(victim_xy, (other.world_x, other.world_y)), 1)}
        for other in belief.roster.values()
        if other.color != victim.color
        and other.color not in belief.teammate_colors
        and other.life_status != "dead"
        and belief.last_tick - other.last_seen_tick <= WITNESS_WINDOW_TICKS
        and ic.dist2(victim_xy, (other.world_x, other.world_y)) <= BASE_ISOLATION_RADIUS**2
    ]
    others = [
        (candidate, math.dist(self_xy, (candidate.world_x, candidate.world_y)))
        for candidate in visible_victims(belief)
        if candidate.color != victim.color
    ]
    nearest_other = min(others, key=lambda pair: pair[1]) if others else None
    return {
        "outcome": outcome,
        "victim_color": victim.color,
        "victim_dist": round(math.dist(self_xy, victim_xy), 1),
        "in_range": in_range,
        "unwitnessed": kill_is_unwitnessed,
        "already_killed": already_killed,
        "urgency_ticks": urgency,
        "urgency_frac": round(min(1.0, urgency / urgency_full_ticks()), 3),
        "witnesses": witnesses,
        "nearest_other": (
            {
                "color": nearest_other[0].color,
                "dist": round(nearest_other[1], 1),
                "in_kill_range": nearest_other[1] ** 2 <= KILL_RANGE_SQ,
            }
            if nearest_other is not None
            else None
        ),
    }
