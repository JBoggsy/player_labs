"""Bridge tests against a scripted nim_control server, using the REAL wow_sdk client
from the pinned-image SDK snapshot (conftest adds it to sys.path; importorskip guards).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("wow_sdk.nim_control")

from fake_control_server import FakeControlServer  # noqa: E402
from wowborg.bridge import ShimBridge  # noqa: E402
from wowborg.trace import Tracer  # noqa: E402


@pytest.fixture()
def server():
    fake = FakeControlServer().start()
    yield fake
    fake.stop()


def make_bridge(server: FakeControlServer, tmp_path: Path, tracer: Tracer | None = None) -> ShimBridge:
    return ShimBridge(tmp_path, tracer, slot=0, host="127.0.0.1", port=server.port)


def test_connect_and_arm_external_control(server, tmp_path) -> None:
    bridge = make_bridge(server, tmp_path)
    assert bridge.connect(timeout_s=5.0)
    assert bridge.arm_external_control()
    assert server.goal is not None
    assert server.goal["selection_mode"] == "external"
    assert server.goal["goal_kind"] == "leveling"
    bridge.close()


def test_wait_for_frame_and_observe(server, tmp_path) -> None:
    bridge = make_bridge(server, tmp_path)
    assert bridge.connect(timeout_s=5.0)
    assert bridge.arm_external_control()
    frame = bridge.wait_for_frame(timeout_s=5.0)
    assert frame is not None and frame.action_ready
    obs = bridge.observe()
    assert obs is not None
    assert obs.map_id == 1
    assert round(obs.position.x, 1) == -618.5
    assert obs.health == 60 and not obs.is_dead
    bridge.close()


def test_move_selection_settles_and_moves_position(server, tmp_path) -> None:
    bridge = make_bridge(server, tmp_path)
    assert bridge.connect(timeout_s=5.0)
    assert bridge.arm_external_control()
    frame = bridge.wait_for_frame(timeout_s=5.0)
    request_id = bridge.select_move_to(frame, -600.0, -4260.0, 39.0, 1)
    assert request_id == f"frame-{frame.frame_id}"
    outcome = bridge.wait_for_settlement(frame.frame_id, timeout_s=5.0)
    assert outcome is not None and outcome.success
    assert outcome.kind == "move"
    # the fake server relocates to the selected destination
    obs = bridge.observe()
    assert (round(obs.position.x), round(obs.position.y)) == (-600, -4260)
    bridge.close()


def test_selection_refused_by_mask_returns_none(server, tmp_path) -> None:
    from wow_sdk.nim_control import FactorizedAction

    bridge = make_bridge(server, tmp_path)
    assert bridge.connect(timeout_s=5.0)
    assert bridge.arm_external_control()
    frame = bridge.wait_for_frame(timeout_s=5.0)
    # target index beyond the (empty) entity bindings — allows_action must refuse
    bad = FactorizedAction(kind="attack", target=3)
    assert bridge.select_action(frame, bad) is None
    bridge.close()


def test_settlement_timeout_returns_none(server, tmp_path) -> None:
    bridge = make_bridge(server, tmp_path)
    assert bridge.connect(timeout_s=5.0)
    assert bridge.arm_external_control()
    # no selection made → wait for a frame_id that will never settle
    assert bridge.wait_for_settlement(999, timeout_s=1.0) is None
    bridge.close()


def test_say_uses_admitted_vocabulary_only(server, tmp_path) -> None:
    bridge = make_bridge(server, tmp_path)
    assert bridge.connect(timeout_s=5.0)
    assert bridge.arm_external_control()
    bridge.wait_for_frame(timeout_s=5.0)
    # admitted text (the fake server binds this exact string at index 1)
    assert bridge.say("wowborg random_walk starting") is not None
    bridge.wait_for_settlement(server.frame_id, timeout_s=5.0)
    # rate limit suppresses immediately-following says
    assert bridge.say("anything") is None
    bridge.close()


def test_bridge_traces_frames_intents_outcomes(server, tmp_path) -> None:
    trace_file = tmp_path / "trace.jsonl"
    bridge = make_bridge(server, tmp_path, Tracer(trace_file, echo_stdout=False))
    assert bridge.connect(timeout_s=5.0)
    assert bridge.arm_external_control()
    frame = bridge.wait_for_frame(timeout_s=5.0)
    bridge.select_move_to(frame, -600.0, -4260.0, 39.0, 1)
    bridge.wait_for_settlement(frame.frame_id, timeout_s=5.0)
    bridge.close()

    kinds = [json.loads(line)["kind"] for line in trace_file.read_text().splitlines()]
    assert "control_connected" in kinds
    assert "goal_armed" in kinds
    assert "observation" in kinds
    assert "intent" in kinds
    assert "outcome" in kinds
