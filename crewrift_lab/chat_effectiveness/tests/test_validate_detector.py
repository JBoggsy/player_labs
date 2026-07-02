import sys
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
SUSPICION_TOOLS = Path(__file__).resolve().parents[2] / "suspicion_lab" / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(SUSPICION_TOOLS))

from replay_parse import ChatLine, Game, Meeting, PlayerInfo  # noqa: E402
from validate_detector import compute_agreement, regex_lines  # noqa: E402


def _game_with_chat() -> Game:
    players = {
        0: PlayerInfo(slot=0, name="P0", color="red", role="crew"),
        1: PlayerInfo(slot=1, name="P1", color="blue", role="imposter"),
    }
    meeting = Meeting(
        call_tick=100,
        caller_slot=0,
        kind="body",
        chats=[ChatLine(tick=101, slot=0, text="blue sus, saw them vent")],
    )
    return Game(
        episode="test_ep", config={}, players=players, states={}, visibility={},
        body_visibility={}, kills=[], bodies=[], ejections=[], meetings=[meeting],
        task_completions=[], vents=[], task_sites=[], tick_count=120, complete=True,
    )


def test_regex_lines_extracts_classifiable_chat():
    rows = regex_lines(_game_with_chat())

    assert len(rows) == 1
    assert rows[0]["episode"] == "test_ep"
    assert rows[0]["speaker_slot"] == 0
    assert rows[0]["tick"] == 101
    assert rows[0]["regex_stance"] == "accuses"
    assert rows[0]["regex_target_slot"] == 1


def test_compute_agreement_matches_on_episode_speaker_tick():
    sample = pd.DataFrame(
        [{"episode": "test_ep", "speaker_slot": 0, "tick": 101, "regex_stance": "accuses", "regex_target_slot": 1}]
    )
    chat_suss = pd.DataFrame(
        [{
            "episode_id": "test_ep", "slot": 0, "ts": 101,
            "is_suss": True, "suss_target_slot": 1,
        }]
    )

    agreement = compute_agreement(sample, chat_suss)

    assert agreement["n_matched"] == 1
    assert agreement["n_sampled"] == 1
    assert agreement["stance_agreement"] == 1.0
    assert agreement["target_agreement"] == 1.0


def test_compute_agreement_handles_no_matches():
    sample = pd.DataFrame(
        [{"episode": "test_ep", "speaker_slot": 0, "tick": 101, "regex_stance": "accuses", "regex_target_slot": 1}]
    )
    chat_suss = pd.DataFrame(columns=["episode_id", "slot", "ts", "is_suss", "suss_target_slot"])

    agreement = compute_agreement(sample, chat_suss)

    assert agreement == {"n_matched": 0, "stance_agreement": None, "target_agreement": None}


def test_compute_agreement_remaps_opaque_episode_id_through_map():
    sample = pd.DataFrame(
        [{"episode": "test_ep", "speaker_slot": 0, "tick": 101, "regex_stance": "accuses", "regex_target_slot": 1}]
    )
    chat_suss_opaque = pd.DataFrame(
        [{
            "episode_id": "ep_opaque_internal", "slot": 0, "ts": 101,
            "is_suss": True, "suss_target_slot": 1,
        }]
    )
    episode_id_map = {"ep_opaque_internal": "test_ep"}

    # Without the map, the opaque id doesn't match the stem -> no match.
    agreement_no_map = compute_agreement(sample, chat_suss_opaque)
    assert agreement_no_map["n_matched"] == 0

    # With the map, the opaque id is remapped to the stem -> matches.
    agreement_with_map = compute_agreement(sample, chat_suss_opaque, episode_id_map)
    assert agreement_with_map["n_matched"] == 1
    assert agreement_with_map["stance_agreement"] == 1.0
    assert agreement_with_map["target_agreement"] == 1.0

    # No-regression check: existing stem-keyed chat_suss still matches
    # correctly with no map passed at all.
    chat_suss_with_stem_ids = pd.DataFrame(
        [{
            "episode_id": "test_ep", "slot": 0, "ts": 101,
            "is_suss": True, "suss_target_slot": 1,
        }]
    )
    agreement_stem = compute_agreement(sample, chat_suss_with_stem_ids)
    assert agreement_stem["n_matched"] == 1
    assert agreement_stem["stance_agreement"] == 1.0
    assert agreement_stem["target_agreement"] == 1.0


def test_compute_agreement_handles_empty_sample():
    sample = pd.DataFrame()
    chat_suss = pd.DataFrame(
        [{
            "episode_id": "test_ep", "slot": 0, "ts": 101,
            "is_suss": True, "suss_target_slot": 1,
        }]
    )

    agreement = compute_agreement(sample, chat_suss)

    assert agreement == {"n_matched": 0, "stance_agreement": None, "target_agreement": None}
