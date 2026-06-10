"""Crewborg's Sprite-v1 websocket bridge (design §3, AGENTS.md §Transport).

The bridge connects to the Crewrift engine, maintains a :class:`SceneState` as
binary messages arrive, drives ``runtime.step`` once per tick, and sends an input
packet only when the held button mask changes. It exits cleanly when the server
closes the socket (= game over).

Each incoming binary message is decoded into the ``SceneState`` and drives one
``runtime.step``; the held button mask is sent only when it changes, and meeting
chat is sent during Voting.

Environment:

- ``COWORLD_PLAYER_WS_URL`` — websocket URL including ``?slot=…&token=…``
  (the runner fills these in; token validation is at HTTP upgrade). The legacy
  ``COGAMES_ENGINE_WS_URL`` alias (same value) is accepted as a fallback.
- ``CREWBORG_TRACE_OUTPUTS`` — SDK trace output specs (``format@destination``,
  comma-separated; see ``players.player_sdk.trace_outputs``). Defaults to
  ``jsonl@artifact``: traces/metrics stream to a temp file and are zipped and
  uploaded to ``COWORLD_PLAYER_ARTIFACT_UPLOAD_URL`` at exit, keeping stderr
  under Observatory's policy-log line cap. When no upload URL is present (the
  bridge is running outside a Coworld runner), the bridge falls back to
  ``jsonl@stderr`` instead of crashing.
- ``CREWBORG_METRICS`` / ``CREWBORG_TRACE`` — metric fan-out and trace
  verbosity/filtering (see ``crewrift.crewborg.trace``).
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections.abc import Callable
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from crewrift.crewborg import build_runtime
from crewrift.crewborg.action import encode_chat, encode_input
from crewrift.crewborg.coworld.scene import SceneState
from crewrift.crewborg.map import walkability_matches
from crewrift.crewborg.trace import TraceConfig
from crewrift.crewborg.types import Observation
from players.player_sdk import TraceOutputs, parse_trace_output_specs

METRICS_ENV = "CREWBORG_METRICS"

DEFAULT_TRACE_OUTPUTS = "jsonl@artifact"
FALLBACK_TRACE_OUTPUTS = "jsonl@stderr"

# The engine pushes one frame per game tick at ~24 Hz and does NOT wait for the
# player (docs/crewrift-player.md). At the hosted 250m-CPU budget that gives
# runtime.step() ~42 ms per tick; exceeding it makes frames queue and inputs
# land late. The bridge latency metrics below exist to make that visible:
# `scene.tick` is a local received-message counter, so falling behind is
# invisible in tick numbers and must be measured in wall-clock.
ENGINE_TICK_HZ = 24.0


def build_trace_outputs() -> TraceOutputs:
    """Build the SDK trace outputs, defaulting to the player artifact zip.

    The artifact destination needs the runner-provided
    ``COWORLD_PLAYER_ARTIFACT_UPLOAD_URL``; the SDK raises when it is missing
    rather than skipping. Crashing here would happen before connect and fail
    the episode (a -100 connect timeout), so fall back to plain stderr JSONL
    — same content, just subject to the hosted log cap.
    """

    trace_config = TraceConfig.from_env()
    try:
        return TraceOutputs.from_env(
            prefix="CREWBORG",
            event_filter=trace_config.allows,
            metrics_enabled=_metrics_enabled(),
            default_outputs=DEFAULT_TRACE_OUTPUTS,
        )
    except ValueError as exc:
        print(
            f"WARNING: trace outputs unavailable ({exc}); falling back to {FALLBACK_TRACE_OUTPUTS}",
            file=sys.stderr,
            flush=True,
        )
        return TraceOutputs.from_specs(
            parse_trace_output_specs(FALLBACK_TRACE_OUTPUTS),
            event_filter=trace_config.allows,
            metrics_enabled=_metrics_enabled(),
        )


async def run_bridge(
    engine_ws_url: str,
    *,
    connect: Callable[..., Any] = websockets.connect,
    build: Callable[..., Any] = build_runtime,
) -> None:
    """Connect, run the per-tick loop, and return when the socket closes."""

    scene = SceneState()
    # The with-block guarantees outputs.close() runs at exit — that close is what
    # zips and uploads the artifact (when configured), so it must happen before
    # the container exits and the runner tears the pod down.
    with build_trace_outputs() as outputs:
        runtime = build(trace_sink=outputs.trace_sink, metrics_sink=outputs.metrics_sink)
        metrics = outputs.metrics_sink
        last_sent_mask: int | None = None
        walkability_checked = False
        first_message_wall: float | None = None
        previous_arrival: float | None = None

        # Guarantee runtime cleanup (the strategy runner may own background
        # threads/tasks) even if connect, a step, or a shutdown-race send raises.
        try:
            async with connect(engine_ws_url, max_size=None) as websocket:
                try:
                    async for message in websocket:
                        if isinstance(message, str):
                            # The /player stream is binary Sprite-v1; ignore stray text.
                            continue
                        # Latency metrics (no-ops unless CREWBORG_METRICS is on).
                        # loop_gap_ms: wall-clock between consecutive frame
                        # arrivals — sustained gaps *below* the ~42 ms frame
                        # interval mean queued frames are being drained, i.e.
                        # we had fallen behind the engine.
                        arrival = time.perf_counter()
                        if first_message_wall is None:
                            first_message_wall = arrival
                        if previous_arrival is not None:
                            metrics.histogram(
                                "bridge.loop_gap_ms",
                                round((arrival - previous_arrival) * 1000.0, 3),
                                tags={"tick": scene.tick + 1},
                            )
                        scene.apply(message)
                        scene.tick += 1

                        # Validate the baked map against the streamed walkability mask
                        # once it arrives (design §6); a size mismatch means a different
                        # map than croatoan. Warn loudly rather than misnavigate later.
                        if not walkability_checked and scene.walkability is not None:
                            walkability_checked = True
                            map_data = runtime.belief.map
                            if map_data is not None and not walkability_matches(
                                map_data, scene.walkability_width, scene.walkability_height
                            ):
                                print(
                                    "WARNING: walkability map "
                                    f"{scene.walkability_width}x{scene.walkability_height} does not match "
                                    f"baked map {map_data.width}x{map_data.height}; server may be running "
                                    "a different map than croatoan.",
                                    file=sys.stderr,
                                    flush=True,
                                )
                            # Optional capture: emit the streamed walkability mask once
                            # so tools/nav_bake.py can re-bake the offline nav asset when
                            # the map changes. Inert unless CREWBORG_CAPTURE_WALKABILITY
                            # is set; the mask is the authoritative input crewborg sees.
                            if _capture_walkability_enabled():
                                _emit_walkability_capture(scene.walkability)

                        # step_ms: the per-tick compute budget check (~42 ms at
                        # 24 Hz). tick_drift: ticks the engine has likely run
                        # ahead of us (elapsed wall-clock x 24 Hz minus frames
                        # received) — growth over a game means we're losing the
                        # real-time race and inputs are landing late.
                        step_start = time.perf_counter()
                        command = runtime.step(Observation(scene=scene, tick=scene.tick))
                        step_end = time.perf_counter()
                        metrics.histogram(
                            "bridge.step_ms",
                            round((step_end - step_start) * 1000.0, 3),
                            tags={"tick": scene.tick},
                        )
                        metrics.gauge(
                            "bridge.tick_drift",
                            round((step_end - first_message_wall) * ENGINE_TICK_HZ - scene.tick, 2),
                            tags={"tick": scene.tick},
                        )

                        # Send only when the held mask changes (design §3.3). The first
                        # tick sends the neutral mask once, establishing "all released".
                        if command.held_mask != last_sent_mask:
                            await websocket.send(encode_input(command.held_mask))
                            last_sent_mask = command.held_mask

                        # Meeting chat (accepted only during Voting); sent as it appears.
                        if command.chat is not None:
                            await websocket.send(encode_chat(command.chat))
                        previous_arrival = arrival
                except ConnectionClosed:
                    # Game end: the Crewrift server closes the socket to signal the
                    # episode is over. It does so *abruptly* — no close handshake
                    # (code 1006, "no close frame received or sent") — which the
                    # websockets async iterator surfaces as ConnectionClosedError
                    # rather than swallowing (as it does a clean ConnectionClosedOK).
                    # Either way a close means the game is over: treat it as normal
                    # termination so the process exits 0. The Coworld runner requires
                    # every player container to exit 0; propagating here would fail
                    # the whole episode (runner._wait_for_player_exit).
                    print("game over: server closed the connection", file=sys.stderr, flush=True)
        finally:
            runtime.close()


def main() -> None:
    # Canonical player-contract var is COWORLD_PLAYER_WS_URL; COGAMES_ENGINE_WS_URL is
    # a legacy alias the runner also sets to the same value. Prefer the canonical one,
    # fall back to the alias (see metta docs/roles/PLAYER.md, ../../player-build.md).
    engine_ws_url = os.environ.get("COWORLD_PLAYER_WS_URL") or os.environ.get("COGAMES_ENGINE_WS_URL")
    if not engine_ws_url:
        raise SystemExit("no player websocket URL: set COWORLD_PLAYER_WS_URL "
                         "(or the legacy COGAMES_ENGINE_WS_URL)")
    asyncio.run(run_bridge(engine_ws_url))


def _metrics_enabled() -> bool:
    trace_level = os.environ.get("CREWBORG_TRACE", "").strip().lower()
    metrics_flag = os.environ.get(METRICS_ENV, "").strip().lower()
    return trace_level == "debug" or metrics_flag in {"1", "true", "yes", "on"}


def _capture_walkability_enabled() -> bool:
    return os.environ.get("CREWBORG_CAPTURE_WALKABILITY", "").strip().lower() in {"1", "true", "yes", "on"}


def _emit_walkability_capture(walkability: Any) -> None:
    """Print the walkability mask to stderr as one bit-packed, base64 JSON line.

    A line, not a file: the player container's filesystem isn't collected on local
    runs, but its stderr is (the policy log). ``tools/nav_bake.py capture`` reads
    this line back. ~100 KB packed for the croatoan mask — fine as a single line.
    """

    import base64
    import json

    import numpy as np

    mask = np.ascontiguousarray(walkability, dtype=bool)
    packed = np.packbits(mask)
    print(
        json.dumps(
            {
                "event": "walkability_capture",
                "shape": list(mask.shape),
                "packbits_b64": base64.b64encode(packed.tobytes()).decode("ascii"),
            }
        ),
        file=sys.stderr,
        flush=True,
    )


if __name__ == "__main__":
    main()
