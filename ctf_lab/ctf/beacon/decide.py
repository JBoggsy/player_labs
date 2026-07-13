"""Sprite-bridge ``decide`` adapter for beacon, plus the trace logger.

``build_decide(team, seat, trace_sink=…)`` returns a stateful callback for
``run_sprite_bridge`` backed by one BeaconRuntime. When diagnostics are on (default;
disable with ``CTF_DIAG=0``) it records structured **TraceEvents** through the SDK
trace sink — periodic full-state ``snapshot`` events plus immediate transition events
(``objective`` / ``alive`` / ``engage``). Wired to ``TraceOutputs`` in ``main.py``, those
land as a ``jsonl``/``parquet`` member of the episode's player-artifact zip (queryable by
the event warehouse), not just as stderr lines. With no trace sink (e.g. an ad-hoc local
call) it falls back to printing ``CTF_DIAG`` lines to stderr.

Snapshot cadence is ``BEACON_DIAG_EVERY_TICKS`` (config) — set it to ``1`` for a
per-tick, full-resolution trace.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable

from ctf.beacon.config import DIAG_EVERY_TICKS
from ctf.beacon.runtime import BeaconRuntime, StepInfo
from ctf.beacon.types import Team
from players.player_sdk import SpriteContext, SpriteWorld, TraceEvent, TraceSink


def _diagnostics_enabled() -> bool:
    return os.getenv("CTF_DIAG", "1").strip().lower() not in {"0", "false", "off", "no"}


def build_decide(
    team: Team,
    seat: int = 0,
    *,
    trace_sink: TraceSink | None = None,
) -> Callable[[SpriteWorld, SpriteContext], int]:
    """Build a stateful bridge callback backed by one runtime instance.

    ``trace_sink`` (from the SDK ``TraceOutputs``) receives structured trace events.
    When it is ``None`` and diagnostics are enabled, events print to stderr instead.
    """
    if _diagnostics_enabled():
        sink = trace_sink if trace_sink is not None else _StderrTraceSink()
        diagnostics: _DiagnosticLogger | None = _DiagnosticLogger(sink)
    else:
        diagnostics = None
    runtime = BeaconRuntime(team, seat, on_step=diagnostics.on_step if diagnostics else None)

    def _decide(world: SpriteWorld, ctx: SpriteContext) -> int:
        command = runtime.step(_Obs(world, ctx.frame))
        return int(command.held_mask)

    return _decide


class _Obs:
    """Minimal Observation shim (avoids importing the dataclass constructor path)."""

    __slots__ = ("world", "frame")

    def __init__(self, world: SpriteWorld, frame: int) -> None:
        self.world = world
        self.frame = frame


class _StderrTraceSink:
    """Fallback sink: prints ``CTF_DIAG <name> <json>`` to stderr (no artifact URL).

    Matches the record shape a TraceSink writer would emit, so local greps stay stable.
    """

    def record(self, event: TraceEvent) -> None:
        print(
            f"CTF_DIAG {event.name} "
            + json.dumps({"tick": event.tick, **event.data}, separators=(",", ":"), sort_keys=True),
            file=sys.stderr,
            flush=True,
        )


class _DiagnosticLogger:
    """Periodic snapshots + transition events, recorded via a TraceSink.

    Everything a post-mortem needs to reconstruct what beacon believed and why it acted:
    a periodic full-state ``snapshot`` (cadence ``BEACON_DIAG_EVERY_TICKS``) plus immediate
    ``objective`` / ``alive`` / ``engage`` transition events.
    """

    def __init__(self, sink: TraceSink) -> None:
        self._sink = sink
        self._last_objective: str | None = None
        self._last_alive: bool | None = None
        self._last_engaged: bool | None = None

    def on_step(self, step: StepInfo) -> None:
        self._log_transitions(step)
        if step.tick % DIAG_EVERY_TICKS == 0 or (self._last_alive is None and step.belief.alive):
            self._record(step.tick, "snapshot", self._payload(step))

    def _log_transitions(self, step: StepInfo) -> None:
        b = step.belief
        objective = step.intent.reason
        if objective != self._last_objective:
            self._record(step.tick, "objective",
                         {"from": self._last_objective, "to": objective, "flow": step.flow_kind})
            self._last_objective = objective
        if b.alive != self._last_alive:
            self._record(step.tick, "alive", {"alive": b.alive, "self_xy": b.self_xy})
            self._last_alive = b.alive
        engaged = len(b.enemies) > 0
        if engaged != self._last_engaged:
            self._record(step.tick, "engage", {"engaged": engaged, "n_enemies": len(b.enemies)})
            self._last_engaged = engaged

    def _payload(self, step: StepInfo) -> dict:
        b = step.belief
        return {
            "team": b.team,
            "seat": b.seat,
            "role": b.role,
            "hold_point": b.hold_point,
            "alive": b.alive,
            "self_xy": b.self_xy,
            "aim_brads": b.aim_brads,
            "fire_ready": b.fire_ready,
            "n_enemies": len(b.enemies),
            "objective": step.intent.reason,
            "flow_kind": step.flow_kind,
            "i_carry": b.i_carry_enemy_flag,
            "enemy_flag_on_pedestal": b.enemy_flag_on_pedestal,
            "own_flag_stolen": b.own_flag_stolen,
            "sweep_offset": b.sweep_offset,
            "nav_stuck": b.nav_stuck_ticks,
            "held_mask": step.command.held_mask,
        }

    def _record(self, tick: int, name: str, data: dict) -> None:
        self._sink.record(TraceEvent(tick=tick, name=name, data=data))


__all__ = ["build_decide"]
