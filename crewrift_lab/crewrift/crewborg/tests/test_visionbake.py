"""Task-vision bake tests (visionbake.py + the vendored croatoan asset).

The bake precomputes, per task station, which occupancy-grid cells are visible
(LOS + range) from the station's stand point — WATCH camouflage's spot-scoring
input. Covered: LOS/occlusion correctness, standability filtering, the
serialize/load round trip with every validation rejection, and that the
committed croatoan asset actually loads against the committed nav bake.
"""

from __future__ import annotations

import gzip
import pickle
from pathlib import Path

import numpy as np

from crewrift.crewborg import visionbake
from crewrift.crewborg.map import load_croatoan_map
from crewrift.crewborg.map.types import MapData, MapPoint, MapRect, Room, TaskStation
from crewrift.crewborg.nav import build_nav_graph
from crewrift.crewborg.visionbake import (
    TaskVisionBake,
    build_task_vision,
    load_visionbake,
    serialize_visionbake,
)

CELL = 32


def _walled_map() -> tuple[MapData, np.ndarray]:
    """Two rooms split by a full-height wall spanning grid column 4 exactly."""

    m = MapData(
        width=320, height=96,
        tasks=(
            TaskStation(name="L", x=40, y=44, w=8, h=8),
            TaskStation(name="R", x=260, y=44, w=8, h=8),
        ),
        vents=(),
        rooms=(
            Room(name="Left", x=0, y=0, w=128, h=96),
            Room(name="Right", x=160, y=0, w=160, h=96),
        ),
        button=MapRect(x=4, y=4, w=8, h=8),
        home=MapPoint(x=40, y=48),
    )
    walk = np.ones((m.height, m.width), dtype=bool)
    walk[:, 128:160] = False  # the wall fills grid column 4 (x 128..159)
    return m, walk


def test_bake_respects_walls_range_and_standability() -> None:
    m, walk = _walled_map()
    nav = build_nav_graph(walk, map_data=m)
    bake = build_task_vision(walk, m, nav)

    assert bake.masks.shape == (2, 3, 10)
    # Task L sees its own side of the wall...
    assert bake.visible_from(0, (60, 48))
    # ...but nothing through or beyond it.
    assert not bake.masks[0, :, 4].any()   # the wall column is not standable
    assert not bake.visible_from(0, (260, 48))
    # Symmetrically for task R.
    assert bake.visible_from(1, (280, 48))
    assert not bake.visible_from(1, (60, 48))
    # Counts match the masks (the tie-break input).
    assert bake.visible_area(0) == int(bake.masks[0].sum()) > 0
    # Out-of-range / out-of-map queries are safely False.
    assert not bake.visible_from(5, (60, 48))
    assert not bake.visible_from(0, (-10, -10))
    assert bake.visible_area(5) == 0


def test_range_cap_limits_visibility() -> None:
    m, walk = _walled_map()
    nav = build_nav_graph(walk, map_data=m)
    tight = build_task_vision(walk, m, nav, range_px=40)
    # With a 40px range the far end of the Left room is out of sight.
    assert not tight.visible_from(0, (10, 90))
    assert tight.visible_area(0) < build_task_vision(walk, m, nav).visible_area(0)


def _payload_from(bake: TaskVisionBake) -> dict:
    return pickle.loads(gzip.decompress(serialize_visionbake(bake)))


def test_load_round_trip_and_validation(monkeypatch) -> None:
    m, walk = _walled_map()
    nav = build_nav_graph(walk, map_data=m)
    bake = build_task_vision(walk, m, nav)
    monkeypatch.setattr(visionbake, "_read_payload", lambda: _payload_from(bake))

    loaded = load_visionbake(walk, len(m.tasks))
    assert loaded is not None
    assert np.array_equal(loaded.masks, bake.masks)

    # Wrong task count (a different map bake) -> rejected.
    assert load_visionbake(walk, len(m.tasks) + 1) is None
    # Wrong shape -> rejected.
    assert load_visionbake(np.ones((10, 10), dtype=bool), len(m.tasks)) is None
    # Same shape, one flipped pixel (a redeployed map) -> fingerprint rejects.
    flipped = walk.copy()
    flipped[0, 0] = not flipped[0, 0]
    assert load_visionbake(flipped, len(m.tasks)) is None


def test_load_degrades_to_none_on_unusable_payloads(monkeypatch) -> None:
    m, walk = _walled_map()
    monkeypatch.setattr(visionbake, "_read_payload", lambda: None)
    assert load_visionbake(walk, len(m.tasks)) is None
    monkeypatch.setattr(visionbake, "_read_payload", lambda: {"format": visionbake.VISIONBAKE_FORMAT})
    assert load_visionbake(walk, len(m.tasks)) is None  # payload without a bake


def test_vendored_croatoan_asset_matches_the_vendored_nav_bake() -> None:
    # Regression: the committed vision asset must load against the walkability the
    # committed NAV bake carries (they are baked from the same mask). If this fails,
    # re-run tools/vision_bake.py.
    map_dir = Path(visionbake.__file__).resolve().parent / "map"
    nav_payload = pickle.loads(gzip.decompress((map_dir / "croatoan_navbake.pkl.gz").read_bytes()))
    walkability = nav_payload["nav"].walkability
    bake = load_visionbake(walkability, len(load_croatoan_map().tasks))
    assert bake is not None
    assert bake.masks.shape[0] == 41
    assert all(bake.visible_area(i) > 0 for i in range(41))  # every station sees somewhere
