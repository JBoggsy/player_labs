"""Drive RecallPlayer.on_state through a full episode against a fake socket and assert the
planted digit-recall policy: ask 3 digit-forcing probes, extract the judge's digit replies,
commit those recalled digits as our proposal + blind answers. Every answer is checked against
the vendored validator (which mirrors the game's CHARACTER-based token limit)."""
from __future__ import annotations

import json

import pytest

from recall_player import config
from recall_player.answers import extract_digits, recalled_answers
from recall_player.player import RecallPlayer
from recall_player.validator import validate_answer, simple_token_count


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []
    async def send(self, raw: str) -> None:
        self.sent.append(json.loads(raw))


def state(phase, *, judge=None, proposals=None, answers=None, opponent_questions=None):
    return {"type": "state", "phase": phase,
            "me": {"judge": judge or [], "proposals": proposals or [], "answers": answers or []},
            "opponent_questions": opponent_questions or [], "remaining_seconds": 300}


def landed(prev_judge, q, judge_reply):
    return prev_judge + [{"question": q, "answer": judge_reply}]


# --- digit extraction (the core no-LLM primitive) ---------------------------

def test_extract_digits():
    assert extract_digits("42837651029") == "42837651029"
    assert extract_digits("Sure: 4283 7651 029!") == "42837651029"   # strips spaces
    assert extract_digits("I'd say a worn compass") is None
    assert extract_digits("") is None


def test_recalled_answers_are_legal_and_from_transcript():
    judge = [{"question": "q1", "answer": "42837651029"},
             {"question": "q2", "answer": "6174927361"}]
    out = recalled_answers(judge, 3)
    assert len(out) == 3
    # each is one of the recalled digit strings, cycled
    assert out[0] == "42837651029" and out[1] == "6174927361" and out[2] == "42837651029"
    for a in out:
        validate_answer(a)
        assert simple_token_count(a) <= 12


def test_recalled_falls_back_when_no_digits():
    out = recalled_answers([{"question": "q", "answer": "no numbers here"}], 2)
    assert out == [config.FALLBACK_DIGITS, config.FALLBACK_DIGITS]
    for a in out:
        validate_answer(a)


# --- phase flow -------------------------------------------------------------

@pytest.mark.asyncio
async def test_asks_exactly_the_required_probes():
    player = RecallPlayer()
    ws = FakeWS()
    judge: list[dict] = []
    assert len(config.PROBES) == config.PRIVATE_QUESTIONS == 3
    for i in range(3):
        await player.on_state(ws, state("private_questions", judge=judge))
        assert ws.sent[-1] == {"type": "ask", "question": config.PROBES[i]}
        assert "digits" in config.PROBES[i]   # each probe forces a digit reply
        judge = landed(judge, config.PROBES[i], f"{i}234567890")
    # all 3 landed -> no fourth ask
    await player.on_state(ws, state("private_questions", judge=judge))
    assert len(ws.sent) == 3


@pytest.mark.asyncio
async def test_proposals_commit_recalled_digits():
    player = RecallPlayer()
    ws = FakeWS()
    judge = [{"question": q, "answer": d} for q, d in
             zip(config.PROBES, ["42837651029", "6174927361", "8675309420"])]
    await player.on_state(ws, state("proposals", judge=judge))
    action = ws.sent[-1]
    assert action["type"] == "propose"
    assert [p["question"] for p in action["proposals"]] == list(config.PROPOSAL_QUESTIONS)
    for p in action["proposals"]:
        assert p["answer"] in {"42837651029", "6174927361", "8675309420"}  # recalled, verbatim
        validate_answer(p["answer"])


@pytest.mark.asyncio
async def test_blind_answers_recalled_and_legal():
    player = RecallPlayer()
    ws = FakeWS()
    judge = [{"question": q, "answer": d} for q, d in zip(config.PROBES, ["42837651029", "6174927361", "8675309420"])]
    opp = [{"question": "x?"}, {"question": "y?"}, {"question": "z?"}]
    await player.on_state(ws, state("answers", judge=judge, opponent_questions=opp))
    action = ws.sent[-1]
    assert action["type"] == "answer" and len(action["answers"]) == 3
    for a in action["answers"]:
        validate_answer(a)
        assert a.isdigit()


@pytest.mark.asyncio
async def test_idempotent_within_phase():
    player = RecallPlayer()
    ws = FakeWS()
    judge = [{"question": q, "answer": "42837651029"} for q in config.PROBES]
    await player.on_state(ws, state("proposals", judge=judge))
    await player.on_state(ws, state("proposals", judge=judge))
    assert len(ws.sent) == 1


@pytest.mark.asyncio
async def test_reveal_ends_episode():
    player = RecallPlayer()
    ws = FakeWS()
    done = await player.on_state(ws, {"type": "state", "phase": "reveal", "results": {}})
    assert done is True and ws.sent == []
