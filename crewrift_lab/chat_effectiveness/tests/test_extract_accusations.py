import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
SUSPICION_TOOLS = Path(__file__).resolve().parents[2] / "suspicion_lab" / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(SUSPICION_TOOLS))

from extract_accusations import extract_accusation_rows  # noqa: E402
from replay_parse import ChatLine, Game, Meeting, PlayerInfo, StateSample, Vote  # noqa: E402


def _game_with_one_meeting() -> Game:
    players = {
        0: PlayerInfo(slot=0, name="P0", color="red", role="crew"),
        1: PlayerInfo(slot=1, name="P1", color="blue", role="imposter"),
        2: PlayerInfo(slot=2, name="P2", color="green", role="crew"),
    }
    states = {
        slot: [StateSample(tick=0, x=0, y=0, room="hall", alive=True, connected=True)]
        for slot in players
    }
    meeting = Meeting(
        call_tick=100,
        caller_slot=0,
        kind="body",
        votes=[
            Vote(tick=110, voter_slot=0, target_slot=1),
            Vote(tick=111, voter_slot=2, target_slot=1),
        ],
        chats=[
            # "blue sus, saw them vent" -> P0 accuses P1 (the actual imposter)
            ChatLine(tick=101, slot=0, text="blue sus, saw them vent"),
        ],
        ejected_slot=1,
        end_tick=120,
    )
    return Game(
        episode="test_ep",
        config={},
        players=players,
        states=states,
        visibility={},
        body_visibility={},
        kills=[],
        bodies=[],
        ejections=[(120, 1)],
        meetings=[meeting],
        task_completions=[],
        vents=[],
        task_sites=[],
        tick_count=120,
        complete=True,
    )


def test_extract_accusation_rows_joins_ground_truth_and_meeting_outcome():
    game = _game_with_one_meeting()

    rows = extract_accusation_rows(game)

    assert len(rows) == 1
    row = rows[0]
    assert row["episode"] == "test_ep"
    assert row["speaker_slot"] == 0
    assert row["speaker_role"] == "crew"
    assert row["stance"] == "accuses"
    assert row["target_slot"] == 1
    assert row["target_role"] == "imposter"
    assert row["target_is_imposter"] is True
    assert row["target_voted_same_meeting"] is True
    assert row["target_ejected_same_meeting"] is True
    assert row["num_candidates"] == 2  # P1 and P2, excluding the speaker P0


def test_extract_accusation_rows_returns_empty_for_no_meetings():
    game = _game_with_one_meeting()
    game.meetings = []

    assert extract_accusation_rows(game) == []


def test_extract_accusation_rows_detects_ejection_even_when_meeting_ejected_slot_is_none():
    """Regression test for a real replay_parse.py ordering bug (found via a live
    200-episode run: 0/73 meetings ever had Meeting.ejected_slot set). The
    `phase: Playing/GameOver` event that closes a meeting fires at the SAME
    tick as the `died` event but is processed first in the event stream, so
    Meeting.ejected_slot is never populated in practice. extract_accusation_rows
    must derive ejection from game.ejections (the raw list, reliably populated)
    instead of trusting Meeting.ejected_slot.
    """
    game = _game_with_one_meeting()
    game.meetings[0].ejected_slot = None  # simulates the real, always-unset field

    rows = extract_accusation_rows(game)

    assert len(rows) == 1
    assert rows[0]["target_ejected_same_meeting"] is True
