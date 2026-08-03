"""stencil runtime — the per-tick perceive -> believe -> decide -> act pipeline.

The paintbot-specific responsibility here (vs beacon) is WORLD MODEL LIFECYCLE:
the episode's WorldMap is built the first frame all three init inputs are
present (the ``game teams`` marker, the endzone markers, the decoded walkability
sprite), and rebuilt if the map signature ever changes (a second game in one
process would define a new walkability sprite). Roles and hold points derive
once the map exists, because they need the real roster size and geometry.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from paintbot.stencil.action import resolve_action
from paintbot.stencil.belief import update_belief
from paintbot.stencil.chat import choose_shout
from paintbot.stencil.config import CHAT, TEAM_COLORS
from paintbot.stencil.perception import perceive
from paintbot.stencil.roles import hold_point_for_seat, role_for_seat
from paintbot.stencil.types import (
    ActionState,
    Belief,
    Command,
    Intent,
    Observation,
    PaintState,
    Team,
)
from paintbot.stencil.worldmap import Endzone, WorldMap


@dataclass(frozen=True)
class StepInfo:
    """End-of-tick snapshot for diagnostics."""

    tick: int
    percept: PaintState
    belief: Belief
    intent: Intent
    flow_goal: tuple[int, int] | None
    command: Command


StepHook = Callable[[StepInfo], None]


class StencilRuntime:
    """Holds the folded belief/action state and runs one tick per frame."""

    def __init__(self, slot: int, *, on_step: StepHook | None = None) -> None:
        # Color/seat are re-dealt once the team count is known (first frame);
        # start from the 2-team guess so pre-init frames are harmless.
        self.slot = slot
        self.belief = Belief(
            team=TEAM_COLORS[slot % 2],
            seat=min(slot // 2, 7),
            slot=slot,
        )
        self.action_state = ActionState()
        self.on_step = on_step
        self.tick = 0
        self._teams_known = False
        self._roles_assigned = False

    def _adopt_game_params(self, percept: PaintState) -> None:
        """Deal color + seat from the wire-stated team count (once)."""
        if self._teams_known or percept.game_teams is None:
            return
        teams = percept.game_teams
        self.belief.colors = tuple(TEAM_COLORS[:teams])
        if not self.belief.color_locked:
            self.belief.team = TEAM_COLORS[self.slot % teams]
        self.belief.seat = min(self.slot // teams, 7)
        self._teams_known = True

    def _ensure_worldmap(self, percept: PaintState) -> None:
        """Build (or rebuild) the episode WorldMap when the inputs are ready."""
        if percept.walkability is None or percept.game_teams is None:
            return
        teams = percept.game_teams
        expected = self.belief.colors or tuple(TEAM_COLORS[:teams])
        if len(percept.endzones) < len(expected):
            return  # endzone markers not all in yet
        h, w = percept.walkability.shape
        current = self.belief.worldmap
        if current is not None and current.signature() == (w, h, teams):
            return
        endzones = {
            color: Endzone(color, shape, *box)
            for color, (shape, box) in percept.endzones.items()
        }
        self.belief.worldmap = WorldMap(percept.walkability, teams, endzones)
        self._roles_assigned = False
        # Prime the two always-used flow fields while the lobby is still idle.
        team = self.belief.team
        if team is not None:
            wm = self.belief.worldmap
            wm.route_distance(wm.center, wm.capture_point(team))

    def _ensure_roles(self) -> None:
        """Assign role + hold point once the map (and thus roster size) is known."""
        wm = self.belief.worldmap
        if self._roles_assigned or wm is None or self.belief.team is None:
            return
        seats = wm.seats_per_team()
        self.belief.role = role_for_seat(self.belief.seat, seats)
        self.belief.hold_point = (
            hold_point_for_seat(wm, self.belief.team, self.belief.seat, seats)
            if self.belief.role == "defender"
            else None
        )
        self._roles_assigned = True

    def step(self, obs: Observation) -> Command:
        self.tick += 1
        colors = self.belief.colors
        team: Team = self.belief.team or "red"
        percept = perceive(obs, team, colors)
        self._adopt_game_params(percept)
        self._ensure_worldmap(percept)
        update_belief(self.belief, percept, self.action_state, self.tick)
        self._ensure_roles()

        from paintbot.stencil.strategy import decide_objective

        if not self.belief.alive:
            command = resolve_action(
                Intent(kind="hold", reason="not_alive"), self.belief, self.action_state
            )
            intent, flow_goal = Intent(kind="hold", reason="not_alive"), None
        else:
            intent, flow_goal = decide_objective(self.belief)
            command = resolve_action(intent, self.belief, self.action_state)
            if CHAT:
                shout = choose_shout(self.belief)
                if shout is not None:
                    self.belief.chat_last_sent_text = shout
                    command = Command(held_mask=command.held_mask, chat=shout)

        if self.on_step is not None:
            self.on_step(StepInfo(self.tick, percept, self.belief, intent, flow_goal, command))
        return command


__all__ = ["StencilRuntime", "StepHook", "StepInfo"]
