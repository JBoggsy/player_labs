"""Sprite-bridge ``decide`` adapter for beacon, plus the CTF_DIAG logger.

``build_decide(team)`` returns a stateful callback for ``run_sprite_bridge``: it holds
one BeaconRuntime and, when diagnostics are on (default; disable with CTF_DIAG=0),
emits ``CTF_DIAG`` lines to stderr — periodic full-state snapshots plus immediate
transition lines whenever the objective, alive-state, or combat status changes. That
is everything a post-mortem needs to reconstruct what beacon believed and why it acted.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable

from ctf.beacon.config import DIAG_EVERY_TICKS
from ctf.beacon.runtime import BeaconRuntime, StepInfo
from ctf.beacon.types import Team
from players.player_sdk import SpriteContext, SpriteWorld


def _diagnostics_enabled() -> bool:
    return os.getenv("CTF_DIAG", "1").strip().lower() not in {"0", "false", "off", "no"}


def build_decide(team: Team, seat: int = 0) -> Callable[[SpriteWorld, SpriteContext], int]:
    """Build a stateful bridge callback backed by one runtime instance."""
    diagnostics = _DiagnosticLogger() if _diagnostics_enabled() else None
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


class _DiagnosticLogger:
    """Periodic snapshots + transition lines, mirroring cady's CTF_DIAG approach."""

    def __init__(self) -> None:
        self._last_objective: str | None = None
        self._last_alive: bool | None = None
        self._last_engaged: bool | None = None

    def on_step(self, step: StepInfo) -> None:
        self._log_transitions(step)
        if step.tick % DIAG_EVERY_TICKS == 0 or (self._last_alive is None and step.belief.alive):
            self._emit("snapshot", self._payload(step))

    def _log_transitions(self, step: StepInfo) -> None:
        b = step.belief
        objective = step.intent.reason
        if objective != self._last_objective:
            self._emit("objective", {"tick": step.tick, "from": self._last_objective,
                                     "to": objective, "flow": step.flow_kind})
            self._last_objective = objective
        if b.alive != self._last_alive:
            self._emit("alive", {"tick": step.tick, "alive": b.alive, "self_xy": b.self_xy})
            self._last_alive = b.alive
        engaged = len(b.enemies) > 0
        if engaged != self._last_engaged:
            self._emit("engage", {"tick": step.tick, "engaged": engaged,
                                  "n_enemies": len(b.enemies)})
            self._last_engaged = engaged

    def _payload(self, step: StepInfo) -> dict:
        b = step.belief
        return {
            "tick": step.tick,
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

    def _emit(self, kind: str, payload: dict) -> None:
        print(f"CTF_DIAG {kind} " + json.dumps(payload, separators=(",", ":"), sort_keys=True),
              file=sys.stderr, flush=True)


__all__ = ["build_decide"]
