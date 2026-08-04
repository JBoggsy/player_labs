"""stencil entry point — connect to the runner's sprite websocket and play.

The connection slot seeds the color/seat guess (slot mod teams / slot div
teams); the real team count arrives in the init snapshot and the real color is
confirmed by the first self sighting. The websocket keepalive is disabled:
stencil's decide runs synchronously inside the async loop, and the one-time
WorldMap build (walkability decode + first Dijkstra) can take a beat on giant
boards — a ping/pong timeout there would drop the connection mid-game.

Tracing: structured trace events are routed through the SDK ``TraceOutputs`` —
by default ``jsonl@artifact`` so they land in the episode's player-artifact zip.
Override with ``STENCIL_TRACE_OUTPUTS``; ``STENCIL_DIAG_EVERY_TICKS=1`` gives a
per-tick trace.
"""

from __future__ import annotations

import asyncio
import sys
from urllib.parse import parse_qs, urlsplit

from paintbot.stencil.decide import build_decide
from players.player_sdk import (
    TraceOutputs,
    env_ws_url,
    parse_trace_output_specs,
    run_sprite_bridge,
)
import players.player_sdk.sprite_bridge as _sprite_bridge

# The grenade throw is the 8th controller bit (bitworld ButtonC = 128), but the
# SDK bridge clamps input masks to 7 bits — widen it (the game's pinned bitworld
# decodes the full byte). Remove once the SDK's INPUT_MASK_MAX learns ButtonC.
_sprite_bridge.INPUT_MASK_MAX = 0xFF

DEFAULT_TRACE_OUTPUTS = "jsonl@artifact"
FALLBACK_TRACE_OUTPUTS = "jsonl@stderr"


def slot_from_url(url: str) -> int:
    try:
        return int(parse_qs(urlsplit(url).query).get("slot", ["0"])[0])
    except (ValueError, IndexError):
        return 0


def build_trace_outputs() -> TraceOutputs:
    """Build SDK trace outputs (STENCIL_TRACE_OUTPUTS), falling back to stderr."""
    try:
        return TraceOutputs.from_env(prefix="STENCIL", default_outputs=DEFAULT_TRACE_OUTPUTS)
    except ValueError as exc:
        print(
            f"WARNING: trace outputs unavailable ({exc}); falling back to {FALLBACK_TRACE_OUTPUTS}",
            file=sys.stderr,
            flush=True,
        )
        return TraceOutputs.from_specs(parse_trace_output_specs(FALLBACK_TRACE_OUTPUTS))


def main() -> None:
    url = env_ws_url()
    slot = slot_from_url(url)
    print(f"stencil: slot={slot} url={url}", file=sys.stderr, flush=True)
    outputs = build_trace_outputs()
    decide = build_decide(slot, trace_sink=outputs.trace_sink)
    asyncio.run(
        run_sprite_bridge(url, decide, trace_outputs=outputs, ping_interval=None, max_size=None)
    )


if __name__ == "__main__":
    main()
