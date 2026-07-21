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
from wowborg.types import ActionOutcome, Observation, Position

# Replay-visible breadcrumbs cost real game actions; keep them sparse.
SAY_MIN_INTERVAL_SECONDS = 5.0
FRAME_POLL_SECONDS = 0.25
GOAL_ID = "wowborg"


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
        except NimControlError as exc:
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

    # ---- observations ----------------------------------------------------------

    def wait_for_frame(self, *, timeout_s: float = 60.0) -> EnvironmentFrame | None:
        """Block until the controller offers a decision frame (action_ready)."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                result = self._client.status(include_environment_frame=True)
            except NimControlError as exc:
                self._tracer.emit("status_error", error=str(exc))
                time.sleep(FRAME_POLL_SECONDS)
                continue
            if isinstance(result, EnvironmentFrame) and result.action_ready:
                self._trace_frame(result)
                return result
            time.sleep(FRAME_POLL_SECONDS)
        return None

    def observe(self) -> Observation | None:
        """Latest self-state, from the frame if offered, else ControlStatus-only ticks.

        Policies that just need pose/vitals can call this anytime; per-step control
        should use wait_for_frame() to get bindings + masks with the same data.
        """
        try:
            result = self._client.status(include_environment_frame=True)
        except NimControlError:
            return None
        if not isinstance(result, EnvironmentFrame):
            return None
        self._trace_frame(result)
        return self._observation(result)

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
            except NimControlError:
                settled = None
            if settled is not None and settled.frame_id >= frame_id:
                outcome = ActionOutcome(
                    request_id=f"frame-{settled.frame_id}",
                    kind=settled.action_kind or settled.action.kind,
                    success=settled.success,
                    settlement_kind=None,  # granular kinds live in action-results.jsonl
                    displacement_yards=None,
                    end_position=None,
                    detail=settled.message,
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
        except NimControlError:
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
