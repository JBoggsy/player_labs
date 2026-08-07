from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import campaign_order_controller as controller  # noqa: E402


PLAYER = controller.DEFAULT_PLAYER
OPPONENT = "ply_opponent"


class Dump:
    def __init__(self, value):
        self.value = value

    def model_dump(self, *, mode):
        assert mode == "json"
        return self.value


class FakeClient:
    def __init__(self, board):
        self.board = board
        self.prompt = "Standing campaign guidance."
        self.conversation = None
        self.full_prompt_failures = 0
        self.full_prompt_reads = 0

    def get_campaign_board(self, league):
        return Dump(self.board)

    def get_campaign_prompt(self, league, *, player_id):
        return SimpleNamespace(prompt=self.prompt)

    def set_campaign_prompt(self, league, *, player_id, prompt):
        self.prompt = prompt

    def get_campaign_full_prompt(self, league, *, player_id):
        self.full_prompt_reads += 1
        if self.full_prompt_reads <= self.full_prompt_failures:
            return SimpleNamespace(context="Standing campaign guidance.")
        return SimpleNamespace(context=self.prompt)

    def get_campaign_conversation(self, league, *, player_id, round_no):
        if self.conversation is None:
            raise RuntimeError("not ready")
        return self.conversation


def board(*, pending=None, round_no=5):
    return {
        "round": round_no,
        "config": {"width": 2, "height": 1},
        "frames": [{"round": round_no, "owners": [OPPONENT, PLAYER], "battles": []}],
        "map_refs": ["1v1", "1v1"],
        "modes": ["2v2", "2v2"],
        "players": [{"id": OPPONENT, "name": "Max Yankov"}, {"id": PLAYER, "name": "James Botts"}],
        "pending_round": pending,
    }


def args():
    return argparse.Namespace(
        league=controller.DEFAULT_LEAGUE,
        player=PLAYER,
        server="https://softmax.com/api",
        arm_now=True,
    )


def test_cycle_arms_audits_and_restores_exact_unstaked_order():
    client = FakeClient(board())
    checkpoints = []
    events = []
    state = controller.run_cycle(args(), client, {}, events.append, lambda value: checkpoints.append(value.copy()))

    assert state["phase"] == "armed"
    assert state["directive_round"] == 6
    assert state["target"]["cell"] == "0,0"
    assert checkpoints[0]["phase"] == "arming"
    assert state["nonce"] in client.prompt

    pending = {
        "round": 6,
        "orders": {
            PLAYER: {"airdrops": ["0,0"], "invasions": [], "auto_airdrops": 0, "dropped": []}
        },
        "battles": [
            {
                "attacker": PLAYER,
                "defender": OPPONENT,
                "target": "0,0",
                "source": None,
                "staked": False,
                "map_ref": "1v1",
                "mode": "2v2",
            }
        ],
    }
    client.board = board(pending=pending)
    client.conversation = SimpleNamespace(
        response=[{"type": "tool_use", "name": "invade", "input": {"target_cell": "0,0"}}],
        reasoning="exact directive",
        error=None,
    )
    state = controller.run_cycle(args(), client, state, events.append, lambda value: checkpoints.append(value.copy()))

    assert state["audit_compliant"] is True
    assert state["pending_order_compliant"] is True
    assert state["directive_restored"] is True
    assert state["phase"] == "restored"
    assert client.prompt == "Standing campaign guidance."


def test_cycle_recovers_checkpointed_arm_after_interruption():
    client = FakeClient(board())
    target = controller.choose_target(client.board, PLAYER)
    nonce = "r6-testnonce"
    state = {
        "phase": "arming",
        "directive_round": 6,
        "board_round_when_written": 5,
        "target": target,
        "nonce": nonce,
        "base_prompt_sha256": hashlib.sha256(client.prompt.encode()).hexdigest(),
        "written_at": controller.now(),
    }
    checkpoints = []
    events = []

    state = controller.run_cycle(args(), client, state, events.append, lambda value: checkpoints.append(value.copy()))

    assert state["phase"] == "armed"
    assert nonce in client.prompt
    assert [event["event"] for event in events] == ["directive_arm_recovered"]


def test_cycle_retries_eventually_consistent_full_prompt(monkeypatch):
    client = FakeClient(board())
    client.full_prompt_failures = 3
    sleeps = []
    monkeypatch.setattr(controller.time, "sleep", sleeps.append)

    state = controller.run_cycle(args(), client, {}, lambda event: None, lambda value: None)

    assert state["phase"] == "armed"
    assert client.full_prompt_reads == 4
    assert sleeps == [2, 2, 2]


def test_failed_arm_restores_prompt_and_previous_state(monkeypatch):
    client = FakeClient(board())
    client.full_prompt_failures = 99
    checkpoints = []
    monkeypatch.setattr(controller.time, "sleep", lambda seconds: None)

    with pytest.raises(RuntimeError, match="readback"):
        controller.run_cycle(args(), client, {}, lambda event: None, lambda value: checkpoints.append(value.copy()))

    assert client.prompt == "Standing campaign guidance."
    assert checkpoints[-1] == {}


def test_restore_retries_eventually_consistent_prompt(monkeypatch):
    client = FakeClient(board())
    target = controller.choose_target(client.board, PLAYER)
    nonce = "r6-restoretest"
    base = client.prompt
    client.prompt = base + "\n\n" + controller.directive(6, target, nonce)
    state = {
        "directive_round": 6,
        "target": target,
        "nonce": nonce,
        "base_prompt_sha256": hashlib.sha256(base.encode()).hexdigest(),
    }
    live_prompt = client.prompt
    reads = 0
    sleeps = []

    def lagged_get_prompt(league, *, player_id):
        nonlocal reads
        reads += 1
        return SimpleNamespace(prompt=live_prompt if reads <= 3 else client.prompt)

    client.get_campaign_prompt = lagged_get_prompt
    monkeypatch.setattr(controller.time, "sleep", sleeps.append)

    controller.restore_directive(client, controller.DEFAULT_LEAGUE, PLAYER, state, lambda event: None)

    assert state["directive_restored"] is True
    assert client.prompt == base
    assert sleeps == [2, 2]
