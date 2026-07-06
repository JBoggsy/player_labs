"""Runtime loader for Cady's baked Heartleaf map data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

Point = tuple[int, int]
Rect = tuple[int, int, int, int]


@dataclass(frozen=True)
class _LoadedMap:
    walk_grid: np.ndarray
    grid_w: int
    grid_h: int
    garden_approaches: list[Point]
    garden_rects: list[Rect]
    house_targets: list[Point]
    house_rects: list[Rect]
    garden_circuit: list[int]
    world_to_map: Point


_ATTRS = {
    "WALK_GRID": "walk_grid",
    "GRID_W": "grid_w",
    "GRID_H": "grid_h",
    "GARDEN_APPROACHES": "garden_approaches",
    "GARDEN_RECTS": "garden_rects",
    "HOUSE_TARGETS": "house_targets",
    "HOUSE_RECTS": "house_rects",
    "GARDEN_CIRCUIT": "garden_circuit",
    "WORLD_TO_MAP": "world_to_map",
}


@lru_cache(maxsize=1)
def _load() -> _LoadedMap:
    data_dir = Path(__file__).with_name("mapdata")
    with np.load(data_dir / "walk.npz") as walk_npz:
        shape = tuple(int(v) for v in walk_npz["shape"])
        packed = walk_npz["packed"]
        flat = np.unpackbits(packed)[: shape[0] * shape[1]]
        walk_grid = flat.reshape(shape).astype(bool)

    layout = json.loads((data_dir / "layout.json").read_text())
    grid_h, grid_w = walk_grid.shape
    return _LoadedMap(
        walk_grid=walk_grid,
        grid_w=grid_w,
        grid_h=grid_h,
        garden_approaches=[_point(point) for point in layout["garden_approaches"]],
        garden_rects=[_rect(rect) for rect in layout["garden_rects"]],
        house_targets=[_point(point) for point in layout["house_targets"]],
        house_rects=[_rect(rect) for rect in layout["house_rects"]],
        garden_circuit=[int(index) for index in layout["garden_circuit"]],
        world_to_map=_point(layout["world_to_map"]),
    )


def __getattr__(name: str) -> Any:
    """Load baked map data on first module attribute access."""

    attr = _ATTRS.get(name)
    if attr is None:
        raise AttributeError(name)
    return getattr(_load(), attr)


def _point(value: list[int]) -> Point:
    return (int(value[0]), int(value[1]))


def _rect(value: list[int]) -> Rect:
    return (int(value[0]), int(value[1]), int(value[2]), int(value[3]))


if TYPE_CHECKING:
    WALK_GRID: np.ndarray
    GRID_W: int
    GRID_H: int
    GARDEN_APPROACHES: list[Point]
    GARDEN_RECTS: list[Rect]
    HOUSE_TARGETS: list[Point]
    HOUSE_RECTS: list[Rect]
    GARDEN_CIRCUIT: list[int]
    WORLD_TO_MAP: Point


__all__ = list(_ATTRS)
