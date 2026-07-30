"""Wowborg's policy runtime over the canonical Gymnasium ``WS /env`` interface.

The game owns the client, observation projection, action admission, execution,
settlement, reconnects, and transport.  This module only adds policy conveniences:
current-frame bookkeeping, structured traces, and the read-only navmesh query.
"""

from __future__ import annotations

import os
import time
from urllib.parse import parse_qs, urlsplit, urlunsplit

from environment import VanillaWowEnv
from environment.contract.agent import (
    AgentAction,
    AgentFrame,
    AreaTriggerAction,
    CastAction,
    MoveAction,
    NoArgumentAction,
    TextAction,
    WaitAction,
    WorldPoint,
)
from environment.runtime.hosted_session import hosted_runtime_factory
from player.sdk.navmesh import route_navmesh

from wowborg.trace import NullTracer, Tracer
from wowborg.types import ActionOutcome, PlannedRoute, Position

PLAYER_WS_URL_ENV = "COWORLD_PLAYER_WS_URL"
NAVMESH_SERVICE_URL_ENV = "VANILLA_WOW_NAVMESH_SERVICE_URL"
STUCK_SPELL_ID = 7355


def hosted_endpoints(player_ws_url: str) -> tuple[str, str, int, str]:
    """Derive the authenticated environment and navmesh endpoints from `/player`."""

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
    clean_query = ""
    env_url = urlunsplit((ws_scheme, parts.netloc, "/env", clean_query, ""))
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
    return VanillaWowEnv(
        runtime_factory=hosted_runtime_factory(
            env_url,
            slot,
            token,
            startup_timeout_seconds=startup_timeout_seconds,
            step_timeout_seconds=step_timeout_seconds,
        )
    )


class GymSession:
    """Stateful policy convenience around one already-reset ``VanillaWowEnv``."""

    def __init__(
        self,
        env: VanillaWowEnv,
        frame: AgentFrame,
        info: dict[str, object],
        tracer: Tracer | None = None,
    ) -> None:
        self.env = env
        self.frame = frame
        self.info = info
        self.finished = False
        self._tracer = tracer or NullTracer()
        self._last_outcome: ActionOutcome | None = None
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
            MoveAction(
                destination=WorldPoint(map_id=map_id, x=x, y=y, z=z),
                arrival_radius=3.0,
                purpose="wowborg navigation",
            ),
        )

    def select_action(self, frame: AgentFrame, action: AgentAction) -> str | None:
        if self.finished or frame.frame_id != self.frame.frame_id:
            return None
        request_id = f"frame-{frame.frame_id}"
        self._tracer.emit(
            "intent",
            request_id=request_id,
            frame_id=frame.frame_id,
            action=action.model_dump(mode="json"),
        )
        next_frame, _reward, terminated, truncated, info = self.env.step(action)
        self.frame = next_frame
        self.info = info
        self.finished = terminated or truncated
        self._trace_frame(next_frame)
        action_state = next_frame.action_state
        success = info.get("action_status") not in ("rejected", "timeout")
        detail = str(info.get("action_detail") or "")
        if action_state is not None and action_state.submitted_frame_id == frame.frame_id:
            success = action_state.status == "succeeded"
            detail = action_state.detail or action_state.reason_code
        self._last_outcome = ActionOutcome(
            request_id=request_id,
            kind=action.kind,
            success=success,
            settlement_kind=None,
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
        )
        return request_id

    def select_kind(self, frame: AgentFrame, kind: str) -> str | None:
        return self.select_action(frame, NoArgumentAction(kind=kind))

    def select_wait(self, frame: AgentFrame) -> str | None:
        return self.select_action(
            frame, WaitAction(duration=0.25, reason="wowborg supervision")
        )

    def select_stuck(self, frame: AgentFrame) -> str | None:
        if STUCK_SPELL_ID not in frame.known_spells:
            return None
        return self.select_action(
            frame,
            CastAction(
                spell_id=STUCK_SPELL_ID,
                cast_without_target=True,
                purpose="recover from navigation stall",
            ),
        )

    def select_area_trigger(
        self, frame: AgentFrame, trigger_id: int | None
    ) -> str | None:
        selected = trigger_id
        if selected is None and frame.active_area_trigger_ids:
            selected = frame.active_area_trigger_ids[0]
        if selected is None or selected not in frame.active_area_trigger_ids:
            return None
        return self.select_action(frame, AreaTriggerAction(target_entry=selected))

    def say(self, text: str) -> str | None:
        return self.select_action(
            self.frame, TextAction(kind="chat_say", text=text)
        )

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
            jump_required=bool(route.jump_required),
            message=route.message or "",
        )

    def _trace_frame(self, frame: AgentFrame) -> None:
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
