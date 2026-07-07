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
    home_walk_grid: np.ndarray
    home_grid_w: int
    home_grid_h: int
    garden_approaches: list[Point]
    garden_rects: list[Rect]
    house_targets: list[Point]
    house_rects: list[Rect]
    garden_circuit: list[int]
    world_to_map: Point
    home_exit: Point
    home_exit_rect: Rect
    home_diners: list[Point]
    home_cook: Point
    home_wash: Point


_ATTRS = {
    "WALK_GRID": "walk_grid",
    "GRID_W": "grid_w",
    "GRID_H": "grid_h",
    "HOME_WALK_GRID": "home_walk_grid",
    "HOME_GRID_W": "home_grid_w",
    "HOME_GRID_H": "home_grid_h",
    "GARDEN_APPROACHES": "garden_approaches",
    "GARDEN_RECTS": "garden_rects",
    "HOUSE_TARGETS": "house_targets",
    "HOUSE_RECTS": "house_rects",
    "GARDEN_CIRCUIT": "garden_circuit",
    "WORLD_TO_MAP": "world_to_map",
    "HOME_EXIT": "home_exit",
    "HOME_EXIT_RECT": "home_exit_rect",
    "HOME_DINERS": "home_diners",
    "HOME_COOK": "home_cook",
    "HOME_WASH": "home_wash",
}


@lru_cache(maxsize=1)
def _load() -> _LoadedMap:
    data_dir = Path(__file__).with_name("mapdata")
    with np.load(data_dir / "walk.npz") as walk_npz:
        walk_grid = _load_walk_grid(walk_npz)

    with np.load(data_dir / "home_walk.npz") as walk_npz:
        home_walk_grid = _load_walk_grid(walk_npz)

    layout = json.loads((data_dir / "layout.json").read_text())
    grid_h, grid_w = walk_grid.shape
    home_grid_h, home_grid_w = home_walk_grid.shape
    home = layout["home"]
    return _LoadedMap(
        walk_grid=walk_grid,
        grid_w=grid_w,
        grid_h=grid_h,
        home_walk_grid=home_walk_grid,
        home_grid_w=home_grid_w,
        home_grid_h=home_grid_h,
        garden_approaches=[_point(point) for point in layout["garden_approaches"]],
        garden_rects=[_rect(rect) for rect in layout["garden_rects"]],
        house_targets=[_point(point) for point in layout["house_targets"]],
        house_rects=[_rect(rect) for rect in layout["house_rects"]],
        garden_circuit=[int(index) for index in layout["garden_circuit"]],
        world_to_map=_point(layout["world_to_map"]),
        home_exit=_point(home["exit"]),
        home_exit_rect=_rect(home["exit_rect"]),
        home_diners=[_point(point) for point in home["diners"]],
        home_cook=_point(home["cook"]),
        home_wash=_point(home["wash"]),
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


def _load_walk_grid(walk_npz: Any) -> np.ndarray:
    shape = tuple(int(v) for v in walk_npz["shape"])
    packed = walk_npz["packed"]
    flat = np.unpackbits(packed)[: shape[0] * shape[1]]
    return flat.reshape(shape).astype(bool)


if TYPE_CHECKING:
    WALK_GRID: np.ndarray
    GRID_W: int
    GRID_H: int
    HOME_WALK_GRID: np.ndarray
    HOME_GRID_W: int
    HOME_GRID_H: int
    GARDEN_APPROACHES: list[Point]
    GARDEN_RECTS: list[Rect]
    HOUSE_TARGETS: list[Point]
    HOUSE_RECTS: list[Rect]
    GARDEN_CIRCUIT: list[int]
    WORLD_TO_MAP: Point
    HOME_EXIT: Point
    HOME_EXIT_RECT: Rect
    HOME_DINERS: list[Point]
    HOME_COOK: Point
    HOME_WASH: Point


__all__ = list(_ATTRS)
