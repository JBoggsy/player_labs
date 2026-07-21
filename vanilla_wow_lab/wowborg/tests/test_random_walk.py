"""Unit tests for the random-walk policy against a fake bridge (no wow_sdk needed)."""

from __future__ import annotations

import math
import random
import time

from wowborg.policies.random_walk import (
    MAX_LEG_YARDS,
    MIN_LEG_YARDS,
    RandomWalkPolicy,
)
from wowborg.types import ActionOutcome, Observation, Position


def observation(x: float = 100.0, y: float = 200.0, *, dead: bool = False) -> Observation:
    return Observation(
        tick=7,
        captured_at=time.time(),
        map_id=1,
        zone="Durotar",
        position=Position(x, y, 30.0, 0.0),
        health=100,
        max_health=100,
        in_combat=False,
        is_dead=dead,
        is_ghost=False,
    )


def outcome(request_id: str, kind_: str = "reached_target") -> ActionOutcome:
    return ActionOutcome(
        request_id=request_id,
        kind="move",
        success=kind_ in {"reached_target", "advanced_corridor", "combat_interrupted"},
        settlement_kind=kind_,
        displacement_yards=12.0,
        end_position=None,
        detail="",
    )


class FakeBridge:
    def __init__(self, settlement_kinds: list[str]) -> None:
        self._kinds = settlement_kinds
        self.moves: list[tuple[float, float, float, int]] = []
        self.says: list[str] = []

    def say(self, text: str) -> str | None:
        self.says.append(text)
        return f"say-{len(self.says)}"

    def observe(self) -> Observation:
        return observation()

    def move_to(self, x, y, z, map_id, *, arrival_radius=3.0, trust_z=False):
        self.moves.append((x, y, z, map_id))
        return f"req-{len(self.moves)}"

    def wait_for_result(self, request_id, *, timeout_s=90.0):
        if not self._kinds:
            return None
        return outcome(request_id, self._kinds[(len(self.moves) - 1) % len(self._kinds)])


def test_destinations_are_within_leg_bounds() -> None:
    policy = RandomWalkPolicy(rng=random.Random(42))
    for _ in range(200):
        dx, dy = policy.next_destination(0.0, 0.0)
        distance = math.hypot(dx, dy)
        assert MIN_LEG_YARDS <= distance <= MAX_LEG_YARDS


def test_run_counts_successful_legs() -> None:
    bridge = FakeBridge(["reached_target"] * 3)
    policy = RandomWalkPolicy(rng=random.Random(1))
    policy.run(bridge, until=time.monotonic() + 0.2)
    assert policy.legs_attempted >= 1
    # The deadline may land mid-leg: the final attempted leg can go unsettled.
    assert policy.legs_reached in (policy.legs_attempted, policy.legs_attempted - 1)
    # every leg targeted the observed map and kept the observed z
    assert all(m[2] == 30.0 and m[3] == 1 for m in bridge.moves)


def test_run_stops_when_dead() -> None:
    class DeadBridge(FakeBridge):
        def observe(self) -> Observation:
            return observation(dead=True)

    bridge = DeadBridge([])
    policy = RandomWalkPolicy(rng=random.Random(1))
    policy.run(bridge, until=time.monotonic() + 5.0)
    assert policy.legs_attempted == 0
    assert bridge.moves == []
    assert any("died" in s for s in bridge.says)


def test_run_emits_breadcrumbs_and_summary_verbose(monkeypatch) -> None:
    monkeypatch.setenv("WOWBORG_BREADCRUMBS", "verbose")
    bridge = FakeBridge(["reached_target"])
    policy = RandomWalkPolicy(rng=random.Random(1))
    policy.run(bridge, until=time.monotonic() + 0.05)
    assert any("starting" in s for s in bridge.says)
    assert any("leg 1" in s for s in bridge.says)
    summary = policy.summary()
    assert summary["legs_attempted"] >= 1
    assert 0 <= summary["legs_reached"] <= summary["legs_attempted"]


def test_minimal_breadcrumbs_skip_per_leg_says(monkeypatch) -> None:
    monkeypatch.delenv("WOWBORG_BREADCRUMBS", raising=False)  # default = minimal
    bridge = FakeBridge(["reached_target"])
    policy = RandomWalkPolicy(rng=random.Random(1))
    policy.run(bridge, until=time.monotonic() + 0.05)
    assert any("starting" in s for s in bridge.says)
    # No per-leg chat spam (the "done:" summary mentions legs; per-leg says start "wowborg leg")
    assert not any(s.startswith("wowborg leg") for s in bridge.says)
    assert any("done:" in s for s in bridge.says)
    assert policy.legs_attempted >= 1  # still walking, still tracing


def test_breadcrumbs_off_says_nothing(monkeypatch) -> None:
    monkeypatch.setenv("WOWBORG_BREADCRUMBS", "off")
    bridge = FakeBridge(["reached_target"])
    policy = RandomWalkPolicy(rng=random.Random(1))
    policy.run(bridge, until=time.monotonic() + 0.05)
    assert bridge.says == []
    assert policy.legs_attempted >= 1


def test_timeout_leg_is_not_counted_as_reached() -> None:
    bridge = FakeBridge([])  # wait_for_result always returns None
    policy = RandomWalkPolicy(rng=random.Random(1))
    policy.run(bridge, until=time.monotonic() + 0.05)
    assert policy.legs_reached == 0
