"""Read-only Coworld ``/player`` progress reporting for the ``/env`` policy."""

from __future__ import annotations

from collections import Counter
import json
import math
import time

from environment.contract.agent import AgentFrame
from websockets.sync.client import ClientConnection, connect

from wowborg.trace import Tracer

SESSION_PROTOCOL = "vanilla_wow.session.v1"
SESSION_EXTENSIONS = (
    "party_role%2Crfc_party%2Cnavigation%2Csimulation_time_scale"
)
PING_INTERVAL_SECONDS = 5.0
PROGRESS_INTERVAL_SECONDS = 1.0
TEARDOWN_MARGIN_SECONDS = 35.0

XP_TO_NEXT_LEVEL = (
    400,
    900,
    1400,
    2100,
    2800,
    3600,
    4500,
    5400,
    6500,
    7600,
    8800,
    10100,
    11400,
    12900,
    14400,
    16000,
    17700,
    19400,
    21300,
    23200,
    25200,
    27300,
    29400,
    31700,
    34000,
    36400,
    38900,
    41400,
    44300,
    47400,
    50800,
    54500,
    58600,
    62800,
    67100,
    71600,
    76100,
    80800,
    85700,
    90700,
    95800,
    101000,
    106300,
    111800,
    117500,
    123200,
    129100,
    135100,
    141200,
    147500,
    153900,
    160400,
    167100,
    173900,
    180800,
    187900,
    195000,
    202300,
    209800,
)


def _cumulative_xp(level: int, xp: int) -> int:
    bounded_level = max(1, min(level, len(XP_TO_NEXT_LEVEL) + 1))
    return max(0, xp) + sum(XP_TO_NEXT_LEVEL[: bounded_level - 1])


class PlayerProgressReporter:
    """Project observed AgentFrames onto the owner-supported progress channel."""

    def __init__(self, player_ws_url: str, tracer: Tracer) -> None:
        self._url = player_ws_url
        self._tracer = tracer
        self._socket: ClientConnection | None = None
        self._slot: int | None = None
        self._deadline_seconds: float | None = None
        self._started_at = 0.0
        self._last_sample_at = 0.0
        self._last_progress_at = 0.0
        self._last_ping_at = 0.0
        self._start_level = 1
        self._start_xp = 0
        self._last_level = 1
        self._last_xp = 0
        self._last_position: tuple[float, float] | None = None
        self._displacement = 0.0
        self._frame_samples = 0
        self._combat_seconds = 0.0
        self._dead_seconds = 0.0
        self._death_transitions = 0
        self._prior_dead = False
        self._sequence = 0
        self._action_kind_samples: Counter[str] = Counter()
        self._settled_successes: Counter[str] = Counter()
        self._settled_failures: Counter[str] = Counter()
        self._last_action_id = 0
        self._last_settled_action_id = 0

    def connect(self) -> None:
        """Open the observer socket and consume its typed session handoff."""

        separator = "&" if "?" in self._url else "?"
        observer_url = (
            f"{self._url}{separator}session_extensions={SESSION_EXTENSIONS}"
        )
        socket: ClientConnection | None = None
        try:
            socket = connect(
                observer_url,
                open_timeout=30,
                ping_interval=None,
            )
            raw = socket.recv(timeout=30)
            message = json.loads(raw)
            if (
                message.get("protocol") != SESSION_PROTOCOL
                or message.get("type") != "wow_session"
            ):
                raise ValueError("Coworld /player did not send a wow_session handoff")
            self._slot = int(message["slot"])
            self._deadline_seconds = float(message["deadline_seconds"])
            self._socket = socket
            self._tracer.emit(
                "player_session_connected",
                protocol=SESSION_PROTOCOL,
                slot=self._slot,
                character_name=message.get("character_name"),
                deadline_seconds=self._deadline_seconds,
            )
        except Exception as exc:
            self._close_socket(socket)
            self._socket = None
            self._tracer.emit("player_session_error", phase="connect", error=repr(exc))

    def policy_duration(self, requested_seconds: float) -> float:
        """Leave the owner-standard margin for ``done`` and replay finalization."""

        if self._deadline_seconds is None:
            return requested_seconds
        return min(
            requested_seconds,
            max(1.0, self._deadline_seconds - TEARDOWN_MARGIN_SECONDS),
        )

    def observe(self, frame: AgentFrame) -> None:
        """Sample one canonical frame and report it at the supported cadence."""

        if self._socket is None or self._slot is None:
            return
        now = time.monotonic()
        if self._started_at == 0:
            self._started_at = now
            self._last_sample_at = now
            self._start_level = frame.level
            self._start_xp = frame.xp

        elapsed = max(0.0, now - self._last_sample_at)
        dead = frame.is_dead or frame.is_ghost
        if frame.in_combat:
            self._combat_seconds += elapsed
        if dead:
            self._dead_seconds += elapsed
        if dead and not self._prior_dead:
            self._death_transitions += 1
        self._prior_dead = dead

        position = (frame.location.x, frame.location.y)
        if self._last_position is not None:
            self._displacement += math.dist(self._last_position, position)
        self._last_position = position
        self._last_level = frame.level
        self._last_xp = frame.xp
        self._last_sample_at = now
        self._frame_samples += 1
        self._observe_action(frame)

        try:
            if self._drain_control_messages():
                return
            if now - self._last_ping_at >= PING_INTERVAL_SECONDS:
                self._send(
                    {
                        "protocol": SESSION_PROTOCOL,
                        "type": "ping",
                        "slot": self._slot,
                    }
                )
                self._last_ping_at = now
            if now - self._last_progress_at >= PROGRESS_INTERVAL_SECONDS:
                self._sequence += 1
                self._send(self._progress_payload(frame, now))
                self._last_progress_at = now
                self._tracer.emit(
                    "player_progress",
                    sequence=self._sequence,
                    frame_id=frame.frame_id,
                    displacement_yards=round(self._displacement, 3),
                )
        except Exception as exc:
            self._disable("observe", exc)

    def close(self, *, success: bool, detail: str) -> None:
        """Finish the observer session without affecting policy ownership."""

        if self._socket is None or self._slot is None:
            return
        try:
            self._send(
                {
                    "protocol": SESSION_PROTOCOL,
                    "type": "done",
                    "slot": self._slot,
                    "success": success,
                    "detail": detail,
                }
            )
            self._tracer.emit(
                "player_session_done",
                success=success,
                detail=detail,
                progress_reports=self._sequence,
            )
        except Exception as exc:
            self._tracer.emit("player_session_error", phase="close", error=repr(exc))
        finally:
            self._close_socket(self._socket)
            self._socket = None

    def _observe_action(self, frame: AgentFrame) -> None:
        action_state = frame.action_state
        if action_state is None:
            return
        action_id = action_state.action_id
        action_kind = action_state.action.kind
        if action_id > self._last_action_id:
            self._action_kind_samples[action_kind] += 1
            self._last_action_id = action_id
        if (
            action_id > self._last_settled_action_id
            and action_state.status
            in {"succeeded", "failed", "timed_out", "cancelled", "rejected"}
        ):
            target = (
                self._settled_successes
                if action_state.status == "succeeded"
                else self._settled_failures
            )
            target[action_kind] += 1
            self._last_settled_action_id = action_id

    def _progress_payload(self, frame: AgentFrame, now: float) -> dict[str, object]:
        elapsed = max(0.0, now - self._started_at)
        gained = max(
            0,
            _cumulative_xp(self._last_level, self._last_xp)
            - _cumulative_xp(self._start_level, self._start_xp),
        )
        return {
            "protocol": SESSION_PROTOCOL,
            "type": "progress",
            "slot": self._slot,
            "sequence": self._sequence,
            "observed_wall_clock_ms": int(time.time() * 1000),
            "report": {
                "protocol": "vanilla_wow.leveling_performance.v1",
                "elapsed_seconds": elapsed,
                "frame_samples": self._frame_samples,
                "frame_misses": 0,
                "frame_miss_fraction": 0.0,
                "start_level": self._start_level,
                "start_xp": self._start_xp,
                "level": self._last_level,
                "xp": self._last_xp,
                "next_level_xp": frame.next_level_xp,
                "observed_xp_gained": gained,
                "observed_xp_per_hour": (
                    gained * 3600.0 / elapsed if elapsed > 0 else 0.0
                ),
                "observed_displacement_yards": self._displacement,
                "death_transitions": self._death_transitions,
                "combat_sample_fraction": (
                    min(1.0, self._combat_seconds / elapsed)
                    if elapsed > 0
                    else 0.0
                ),
                "dead_or_ghost_sample_fraction": (
                    min(1.0, self._dead_seconds / elapsed)
                    if elapsed > 0
                    else 0.0
                ),
                "route_nodes_observed": 0,
                "quest_rewards_observed": 0,
                "spells_learned_observed": 0,
                "action_kind_samples": dict(self._action_kind_samples),
                "settled_action_successes": dict(self._settled_successes),
                "settled_action_failures": dict(self._settled_failures),
                "context_windows": [],
            },
        }

    def _send(self, payload: dict[str, object]) -> None:
        assert self._socket is not None
        self._socket.send(json.dumps(payload, separators=(",", ":")))

    def _drain_control_messages(self) -> bool:
        assert self._socket is not None
        while True:
            try:
                raw = self._socket.recv(timeout=0)
            except TimeoutError:
                return False
            message = json.loads(raw)
            if message.get("type") == "final":
                self._tracer.emit(
                    "player_session_final",
                    success=message.get("success"),
                    detail=message.get("detail"),
                )
                self._close_socket(self._socket)
                self._socket = None
                return True

    def _disable(self, phase: str, exc: Exception) -> None:
        self._tracer.emit("player_session_error", phase=phase, error=repr(exc))
        self._close_socket(self._socket)
        self._socket = None

    @staticmethod
    def _close_socket(socket: ClientConnection | None) -> None:
        if socket is None:
            return
        try:
            socket.close()
        except Exception:
            pass
