"""Unit tests for the waypoint-race policy against a fake frame-driven bridge."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from wowborg.policies.waypoint_race import (
    ARRIVAL_TOLERANCE_YARDS,
    MAX_LEG_ATTEMPTS,
    WaypointRacePolicy,
    load_course,
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
class FakeObservation:
    location: FakeLocation = field(default_factory=FakeLocation)
    is_dead: bool = False
    is_ghost: bool = False


@dataclass
class FakeFrame:
    frame_id: int
    observation: FakeObservation
    action_ready: bool = True
    recommended_action: object | None = object()


class TeleportBridge:
    """Settles every move by relocating exactly to the destination."""

    def __init__(self, *, fail_moves: bool = False) -> None:
        self.position = [0.0, 0.0, 30.0]
        self._frame = 0
        self.fail_moves = fail_moves
        self.says: list[str] = []
        self._tracer = None

    def say(self, text: str) -> str | None:
        self.says.append(text)
        return "say"

    def wait_for_frame(self, *, timeout_s: float = 60.0) -> FakeFrame:
        self._frame += 1
        loc = FakeLocation(x=self.position[0], y=self.position[1], z=self.position[2])
        return FakeFrame(frame_id=self._frame, observation=FakeObservation(location=loc))

    def select_move_to(self, frame, x, y, z, map_id) -> str:
        if not self.fail_moves:
            self.position = [x, y, z]
        return f"frame-{frame.frame_id}"

    def select_recommended(self, frame) -> str:
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


SQUARE = [[0.0, 0.0, 30.0], [50.0, 0.0, 30.0], [50.0, 50.0, 30.0], [0.0, 50.0, 30.0]]


def test_load_course_default_and_env(monkeypatch) -> None:
    monkeypatch.delenv("WOWBORG_WAYPOINTS", raising=False)
    monkeypatch.delenv("WOWBORG_WAYPOINTS_FILE", raising=False)
    default = load_course()
    assert len(default) >= 2 and all(len(p) == 3 for p in default)

    monkeypatch.setenv("WOWBORG_WAYPOINTS", json.dumps(SQUARE))
    assert load_course() == SQUARE

    monkeypatch.setenv("WOWBORG_WAYPOINTS", "[[1,2]]")  # malformed → default
    assert load_course() == default


def test_race_completes_laps_and_records_splits() -> None:
    policy = WaypointRacePolicy(course=[list(p) for p in SQUARE])
    bridge = TeleportBridge()
    policy.run(bridge, until=time.monotonic() + 0.5)
    assert policy.laps_completed >= 1
    assert policy.legs_completed >= 4
    assert policy.legs_skipped == 0
    summary = policy.summary()
    assert summary["total_yards"] > 0
    # teleport-fast fake bridge can complete legs in ~0s → rate may be None there
    if summary["total_seconds"] > 0:
        assert summary["yards_per_second"] is not None
    # split legs measure the square's 50-yd sides
    sides = [s["yards"] for s in policy.splits[1:5]]
    assert all(abs(y - 50.0) < 1.0 for y in sides)
    assert any("lap 1 complete" in s for s in bridge.says)


def test_blocked_waypoints_are_skipped_after_max_attempts() -> None:
    policy = WaypointRacePolicy(course=[list(p) for p in SQUARE])
    bridge = TeleportBridge(fail_moves=True)
    policy.run(bridge, until=time.monotonic() + 0.4)
    # standing at wp0 must not accrue phantom completed legs while everything
    # else gets skipped after MAX_LEG_ATTEMPTS failures
    assert policy.legs_completed == 0
    assert policy.legs_skipped >= 3
    assert policy.summary()["total_yards"] == 0


def test_arrival_tolerance_counts_near_misses() -> None:
    course = [[0.0, 0.0, 30.0], [50.0, 0.0, 30.0]]
    policy = WaypointRacePolicy(course=course)

    class NearMissBridge(TeleportBridge):
        def select_move_to(self, frame, x, y, z, map_id) -> str:
            # settle 5 yd short of the target — inside tolerance
            self.position = [x - ARRIVAL_TOLERANCE_YARDS + 3.0, y, z]
            return f"frame-{frame.frame_id}"

    bridge = NearMissBridge()
    policy.run(bridge, until=time.monotonic() + 0.3)
    assert policy.legs_completed >= 1
