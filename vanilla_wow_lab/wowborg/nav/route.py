"""L1 — the route navigator: same-map navigation to any distance, with the nav
state machine the codex audit prescribed.

Flow per navigate_to(target):
  plan (via /player/navigation) → one direct L0 semantic move per plan → arrived
  (the executor's server-side Detour owns locomotion; the plan supplies the
  reachability verdict, the distance-derived budget, and — for partial corridors —
  the intermediate progression target)
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
            # First plan per navigate_to loads ALL map tiles: a definitive full
            # route (true distance → honest budget) or a definitive no_path —
            # v26 evidence: "auto" corridor loading returned 150-300yd partials
            # that forced a re-plan cycle every corridor end on long hauls.
            # Re-plans use the cheap corridor mode; "all" falls back to "auto"
            # if the heavyweight query itself fails.
            tile_mode = "all" if replans == 0 else "auto"
            plan = bridge.plan_route(
                _pos(here), _pos(target), target.map_id,
                arrival_radius=arrival_radius, tile_load_mode=tile_mode,
            )
            if tile_mode == "all" and (plan.status not in ("ok", "no_path")):
                plan = bridge.plan_route(
                    _pos(here), _pos(target), target.map_id,
                    arrival_radius=arrival_radius,
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
                # Bare no_path (zero waypoints) has two very different causes:
                # a genuinely off-mesh target, or a BROKEN planner (v25 hosted
                # evidence: after service timeouts, EVERY plan — including for
                # known-good targets — returned bare no_path, and reachable
                # stations were reported "unreachable"). Disambiguate with a
                # self-probe: planning here→here trivially succeeds on a working
                # planner. Probe fails → degrade (the executor's own server-side
                # Detour still routes direct moves); probe passes → honest fail.
                probe = bridge.plan_route(_pos(here), _pos(here), here.map_id)
                if probe.status == "ok":
                    return RouteResult(NavState.FAILED, reason="unreachable", end=here,
                                       walked_seconds=walked_seconds,
                                       combat_pauses=combat_pauses, deaths=deaths,
                                       replans=replans)
                self._trace("nav_planner_broken", probe_status=probe.status)
                plan = plan.__class__(
                    status="unavailable", map_id=plan.map_id, waypoints=[],
                    route_distance=0.0, partial=False,
                    projected_target_distance=None, jump_required=False,
                    message="planner self-probe failed; degrading",
                )
            if plan.status in ("unavailable", "error") or not plan.waypoints:
                # Degraded mode: no planner — one direct L0 move with a floor budget.
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
                planned_distance = plan.route_distance
                if plan.partial:
                    partial_end = _pt(plan.waypoints[-1], target.map_id)
                    progress = here.distance(target) - partial_end.distance(target)
                    # An empty partial — its end within the stage radius, so L0
                    # would "arrive" without moving (v30: a repeated 37yd corridor
                    # at the valley gate looped 500s that way). NOT proof of
                    # unreachability either: findPath's node pool truncates long
                    # corridors at a heuristic frontier (v29: razor-hill declared
                    # unreachable off a 26yd partial). Genuine unreachables still
                    # fail fast via off-mesh projection or zero-waypoint no_path.
                    if (progress < ARRIVAL_RADIUS_YARDS
                            or here.distance(partial_end) <= STAGE_ARRIVAL_RADIUS_YARDS):
                        nearby = sum(1 for s in replan_spots
                                     if s.distance(here) <= SAME_SPOT_YARDS)
                        if nearby >= REPLAN_LIMIT_PER_REGION:
                            return RouteResult(
                                NavState.FAILED, reason="no_progress", end=here,
                                walked_seconds=walked_seconds,
                                combat_pauses=combat_pauses, deaths=deaths,
                                replans=replans)
                        replan_spots.append(here)
                        replans += 1
                        self._trace("nav_state", state="replanning",
                                    cause="empty_partial")
                        # Nudge: one direct semantic move at the raw target — the
                        # executor's server-side Detour escapes local frontiers our
                        # corridor query can't. Budget from the REAL remaining
                        # distance, not the truncated corridor's.
                        arrival_check = target
                        planned_distance = here.distance(target)
                    else:
                        # Walk to the partial end, then re-plan onward from there.
                        arrival_check = partial_end
            result.planned_distance = max(result.planned_distance, planned_distance)

            budget = max(
                BUDGET_FLOOR_SECONDS,
                planned_distance / max(self.pace.estimate, 0.2) * BUDGET_SLACK,
            )
            budget_left = budget

            # ---- WALKING (one direct semantic move per plan) ----
            # We do NOT micro-hop the service waypoints. v28 evidence: Detour
            # findPath returns POOL-LIMITED partial corridors whose frontier is
            # the heuristic-closest node — often up a cliff face — and hopping
            # toward that frontier marched the executor into "no admissible
            # source projection" traps, while our re-issue churn kept resetting
            # its internal auto-unstuck. The executor's own server-side planner
            # (with NavigationMemory + stock recovery) owns locomotion; our plan
            # supplies the honesty verdict, budget, and the partial-progression
            # target. (Same conclusion as the v19 waypoint race: far legs DIRECT.)
            walk_failed: str | None = None
            while True:
                if time.monotonic() >= deadline:
                    return RouteResult(NavState.FAILED, reason="deadline", end=here,
                                       walked_seconds=walked_seconds,
                                       combat_pauses=combat_pauses, deaths=deaths,
                                       replans=replans)
                hop = arrival_check
                hop_started = time.monotonic()
                # A partial end / projection is a corridor-grade stop (stage
                # radius); the true target keeps the caller's arrival radius.
                final_hop = arrival_check.distance(target) <= arrival_radius
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
                    if final_hop:
                        self._trace("nav_state", state="arrived")
                        return RouteResult(
                            NavState.ARRIVED, end=here,
                            planned_distance=result.planned_distance,
                            walked_seconds=walked_seconds,
                            combat_pauses=combat_pauses, deaths=deaths, replans=replans)
                    break  # reached a partial end / projection → re-plan onward

                if move.status == LocalMoveStatus.COMBAT:
                    combat_pauses += 1
                    self._trace("nav_state", state="combat_paused")
                    if not self._wait_out_combat(bridge, deadline):
                        return RouteResult(NavState.FAILED, reason="deadline", end=here,
                                           walked_seconds=walked_seconds,
                                           combat_pauses=combat_pauses, deaths=deaths,
                                           replans=replans)
                    here = self._observe_position(bridge) or here
                    # Same target, same plan — resume the walk directly (v31: a
                    # full re-plan after every canyon fight cost a plan round
                    # trip + empty-partial churn per pull; budget clock was
                    # paused either way).
                    continue

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
                    # Not instantly fatal (v27: transient socket timeouts +
                    # controller frame droughts produced 60s NO_FRAMEs while the
                    # session was otherwise healthy). Re-plan from wherever we
                    # are; the same-spot replan limit still bounds it honestly.
                    here = self._observe_position(bridge) or here
                    walk_failed = "no_frame"
                    break

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


