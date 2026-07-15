"""Unit tests for tools/cwreplay.py against a synthesized CWREPLAY fixture."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
import sys
import zlib
from pathlib import Path

TOOL_PATH = Path(__file__).resolve().parents[2] / "tools" / "cwreplay.py"
spec = importlib.util.spec_from_file_location("cwreplay_tool", TOOL_PATH)
cwreplay = importlib.util.module_from_spec(spec)
sys.modules["cwreplay_tool"] = cwreplay
spec.loader.exec_module(cwreplay)


def _string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack("<H", len(encoded)) + encoded


def _packet(from_client: bool, opcode: int, body: bytes, server_ms: int) -> bytes:
    direction = 0x00 if from_client else 0xFF
    opcode_bytes = struct.pack("<I", opcode) if from_client else struct.pack("<H", opcode)
    return (
        struct.pack("<B", direction)
        + struct.pack("<I", 1784000000)
        + struct.pack("<I", server_ms)
        + struct.pack("<I", len(opcode_bytes) + len(body))
        + opcode_bytes
        + body
    )


def _movement_body(flags: int, time_ms: int, x: float, y: float, z: float, o: float) -> bytes:
    return struct.pack("<II", flags, time_ms) + struct.pack("<ffff", x, y, z, o) + struct.pack("<I", 0)


def build_replay(tmp_path: Path) -> Path:
    login_verify = _packet(False, 566, struct.pack("<Iffff", 1, 1.0, 2.0, 3.0, 0.5), 100)
    move = _packet(True, 181, _movement_body(1, 0, 100.0, 200.0, 30.0, 0.0), 200)
    heartbeat = _packet(True, 238, _movement_body(1, 200, 103.0, 204.0, 30.0, 0.0), 400)
    say = _packet(True, 149, struct.pack("<II", 0, 0) + b"wowborg leg 1: reached_target\x00", 300)
    pkt = b"PKT" + struct.pack("<H", 0x0201) + struct.pack("<H", 5875) + b"\x00" * 40
    pkt += login_verify + move + heartbeat + say

    segment = (
        struct.pack("<Q", 0x1234)
        + _string("Freshwar")
        + struct.pack("<Q", 1784000000000)
        + struct.pack("<I", 4)
        + struct.pack("<Q", len(pkt))
        + hashlib.sha256(pkt).digest()
        + pkt
    )
    party_wire = (
        b"CWPARTY4" + struct.pack("<H", 1) + struct.pack("<I", 1) + struct.pack("<I", 0)
        + struct.pack("<H", 1) + segment
    )
    compressed = zlib.compress(party_wire)
    record = (
        struct.pack("<B", 0x02)
        + struct.pack("<Q", len(party_wire))
        + struct.pack("<Q", len(compressed))
        + hashlib.sha256(party_wire).digest()
        + compressed
    )
    header = json.dumps({"protocol": "vanilla_wow.replay.v4", "scope": "episode"}).encode()
    blob = (
        b"CWREPLAY" + struct.pack("<H", 1) + _string("vanilla_wow_local") + _string("0.1.4")
        + struct.pack("<Q", 1784000000000) + struct.pack("<I", len(header)) + header + record
    )
    path = tmp_path / "fixture.cwreplay"
    path.write_bytes(blob)
    return path


def test_decode_replay_fixture(tmp_path: Path) -> None:
    replay = cwreplay.decode_replay(build_replay(tmp_path))
    assert replay.game == "vanilla_wow_local"
    assert replay.header["protocol"] == "vanilla_wow.replay.v4"
    assert len(replay.members) == 1
    member = replay.members[0]
    assert member.name == "Freshwar"
    assert [p.opcode for p in member.packets] == [566, 181, 238, 149]
    assert member.packets[0].opcode_name == "SMSG_LOGIN_VERIFY_WORLD"


def test_chat_text_extraction(tmp_path: Path) -> None:
    replay = cwreplay.decode_replay(build_replay(tmp_path))
    say = replay.members[0].packets[3]
    assert cwreplay._chat_text(say) == "wowborg leg 1: reached_target"


def test_trajectory_from_outbound_movement(tmp_path: Path) -> None:
    replay = cwreplay.decode_replay(build_replay(tmp_path))
    member = replay.members[0]
    infos = [cwreplay._movement_info(p) for p in member.packets]
    positions = [i for i in infos if i is not None]
    assert len(positions) == 2
    assert (positions[0]["x"], positions[0]["y"]) == (100.0, 200.0)
    assert (positions[1]["x"], positions[1]["y"]) == (103.0, 204.0)
    # displacement 3-4-5 triangle: travelled distance = 5.0 yd
    dx = positions[1]["x"] - positions[0]["x"]
    dy = positions[1]["y"] - positions[0]["y"]
    assert (dx**2 + dy**2) ** 0.5 == 5.0
    # inbound and non-movement packets yield None
    assert infos[0] is None and infos[3] is None


def test_summary_counts(tmp_path: Path, capsys) -> None:
    replay = cwreplay.decode_replay(build_replay(tmp_path))
    cwreplay.cmd_summary(replay, as_json=True)
    summary = json.loads(capsys.readouterr().out)
    member = summary["members"][0]
    assert member["login_verified"] is True
    assert member["movement_packets"] == 2  # MSG_MOVE_START_FORWARD + HEARTBEAT
    assert member["chat_packets"] == 1


def test_rejects_bad_magic(tmp_path: Path) -> None:
    bad = tmp_path / "bad.cwreplay"
    bad.write_bytes(b"NOTMAGIC" + b"\x00" * 32)
    try:
        cwreplay.decode_replay(bad)
        raise AssertionError("expected ReplayError")
    except cwreplay.ReplayError:
        pass
