"""Cady player entry point."""

from __future__ import annotations

import asyncio
import sys

from cady.decide import build_decide
from players.player_sdk import (
    TraceOutputs,
    env_ws_url,
    parse_trace_output_specs,
    run_sprite_bridge,
)

DEFAULT_TRACE_OUTPUTS = "jsonl@artifact"
FALLBACK_TRACE_OUTPUTS = "jsonl@stderr"


def build_trace_outputs() -> TraceOutputs:
    """Build SDK trace outputs, falling back to stderr outside a runner."""

    try:
        return TraceOutputs.from_env(prefix="CADY", default_outputs=DEFAULT_TRACE_OUTPUTS)
    except ValueError as exc:
        print(
            f"WARNING: trace outputs unavailable ({exc}); falling back to {FALLBACK_TRACE_OUTPUTS}",
            file=sys.stderr,
            flush=True,
        )
        return TraceOutputs.from_specs(parse_trace_output_specs(FALLBACK_TRACE_OUTPUTS))


def main() -> None:
    """Run Cady against the runner-provided SpriteV1 websocket URL."""

    url = env_ws_url()
    outputs = build_trace_outputs()
    decide = build_decide(trace_sink=outputs.trace_sink, metrics_sink=outputs.metrics_sink)
    asyncio.run(run_sprite_bridge(url, decide, trace_outputs=outputs))


if __name__ == "__main__":
    main()
