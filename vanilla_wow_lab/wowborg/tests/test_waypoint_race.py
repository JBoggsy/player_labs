"""Unit tests for the randomized-course waypoint-race policy."""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field

from wowborg.policies.waypoint_race import (
    ARRIVAL_TOLERANCE_YARDS,
    DEFAULT_SUBSET_BY_TIER,
    WAYPOINT_CATALOG,
    WaypointRacePolicy,
    load_course,
    sample_course,
)
from wowborg.types import ActionOutcome


@dataclass
class FakeLocation:
    map_id: int = 1
    x: float = 0.0
    y: float = 0.0
    z: float = 30.0
    orientation: float = 0.0


@dataclass
class FakeFrame:
    frame_id: int
    location: FakeLocation
    is_dead: bool = False
    is_ghost: bool = False


class TeleportBridge:
    """Settles every move by relocating exactly to the destination."""

    def __init__(self, *, fail_moves: bool = False) -> None:
        self.position = [0.0, 0.0, 30.0]
        self._frame = 0
        self.fail_moves = fail_moves
        self.says: list[str] = []
        self.moves: list[list[float]] = []
        self._tracer = None

    def say(self, text: str) -> str | None:
        self.says.append(text)
        return "say"

    def wait_for_frame(self, *, timeout_s: float = 60.0) -> FakeFrame:
        self._frame += 1
        loc = FakeLocation(x=self.position[0], y=self.position[1], z=self.position[2])
        return FakeFrame(frame_id=self._frame, location=loc)

    def select_move_to(self, frame, x, y, z, map_id) -> str:
        self.moves.append([x, y, z])
        if not self.fail_moves:
            self.position = [x, y, z]
        return f"frame-{frame.frame_id}"

    def select_wait(self, frame) -> str:
        return f"frame-{frame.frame_id}"

    def wait_for_settlement(self, frame_id, *, timeout_s=90.0) -> ActionOutcome:
        return ActionOutcome(
            request_id=f"frame-{frame_id}",
            kind="move",
            success=not self.fail_moves,
            settlement_kind=None,
            displacement_yards=None,
            end_position=None,
            detail="teleport" if not self.fail_moves else "blocked",
        )


SQUARE = [
    ("a", [0.0, 0.0, 30.0]),
    ("b", [50.0, 0.0, 30.0]),
    ("c", [50.0, 50.0, 30.0]),
    ("d", [0.0, 50.0, 30.0]),
]


# ---- catalog & course sampling ----------------------------------------------------


def test_catalog_tiers_distances_and_vias() -> None:
    import math

    spawn = WAYPOINT_CATALOG["spawn-plaza"]
    for name, (x, y, z, tier, via) in WAYPOINT_CATALOG.items():
        d = math.hypot(x - spawn[0], y - spawn[1])
        if tier == "near":
            assert d < 150, f"{name}: {d:.0f} yd is not near"
        elif tier == "mid":
            assert 100 <= d <= 500, f"{name}: {d:.0f} yd is not mid"
        elif tier == "far":
            assert d > 450, f"{name}: {d:.0f} yd is not far"
        else:
            assert tier in ("stage", "hard"), f"{name}: unknown tier {tier}"
        for via_name in via:
            assert via_name in WAYPOINT_CATALOG, f"{name}: unknown via {via_name}"
            assert via_name != name


def test_sample_course_is_tier_balanced_and_seeded() -> None:
    course_a = sample_course(random.Random(7))
    course_b = sample_course(random.Random(7))
    course_c = sample_course(random.Random(8))
    assert course_a == course_b  # same seed → same course
    assert course_a != course_c  # different seed → (overwhelmingly) different
    assert len(course_a) == sum(DEFAULT_SUBSET_BY_TIER.values())
    tiers = [WAYPOINT_CATALOG[name][3] for name, _ in course_a]
    for tier, count in DEFAULT_SUBSET_BY_TIER.items():
        assert tiers.count(tier) == count
    names = [n for n, _ in course_a]
    assert len(set(names)) == len(names)  # no duplicates


def test_staged_leg_routes_via_staging_nodes() -> None:
    from wowborg.policies.waypoint_race import waypoint_point

    # course: spawn → sarkoth-mesa (staged via scorpid-field-edge then hanazua-rock)
    course = [
        ("spawn-plaza", waypoint_point("spawn-plaza")),
        ("sarkoth-mesa", waypoint_point("sarkoth-mesa")),
    ]
    policy = WaypointRacePolicy(course=course, rng=random.Random(1))
    bridge = TeleportBridge()
    bridge.position = list(waypoint_point("spawn-plaza"))
    policy.run(bridge, until=time.monotonic() + 0.5)
    # The mesa leg must route THROUGH its staging chain (suffix from the nearest chain
    # node — prefix nodes behind the start are dropped) before the final point.
    targets = [(round(m[0], 1), round(m[1], 1)) for m in bridge.moves]
    rock = waypoint_point("hanazua-rock")
    mesa = waypoint_point("sarkoth-mesa")
    shelf4 = waypoint_point("field-shelf-4")
    assert (round(shelf4[0], 1), round(shelf4[1], 1)) in targets
    assert (round(rock[0], 1), round(rock[1], 1)) in targets
    assert (round(mesa[0], 1), round(mesa[1], 1)) in targets
    mesa_i = targets.index((round(mesa[0], 1), round(mesa[1], 1)))
    rock_i = targets.index((round(rock[0], 1), round(rock[1], 1)))
    assert rock_i < mesa_i  # staging precedes the target
    assert policy.legs_completed >= 2


def test_load_course_env_override_and_seed(monkeypatch) -> None:
    monkeypatch.setenv("WOWBORG_WAYPOINTS", json.dumps([[1, 2, 3], [4, 5, 6]]))
    fixed = load_course()
    assert fixed == [("wp0", [1.0, 2.0, 3.0]), ("wp1", [4.0, 5.0, 6.0])]

    monkeypatch.delenv("WOWBORG_WAYPOINTS", raising=False)
    monkeypatch.setenv("WOWBORG_RACE_SEED", "42")
    assert load_course() == load_course()  # seeded → reproducible


# ---- race mechanics ----------------------------------------------------------------


def test_race_completes_laps_and_records_named_splits() -> None:
    policy = WaypointRacePolicy(course=[(n, list(p)) for n, p in SQUARE], rng=random.Random(1))
    bridge = TeleportBridge()
    policy.run(bridge, until=time.monotonic() + 0.5)
    assert policy.laps_completed >= 1
    assert policy.legs_completed >= 4
    assert policy.legs_skipped == 0
    summary = policy.summary()
    assert summary["completion_rate"] == 1.0
    assert summary["total_yards"] > 0
    assert set(summary["course"]) == {"a", "b", "c", "d"}
    assert all(s["name"] in {"a", "b", "c", "d"} for s in policy.splits)
    assert any("lap 1 complete" in s for s in bridge.says)


def test_course_reshuffles_between_laps() -> None:
    policy = WaypointRacePolicy(course=[(n, list(p)) for n, p in SQUARE], rng=random.Random(3))
    bridge = TeleportBridge()
    first_order = [n for n, _ in policy.course]
    policy.run(bridge, until=time.monotonic() + 0.5)
    assert policy.laps_completed >= 2
    # after ≥1 reshuffle the live course order should (overwhelmingly) differ
    assert [n for n, _ in policy.course] != first_order or policy.laps_completed < 2


def test_blocked_waypoints_are_skipped_after_max_attempts() -> None:
    policy = WaypointRacePolicy(course=[(n, list(p)) for n, p in SQUARE], rng=random.Random(1))
    bridge = TeleportBridge(fail_moves=True)
    policy.run(bridge, until=time.monotonic() + 0.4)
    assert policy.legs_completed == 0
    assert policy.legs_skipped >= 3
    assert policy.summary()["completion_rate"] == 0.0
    assert policy.summary()["total_yards"] == 0


def test_arrival_tolerance_counts_near_misses() -> None:
    course = [("a", [0.0, 0.0, 30.0]), ("b", [50.0, 0.0, 30.0])]
    policy = WaypointRacePolicy(course=course, rng=random.Random(1))

    class NearMissBridge(TeleportBridge):
        def select_move_to(self, frame, x, y, z, map_id) -> str:
            self.position = [x - ARRIVAL_TOLERANCE_YARDS + 3.0, y, z]
            return f"frame-{frame.frame_id}"

    bridge = NearMissBridge()
    policy.run(bridge, until=time.monotonic() + 0.3)
    assert policy.legs_completed >= 1
