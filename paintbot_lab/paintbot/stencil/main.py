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
import base64
import json
import os
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
PLAYER_READY_PACKET = bytes([0x85])
SPRITES_OFF_PACKET = bytes([0x87])


class _RecordingConnection:
    """Transparent websocket wrapper for byte-exact differential fixtures."""

    def __init__(self, connection, output) -> None:
        self._connection = connection
        self._output = output
        self._iterator = connection.__aiter__()

    def __aiter__(self):
        return self

    async def __anext__(self):
        message = await self._iterator.__anext__()
        self._record("in", message)
        return message

    async def send(self, message) -> None:
        self._record("out", message)
        await self._connection.send(message)

    def _record(self, direction: str, message) -> None:
        if isinstance(message, str):
            row = {"direction": direction, "type": "text", "data": message}
        else:
            row = {
                "direction": direction,
                "type": "binary",
                "data": base64.b64encode(bytes(message)).decode("ascii"),
            }
        self._output.write(json.dumps(row, separators=(",", ":")) + "\n")
        self._output.flush()


class _RecordingConnect:
    def __init__(self, connect, output_path: str) -> None:
        self._connect = connect
        self._output_path = output_path
        self._context = None
        self._output = None

    def __call__(self, url: str, **kwargs):
        self._context = self._connect(url, **kwargs)
        return self

    async def __aenter__(self):
        self._output = open(self._output_path, "w", encoding="utf-8")
        connection = await self._context.__aenter__()
        return _RecordingConnection(connection, self._output)

    async def __aexit__(self, *args):
        try:
            return await self._context.__aexit__(*args)
        finally:
            self._output.close()


def enable_fast_ready() -> None:
    """Append accelerated Sprite-v1 control packets during local self-play.

    This is deliberately opt-in: the local self-play harness enables it, while
    ordinary hosted policy runs retain their existing pacing behavior. The
    exact canonical server used by self-play supports ready (0x85) and
    pixel-free bot traffic (0x87).
    """
    original_pack_outbound = _sprite_bridge._pack_outbound
    if getattr(original_pack_outbound, "_stencil_fast_ready", False):
        return

    def pack_outbound_with_ready(mask: int | None, chat: str | None) -> list[bytes]:
        return [
            *original_pack_outbound(mask, chat),
            SPRITES_OFF_PACKET,
            PLAYER_READY_PACKET,
        ]

    pack_outbound_with_ready._stencil_fast_ready = True  # type: ignore[attr-defined]
    _sprite_bridge._pack_outbound = pack_outbound_with_ready


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
    if os.environ.get("STENCIL_FAST_READY") == "1":
        enable_fast_ready()
        print("stencil: fast-ready enabled", file=sys.stderr, flush=True)
    print(f"stencil: slot={slot} url={url}", file=sys.stderr, flush=True)
    outputs = build_trace_outputs()
    decide = build_decide(slot, trace_sink=outputs.trace_sink)
    connect = None
    wire_record = os.environ.get("STENCIL_WIRE_RECORD")
    if wire_record:
        import websockets

        connect = _RecordingConnect(websockets.connect, wire_record)
    asyncio.run(
        run_sprite_bridge(
            url,
            decide,
            trace_outputs=outputs,
            connect=connect,
            ping_interval=None,
            max_size=None,
        )
    )


if __name__ == "__main__":
    main()
