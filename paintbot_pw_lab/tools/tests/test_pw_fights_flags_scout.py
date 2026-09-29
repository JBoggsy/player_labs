"""Contracts of pw_fights, pw_flags and pw_scout that reports and diagnosis rely on.

Synthetic tables pin the grouping/statistics rules; the integration test runs every
builder on a traced sample league replay and skips when the build or sample is absent.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import pw_episodes as pe  # noqa: E402
import pw_fights as pfi  # noqa: E402
import pw_flags as pfl  # noqa: E402
import pw_metrics as pm  # noqa: E402
import pw_scout as ps  # noqa: E402

SAMPLE = TOOLS.parent / "episode_data" / "20260928T214433_ereq_5092af64-d3"
BINARY = TOOLS / "bin" / pe.DEFAULT_TAG / "pw_trace"
needs_sample = pytest.mark.skipif(not (SAMPLE.is_dir() and BINARY.is_file()),
                                  reason="sample episode or pw_trace build missing")


class FakeEpisode(dict):
    meta = {"hearts": [{"idx": 0, "pos": [0, 0]}]}


def hit(t, seat, victim, ax, vx, killed=False, hp=1):
    return {"t": t, "seat": seat, "team": seat % 2, "victim": victim, "victim_team": victim % 2, "weapon": "gun",
            "hp_removed": hp, "armor_absorbed": 0, "killed": killed, "friendly": seat % 2 == victim % 2,
            "self": seat == victim, "distance": abs(ax - vx), "attacker_x": ax, "attacker_z": 0,
            "victim_x": vx, "victim_z": 0}


def fake_episode(damage_rows):
    return FakeEpisode({
        "episodes": pd.DataFrame([{"episode_id": "e", "ticks": 1000}]),
        "damage": pd.DataFrame(damage_rows),
        "seats": pd.DataFrame({"seat": range(8), "team": [s % 2 for s in range(8)]}),
        "visibility": pd.DataFrame(columns=["t", "seat", "sees"]),
        "captures": pd.DataFrame(columns=["t", "kind", "heart", "team"]),
    })


def test_engagements_join_by_time_and_distance_and_pick_a_winner():
    ep = fake_episode([
        hit(100, 0, 1, 0, 500),                  # fight A starts
        hit(130, 3, 2, 900, 1400),               # 30 ticks later, 400 units from A's victim: joins A
        hit(140, 1, 0, 500, 0, killed=True),     # shares seats with A: joins, team 1 kills
        hit(190, 5, 4, 20000, 21000),            # far away in space: a separate engagement
        hit(400, 0, 1, 0, 500),                  # 260 ticks after A's last event: a new engagement
        hit(401, 1, 0, 500, 0),                  # same tick-ish, equal kills and hp: draw
    ])
    fights = pfi.engagements(ep)
    assert list(fights.events) == [3, 1, 2]
    a = fights.iloc[0]
    assert (a.n_0, a.n_1, a.first_hit_team, a.kills_1, a.winner) == (2, 2, 0, 1, 1)
    assert fights.iloc[2].winner == pfi.DRAW
    assert fights.first_sight_t.isna().all() and not fights.vision_sampled.any()   # unknown, not 0


def test_friendly_and_self_damage_never_make_an_engagement():
    ep = fake_episode([hit(10, 0, 2, 0, 100), hit(20, 1, 1, 0, 0)])
    assert len(pfi.engagements(ep)) == 0


def kill(t, seat, victim):
    return {"t": t, "seat": seat, "team": seat % 2, "victim": victim, "victim_team": victim % 2,
            "friendly": seat % 2 == victim % 2, "self": seat == victim}


def test_trade_events_match_the_metric_definition():
    kills = pd.DataFrame([kill(100, 1, 0), kill(150, 2, 1), kill(300, 3, 4), kill(400, 6, 3), kill(500, 5, 5)])
    trades = pfi.trade_events(kills)
    assert trades[["victim", "killer", "avenger", "trade_ticks"]].values.tolist() == [[0, 1, 2, 50]]
    trade_kills, deaths_traded = pm.trades(kills)
    assert trade_kills.to_dict() == {2: 1} and deaths_traded.to_dict() == {0: 1}


def test_sighting_streak_is_censored_at_the_lookback():
    lookback = pfi.SIGHTING_LOOKBACK_TICKS
    assert pfi.sighting_streak_start({1000: True, 988: True, 976: False}, 1000) == (988, False)
    assert pfi.sighting_streak_start({1000: False, 988: True}, 1000) == (None, False)
    always = {t: True for t in range(1000 - lookback, 1001, 12)}
    assert pfi.sighting_streak_start(always, 1000) == (1000 - lookback, True)


def test_flag_runs_and_friendly_fire_merging():
    assert pfl._runs([False, True, True, False, True]) == [(1, 2), (4, 4)]
    ep = FakeEpisode({
        "episodes": pd.DataFrame([{"episode_id": "e", "ticks": 1000}]),
        "seats": pd.DataFrame({"seat": range(4), "team": [0, 1, 0, 1], "policy_key": ["a", "b", "a", "b"]}),
        "damage": pd.DataFrame([hit(10, 0, 2, 0, 50), hit(30, 0, 2, 0, 50, killed=True), hit(500, 0, 2, 0, 50)]),
    })
    flags = pfl.friendly_fire_flags(ep)
    assert [(f["t_start"], f["t_end"]) for f in flags] == [(10, 30), (500, 500)]
    assert json.loads(flags[0]["detail"])["kills"] == 1


def test_zero_glory_win_is_flagged_only_for_the_winner_at_zero():
    base = {"episode_id": "e", "ticks": 900, "winner": 1, "glory_0": 0}
    seats = pd.DataFrame({"seat": [0, 1], "team": [0, 1], "policy_key": ["a", "b"]})
    assert pfl.zero_glory_flags(FakeEpisode({"episodes": pd.DataFrame([{**base, "glory_1": 0}]), "seats": seats}))
    assert not pfl.zero_glory_flags(FakeEpisode({"episodes": pd.DataFrame([{**base, "glory_1": 10}]), "seats": seats}))


def test_wilson_interval():
    assert ps.wilson(0, 0) == (None, None)
    low, high = ps.wilson(3, 3)
    assert low == pytest.approx(0.4385, abs=1e-3) and high == 1.0
    low, high = ps.wilson(5, 10)
    assert low == pytest.approx(0.2366, abs=1e-3) and high == pytest.approx(0.7634, abs=1e-3)


def test_shout_templates_split_numbers_out_of_words():
    assert ps.shout_template("FIRE22 1137 -1763") == ("FIRE<n> <n> <n>", [22.0, 1137.0, -1763.0])
    assert ps.shout_template("Grenade out!") == ("Grenade out!", [])


def test_slot_hints_name_the_tracked_field_and_leave_unknown_as_none():
    context = pd.DataFrame({field: [0.0] * 6 for field in ps.SLOT_CANDIDATES})
    context["aim_x"] = [100, 900, 1500, 2200, 3000, 4100]
    numbers = [[22, x + 30] for x in context.aim_x]
    hints = ps.slot_hints(context, numbers)
    assert hints[0]["tracks"] is None and hints[0]["distinct"] == 1      # constant: no guess
    assert hints[1]["tracks"] == "aim_x" and hints[1]["median_error"] == 30


def test_sides_exclude_mirror_and_mixed_teams():
    def ep(keys):
        return FakeEpisode({"seats": pd.DataFrame({"seat": range(4), "team": [0, 1, 0, 1], "policy_key": keys,
                                                   "policy_name": keys, "policy_version": [1] * 4})})
    rows, reason = ps.sides(ep(["a", "b", "a", "b"]), "version")
    assert reason is None and [r["label"] for r in rows] == ["a:v1", "b:v1"]
    assert ps.sides(ep(["a", "a", "a", "a"]), "version")[1] == "mirror"
    assert ps.sides(ep(["a", "b", "c", "b"]), "version")[1] == "mixed_team"


@needs_sample
def test_sample_episode_builders_are_consistent():
    ep = pe.load_episode(SAMPLE)
    hearts, _pickups = ps.mirror_maps(ep.meta)
    assert hearts[0] == 1 and hearts[1] == 0 and all(hearts[hearts[k]] == k for k in hearts)   # an involution
    fights = pfi.engagements(ep)
    enemy = ep["damage"][ep["damage"].seat.notna() & ~ep["damage"].friendly & ~ep["damage"]["self"]]
    assert fights.events.sum() == len(enemy)            # every enemy damage event in exactly one engagement
    policy = pfi.fight_policy_metrics(ep)
    trade_kills, _ = pm.trades(ep["kills"])
    assert policy.trade_kills.sum() == trade_kills.sum()
    flags = pfl.episode_flags(ep)
    assert set(flags.flag) <= set(pfl.FLAG_NAMES) and flags.t_start.le(flags.t_end).all()
    # Sampled idle agrees with the exact counter: no idle decision ticks means no idle flag.
    if ep["seats"].idle_ticks.sum() == 0:
        assert not (flags.flag == "idle_alive").any()


@needs_sample
def test_flags_cli_top_zero_prints_counts_only_and_json_lists_them(capfd):
    assert pfl.main([str(SAMPLE), "--top", "0"]) == 0
    out = capfd.readouterr().out
    assert "Empty DataFrame" not in out and "flag counts:" in out
    assert pfl.main([str(SAMPLE), "--top", "0", "--json"]) == 0
    data = json.loads(capfd.readouterr().out)
    assert data["ok"] and data["result"]["rows"] == [] and data["result"]["rows_total"] > 0
    assert sum(data["result"]["flag_counts"].values()) == data["result"]["rows_total"]


@needs_sample
def test_unknown_policy_is_exit_2_listing_valid_values(capfd):
    for main in (pfl.main, pfi.main, pm.main):
        assert main([str(SAMPLE), "--policy", "nobody", "--json"]) == 2
        data = json.loads(capfd.readouterr().out)
        assert "richard-paintbot-pw" in data["result"]["valid"] and data["failures"][0]["code"] == "usage_error"
