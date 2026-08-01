"""Unit tests for the frame-driven random-walk policy against a fake session."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field

from wowborg.policies.random_walk import (
    MAX_LEG_YARDS,
    MIN_LEG_YARDS,
    RandomWalkPolicy,
)
from wowborg.types import ActionOutcome


@dataclass
class FakeLocation:
    map_id: int = 1
    x: float = 100.0
    y: float = 200.0
    z: float = 30.0
    orientation: float = 0.0


@dataclass
class FakeFrame:
    frame_id: int
    location: FakeLocation = field(default_factory=FakeLocation)
    is_dead: bool = False
    is_ghost: bool = False


class FakeSession:
    """Frame-driven session double: offers frames and settles steps successfully."""

    def __init__(self, *, refuse_moves: bool = False, dead: bool = False) -> None:
        self._next_frame = 0
        self.refuse_moves = refuse_moves
        self.dead = dead
        self.moves: list[tuple[float, float, float, int]] = []
        self.waits_taken = 0
        self.says: list[str] = []

    def say(self, text: str) -> str | None:
        self.says.append(text)
        return f"say-{len(self.says)}"

    def wait_for_frame(self, *, timeout_s: float = 60.0) -> FakeFrame:
        self._next_frame += 1
        return FakeFrame(frame_id=self._next_frame, is_dead=self.dead)

    def select_move_to(self, frame, x, y, z, map_id) -> str | None:
        if self.refuse_moves:
            return None
        self.moves.append((x, y, z, map_id))
        return f"frame-{frame.frame_id}"

    def select_wait(self, frame) -> str | None:
        self.waits_taken += 1
        return f"frame-{frame.frame_id}"

    def wait_for_settlement(self, frame_id, *, timeout_s=90.0) -> ActionOutcome:
        return ActionOutcome(
            request_id=f"frame-{frame_id}",
            kind="move",
            success=True,
            settlement_kind=None,
            displacement_yards=None,
            end_position=None,
            detail="fake settlement",
        )


def test_destinations_are_within_leg_bounds() -> None:
    policy = RandomWalkPolicy(rng=random.Random(42))
    for _ in range(200):
        dx, dy = policy.next_destination(0.0, 0.0)
        distance = math.hypot(dx, dy)
        assert MIN_LEG_YARDS <= distance <= MAX_LEG_YARDS


def test_run_selects_moves_and_counts_success() -> None:
    bridge = FakeSession()
    policy = RandomWalkPolicy(rng=random.Random(1))
    policy.run(bridge, until=time.monotonic() + 0.1)
    assert policy.legs_attempted >= 1
    assert policy.legs_reached >= 1
    assert policy.legs_fallback == 0
    # every move targeted the observed map and kept the observed z
    assert all(m[2] == 30.0 and m[3] == 1 for m in bridge.moves)


def test_move_rejection_yields_one_step() -> None:
    bridge = FakeSession(refuse_moves=True)
    policy = RandomWalkPolicy(rng=random.Random(1))
    policy.run(bridge, until=time.monotonic() + 0.1)
    assert policy.legs_attempted >= 1
    assert policy.legs_fallback == policy.legs_attempted
    assert bridge.waits_taken >= 1
    assert bridge.moves == []


def test_dead_character_yields_for_recovery() -> None:
    bridge = FakeSession(dead=True)
    policy = RandomWalkPolicy(rng=random.Random(1))
    policy.run(bridge, until=time.monotonic() + 0.1)
    assert policy.legs_attempted == 0
    assert bridge.moves == []
    assert bridge.waits_taken >= 1


def test_breadcrumb_modes(monkeypatch) -> None:
    monkeypatch.setenv("WOWBORG_BREADCRUMBS", "off")
    bridge = FakeSession()
    RandomWalkPolicy(rng=random.Random(1)).run(bridge, until=time.monotonic() + 0.05)
    assert bridge.says == []

    monkeypatch.delenv("WOWBORG_BREADCRUMBS", raising=False)  # default minimal
    bridge = FakeSession()
    RandomWalkPolicy(rng=random.Random(1)).run(bridge, until=time.monotonic() + 0.05)
    assert any("starting" in s for s in bridge.says)


def test_summary_shape() -> None:
    bridge = FakeSession()
    policy = RandomWalkPolicy(rng=random.Random(1))
    policy.run(bridge, until=time.monotonic() + 0.05)
    summary = policy.summary()
    assert set(summary) == {"legs_attempted", "legs_reached", "legs_fallback"}
    assert 0 <= summary["legs_reached"] <= summary["legs_attempted"]
