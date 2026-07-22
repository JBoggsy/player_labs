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

import numpy as np

from ctf.beacon.config import DANGER_TRACE_DOWNSAMPLE, DIAG_EVERY_TICKS, NAV_CELL
from ctf.beacon.runtime import BeaconRuntime, StepInfo
from ctf.beacon.types import PlayerTrack, Team
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
        self._last_micro: str | None = None
        # Cumulative activation tick-counts per micro mode ("duck"/"peek"), carried in
        # every snapshot. Behavior-change discipline: any new gated behavior must be
        # countable from the trace, so a null A/B can distinguish "never fired" from
        # "fired and didn't help".
        self._micro_ticks: dict[str, int] = {}
        # v10 activation counters (lead aim + items), carried in every snapshot.
        self._lead_shots = 0  # A-press ticks with a nonzero lead applied
        self._unled_shots = 0  # A-press ticks with zero lead (gun fights only)
        self._lead_brads_sum = 0  # total |lead| across led shots
        self._throws = 0  # grenade releases (charge -> 0 while holding one)
        self._last_charging = False
        self._last_items: tuple[bool, bool, bool] | None = None  # grenade/shield/arc
        self._last_hp: int | None = None

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
        if b.micro is not None:
            self._micro_ticks[b.micro] = self._micro_ticks.get(b.micro, 0) + 1
        if b.micro != self._last_micro:
            self._record(step.tick, "micro",
                         {"from": self._last_micro, "to": b.micro, "self_xy": b.self_xy,
                          "fire_ready": b.fire_ready})
            self._last_micro = b.micro

        # v10 lead-aim counters: count each fired shot as led / unled.
        if step.command.held_mask & 32:  # Button.A pressed this tick
            if b.lead_brads != 0:
                self._lead_shots += 1
                self._lead_brads_sum += abs(b.lead_brads)
            else:
                self._unled_shots += 1

        # v10 item transitions: pickups/losses of carried items, heals, throws.
        items_now = (b.i_have_grenade, b.i_have_shield, b.i_have_arc)
        if self._last_items is not None and items_now != self._last_items:
            for name, was, now in zip(
                ("grenade", "shield", "arc"), self._last_items, items_now
            ):
                if now != was:
                    self._record(step.tick, "item",
                                 {"kind": name, "have": now, "self_xy": b.self_xy})
        self._last_items = items_now
        charging = b.throw_charge_ticks > 0
        if self._last_charging and not charging and b.i_have_grenade:
            self._throws += 1
            self._record(step.tick, "throw", {"self_xy": b.self_xy})
        self._last_charging = charging
        if (
            b.hp_pips is not None
            and self._last_hp is not None
            and b.hp_pips > self._last_hp
            and step.intent.reason == "fetch_medkit"
        ):
            self._record(step.tick, "heal", {"hp": b.hp_pips, "self_xy": b.self_xy})
        self._last_hp = b.hp_pips

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
            "micro": b.micro,
            "micro_ticks": dict(self._micro_ticks),
            # v10 skill activation (cumulative): lead-aim shot split + item counters.
            "lead_shots": self._lead_shots,
            "unled_shots": self._unled_shots,
            "lead_brads_sum": self._lead_brads_sum,
            "throws": self._throws,
            "hp_pips": b.hp_pips,
            "have_grenade": b.i_have_grenade,
            "have_shield": b.i_have_shield,
            "have_arc": b.i_have_arc,
            "items_present": sum(1 for s in b.item_spawns if s.present),
            "enemy_tracks": [_track_row(t, step.tick) for t in b.enemy_tracks],
            "teammate_tracks": [_track_row(t, step.tick) for t in b.teammate_tracks],
            "danger": _danger_grid(b.danger),
        }

    def _record(self, tick: int, name: str, data: dict) -> None:
        self._sink.record(TraceEvent(tick=tick, name=name, data=data))


def _track_row(t: PlayerTrack, tick: int) -> dict:
    """One track as a compact JSON-safe row (age instead of an absolute tick)."""
    return {
        "pos": list(t.pos),
        "age": tick - t.last_tick,  # 0 = seen this tick
        "facing": t.facing,
        "vel": [round(t.vel[0], 2), round(t.vel[1], 2)] if t.vel is not None else None,
        "frames_seen": t.frames_seen,
    }


def _danger_grid(danger: np.ndarray | None) -> dict | None:
    """The danger field, block-max downsampled and quantized to 0..255 rows.

    Max (not mean) per block so a hot single cell survives the fold — for danger,
    the pessimistic read is the honest one. The full grid would be ~13k floats per
    snapshot; this is a ~38x20 grid of small ints (renderable as a heatmap).
    """
    if danger is None:
        return None
    ds = DANGER_TRACE_DOWNSAMPLE
    h, w = danger.shape
    th, tw = h // ds, w // ds
    blocks = danger[: th * ds, : tw * ds].reshape(th, ds, tw, ds).max(axis=(1, 3))
    quantized = (blocks * 255).astype(int)
    return {"cell_px": ds * NAV_CELL, "rows": quantized.tolist()}


__all__ = ["build_decide"]
