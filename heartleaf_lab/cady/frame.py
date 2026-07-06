"""Coordinate-frame conversion for Cady's baked Heartleaf map."""

from __future__ import annotations

from cady import mapdata

Point = tuple[int, int]


def to_map(world_xy: Point) -> Point:
    """Convert a world-frame point from perception into baked map pixels."""

    wx, wy = world_xy
    ox, oy = mapdata.WORLD_TO_MAP
    return (wx + ox, wy + oy)


def to_world(map_xy: Point) -> Point:
    """Convert baked map pixels into the world frame used by action steering."""

    mx, my = map_xy
    ox, oy = mapdata.WORLD_TO_MAP
    return (mx - ox, my - oy)


__all__ = ["Point", "to_map", "to_world"]
