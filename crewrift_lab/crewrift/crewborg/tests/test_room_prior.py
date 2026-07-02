"""Empirical room-density prior tests (strategy/room_prior.py).

The prior is failure-tolerant by contract: a missing/malformed table or an
unknown room disables it (weight 0.0) — Search must degrade to live-evidence
scoring, never crash.
"""

from __future__ import annotations

import json

import pytest

from crewrift.crewborg.map import load_croatoan_map
from crewrift.crewborg.strategy import room_prior


def _raw(share: dict[str, list[float]], bucket_ticks: int = 600) -> dict:
    n_bands = len(next(iter(share.values())))
    return {
        "schema": "crewborg-room-density/v1",
        "bucket_ticks": bucket_ticks,
        "bucket_start_ticks": [band * bucket_ticks for band in range(n_bands)],
        "share": share,
    }


@pytest.fixture(autouse=True)
def _restore_prior_table():
    saved = room_prior._DENSITY
    yield
    room_prior._DENSITY = saved


def test_vendored_table_loads_and_covers_the_croatoan_rooms() -> None:
    table = room_prior._load_density()
    assert table is not None
    map_rooms = {room.name for room in load_croatoan_map().rooms}
    assert map_rooms <= set(table["share_norm"])  # every map room has a prior column


def test_missing_bad_or_disabled_file_disables_the_prior(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CREWBORG_ROOM_DENSITY", str(tmp_path / "nope.json"))
    assert room_prior._load_density() is None

    wrong_schema = tmp_path / "wrong.json"
    wrong_schema.write_text(json.dumps({"schema": "something-else/v9"}))
    monkeypatch.setenv("CREWBORG_ROOM_DENSITY", str(wrong_schema))
    assert room_prior._load_density() is None

    garbage = tmp_path / "garbage.json"
    garbage.write_text("{not json")
    monkeypatch.setenv("CREWBORG_ROOM_DENSITY", str(garbage))
    assert room_prior._load_density() is None

    monkeypatch.setenv("CREWBORG_ROOM_DENSITY", "0")
    assert room_prior._load_density() is None


def test_env_override_points_at_a_custom_table(monkeypatch, tmp_path) -> None:
    custom = tmp_path / "density.json"
    custom.write_text(json.dumps(_raw({"A": [0.5], "B": [0.5]})))
    monkeypatch.setenv("CREWBORG_ROOM_DENSITY", str(custom))
    table = room_prior._load_density()
    assert table is not None and set(table["share_norm"]) == {"A", "B"}


def test_share_prior_is_max_normalized_within_each_band() -> None:
    room_prior.set_density(_raw({"A": [0.75, 0.2], "B": [0.25, 0.6]}))
    assert room_prior.room_share_prior("A", 0) == 1.0          # band 0 max
    assert room_prior.room_share_prior("B", 0) == pytest.approx(0.25 / 0.75)
    assert room_prior.room_share_prior("B", 700) == 1.0        # band 1 max
    assert room_prior.room_share_prior("A", 700) == pytest.approx(0.2 / 0.6)


def test_band_clamps_to_the_table_ends() -> None:
    room_prior.set_density(_raw({"A": [1.0, 0.1], "B": [0.5, 1.0]}))
    # Way past the last band start ⇒ keep using the last band's distribution.
    assert room_prior.room_share_prior("A", 10**9) == pytest.approx(0.1)
    # A (nonsensical) negative tick clamps to band 0 rather than indexing backwards.
    assert room_prior.room_share_prior("A", -5) == 1.0


def test_unknown_room_and_disabled_prior_score_zero() -> None:
    room_prior.set_density(_raw({"A": [1.0]}))
    assert room_prior.room_share_prior("Nowhere", 0) == 0.0
    room_prior.set_density(None)
    assert room_prior.room_share_prior("A", 0) == 0.0
