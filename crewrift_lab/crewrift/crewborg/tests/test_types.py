"""Tests for the new chat-evidence data shapes on types.py."""

from __future__ import annotations

import pytest

from crewrift.crewborg.types import Belief, ChatClaim, PlayerRecord, VoteCast


def test_chat_claim_is_frozen_and_defaults_to_spacy_source() -> None:
    claim = ChatClaim(tick=10, speaker_color="red", target_color="blue", claim_type="accusation")
    assert claim.source == "spacy"
    assert claim.verification is None
    with pytest.raises(Exception):
        claim.tick = 20  # frozen


def test_vote_cast_is_frozen() -> None:
    cast = VoteCast(meeting_tick=0, ticks_after_meeting_start=50, target_color="red", rank=1)
    with pytest.raises(Exception):
        cast.rank = 2  # frozen


def test_player_record_defaults_new_fields_empty() -> None:
    record = PlayerRecord(color="red")
    assert record.claims == []
    assert record.vote_history == []
    assert record.spoke_first_count == 0


def test_belief_defaults_vote_order_empty() -> None:
    assert Belief().social_vote_order == []
