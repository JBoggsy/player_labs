"""Hunt mode: kill-ready pursuit of a visible victim (imposter; design §7.2).

Selected only when the kill is ready and a non-teammate crewmate is visible.
Search owns the pre-cooldown lead window and target acquisition; Hunt owns the
actual kill-ready close/strike behavior. Hunt commits to a visible victim, leads
its motion so it closes range on a moving target, and strikes when the victim is
in range:

- pick the most-isolated reachable visible crewmate
  (``strategy.opportunity.select_victim``)
  and stick with it until it's killed or lost;
- navigate to its **predicted intercept** point (``strategy.trajectory``) — leading a
  moving target instead of tail-chasing its live position at equal speed;
- when within KillRange and kill-ready → ``kill``. **Witnesses are no longer a gate**
  (James 2026-06-30): both the 1st and 2nd+ kills strike regardless of witnesses. The
  no-witnesses requirement on the first kill was the main acquisition drag (crewborg sat
  ready-but-passive far from crew and passed on kill windows it should take); for a
  2-imposter game, aggression/conversion beats stealth. If in range but not yet
  kill-ready, lie in wait for the cooldown.

Victim selection also has a local teammate-claim heuristic: if a recently seen
fellow imposter is already closer to a target, prefer another victim when one
exists.
"""

from __future__ import annotations

from crewrift.crewborg.action import KILL_RANGE_SQ
from crewrift.crewborg.modes import imposter_common as ic
from crewrift.crewborg.nav import plan_route
from crewrift.crewborg.strategy.commander.bias import commander_of
from crewrift.crewborg.strategy.opportunity import select_victim, visible_victims
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

        # Strike whenever kill-ready and in range — witnesses are no longer a gate.
        # James 2026-06-30: the no-witnesses requirement on the FIRST kill was the main
        # acquisition drag (latest Prime data: crewborg sat ready-but-passive, median
        # 266px from crew, and passed on witnessed kill windows it should take); the 2nd+
        # kill already ignored witnesses. For a 2-imposter game, aggression/conversion
        # beats stealth. (The commander's allow_witnessed_kill danger lever is subsumed —
        # witnessed kills are now always allowed.)
        if in_range and belief.self_kill_ready:
            return Intent(kind="kill", target_color=victim.color, reason="striking in-range victim")

        # Otherwise close on the predicted intercept (lead a moving target) and shadow.
        # When already in range but not yet kill-ready, lie in wait for the cooldown.
        intercept = predict(victim, lead_ticks(self_xy, victim_xy))
        reason = "lying in wait (cooldown)" if in_range else "stalking the victim"
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
