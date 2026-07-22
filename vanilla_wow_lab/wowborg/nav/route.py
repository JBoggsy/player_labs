"""L1 — the route navigator: same-map navigation to any distance, with the nav
state machine the codex audit prescribed.

Flow per navigate_to(target):
  plan (via /player/navigation) → walk planned waypoints as L0 hops → arrived
  Transitions handled at THIS layer (the audit's critical findings):
  - combat  → combat_paused: budget clock stops; on combat end, re-plan from here.
  - death   → recovering: defer to the planner's recovery recommendations (release/
    corpse-run/reclaim are its recommended actions); on revival, re-plan. Budget paused.
  - map change → escalate (the journey layer owns cross-map).
  - stall/oscillation → re-plan once from the current position; second failure at the
    same region → honest failure.
  - partial route / unreachable target → detected AT PLANNING TIME: walk to the
    partial end only if it makes real progress, else fail fast with "unreachable".

Budgets derive from PLANNED ROUTE DISTANCE and an ONLINE pace estimate — never
straight-line distance, never zone constants.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from wowborg.nav.local import (
    ARRIVAL_RADIUS_YARDS,
    STAGE_ARRIVAL_RADIUS_YARDS,
    LocalMover,
    LocalMoveStatus,
)
from wowborg.nav.world_model import Point

# Structural constants (not zone calibration):
HOP_HORIZON_YARDS = 60.0        # hop to the farthest planned waypoint within this
REPLAN_LIMIT_PER_REGION = 2     # planning attempts from ~the same spot before failing
SAME_SPOT_YARDS = 20.0
BUDGET_SLACK = 1.8              # x planned_time; generous — the pace estimate tightens it
BUDGET_FLOOR_SECONDS = 45.0
DEFAULT_PACE_YDS_PER_S = 1.8    # prior; replaced by the online estimate as legs complete
RECOVERY_STEP_TIMEOUT_S = 45.0
UNREACHABLE_PROJECTION_YARDS = 12.0  # planned-target projection beyond this = off-mesh target


class NavState(Enum):
    PLANNING = "planning"
    WALKING = "walking"
    COMBAT_PAUSED = "combat_paused"
    RECOVERING = "recovering"
    ARRIVED = "arrived"
    FAILED = "failed"
    ESCALATE_MAP = "escalate_map"   # target on another map — journey layer's job


@dataclass
class RouteResult:
    state: NavState                  # ARRIVED / FAILED / ESCALATE_MAP
    reason: str = ""                 # for FAILED: unreachable|no_progress|budget|no_frame|deadline
    end: Point | None = None
    planned_distance: float = 0.0
    walked_seconds: float = 0.0      # budget-clock seconds (combat/recovery excluded)
    combat_pauses: int = 0
    deaths: int = 0
    replans: int = 0


@dataclass
class PaceEstimator:
    """Online yards-per-second over completed hops (EW average, session-scoped)."""

    estimate: float = DEFAULT_PACE_YDS_PER_S
    _samples: int = 0

    def record(self, yards: float, seconds: float) -> None:
        if seconds <= 0.5 or yards <= 1.0:
            return
        sample = yards / seconds
        # clamp absurd samples (teleports, clock skew)
        sample = max(0.2, min(sample, 8.0))
        weight = 0.3 if self._samples else 1.0
        self.estimate = (1 - weight) * self.estimate + weight * sample
        self._samples += 1


@dataclass
class RouteNavigator:
    tracer: object | None = None
    pace: PaceEstimator = field(default_factory=PaceEstimator)
    mover: LocalMover = field(default_factory=LocalMover)

    def __post_init__(self) -> None:
        self.mover.tracer = self.tracer

    def _trace(self, kind: str, **payload) -> None:
        if self.tracer is not None:
            self.tracer.emit(kind, **payload)

    # ---- the public verb -------------------------------------------------------

    def navigate_to(
        self,
        bridge,
        target: Point,
        *,
        deadline: float,
        arrival_radius: float = ARRIVAL_RADIUS_YARDS,
    ) -> RouteResult:
        result = RouteResult(state=NavState.PLANNING)
        combat_pauses = deaths = replans = 0
        walked_seconds = 0.0
        replan_spots: list[Point] = []

        here = self._observe_position(bridge)
        if here is None:
            return RouteResult(NavState.FAILED, reason="no_frame")
        if here.map_id != target.map_id:
            return RouteResult(NavState.ESCALATE_MAP, end=here)

        while True:
            if time.monotonic() >= deadline:
                return RouteResult(NavState.FAILED, reason="deadline", end=here,
                                   walked_seconds=walked_seconds,
                                   combat_pauses=combat_pauses, deaths=deaths, replans=replans)

            # ---- PLANNING ----
            plan = bridge.plan_route(
                _pos(here), _pos(target), target.map_id, arrival_radius=arrival_radius
            )
            self._trace("nav_state", state="planning", plan_status=plan.status,
                        planned_distance=round(plan.route_distance, 1))

            arrival_check = target
            # Live-service semantics (first hosted World Race): a distant target often
            # returns status="no_path" WITH partial waypoints — Detour tiles load
            # progressively, so the full path only resolves as we approach. no_path is
            # unreachable ONLY when the service offers no usable progress.
            if plan.status in ("no_path", "unreachable_target") and plan.waypoints:
                plan = plan.__class__(
                    status="ok", map_id=plan.map_id, waypoints=plan.waypoints,
                    route_distance=plan.route_distance, partial=True,
                    projected_target_distance=plan.projected_target_distance,
                    jump_required=plan.jump_required, message=plan.message,
                )
            if plan.status in ("no_path", "unreachable_target"):
                return RouteResult(NavState.FAILED, reason="unreachable", end=here,
                                   walked_seconds=walked_seconds,
                                   combat_pauses=combat_pauses, deaths=deaths, replans=replans)
            if plan.status in ("unavailable", "error") or not plan.waypoints:
                # Degraded mode: no planner — one direct L0 move with a floor budget.
                waypoints = [target]
                planned_distance = here.distance(target)
            else:
                if (
                    plan.projected_target_distance is not None
                    and plan.projected_target_distance > UNREACHABLE_PROJECTION_YARDS
                ):
                    # The target itself is off-mesh; the walkable end is the projection.
                    if plan.partial or not plan.waypoints:
                        return RouteResult(
                            NavState.FAILED, reason="unreachable", end=here,
                            walked_seconds=walked_seconds,
                            combat_pauses=combat_pauses, deaths=deaths, replans=replans)
                    arrival_check = _pt(plan.waypoints[-1], target.map_id)
                if plan.partial:
                    partial_end = _pt(plan.waypoints[-1], target.map_id)
                    progress = here.distance(target) - partial_end.distance(target)
                    if progress < STAGE_ARRIVAL_RADIUS_YARDS:
                        return RouteResult(
                            NavState.FAILED, reason="unreachable", end=here,
                            walked_seconds=walked_seconds,
                            combat_pauses=combat_pauses, deaths=deaths, replans=replans)
                    # Walk to the partial end, then re-plan (loop continues from there).
                    arrival_check = partial_end
                waypoints = [_pt(w, target.map_id) for w in plan.waypoints]
                planned_distance = plan.route_distance
            result.planned_distance = max(result.planned_distance, planned_distance)

            budget = max(
                BUDGET_FLOOR_SECONDS,
                planned_distance / max(self.pace.estimate, 0.2) * BUDGET_SLACK,
            )
            budget_left = budget

            # ---- WALKING (hop over planned waypoints) ----
            walk_failed: str | None = None
            hop_index = 0
            while True:
                if time.monotonic() >= deadline:
                    return RouteResult(NavState.FAILED, reason="deadline", end=here,
                                       walked_seconds=walked_seconds,
                                       combat_pauses=combat_pauses, deaths=deaths,
                                       replans=replans)
                hop, hop_index = _next_hop_index(here, waypoints, hop_index, arrival_check)
                hop_started = time.monotonic()
                final_hop = hop.distance(arrival_check) <= ARRIVAL_RADIUS_YARDS
                move = self.mover.move_to(
                    bridge, hop,
                    arrival_radius=arrival_radius if final_hop else STAGE_ARRIVAL_RADIUS_YARDS,
                    until=min(deadline, time.monotonic() + budget_left),
                    arrival_target=None,
                )
                hop_seconds = time.monotonic() - hop_started

                if move.end is not None:
                    self.pace.record(here.distance(move.end), hop_seconds)
                    here = move.end
                walked_seconds += hop_seconds
                budget_left -= hop_seconds

                if move.status == LocalMoveStatus.ARRIVED:
                    if here.distance(arrival_check) <= arrival_radius:
                        if arrival_check is target or arrival_check.distance(target) <= arrival_radius:
                            self._trace("nav_state", state="arrived")
                            return RouteResult(
                                NavState.ARRIVED, end=here,
                                planned_distance=result.planned_distance,
                                walked_seconds=walked_seconds,
                                combat_pauses=combat_pauses, deaths=deaths, replans=replans)
                        break  # reached a partial end / projection → re-plan onward
                    continue  # hop done, more waypoints ahead

                if move.status == LocalMoveStatus.COMBAT:
                    combat_pauses += 1
                    self._trace("nav_state", state="combat_paused")
                    if not self._wait_out_combat(bridge, deadline):
                        return RouteResult(NavState.FAILED, reason="deadline", end=here,
                                           walked_seconds=walked_seconds,
                                           combat_pauses=combat_pauses, deaths=deaths,
                                           replans=replans)
                    here = self._observe_position(bridge) or here
                    break  # re-plan from wherever combat left us (budget clock was paused)

                if move.status == LocalMoveStatus.DEAD:
                    deaths += 1
                    self._trace("nav_state", state="recovering")
                    if not self._recover_from_death(bridge, deadline):
                        return RouteResult(NavState.FAILED, reason="deadline", end=here,
                                           walked_seconds=walked_seconds,
                                           combat_pauses=combat_pauses, deaths=deaths,
                                           replans=replans)
                    here = self._observe_position(bridge) or here
                    if here.map_id != target.map_id:
                        return RouteResult(NavState.ESCALATE_MAP, end=here,
                                           walked_seconds=walked_seconds,
                                           combat_pauses=combat_pauses, deaths=deaths,
                                           replans=replans)
                    break  # re-plan from the revival point

                if move.status == LocalMoveStatus.MAP_CHANGED:
                    return RouteResult(NavState.ESCALATE_MAP, end=here,
                                       walked_seconds=walked_seconds,
                                       combat_pauses=combat_pauses, deaths=deaths,
                                       replans=replans)

                if move.status in (LocalMoveStatus.STALLED, LocalMoveStatus.OSCILLATING):
                    walk_failed = move.status.value
                    break

                if move.status == LocalMoveStatus.NO_FRAME:
                    return RouteResult(NavState.FAILED, reason="no_frame", end=here,
                                       walked_seconds=walked_seconds,
                                       combat_pauses=combat_pauses, deaths=deaths,
                                       replans=replans)

                if move.status == LocalMoveStatus.DEADLINE:
                    if budget_left <= 0:
                        walk_failed = "budget"
                        break
                    return RouteResult(NavState.FAILED, reason="deadline", end=here,
                                       walked_seconds=walked_seconds,
                                       combat_pauses=combat_pauses, deaths=deaths,
                                       replans=replans)

            # ---- RE-PLAN or FAIL ----
            if walk_failed is not None:
                nearby = sum(1 for s in replan_spots if s.distance(here) <= SAME_SPOT_YARDS)
                if nearby >= REPLAN_LIMIT_PER_REGION:
                    return RouteResult(
                        NavState.FAILED,
                        reason="no_progress" if walk_failed != "budget" else "budget",
                        end=here, planned_distance=result.planned_distance,
                        walked_seconds=walked_seconds,
                        combat_pauses=combat_pauses, deaths=deaths, replans=replans)
                replan_spots.append(here)
            replans += 1
            self._trace("nav_state", state="replanning", cause=walk_failed or "waypoint")

    # ---- transitions -----------------------------------------------------------------

    def _observe_position(self, bridge) -> Point | None:
        obs = bridge.observe()
        if obs is None:
            return None
        # During login the controller reports map 0 at the origin — not a real
        # position (first hosted World Race: a slow login turned every station into
        # instant unknown_region failures). Not-yet-in-world reads as "no position".
        if obs.map_id == 0 and abs(obs.position.x) < 0.5 and abs(obs.position.y) < 0.5:
            return None
        return Point(obs.map_id, obs.position.x, obs.position.y, obs.position.z)

    def _wait_out_combat(self, bridge, deadline: float) -> bool:
        """Budget clock is paused by construction (walk loop measures only hops).
        Nav never fights: defer to the recommended action (the authored combat stack)
        until in_combat clears."""
        while time.monotonic() < deadline:
            frame = bridge.wait_for_frame(timeout_s=min(30.0, max(0.5, deadline - time.monotonic())))
            if frame is None:
                time.sleep(1.0)
                continue
            if not frame.observation.in_combat:
                return True
            request_id = bridge.select_recommended(frame)
            if request_id is not None:
                bridge.wait_for_settlement(frame.frame_id, timeout_s=RECOVERY_STEP_TIMEOUT_S)
        return False

    def _recover_from_death(self, bridge, deadline: float) -> bool:
        """Defer to the planner's recovery recommendations (release → corpse run →
        reclaim are its masked recommended actions) until alive again."""
        while time.monotonic() < deadline:
            frame = bridge.wait_for_frame(timeout_s=min(30.0, max(0.5, deadline - time.monotonic())))
            if frame is None:
                time.sleep(1.0)
                continue
            obs = frame.observation
            if not obs.is_dead and not obs.is_ghost:
                return True
            request_id = bridge.select_recommended(frame)
            if request_id is not None:
                bridge.wait_for_settlement(frame.frame_id, timeout_s=RECOVERY_STEP_TIMEOUT_S)
        return False


def _pos(point: Point):
    from wowborg.types import Position

    return Position(point.x, point.y, point.z, 0.0)


def _pt(position, map_id: int) -> Point:
    return Point(map_id, position.x, position.y, position.z)


def _next_hop_index(
    here: Point, waypoints: list[Point], start_index: int, final: Point
) -> tuple[Point, int]:
    """Directional hop selection: consume waypoints in ROUTE ORDER, never backwards.

    Returns (hop_target, new_start_index). start_index advances past every waypoint
    we are already within stage radius of; the hop is the farthest REMAINING waypoint
    within the horizon (unit-test lesson: distance-only selection picked waypoints
    BEHIND us once the list contained passed points — a 2-point oscillation).
    """
    index = start_index
    while index < len(waypoints) and here.distance(waypoints[index]) <= STAGE_ARRIVAL_RADIUS_YARDS:
        index += 1
    if here.distance(final) <= HOP_HORIZON_YARDS:
        return final, index
    candidate: Point | None = None
    scan = index
    while scan < len(waypoints):
        if here.distance(waypoints[scan]) <= HOP_HORIZON_YARDS:
            candidate = waypoints[scan]
            scan += 1
        else:
            break
    if candidate is not None:
        return candidate, index
    if index < len(waypoints):
        return waypoints[index], index
    return final, index
