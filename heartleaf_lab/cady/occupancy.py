"""Runtime access to the baked per-game-hour occupancy heatmap.

Learned offline from many replays (`tools/build_occupancy_heatmap.py`): for each
game-hour, a coarse grid of how often OTHER players were seen in each cell. Cady
uses it during the invite window to head toward empirically-crowded spots when
she can't see anyone live — replacing the old blind "walk to map center".

Positions are main-map foot pixels (same frame as the baked walk grid), so a hot
cell converts directly to a world point to navigate to.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

Point = tuple[int, int]


@dataclass(frozen=True)
class _Heatmap:
    hours: np.ndarray          # (n_hours,) game-hour labels, e.g. 8..21
    counts: np.ndarray         # (n_hours, cells_y, cells_x) occupancy counts
    cell_size: int
    grid_w: int
    grid_h: int


@lru_cache(maxsize=1)
def _load() -> _Heatmap | None:
    """Load the baked heatmap, or None if it hasn't been built yet."""
    path = Path(__file__).with_name("mapdata") / "occupancy.npz"
    if not path.exists():
        return None
    with np.load(path) as data:
        return _Heatmap(
            hours=data["hours"],
            counts=data["counts"].astype(np.float64),
            cell_size=int(data["cell_size"]),
            grid_w=int(data["grid_w"]),
            grid_h=int(data["grid_h"]),
        )


def _hour_row(heatmap: _Heatmap, game_minutes_since_8am: int) -> np.ndarray | None:
    """The occupancy grid for the hour containing this time, or None."""
    game_hour = 8 + game_minutes_since_8am // 60
    matches = np.where(heatmap.hours == game_hour)[0]
    if matches.size == 0:
        return None
    return heatmap.counts[int(matches[0])]


def _cell_center_world(heatmap: _Heatmap, cy: int, cx: int) -> Point:
    half = heatmap.cell_size // 2
    return (cx * heatmap.cell_size + half, cy * heatmap.cell_size + half)


def hottest_spot(time_minutes: int | None, *, avoid: Point | None = None,
                 avoid_radius: int = 64) -> Point | None:
    """World point at the center of the most-occupied cell for the current game
    hour, excluding cells within ``avoid_radius`` of ``avoid`` (so we don't keep
    picking the spot we're already standing on). None if no heatmap is baked or
    the hour is unknown.

    ``time_minutes`` is minutes-since-8AM (Cady's clock convention)."""
    if time_minutes is None:
        return None
    heatmap = _load()
    if heatmap is None:
        return None
    grid = _hour_row(heatmap, time_minutes)
    if grid is None or not grid.any():
        return None

    order = np.argsort(grid, axis=None)[::-1]  # cells by descending occupancy
    cells_x = grid.shape[1]
    for flat in order:
        count = grid.flat[flat]
        if count <= 0:
            break
        cy, cx = divmod(int(flat), cells_x)
        spot = _cell_center_world(heatmap, cy, cx)
        if avoid is not None:
            if (spot[0] - avoid[0]) ** 2 + (spot[1] - avoid[1]) ** 2 <= avoid_radius ** 2:
                continue
        return spot
    return None


def is_available() -> bool:
    """Whether a baked heatmap is present (else callers keep their fallback)."""
    return _load() is not None


__all__ = ["hottest_spot", "is_available"]
