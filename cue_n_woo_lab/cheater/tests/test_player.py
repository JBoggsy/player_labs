"""Drive Cheater.on_state through a full episode against a fake socket and assert
the "daveey" policy: the goblin-promoting injection on all three probes, and the
fixed short answer "The goblin" for both our proposals and the opponent's blind
questions. Every submitted answer is checked against cheater's vendored validator.
"""
from __future__ import annotations

import json

import pytest

from cheater import config
from cheater.player import Cheater
from cheater.answers import goblin_answer

# cheater's OWN vendored validator (no dependency on the mentalist player, which
# is under separate active development).
from cheater.validator import validate_answer

TARGET = config.TARGET_WORD
ANSWER = config.ANSWER


class FakeWS:
    """Captures the JSON actions the player sends."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, raw: str) -> None:
        self.sent.append(json.loads(raw))


def state(phase: str, *, judge=None, proposals=None, answers=None, opponent_questions=None):
    return {
        "type": "state",
        "phase": phase,
        "me": {
            "judge": judge or [],
            "proposals": proposals or [],
            "answers": answers or [],
        },
        "opponent_questions": opponent_questions or [],
        "remaining_seconds": 300,
    }


def landed_ask(prev_judge, q):
    """Judge transcript after an `ask` lands (server appends a generated answer)."""
    return prev_judge + [{"question": q, "answer": "...style answer..."}]


@pytest.mark.asyncio
async def test_private_questions_ask_three_distinct_probes():
    player = Cheater()
    ws = FakeWS()
    judge: list[dict] = []

    assert len(config.PROBES) == 3
    for i in range(3):
        # fresh broadcast for this probe; settle clears the prior in-flight ask
        await player.on_state(ws, state("private_questions", judge=judge))
        # v4: the i-th probe is config.PROBES[i] (three DIFFERENT probes)
        assert ws.sent[-1] == {"type": "ask", "question": config.PROBES[i]}
        judge = landed_ask(judge, config.PROBES[i])

    assert len(ws.sent) == 3
    # the probes are genuinely distinct, and all mention the target word
    assert len(set(config.PROBES)) == 3
    assert all(TARGET in p for p in config.PROBES)
    # a fourth broadcast with all three asks landed must NOT ask again
    await player.on_state(ws, state("private_questions", judge=judge))
    assert len(ws.sent) == 3


def test_answer_is_the_goblin():
    a = goblin_answer()
    assert a == ANSWER == f"The {TARGET}"
    validate_answer(a)


@pytest.mark.asyncio
async def test_proposals_commit_the_goblin():
    player = Cheater()
    ws = FakeWS()
    await player.on_state(ws, state("proposals"))

    action = ws.sent[-1]
    assert action["type"] == "propose"
    proposals = action["proposals"]
    assert len(proposals) == 3
    assert [p["question"] for p in proposals] == list(config.PROPOSAL_QUESTIONS)
    for p in proposals:
        assert p["answer"] == ANSWER               # fixed short "The goblin"
        validate_answer(p["answer"])


@pytest.mark.asyncio
async def test_blind_answers_are_the_goblin_and_legal():
    player = Cheater()
    ws = FakeWS()
    opp = [
        {"question": "What would you do with a completely free afternoon?"},
        {"question": "Describe your ideal vacation destination."},
        {"question": "?!?"},
    ]
    await player.on_state(ws, state("answers", opponent_questions=opp))

    action = ws.sent[-1]
    assert action["type"] == "answer"
    assert action["answers"] == [ANSWER, ANSWER, ANSWER]
    for a in action["answers"]:
        validate_answer(a)


@pytest.mark.asyncio
async def test_idempotent_within_phase():
    """Repeated broadcasts for an already-acted phase don't re-send."""
    player = Cheater()
    ws = FakeWS()

    # propose once; pending guard blocks a second send until it lands
    await player.on_state(ws, state("proposals"))
    await player.on_state(ws, state("proposals"))
    assert len(ws.sent) == 1

    # once the proposal is reflected in state, still no duplicate
    proposed = [{"question": q, "answer": ANSWER} for q in config.PROPOSAL_QUESTIONS]
    await player.on_state(ws, state("proposals", proposals=proposed))
    assert len(ws.sent) == 1


@pytest.mark.asyncio
async def test_reveal_ends_episode():
    player = Cheater()
    ws = FakeWS()
    done = await player.on_state(ws, {"type": "state", "phase": "reveal", "results": {}})
    assert done is True
    assert ws.sent == []
