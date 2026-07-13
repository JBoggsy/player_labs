"""beacon runtime — the per-tick perceive -> believe -> decide -> act pipeline.

Deliberately compact and direct (not the SDK's full mode-machine AgentRuntime): the
v1 brain is a short priority ladder plus a combat overlay, so a mode registry would be
ceremony. We keep the design's pipeline shape and expose an optional step-complete hook
for diagnostics; the SDK still owns transport (the sprite bridge) and trace outputs.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ctf.beacon.action import resolve_action
from ctf.beacon.belief import update_belief
from ctf.beacon.perception import perceive
from ctf.beacon.roles import hold_point_for_seat, role_for_seat
from ctf.beacon.strategy import decide_objective
from ctf.beacon.types import ActionState, Belief, Command, CtfState, Intent, Observation, Team


@dataclass(frozen=True)
class StepInfo:
    """End-of-tick snapshot for diagnostics."""

    tick: int
    percept: CtfState
    belief: Belief
    intent: Intent
    flow_kind: str | None
    command: Command


StepHook = Callable[[StepInfo], None]


class BeaconRuntime:
    """Holds the folded belief/action state and runs one tick per frame."""

    def __init__(self, team: Team, seat: int = 0, *, on_step: StepHook | None = None) -> None:
        role = role_for_seat(seat)
        self.belief = Belief(
            team=team,
            seat=seat,
            role=role,
            hold_point=hold_point_for_seat(team, seat) if role == "defender" else None,
        )
        self.action_state = ActionState()
        self.on_step = on_step
        self.tick = 0

    def step(self, obs: Observation) -> Command:
        self.tick += 1
        percept = perceive(obs, self.belief.team)
        update_belief(self.belief, percept, self.action_state)

        if not self.belief.alive:
            # Dead/ghost or not yet spawned: release inputs, hold state.
            command = resolve_action(Intent(kind="hold", reason="not_alive"), self.belief, self.action_state)
            intent, flow_kind = Intent(kind="hold", reason="not_alive"), None
        else:
            intent, flow_kind = decide_objective(self.belief)
            command = resolve_action(intent, self.belief, self.action_state)

        if self.on_step is not None:
            self.on_step(StepInfo(self.tick, percept, self.belief, intent, flow_kind, command))
        return command


__all__ = ["BeaconRuntime", "StepHook", "StepInfo"]
