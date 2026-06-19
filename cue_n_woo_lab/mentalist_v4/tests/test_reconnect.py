"""The reconnect loop: a mid-episode socket drop must NOT orphan us. We reconnect
and resume from the server's fresh state broadcast until the engine sees game-over.

This guards the #1 cause of qualifier DQ: a dropped connection (idle during a slow
judge phase, or a transient blip) leaving us inactive -> -100 -> mean<=0 -> DQ.
"""
from __future__ import annotations

import asyncio
from typing import Any

import mentalist_v4.__main__ as m


class _FakeBridge:
    """Stands in for run_message_bridge. Each call = one 'connection' that feeds a
    scripted list of state messages to the handler, then 'closes' (returns) — simulating
    the server dropping us. The reconnect loop should call us again until engine.done."""

    def __init__(self, connections: list[list[dict[str, Any]]]):
        self.connections = connections
        self.calls = 0
        self.sent: list[list[str]] = []  # frames the handler returned, per message

    async def __call__(self, url, handler, **kwargs):
        msgs = self.connections[self.calls] if self.calls < len(self.connections) else []
        self.calls += 1
        import json
        for msg in msgs:
            replies = handler(json.dumps(msg))
            if asyncio.iscoroutine(replies):
                replies = await replies
            self.sent.append(replies)
        # connection closes (returns) — mimics a server-side drop / game-over close


def _state(phase, judge=None, proposals=None, answers=None, opp=None, done=False):
    return {"type": "state", "phase": phase, "done": done,
            "me": {"judge": judge or [], "proposals": proposals or [], "answers": answers or []},
            "opponent_questions": opp or []}


def test_reconnects_after_midepisode_drop_until_done(monkeypatch):
    """Connection 1 delivers some interview states then drops; the loop must reconnect
    (connection 2) and keep going until it sees phase=reveal (engine.done)."""
    # connection 1: one private-questions state (we ask a probe), then the socket drops.
    conn1 = [_state("private_questions", judge=[])]
    # connection 2: server re-broadcasts; eventually reveal -> done.
    conn2 = [_state("private_questions", judge=[{"question": "q", "answer": "a"}]),
             _state("reveal", done=True)]
    bridge = _FakeBridge([conn1, conn2])

    monkeypatch.setattr(m, "run_message_bridge", bridge)
    monkeypatch.setenv("COWORLD_PLAYER_WS_URL", "ws://fake")
    # avoid real Bedrock/fingerprint init
    monkeypatch.setattr(m, "Fingerprinter", lambda **k: None)
    monkeypatch.setattr(m, "AnswerWriter", lambda *a, **k: None)
    monkeypatch.setattr(m.config, "FINGERPRINT_ENABLED", False)
    async def _no_sleep(*_a, **_k):
        return None
    monkeypatch.setattr(m.asyncio, "sleep", _no_sleep)

    asyncio.run(asyncio.wait_for(m._run(), timeout=5))

    # We must have reconnected at least once (>=2 bridge calls) and ended via game-over.
    assert bridge.calls >= 2, f"expected reconnect, got {bridge.calls} connection(s)"


def test_quiet_close_does_not_exit_on_connection_closed():
    """The reconnect close policy must swallow ConnectionClosed (so the loop continues),
    unlike the SDK default which ends the process."""
    from websockets.exceptions import ConnectionClosedError
    # Should NOT raise / exit:
    m._quiet_close(None)
    m._quiet_close(ConnectionClosedError(None, None))
    # A non-close error still propagates:
    import pytest
    with pytest.raises(ValueError):
        m._quiet_close(ValueError("boom"))
