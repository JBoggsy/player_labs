"""Typed seam between wowborg policies and the Nim client's control socket (0.1.31+).

Policies see ONLY ``wowborg.types`` (``Observation``, intents, ``ActionOutcome``); they
never touch ``wow_sdk`` models, sockets, or processes. This module is the adapter half
of the swap seam: it drives ``vanilla_wow.nim_control.v1`` — the binary-framed local TCP
socket that replaced the 0.1.19 action.json file bridge (recon:
``docs/recon/player-contract-0131-2026-07-21.md``).

Control contract (verified against the deployed 0.1.31 image's wow_sdk):
- One ``GoalRequest(selection_mode="external")`` arms per-step control; the Nim
  controller then OFFERS immutable EnvironmentFrames (observation + dense one-based
  bindings + factorized action masks + a recommended action).
- The policy's only write is one mask-admitted ``FactorizedAction`` per offered frame,
  bound to that frame's ``frame_id``/``observed_tick``/``revision`` (single-use,
  stale-safe).
- Settlements arrive as typed ``ActionSettled`` records (also mirrored to the read-only
  ``action-results.jsonl``); "sent is not accepted" maps to: selection accepted ≠ done —
  wait for the settlement of that frame's action.
"""

from __future__ import annotations

import time
from pathlib import Path

from pydantic import ValidationError

from wow_sdk.nim_control import (
    ActionSelectionRequest,
    ControlStatus,
    EnvironmentFrame,
    FactorizedAction,
    GoalRequest,
    NimControlClient,
    NimControlError,
    WorldPoint,
)

from wowborg.trace import NullTracer, Tracer
from wowborg.types import ActionOutcome, Observation, PlannedRoute, Position

# Replay-visible breadcrumbs cost real game actions; keep them sparse.
SAY_MIN_INTERVAL_SECONDS = 5.0
FRAME_POLL_SECONDS = 0.25
GOAL_ID = "wowborg"

# nim_control wire framing (mirrors the pinned SDK's private constants; used only by
# the lenient-frame fallback below).
_FRAME_STATUS_REQUEST = 4
_FRAME_ENVIRONMENT_FRAME = 6


class _LenientLocation:
    def __init__(self, data: dict) -> None:
        self.map_id = int(data.get("map_id", 0))
        self.x = float(data.get("x", 0.0))
        self.y = float(data.get("y", 0.0))
        self.z = float(data.get("z", 0.0))
        self.orientation = float(data.get("orientation", 0.0))


class _LenientObservation:
    def __init__(self, data: dict) -> None:
        self.tick = int(data.get("tick", 0))
        self.location = _LenientLocation(data.get("location", {}))
        self.health = int(data.get("health", 0))
        self.max_health = int(data.get("max_health", 0)) or 1
        self.in_combat = bool(data.get("in_combat", False))
        self.is_dead = bool(data.get("is_dead", False))
        self.is_ghost = bool(data.get("is_ghost", False))


class _LenientBindings:
    def __init__(self, data: dict) -> None:
        class Row:
            def __init__(self, r):
                self.index = r.get("index", 0)
                self.trigger_id = r.get("trigger_id", 0)
                self.spell_id = r.get("spell_id", 0)
                self.value = r.get("value", "")

        self.triggers = [Row(r) for r in data.get("triggers", [])]
        self.texts = [Row(r) for r in data.get("texts", [])]
        self.spells = [Row(r) for r in data.get("spells", [])]
        self.entities = data.get("entities", [])


class LenientFrame:
    """A validation-tolerant EnvironmentFrame stand-in (v24: the live controller
    emits frames whose recommended_action violates its own mask in LONG storms —
    strict parsing rejects the whole frame and navigation goes blind AND mute).
    Carries what selection + supervision need; the SERVER remains the validator —
    an inadmissible selection settles as a typed control error, which we handle."""

    is_lenient = True
    recommended_action = None  # never trust the recommendation on an invalid frame

    def __init__(self, payload: dict) -> None:
        self.revision = int(payload.get("revision", 0))
        self.frame_id = int(payload.get("frame_id", 0))
        self.phase = payload.get("phase", "")
        self.observed_tick = int(payload.get("observed_tick", 0))
        self.action_ready = bool(payload.get("action_ready", False))
        self.observation = _LenientObservation(payload.get("observation", {}))
        self.bindings = _LenientBindings(payload.get("bindings", {}))
        self.slot = int(payload.get("slot", 0))

    def allows_action(self, action) -> bool:  # noqa: ARG002 — server validates
        return True


class ShimBridge:
    """Drives one Nim control socket: observe frames, select actions, await settlement."""

    def __init__(
        self,
        runtime_dir: Path | str,  # kept for evidence-surface symmetry (trace/artifact)
        tracer: Tracer | None = None,
        *,
        slot: int = 0,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        self._runtime_dir = Path(runtime_dir)
        self._tracer = tracer or NullTracer()
        self._client = NimControlClient(host=host, port=port, slot=slot)
        self._slot = slot
        self._last_say = 0.0
        self._last_traced_tick: int | None = None
        self._goal_armed = False
        self._state_reader = None

    # ---- lifecycle -----------------------------------------------------------

    def connect(self, *, timeout_s: float = 120.0) -> bool:
        """Connect to the control socket, retrying until the Nim client serves it."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                self._client.connect()
                status = self._client.status()
                self._tracer.emit(
                    "control_connected", phase=status.phase, revision=status.revision
                )
                return True
            except (OSError, NimControlError):
                self._client.close()
                time.sleep(1.0)
        return False

    def arm_external_control(
        self, *, goal_kind: str = "leveling", deadline_unix_seconds: float = 0.0
    ) -> bool:
        """Submit the goal that switches the controller to external per-step selection.

        The Nim planner still PLANS (it paces frames and supplies recommended_action);
        external mode means WE choose which admitted action executes each frame.
        """
        status = self._client.status()
        request = GoalRequest(
            goal_id=GOAL_ID,
            goal_kind=goal_kind,
            deadline_unix_seconds=deadline_unix_seconds,
            expected_slot=self._slot,
            expected_revision=status.revision,
            selection_mode="external",
        )
        try:
            accepted = self._client.submit_goal(request)
        except (OSError, NimControlError) as exc:
            self._tracer.emit("goal_rejected", error=str(exc))
            return False
        self._goal_armed = True
        self._tracer.emit(
            "goal_armed",
            goal_kind=goal_kind,
            revision=accepted.revision,
            phase=accepted.phase,
        )
        return True

    def close(self) -> None:
        self._client.close()

    def _reconnect(self) -> None:
        """Drop and re-dial the control socket after any socket-level error.

        socket.timeout is an OSError, NOT a NimControlError — v9 hosted evidence: one
        5s read timeout escaped the old except clauses and ended a 970s session at
        158s. The Nim server accepts fresh connections; state lives server-side."""
        try:
            self._client.close()
        except OSError:
            pass

    # ---- observations ----------------------------------------------------------

    def wait_for_frame(self, *, timeout_s: float = 60.0) -> EnvironmentFrame | None:
        """Block until the controller offers a decision frame (action_ready)."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                result = self._client.status(include_environment_frame=True)
            except ValidationError as exc:
                # Upstream contract violation (e.g. recommended action fails its own
                # mask). Fall back to a LENIENT parse so navigation can still SELECT;
                # the server stays the validator.
                self._tracer.emit("frame_invalid", error=str(exc)[:120])
                lenient = self._lenient_frame()
                if lenient is not None and lenient.action_ready:
                    self._trace_frame(lenient)
                    return lenient
                time.sleep(FRAME_POLL_SECONDS)
                continue
            except (OSError, NimControlError) as exc:
                self._tracer.emit("status_error", error=str(exc))
                self._reconnect()
                time.sleep(FRAME_POLL_SECONDS)
                continue
            if isinstance(result, EnvironmentFrame) and result.action_ready:
                self._trace_frame(result)
                return result
            time.sleep(FRAME_POLL_SECONDS)
        return None

    def observe(self) -> Observation | None:
        """Latest self-state, from the frame if offered, else the state.json mirror.

        The state.json fallback matters operationally: the 0.1.31 controller emits
        VALIDATION-INVALID frames in long storms (recommended-action-vs-mask upstream
        bug, v24 evidence: 588-1044 invalid frames/episode) — during a storm the
        socket is blind but the Nim client still writes its TelemetrySnapshot every
        0.5s, which is all navigation supervision needs.
        """
        try:
            result = self._client.status(include_environment_frame=True)
        except ValidationError as exc:
            self._tracer.emit("frame_invalid", error=str(exc)[:120])
            return self._observe_from_state_file()
        except (OSError, NimControlError):
            self._reconnect()
            return self._observe_from_state_file()
        if not isinstance(result, EnvironmentFrame):
            return self._observe_from_state_file()
        self._trace_frame(result)
        return self._observation(result)

    def _lenient_frame(self) -> "LenientFrame | None":
        """Raw-JSON status request over the client's wire framing (bypasses pydantic).
        Uses the pinned SDK's private framing helpers — acceptable coupling: the
        snapshot is digest-pinned and the bump recipe re-validates."""
        import json as _json

        try:
            request_id = self._client._next_request_id()
            # The Nim server REQUIRES all five status_request fields present
            # (requireControlBool raises on a missing key) — v25 hosted evidence:
            # omitting include_action_settled turned every lenient request into a
            # CONTROL_ERROR and the fallback silently never fired.
            body = _json.dumps({
                "protocol": "vanilla_wow.nim_control.v1",
                "type": "status_request",
                "expected_slot": self._slot,
                "include_environment_frame": True,
                "include_action_settled": False,
            }).encode()
            self._client._send_frame(_FRAME_STATUS_REQUEST, request_id, body)
            frame_type, rid, payload = self._client._recv_frame()
            if frame_type != _FRAME_ENVIRONMENT_FRAME or rid != request_id:
                self._tracer.emit(
                    "lenient_frame_rejected", frame_type=frame_type, request_id=rid
                )
                return None
            return LenientFrame(_json.loads(payload))
        except Exception:  # noqa: BLE001 — lenient path never raises
            try:
                self._reconnect()
            except Exception:  # noqa: BLE001
                pass
            return None

    def _observe_from_state_file(self) -> Observation | None:
        try:
            from wow_sdk.runtime import EmbeddedClientRuntimeClient

            if self._state_reader is None:
                self._state_reader = EmbeddedClientRuntimeClient(self._runtime_dir)
            snapshot = self._state_reader.read_snapshot()
        except Exception:  # noqa: BLE001 — fallback must never raise
            return None
        if snapshot is None:
            return None
        character = snapshot.character
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

    # ---- intents ----------------------------------------------------------------

    def select_move_to(
        self,
        frame: EnvironmentFrame,
        x: float,
        y: float,
        z: float,
        map_id: int,
    ) -> str | None:
        """Select a move-to-destination action on an offered frame.

        Returns a synthetic request id (frame-bound) or None if the mask refuses the
        action — the caller should then pick differently (e.g. accept the recommended
        action or wait for the next frame).
        """
        action = FactorizedAction(
            kind="move",
            destination=WorldPoint(map_id=map_id, x=x, y=y, z=z),
        )
        return self._select(frame, action, label="move_to")

    def select_action(self, frame: EnvironmentFrame, action: FactorizedAction) -> str | None:
        """Select an arbitrary factorized action (T1+ policies compose these)."""
        return self._select(frame, action, label=action.kind)

    def select_recommended(self, frame: EnvironmentFrame) -> str | None:
        """Accept the Nim planner's recommendation for this frame."""
        if frame.recommended_action is None:
            return None
        return self._select(frame, frame.recommended_action, label="recommended")

    def select_kind(self, frame: EnvironmentFrame, kind: str) -> str | None:
        """Select a bare factorized action by kind (release_spirit, reclaim_corpse…).

        Recovery must not depend on recommended_action: lenient frames null it
        (codex audit #9 — death recovery went inert during validation storms).
        The mask/server still validates admissibility.
        """
        return self._select(frame, FactorizedAction(kind=kind), label=kind)

    STUCK_SPELL_ID = 7355  # the stock "Stuck" auto-unstuck spell — the game repo's
    # sanctioned recovery for "no physically admissible local source projection"
    # (docs/navigation-collision-issues.md): a targetless cast that relocates the
    # client to a safe pose. No coordinate assignment or collision bypass.

    def select_stuck(self, frame: EnvironmentFrame) -> str | None:
        """Cast Stuck (7355) if this frame's spell bindings offer it."""
        index = None
        for row in getattr(frame.bindings, "spells", []) or []:
            if getattr(row, "spell_id", None) == self.STUCK_SPELL_ID:
                index = row.index
                break
        if index is None:
            return None
        action = FactorizedAction(kind="cast", spell=index)
        return self._select(frame, action, label="stuck")

    # ---- route planning -------------------------------------------------------------

    def plan_route(
        self,
        source: Position,
        target: Position,
        map_id: int,
        *,
        arrival_radius: float = 3.0,
        tile_load_mode: str = "auto",
    ) -> PlannedRoute:
        """Plan a Detour route via the game host's /player/navigation service.

        Uses wow_sdk.navmesh.route_navmesh, which POSTs to
        $VANILLA_WOW_NAVMESH_SERVICE_URL when set (the hosted path; the wrapper
        exports it) and falls back to a local helper otherwise. Never raises —
        service failure returns status="unavailable" and L1 degrades to
        executor-only movement.

        ``tile_load_mode``: "auto" loads corridor tiles and — helper source fact
        (vmangos_navmesh_helper.cpp): when the corridor is partial_poly it returns
        the PARTIAL without retrying — so long hauls plan ~60yd at a time. "all"
        loads every map tile for a definitive full route / genuine no_path.
        """
        try:
            from wow_sdk.navmesh import WorldPoint as NavPoint, route_navmesh

            route = route_navmesh(
                NavPoint(map_id=map_id, x=source.x, y=source.y, z=source.z),
                NavPoint(map_id=map_id, x=target.x, y=target.y, z=target.z),
                arrival_radius=arrival_radius,
                tile_load_mode=tile_load_mode,
            )
        except Exception as exc:  # noqa: BLE001 — planning must never kill navigation
            self._tracer.emit("route_plan_error", error=repr(exc))
            return PlannedRoute(
                status="error", map_id=map_id, waypoints=[], route_distance=0.0,
                partial=False, projected_target_distance=None, jump_required=False,
                message=repr(exc),
            )
        waypoints = [
            Position(w.x, w.y, w.z, 0.0) for w in (route.waypoints or [])
        ]
        partial = bool(route.partial_path_end) or route.path_type == "partial"
        planned = PlannedRoute(
            status=route.status,
            map_id=route.map_id,
            waypoints=waypoints,
            route_distance=float(route.route_distance or 0.0),
            partial=partial,
            projected_target_distance=route.projected_target_distance,
            jump_required=bool(route.jump_required),
            message=route.message or "",
        )
        self._tracer.emit(
            "route_planned",
            status=planned.status,
            waypoints=len(planned.waypoints),
            route_distance=round(planned.route_distance, 1),
            partial=planned.partial,
            projected_target_distance=planned.projected_target_distance,
            jump_required=planned.jump_required,
            # The helper's own reason (e.g. "no mmap corridor tiles could be
            # loaded") — v25 evidence: bare no_path/0-waypoint responses from a
            # live on-mesh position were undiagnosable without it.
            message=planned.message[:160] if planned.message else None,
        )
        return planned

    # ---- results ------------------------------------------------------------------

    def wait_for_settlement(
        self, frame_id: int, *, timeout_s: float = 90.0
    ) -> ActionOutcome | None:
        """Block until the action selected on ``frame_id`` settles; None on timeout.

        "Sent is not accepted": a timeout is failure, never success.
        """
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                settled = self._client.last_settlement()
            except (OSError, NimControlError):
                self._reconnect()
                settled = None
            if settled is not None and settled.frame_id >= frame_id:
                superseded = settled.frame_id > frame_id
                if superseded:
                    # A newer settlement superseded the awaited one. Its result
                    # belongs to a DIFFERENT action — never report its success as
                    # the awaited action's (codex audit #13: misattribution).
                    self._tracer.emit(
                        "settlement_superseded",
                        awaited_frame=frame_id,
                        settled_frame=settled.frame_id,
                    )
                outcome = ActionOutcome(
                    request_id=f"frame-{settled.frame_id}",
                    kind=settled.action_kind or settled.action.kind,
                    success=settled.success and not superseded,
                    settlement_kind=None,  # granular kinds live in action-results.jsonl
                    displacement_yards=None,
                    end_position=None,
                    detail=settled.message,
                    frame_id=settled.frame_id,
                    settled_tick=settled.settled_tick,
                )
                self._tracer.emit(
                    "outcome",
                    frame_id=settled.frame_id,
                    action_kind=outcome.kind,
                    success=outcome.success,
                    settled_tick=settled.settled_tick,
                    detail=outcome.detail,
                )
                return outcome
            time.sleep(FRAME_POLL_SECONDS)
        self._tracer.emit("outcome", frame_id=frame_id, timeout=True, waited_s=timeout_s)
        return None

    # ---- breadcrumbs ----------------------------------------------------------------

    def say(self, text: str) -> str | None:
        """Best-effort replay-visible /say breadcrumb.

        0.1.31 constraint: the ``text`` factor indexes the frame's ADMITTED vocabulary
        (bounded ``PolicyText`` rows) — arbitrary strings are only expressible if the
        frame admits them. We look for our text among the current frame's bindings and
        select a chat_say when possible; otherwise we trace-and-skip. Chat is a bonus
        channel now, never load-bearing (trace + artifact bundle carry the evidence).
        """
        now = time.monotonic()
        if now - self._last_say < SAY_MIN_INTERVAL_SECONDS:
            return None
        self._last_say = now
        self._tracer.emit("say", text=text)
        try:
            result = self._client.status(include_environment_frame=True)
        except ValidationError:
            return None
        except (OSError, NimControlError):
            self._reconnect()
            return None
        if not isinstance(result, EnvironmentFrame) or not result.action_ready:
            return None
        index = next(
            (row.index for row in result.bindings.texts if row.value == text), None
        )
        if index is None:
            self._tracer.emit("say_not_admitted", text=text)
            return None
        action = FactorizedAction(kind="chat_say", text=index)
        return self._select(result, action, label="chat_say")

    # ---- internals --------------------------------------------------------------------

    def _select(
        self, frame: EnvironmentFrame, action: FactorizedAction, *, label: str
    ) -> str | None:
        if not frame.allows_action(action):
            self._tracer.emit(
                "selection_refused_by_mask",
                label=label,
                action_kind=action.kind,
                frame_id=frame.frame_id,
            )
            return None
        request = ActionSelectionRequest(
            action=action,
            frame_id=frame.frame_id,
            observed_tick=frame.observed_tick,
            expected_slot=self._slot,
            expected_revision=frame.revision,
        )
        try:
            self._client.select(request)
        except OSError as exc:
            self._reconnect()
            self._tracer.emit(
                "selection_rejected",
                label=label,
                action_kind=action.kind,
                frame_id=frame.frame_id,
                error=f"socket: {exc!r}",
            )
            return None
        except NimControlError as exc:
            self._tracer.emit(
                "selection_rejected",
                label=label,
                action_kind=action.kind,
                frame_id=frame.frame_id,
                error=str(exc),
            )
            return None
        self._tracer.emit(
            "intent",
            request_id=f"frame-{frame.frame_id}",
            action_kind=action.kind,
            label=label,
            frame_id=frame.frame_id,
            destination=(
                [action.destination.x, action.destination.y, action.destination.z]
                if action.destination
                else None
            ),
            target=action.target or None,
        )
        return f"frame-{frame.frame_id}"

    def _observation(self, frame: EnvironmentFrame) -> Observation:
        obs = frame.observation
        return Observation(
            tick=obs.tick,
            captured_at=time.time(),
            map_id=obs.location.map_id,
            zone="",  # AreaTable localization exists in richer frames; T0 doesn't need it
            position=Position(
                obs.location.x, obs.location.y, obs.location.z, obs.location.orientation
            ),
            health=obs.health,
            max_health=obs.max_health,
            in_combat=obs.in_combat,
            is_dead=obs.is_dead,
            is_ghost=obs.is_ghost,
        )

    def _trace_frame(self, frame: EnvironmentFrame) -> None:
        if frame.observed_tick == self._last_traced_tick:
            return
        self._last_traced_tick = frame.observed_tick
        obs = frame.observation
        self._tracer.emit(
            "observation",
            tick=obs.tick,
            frame_id=frame.frame_id,
            phase=frame.phase,
            map_id=obs.location.map_id,
            position=[obs.location.x, obs.location.y, obs.location.z, obs.location.orientation],
            health=obs.health,
            max_health=obs.max_health,
            in_combat=obs.in_combat,
            is_dead=obs.is_dead,
            is_ghost=obs.is_ghost,
            action_ready=frame.action_ready,
            n_entities=len(frame.bindings.entities),
            recommended=frame.recommended_action.kind if frame.recommended_action else None,
        )
