"""Offline-baked per-task-station visibility for the static croatoan map.

Search's WATCH camouflage (see ``docs/designs/watch-camouflage.md``) needs to
know, for every task station, which parts of the map are visible from it — so
the imposter can fake a task at the spot that keeps the most crew in view.
Vision here is the same line-of-sight proxy WATCH's vantage scoring already
uses: ``nav._segment_clear`` over the walkability mask, range-capped.

Computing that live is ~16k pure-Python segment walks (seconds under the hosted
250m-CPU cap), so — exactly like :mod:`.navbake` — we bake it **once offline**
(``crewrift_lab/tools/vision_bake.py``) into a vendored asset and load it at
runtime. Loading validates a fingerprint of the walkability mask and the task
count; on any mismatch, missing asset, or load error the caller gets ``None``
and falls back to the nearest task spot — correctness never depends on the
asset, only camo spot quality does.
"""

from __future__ import annotations

import gzip
import hashlib
import pickle
from dataclasses import dataclass
from importlib import resources
from typing import TYPE_CHECKING, Any

import numpy as np

from crewrift.crewborg.agent_tracking import GRID_CELL_SIZE

if TYPE_CHECKING:
    from crewrift.crewborg.map.types import MapData
    from crewrift.crewborg.nav import NavGraph

# Vendored next to croatoan.resources; bumped only by re-running the bake tool.
VISIONBAKE_PACKAGE = "crewrift.crewborg.map"
VISIONBAKE_RESOURCE = "croatoan_visionbake.pkl.gz"

# Bumped when the serialized payload shape changes (old assets are ignored).
VISIONBAKE_FORMAT = 1

# Line-of-sight range (px) for the bake — matches modes/search.VANTAGE_RANGE so
# camo spot scoring and vantage scoring agree on what "can see" means. (Game
# vision is the shadow overlay: pure LOS occlusion, screen-bounded; 360px is
# crewborg's established proxy for that bound.)
VISION_RANGE = 360


@dataclass(frozen=True)
class TaskVisionBake:
    """Per-task-station visibility masks over the occupancy grid.

    ``masks[task_index, row, col]`` is True iff the centre of that
    ``cell_size``-px grid cell is within ``range_px`` of the station's stand
    point and the segment between them is clear of walls.
    """

    cell_size: int
    range_px: int
    masks: np.ndarray            # (n_tasks, rows, cols) bool
    counts: np.ndarray           # (n_tasks,) int — total visible cells per task
    walkability_sha1: str        # fingerprint of the mask baked against
    walkability_shape: tuple[int, int]

    def visible_from(self, task_index: int, xy: tuple[int, int]) -> bool:
        """Whether world point ``xy`` sits in a cell visible from ``task_index``."""

        if not (0 <= task_index < self.masks.shape[0]):
            return False
        col, row = xy[0] // self.cell_size, xy[1] // self.cell_size
        if not (0 <= row < self.masks.shape[1] and 0 <= col < self.masks.shape[2]):
            return False
        return bool(self.masks[task_index, row, col])

    def visible_area(self, task_index: int) -> int:
        """Total visible cells from ``task_index`` (the spot-selection tie-break)."""

        if not (0 <= task_index < self.counts.shape[0]):
            return 0
        return int(self.counts[task_index])


def _walkability_sha1(walkability: np.ndarray) -> str:
    return hashlib.sha1(np.packbits(walkability.astype(bool)).tobytes()).hexdigest()


def build_task_vision(
    walkability: np.ndarray,
    map_data: "MapData",
    nav: "NavGraph",
    *,
    cell_size: int = GRID_CELL_SIZE,
    range_px: int = VISION_RANGE,
) -> TaskVisionBake:
    """Compute the per-task visibility masks (the heavy offline pass).

    Stand points are the stations' baked reachable anchors (where the imposter
    will actually stand — same as ``imposter_common.task_point``), falling back
    to the station centre. A cell counts as visible only if someone could stand
    in it (it contains walkable pixels) — unwalkable wall cells are noise.
    """

    from crewrift.crewborg.nav import _segment_clear  # heavy module; bake-time only

    walkability = walkability.astype(bool)
    height, width = walkability.shape
    rows = (height + cell_size - 1) // cell_size
    cols = (width + cell_size - 1) // cell_size
    n_tasks = len(map_data.tasks)
    masks = np.zeros((n_tasks, rows, cols), dtype=bool)
    range_sq = range_px * range_px

    # A cell is standable if any pixel in it is walkable.
    standable = np.zeros((rows, cols), dtype=bool)
    for row in range(rows):
        for col in range(cols):
            block = walkability[row * cell_size:(row + 1) * cell_size, col * cell_size:(col + 1) * cell_size]
            standable[row, col] = bool(block.any())

    for index, task in enumerate(map_data.tasks):
        anchor = nav.task_anchor(index) or (task.center.x, task.center.y)
        for row in range(rows):
            cy = min(row * cell_size + cell_size // 2, height - 1)
            for col in range(cols):
                if not standable[row, col]:
                    continue
                cx = min(col * cell_size + cell_size // 2, width - 1)
                dx, dy = cx - anchor[0], cy - anchor[1]
                if dx * dx + dy * dy > range_sq:
                    continue
                if _segment_clear(walkability, anchor, (cx, cy)):
                    masks[index, row, col] = True

    return TaskVisionBake(
        cell_size=cell_size,
        range_px=range_px,
        masks=masks,
        counts=masks.sum(axis=(1, 2)).astype(np.int64),
        walkability_sha1=_walkability_sha1(walkability),
        walkability_shape=(height, width),
    )


def serialize_visionbake(bake: TaskVisionBake) -> bytes:
    """Gzip-pickle the bake for vendoring as the asset."""

    payload = {"format": VISIONBAKE_FORMAT, "bake": bake}
    return gzip.compress(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))


def _read_payload() -> dict[str, Any] | None:
    """Load the vendored payload, or ``None`` if unusable (never raises)."""

    try:
        resource = resources.files(VISIONBAKE_PACKAGE).joinpath(VISIONBAKE_RESOURCE)
        if not resource.is_file():
            return None
        payload = pickle.loads(gzip.decompress(resource.read_bytes()))
    except Exception:  # noqa: BLE001 - any load failure must degrade to the fallback.
        return None
    if not isinstance(payload, dict) or payload.get("format") != VISIONBAKE_FORMAT:
        return None
    return payload


def load_visionbake(walkability: np.ndarray, task_count: int) -> TaskVisionBake | None:
    """Return the vendored bake iff it matches ``walkability`` and ``task_count``.

    Any mismatch (a redeployed/different map) returns ``None`` — the caller
    falls back to the nearest task spot rather than trusting stale vision.
    """

    payload = _read_payload()
    if payload is None:
        return None
    bake = payload.get("bake")
    if not isinstance(bake, TaskVisionBake):
        return None
    if bake.masks.shape[0] != task_count:
        return None
    if bake.walkability_shape != walkability.shape:
        return None
    if bake.walkability_sha1 != _walkability_sha1(walkability):
        return None
    return bake
