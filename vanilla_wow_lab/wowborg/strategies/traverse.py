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
TRAVERSE_INPUT_SECONDS = 0.75
ROAD_ARRIVAL_RADIUS_YARDS = 8.0
ROAD_PASS_LATERAL_YARDS = 60.0
ROAD_PASS_VERTICAL_YARDS = 10.0
ROAD_PASS_NORTHING_SLACK_YARDS = 20.0
ROAD_STALL_SECONDS = 8.0
ROAD_UNSTICK_ATTEMPTS = 2
ROAD_SETTLE_PAUSE_INTERVAL = 8
ROAD_HAZARD_ENTER_YARDS = 30.0
ROAD_HAZARD_EXIT_YARDS = 40.0
ROAD_HAZARD_LOOKAHEAD_YARDS = 60.0
ROAD_HAZARD_RESIDENT_RADIUS_YARDS = 30.0
ROAD_HAZARD_CORRIDOR_YARDS = 18.0
ROAD_HAZARD_TRACK_YARDS = 80.0
ROAD_HAZARD_FORWARD_YARDS = 20.0
ROAD_HAZARD_LATERAL_YARDS = (30.0, 45.0, 60.0)
ROAD_HAZARD_MIN_CLEARANCE_YARDS = 20.0
ROAD_HAZARD_HOLD_RADIUS_YARDS = 2.0
ROAD_HAZARD_SWITCH_MARGIN_YARDS = 5.0
ROAD_EXACT_GUIDEPOINTS = frozenset(
    {
        "tanaris-road-8-detour-west",
        "tanaris-road-8-detour-south",
        "tanaris-road-8-detour-east-turn",
        "tanaris-road-8-detour-east",
        "shimmering-flats-ramp-approach",
        "shimmering-flats-ramp-turn",
        "shimmering-flats-ramp-base",
        "shimmering-flats-ramp-rise",
        "shimmering-flats-ramp-crest",
        "great-lift-lower-dock",
    }
)

# Follow the deployed owner's level-51 Tanaris and Thousand Needles road spine
# to the Great Lift lower dock. Great Lift boarding is a separate campaign.
TRAVERSE_ROUTE_PREFIX = (
    # The current host drops the next Observation when the opening movement
    # prefix turns east from the exact spawn. A short southwest prefix settles
    # normally and leaves the canonical road reachable on the following frame.
    ("tanaris-movement-bootstrap", Point(1, -9200.0, -2545.0, 13.5)),
    ("tanaris-north-road-1", Point(1, -8974.0117, -2741.5291, 41.0118)),
    ("tanaris-north-road-2", Point(1, -8761.0234, -2952.8083, 24.5674)),
    ("tanaris-north-road-3", Point(1, -8548.0352, -3164.0835, 10.1670)),
    # Keep v100's proven center-road trajectory until south of v101's Dunemaul
    # Brute, then cross east through the gap north of v100's Glasshide Gazer.
    ("tanaris-brute-gate-south", Point(1, -8401.8008, -3220.6948, 11.3410)),
    ("tanaris-gazer-gate-north", Point(1, -8300.0, -3220.0, 17.4170)),
    ("tanaris-north-road-4", Point(1, -8278.7275, -3284.8706, 23.8400)),
    ("tanaris-north-road-5", Point(1, -8085.3330, -3349.3330, 43.3455)),
    ("tanaris-north-road-6", Point(1, -7866.4028, -3550.8655, 58.3285)),
    ("tanaris-north-road-7", Point(1, -7577.2563, -3602.6570, 15.3188)),
    ("tanaris-north-road-8", Point(1, -7314.9946, -3715.9453, 9.9459)),
    # The Detour corridor bends around impassable terrain here. These exact
    # anchors preserve the bend even after hazard avoidance displaces us north
    # or south; northing-pass semantics would incorrectly skip the west anchor.
    ("tanaris-road-8-detour-west", Point(1, -7193.6000, -3733.3330, 8.9030)),
    ("tanaris-road-8-detour-south", Point(1, -7172.2670, -3753.6000, 9.0610)),
    ("tanaris-road-8-detour-east-turn", Point(1, -7128.8000, -3767.2000, 9.8100)),
    ("tanaris-road-8-detour-east", Point(1, -7096.5330, -3795.4670, 9.3110)),
    ("tanaris-north-road-9", Point(1, -6948.5264, -3856.7524, 28.9407)),
    ("shimmering-flats-ramp-approach", Point(1, -6905.4900, -3869.4600, 38.8900)),
    ("shimmering-flats-ramp-turn", Point(1, -6889.5900, -3885.4700, 47.9500)),
    ("shimmering-flats-ramp-base", Point(1, -6884.0000, -3900.0000, 53.6400)),
    ("shimmering-flats-ramp-rise", Point(1, -6875.8500, -3912.0900, 100.0800)),
    ("shimmering-flats-ramp-crest", Point(1, -6848.0000, -3925.3300, 124.6400)),
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


def _steer_toward(
    bridge,
    frame,
    target: Point,
    *,
    purpose: str,
    precise_arrival: bool = False,
) -> None:
    desired = math.atan2(target.y - frame.location.y, target.x - frame.location.x)
    delta = (desired - frame.location.orientation + math.pi) % (2 * math.pi) - math.pi
    turn_deadband = math.pi / 4
    if abs(delta) > turn_deadband:
        bridge.select_move_vector(
            frame,
            forward=0.0,
            turn=1.0 if delta > 0 else -1.0,
            duration=0.25,
            purpose=purpose,
        )
        return
    bridge.select_move_vector(
        frame,
        forward=1.0,
        strafe=(
            (1.0 if delta > 0 else -1.0)
            if abs(delta) > math.pi / 8
            else 0.0
        ),
        duration=0.25 if precise_arrival else TRAVERSE_INPUT_SECONDS,
        purpose=purpose,
    )


def _point_segment_distance(
    point_x: float,
    point_y: float,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
) -> float:
    segment_x = end_x - start_x
    segment_y = end_y - start_y
    segment_length_squared = segment_x * segment_x + segment_y * segment_y
    if segment_length_squared == 0:
        return math.hypot(point_x - start_x, point_y - start_y)
    progress = max(
        0.0,
        min(
            1.0,
            (
                (point_x - start_x) * segment_x
                + (point_y - start_y) * segment_y
            )
            / segment_length_squared,
        ),
    )
    return math.hypot(
        point_x - (start_x + progress * segment_x),
        point_y - (start_y + progress * segment_y),
    )


def _unit_path(unit) -> tuple[float, float, float, float]:
    if (
        unit.movement_destination_known
        and unit.movement_destination.map_id == unit.location.map_id
    ):
        return (
            unit.location.x,
            unit.location.y,
            unit.movement_destination.x,
            unit.movement_destination.y,
        )
    return unit.location.x, unit.location.y, unit.location.x, unit.location.y


def _segment_clearance(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    unit,
) -> float:
    unit_start_x, unit_start_y, unit_end_x, unit_end_y = _unit_path(unit)
    route_x = end_x - start_x
    route_y = end_y - start_y
    unit_x = unit_end_x - unit_start_x
    unit_y = unit_end_y - unit_start_y
    cross = route_x * unit_y - route_y * unit_x
    if cross != 0:
        offset_x = unit_start_x - start_x
        offset_y = unit_start_y - start_y
        route_progress = (offset_x * unit_y - offset_y * unit_x) / cross
        unit_progress = (offset_x * route_y - offset_y * route_x) / cross
        if 0.0 <= route_progress <= 1.0 and 0.0 <= unit_progress <= 1.0:
            return 0.0
    return min(
        _point_segment_distance(
            unit_start_x, unit_start_y, start_x, start_y, end_x, end_y
        ),
        _point_segment_distance(
            unit_end_x, unit_end_y, start_x, start_y, end_x, end_y
        ),
        _point_segment_distance(
            start_x, start_y, unit_start_x, unit_start_y, unit_end_x, unit_end_y
        ),
        _point_segment_distance(
            end_x, end_y, unit_start_x, unit_start_y, unit_end_x, unit_end_y
        ),
    )


def _hazard_avoidance_target(
    frame,
    target: Point,
    *,
    side: float | None,
    active_holding_guids: set[str],
):
    route_x = target.x - frame.location.x
    route_y = target.y - frame.location.y
    route_length = math.hypot(route_x, route_y)
    if route_length == 0:
        return target, None, [], [], {}, {}, False
    route_x /= route_length
    route_y /= route_length
    left_x, left_y = -route_y, route_x
    detection_radius = (
        ROAD_HAZARD_EXIT_YARDS if side is not None else ROAD_HAZARD_ENTER_YARDS
    )
    tracked = [
        unit
        for unit in frame.units
        if unit.player_reaction_hostile
        and not unit.is_dead
        and unit.distance <= ROAD_HAZARD_TRACK_YARDS
    ]
    safe_active_holding_guids = {
        unit.guid
        for unit in tracked
        if unit.guid in active_holding_guids
        and unit.movement_destination_known
        and _point_segment_distance(
            frame.location.x,
            frame.location.y,
            *_unit_path(unit),
        )
        >= ROAD_HAZARD_MIN_CLEARANCE_YARDS
    }
    immediate_end_x = frame.location.x + route_x * detection_radius
    immediate_end_y = frame.location.y + route_y * detection_radius
    immediate_hazards = [
        unit
        for unit in tracked
        if unit.guid not in safe_active_holding_guids
        and _segment_clearance(
            frame.location.x,
            frame.location.y,
            immediate_end_x,
            immediate_end_y,
            unit,
        )
        <= ROAD_HAZARD_CORRIDOR_YARDS
    ]
    lookahead_end_x = frame.location.x + route_x * ROAD_HAZARD_LOOKAHEAD_YARDS
    lookahead_end_y = frame.location.y + route_y * ROAD_HAZARD_LOOKAHEAD_YARDS
    lookahead_hazards = [
        unit
        for unit in tracked
        if _segment_clearance(
            frame.location.x,
            frame.location.y,
            lookahead_end_x,
            lookahead_end_y,
            unit,
        )
        <= ROAD_HAZARD_CORRIDOR_YARDS
    ]
    immediate_guids = {unit.guid for unit in immediate_hazards}
    threatening_crossings = [
        unit
        for unit in lookahead_hazards
        if unit.guid not in immediate_guids
        and unit.movement_destination_known
        and _point_segment_distance(
            frame.location.x,
            frame.location.y,
            *_unit_path(unit),
        )
        < ROAD_HAZARD_MIN_CLEARANCE_YARDS
    ]
    resident_hazards = [
        unit
        for unit in lookahead_hazards
        if unit.movement_destination_known
        and math.dist(
            (unit.movement_destination.x, unit.movement_destination.y),
            (target.x, target.y),
        )
        <= ROAD_HAZARD_RESIDENT_RADIUS_YARDS
    ]
    if threatening_crossings and not immediate_hazards and not resident_hazards:
        return (
            target,
            None,
            threatening_crossings,
            tracked,
            {},
            {},
            True,
        )
    hazards_by_guid = {
        unit.guid: unit
        for unit in (*immediate_hazards, *resident_hazards)
    }
    hazards = list(hazards_by_guid.values())
    if not hazards:
        return target, None, [], tracked, {}, {}, False

    def clearance(candidate_side: float, lateral_yards: float) -> float:
        candidate_x = (
            frame.location.x
            + route_x * ROAD_HAZARD_FORWARD_YARDS
            + left_x * candidate_side * lateral_yards
        )
        candidate_y = (
            frame.location.y
            + route_y * ROAD_HAZARD_FORWARD_YARDS
            + left_y * candidate_side * lateral_yards
        )
        return min(
            _segment_clearance(
                frame.location.x,
                frame.location.y,
                candidate_x,
                candidate_y,
                unit,
            )
            for unit in tracked
        )

    candidate_clearances = {
        side: {
            lateral_yards: clearance(side, lateral_yards)
            for lateral_yards in ROAD_HAZARD_LATERAL_YARDS
        }
        for side in (-1.0, 1.0)
    }

    def choose_lateral(candidate_side: float) -> float:
        safe = [
            lateral_yards
            for lateral_yards, candidate_clearance in candidate_clearances[
                candidate_side
            ].items()
            if candidate_clearance >= ROAD_HAZARD_MIN_CLEARANCE_YARDS
        ]
        if safe:
            return min(safe)
        return max(
            ROAD_HAZARD_LATERAL_YARDS,
            key=lambda lateral_yards: (
                candidate_clearances[candidate_side][lateral_yards],
                -lateral_yards,
            ),
        )

    lateral_by_side = {
        candidate_side: choose_lateral(candidate_side)
        for candidate_side in (-1.0, 1.0)
    }
    clearances = {
        candidate_side: candidate_clearances[candidate_side][
            lateral_by_side[candidate_side]
        ]
        for candidate_side in (-1.0, 1.0)
    }
    if side is None:
        side = max((-1.0, 1.0), key=clearances.get)
    else:
        other_side = -side
        if (
            clearances[side] < ROAD_HAZARD_MIN_CLEARANCE_YARDS
            and clearances[other_side]
            >= clearances[side] + ROAD_HAZARD_SWITCH_MARGIN_YARDS
        ):
            side = other_side

    return (
        Point(
            frame.location.map_id,
            frame.location.x
            + route_x * ROAD_HAZARD_FORWARD_YARDS
            + left_x * side * lateral_by_side[side],
            frame.location.y
            + route_y * ROAD_HAZARD_FORWARD_YARDS
            + left_y * side * lateral_by_side[side],
            frame.location.z,
        ),
        side,
        hazards,
        tracked,
        clearances,
        lateral_by_side,
        False,
    )


def _combat_escape_target(frame, target: Point) -> Point:
    attackers = [
        unit
        for unit in frame.units
        if unit.player_reaction_hostile
        and not unit.is_dead
        and unit.target_guid_known
        and unit.target_guid == frame.player_guid
    ]
    if not attackers:
        return target
    away_x = sum(frame.location.x - unit.location.x for unit in attackers)
    away_y = sum(frame.location.y - unit.location.y for unit in attackers)
    away_length = math.hypot(away_x, away_y)
    if away_length == 0:
        return target
    return Point(
        frame.location.map_id,
        frame.location.x + away_x / away_length * ROAD_HAZARD_EXIT_YARDS,
        frame.location.y + away_y / away_length * ROAD_HAZARD_EXIT_YARDS,
        frame.location.z,
    )


def _hazard_evasion_target(frame, hazards, target: Point) -> Point:
    if not hazards:
        return target
    away_x = sum(
        (frame.location.x - unit.location.x) / max(1.0, unit.distance)
        for unit in hazards
    )
    away_y = sum(
        (frame.location.y - unit.location.y) / max(1.0, unit.distance)
        for unit in hazards
    )
    away_length = math.hypot(away_x, away_y)
    if away_length == 0:
        return target
    return Point(
        frame.location.map_id,
        frame.location.x + away_x / away_length * ROAD_HAZARD_EXIT_YARDS,
        frame.location.y + away_y / away_length * ROAD_HAZARD_EXIT_YARDS,
        frame.location.z,
    )


@dataclass
class HazardAvoidanceState:
    side: float | None = None
    holding: bool = False
    holding_guids: set[str] = field(default_factory=set)
    evading: bool = False
    retreating: bool = False
    retreat_blocked: bool = False
    retreat_stalled_pulses: int = 0
    safe_point: Point | None = None
    settled_pulses: int = 0


def _steer_road_leg(
    bridge,
    target: Point,
    *,
    deadline: float,
    trace,
    avoidance: HazardAvoidanceState,
    allow_northing_pass: bool,
):
    settle_pause_interval = (
        1 if not allow_northing_pass else ROAD_SETTLE_PAUSE_INTERVAL
    )
    closest = math.inf
    last_progress = time.monotonic()
    road_unstick_attempts = 0
    combat_escape_started: float | None = None
    while time.monotonic() < deadline and not getattr(bridge, "finished", False):
        frame = bridge.observe()
        if frame is None:
            return None, "no_frame"
        if frame.is_dead or frame.is_ghost:
            return None, "death"
        if frame.in_combat:
            if combat_escape_started is None:
                combat_escape_started = time.monotonic()
                visible_attackers = [
                    {
                        "entry": unit.entry,
                        "name": unit.name,
                        "distance": round(unit.distance, 3),
                    }
                    for unit in frame.units
                    if unit.player_reaction_hostile
                    and not unit.is_dead
                    and unit.target_guid_known
                    and unit.target_guid == frame.player_guid
                ]
                trace(
                    "traverse_combat_escape",
                    activation=1,
                    health=frame.health,
                    max_health=frame.max_health,
                    attacker_count=frame.threat.attacker_count,
                    visible_attackers=visible_attackers,
                )
        elif combat_escape_started is not None:
            trace(
                "traverse_combat_escape_ended",
                activation=1,
                duration_seconds=round(time.monotonic() - combat_escape_started, 3),
                health=frame.health,
                max_health=frame.max_health,
            )
            combat_escape_started = None

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
        lateral_distance = abs(frame.location.y - target.y)
        vertical_distance = abs(frame.location.z - target.z)
        if (
            allow_northing_pass
            and frame.location.x >= target.x - ROAD_PASS_NORTHING_SLACK_YARDS
            and lateral_distance <= ROAD_PASS_LATERAL_YARDS
            and vertical_distance <= ROAD_PASS_VERTICAL_YARDS
        ):
            trace(
                "traverse_road_guidepoint_passed",
                activation=1,
                distance=round(distance, 3),
                lateral_distance=round(lateral_distance, 3),
                vertical_distance=round(vertical_distance, 3),
            )
            return Point(
                frame.location.map_id,
                frame.location.x,
                frame.location.y,
                frame.location.z,
            ), ""
        if distance < closest - 1.0:
            closest = distance
            last_progress = time.monotonic()
            road_unstick_attempts = 0
        elif time.monotonic() - last_progress >= ROAD_STALL_SECONDS:
            if road_unstick_attempts >= ROAD_UNSTICK_ATTEMPTS:
                trace(
                    "traverse_road_stalled",
                    activation=1,
                    distance=round(distance, 3),
                    recovery_exhausted=True,
                )
                return None, "no_progress"
            side = 1.0 if road_unstick_attempts == 0 else -1.0
            trace(
                "traverse_road_unstick",
                activation=1,
                attempt=road_unstick_attempts + 1,
                side="left" if side > 0 else "right",
                distance=round(distance, 3),
            )
            bridge.select_move_vector(
                frame,
                forward=1.0,
                strafe=side,
                duration=TRAVERSE_INPUT_SECONDS,
                purpose="sidestep a blocked Traverse road translation",
            )
            settle_frame = bridge.observe()
            if settle_frame is None:
                return None, "no_frame"
            movement = math.dist(
                (frame.location.x, frame.location.y),
                (settle_frame.location.x, settle_frame.location.y),
            )
            road_unstick_attempts += 1
            trace(
                "traverse_road_unstick_settled",
                activation=1,
                attempt=road_unstick_attempts,
                movement=round(movement, 3),
            )
            if movement >= 0.5:
                closest = math.inf
                last_progress = time.monotonic()
                road_unstick_attempts = 0
            avoidance.settled_pulses += 1
            if avoidance.settled_pulses % settle_pause_interval == 0:
                bridge.select_wait(settle_frame)
                trace("traverse_road_settle_pause", frame_id=settle_frame.frame_id)
            trace("traverse_road_pulse_settled", frame_id=settle_frame.frame_id)
            continue

        if frame.in_combat:
            steering_target = _combat_escape_target(frame, target)
            next_avoidance_side = avoidance.side
            hazards = []
            should_hold = False
        else:
            (
                steering_target,
                next_avoidance_side,
                hazards,
                tracked_hazards,
                side_clearances,
                side_lateral_yards,
                should_hold,
            ) = _hazard_avoidance_target(
                frame,
                target,
                side=avoidance.side,
                active_holding_guids=avoidance.holding_guids,
            )
        if should_hold:
            if not avoidance.holding:
                trace(
                    "traverse_hazard_hold",
                    activation=1,
                    hazards=[
                        {
                            "entry": unit.entry,
                            "name": unit.name,
                            "distance": round(unit.distance, 3),
                            "destination": [
                                round(unit.movement_destination.x, 3),
                                round(unit.movement_destination.y, 3),
                            ],
                        }
                        for unit in hazards
                    ],
                )
            if avoidance.side is not None:
                trace("traverse_hazard_avoidance_ended", activation=1, reason="hold")
            if avoidance.evading:
                trace("traverse_hazard_evasion_ended", activation=1, reason="hold")
            if avoidance.retreating:
                trace("traverse_hazard_retreat_ended", activation=1, reason="hold")
            avoidance.holding = True
            avoidance.holding_guids = {unit.guid for unit in hazards}
            avoidance.side = None
            avoidance.evading = False
            avoidance.retreating = False
            avoidance.retreat_blocked = False
            avoidance.safe_point = Point(
                frame.location.map_id,
                frame.location.x,
                frame.location.y,
                frame.location.z,
            )
            last_progress = time.monotonic()
            bridge.select_wait(frame)
            trace("traverse_hazard_hold_pulse", frame_id=frame.frame_id)
            continue
        if avoidance.holding:
            trace("traverse_hazard_hold_ended", activation=1)
            avoidance.holding = False
            avoidance.holding_guids = set()
        if next_avoidance_side is not None and avoidance.side is None:
            trace(
                "traverse_hazard_avoidance",
                activation=1,
                side="left" if next_avoidance_side > 0 else "right",
                side_clearances={
                    "right": round(side_clearances[-1.0], 3),
                    "left": round(side_clearances[1.0], 3),
                },
                side_lateral_yards={
                    "right": side_lateral_yards[-1.0],
                    "left": side_lateral_yards[1.0],
                },
                hazards=[
                    {
                        "entry": unit.entry,
                        "name": unit.name,
                        "distance": round(unit.distance, 3),
                        "location": [
                            round(unit.location.x, 3),
                            round(unit.location.y, 3),
                            round(unit.location.z, 3),
                        ],
                    }
                    for unit in hazards
                ],
                tracked_hazards=[
                    {
                        "entry": unit.entry,
                        "name": unit.name,
                        "distance": round(unit.distance, 3),
                        "moving": unit.movement_destination_known,
                        "destination": (
                            [
                                round(unit.movement_destination.x, 3),
                                round(unit.movement_destination.y, 3),
                            ]
                            if unit.movement_destination_known
                            else None
                        ),
                    }
                    for unit in tracked_hazards
                ],
                resident_blocker_count=sum(
                    unit.movement_destination_known
                    and math.dist(
                        (
                            unit.movement_destination.x,
                            unit.movement_destination.y,
                        ),
                        (target.x, target.y),
                    )
                    <= ROAD_HAZARD_RESIDENT_RADIUS_YARDS
                    for unit in hazards
                ),
            )
        elif next_avoidance_side is None and avoidance.side is not None:
            trace("traverse_hazard_avoidance_ended", activation=1)
        elif (
            next_avoidance_side is not None
            and avoidance.side is not None
            and next_avoidance_side != avoidance.side
        ):
            trace(
                "traverse_hazard_avoidance_switched",
                activation=1,
                side="left" if next_avoidance_side > 0 else "right",
                side_clearances={
                    "right": round(side_clearances[-1.0], 3),
                    "left": round(side_clearances[1.0], 3),
                },
                side_lateral_yards={
                    "right": side_lateral_yards[-1.0],
                    "left": side_lateral_yards[1.0],
                },
            )
        avoidance.side = next_avoidance_side

        unsafe = (
            not frame.in_combat
            and avoidance.side is not None
            and side_clearances[avoidance.side]
            < ROAD_HAZARD_MIN_CLEARANCE_YARDS
        )
        if avoidance.side is None and not avoidance.retreating:
            avoidance.retreat_blocked = False
            avoidance.safe_point = Point(
                frame.location.map_id,
                frame.location.x,
                frame.location.y,
                frame.location.z,
            )
        retreat_distance = (
            math.dist(
                (frame.location.x, frame.location.y),
                (avoidance.safe_point.x, avoidance.safe_point.y),
            )
            if (unsafe or avoidance.retreating) and avoidance.safe_point is not None
            else 0.0
        )
        should_retreat = (
            not avoidance.evading
            and not avoidance.retreat_blocked
            and (unsafe or avoidance.retreating)
            and retreat_distance > ROAD_HAZARD_HOLD_RADIUS_YARDS
        )
        should_evade = unsafe and not should_retreat
        if should_evade:
            if avoidance.retreating:
                trace("traverse_hazard_retreat_ended", activation=1)
                avoidance.retreating = False
            if not avoidance.evading:
                trace(
                    "traverse_hazard_evasion",
                    activation=1,
                    side="left" if avoidance.side > 0 else "right",
                    clearance=round(side_clearances[avoidance.side], 3),
                )
                avoidance.evading = True
            last_progress = time.monotonic()
            steering_target = _hazard_evasion_target(frame, hazards, target)
        elif avoidance.evading:
            trace("traverse_hazard_evasion_ended", activation=1)
            avoidance.evading = False
            avoidance.retreat_blocked = False
            avoidance.safe_point = Point(
                frame.location.map_id,
                frame.location.x,
                frame.location.y,
                frame.location.z,
            )
        if should_retreat:
            if not avoidance.retreating:
                trace(
                    "traverse_hazard_retreat",
                    activation=1,
                    clearance=round(side_clearances[avoidance.side], 3),
                    retreat_distance=round(retreat_distance, 3),
                    safe_point=[
                        round(avoidance.safe_point.x, 3),
                        round(avoidance.safe_point.y, 3),
                        round(avoidance.safe_point.z, 3),
                    ],
                )
                avoidance.retreating = True
            last_progress = time.monotonic()
            steering_target = avoidance.safe_point
        elif avoidance.retreating:
            trace("traverse_hazard_retreat_ended", activation=1)
            avoidance.retreating = False

        if frame.in_combat:
            steering_purpose = "flee directly away from current Traverse attackers"
        elif should_retreat:
            steering_purpose = "retreat to the last safe Traverse holding point"
        elif should_evade:
            steering_purpose = "move away from hazards at the Traverse holding point"
        elif hazards:
            steering_purpose = "steer around visible Traverse hazards"
        else:
            steering_purpose = (
                "steer the canonical Traverse road after movement bootstrap"
            )
        _steer_toward(
            bridge,
            frame,
            steering_target,
            purpose=steering_purpose,
            precise_arrival=(
                should_retreat
                or should_evade
                or distance <= ROAD_HAZARD_FORWARD_YARDS
            ),
        )
        settle_frame = bridge.observe()
        if settle_frame is None:
            return None, "no_frame"
        if should_retreat:
            retreat_progress = math.dist(
                (frame.location.x, frame.location.y),
                (settle_frame.location.x, settle_frame.location.y),
            )
            if retreat_progress < 0.5:
                avoidance.retreat_stalled_pulses += 1
            else:
                avoidance.retreat_stalled_pulses = 0
            if avoidance.retreat_stalled_pulses >= 3:
                trace(
                    "traverse_hazard_retreat_blocked",
                    activation=1,
                    safe_point=[
                        round(avoidance.safe_point.x, 3),
                        round(avoidance.safe_point.y, 3),
                        round(avoidance.safe_point.z, 3),
                    ],
                    retreat_distance=round(retreat_distance, 3),
                )
                avoidance.retreating = False
                avoidance.retreat_blocked = True
                avoidance.retreat_stalled_pulses = 0
        else:
            avoidance.retreat_stalled_pulses = 0
        avoidance.settled_pulses += 1
        if avoidance.settled_pulses % settle_pause_interval == 0:
            bridge.select_wait(settle_frame)
            trace("traverse_road_settle_pause", frame_id=settle_frame.frame_id)
        trace("traverse_road_pulse_settled", frame_id=settle_frame.frame_id)
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
    hazard_avoidance: HazardAvoidanceState = field(
        default_factory=HazardAvoidanceState
    )
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
                if self.route_guidepoints_arrived > 0:
                    end, failure_reason = _steer_road_leg(
                        bridge,
                        target,
                        deadline=until,
                        trace=trace,
                        avoidance=self.hazard_avoidance,
                        allow_northing_pass=name not in ROAD_EXACT_GUIDEPOINTS,
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
                safe_resume = (
                    (lambda: _activate_prowl(bridge, trace))
                    if self.route_guidepoints_arrived < PROWL_ROUTE_GUIDEPOINTS
                    else (lambda: _activate_travel_form(bridge, trace))
                )
                result = navigator.navigate_to(
                    bridge,
                    target,
                    deadline=until,
                    on_safe_resume=safe_resume,
                    engage_attackers=False,
                )
                if result.end is not None:
                    self.best_world_x = max(self.best_world_x, result.end.x)
                if result.state == NavState.ARRIVED:
                    self.route_guidepoints_arrived += 1
                    trace(
                        "traverse_route_guidepoint_arrived",
                        activation=self.route_guidepoints_arrived,
                        name=name,
                        world_x=(round(result.end.x, 3) if result.end else None),
                    )
                    if self.route_guidepoints_arrived == len(TRAVERSE_ROUTE_PREFIX):
                        trace(
                            "traverse_great_lift_arrived",
                            world_x=(round(result.end.x, 3) if result.end else None),
                            world_y=(round(result.end.y, 3) if result.end else None),
                            world_z=(round(result.end.z, 3) if result.end else None),
                        )
                        break
                else:
                    self.route_failures += 1
                    self.route_prefix_abandoned = True
                    trace(
                        "traverse_route_guidepoint_failed",
                        activation=self.route_guidepoints_arrived + 1,
                        name=name,
                        reason=result.reason,
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
