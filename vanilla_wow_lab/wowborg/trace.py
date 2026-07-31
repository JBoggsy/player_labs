"""Structured tracing for wowborg — every decision, intent, and outcome, twice.

Hosted lesson (session 3): per-agent policy stdout was NOT retained by the platform, so a
single log channel is a single point of evidence loss. The tracer therefore writes each
event to BOTH:

1. a JSONL trace file (``WOWBORG_TRACE_FILE``, default ``<runtime_dir>/trace.jsonl``) —
   the machine-readable record our report tooling parses if artifacts are retained, and
2. stdout with a ``WOWBORG-TRACE`` prefix — greppable in whatever log capture exists.

A third, replay-visible channel (``/say`` breadcrumbs, which the CWREPLAY v4 format
records as real chat packets) is emitted by policies via the environment session — see
``GymSession.say`` — not by the tracer; it costs game actions and is rate-limited.

Event shape: one JSON object per line — ``{"ts": <unix>, "seq": <int>, "kind": <str>,
**payload}``. Kinds are free-form strings; established ones: ``session_start``,
``observation``, ``intent``, ``outcome``, ``leg``, ``say``, ``error``, ``session_end``.
The `/player` observer adds ``player_session_connected``, ``player_progress``,
``player_session_final``, ``player_session_done``, and ``player_session_error``.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class Tracer:
    def __init__(self, trace_file: Path | str | None, *, echo_stdout: bool = True) -> None:
        self._path = Path(trace_file) if trace_file is not None else None
        self._echo = echo_stdout
        self._seq = 0
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, runtime_dir: Path) -> "Tracer":
        override = os.environ.get("WOWBORG_TRACE_FILE")
        return cls(Path(override) if override else runtime_dir / "trace.jsonl")

    def emit(self, kind: str, **payload: Any) -> None:
        self._seq += 1
        event = {"ts": round(time.time(), 3), "seq": self._seq, "kind": kind, **payload}
        line = json.dumps(event, separators=(",", ":"), default=str)
        if self._path is not None:
            try:
                with self._path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
            except OSError:
                pass  # never let tracing kill the slot; stdout still carries the event
        if self._echo:
            print(f"WOWBORG-TRACE {line}", flush=True)


class NullTracer(Tracer):
    """For tests and callers that don't care."""

    def __init__(self) -> None:
        super().__init__(None, echo_stdout=False)

    def emit(self, kind: str, **payload: Any) -> None:  # noqa: ARG002
        self._seq += 1
