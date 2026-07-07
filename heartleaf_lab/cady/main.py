"""Cady player entry point."""

from __future__ import annotations

import asyncio
import os
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from cady.decide import build_decide
from players.player_sdk import (
    TraceOutputs,
    env_ws_url,
    parse_trace_output_specs,
    run_sprite_bridge,
)

DEFAULT_TRACE_OUTPUTS = "jsonl@artifact"
FALLBACK_TRACE_OUTPUTS = "jsonl@stderr"
#: Heartleaf reads the player's display name from a ``?username=`` query param on the
#: connection URL (heartleaf.nim). Announce ourselves as "Cady" (override via env).
USERNAME = os.getenv("CADY_USERNAME", "Cady")


def _with_username(url: str, username: str) -> str:
    """Return ``url`` with a ``username=`` query param set (preserving others)."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "username"]
    query.append(("username", username))
    return urlunsplit(parts._replace(query=urlencode(query)))


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

    url = _with_username(env_ws_url(), USERNAME)
    outputs = build_trace_outputs()
    decide = build_decide(trace_sink=outputs.trace_sink, metrics_sink=outputs.metrics_sink)
    asyncio.run(run_sprite_bridge(url, decide, trace_outputs=outputs))


if __name__ == "__main__":
    main()
