"""Miner adapter contract: never = last tick + 1, unknown stays absent, score parts excluded."""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
MINER = TOOLS.parents[1] / ".claude" / "skills" / "coworld-hypothesis-miner" / "scripts"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(MINER))
import features  # noqa: E402


def row(**overrides):
    base = {
        "episode_id": "local:e1", "policy_key": "local:a.bas", "team": 0, "opponents": ["local:b.bas"],
        "source": "local", "ticks": 2880, "result": "win", "score_kind": "elo", "score": 0.75,
        "metrics": {"shots": 100, "gun_shots_band_3500_5250": 40, "kills": 10, "deaths": 0, "kd": None,
                    "deaths_traded": 0, "alive_ticks": 20000, "water_ticks": 500, "grenade_throws": 0,
                    "grenade_blasts_effective": 0, "glory_hearts_taken": 2, "captures_completed": 4},
        "team_metrics": {"first_capture_tick": 300, "capture_starts": 0, "capture_resets": 0, "contests": 0,
                         "hearts_held_mean": 3.0, "longest_supply_gap_ticks": 720, "cogs_out_end": 0,
                         "team_lives_end": 30},
        "timing": {"first_kill_tick": 200, "first_death_tick": None, "enemy_first_death_tick": 200,
                   "first_heart_lost_tick": None, "first_friendly_hit_tick": None},
        "intent": None,
    }
    base.update(overrides)
    return base


def test_never_is_last_tick_plus_one_and_score_is_scaled():
    episode = features.adapter(row())
    assert episode.features["first_death_tick"] == 2881.0
    assert episode.features["first_heart_lost_tick"] == 2881.0
    assert episode.features["first_capture_tick"] == 300.0
    assert episode.features["first_blood"] == 1.0
    assert episode.score == 75.0
    assert episode.episode_id == "local:e1:local:a.bas"


def test_zero_denominators_and_missing_logs_are_absent_not_zero():
    f = features.adapter(row()).features
    for name in ("trade_share", "grenade_effective_share", "capture_reset_share", "kd",
                 "vm_error_logged", "intent_share_fight"):
        assert name not in f
    assert f["long_range_shot_share"] == 0.4
    assert f["kills_per_min"] == 5.0


def test_score_components_are_excluded_per_score_kind():
    elo = features.adapter(row()).features
    for name in features.SCORE_COMPONENTS["elo"]:
        assert name not in elo
    win = features.adapter(row(score_kind="win", score=1.0)).features
    assert "match_minutes" in win and "glory_hearts_per_min" in win
    for name in ("hearts_held_mean", "captures_completed_per_min", "cogs_out_end", "team_lives_end"):
        assert name not in win


def test_mirror_or_unscored_rows_are_dropped():
    assert features.adapter(row(score=None)) is None


def test_every_feature_the_adapter_can_emit_has_meta():
    full = row(intent={"vm_errors": 0, "intent_lines": 10, "heart_switches": 2, "mode_share_retreat": 0.1,
                       "mode_share_supply": 0.2, "mode_share_fight": 0.5, "mode_share_heart": 0.2},
               score_kind="none")
    full["metrics"].update(deaths=5, kd=2.0, deaths_traded=1, grenade_throws=2, grenade_blasts_effective=1)
    full["team_metrics"].update(capture_starts=3, capture_resets=1)
    full["fights"] = {"engagements": 10, "engagements_won": 6, "engagements_first_hit": 5, "engagements_outnumbered": 2,
                      "won_when_outnumbered": 1, "opening_duels": 3, "opening_duels_won": 2}
    full["flags"] = {"stuck": 1, "oscillating": 0, "idle_alive": 0, "death_alone": 2, "heart_lost_with_allies": 1,
                     "wasted_grenade": 1, "long_wade": 0}
    emitted = features.adapter(full).features
    assert set(emitted) <= set(features.METAS)
    assert {"engagement_win_share", "death_alone_per_min", "intent_share_fight"} <= set(emitted)


def test_rules49_pickups_count_in_all_supplies():
    data = row()
    data['metrics'].update(pickups_mister=1, pickups_sniper=2, pickups_radar=3)
    assert features.adapter(data).features['pickups_per_min'] == 3.0
