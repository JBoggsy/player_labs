"""Wowborg player entry point."""

from __future__ import annotations

import asyncio
import sys

from players.player_sdk import TraceOutputs, env_ws_url, parse_trace_output_specs

from wowborg.run import run


DEFAULT_TRACE_OUTPUTS = "jsonl@artifact"
FALLBACK_TRACE_OUTPUTS = "jsonl@stderr"


def build_trace_outputs() -> TraceOutputs:
    """Build SDK trace outputs, falling back to stderr outside a runner."""

    try:
        return TraceOutputs.from_env(prefix="WOWBORG", default_outputs=DEFAULT_TRACE_OUTPUTS)
    except ValueError as exc:
        print(
            f"WARNING: trace outputs unavailable ({exc}); falling back to {FALLBACK_TRACE_OUTPUTS}",
            file=sys.stderr,
            flush=True,
        )
        return TraceOutputs.from_specs(parse_trace_output_specs(FALLBACK_TRACE_OUTPUTS))


def main() -> None:
    """Run wowborg against the runner-provided Coworld websocket URL."""

    outputs = build_trace_outputs()
    raise SystemExit(asyncio.run(run(env_ws_url(), trace_outputs=outputs)))
