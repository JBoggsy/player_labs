"""Runtime assembly for Cady's cyborg policy."""

from __future__ import annotations

from cady.action import resolve_action
from cady.belief import update_belief
from cady.modes import GatherMode, HostMode, IdleMode
from cady.perception import perceive
from cady.strategy import ClockStrategy
from cady.types import ActionState, Belief, Command, HeartleafState, Intent, Observation
from players.player_sdk import (
    AgentRuntime,
    MetricsSink,
    ModeDirective,
    ModeRegistry,
    SynchronousStrategyRunner,
    TraceSink,
)


def build_runtime(
    *,
    trace_sink: TraceSink | None = None,
    metrics_sink: MetricsSink | None = None,
) -> AgentRuntime[Observation, HeartleafState, Belief, ActionState, Intent, Command]:
    """Assemble Cady's ``perceive -> belief -> mode -> action`` runtime."""

    registry: ModeRegistry[Belief, ActionState, Intent] = ModeRegistry()
    registry.register(IdleMode)
    registry.register(GatherMode)
    registry.register(HostMode)

    return AgentRuntime(
        belief=Belief(),
        action_state=ActionState(),
        perceive=_perceive_for_runtime,
        update_belief=update_belief,
        resolve_action=resolve_action,
        mode_registry=registry,
        default_directive=ModeDirective(mode="idle", source="default", reason="default idle"),
        strategy_runner=SynchronousStrategyRunner(
            ClockStrategy(),
            trace_sink=trace_sink,
            metrics_sink=metrics_sink,
        ),
        trace_sink=trace_sink,
        metrics_sink=metrics_sink,
    )


def _perceive_for_runtime(obs: Observation, tick: int) -> HeartleafState:
    del tick
    return perceive(obs)


__all__ = ["build_runtime"]
