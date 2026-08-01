"""Unit tests for tools/trace_audit.py — the trace ↔ replay cross-check."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


trace_audit = _load("trace_audit_test_mod", TOOLS_DIR / "trace_audit.py")
cwreplay = sys.modules["cwreplay"]  # loaded by trace_audit at import

from test_cwreplay_tool import build_replay  # noqa: E402


def make_trace(tmp_path: Path, events: list[dict]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "trace.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return path


def agreeing_trace_events() -> list[dict]:
    # The fixture replay (test_cwreplay_tool.build_replay) has Freshwar moving 5.0 yd
    # and saying "wowborg leg 1: reached_target".
    return [
        {"kind": "session_start", "policy": "random_walk"},
        {"kind": "intent", "request_id": "r1", "action_kind": "move"},
        {
            "kind": "outcome",
            "request_id": "r1",
            "action_kind": "move",
            "success": True,
            "settlement_kind": "reached_target",
            "displacement_yards": 5.0,
        },
        {"kind": "say", "text": "wowborg leg 1: reached_target"},
        {"kind": "session_end"},
    ]


def test_audit_agreement(tmp_path: Path) -> None:
    replay = cwreplay.decode_replay(build_replay(tmp_path))
    report = trace_audit.audit(agreeing_trace_events(), replay, "Freshwar")
    assert report["ok"], report["findings"]
    assert report["trace"]["claimed_displacement_yd"] == 5.0
    assert report["replay"]["travelled_yd"] == 5.0
    assert report["replay"]["login_verified"] is True


def test_audit_flags_claimed_movement_without_packets(tmp_path: Path) -> None:
    replay = cwreplay.decode_replay(build_replay(tmp_path))
    events = agreeing_trace_events()
    events[2]["displacement_yards"] = 500.0  # trace claims far more than observed
    report = trace_audit.audit(events, replay, "Freshwar")
    assert not report["ok"]
    assert any("mismatch" in f for f in report["findings"])


def test_audit_flags_missing_breadcrumb(tmp_path: Path) -> None:
    replay = cwreplay.decode_replay(build_replay(tmp_path))
    events = agreeing_trace_events()
    events[3]["text"] = "this say never reached the wire"
    report = trace_audit.audit(events, replay, "Freshwar")
    assert not report["ok"]
    assert any("says missing" in f for f in report["findings"])


def test_audit_identifies_member_by_breadcrumb(tmp_path: Path) -> None:
    replay = cwreplay.decode_replay(build_replay(tmp_path))
    report = trace_audit.audit(agreeing_trace_events(), replay, None)
    # single member → identified even without breadcrumb; both paths must work
    assert report["replay"].get("member") == "Freshwar"


def test_main_exit_codes(tmp_path: Path) -> None:
    replay_path = build_replay(tmp_path)
    trace_path = make_trace(tmp_path, agreeing_trace_events())
    assert trace_audit.main([str(trace_path), str(replay_path), "--member", "Freshwar"]) == 0
    bad_trace = make_trace(
        tmp_path / "bad", [{"kind": "say", "text": "never said"}]
    )
    assert trace_audit.main([str(bad_trace), str(replay_path), "--member", "Freshwar"]) == 1
    assert trace_audit.main([str(tmp_path / "missing.jsonl"), str(replay_path)]) == 2
