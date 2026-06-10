"""In-process bridge smoke (design §3).

Stands up a real websocket server, streams a few binary "scene" frames, and
asserts the bridge connects, drives the idle runtime, sends the neutral input
packet exactly once (send-only-on-change), and exits cleanly when the server
closes the socket.
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
import zipfile

import pytest
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed, ConnectionClosedError

from crewrift.crewborg.action import INPUT_HEADER, encode_chat
from crewrift.crewborg.coworld.policy_player import build_trace_outputs, run_bridge
from crewrift.crewborg.tests import sprite_wire as w
from crewrift.crewborg.types import Command
from players.player_sdk import NullMetricsSink, TraceEvent

pytestmark = pytest.mark.asyncio


def _json_records(raw: str) -> list[dict]:
    """Parse the JSON lines from a stream, skipping plain-text warnings."""

    records = []
    for line in raw.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


async def test_bridge_defaults_to_lean_trace_and_no_metrics(monkeypatch) -> None:
    class FakeRuntime:
        def close(self) -> None:
            pass

    captured: dict[str, object] = {}
    stderr = io.StringIO()
    monkeypatch.delenv("CREWBORG_TRACE", raising=False)
    monkeypatch.delenv("CREWBORG_METRICS", raising=False)
    monkeypatch.delenv("CREWBORG_TRACE_OUTPUTS", raising=False)
    monkeypatch.delenv("COWORLD_PLAYER_ARTIFACT_UPLOAD_URL", raising=False)
    monkeypatch.setattr(sys, "stderr", stderr)

    def build(**kwargs):
        captured.update(kwargs)
        return FakeRuntime()

    def failing_connect(*_args, **_kwargs):
        raise RuntimeError("connect failed")

    with pytest.raises(RuntimeError, match="connect failed"):
        await run_bridge("ws://unused", connect=failing_connect, build=build)

    assert isinstance(captured["metrics_sink"], NullMetricsSink)
    trace_sink = captured["trace_sink"]
    trace_sink.record(TraceEvent(tick=1, name="perception", data={}))
    trace_sink.record(TraceEvent(tick=2, name="domain.meeting_vote_selected", data={}))
    records = _json_records(stderr.getvalue())
    assert [record["event"] for record in records] == ["domain.meeting_vote_selected"]


async def test_bridge_enables_metrics_when_requested(monkeypatch) -> None:
    class FakeRuntime:
        def close(self) -> None:
            pass

    captured: dict[str, object] = {}
    monkeypatch.setenv("CREWBORG_METRICS", "1")
    monkeypatch.delenv("CREWBORG_TRACE_OUTPUTS", raising=False)
    monkeypatch.delenv("COWORLD_PLAYER_ARTIFACT_UPLOAD_URL", raising=False)
    monkeypatch.setattr(sys, "stderr", io.StringIO())

    def build(**kwargs):
        captured.update(kwargs)
        return FakeRuntime()

    def failing_connect(*_args, **_kwargs):
        raise RuntimeError("connect failed")

    with pytest.raises(RuntimeError, match="connect failed"):
        await run_bridge("ws://unused", connect=failing_connect, build=build)

    assert not isinstance(captured["metrics_sink"], NullMetricsSink)


async def test_trace_outputs_default_to_artifact_zip(tmp_path, monkeypatch) -> None:
    """With the runner-provided upload URL present, the default output is the
    player artifact zip: traces land in telemetry.jsonl inside the uploaded
    zip, not on stderr (design §11; metta PLAYER_ARTIFACT contract)."""

    destination = tmp_path / "policy_artifact_0.zip"
    stderr = io.StringIO()
    monkeypatch.delenv("CREWBORG_TRACE", raising=False)
    monkeypatch.delenv("CREWBORG_METRICS", raising=False)
    monkeypatch.delenv("CREWBORG_TRACE_OUTPUTS", raising=False)
    monkeypatch.setenv("COWORLD_PLAYER_ARTIFACT_UPLOAD_URL", f"file://{destination}")
    monkeypatch.setattr(sys, "stderr", stderr)

    outputs = build_trace_outputs()
    outputs.trace_sink.record(TraceEvent(tick=1, name="domain.vote_cast", data={}))
    outputs.close()

    assert not _json_records(stderr.getvalue())
    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        telemetry = next(name for name in names if name != "manifest.json")
        records = _json_records(archive.read(telemetry).decode("utf-8"))
    assert [record["event"] for record in records] == ["domain.vote_cast"]


async def test_trace_outputs_fall_back_to_stderr_without_upload_url(monkeypatch) -> None:
    """Without an upload URL (bridge running outside a runner) the artifact
    default must degrade to stderr JSONL instead of raising — a crash here
    would happen before connect and fail the episode."""

    stderr = io.StringIO()
    monkeypatch.delenv("CREWBORG_TRACE", raising=False)
    monkeypatch.delenv("CREWBORG_METRICS", raising=False)
    monkeypatch.delenv("CREWBORG_TRACE_OUTPUTS", raising=False)
    monkeypatch.delenv("COWORLD_PLAYER_ARTIFACT_UPLOAD_URL", raising=False)
    monkeypatch.setattr(sys, "stderr", stderr)

    outputs = build_trace_outputs()
    outputs.trace_sink.record(TraceEvent(tick=1, name="domain.vote_cast", data={}))
    outputs.close()

    raw = stderr.getvalue()
    assert "falling back" in raw
    records = _json_records(raw)
    assert [record["event"] for record in records] == ["domain.vote_cast"]


async def test_bridge_runs_idle_loop_and_exits_cleanly() -> None:
    bridge_packets: list[bytes] = []

    async def handler(websocket) -> None:
        # Stream three valid scene frames, then drain whatever the bridge replies
        # with and close (returning from the handler closes the connection).
        for _ in range(3):
            await websocket.send(w.clear_objects())
        try:
            while True:
                bridge_packets.append(await asyncio.wait_for(websocket.recv(), timeout=0.25))
        except (asyncio.TimeoutError, ConnectionClosed):
            return

    async with serve(handler, "localhost", 0) as server:
        port = server.sockets[0].getsockname()[1]
        url = f"ws://localhost:{port}/player?slot=0&token="
        # The bridge must return on its own when the server closes the socket.
        await asyncio.wait_for(run_bridge(url), timeout=5.0)

    # Idle holds mask 0; the bridge sends the neutral packet once and nothing
    # after, since the held mask never changes.
    assert bridge_packets == [bytes([INPUT_HEADER, 0x00])]


async def test_bridge_treats_unclean_close_as_game_end() -> None:
    """The Crewrift Nim server drops the ``/player`` socket without a close
    handshake (code 1006, "no close frame received or sent") at game end. The
    bridge must treat that unclean close as normal termination — return without
    raising so the container exits 0 — and still close the runtime. (The
    websockets async iterator swallows a *clean* close but re-raises
    ``ConnectionClosedError`` on an unclean one, which is what this guards.)"""

    class FakeRuntime:
        def __init__(self) -> None:
            self.closed = False

        def step(self, _observation) -> Command:
            return Command(held_mask=0)

        def close(self) -> None:
            self.closed = True

    fake_runtime = FakeRuntime()

    class UncleanConnection:
        """Async context manager + iterator: yields one scene frame, then raises
        ``ConnectionClosedError`` exactly as the real server's abrupt close does."""

        def __init__(self) -> None:
            self._frame_sent = False

        async def __aenter__(self) -> UncleanConnection:
            return self

        async def __aexit__(self, *exc: object) -> bool:
            return False

        def __aiter__(self) -> UncleanConnection:
            return self

        async def __anext__(self) -> bytes:
            if not self._frame_sent:
                self._frame_sent = True
                return w.clear_objects()
            raise ConnectionClosedError(None, None)

        async def send(self, _data: bytes) -> None:
            pass

    def fake_connect(*_args: object, **_kwargs: object) -> UncleanConnection:
        return UncleanConnection()

    # Must return (not raise) despite the unclean close, and still close the runtime.
    await asyncio.wait_for(
        run_bridge("ws://unused", connect=fake_connect, build=lambda **_: fake_runtime),
        timeout=5.0,
    )
    assert fake_runtime.closed


async def test_bridge_closes_runtime_when_connect_raises() -> None:
    """A failure anywhere in connect/loop/send must still close the runtime
    (the strategy runner may own background threads/tasks)."""

    class FakeRuntime:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    fake = FakeRuntime()

    def failing_connect(*args, **kwargs):
        raise RuntimeError("connect failed")

    with pytest.raises(RuntimeError, match="connect failed"):
        await run_bridge("ws://unused", connect=failing_connect, build=lambda **_: fake)

    assert fake.closed


async def test_bridge_sends_chat_packet() -> None:
    received: list[bytes] = []

    class ChattyRuntime:
        def __init__(self) -> None:
            self.steps = 0

        def step(self, _observation) -> Command:
            self.steps += 1
            return Command(held_mask=0, chat="gg") if self.steps == 1 else Command(held_mask=0)

        def close(self) -> None:
            pass

    async def handler(websocket) -> None:
        await websocket.send(w.clear_objects())
        try:
            while True:
                received.append(await asyncio.wait_for(websocket.recv(), timeout=0.25))
        except (asyncio.TimeoutError, ConnectionClosed):
            return

    async with serve(handler, "localhost", 0) as server:
        port = server.sockets[0].getsockname()[1]
        url = f"ws://localhost:{port}/player?slot=0&token="
        await asyncio.wait_for(run_bridge(url, build=lambda **_: ChattyRuntime()), timeout=5.0)

    assert encode_chat("gg") in received


async def test_bridge_emits_latency_metrics_to_artifact(tmp_path, monkeypatch) -> None:
    """With metrics on, each tick must produce bridge.step_ms / loop_gap_ms /
    tick_drift records in the artifact — the wall-clock fall-behind
    instrumentation (the engine streams in real time; local tick numbers can't
    show lag)."""

    destination = tmp_path / "policy_artifact_0.zip"
    monkeypatch.setenv("CREWBORG_METRICS", "1")
    monkeypatch.delenv("CREWBORG_TRACE", raising=False)
    monkeypatch.delenv("CREWBORG_TRACE_OUTPUTS", raising=False)
    monkeypatch.setenv("COWORLD_PLAYER_ARTIFACT_UPLOAD_URL", f"file://{destination}")

    class FakeRuntime:
        def step(self, _observation) -> Command:
            return Command(held_mask=0)

        def close(self) -> None:
            pass

    async def handler(websocket) -> None:
        for _ in range(3):
            await websocket.send(w.clear_objects())
        try:
            while True:
                await asyncio.wait_for(websocket.recv(), timeout=0.25)
        except (asyncio.TimeoutError, ConnectionClosed):
            return

    async with serve(handler, "localhost", 0) as server:
        port = server.sockets[0].getsockname()[1]
        url = f"ws://localhost:{port}/player?slot=0&token="
        await asyncio.wait_for(run_bridge(url, build=lambda **_: FakeRuntime()), timeout=5.0)

    with zipfile.ZipFile(destination) as archive:
        telemetry = next(name for name in archive.namelist() if name != "manifest.json")
        records = _json_records(archive.read(telemetry).decode("utf-8"))
    by_name: dict[str, list[dict]] = {}
    for record in records:
        if record.get("kind") == "metric":
            by_name.setdefault(record["name"], []).append(record)

    assert len(by_name["bridge.step_ms"]) == 3          # one per frame
    assert len(by_name["bridge.loop_gap_ms"]) == 2      # gaps between 3 frames
    assert len(by_name["bridge.tick_drift"]) == 3
    assert by_name["bridge.step_ms"][0]["tags"] == {"tick": 1}
    assert by_name["bridge.step_ms"][-1]["tags"] == {"tick": 3}
