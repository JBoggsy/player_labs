"""Entry point: `python -m mentalist_v4`.

Wires the SDK's protocol-agnostic websocket bridge (run_message_bridge) + telemetry
(TraceOutputs) to the transport-free PhaseEngine. The bridge owns connect/iterate/send
and the exit-0-on-unclean-close rule; we own decoding the Cue-n-Woo JSON protocol and
the strategy.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

from players.player_sdk import TraceOutputs, run_message_bridge

from . import config
from .engine import PhaseEngine
from .fingerprint import Fingerprinter
from .writer import AnswerWriter


def _log(msg: str) -> None:
    print(f"[mentalist_v4] {msg}", file=sys.stderr, flush=True)


def _quiet_close(exc: BaseException | None) -> None:
    """Close policy for the reconnect loop: NEVER exit/raise on a websocket close —
    just return so the reconnect loop can re-establish the connection. The SDK default
    (exit_zero_on_unclean_close) ends the process on any close, so a transient mid-episode
    drop would orphan us for the rest of the episode -> inactive timeout -100 -> DQ. We
    only stop reconnecting once the engine has seen the real game-over (phase=reveal/done).
    """
    from websockets.exceptions import ConnectionClosed
    if exc is None or isinstance(exc, ConnectionClosed):
        return
    raise exc


class Handler:
    """Decodes one inbound frame, drives the engine, returns outbound frames."""

    def __init__(self, engine: PhaseEngine) -> None:
        self.engine = engine

    def __call__(self, message: str | bytes) -> list[str]:
        if isinstance(message, bytes):
            message = message.decode("utf-8", "replace")
        try:
            msg = json.loads(message)
        except (json.JSONDecodeError, TypeError):
            return []
        mtype = msg.get("type")
        if mtype == "error":
            self.engine.on_error(msg.get("error", "unknown validation error"))
            return []
        if mtype != "state":
            return []
        action = self.engine.decide(msg)
        return [json.dumps(action)] if action is not None else []


async def _run() -> None:
    url = os.environ.get("COWORLD_PLAYER_WS_URL")
    if not url:
        _log("COWORLD_PLAYER_WS_URL not set; nothing to do")
        return
    with TraceOutputs.from_env(prefix="MENTALIST") as out:
        emit = _emit_via(out)
        fingerprinter = Fingerprinter(emit=emit) if config.FINGERPRINT_ENABLED else None
        if fingerprinter is not None:
            _log(f"fingerprinter ready={fingerprinter.ready}")
        writer = AnswerWriter()
        # ONE engine instance across reconnects: it is idempotent (reads phase from each
        # state, guards in-flight actions via `pending` + per-slot state counts), so on
        # reconnect it resumes from the server's fresh state broadcast with no double-acting.
        engine = PhaseEngine(emit=emit, fingerprinter=fingerprinter, writer=writer)
        handler = Handler(engine)
        attempt = 0
        # ALWAYS BE RECONNECTING: the server may drop our socket mid-episode (idle during a
        # slow judge phase, or a transient blip). The SDK's default close policy exits the
        # process on any close, orphaning us -> inactive -100 -> DQ. Instead, loop and
        # reconnect until the engine has seen the real game-over (engine.done), bounded by
        # the outer hard timer. Each reconnect: server re-broadcasts current state, engine
        # resumes. `pending` is cleared on reconnect so a half-sent action is re-attempted.
        while not engine.done:
            attempt += 1
            engine.pending = None  # a reconnect means any in-flight send may have been lost; allow re-send
            _log(f"connecting to {url} (attempt {attempt}, done={engine.done})")
            try:
                await run_message_bridge(
                    url, handler, trace_outputs=None, on_close=_quiet_close,
                    ping_interval=20, ping_timeout=20, max_size=None, open_timeout=15,
                )
            except Exception as exc:  # connect failure / unexpected — keep trying until timer
                _log(f"bridge error (attempt {attempt}): {exc!r}")
            if engine.done:
                break
            await asyncio.sleep(min(2.0, 0.5 * attempt))  # brief backoff, capped
        _log(f"episode complete (engine.done={engine.done}, attempts={attempt})")


def _emit_via(out: "TraceOutputs"):
    """Adapt TraceOutputs.trace_sink into the engine's emit(name, data, *, step) hook."""
    from players.player_sdk import TraceEvent

    def emit(name: str, data: dict | None = None, *, step=None) -> None:
        full = name if name.startswith("domain.") else f"domain.{name}"
        out.trace_sink.record(TraceEvent(tick=0, step=step, name=full, data=dict(data or {})))

    return emit


def main() -> None:
    try:
        asyncio.run(asyncio.wait_for(_run(), timeout=config.EPISODE_HARD_TIMEOUT_SECONDS))
    except asyncio.TimeoutError:
        _log("hard timeout reached; exiting cleanly")


if __name__ == "__main__":
    main()
