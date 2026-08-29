"""Wowborg's policy runtime over the canonical Gymnasium ``WS /player`` interface.

The game owns the client, observation projection, action admission, execution,
settlement, reconnects, and transport.  This module only adds policy conveniences:
current-frame bookkeeping, structured traces, and the read-only navmesh query.
"""

from __future__ import annotations

import os
import struct
import time
from collections.abc import Callable
from typing import Literal
from urllib.parse import parse_qs, urlsplit, urlunsplit

from environment import VanillaWowEnv
from environment.contract.policy import (
    Action as AgentAction,
    Observation as AgentFrame,
    SpellObservation,
    WorldPoint,
)
from environment.control import EnvironmentRequestError
from environment.control import EnvironmentWebSocketClient
from environment.runtime.episode import (
    EnvironmentTransition,
    HostedSessionRuntime,
)
from player.sdk.navmesh.client import local_navmesh_graph, route_navmesh

from wowborg.nav.world_model import Point
from wowborg.trace import NullTracer, Tracer
from wowborg.types import ActionOutcome, PlannedRoute, Position

PLAYER_WS_URL_ENV = "COWORLD_PLAYER_WS_URL"
NAVMESH_SERVICE_URL_ENV = "VANILLA_WOW_NAVMESH_SERVICE_URL"
STUCK_SPELL_ID = 7355
STALE_FRAME_REJECTIONS = (
    "submission does not match the current Observation",
    "no Observation is awaiting an action",
    "action submission arrived after the game-wide deadline",
)


def _wire_float(value: float) -> float:
    """Round a Python float to the Nim contract's IEEE-754 float32 value."""

    return struct.unpack("f", struct.pack("f", value))[0]


def _accept_host_spell_intents() -> None:
    """Match the host's open spell-intent vocabulary at the wire boundary."""
    intent_names = SpellObservation.model_fields["intent_names"]
    intent_names.annotation = list[str]
    SpellObservation.model_rebuild(force=True)
    AgentFrame.model_rebuild(force=True)


_accept_host_spell_intents()


class FrameRefreshingHostedRuntime(HostedSessionRuntime):
    """Consume the frame pushed immediately after a stale-action rejection."""

    def step(
        self,
        action: AgentAction,
        frame: AgentFrame,
    ) -> EnvironmentTransition:
        transition = super().step(action, frame)
        if (
            transition.action_status != "rejected"
            or not any(
                marker in transition.action_detail
                for marker in STALE_FRAME_REJECTIONS
            )
            or self._client is None
        ):
            return transition

        deadline = time.monotonic() + self.step_timeout_seconds
        while time.monotonic() < deadline:
            self._client.set_timeout(max(0.001, deadline - time.monotonic()))
            try:
                observed = self._client.frame()
            except EnvironmentRequestError:
                continue
            if observed.frame_id > frame.frame_id:
                self._current = observed
                return self._frame_transition(
                    observed,
                    action_status=transition.action_status,
                    action_detail=transition.action_detail,
                    metrics=transition.metrics,
                )
        return transition


def hosted_endpoints(player_ws_url: str) -> tuple[str, str, int, str]:
    """Derive the environment base URL and authenticated navmesh endpoint."""

    parts = urlsplit(player_ws_url)
    query = parse_qs(parts.query)
    try:
        slot = int(query["slot"][-1])
        token = query["token"][-1]
    except (KeyError, ValueError, IndexError) as exc:
        raise ValueError(
            "COWORLD_PLAYER_WS_URL must include integer slot and token query values"
        ) from exc
    if not token:
        raise ValueError("COWORLD_PLAYER_WS_URL token must be non-empty")
    ws_scheme = "wss" if parts.scheme in ("wss", "https") else "ws"
    http_scheme = "https" if ws_scheme == "wss" else "http"
    env_url = player_ws_url
    navigation_url = urlunsplit(
        (http_scheme, parts.netloc, "/player/navigation", parts.query, "")
    )
    return env_url, navigation_url, slot, token


def build_hosted_env(
    player_ws_url: str,
    *,
    startup_timeout_seconds: float = 240.0,
    step_timeout_seconds: float = 30.0,
) -> VanillaWowEnv:
    env_url, navigation_url, slot, token = hosted_endpoints(player_ws_url)
    os.environ[NAVMESH_SERVICE_URL_ENV] = navigation_url

    def runtime_factory() -> FrameRefreshingHostedRuntime:
        return FrameRefreshingHostedRuntime(
            env_url,
            slot,
            token,
            startup_timeout_seconds=startup_timeout_seconds,
            step_timeout_seconds=step_timeout_seconds,
        )

    return VanillaWowEnv(runtime_factory=runtime_factory)


def hosted_endpoint_diagnostics(player_ws_url: str) -> dict[str, object]:
    """Describe hosted endpoint routing without exposing credential values."""

    env_url, _navigation_url, slot, token = hosted_endpoints(player_ws_url)
    client = EnvironmentWebSocketClient(url=env_url, slot=slot, token=token)
    player_parts = urlsplit(player_ws_url)
    client_parts = urlsplit(client.url)
    return {
        "player_path": player_parts.path,
        "player_query_keys": sorted(parse_qs(player_parts.query)),
        "environment_path": client_parts.path,
        "environment_query_keys": sorted(parse_qs(client_parts.query)),
    }


class GymSession:
    """Stateful policy convenience around one already-reset ``VanillaWowEnv``."""

    def __init__(
        self,
        env: VanillaWowEnv,
        frame: AgentFrame,
        info: dict[str, object],
        tracer: Tracer | None = None,
        frame_observer: Callable[[AgentFrame], None] | None = None,
    ) -> None:
        self.env = env
        self.frame = frame
        self.info = info
        self.finished = False
        self._tracer = tracer or NullTracer()
        self._frame_observer = frame_observer
        self._last_outcome: ActionOutcome | None = None
        self._frame_received_at = time.monotonic()
        self._trace_frame(frame)

    def close(self) -> None:
        self.env.close()

    def wait_for_frame(self, *, timeout_s: float = 60.0) -> AgentFrame | None:
        del timeout_s
        return None if self.finished else self.frame

    def observe(self) -> AgentFrame | None:
        return None if self.finished else self.frame

    def select_move_to(
        self,
        frame: AgentFrame,
        x: float,
        y: float,
        z: float,
        map_id: int,
    ) -> str | None:
        return self.select_action(
            frame,
            AgentAction(
                kind="move_to",
                destination=WorldPoint(
                    map_id=map_id,
                    x=_wire_float(x),
                    y=_wire_float(y),
                    z=_wire_float(z),
                ),
                arrival_radius=3.0,
            ),
        )

    def select_move_vector(
        self,
        frame: AgentFrame,
        *,
        forward: float = 0.0,
        strafe: float = 0.0,
        turn: float = 0.0,
        jump: bool = False,
        duration: float,
        purpose: str,
    ) -> str | None:
        return self.select_action(
            frame,
            AgentAction(
                kind="move_vector",
                intent=purpose,
                forward=forward,
                strafe=strafe,
                turn=turn,
                jump=jump,
                duration=duration,
            ),
        )

    def select_action(self, frame: AgentFrame, action: AgentAction) -> str | None:
        frame_age_ms = round(
            (time.monotonic() - self._frame_received_at) * 1000,
            3,
        )
        if self.finished or frame.frame_id != self.frame.frame_id:
            self._tracer.emit(
                "action_skipped",
                reason="finished" if self.finished else "stale_frame",
                submitted_frame_id=frame.frame_id,
                current_frame_id=self.frame.frame_id,
                action_kind=action.kind,
                frame_age_ms=frame_age_ms,
            )
            return None
        request_id = f"frame-{frame.frame_id}"
        self._tracer.emit(
            "intent",
            request_id=request_id,
            frame_id=frame.frame_id,
            frame_age_ms=frame_age_ms,
            action=action.model_dump(mode="json"),
        )
        step_started_at = time.monotonic()
        next_frame, _reward, terminated, truncated, info = self.env.step(action)
        next_frame_received_at = time.monotonic()
        step_round_trip_ms = round(
            (next_frame_received_at - step_started_at) * 1000,
            3,
        )
        action_status = str(info.get("action_status") or "")
        action_detail = str(info.get("action_detail") or "")
        refreshed = (
            action_status == "rejected"
            and next_frame.frame_id > frame.frame_id
            and any(
                marker in action_detail
                for marker in STALE_FRAME_REJECTIONS
            )
        )
        if refreshed:
            self._tracer.emit(
                "frame_refresh",
                submitted_frame_id=frame.frame_id,
                stale_frame_id=frame.frame_id,
                refreshed_frame_id=next_frame.frame_id,
                rejection=action_detail,
            )
        self.frame = next_frame
        self._frame_received_at = next_frame_received_at
        self.info = info
        self.finished = terminated or truncated
        self._trace_frame(next_frame)
        action_state = next_frame.action_state
        success = action_status not in ("rejected", "timeout")
        detail = action_detail
        settlement_kind = (
            action_status if action_status in ("rejected", "timeout") else None
        )
        if (
            not refreshed
            and action_state is not None
            and action_state.submitted_frame_id == frame.frame_id
        ):
            success = action_state.status == "succeeded"
            detail = action_state.detail or action_state.reason_code
            settlement_kind = action_state.status
        self._last_outcome = ActionOutcome(
            request_id=request_id,
            kind=action.kind,
            success=success,
            settlement_kind=settlement_kind,
            displacement_yards=None,
            end_position=Position(
                next_frame.location.x,
                next_frame.location.y,
                next_frame.location.z,
                0.0,
            ),
            detail=detail,
            frame_id=frame.frame_id,
            settled_tick=next_frame.tick,
        )
        self._tracer.emit(
            "outcome",
            request_id=request_id,
            action_kind=action.kind,
            success=success,
            detail=detail,
            frame_id=next_frame.frame_id,
            tick=next_frame.tick,
            submitted_frame_id=frame.frame_id,
            returned_frame_id=next_frame.frame_id,
            frame_age_ms=frame_age_ms,
            step_round_trip_ms=step_round_trip_ms,
            action_status=action_status,
            stale_refresh=refreshed,
        )
        return request_id

    def select_kind(self, frame: AgentFrame, kind: str) -> str | None:
        action = self._invocation(frame, label=kind)
        return None if action is None else self.select_action(frame, action)

    def select_wait(self, frame: AgentFrame) -> str | None:
        return self.select_action(frame, AgentAction(kind="wait", duration=0.25))

    def select_target_action(
        self,
        frame: AgentFrame,
        kind: Literal["face", "attack"],
        target_guid: str,
    ) -> str | None:
        if kind == "face":
            return self.select_action(
                frame,
                AgentAction(kind="face", target_guid=target_guid),
            )
        action = self._invocation(
            frame,
            label=kind,
            source_kind="unit",
            source_id=target_guid,
        )
        return None if action is None else self.select_action(frame, action)

    def select_stuck(self, frame: AgentFrame) -> str | None:
        if STUCK_SPELL_ID in frame.cooldown_spell_ids:
            self._tracer.emit(
                "stuck_skipped",
                reason="cooldown",
                spell_id=STUCK_SPELL_ID,
                frame_id=frame.frame_id,
            )
            return None
        return self.select_cast_without_target(
            frame,
            STUCK_SPELL_ID,
            purpose="recover from navigation stall",
        )

    def select_cast_without_target(
        self,
        frame: AgentFrame,
        spell_id: int,
        *,
        purpose: str,
    ) -> str | None:
        if spell_id not in frame.known_spells:
            return None
        action = self._invocation(
            frame,
            label="cast",
            source_kind="spell",
            source_id=str(spell_id),
        )
        return None if action is None else self.select_action(frame, action)

    def select_cast_target(
        self,
        frame: AgentFrame,
        spell_id: int,
        target_guid: str,
    ) -> str | None:
        if spell_id not in frame.known_spells:
            return None
        action = self._invocation(
            frame,
            label="cast",
            source_kind="spell",
            source_id=str(spell_id),
            target_guid=target_guid,
        )
        return None if action is None else self.select_action(frame, action)

    def select_cancel_aura(self, frame: AgentFrame, spell_id: int) -> str | None:
        action = self._invocation(
            frame,
            label="cancel_aura",
            source_kind="spell",
            source_id=str(spell_id),
        )
        return None if action is None else self.select_action(frame, action)

    def select_area_trigger(
        self, frame: AgentFrame, trigger_id: int | None
    ) -> str | None:
        selected = trigger_id
        if selected is None and frame.active_area_trigger_ids:
            selected = frame.active_area_trigger_ids[0]
        if selected is None or selected not in frame.active_area_trigger_ids:
            return None
        action = self._invocation(
            frame,
            label="area_trigger",
            source_id=str(selected),
        )
        return None if action is None else self.select_action(frame, action)

    def say(self, text: str) -> str | None:
        action = self._invocation(
            self.frame,
            label="chat_say",
            source_kind="frame",
            source_id="player",
            text=text,
        )
        return None if action is None else self.select_action(self.frame, action)

    @staticmethod
    def _invocation(
        frame: AgentFrame,
        *,
        label: str,
        source_kind: str | None = None,
        source_id: str | None = None,
        target_guid: str | None = None,
        text: str | None = None,
    ) -> AgentAction | None:
        for available in frame.available_actions:
            if available.verb != label:
                continue
            if source_kind is not None and available.source_kind != source_kind:
                continue
            if source_id is not None and available.source_id != source_id:
                continue
            return AgentAction(
                kind="invoke",
                verb=available.verb,
                source_kind=available.source_kind,
                source_id=available.source_id,
                target_guid=target_guid,
                text=text,
            )
        return None

    def wait_for_settlement(
        self, frame_id: int, *, timeout_s: float = 90.0
    ) -> ActionOutcome | None:
        del timeout_s
        if self._last_outcome is None or self._last_outcome.frame_id != frame_id:
            return None
        return self._last_outcome

    def plan_route(
        self,
        source: Position,
        target: Position,
        map_id: int,
        *,
        arrival_radius: float = 3.0,
        tile_load_mode: str = "auto",
    ) -> PlannedRoute:
        route = route_navmesh(
            WorldPoint(map_id=map_id, x=source.x, y=source.y, z=source.z),
            WorldPoint(map_id=map_id, x=target.x, y=target.y, z=target.z),
            arrival_radius=arrival_radius,
            tile_load_mode=tile_load_mode,
        )
        return PlannedRoute(
            status=route.status,
            map_id=route.map_id,
            waypoints=[
                Position(point.x, point.y, point.z, 0.0)
                for point in (route.waypoints or [])
            ],
            route_distance=float(route.route_distance or 0.0),
            partial=bool(route.partial_path_end) or route.path_type == "partial",
            projected_target_distance=route.projected_target_distance,
            jump_required=bool(getattr(route, "jump_required", False)),
            message=route.message or "",
        )

    def local_navigation_graph(
        self,
        source: Point,
        *,
        radius: float,
    ):
        """Return the canonical read-only connected navmesh neighborhood."""
        return local_navmesh_graph(
            WorldPoint(
                map_id=source.map_id,
                x=source.x,
                y=source.y,
                z=source.z,
            ),
            radius=radius,
        )

    def _trace_frame(self, frame: AgentFrame) -> None:
        if self._frame_observer is not None:
            self._frame_observer(frame)
        self._tracer.emit(
            "observation",
            frame_id=frame.frame_id,
            tick=frame.tick,
            map_id=frame.location.map_id,
            position=[frame.location.x, frame.location.y, frame.location.z],
            health=frame.health,
            max_health=frame.max_health,
            in_combat=frame.in_combat,
            is_dead=frame.is_dead,
            is_ghost=frame.is_ghost,
            terminal=frame.environment.terminal,
            captured_at=round(time.time(), 3),
        )
