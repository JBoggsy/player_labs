"""Meeting LLM context and decision schema tests."""

from __future__ import annotations

import pytest

from crewrift.crewborg.perception.entities import VoteCandidate, VoteDot, VotingState
from crewrift.crewborg.strategy import suspicion as suspicion_module
from crewrift.crewborg.strategy.meeting import (
    VOTE_SKIP,
    MeetingDecision,
    MeetingDecisionValidationError,
    sanitize_chat,
    serialize_meeting_context,
    validate_meeting_decision,
    valid_vote_targets,
)
from crewrift.crewborg.strategy.suspicion import VOTE_PROBABILITY
from crewrift.crewborg.types import Belief, ChatEvent, PlayerRecord


def _belief() -> Belief:
    belief = Belief(phase="Voting", phase_start_tick=10, last_tick=34, total_player_count=3)
    belief.voting = VotingState(
        timer_present=True,
        self_marker_color="blue",
        candidates=(
            VoteCandidate(slot=0, color="red", alive=True),
            VoteCandidate(slot=1, color="blue", alive=True),
            VoteCandidate(slot=2, color="green", alive=False),
        ),
        dots=(VoteDot(voter=0, target=2), VoteDot(voter=1, target=-2)),
        cursor_slot=0,
    )
    belief.roster["red"] = PlayerRecord(color="red", life_status="alive", last_seen_tick=20)
    belief.roster["blue"] = PlayerRecord(color="blue", life_status="alive", last_seen_tick=20)
    belief.roster["green"] = PlayerRecord(color="green", life_status="dead", death_seen_tick=30)
    belief.chat_log = [ChatEvent(tick=25, speaker_color="red", text="blue sus")]
    belief.suspicion = {"red": 0.91, "green": 0.2}
    return belief


def test_valid_vote_targets_excludes_self_and_dead_candidates() -> None:
    assert valid_vote_targets(_belief()) == {"red"}


def test_meeting_context_serializes_timer_chat_votes_and_suspicion() -> None:
    context = serialize_meeting_context(
        _belief(),
        trigger="meeting_start",
        tentative_vote="red",
        sent_chat_texts={"hello"},
        last_chat_tick=10,
    )

    assert context["meeting"]["estimated_remaining_ticks"] == 1176
    assert context["constraints"]["valid_vote_targets"] == ["red", VOTE_SKIP]
    assert context["constraints"]["chat_cooldown_ready"] is False
    assert context["state"]["tentative_vote"] == "red"
    assert context["chat"]["messages"][0]["text"] == "blue sus"
    assert context["voting"]["tally"] == {VOTE_SKIP: 1, "green": 1}
    # players is terse prose, one line per player (sorted), with life + suspicion + flags
    players = context["players"]
    assert isinstance(players, str)
    lines = players.splitlines()
    assert lines[0].startswith("blue: alive")  # sorted order: blue, green, red
    assert any(line.startswith("green: dead") for line in lines)
    assert any(line.startswith("red: alive") and "sus 0.91" in line for line in lines)
    assert context["suspicion"]["would_vote"] == "red"


def test_players_prose_is_terse_and_covers_events() -> None:
    # players is rendered as prose (not JSON) to cut ~65% of the context tokens. Verify the shape:
    # one line per player, a proximity event reads "near <color>", and self/teammate are flagged.
    from crewrift.crewborg.strategy.meeting.context import _players_prose
    from crewrift.crewborg.types import PlayerEvent

    belief = _belief()  # _belief() already sets voting.self_marker_color = "blue"
    belief.teammate_colors = {"red"}
    belief.roster["green"].events = [
        PlayerEvent(kind="proximity", start_tick=1, end_tick=5, target_color="red"),
    ]
    prose = _players_prose(belief)
    lines = {ln.split(":")[0]: ln for ln in prose.splitlines()}
    assert "[me]" in lines["blue"]
    assert "[teammate]" in lines["red"]
    assert "near red" in lines["green"]  # proximity event as a terse phrase
    assert "{" not in prose and '"' not in prose  # no JSON overhead


def test_chat_sanitizer_keeps_printable_ascii_and_truncates() -> None:
    assert sanitize_chat("  héllo\nthere  ") == "hllothere"
    assert len(sanitize_chat("x" * 500)) == 160


def test_meeting_decision_validation_rejects_dead_or_unknown_vote_target() -> None:
    with pytest.raises(MeetingDecisionValidationError):
        validate_meeting_decision(
            MeetingDecision(action="submit_vote", vote_target="green"),
            alive_vote_targets={"red"},
            fallback_vote=VOTE_SKIP,
        )


def test_fallback_vote_reason_quotes_the_actual_fitted_bar_not_the_legacy_constant(monkeypatch) -> None:
    # Fitted weights loaded (the production default), a crewmate role, and a
    # deployed bar (0.6) below the legacy hand-model constant (0.8). The top
    # suspect (0.5) clears neither, so the reason must name the REAL bar (0.6) —
    # quoting the legacy 0.8 here would mislead the LLM about what actually gates
    # a vote (context.py must ask suspicion for the CURRENT bar, not import the
    # legacy constant directly).
    monkeypatch.setattr(suspicion_module, "WEIGHTS_VOTE_PROBABILITY", 0.6)
    belief = _belief()
    belief.self_role = "crewmate"
    belief.suspicion = {"red": 0.5, "green": 0.2}

    context = serialize_meeting_context(belief, trigger="meeting_start")

    assert context["state"]["fallback_vote"] == VOTE_SKIP
    assert context["state"]["fallback_vote_reason"] == "no suspect at or above vote bar 0.6"
    assert context["suspicion"]["vote_probability_threshold"] == 0.6


def test_fallback_vote_reason_stays_on_the_legacy_bar_for_imposter_role(monkeypatch) -> None:
    # Imposter deflection deliberately keeps the legacy clear-leader logic
    # regardless of the fitted crewmate knobs, so the reported bar must stay the
    # legacy VOTE_PROBABILITY (0.8) even with a very different fitted bar set.
    monkeypatch.setattr(suspicion_module, "WEIGHTS_VOTE_PROBABILITY", 0.6)
    belief = _belief()
    belief.self_role = "imposter"
    belief.suspicion = {"red": 0.3, "green": 0.2}  # below VOTE_LEAD_MIN_P too -> a real skip

    context = serialize_meeting_context(belief, trigger="meeting_start")

    assert context["state"]["fallback_vote"] == VOTE_SKIP
    assert context["state"]["fallback_vote_reason"] == f"no suspect at or above vote bar {VOTE_PROBABILITY}"
    assert context["suspicion"]["vote_probability_threshold"] == VOTE_PROBABILITY


def test_submit_without_target_uses_tentative_then_fallback() -> None:
    decision = validate_meeting_decision(
        MeetingDecision(action="submit_vote"),
        alive_vote_targets={"red"},
        current_tentative="red",
        fallback_vote=VOTE_SKIP,
    )
    assert decision.vote_target == "red"

    decision = validate_meeting_decision(
        MeetingDecision(action="submit_vote"),
        alive_vote_targets={"red"},
        fallback_vote=VOTE_SKIP,
    )
    assert decision.vote_target == VOTE_SKIP
