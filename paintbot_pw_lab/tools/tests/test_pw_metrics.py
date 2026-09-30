"""Metric definitions in pw_metrics that downstream A/B and mining rely on."""
import sys
from pathlib import Path

import pandas as pd
import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import pw_episodes as pe  # noqa: E402
import pw_metrics as pm  # noqa: E402

SAMPLE = TOOLS.parent / "episode_data" / "20260928T214433_ereq_5092af64-d3"
BINARY = TOOLS / "bin" / pe.DEFAULT_TAG / "pw_trace"


def test_elo_outcome_uses_margin_scale_and_clamps():
    assert pm.elo_outcome(542, 0) == pytest.approx(0.771)
    assert pm.elo_outcome(0, 542) == pytest.approx(0.229)
    assert pm.elo_outcome(0, 0) == 0.5
    assert pm.elo_outcome(3000, 0) == 1.0 and pm.elo_outcome(0, 3000) == 0.0


def kill(t, seat, victim):
    return {"t": t, "seat": seat, "team": seat % 2, "victim": victim, "victim_team": victim % 2,
            "friendly": seat % 2 == victim % 2, "self": seat == victim}


def test_trades_count_revenge_kills_within_the_window():
    kills = pd.DataFrame([
        kill(100, 1, 0),   # enemy 1 kills our 0 ...
        kill(150, 2, 1),   # ... and our 2 kills 1 within 72 ticks: a trade
        kill(300, 3, 4),   # enemy 3 kills our 4 ...
        kill(400, 6, 3),   # ... avenged too late (100 ticks)
        kill(500, 5, 5),   # a self kill is never a trade
    ])
    trade_kills, deaths_traded = pm.trades(kills)
    assert trade_kills.to_dict() == {2: 1}
    assert deaths_traded.to_dict() == {0: 1}


def test_heart_ticks_follow_capture_ownership():
    ep = {
        "episodes": pd.DataFrame([{"ticks": 100}]),
        "heart_states": pd.DataFrame([{"t": 0, "heart": 0, "owner": 0}, {"t": 0, "heart": 1, "owner": -1}]),
        "captures": pd.DataFrame([{"t": 40, "kind": "capture_complete", "heart": 0, "team": 1},
                                  {"t": 10, "kind": "capture_complete", "heart": 1, "team": 0},
                                  {"t": 20, "kind": "capture_start", "heart": 0, "team": 1}]),
    }
    # heart 0: team 0 scores ticks 1..39 (39), team 1 ticks 40..100 (61); heart 1: team 0 ticks 10..100 (91)
    assert pm.heart_ticks(ep) == {0: 39 + 91, 1: 61}


def test_policy_rows_sum_seats_and_mirror_policies_have_no_outcome():
    seats = pd.DataFrame([
        {"policy_key": "A", "policy_version_id": "A", "policy_name": "a", "team": 0, "shots": 10, "gun_hits": 5,
         "gun_hits_enemy": 4, "kills": 2, "deaths": 1, "alive_ticks": 90, "heart_reach_ticks": 9,
         "idle_ticks": 0, "decision_ticks": 90, "vm_disabled_suspect": False},
        {"policy_key": "A", "policy_version_id": "A", "policy_name": "a", "team": 0, "shots": 0, "gun_hits": 0,
         "gun_hits_enemy": 0, "kills": 0, "deaths": 1, "alive_ticks": 50, "heart_reach_ticks": 5,
         "idle_ticks": 5, "decision_ticks": 50, "vm_disabled_suspect": True},
        {"policy_key": "B", "policy_version_id": "B", "policy_name": "b", "team": 1, "shots": 4, "gun_hits": 1,
         "gun_hits_enemy": 1, "kills": 1, "deaths": 2, "alive_ticks": 100, "heart_reach_ticks": 0,
         "idle_ticks": 0, "decision_ticks": 100, "vm_disabled_suspect": False},
        {"policy_key": "B", "policy_version_id": "B", "policy_name": "b", "team": 0, "shots": 0, "gun_hits": 0,
         "gun_hits_enemy": 0, "kills": 0, "deaths": 0, "alive_ticks": 100, "heart_reach_ticks": 0,
         "idle_ticks": 0, "decision_ticks": 100, "vm_disabled_suspect": False},
    ])
    ep = {"episodes": pd.DataFrame([{"episode_id": "e", "ticks": 100, "glory_0": 500, "glory_1": 0, "winner": 0}])}
    rows = pm.policy_metrics(ep, seats).set_index("policy_key")
    a = rows.loc["A"]
    assert a.seats == 2 and a.shots == 10 and a.gun_accuracy == 0.5   # (5+0)/(10+0), not a mean of ratios
    assert a.kd == 1.0 and a.idle_share == pytest.approx(5 / 140) and a.vm_disabled_suspect_seats == 1
    assert a.result == "win" and a.elo_outcome == pytest.approx(0.75) and a.winning_glory == 500
    assert pd.isna(rows.loc["B"].result) and pd.isna(rows.loc["B"].elo_outcome) and pd.isna(rows.loc["B"].team)


@pytest.mark.skipif(not (SAMPLE.is_dir() and BINARY.is_file()), reason="sample episode or pw_trace build missing")
def test_sample_episode_metrics_are_consistent():
    ep = pe.load_episode(SAMPLE)
    seats = pm.seat_metrics(ep)
    teams = pm.team_metrics(ep, seats)   # raises if glory composition or meter identities fail
    policies = pm.policy_metrics(ep, seats)
    assert len(seats) == 16 and len(policies) == 2 and len(teams) == 2
    assert policies.kills.sum() == teams.kills.sum() == seats.kills.sum()
    assert (policies.shots.sum(), policies.gun_hits.sum()) == (len(ep["shots"]), ep["shots"].hit.sum())
    winner = teams[teams.result == "win"].iloc[0]
    assert winner.glory_ours == 542 and winner.elo_outcome == pytest.approx(0.771)
    band_shots = sum(seats[f"gun_shots_band_{pm._band_name(b)}"].sum() for b in pm.DISTANCE_BANDS)
    assert band_shots <= seats.shots.sum()
    assert seats.vm_errors.isna().all()   # league episodes carry no seat logs: unknown, not zero


@pytest.mark.skipif(not (SAMPLE.is_dir() and BINARY.is_file()), reason="sample episode or pw_trace build missing")
def test_contests_count_every_contest_start_for_both_teams():
    # A contest that begins with no capture in progress has team null; it still counts.
    ep = pe.load_episode(SAMPLE)
    caps = ep.tables["captures"]
    base = int((caps.kind == "contest_start").sum())
    extra = pd.DataFrame([{"t": 100, "kind": "contest_start", "heart": 0, "team": None},
                          {"t": 200, "kind": "contest_start", "heart": 1, "team": 1}])
    ep.tables["captures"] = pd.concat([caps, extra], ignore_index=True)
    teams = pm.team_metrics(ep, pm.seat_metrics(ep))
    assert list(teams.contests) == [base + 2, base + 2]
