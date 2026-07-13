"""Tests for the baked occupancy heatmap lookup."""

from __future__ import annotations

from cady import occupancy


def test_heatmap_is_baked_and_returns_walkable_hot_spots() -> None:
    # The heatmap ships baked from replays; hottest spots must be real points.
    assert occupancy.is_available()
    from cady.mapdata import GRID_H, GRID_W

    for minutes in (60, 240, 420, 480, 540):  # 9AM..5PM (since-8AM)
        spot = occupancy.hottest_spot(minutes)
        assert spot is not None
        assert 0 <= spot[0] < GRID_W and 0 <= spot[1] < GRID_H


def test_hottest_spot_none_without_time() -> None:
    assert occupancy.hottest_spot(None) is None


def test_hottest_spot_avoids_current_position() -> None:
    # Asking to avoid the hottest cell yields a DIFFERENT spot (not where we are).
    first = occupancy.hottest_spot(480)
    assert first is not None
    avoided = occupancy.hottest_spot(480, avoid=first, avoid_radius=64)
    assert avoided is not None
    assert avoided != first
