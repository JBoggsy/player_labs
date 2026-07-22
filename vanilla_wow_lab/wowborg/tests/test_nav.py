"""Nav v2 unit tests: L0/L1/L2 against the scripted fake world."""

from __future__ import annotations

import time

from fake_nav_bridge import NavWorldBridge
from wowborg.nav.journey import JourneyPlanner, JourneyStatus
from wowborg.nav.local import LocalMover, LocalMoveStatus
from wowborg.nav.route import NavState, RouteNavigator
from wowborg.nav.world_model import Edge, Place, Point, WorldModel


def deadline(seconds: float = 20.0) -> float:
    return time.monotonic() + seconds


# ---- L0: local mover ---------------------------------------------------------------


def test_l0_arrives_in_3d() -> None:
    bridge = NavWorldBridge()
    result = LocalMover().move_to(bridge, Point(1, 50.0, 0.0, 0.0), until=deadline())
    assert result.status == LocalMoveStatus.ARRIVED
    assert result.end.distance(Point(1, 50.0, 0.0, 0.0)) <= 8.0


def test_l0_wrong_floor_is_not_arrival() -> None:
    # Target 40yd straight up: 2D distance is 0 from the start — v1 would "arrive".
    bridge = NavWorldBridge()
    bridge.walls = [(0.0, 0.0, 0.0)]  # no walls; the mover just can't climb
    target = Point(1, 0.0, 0.0, 40.0)
    result = LocalMover().move_to(bridge, target, until=deadline(5.0))
    assert result.status != LocalMoveStatus.ARRIVED


def test_l0_wall_stall_detected() -> None:
    bridge = NavWorldBridge(walls=[(30.0, 0.0, 25.0)])
    result = LocalMover().move_to(bridge, Point(1, 100.0, 0.0, 0.0), until=deadline())
    assert result.status == LocalMoveStatus.STALLED
    assert bridge.recommended_selections > 0  # unstick ladder ran


def test_l0_combat_surfaces_immediately() -> None:
    bridge = NavWorldBridge(combat_at=(30.0, 0.0, 10.0))
    result = LocalMover().move_to(bridge, Point(1, 100.0, 0.0, 0.0), until=deadline())
    assert result.status == LocalMoveStatus.COMBAT


def test_l0_death_surfaces_immediately() -> None:
    bridge = NavWorldBridge(death_at=(30.0, 0.0, 10.0))
    result = LocalMover().move_to(bridge, Point(1, 100.0, 0.0, 0.0), until=deadline())
    assert result.status == LocalMoveStatus.DEAD


# ---- L1: route navigator -------------------------------------------------------------


def test_l1_navigates_long_route() -> None:
    bridge = NavWorldBridge()
    result = RouteNavigator().navigate_to(bridge, Point(1, 400.0, 300.0, 0.0),
                                          deadline=deadline(30.0))
    assert result.state == NavState.ARRIVED
    assert result.planned_distance > 400  # detour-inflated true path length
    assert bridge.plan_calls >= 1


def test_l1_unreachable_fails_fast() -> None:
    bridge = NavWorldBridge(route_status="no_path")
    started = time.monotonic()
    result = RouteNavigator().navigate_to(bridge, Point(1, 400.0, 0.0, 0.0),
                                          deadline=deadline(30.0))
    assert result.state == NavState.FAILED and result.reason == "unreachable"
    assert time.monotonic() - started < 2.0  # detected at planning, not by grinding
    assert bridge.move_selections == 0


def test_l1_combat_pause_then_arrival() -> None:
    bridge = NavWorldBridge(combat_at=(100.0, 75.0, 15.0))
    result = RouteNavigator().navigate_to(bridge, Point(1, 200.0, 150.0, 0.0),
                                          deadline=deadline(30.0))
    assert result.state == NavState.ARRIVED
    assert result.combat_pauses >= 1


def test_l1_death_recovery_then_arrival() -> None:
    bridge = NavWorldBridge(death_at=(100.0, 75.0, 12.0), graveyard=(1, 20.0, 10.0, 0.0))
    result = RouteNavigator().navigate_to(bridge, Point(1, 200.0, 150.0, 0.0),
                                          deadline=deadline(40.0))
    assert result.state == NavState.ARRIVED
    assert result.deaths == 1


def test_l1_wall_replans_then_honest_failure() -> None:
    # A wall dead across the (straight-line scripted) route: L1 re-plans a bounded
    # number of times then fails with no_progress — never grinds forever.
    bridge = NavWorldBridge(walls=[(60.0, 45.0, 40.0)])
    result = RouteNavigator().navigate_to(bridge, Point(1, 120.0, 90.0, 0.0),
                                          deadline=deadline(30.0))
    assert result.state == NavState.FAILED
    assert result.reason in ("no_progress", "budget")
    assert result.replans >= 1


def test_l1_degrades_without_planner() -> None:
    bridge = NavWorldBridge(planner_available=False)
    result = RouteNavigator().navigate_to(bridge, Point(1, 80.0, 0.0, 0.0),
                                          deadline=deadline(20.0))
    assert result.state == NavState.ARRIVED  # direct move fallback still works


def test_l1_escalates_cross_map() -> None:
    bridge = NavWorldBridge()
    result = RouteNavigator().navigate_to(bridge, Point(389, 0.0, 0.0, 0.0),
                                          deadline=deadline())
    assert result.state == NavState.ESCALATE_MAP


# ---- L2: journey planner ---------------------------------------------------------------


def small_world() -> WorldModel:
    world = WorldModel(places={}, edges=[])
    world.places = {
        "home": Place("home", Point(1, 0.0, 0.0, 0.0)),
        "pad": Place("pad", Point(1, 100.0, 0.0, 0.0)),
        "dungeon-in": Place("dungeon-in", Point(389, 5.0, 5.0, -10.0)),
        "dungeon-hall": Place("dungeon-hall", Point(389, 80.0, 40.0, -20.0)),
    }
    world.edges = [
        Edge("walk", "home", "pad", cost_hint=100),
        Edge("portal", "pad", "dungeon-in", bidirectional=False,
             trigger_id=2230, cost_hint=1),
        Edge("walk", "dungeon-in", "dungeon-hall", cost_hint=90),
    ]
    return world


def test_l2_same_map_delegates_to_l1() -> None:
    bridge = NavWorldBridge()
    journey = JourneyPlanner(world=small_world())
    result = journey.journey_to(bridge, Point(1, 90.0, 60.0, 0.0), deadline=deadline(30.0))
    assert result.status == JourneyStatus.ARRIVED


def test_l2_cross_map_via_portal() -> None:
    bridge = NavWorldBridge(portals={2230: (389, 5.0, 5.0, -10.0)})
    journey = JourneyPlanner(world=small_world())
    result = journey.journey_to(bridge, Point(389, 80.0, 40.0, -20.0),
                                deadline=deadline(60.0))
    assert result.status == JourneyStatus.ARRIVED
    assert bridge.map_id == 389
    kinds = [leg["kind"] for leg in result.legs]
    assert "portal" in kinds and "walk" in kinds


def test_l2_unknown_region_fails_honestly() -> None:
    bridge = NavWorldBridge()
    journey = JourneyPlanner(world=small_world())
    result = journey.journey_to(bridge, Point(530, 0.0, 0.0, 0.0), deadline=deadline(10.0))
    assert result.status == JourneyStatus.FAILED
    assert result.reason in ("unknown_region", "no_world_path")


# ---- world race policy ----------------------------------------------------------------


def test_world_race_draw_is_seeded_and_multi_region() -> None:
    import random

    from wowborg.policies.world_race import STATIONS, draw_course

    a = draw_course(random.Random(5), dict(STATIONS), 5)
    b = draw_course(random.Random(5), dict(STATIONS), 5)
    c = draw_course(random.Random(6), dict(STATIONS), 5)
    assert a == b and a != c
    regions = {STATIONS[n][1] for n in a if STATIONS[n][2] != "unreachable"}
    assert len(regions) >= 3
    assert any(STATIONS[n][2] == "unreachable" for n in a)  # adversarial included


def test_world_race_custom_stations_env(monkeypatch) -> None:
    import json as _json

    from wowborg.policies.world_race import load_stations

    monkeypatch.setenv(
        "WOWBORG_STATIONS",
        _json.dumps([["my-spot", 1, 10.0, 20.0, 30.0, "reachable"]]),
    )
    stations = load_stations()
    assert list(stations) == ["my-spot"]
    point, region, expected = stations["my-spot"]
    assert (point.map_id, point.x, expected) == (1, 10.0, "reachable")
