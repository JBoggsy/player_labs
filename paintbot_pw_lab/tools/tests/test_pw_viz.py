"""Contracts in pw_viz / pw_match_report that plots and reports rely on: time parsing,
trail breaks, heart ownership, occupancy overlap, side normalization, moment selection."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import pw_match_report as pr  # noqa: E402
import pw_viz as pv  # noqa: E402


def test_parse_time_accepts_ticks_seconds_and_minutes():
    assert pv.parse_time("1500") == 1500
    assert pv.parse_time("62.5s") == 1500
    assert pv.parse_time("1:10") == 70 * 24
    assert pv.parse_time(None) is None
    with pytest.raises(ValueError):
        pv.parse_time("ten")


def states(rows):
    return pd.DataFrame(rows, columns=["t", "x", "z", "alive"])


def test_trails_break_at_death_and_respawn():
    rows = states([(0, 0, 0, True), (6, 10, 0, True), (12, 10, 0, False), (18, 10, 0, False),
                   (24, 500, 500, True), (30, 510, 500, True)])
    segments = pv.trail_segments(rows, spawn_ticks=[22])
    assert [list(s.t) for s in segments] == [[0, 6], [24, 30]]


def test_trails_break_at_a_respawn_between_two_alive_samples():
    # died and respawned between samples: no dead row, but the spawn tick splits the line
    rows = states([(0, 0, 0, True), (6, 10, 0, True), (12, 900, 900, True)])
    assert [list(s.t) for s in pv.trail_segments(rows, spawn_ticks=[11])] == [[0, 6], [12]]


class FakeEpisode:
    def __init__(self, tables, meta=None):
        self.tables, self.meta = tables, meta or {}

    def __getitem__(self, name):
        return self.tables[name]


def test_heart_owners_follow_capture_completes_up_to_the_tick():
    ep = FakeEpisode({
        "heart_states": pd.DataFrame({"t": [0, 0], "heart": [0, 1], "owner": [0, -1]}),
        "captures": pd.DataFrame({"t": [100, 200, 300], "kind": ["capture_complete", "capture_start", "capture_complete"],
                                  "heart": [1, 0, 0], "team": [1, 1, 1]}),
    })
    assert pv.heart_owners_at(ep, 99) == {0: 0, 1: -1}
    assert pv.heart_owners_at(ep, 100) == {0: 0, 1: 1}
    assert pv.heart_owners_at(ep, 300) == {0: 1, 1: 1}


def test_bhattacharyya_overlap():
    a = np.array([[1, 0], [0, 1]])
    assert pv.bhattacharyya(a, a * 5) == pytest.approx(1.0)
    assert pv.bhattacharyya(a, np.array([[0, 1], [1, 0]])) == 0.0
    assert pv.bhattacharyya(a, np.zeros((2, 2))) is None  # empty is unknown, not 0


HEARTWICK_LIKE = {"map": "", "homes": [[960, 2000], [5440, 2000]],
                  "hearts": [{"pos": [960, 2000]}, {"pos": [5440, 2000]}, {"pos": [880, -1720]}, {"pos": [5520, 5720]}]}


def test_side_normalization_rotates_azure_only_on_symmetric_maps():
    frame = pd.DataFrame({"team": [0, 1], "x": [5440.0, 5440.0], "z": [2000.0, 2000.0]})
    out = pv.to_ember_side(frame, HEARTWICK_LIKE)
    assert list(out.x) == [5440.0, 960.0] and list(out.z) == [2000.0, 2000.0]
    lopsided = {**HEARTWICK_LIKE, "hearts": HEARTWICK_LIKE["hearts"] + [{"pos": [100, 100]}]}
    with pytest.raises(ValueError):
        pv.symmetry_center(lopsided)


def kill(t, seat, victim):
    return {"t": t, "seat": seat, "team": seat % 2, "victim": victim, "victim_team": victim % 2,
            "friendly": seat % 2 == victim % 2, "self": seat == victim, "victim_x": 0, "victim_z": 0}


def test_kill_bursts_need_three_kills_within_the_gap():
    kills = pd.DataFrame([kill(100, 1, 0), kill(150, 3, 2), kill(200, 1, 4), kill(260, 0, 1),  # burst of 3, lost 1
                          kill(1000, 1, 6), kill(1050, 1, 8)])                              # only 2: not a burst
    bursts = pr.kill_bursts(kills)
    assert [(b["team"], b["start"], b["end"], b["kills"], b["lost"]) for b in bursts] == [(1, 100, 200, 3, 0)]


def test_top_moments_keep_first_captures_and_rank_the_rest_by_swing():
    moments = [{"kind": "first_capture", "t": 500, "swing": 1}, {"kind": "kill_burst", "t": 100, "swing": 3},
               {"kind": "kill_burst", "t": 50, "swing": 1}, {"kind": "elimination", "t": 900, "swing": 10}]
    chosen = pr.top_moments(moments, limit=3)
    assert [(m["kind"], m["t"], m["rank"]) for m in chosen] == [
        ("kill_burst", 100, 1), ("first_capture", 500, 2), ("elimination", 900, 3)]
