"""Kalimdor Traverse strategy: keep selecting reachable northbound frontiers."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from environment.navigation import NAV_SEMANTIC_HAZARD

from wowborg.nav.route import NavState, RouteNavigator
from wowborg.nav.world_model import Point

KALIMDOR_MAP_ID = 1
TRAVERSE_START_WORLD_X = -9187.0
TRAVERSE_GOAL_WORLD_X = 6687.333052
FRONTIER_RADIUS_YARDS = 700.0
MIN_FRONTIER_DISTANCE_YARDS = 50.0
MAX_BACKTRACK_YARDS = 100.0
GOAL_RADIUS_YARDS = 8.0
CAT_FORM_SPELL_ID = 768
PROWL_SPELL_IDS = (9913, 6783, 5215)
TRAVEL_FORM_SPELL_ID = 783
PROWL_ROUTE_GUIDEPOINTS = 0
GREAT_LIFT_ENTRIES = (11898, 11899)
GREAT_LIFT_LOWER_DOCK = Point(1, -4677.066, -1853.667, -43.857)
GREAT_LIFT_UPPER_DOCK = Point(1, -4650.066, -1850.482, 85.705)
GREAT_LIFT_UPPER_ROAD = Point(1, -4583.315, -1908.142, 95.58)
GREAT_LIFT_VISIBLE_RANGE = 42.0
GREAT_LIFT_DOCK_Z_SLACK = 2.0
GREAT_LIFT_EXIT_Z = 80.0
GREAT_LIFT_TURN_DEADBAND = 0.20
GREAT_LIFT_INPUT_SECONDS = 0.75
ROAD_ARRIVAL_RADIUS_YARDS = 8.0
ROAD_STALL_SECONDS = 8.0

# Follow the deployed owner's level-51 Tanaris and Thousand Needles road spine
# to the Great Lift lower dock. Great Lift boarding is a separate campaign.
TRAVERSE_ROUTE_PREFIX = (
    ("tanaris-north-road-1", Point(1, -8974.0117, -2741.5291, 41.0118)),
    ("tanaris-north-road-2", Point(1, -8761.0234, -2952.8083, 24.5674)),
    ("tanaris-north-road-3", Point(1, -8548.0352, -3164.0835, 10.1670)),
    ("tanaris-north-road-4", Point(1, -8278.7275, -3284.8706, 23.8400)),
    ("tanaris-north-road-5", Point(1, -8085.3330, -3349.3330, 43.3455)),
    ("tanaris-north-road-6", Point(1, -7866.4028, -3550.8655, 58.3285)),
    ("tanaris-north-road-7", Point(1, -7577.2563, -3602.6570, 15.3188)),
    ("tanaris-north-road-8", Point(1, -7314.9946, -3715.9453, 9.9459)),
    ("tanaris-north-road-9", Point(1, -6948.5264, -3856.7524, 28.9407)),
    ("shimmering-flats-south-ramp", Point(1, -6794.0220, -3953.5276, 100.8641)),
    ("shimmering-flats-south-road", Point(1, -6624.2671, -4050.1333, -41.6139)),
    ("shimmering-flats-road", Point(1, -6239.9995, -4085.3330, -58.0107)),
    ("thousand-needles-east-road-1", Point(1, -6035.5581, -3865.7529, -59.6654)),
    ("thousand-needles-east-road-2", Point(1, -5894.7827, -3611.1252, -58.0235)),
    ("thousand-needles-east-road-3", Point(1, -5866.8999, -3499.5984, -57.5426)),
    ("thousand-needles-central-road-1", Point(1, -5745.3672, -3200.0486, -40.1584)),
    ("thousand-needles-central-road-2", Point(1, -5629.6523, -2928.8188, -44.9830)),
    ("thousand-needles-central-road-3", Point(1, -5504.7778, -2670.9585, -49.1217)),
    ("thousand-needles-west-road-1", Point(1, -5349.2344, -2439.9663, -31.8258)),
    ("thousand-needles-west-road-2", Point(1, -5312.8003, -2325.3333, -31.6509)),
    ("thousand-needles-west-3", Point(1, -5116.142, -1794.543, -55.277)),
    ("great-lift-south-road", Point(1, -4971.3, -1718.92, -59.379)),
    ("great-lift-lower-dock", GREAT_LIFT_LOWER_DOCK),
)


def _observed_lift_at_lower_dock(frame):
    lifts = (
        obj
        for obj in frame.objects
        if obj.entry in GREAT_LIFT_ENTRIES
        and obj.distance <= GREAT_LIFT_VISIBLE_RANGE
        and abs(obj.location.z - GREAT_LIFT_LOWER_DOCK.z)
        <= GREAT_LIFT_DOCK_Z_SLACK
    )
    return min(lifts, key=lambda obj: obj.distance, default=None)


def _steer_toward(bridge, frame, target: Point, *, purpose: str) -> None:
    desired = math.atan2(target.y - frame.location.y, target.x - frame.location.x)
    delta = (desired - frame.location.orientation + math.pi) % (2 * math.pi) - math.pi
    if abs(delta) > GREAT_LIFT_TURN_DEADBAND:
        bridge.select_move_vector(
            frame,
            turn=1.0 if delta > 0 else -1.0,
            duration=min(GREAT_LIFT_INPUT_SECONDS, max(0.15, abs(delta) / math.pi)),
            purpose=purpose,
        )
        return
    bridge.select_move_vector(
        frame,
        forward=1.0,
        duration=GREAT_LIFT_INPUT_SECONDS,
        purpose=purpose,
    )


def _steer_road_leg(bridge, target: Point, *, deadline: float, trace):
    closest = math.inf
    last_progress = time.monotonic()
    while time.monotonic() < deadline and not getattr(bridge, "finished", False):
        frame = bridge.observe()
        if frame is None:
            return None, "no_frame"
        if frame.is_dead or frame.is_ghost:
            return None, "death"
        if frame.in_combat:
            return None, "combat"

        distance = math.dist(
            (frame.location.x, frame.location.y, frame.location.z),
            (target.x, target.y, target.z),
        )
        if distance <= ROAD_ARRIVAL_RADIUS_YARDS:
            return Point(
                frame.location.map_id,
                frame.location.x,
                frame.location.y,
                frame.location.z,
            ), ""
        if distance < closest - 1.0:
            closest = distance
            last_progress = time.monotonic()
        elif time.monotonic() - last_progress >= ROAD_STALL_SECONDS:
            trace("traverse_road_stalled", distance=round(distance, 3))
            return None, "no_progress"

        _steer_toward(
            bridge,
            frame,
            target,
            purpose="follow the authored Traverse road",
        )
    return None, "deadline"


def _select_frontier(graph, *, best_world_x: float, visited: set[str]):
    candidates = [
        node
        for node in graph.nodes
        if node.key not in visited
        and node.distance_from_source >= MIN_FRONTIER_DISTANCE_YARDS
        and node.centroid.x >= best_world_x - MAX_BACKTRACK_YARDS
        and not node.semantic_flags & NAV_SEMANTIC_HAZARD
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda node: (node.centroid.x, node.distance_from_source))


def _activate_prowl(bridge, trace) -> None:
    frame = bridge.observe()
    if frame is None:
        trace("traverse_prowl", activation=0, reason="no_frame")
        return
    if frame.in_combat:
        trace("traverse_prowl", activation=0, reason="in_combat")
        return
    if any(spell_id in frame.active_aura_spell_ids for spell_id in PROWL_SPELL_IDS):
        trace("traverse_prowl", activation=0, reason="already_active")
        return

    if not frame.shapeshift_form_known or frame.shapeshift_form_id != 1:
        request_id = bridge.select_cast_without_target(
            frame,
            CAT_FORM_SPELL_ID,
            purpose="enter Cat Form for stealth Traverse",
        )
        if request_id is None:
            trace("traverse_cat_form", activation=0, reason="spell_unavailable")
            return
        outcome = bridge.wait_for_settlement(frame.frame_id)
        trace(
            "traverse_cat_form",
            activation=1,
            success=outcome is not None and outcome.success,
            detail=outcome.detail if outcome is not None else "unsettled",
        )
        frame = bridge.observe()
        if frame is None or not frame.shapeshift_form_known or frame.shapeshift_form_id != 1:
            trace("traverse_prowl", activation=0, reason="cat_form_not_active")
            return

    prowl_spell_id = next(
        (spell_id for spell_id in PROWL_SPELL_IDS if spell_id in frame.known_spells),
        None,
    )
    if prowl_spell_id is None:
        trace("traverse_prowl", activation=0, reason="spell_unavailable")
        return
    request_id = bridge.select_cast_without_target(
        frame,
        prowl_spell_id,
        purpose="activate Prowl for stealth Traverse",
    )
    if request_id is None:
        trace("traverse_prowl", activation=0, reason="cast_unavailable")
        return
    outcome = bridge.wait_for_settlement(frame.frame_id)
    trace(
        "traverse_prowl",
        activation=1,
        spell_id=prowl_spell_id,
        success=outcome is not None and outcome.success,
        detail=outcome.detail if outcome is not None else "unsettled",
    )


def _activate_travel_form(bridge, trace) -> None:
    frame = bridge.observe()
    if frame is None:
        trace("traverse_travel_form", activation=0, reason="no_frame")
        return
    if (
        frame.shapeshift_form_spell_known
        and frame.shapeshift_form_spell_id == TRAVEL_FORM_SPELL_ID
    ):
        trace("traverse_travel_form", activation=0, reason="already_active")
        return
    request_id = bridge.select_cast_without_target(
        frame,
        TRAVEL_FORM_SPELL_ID,
        purpose="activate Travel Form for speed-first Traverse",
    )
    if request_id is None:
        trace("traverse_travel_form", activation=0, reason="spell_unavailable")
        return
    outcome = bridge.wait_for_settlement(frame.frame_id)
    trace(
        "traverse_travel_form",
        activation=1,
        success=outcome is not None and outcome.success,
        detail=outcome.detail if outcome is not None else "unsettled",
    )


@dataclass
class TraverseStrategy:
    """Advance north over the connected local navmesh until time or goal."""

    best_world_x: float = TRAVERSE_START_WORLD_X
    frontiers_attempted: int = 0
    frontiers_arrived: int = 0
    route_failures: int = 0
    route_guidepoints_arrived: int = 0
    route_prefix_abandoned: bool = False
    great_lift_boarded: bool = False
    great_lift_completed: bool = False
    great_lift_upper_road_arrived: bool = False
    visited_frontiers: set[str] = field(default_factory=set)

    def summary(self) -> dict[str, object]:
        northing = max(0.0, self.best_world_x - TRAVERSE_START_WORLD_X)
        full_distance = TRAVERSE_GOAL_WORLD_X - TRAVERSE_START_WORLD_X
        return {
            "best_world_x": round(self.best_world_x, 3),
            "northing_yards": round(northing, 3),
            "goal_fraction": round(min(1.0, northing / full_distance), 4),
            "reached_goal": self.best_world_x >= TRAVERSE_GOAL_WORLD_X,
            "frontiers_attempted": self.frontiers_attempted,
            "frontiers_arrived": self.frontiers_arrived,
            "route_failures": self.route_failures,
            "route_guidepoints_arrived": self.route_guidepoints_arrived,
            "route_prefix_completed": (
                self.route_guidepoints_arrived == len(TRAVERSE_ROUTE_PREFIX)
            ),
            "great_lift_boarded": self.great_lift_boarded,
            "great_lift_completed": self.great_lift_completed,
            "great_lift_upper_road_arrived": self.great_lift_upper_road_arrived,
        }

    def run(self, bridge, *, until: float) -> None:
        tracer = getattr(bridge, "_tracer", None)

        def trace(kind: str, **payload) -> None:
            if tracer is not None:
                tracer.emit(kind, **payload)

        navigator = RouteNavigator(tracer=tracer)
        trace(
            "strategy_start",
            strategy="traverse",
            map_id=KALIMDOR_MAP_ID,
            goal_world_x=TRAVERSE_GOAL_WORLD_X,
        )
        while time.monotonic() < until and not getattr(bridge, "finished", False):
            if self.route_guidepoints_arrived < PROWL_ROUTE_GUIDEPOINTS:
                _activate_prowl(bridge, trace)
            else:
                _activate_travel_form(bridge, trace)
            here = navigator._observe_position(bridge)
            if here is None:
                time.sleep(1.0)
                continue
            if here.map_id != KALIMDOR_MAP_ID:
                trace("traverse_stopped", reason="left_kalimdor", map_id=here.map_id)
                break

            previous_best = self.best_world_x
            self.best_world_x = max(self.best_world_x, here.x)
            if self.best_world_x > previous_best:
                trace(
                    "traverse_progress",
                    world_x=round(here.x, 3),
                    **self.summary(),
                )
            if here.x >= TRAVERSE_GOAL_WORLD_X - GOAL_RADIUS_YARDS:
                self.best_world_x = max(self.best_world_x, TRAVERSE_GOAL_WORLD_X)
                break

            if (
                not self.route_prefix_abandoned
                and self.route_guidepoints_arrived < len(TRAVERSE_ROUTE_PREFIX)
            ):
                name, target = TRAVERSE_ROUTE_PREFIX[self.route_guidepoints_arrived]
                trace(
                    "traverse_route_guidepoint",
                    activation=self.route_guidepoints_arrived + 1,
                    name=name,
                    target=[target.x, target.y, target.z],
                )
                end, failure_reason = _steer_road_leg(
                    bridge,
                    target,
                    deadline=until,
                    trace=trace,
                )
                if end is not None:
                    self.best_world_x = max(self.best_world_x, end.x)
                    self.route_guidepoints_arrived += 1
                    trace(
                        "traverse_route_guidepoint_arrived",
                        activation=self.route_guidepoints_arrived,
                        name=name,
                        world_x=round(end.x, 3),
                    )
                    if self.route_guidepoints_arrived == len(TRAVERSE_ROUTE_PREFIX):
                        trace(
                            "traverse_great_lift_arrived",
                            world_x=round(end.x, 3),
                            world_y=round(end.y, 3),
                            world_z=round(end.z, 3),
                        )
                        break
                else:
                    self.route_failures += 1
                    self.route_prefix_abandoned = True
                    trace(
                        "traverse_route_guidepoint_failed",
                        activation=self.route_guidepoints_arrived + 1,
                        name=name,
                        reason=failure_reason,
                    )
                continue

            if (
                self.route_guidepoints_arrived == len(TRAVERSE_ROUTE_PREFIX)
                and not self.great_lift_completed
            ):
                frame = bridge.observe()
                if frame is None:
                    time.sleep(1.0)
                    continue
                if frame.on_transport:
                    if not self.great_lift_boarded:
                        self.great_lift_boarded = True
                        trace(
                            "traverse_great_lift_boarded",
                            world_z=round(frame.location.z, 3),
                        )
                    if frame.location.z >= GREAT_LIFT_EXIT_Z:
                        _steer_toward(
                            bridge,
                            frame,
                            GREAT_LIFT_UPPER_DOCK,
                            purpose="walk off the observed Great Lift at its upper dock",
                        )
                        trace(
                            "traverse_great_lift_disembarking",
                            world_z=round(frame.location.z, 3),
                        )
                    else:
                        bridge.select_wait(frame)
                    continue

                if frame.location.z >= GREAT_LIFT_EXIT_Z:
                    self.great_lift_completed = True
                    trace(
                        "traverse_great_lift_completed",
                        world_z=round(frame.location.z, 3),
                    )
                    continue

                lift = _observed_lift_at_lower_dock(frame)
                if lift is None:
                    bridge.select_wait(frame)
                    trace("traverse_great_lift_waiting")
                    continue
                _steer_toward(
                    bridge,
                    frame,
                    Point(
                        frame.location.map_id,
                        lift.location.x,
                        lift.location.y,
                        lift.location.z,
                    ),
                    purpose="board the observed Great Lift through ordinary movement",
                )
                trace(
                    "traverse_great_lift_boarding",
                    lift_entry=lift.entry,
                    lift_guid=lift.guid,
                    lift_distance=round(lift.distance, 3),
                    lift_z=round(lift.location.z, 3),
                )
                continue

            if self.great_lift_completed and not self.great_lift_upper_road_arrived:
                result = navigator.navigate_to(
                    bridge,
                    GREAT_LIFT_UPPER_ROAD,
                    deadline=until,
                    engage_attackers=False,
                )
                if result.end is not None:
                    self.best_world_x = max(self.best_world_x, result.end.x)
                if result.state == NavState.ARRIVED:
                    self.great_lift_upper_road_arrived = True
                    trace("traverse_great_lift_upper_road_arrived")
                else:
                    self.route_failures += 1
                    trace(
                        "traverse_great_lift_upper_road_failed",
                        reason=result.reason,
                    )
                continue

            graph = bridge.local_navigation_graph(
                here,
                radius=FRONTIER_RADIUS_YARDS,
            )
            if not graph.ok:
                trace(
                    "traverse_stopped",
                    reason="local_graph_unavailable",
                    status=graph.status,
                    detail=graph.message,
                )
                break
            frontier = _select_frontier(
                graph,
                best_world_x=self.best_world_x,
                visited=self.visited_frontiers,
            )
            if frontier is None:
                trace("traverse_stopped", reason="no_untried_northbound_frontier")
                break

            self.visited_frontiers.add(frontier.key)
            self.frontiers_attempted += 1
            target = Point(
                KALIMDOR_MAP_ID,
                min(frontier.centroid.x, TRAVERSE_GOAL_WORLD_X),
                frontier.centroid.y,
                frontier.centroid.z,
            )
            trace(
                "traverse_frontier",
                activation=self.frontiers_attempted,
                key=frontier.key,
                target=[target.x, target.y, target.z],
                northing_gain=round(target.x - here.x, 3),
            )
            result = navigator.navigate_to(
                bridge,
                target,
                deadline=until,
                engage_attackers=False,
            )
            if result.end is not None:
                self.best_world_x = max(self.best_world_x, result.end.x)
            if result.state == NavState.ARRIVED:
                self.frontiers_arrived += 1
            else:
                self.route_failures += 1
                trace(
                    "traverse_route_failed",
                    key=frontier.key,
                    reason=result.reason,
                    failures=self.route_failures,
                )

        trace("strategy_end", strategy="traverse", **self.summary())
