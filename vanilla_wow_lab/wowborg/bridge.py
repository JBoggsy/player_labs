"""Typed seam between wowborg policies and the Nim shim's file bridge.

Policies see ONLY the types defined here (``Observation``, ``ActionOutcome``); they never
touch ``wow_sdk`` models, runtime files, or processes. This module is the adapter half of
the swap seam: it imports ``wow_sdk`` (installed in the base image) and reduces its
``TelemetrySnapshot`` / ``ActionExecutionResult`` into the T0 slice of the observation and
action-result spaces designed in
``docs/designs/wowborg-observation-action-spaces.html`` (§3.1, §4.1, §4.9).

The file-bridge contract (verified against the game repo @ 312d1d0c7):
- ``state.json``   — one TelemetrySnapshot, atomically replaced by the Nim client.
- ``action.json``  — flat envelope ``{sequence>=1, request_id, kind, ...allowlisted args}``.
- ``action-results.jsonl`` — one ActionExecutionResult per line; move results always carry
  a typed ``movement_settlement`` (success ⇔ kind ∈ {reached_target, advanced_corridor,
  combat_interrupted}).
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from wow_sdk.runtime import EmbeddedClientRuntimeClient, atomic_write_json

from wowborg.trace import NullTracer, Tracer
from wowborg.types import ActionOutcome, Observation, Position

# Replay-visible breadcrumbs cost real game actions; keep them sparse.
SAY_MIN_INTERVAL_SECONDS = 5.0


class ShimBridge:
    """Drives one Nim-shim runtime dir: observe, emit intents, await typed results."""

    def __init__(self, runtime_dir: Path | str, tracer: Tracer | None = None) -> None:
        self._client = EmbeddedClientRuntimeClient(Path(runtime_dir))
        self._sequence = 0
        self._result_offset = 0
        self._tracer = tracer or NullTracer()
        self._last_say = 0.0
        self._last_traced_tick: int | None = None
        # Settled-but-unclaimed results: action.json is a single slot, so results can
        # arrive for requests other than the one currently being awaited.
        self._pending_results: list = []

    # ---- observations ------------------------------------------------------

    def observe(self) -> Observation | None:
        """Read the latest snapshot; None while the client has not written one."""
        snapshot = self._client.read_snapshot()
        if snapshot is None:
            return None
        character = snapshot.character
        if snapshot.tick != self._last_traced_tick:
            self._last_traced_tick = snapshot.tick
            self._tracer.emit(
                "observation",
                tick=snapshot.tick,
                map_id=character.map_id,
                zone=character.zone,
                position=[character.x, character.y, character.z, character.orientation],
                health=character.health,
                max_health=character.max_health,
                in_combat=character.in_combat,
                is_dead=bool(character.is_dead),
                is_ghost=bool(character.is_ghost),
            )
        return Observation(
            tick=snapshot.tick,
            captured_at=time.time(),
            map_id=character.map_id,
            zone=character.zone,
            position=Position(character.x, character.y, character.z, character.orientation),
            health=character.health,
            max_health=character.max_health,
            in_combat=character.in_combat,
            is_dead=bool(character.is_dead),
            is_ghost=bool(character.is_ghost),
        )

    # ---- intents -----------------------------------------------------------

    def move_to(
        self,
        x: float,
        y: float,
        z: float,
        map_id: int,
        *,
        arrival_radius: float = 3.0,
        trust_z: bool = False,
    ) -> str:
        """Queue a move intent; returns its request_id. ``trust_z=False`` lets the
        executor's Detour projection settle the destination height (the proven default
        for computed points)."""
        payload: dict[str, object] = {
            "destination": {"map_id": map_id, "x": x, "y": y, "z": z},
            "arrival_radius": arrival_radius,
        }
        if not trust_z:
            payload["target_z_known"] = False
        return self._queue("move", payload)

    def say(self, text: str) -> str | None:
        """Emit a replay-visible /say breadcrumb (CWREPLAY v4 records real chat packets —
        the ONLY channel that survives into replays when policy logs aren't retained).

        Rate-limited; returns the request_id, or None when suppressed. Because
        ``action.json`` is a single slot, we wait (briefly) for the chat action to
        settle so the caller's next intent can't overwrite it before the Nim client
        polls; a timeout is non-fatal — the breadcrumb is best-effort.
        """
        now = time.monotonic()
        if now - self._last_say < SAY_MIN_INTERVAL_SECONDS:
            return None
        self._last_say = now
        self._tracer.emit("say", text=text)
        request_id = self._queue("chat_say", {"text": text[:200]})
        self.wait_for_result(request_id, timeout_s=3.0)
        return request_id

    # ---- results -----------------------------------------------------------

    def wait_for_result(self, request_id: str, *, timeout_s: float = 90.0) -> ActionOutcome | None:
        """Block until the executor settles the given request; None on timeout.

        "Sent is not accepted": callers treat a timeout as failure, never as success.
        """
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            self._pending_results.extend(self._drain_results())
            match = next(
                (r for r in self._pending_results if r.request_id == request_id), None
            )
            if match is not None:
                self._pending_results.remove(match)
                outcome = self._outcome(match)
                self._tracer.emit(
                    "outcome",
                    request_id=outcome.request_id,
                    action_kind=outcome.kind,
                    success=outcome.success,
                    settlement_kind=outcome.settlement_kind,
                    displacement_yards=outcome.displacement_yards,
                    end_position=(
                        [outcome.end_position.x, outcome.end_position.y, outcome.end_position.z]
                        if outcome.end_position
                        else None
                    ),
                    detail=outcome.detail,
                )
                return outcome
            time.sleep(0.5)
        self._tracer.emit("outcome", request_id=request_id, timeout=True, waited_s=timeout_s)
        return None

    # ---- internals ---------------------------------------------------------

    def _queue(self, kind: str, args: dict[str, object]) -> str:
        self._sequence += 1
        request_id = f"wowborg-{self._sequence}-{uuid.uuid4().hex[:8]}"
        payload = {"sequence": self._sequence, "request_id": request_id, "kind": kind, **args}
        atomic_write_json(self._client.paths.action_file, payload)
        self._tracer.emit("intent", request_id=request_id, action_kind=kind, args=args)
        return request_id

    def _drain_results(self):
        results, self._result_offset = self._client.read_action_results(offset=self._result_offset)
        return results

    def _outcome(self, result) -> ActionOutcome:
        settlement = result.movement_settlement
        client_state = result.client_state
        end_position = None
        if client_state is not None and client_state.player_position is not None:
            p = client_state.player_position
            end_position = Position(p.x, p.y, p.z, p.orientation)
        return ActionOutcome(
            request_id=result.request_id,
            kind=result.kind,
            success=result.success,
            settlement_kind=settlement.kind if settlement is not None else None,
            displacement_yards=settlement.displacement_yards if settlement is not None else None,
            end_position=end_position,
            detail=result.message,
        )
