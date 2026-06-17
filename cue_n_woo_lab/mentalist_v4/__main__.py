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
        engine = PhaseEngine(emit=emit, fingerprinter=fingerprinter, writer=writer)
        _log(f"connecting to {url}")
        await run_message_bridge(
            url, Handler(engine), trace_outputs=out,
            ping_interval=None, max_size=None,
        )


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
