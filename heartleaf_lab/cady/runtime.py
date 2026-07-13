"""Runtime assembly for Cady's cyborg policy."""

from __future__ import annotations

from cady.action import resolve_action
from cady.belief import update_belief
from cady.modes import AttendMode, ExitHouseMode, GatherMode, HostMode, IdleMode, InviteMode
from cady.perception import perceive
from cady.strategy import SocialStrategy
from cady.types import ActionState, Belief, Command, HeartleafState, Intent, Observation
from players.player_sdk import (
    AgentRuntime,
    MetricsSink,
    ModeDirective,
    ModeRegistry,
    SynchronousStrategyRunner,
    StepCompleteHook,
    TraceSink,
)


def build_runtime(
    *,
    trace_sink: TraceSink | None = None,
    metrics_sink: MetricsSink | None = None,
    on_step_complete: StepCompleteHook[Belief, ActionState, Intent, Command] | None = None,
) -> AgentRuntime[Observation, HeartleafState, Belief, ActionState, Intent, Command]:
    """Assemble Cady's ``perceive -> belief -> mode -> action`` runtime."""

    registry: ModeRegistry[Belief, ActionState, Intent] = ModeRegistry()
    registry.register(IdleMode)
    registry.register(ExitHouseMode)
    registry.register(GatherMode)
    registry.register(HostMode)
    registry.register(InviteMode)
    registry.register(AttendMode)

    return AgentRuntime(
        belief=Belief(),
        action_state=ActionState(),
        perceive=_perceive_for_runtime,
        update_belief=update_belief,
        resolve_action=resolve_action,
        mode_registry=registry,
        default_directive=ModeDirective(mode="idle", source="default", reason="default idle"),
        strategy_runner=SynchronousStrategyRunner(
            SocialStrategy(),
            trace_sink=trace_sink,
            metrics_sink=metrics_sink,
        ),
        trace_sink=trace_sink,
        metrics_sink=metrics_sink,
        on_step_complete=on_step_complete,
    )


def _perceive_for_runtime(obs: Observation, tick: int) -> HeartleafState:
    del tick
    return perceive(obs)


__all__ = ["build_runtime"]
