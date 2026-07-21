import sys
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from metrics import (  # noqa: E402
    crew_accuracy_table,
    effectiveness_table,
    enrich_accusations,
    winrate_association_table,
)

OUTCOMES = pd.DataFrame(
    [
        {"episode": "ep1", "slot": 0, "policy_name": "crewborg", "policy_version": 89, "role": "crew", "win": True, "score": 108},
        {"episode": "ep1", "slot": 1, "policy_name": "notsus", "policy_version": 168, "role": "imposter", "win": False, "score": 20},
        {"episode": "ep2", "slot": 0, "policy_name": "crewborg", "policy_version": 89, "role": "crew", "win": False, "score": 10},
        {"episode": "ep2", "slot": 1, "policy_name": "notsus", "policy_version": 168, "role": "imposter", "win": True, "score": 108},
    ]
)

ACCUSATIONS = pd.DataFrame(
    [
        {
            "episode": "ep1", "meeting_idx": 0, "call_tick": 100, "speaker_slot": 0,
            "speaker_role": "crew", "stance": "accuses", "target_slot": 1,
            "target_role": "imposter", "target_is_imposter": True,
            "target_voted_same_meeting": True, "target_ejected_same_meeting": True,
            "num_candidates": 1,
        },
        {
            "episode": "ep2", "meeting_idx": 0, "call_tick": 100, "speaker_slot": 0,
            "speaker_role": "crew", "stance": "accuses", "target_slot": 1,
            "target_role": "imposter", "target_is_imposter": True,
            "target_voted_same_meeting": False, "target_ejected_same_meeting": False,
            "num_candidates": 1,
        },
    ]
)


def test_enrich_accusations_adds_policy_identity_and_win():
    enriched = enrich_accusations(ACCUSATIONS, OUTCOMES)

    assert list(enriched["speaker_policy"]) == ["crewborg", "crewborg"]
    assert list(enriched["target_policy"]) == ["notsus", "notsus"]
    assert list(enriched["speaker_win"]) == [True, False]


def test_crew_accuracy_table_is_perfect_for_this_fixture():
    enriched = enrich_accusations(ACCUSATIONS, OUTCOMES)

    table = crew_accuracy_table(enriched)

    row = table[table.speaker_policy == "crewborg"].iloc[0]
    assert row["n"] == 2
    assert row["accuracy"] == 1.0


def test_effectiveness_table_reports_half_voted_half_ejected():
    enriched = enrich_accusations(ACCUSATIONS, OUTCOMES)

    table = effectiveness_table(enriched)

    row = table[(table.speaker_policy == "crewborg") & (table.speaker_role == "crew")].iloc[0]
    assert row["n"] == 2
    assert row["p_target_voted"] == 0.5
    assert row["p_target_ejected"] == 0.5


def test_winrate_association_table_includes_zero_accusation_policies():
    enriched = enrich_accusations(ACCUSATIONS, OUTCOMES)

    table = winrate_association_table(enriched, OUTCOMES)

    crewborg_row = table[(table.policy_name == "crewborg") & (table.role == "crew")].iloc[0]
    assert crewborg_row["seat_games"] == 2
    assert crewborg_row["seat_win_rate"] == 0.5
    assert crewborg_row["accusations_made"] == 2
    notsus_row = table[(table.policy_name == "notsus") & (table.role == "imposter")].iloc[0]
    assert notsus_row["accusations_made"] == 0  # notsus never accused anyone in this fixture
