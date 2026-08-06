"""Wowborg's policy runtime over the canonical Gymnasium ``WS /env`` interface.

The game owns the client, observation projection, action admission, execution,
settlement, reconnects, and transport.  This module only adds policy conveniences:
current-frame bookkeeping, structured traces, and the read-only navmesh query.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Literal
from urllib.parse import parse_qs, urlsplit, urlunsplit

from environment import VanillaWowEnv
from environment.contract.agent import (
    AgentAction,
    AgentFrame,
    AreaTriggerAction,
    CastAction,
    MoveAction,
    NoArgumentAction,
    SpellObservation,
    TargetAction,
    TextAction,
    WaitAction,
    WorldPoint,
)
from environment.control import EnvironmentRequestError
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
    "submission does not match the current AgentFrame",
    "no AgentFrame is awaiting an action",
    "action submission arrived after the game-wide deadline",
)


def _accept_host_spell_intents() -> None:
    """Match the host's open spell-intent vocabulary at the JSON trust boundary."""
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

    def runtime_factory() -> FrameRefreshingHostedRuntime:
        return FrameRefreshingHostedRuntime(
            env_url,
            slot,
            token,
            startup_timeout_seconds=startup_timeout_seconds,
            step_timeout_seconds=step_timeout_seconds,
        )

    return VanillaWowEnv(runtime_factory=runtime_factory)


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
        )
        return request_id

    def select_kind(self, frame: AgentFrame, kind: str) -> str | None:
        return self.select_action(frame, NoArgumentAction(kind=kind))

    def select_wait(self, frame: AgentFrame) -> str | None:
        return self.select_action(
            frame, WaitAction(duration=0.25, reason="wowborg supervision")
        )

    def select_target_action(
        self,
        frame: AgentFrame,
        kind: Literal["face", "attack"],
        target_guid: str,
    ) -> str | None:
        return self.select_action(
            frame,
            TargetAction(kind=kind, target_guid=target_guid),
        )

    def select_stuck(self, frame: AgentFrame) -> str | None:
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
        return self.select_action(
            frame,
            CastAction(
                spell_id=spell_id,
                cast_without_target=True,
                purpose=purpose,
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
