"""Tests for Cady world/map frame conversion."""

from __future__ import annotations

from cady.frame import to_map, to_world


def test_frame_round_trip() -> None:
    point = (123, 456)

    assert to_world(to_map(point)) == point
