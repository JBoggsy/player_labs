"""beacon entry point — connect to the runner's sprite websocket and play.

Team + seat are derived from the connection slot (even = red, odd = blue; seat = slot//2),
matching the CTF server's slot->team assignment. The websocket keepalive is disabled:
beacon's decide runs synchronously inside the async loop, so a slow frame could otherwise
trip the library's ping/pong timeout and drop the connection mid-game (a lesson from cady).

Tracing: structured trace events (snapshots + transitions from decide.py) are routed
through the SDK ``TraceOutputs`` — by default ``jsonl@artifact``, so they land in the
episode's player-artifact zip for the event warehouse. Override with ``BEACON_TRACE_OUTPUTS``
(e.g. ``parquet@artifact``, ``jsonl@stderr``); falls back to stderr outside a runner. Set
``BEACON_DIAG_EVERY_TICKS=1`` for a per-tick, full-resolution trace.
"""

from __future__ import annotations

import asyncio
import sys
from urllib.parse import parse_qs, urlsplit

from ctf.beacon.decide import build_decide
from ctf.beacon.types import Team
from players.player_sdk import (
    TraceOutputs,
    env_ws_url,
    parse_trace_output_specs,
    run_sprite_bridge,
)

DEFAULT_TRACE_OUTPUTS = "jsonl@artifact"
FALLBACK_TRACE_OUTPUTS = "jsonl@stderr"


def _slot_from_url(url: str) -> int:
    try:
        return int(parse_qs(urlsplit(url).query).get("slot", ["0"])[0])
    except (ValueError, IndexError):
        return 0


def team_from_url(url: str) -> Team:
    """Even slot = red (left), odd slot = blue (right). Defaults to red."""
    return "red" if _slot_from_url(url) % 2 == 0 else "blue"


def seat_from_url(url: str) -> int:
    """Per-team seat 0..7 = slot // 2 (fixes the role and defender hold point)."""
    return min(_slot_from_url(url) // 2, 7)


def build_trace_outputs() -> TraceOutputs:
    """Build SDK trace outputs (BEACON_TRACE_OUTPUTS), falling back to stderr."""
    try:
        return TraceOutputs.from_env(prefix="BEACON", default_outputs=DEFAULT_TRACE_OUTPUTS)
    except ValueError as exc:
        print(
            f"WARNING: trace outputs unavailable ({exc}); falling back to {FALLBACK_TRACE_OUTPUTS}",
            file=sys.stderr,
            flush=True,
        )
        return TraceOutputs.from_specs(parse_trace_output_specs(FALLBACK_TRACE_OUTPUTS))


def main() -> None:
    url = env_ws_url()
    team = team_from_url(url)
    seat = seat_from_url(url)
    print(f"beacon: team={team} seat={seat} url={url}", file=sys.stderr, flush=True)
    outputs = build_trace_outputs()
    decide = build_decide(team, seat, trace_sink=outputs.trace_sink)
    asyncio.run(run_sprite_bridge(url, decide, trace_outputs=outputs, ping_interval=None, max_size=None))


if __name__ == "__main__":
    main()
