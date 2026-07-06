"""Sprite bridge decide adapter for Cady."""

from __future__ import annotations

from collections.abc import Callable

from cady.runtime import build_runtime
from cady.types import Observation
from players.player_sdk import MetricsSink, SpriteContext, SpriteWorld, TraceSink


def build_decide(
    *,
    trace_sink: TraceSink | None = None,
    metrics_sink: MetricsSink | None = None,
) -> Callable[[SpriteWorld, SpriteContext], int]:
    """Build a stateful bridge callback backed by one runtime instance."""

    runtime = build_runtime(trace_sink=trace_sink, metrics_sink=metrics_sink)

    def _decide(world: SpriteWorld, ctx: SpriteContext) -> int:
        command = runtime.step(Observation(world=world, frame=ctx.frame))
        return int(command.held_mask)

    return _decide


_DEFAULT_DECIDE = build_decide()


def decide(world: SpriteWorld, ctx: SpriteContext) -> int:
    """Default module-level callback for ``run_sprite_bridge`` convenience."""

    return _DEFAULT_DECIDE(world, ctx)


__all__ = ["build_decide", "decide"]
