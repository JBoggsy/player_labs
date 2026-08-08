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


class Model(Dump):
    def __init__(self, value):
        super().__init__(value)
        for key, item in value.items():
            setattr(self, key, item)


class FakeClient:
    def __init__(self, board):
        self.board = board
        self.prompt = "Standing campaign guidance."
        self.conversation = None
        self.full_prompt_failures = 0
        self.full_prompt_reads = 0
        self.champion = Model({"id": "pv_current", "version": 1, "label": "stencil:v1"})

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

    def list_memberships(self, **kwargs):
        return [SimpleNamespace(policy_version=self.champion)]

    def list_episode_requests(self, **kwargs):
        return SimpleNamespace(entries=[], next_cursor=None)

    def list_experience_requests(self, **kwargs):
        return SimpleNamespace(entries=[])

    def get_campaign_history(self, league, *, player_id):
        return Dump({"battles": [], "names": {}})


def board(*, pending=None, round_no=5):
    return {
        "round": round_no,
        "config": {"width": 2, "height": 1},
        "frames": [{"round": round_no, "owners": [OPPONENT, PLAYER], "battles": []}],
        "map_refs": ["1v1", "1v1"],
        "modes": ["2v2", "2v2"],
        "players": [
            {"id": OPPONENT, "name": "Max Yankov"},
            {"id": PLAYER, "name": "James Botts"},
        ],
        "pending_round": pending,
    }


def args():
    return argparse.Namespace(
        league=controller.DEFAULT_LEAGUE,
        player=PLAYER,
        server="https://softmax.com/api",
        arm_now=True,
        stats_refresh_seconds=60,
    )


def test_cycle_arms_audits_and_restores_exact_unstaked_order():
    client = FakeClient(board())
    checkpoints = []
    events = []
    state = controller.run_cycle(
        args(),
        client,
        {},
        events.append,
        lambda value: checkpoints.append(value.copy()),
    )

    assert state["phase"] == "armed"
    assert state["directive_round"] == 6
    assert state["target"]["cell"] == "0,0"
    assert checkpoints[0]["phase"] == "arming"
    assert state["nonce"] in client.prompt

    pending = {
        "round": 6,
        "orders": {
            PLAYER: {
                "airdrops": ["0,0"],
                "invasions": [],
                "auto_airdrops": 0,
                "dropped": [],
            }
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
        response=[
            {"type": "tool_use", "name": "invade", "input": {"target_cell": "0,0"}}
        ],
        reasoning="exact directive",
        error=None,
    )
    state = controller.run_cycle(
        args(),
        client,
        state,
        events.append,
        lambda value: checkpoints.append(value.copy()),
    )

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

    state = controller.run_cycle(
        args(),
        client,
        state,
        events.append,
        lambda value: checkpoints.append(value.copy()),
    )

    assert state["phase"] == "armed"
    assert nonce in client.prompt
    assert [event["event"] for event in events] == [
        "directive_arm_recovered",
        "statistics_refreshed",
    ]


def test_cycle_retries_eventually_consistent_full_prompt(monkeypatch):
    client = FakeClient(board())
    client.full_prompt_failures = 3
    sleeps = []
    monkeypatch.setattr(controller.time, "sleep", sleeps.append)

    state = controller.run_cycle(
        args(), client, {}, lambda event: None, lambda value: None
    )

    assert state["phase"] == "armed"
    assert client.full_prompt_reads == 4
    assert sleeps == [2, 2, 2]


def test_failed_arm_restores_prompt_and_previous_state(monkeypatch):
    client = FakeClient(board())
    client.full_prompt_failures = 99
    checkpoints = []
    monkeypatch.setattr(controller.time, "sleep", lambda seconds: None)

    with pytest.raises(RuntimeError, match="readback"):
        controller.run_cycle(
            args(),
            client,
            {},
            lambda event: None,
            lambda value: checkpoints.append(value.copy()),
        )

    assert client.prompt == "Standing campaign guidance."
    assert set(checkpoints[-1]) == {"analysis"}


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

    controller.restore_directive(
        client, controller.DEFAULT_LEAGUE, PLAYER, state, lambda event: None
    )

    assert state["directive_restored"] is True
    assert client.prompt == base
    assert sleeps == [2, 2]


def test_posterior_double_victory_probability_is_joint_predictive_probability():
    estimate = controller.posterior(8, 0)

    assert estimate["win_probability"] == pytest.approx(0.9)
    assert estimate["double_victory_probability"] == pytest.approx(9 * 10 / (10 * 11))
    assert estimate["double_victory_probability"] > controller.DOUBLE_VICTORY_THRESHOLD


def test_invasion_requires_exact_opponent_cell_evidence_and_owned_adjacent_source():
    other = "ply_other"
    live_board = {
        "round": 5,
        "config": {"width": 3, "height": 1},
        "frames": [{"round": 5, "owners": [PLAYER, OPPONENT, other], "battles": []}],
        "map_refs": ["1v1", "1v1", "1v1"],
        "modes": ["2v2", "2v2", "2v2"],
        "players": [
            {"id": OPPONENT, "name": "Max Yankov"},
            {"id": other, "name": "Bella"},
            {"id": PLAYER, "name": "James Botts"},
        ],
        "pending_round": None,
    }
    bucket = {
        "opponent_id": OPPONENT,
        "opponent_name": "Max Yankov",
        "map_ref": "1v1",
        "mode": "2v2",
        "campaign_episodes": 2,
        "xp_episodes": 6,
        **controller.posterior(8, 0),
    }
    analysis = {"buckets": {controller.bucket_key(OPPONENT, "1v1", "2v2"): bucket}}
    airdrop = next(
        candidate
        for candidate in controller.candidates(live_board, PLAYER, analysis)
        if candidate["cell"] == "2,0"
    )

    invasion = controller.choose_invasion(live_board, PLAYER, analysis, airdrop)

    assert invasion["cell"] == "1,0"
    assert invasion["from_cell"] == "0,0"
    assert invasion["estimate"]["double_victory_probability"] > 0.75


def test_cycle_audits_airdrop_and_statistically_gated_invasion():
    other = "ply_other"
    live_board = {
        "round": 5,
        "config": {"width": 3, "height": 1},
        "frames": [{"round": 5, "owners": [PLAYER, OPPONENT, other], "battles": []}],
        "map_refs": ["1v1", "1v1", "1v1"],
        "modes": ["2v2", "2v2", "2v2"],
        "players": [
            {"id": OPPONENT, "name": "Max Yankov"},
            {"id": other, "name": "Bella"},
            {"id": PLAYER, "name": "James Botts"},
        ],
        "pending_round": None,
    }
    client = FakeClient(live_board)
    analysis = {"buckets": {}}
    choices = controller.candidates(live_board, PLAYER, analysis)
    target = next(candidate for candidate in choices if candidate["cell"] == "2,0")
    invasion = next(candidate for candidate in choices if candidate["cell"] == "1,0")
    invasion["from_cell"] = "0,0"
    nonce = "r6-two-orders"
    state = {
        "phase": "armed",
        "directive_round": 6,
        "board_round_when_written": 5,
        "target": target,
        "invasion": invasion,
        "nonce": nonce,
        "base_prompt_sha256": hashlib.sha256(client.prompt.encode()).hexdigest(),
        "written_at": controller.now(),
    }
    client.prompt += "\n\n" + controller.directive(6, target, nonce, invasion)
    client.conversation = SimpleNamespace(
        response=[
            {
                "type": "tool_use",
                "name": "invade",
                "input": {"reasoning": "airdrop", "target_cell": "2,0"},
            },
            {
                "type": "tool_use",
                "name": "invade",
                "input": {
                    "reasoning": "high-confidence invasion",
                    "target_cell": "1,0",
                    "from_cell": "0,0",
                },
            },
        ],
        reasoning="two exact orders",
        error=None,
    )
    client.board["pending_round"] = {
        "round": 6,
        "orders": {
            PLAYER: {
                "airdrops": ["2,0"],
                "invasions": [{"from_cell": "0,0", "target_cell": "1,0"}],
                "auto_airdrops": 0,
                "dropped": [],
            }
        },
        "battles": [
            {
                "attacker": PLAYER,
                "defender": other,
                "target": "2,0",
                "source": None,
                "staked": False,
                "map_ref": "1v1",
                "mode": "2v2",
            },
            {
                "attacker": PLAYER,
                "defender": OPPONENT,
                "target": "1,0",
                "source": "0,0",
                "staked": True,
                "map_ref": "1v1",
                "mode": "2v2",
            },
        ],
    }
    events = []

    state = controller.run_cycle(
        args(), client, state, events.append, lambda value: None
    )

    assert state["audit_compliant"] is True
    assert state["pending_order_compliant"] is True
    assert state["directive_restored"] is True
    assert client.prompt == "Standing campaign guidance."
