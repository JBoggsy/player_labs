"""Unit tests for the ShimBridge adapter against the real wow_sdk contract models.

Requires ``wow_sdk`` (installed in the base image; locally the conftest adds the
game-repo checkout's ``src/`` to sys.path when present). Skipped when unavailable —
the policy/shim tests still run everywhere.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

wow_sdk_protocol = pytest.importorskip("wow_sdk.protocol")

from wowborg.bridge import ShimBridge  # noqa: E402


def snapshot_payload(**overrides) -> dict:
    character = {
        "guid": "0x1234",
        "name": "Nightsun",
        "level": 1,
        "xp": 0,
        "next_level_xp": 400,
        "rested_xp": 0,
        "map_id": 1,
        "zone": "Durotar",
        "x": 100.0,
        "y": 200.0,
        "z": 30.0,
        "orientation": 1.5,
        "health": 60,
        "max_health": 60,
        "in_combat": False,
        "death_state_known": True,
        "is_dead": False,
        "is_ghost": False,
    }
    character.update(overrides)
    return {"slot": 0, "tick": 42, "character": character}


def write_state(runtime_dir: Path, payload: dict) -> None:
    (runtime_dir / "state.json").write_text(json.dumps(payload), encoding="utf-8")


def test_observe_none_before_first_state(tmp_path: Path) -> None:
    assert ShimBridge(tmp_path).observe() is None


def test_observe_adapts_snapshot(tmp_path: Path) -> None:
    write_state(tmp_path, snapshot_payload())
    obs = ShimBridge(tmp_path).observe()
    assert obs is not None
    assert obs.tick == 42
    assert obs.map_id == 1
    assert obs.zone == "Durotar"
    assert (obs.position.x, obs.position.y, obs.position.z) == (100.0, 200.0, 30.0)
    assert obs.position.orientation == 1.5
    assert obs.health == 60 and obs.max_health == 60
    assert not obs.is_dead and not obs.is_ghost


def test_move_to_writes_contract_envelope(tmp_path: Path) -> None:
    bridge = ShimBridge(tmp_path)
    request_id = bridge.move_to(110.0, 210.0, 30.0, 1, arrival_radius=3.0)
    payload = json.loads((tmp_path / "action.json").read_text(encoding="utf-8"))
    assert payload["sequence"] == 1
    assert payload["request_id"] == request_id
    assert payload["kind"] == "move"
    assert payload["destination"] == {"map_id": 1, "x": 110.0, "y": 210.0, "z": 30.0}
    assert payload["arrival_radius"] == 3.0
    assert payload["target_z_known"] is False


def test_move_to_trust_z_omits_flag_and_sequences_increment(tmp_path: Path) -> None:
    bridge = ShimBridge(tmp_path)
    bridge.move_to(1.0, 2.0, 3.0, 1)
    bridge.move_to(4.0, 5.0, 6.0, 1, trust_z=True)
    payload = json.loads((tmp_path / "action.json").read_text(encoding="utf-8"))
    assert payload["sequence"] == 2
    assert "target_z_known" not in payload


def test_wait_for_result_adapts_settlement(tmp_path: Path) -> None:
    bridge = ShimBridge(tmp_path)
    request_id = bridge.move_to(110.0, 210.0, 30.0, 1)
    result_line = {
        "slot": 0,
        "sequence": 1,
        "tick": 50,
        "request_id": request_id,
        "kind": "move",
        "success": True,
        "message": "arrived",
        "movement_settlement": {
            "kind": "reached_target",
            "displacement_yards": 12.5,
        },
        "client_state": {
            "player_position": {"map_id": 1, "x": 110.2, "y": 209.8, "z": 30.1, "orientation": 0.4},
        },
    }
    # Validate our fixture against the real contract model before using it.
    wow_sdk_protocol.ActionExecutionResult.model_validate(result_line)
    (tmp_path / "action-results.jsonl").write_text(
        json.dumps(result_line) + "\n", encoding="utf-8"
    )
    outcome = bridge.wait_for_result(request_id, timeout_s=2.0)
    assert outcome is not None
    assert outcome.success is True
    assert outcome.settlement_kind == "reached_target"
    assert outcome.displacement_yards == 12.5
    assert outcome.end_position is not None and outcome.end_position.x == 110.2


def test_wait_for_result_times_out_to_none(tmp_path: Path) -> None:
    bridge = ShimBridge(tmp_path)
    request_id = bridge.move_to(1.0, 2.0, 3.0, 1)
    assert bridge.wait_for_result(request_id, timeout_s=0.6) is None


def test_bridge_traces_intents_observations_and_outcomes(tmp_path: Path) -> None:
    from wowborg.trace import Tracer

    trace_file = tmp_path / "trace.jsonl"
    bridge = ShimBridge(tmp_path, Tracer(trace_file, echo_stdout=False))
    write_state(tmp_path, snapshot_payload())
    bridge.observe()
    bridge.observe()  # same tick — must not re-trace
    request_id = bridge.move_to(1.0, 2.0, 3.0, 1)
    bridge.wait_for_result(request_id, timeout_s=0.6)  # timeout path traces too

    events = [json.loads(line) for line in trace_file.read_text().splitlines()]
    kinds = [e["kind"] for e in events]
    assert kinds == ["observation", "intent", "outcome"]
    assert events[0]["tick"] == 42
    assert events[1]["action_kind"] == "move"
    assert events[2]["timeout"] is True


def test_say_is_rate_limited_and_queues_chat(tmp_path: Path) -> None:
    bridge = ShimBridge(tmp_path)
    first = bridge.say("hello replay")
    second = bridge.say("too soon")
    assert first is not None and second is None
    payload = json.loads((tmp_path / "action.json").read_text(encoding="utf-8"))
    assert payload["kind"] == "chat_say"
    assert payload["text"] == "hello replay"
    assert payload["request_id"] == first
