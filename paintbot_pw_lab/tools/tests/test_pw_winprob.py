"""Contracts of pw_winprob.py: team point of view and mirroring, the grouped held-out split, the
event bracket (before/after rows, sign for the acting team), and the saved-model round trip."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pw_winprob  # noqa: E402


def team_states(episode_id="e1", team0_won=1, ticks=48):
    t = np.arange(0, ticks + 1, 6)
    n = len(t)
    return pd.DataFrame({
        "episode_id": episode_id, "source": "local", "t": t, "end_tick": 14400, "target": 21600,
        "hearts": 10, "ticks": ticks, "team0_won": team0_won,
        "meter_ticks_0": t * 2, "meter_ticks_1": t, "hearts_owned_0": 2, "hearts_owned_1": 1,
        "team_lives_0": np.linspace(32, 30, n).round(), "team_lives_1": np.linspace(32, 20, n).round(),
        "cogs_out_0": 0, "cogs_out_1": 1, "glory_0": 600, "glory_1": 640, "winner": -1})


def test_features_mirror_between_teams():
    ts = team_states()
    f0, f1 = pw_winprob.features(ts, 0), pw_winprob.features(ts, 1)
    assert list(f0.columns) == list(pw_winprob.FEATURES)
    assert np.allclose(f0["own_meter"], f1["enemy_meter"]) and np.allclose(f0["own_lives"], f1["enemy_lives"])
    for name in ("glory_diff", "lives_ratio", "hearts_x_time", "race"):
        assert np.allclose(f0[name], -f1[name]), name
    assert set(f0["side"]) == {0.0} and set(f1["side"]) == {1.0}
    assert f0["glory_diff"].iloc[0] == pytest.approx(-0.04)


def test_design_mirrors_labels_and_weighs_each_episode_once():
    ts = pd.concat([team_states("a", 1, 48), team_states("b", 0, 96)], ignore_index=True)
    X, y, groups, weights = pw_winprob.design(ts)
    assert len(X) == 2 * len(ts)
    first = ts["episode_id"] == "a"
    assert set(y[: len(ts)][first.to_numpy()]) == {1} and set(y[len(ts):][first.to_numpy()]) == {0}
    for episode in ("a", "b"):
        assert weights[groups == episode].sum() == pytest.approx(1.0)


def test_sample_rows_drops_the_final_tick():
    ts = team_states(ticks=48)
    rows = pw_winprob.sample_rows(ts, 24)
    assert list(rows["t"]) == [0, 24]


def test_out_of_fold_never_predicts_with_its_own_episode():
    frames = [team_states(f"e{i}", i % 2, 96) for i in range(6)]
    for i, f in enumerate(frames):  # make the winner visible in the lives so the model can learn it
        if i % 2 == 0:
            f["team_lives_0"], f["team_lives_1"] = f["team_lives_1"].to_numpy(), f["team_lives_0"].to_numpy()
    rows = pd.concat(frames, ignore_index=True)
    p, fold_of = pw_winprob.out_of_fold(rows, pw_winprob.FEATURES, folds=3)
    assert p.notna().all() and len(set(fold_of.values())) == 3
    assert set(fold_of) == set(rows["episode_id"])


class FakeEpisode:
    episode_id = "e1"

    def __init__(self, tables):
        self.tables = tables

    def __getitem__(self, name):
        return self.tables[name]


def test_credit_brackets_the_event_and_signs_for_the_acting_team():
    series = pd.DataFrame({"episode_id": "e1", "t": [0, 6, 12, 18], "p_team0": [0.5, 0.5, 0.6, 1.0],
                           "final": [False, False, False, True]})
    kills = pd.DataFrame({"t": [9], "seat": [3], "team": [1], "victim": [4], "victim_team": [0],
                          "weapon": ["gun"], "friendly": [False], "self": [False]})
    captures = pd.DataFrame({"t": [12, 12], "kind": ["capture_complete", "capture_start"], "heart": [1, 2],
                             "team": [0, 1], "seat": [2, pd.NA]})
    events = pw_winprob.credit_events(FakeEpisode({"kills": kills, "captures": captures}), series)
    by_kind = events.set_index("kind")
    # Event at t=9: before = row t=6, after = first row at t>=9 (t=12). Team 1's P fell 0.5 -> 0.4.
    assert (by_kind.loc["kill", "t_before"], by_kind.loc["kill", "t_after"]) == (6, 12)
    assert by_kind.loc["kill", "delta_wp"] == pytest.approx(-0.1)
    assert by_kind.loc["death", "delta_wp"] == pytest.approx(0.1)          # victim on team 0
    # The capture at t=12 shares the (6, 12] bracket with the kill: two facts in it.
    assert by_kind.loc["capture", "delta_wp"] == pytest.approx(0.1)
    assert set(events["bracket_events"]) == {2}
    assert "capture_start" not in set(events["kind"])


def test_worst_minutes_finds_each_teams_largest_drop():
    t = np.arange(0, 3000, 100)
    p = np.full(len(t), 0.5)
    p[t >= 1000] = 0.2      # team 0 drops 0.3 at t=1000
    p[t >= 2500] = 0.9      # team 1 drops 0.7 at t=2500
    worst = pw_winprob.worst_minutes(pd.DataFrame({"t": t, "p_team0": p}))
    assert worst[0][1] == pytest.approx(0.3) and worst[1][1] == pytest.approx(0.7)
    assert worst[1][0] <= 2400 and worst[1][0] >= 2500 - pw_winprob.SWING_WINDOW_TICKS


def test_model_json_round_trip_predicts_identically():
    rows = pd.concat([team_states(f"e{i}", i % 2, 96) for i in range(4)], ignore_index=True)
    X, y, _, w = pw_winprob.design(rows)
    model = pw_winprob.WinModel().fit(X, y, w)
    again = pw_winprob.WinModel.from_json(model.to_json())
    assert np.allclose(model.team0_probability(rows), again.team0_probability(rows))
