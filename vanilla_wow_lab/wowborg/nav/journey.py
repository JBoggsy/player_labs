"""L2 — the journey planner: navigate literally anywhere, across maps and gates.

journey_to(target): if same-map, delegate straight to L1. Otherwise plan over the
world-model graph from the nearest known place to the nearest place on the target's
map, execute edge by edge (walk edges = L1 routes; portal edges = stand at the pad
and fire area_trigger), then L1 the final same-map stretch. Death-warps that change
our map mid-journey trigger graph re-planning from wherever we are.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from wowborg.nav.route import NavState, RouteNavigator
from wowborg.nav.world_model import Edge, Point, WorldModel

PORTAL_PAD_RADIUS_YARDS = 5.0
PORTAL_FIRE_ATTEMPTS = 3
PORTAL_SETTLE_SECONDS = 20.0
# A correct portal lands NEAR the declared destination — same map elsewhere
# (death warp, unexpected teleport) is NOT success (codex audit #16). Generous:
# instance entrances place the party in a room, not on a point.
PORTAL_DESTINATION_RADIUS_YARDS = 150.0
# Road anchors are corridor waypoints, not destinations — corridor-grade arrival.
ROAD_ANCHOR_RADIUS_YARDS = 30.0
# Proactive road routing kicks in for trips at least this long, when both ends
# sit near graph anchors (structural: short trips are one corridor anyway).
ROAD_TRIP_MIN_YARDS = 400.0
ROAD_ANCHOR_NEAR_YARDS = 250.0


class JourneyStatus(Enum):
    ARRIVED = "arrived"
    FAILED = "failed"


@dataclass
class JourneyResult:
    status: JourneyStatus
    reason: str = ""
    end: Point | None = None
    legs: list[dict] = field(default_factory=list)  # per-leg summaries for tracing


@dataclass
class JourneyPlanner:
    world: WorldModel = field(default_factory=WorldModel)
    tracer: object | None = None
    router: RouteNavigator = field(default_factory=RouteNavigator)

    def __post_init__(self) -> None:
        self.router.tracer = self.tracer

    def _trace(self, kind: str, **payload) -> None:
        if self.tracer is not None:
            self.tracer.emit(kind, **payload)

    def journey_to(self, bridge, target: Point, *, deadline: float) -> JourneyResult:
        legs: list[dict] = []
        replan_count = 0
        last_replan_at: Point | None = None  # local: journeys must not share it
        # (codex audit #17: the old instance attribute leaked across stations)
        while time.monotonic() < deadline:
            here = self.router._observe_position(bridge)
            if here is None:
                return JourneyResult(JourneyStatus.FAILED, reason="no_frame", legs=legs)

            if here.map_id == target.map_id:
                # Proactive road routing: when the target is beyond one Detour
                # corridor AND the world graph knows a road between here and
                # there, walk the road anchors FIRST. v41 long-session evidence:
                # recovery-only road use fired after the character was already
                # wedged in the canyon dead-end (every move from inside the
                # pocket stalls); the graph's own edge note says to take the
                # south road instead of cutting straight — declared knowledge
                # must shape the route before the trap, not after.
                if self._should_take_road(here, target):
                    graph_result = self._same_map_via_graph(
                        bridge, target, deadline, legs)
                    if graph_result is not None:
                        return graph_result
                    here = self.router._observe_position(bridge) or here
                result = self.router.navigate_to(bridge, target, deadline=deadline)
                legs.append(_leg("route", target, result.state.value, result.reason,
                                 route=result))
                if result.state == NavState.ARRIVED:
                    return JourneyResult(JourneyStatus.ARRIVED, end=result.end, legs=legs)
                if result.state == NavState.ESCALATE_MAP:
                    # Death-warp etc. changed our map — re-plan the journey.
                    replan_count += 1
                    if replan_count > 5:
                        return JourneyResult(JourneyStatus.FAILED,
                                             reason="journey_thrash", legs=legs)
                    continue
                if result.reason in ("no_progress", "budget"):
                    # Direct route dead-ended (terrain trap the local corridor
                    # can't solve — the v25-v40 canyon wall). If the world graph
                    # KNOWS a road between here and the target, walk it via the
                    # graph waypoints once before giving up (declared road
                    # knowledge as recovery, not requirement).
                    graph_result = self._same_map_via_graph(
                        bridge, target, deadline, legs)
                    if graph_result is not None:
                        return graph_result
                return JourneyResult(JourneyStatus.FAILED, reason=result.reason,
                                     end=result.end, legs=legs)

            # Cross-map: plan over the world graph.
            start_place = self.world.nearest_place(here, same_map=True)
            goal_place = self.world.nearest_place(target, same_map=True) or (
                # target's map has known places? use nearest on THAT map
                self._nearest_on_map(target)
            )
            if start_place is None or goal_place is None:
                return JourneyResult(
                    JourneyStatus.FAILED, reason="unknown_region", end=here, legs=legs)
            path = self.world.plan(start_place.name, goal_place.name)
            if path is None:
                return JourneyResult(
                    JourneyStatus.FAILED, reason="no_world_path", end=here, legs=legs)
            self._trace("journey_planned",
                        start=start_place.name, goal=goal_place.name,
                        edges=[f"{e.kind}:{e.a}->{e.b}" for e in path])

            # Execute edges until arrival on the target map (then loop → same-map case).
            current = start_place.name
            failed = False
            for edge in path:
                if time.monotonic() >= deadline:
                    return JourneyResult(JourneyStatus.FAILED, reason="deadline",
                                         end=here, legs=legs)
                next_name = edge.b if edge.a == current else edge.a
                ok, here = self._execute_edge(bridge, edge, current, next_name, deadline)
                legs.append(_leg(edge.kind, self.world.place(next_name).point,
                                 "ok" if ok else "failed", ""))
                if not ok:
                    failed = True
                    break
                current = next_name
                if here is not None and here.map_id == target.map_id:
                    break  # we're on the target's map — same-map L1 takes over
            if failed:
                # Progress-aware thrash guard: a re-plan only counts against the
                # limit if we did NOT move meaningfully since the last one
                # (same-map only — cross-map distances are meaningless).
                if (here is not None and last_replan_at is not None
                        and here.map_id == last_replan_at.map_id
                        and here.distance(last_replan_at) > 50.0):
                    replan_count = 0
                last_replan_at = here
                replan_count += 1
                if replan_count > 3:
                    return JourneyResult(JourneyStatus.FAILED,
                                         reason="journey_thrash", legs=legs)
                continue
        return JourneyResult(JourneyStatus.FAILED, reason="deadline", legs=legs)

    def _should_take_road(self, here: Point, target: Point) -> bool:
        """Take the graph road when the trip is long and both ends have nearby
        anchors whose road path is meaningfully articulated (≥2 walk edges —
        a single edge adds nothing over the direct corridor)."""
        if here.horizontal_distance(target) < ROAD_TRIP_MIN_YARDS:
            return False
        start = self.world.nearest_place(here, same_map=True)
        goal = self.world.nearest_place(target, same_map=True)
        if start is None or goal is None or start.name == goal.name:
            return False
        if start.point.horizontal_distance(here) > ROAD_ANCHOR_NEAR_YARDS:
            return False
        if goal.point.horizontal_distance(target) > ROAD_ANCHOR_NEAR_YARDS:
            return False
        path = self.world.plan(start.name, goal.name)
        return path is not None and len(path) >= 2 and all(
            e.kind == "walk" for e in path)

    def _same_map_via_graph(
        self, bridge, target: Point, deadline: float, legs: list[dict]
    ) -> JourneyResult | None:
        """Recovery: walk the world graph's road between here and the target.

        Returns None when the graph can't help (no nearby anchors / no path) —
        the caller then reports the direct route's failure honestly.
        """
        here = self.router._observe_position(bridge)
        if here is None:
            return None
        start_place = self.world.nearest_place(here, same_map=True)
        goal_place = self.world.nearest_place(target, same_map=True)
        if start_place is None or goal_place is None:
            return None
        if start_place.name == goal_place.name:
            return None
        path = self.world.plan(start_place.name, goal_place.name)
        if path is None or not all(e.kind == "walk" for e in path):
            return None
        self._trace("journey_road_recovery",
                    start=start_place.name, goal=goal_place.name,
                    edges=[f"{e.a}->{e.b}" for e in path])
        current = start_place.name
        for edge in path:
            if time.monotonic() >= deadline:
                return JourneyResult(JourneyStatus.FAILED, reason="deadline",
                                     end=here, legs=legs)
            next_name = edge.b if edge.a == current else edge.a
            waypoint = self.world.place(next_name).point
            result = self.router.navigate_to(
                bridge, waypoint, deadline=deadline,
                arrival_radius=ROAD_ANCHOR_RADIUS_YARDS)
            legs.append(_leg("road", waypoint, result.state.value, result.reason,
                             route=result))
            if result.state != NavState.ARRIVED:
                return JourneyResult(JourneyStatus.FAILED, reason=result.reason,
                                     end=result.end, legs=legs)
            current = next_name
            here = result.end or here
        final = self.router.navigate_to(bridge, target, deadline=deadline)
        legs.append(_leg("route", target, final.state.value, final.reason,
                         route=final))
        if final.state == NavState.ARRIVED:
            return JourneyResult(JourneyStatus.ARRIVED, end=final.end, legs=legs)
        return JourneyResult(JourneyStatus.FAILED, reason=final.reason,
                             end=final.end, legs=legs)

    # ---- edges ---------------------------------------------------------------------

    def _execute_edge(
        self, bridge, edge: Edge, from_name: str, to_name: str, deadline: float
    ) -> tuple[bool, Point | None]:
        destination = self.world.place(to_name).point
        if edge.kind == "walk":
            result = self.router.navigate_to(bridge, destination, deadline=deadline)
            return result.state == NavState.ARRIVED, result.end

        if edge.kind == "portal":
            # Stand on the pad (from_name), fire the trigger, verify the map changed.
            pad = self.world.place(from_name).point
            here = self.router._observe_position(bridge)
            if here is None:
                return False, None
            if here.distance(pad) > PORTAL_PAD_RADIUS_YARDS:
                result = self.router.navigate_to(
                    bridge, pad, deadline=deadline,
                    arrival_radius=PORTAL_PAD_RADIUS_YARDS)
                if result.state != NavState.ARRIVED:
                    return False, result.end
            for attempt in range(PORTAL_FIRE_ATTEMPTS):
                fired = self._fire_trigger(bridge, edge.trigger_id, deadline)
                here = self.router._observe_position(bridge)
                if (here is not None and here.map_id == destination.map_id
                        and here.distance(destination)
                        <= PORTAL_DESTINATION_RADIUS_YARDS):
                    self._trace("journey_portal", trigger=edge.trigger_id,
                                attempts=attempt + 1)
                    return True, here
                if (here is not None and here.map_id == destination.map_id):
                    # Right map, wrong place — an unexpected teleport, not a
                    # portal success; surface it instead of silently accepting.
                    self._trace("journey_portal_offsite", trigger=edge.trigger_id,
                                at=[here.x, here.y, here.z])
                    return False, here
                if not fired:
                    time.sleep(1.0)
            return False, here

        self._trace("journey_edge_unsupported", kind=edge.kind)
        return False, None

    def _fire_trigger(self, bridge, trigger_id: int | None, deadline: float) -> bool:
        """Select an area_trigger action; the frame's trigger bindings admit the stock
        trigger when we stand on its pad."""
        frame = bridge.wait_for_frame(
            timeout_s=min(30.0, max(0.5, deadline - time.monotonic())))
        if frame is None:
            return False
        # Find the binding index for the trigger (or any admitted trigger at the pad).
        index = None
        for row in frame.bindings.triggers:
            if trigger_id is None or row.trigger_id == trigger_id:
                index = row.index
                break
        if index is None:
            return False
        try:
            from wow_sdk.nim_control import FactorizedAction

            action = FactorizedAction(kind="area_trigger", trigger=index)
        except Exception:  # noqa: BLE001
            return False
        request_id = bridge.select_action(frame, action)
        if request_id is None:
            return False
        bridge.wait_for_settlement(frame.frame_id, timeout_s=PORTAL_SETTLE_SECONDS)
        return True

    def _nearest_on_map(self, point: Point):
        candidates = [p for p in self.world.places.values() if p.point.map_id == point.map_id]
        if not candidates:
            return None
        return min(candidates, key=lambda p: p.point.horizontal_distance(point))


def _leg(kind: str, to: Point, status: str, reason: str, route=None) -> dict:
    """Per-leg summary; route legs carry the RouteResult's robustness metrics
    (codex audit #11: they were dropped here, so the benchmark hardcoded zeros)."""
    row = {"kind": kind, "to": [to.map_id, to.x, to.y, to.z], "status": status,
           "reason": reason}
    if route is not None:
        row.update(
            deaths=route.deaths,
            combat_pauses=route.combat_pauses,
            replans=route.replans,
            walked_seconds=round(route.walked_seconds, 1),
            planned_distance=round(route.planned_distance, 1),
        )
    return row
