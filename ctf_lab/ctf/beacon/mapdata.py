"""Loader for the baked nav artifact (``mapdata/nav.npz``).

The artifact is produced offline by ``ctf.beacon.tools.bake_map`` and shipped in the
image. This module loads it once and exposes the walkable grid + the four flow fields
(steal/home × red/blue) as read-only numpy arrays. See the design doc §4.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

NAV_PATH = Path(__file__).resolve().parent / "mapdata" / "nav.npz"

# Neighbour table MUST match tools/bake_map.py _NEIGHBORS (index → (dx, dy)).
NEIGHBORS: tuple[tuple[int, int], ...] = (
    (-1, 0), (1, 0), (0, -1), (0, 1),
    (-1, -1), (-1, 1), (1, -1), (1, 1),
)


@lru_cache(maxsize=1)
def _load() -> dict[str, np.ndarray]:
    with np.load(NAV_PATH) as data:
        return {k: data[k] for k in data.files}


def walkable_grid() -> np.ndarray:
    """Boolean [GRID_H, GRID_W] grid; True = a player body fits in the cell."""
    return _load()["walkable"]


def cover_grid() -> np.ndarray:
    """Boolean grid; True = a walkable cell adjacent to a wall (peek-fire cover)."""
    return _load()["cover"]


def flow_field(team: str, kind: str) -> np.ndarray:
    """Next-hop field for a team's fixed goal. ``kind`` is 'steal' or 'home'.

    Value per cell (uint8): 0 = goal/unreachable, else 1 + index into NEIGHBORS —
    the neighbour to step to for one hop toward the goal.
    """
    return _load()[f"flow_{kind}_{team}"]


def nearest_cover(px: int, py: int, max_cells: int = 6):
    """Map-space centre of the nearest cover cell to (px, py), or None if none is
    within ``max_cells`` grid cells. Used to snap hold/staging points off the open."""
    from ctf.beacon.config import GRID_H, GRID_W, NAV_CELL

    cover = cover_grid()
    gx = min(max(px // NAV_CELL, 0), GRID_W - 1)
    gy = min(max(py // NAV_CELL, 0), GRID_H - 1)
    if cover[gy, gx]:
        return (gx * NAV_CELL + NAV_CELL // 2, gy * NAV_CELL + NAV_CELL // 2)
    for ring in range(1, max_cells + 1):
        best = None
        best_d = 1e18
        for dy in range(-ring, ring + 1):
            for dx in range(-ring, ring + 1):
                nx, ny = gx + dx, gy + dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H and cover[ny, nx]:
                    d = dx * dx + dy * dy
                    if d < best_d:
                        best_d = d
                        best = (nx * NAV_CELL + NAV_CELL // 2, ny * NAV_CELL + NAV_CELL // 2)
        if best is not None:
            return best
    return None


__all__ = ["NEIGHBORS", "cover_grid", "flow_field", "nearest_cover", "walkable_grid"]
