"""Unit tests for the Tracer (file + stdout channels)."""

from __future__ import annotations

import json
from pathlib import Path

from wowborg.trace import NullTracer, Tracer


def read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_emit_writes_jsonl_and_stdout(tmp_path: Path, capsys) -> None:
    tracer = Tracer(tmp_path / "trace.jsonl")
    tracer.emit("intent", request_id="r1", action_kind="move")
    tracer.emit("outcome", request_id="r1", success=True)

    events = read_events(tmp_path / "trace.jsonl")
    assert [e["kind"] for e in events] == ["intent", "outcome"]
    assert [e["seq"] for e in events] == [1, 2]
    assert all("ts" in e for e in events)
    assert events[0]["request_id"] == "r1"

    out = capsys.readouterr().out
    assert out.count("WOWBORG-TRACE") == 2
    # stdout lines carry the same JSON payload
    stdout_event = json.loads(out.splitlines()[0].split("WOWBORG-TRACE ", 1)[1])
    assert stdout_event == events[0]


def test_emit_survives_unwritable_file(tmp_path: Path, capsys) -> None:
    tracer = Tracer(tmp_path / "trace.jsonl")
    (tmp_path / "trace.jsonl").mkdir()  # now the file path is a directory → open() fails
    tracer.emit("intent", request_id="r1")
    assert "WOWBORG-TRACE" in capsys.readouterr().out


def test_non_serializable_payload_falls_back_to_str(tmp_path: Path) -> None:
    tracer = Tracer(tmp_path / "trace.jsonl", echo_stdout=False)
    tracer.emit("observation", position=object())
    events = read_events(tmp_path / "trace.jsonl")
    assert isinstance(events[0]["position"], str)


def test_from_env_override(tmp_path: Path, monkeypatch) -> None:
    override = tmp_path / "custom" / "t.jsonl"
    monkeypatch.setenv("WOWBORG_TRACE_FILE", str(override))
    tracer = Tracer.from_env(tmp_path)
    tracer.emit("session_start")
    assert override.exists()


def test_null_tracer_writes_nothing(tmp_path: Path, capsys) -> None:
    tracer = NullTracer()
    tracer.emit("intent", request_id="r1")
    assert capsys.readouterr().out == ""
