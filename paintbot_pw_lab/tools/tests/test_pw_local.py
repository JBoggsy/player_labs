"""Contracts of pw_local.py that do not need the engine: seeds, seat/team identity, outcome score,
per-match rows and the summary statistics."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pw_local  # noqa: E402


def test_parse_seeds_ranges_and_lists():
    assert pw_local.parse_seeds("1-3,9, 12-13") == [1, 2, 3, 9, 12, 13]
    assert pw_local.parse_seeds("7") == [7]
    for bad in ("", "5-3", "1,1", "1-3,2", str(2**31)):
        with pytest.raises(ValueError):
            pw_local.parse_seeds(bad)


def test_seat_policies_follow_team_parity():
    even = pw_local.seat_policies(0)
    odd = pw_local.seat_policies(1)
    assert len(even) == 16
    assert all(even[s] == ("A" if s % 2 == 0 else "B") for s in range(16))
    assert all(odd[s] != even[s] for s in range(16))


def test_elo_outcome_clamps_at_margin_scale_1000():
    assert pw_local.elo_outcome(0, 0) == 0.5
    assert pw_local.elo_outcome(600, 0) == pytest.approx(0.8)
    assert pw_local.elo_outcome(0, 600) == pytest.approx(0.2)
    assert pw_local.elo_outcome(5000, 0) == 1.0
    assert pw_local.elo_outcome(0, 5000) == 0.0


def test_match_record_maps_team_results_to_a():
    results = [2453, 0, 603, 0, 900, 232.9, 7, 2]  # team 0 won with 603 glory
    a_even = pw_local.match_record(7, 0, results)
    assert (a_even["result_a"], a_even["winner_policy"], a_even["a_glory"], a_even["b_glory"]) == ("win", "A", 603, 0)
    assert a_even["a_outcome"] == pytest.approx(0.8015)
    a_odd = pw_local.match_record(7, 1, results)
    assert (a_odd["result_a"], a_odd["winner_policy"], a_odd["a_glory"]) == ("loss", "B", 0)
    assert a_odd["a_outcome"] == pytest.approx(1 - 0.8015)


def test_match_record_draw_has_no_winner():
    row = pw_local.match_record(3, 0, [14400, -1, 0, 0, 450, 450, 5, 5])
    assert (row["result_a"], row["winner"], row["winner_policy"], row["a_outcome"]) == ("draw", None, None, 0.5)


def test_summarize_counts_sides_and_seed_balance():
    rows = [pw_local.match_record(1, 0, [100, 0, 400, 0, 900, 0, 5, 0]),
            pw_local.match_record(1, 1, [100, 0, 400, 0, 900, 0, 5, 0]),
            pw_local.match_record(2, 0, [100, -1, 0, 0, 1, 1, 0, 0])]
    summary = pw_local.summarize(rows)
    assert summary["all"]["n"] == 3
    assert (summary["all"]["wins"], summary["all"]["draws"], summary["all"]["losses"]) == (1, 1, 1)
    assert summary["a_side_0"]["n"] == 2 and summary["a_side_1"]["n"] == 1
    # Only seed 1 has both sides; a policy against itself balances to exactly 0.5 per seed.
    assert summary["seed_balanced"]["n_seeds"] == 1
    assert summary["seed_balanced"]["mean_outcome"] == pytest.approx(0.5)
    assert summary["all"]["ci95_low"] < summary["all"]["mean_outcome"] < summary["all"]["ci95_high"]


def test_mean_ci_unknown_is_none():
    assert pw_local.mean_ci([]) == {"mean_outcome": None, "ci95_low": None, "ci95_high": None}
    assert pw_local.mean_ci([0.7])["ci95_low"] is None


def test_identical_play_needs_equal_hashes_on_both_sides_of_every_seed():
    same = [{"seed": s, "a_side": side, "final_hash": 100 + s} for s in (1, 2) for side in (0, 1)]
    assert pw_local.identical_play(same)
    differs = same[:-1] + [{"seed": 2, "a_side": 1, "final_hash": 999}]
    assert not pw_local.identical_play(differs)
    assert not pw_local.identical_play(same[:1])       # one side only (a `match`): unknown, not identical
    assert not pw_local.identical_play([])
