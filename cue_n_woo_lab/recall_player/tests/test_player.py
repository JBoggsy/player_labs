"""Drive RecallPlayer.on_state through a full episode against a fake socket and assert the
planted PHRASE-recall policy: ask 3 phrase-forcing probes, lift the judge's evocative phrase
replies, commit those recalled phrases as our proposal + blind answers. Every answer is checked
against the vendored validator (which mirrors the game's CHARACTER-based token limit)."""
from __future__ import annotations

import json

import pytest

from recall_player import config
from recall_player.answers import extract_phrase, recalled_answers
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


# --- phrase extraction (the core no-LLM primitive) --------------------------

def test_extract_phrase():
    assert extract_phrase("The wax remembers everything") == "The wax remembers everything"
    # strips surrounding quotes + trailing punctuation
    assert extract_phrase('"The decay note persists."') == "The decay note persists"
    # strips a leading preamble and keeps the first line only
    assert extract_phrase("Sure: The barometer never forgets\n(more text)") == "The barometer never forgets"
    assert extract_phrase("") is None
    # a phrase too short to be a legal answer -> None (caller falls back)
    assert extract_phrase("Hi") is None


def test_recalled_answers_cycle_varied_and_are_legal():
    # cycle DISTINCT phrases (diversity hedge), best-first; all legal.
    judge = [{"question": "q1", "answer": "The wax remembers everything"},
             {"question": "q2", "answer": "The shaft swallows daylight"}]
    out = recalled_answers(judge, 3)
    assert len(out) == 3
    assert len(set(out[:2])) == 2          # two distinct phrases used, not one reused
    assert out[2] == out[0]                # cycles back on the 3rd
    for a in out:
        validate_answer(a)
        assert simple_token_count(a) <= 12


def test_best_phrase_prefers_gabby_register():
    from recall_player.answers import best_phrase
    # crisp surreal declarative beats a wordy literal phrase
    chosen = best_phrase(["a map with too many footnotes here", "The gavel reads old bark"])
    assert chosen == "The gavel reads old bark"


def test_recalled_falls_back_when_no_phrase():
    out = recalled_answers([{"question": "q", "answer": ""}], 2)
    fallback = recalled_answers([], 1)[0]
    assert out == [fallback, fallback]
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
        assert "phrase" in config.PROBES[i].lower()  # each probe forces an evocative phrase
        judge = landed(judge, config.PROBES[i], f"The thing number {i} endures")
    # all 3 landed -> no fourth ask
    await player.on_state(ws, state("private_questions", judge=judge))
    assert len(ws.sent) == 3


_PHRASES = ["The wax remembers everything", "The shaft swallows daylight", "The decay note persists"]


@pytest.mark.asyncio
async def test_proposals_commit_recalled_phrases():
    player = RecallPlayer()
    ws = FakeWS()
    judge = [{"question": q, "answer": p} for q, p in zip(config.PROBES, _PHRASES)]
    await player.on_state(ws, state("proposals", judge=judge))
    action = ws.sent[-1]
    assert action["type"] == "propose"
    assert [p["question"] for p in action["proposals"]] == list(config.PROPOSAL_QUESTIONS)
    for p in action["proposals"]:
        assert p["answer"] in set(_PHRASES)  # recalled, verbatim
        validate_answer(p["answer"])


@pytest.mark.asyncio
async def test_blind_answers_recalled_and_legal():
    player = RecallPlayer()
    ws = FakeWS()
    judge = [{"question": q, "answer": p} for q, p in zip(config.PROBES, _PHRASES)]
    opp = [{"question": "x?"}, {"question": "y?"}, {"question": "z?"}]
    await player.on_state(ws, state("answers", judge=judge, opponent_questions=opp))
    action = ws.sent[-1]
    assert action["type"] == "answer" and len(action["answers"]) == 3
    for a in action["answers"]:
        validate_answer(a)
        assert a in set(_PHRASES)


@pytest.mark.asyncio
async def test_idempotent_within_phase():
    player = RecallPlayer()
    ws = FakeWS()
    judge = [{"question": q, "answer": _PHRASES[0]} for q in config.PROBES]
    await player.on_state(ws, state("proposals", judge=judge))
    await player.on_state(ws, state("proposals", judge=judge))
    assert len(ws.sent) == 1


@pytest.mark.asyncio
async def test_propose_uses_cached_phrases_when_propose_state_lags():
    """Regression: the proposals-phase state can arrive with me.judge EMPTY (our view lags),
    but if we saw the phrase answers during the interview we must still commit the recalled
    phrases, not the fallback."""
    player = RecallPlayer()
    ws = FakeWS()
    judge = []
    for q, p in zip(config.PROBES, _PHRASES):
        judge = landed(judge, q, p)
        await player.on_state(ws, state("private_questions", judge=judge))
    await player.on_state(ws, state("proposals", judge=[]))  # lagging view: empty me.judge
    action = ws.sent[-1]
    assert action["type"] == "propose"
    fallback = recalled_answers([], 1)[0]
    for p in action["proposals"]:
        assert p["answer"] in set(_PHRASES)
        assert p["answer"] != fallback


@pytest.mark.asyncio
async def test_no_wedge_when_proposals_arrives_with_ask_still_pending():
    """League DQ regression: after the 3rd probe we hold pending='ask' (_asks_target=3), and the
    NEXT state is already 'proposals' with me.judge LAGGING (<3). The phase-change clear must
    drop the stale 'ask' guard so we propose — otherwise we wait forever, the global phase
    stalls, and the server times us out inactive (-100). This is exactly what killed v1/v2 in
    the live league while isolated fast-judge races never reproduced it."""
    player = RecallPlayer()
    ws = FakeWS()
    # Probes land with NO transcript echo (judge view never catches up), so each ask stays pending
    # until the phase advances. Drive 3 private_questions states, each showing 0 prior answers.
    for _ in range(3):
        await player.on_state(ws, state("private_questions", judge=[]))
    # After 3 asks the player is still pending='ask' and has only sent... let's confirm it sent 1
    # ask then wedged on its own guard within the interview — that's fine; the real unwedge is the
    # phase change below. Seed the phrase cache as the interview would have (harvested elsewhere).
    player._phrases = list(_PHRASES)
    # proposals phase arrives with me.judge STILL empty (the lag):
    await player.on_state(ws, state("proposals", judge=[]))
    propose = [m for m in ws.sent if m.get("type") == "propose"]
    assert len(propose) == 1, f"expected exactly one propose, got sent={ws.sent}"
    for p in propose[0]["proposals"]:
        assert p["answer"] in set(_PHRASES)


@pytest.mark.asyncio
async def test_reveal_ends_episode():
    player = RecallPlayer()
    ws = FakeWS()
    done = await player.on_state(ws, {"type": "state", "phase": "reveal", "results": {}})
    assert done is True and ws.sent == []
