"""Background daemon worker for meeting LLM calls.

Same shape as ``strategy/commander/worker.py``: the mode publishes a request into a
latest-wins buffer and polls a result buffer each tick, so the game loop never blocks
on an LLM call. Measured on the league (v86): synchronous meeting calls stalled the
loop ~3s each, lagging the belief clock ~670 ticks behind and losing selected votes to
``vote_timeout`` — the worker exists to make that stall impossible.

Unlike the commander worker, all tracing stays in the mode (``emit`` is tick-scoped);
the worker only ferries results and errors back. The mode keeps at most one request
in flight and matches outcomes by ``request_id`` so a stale delivery (e.g. from a
previous meeting) is dropped instead of applied.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from crewrift.crewborg.strategy.meeting.llm import MeetingLLMClient, MeetingLLMResult
from players.player_sdk import OverwriteBuffer


@dataclass(frozen=True)
class MeetingLLMRequest:
    """One serialized meeting-LLM call the mode wants executed off-loop."""

    request_id: int
    trigger: str
    context: dict[str, Any]


@dataclass(frozen=True)
class MeetingLLMOutcome:
    """The worker's answer to a request: a parsed result or the call error."""

    request_id: int
    trigger: str
    result: MeetingLLMResult | None = None
    error: str | None = None


class MeetingLLMWorker:
    """Take the latest meeting request, call the LLM client, publish the outcome.

    The worker never touches live belief. Both directions use latest-value buffers
    so the inner loop cannot block and an unread stale request is overwritten.
    """

    def __init__(self, client: MeetingLLMClient, *, wait_timeout: float = 0.1) -> None:
        self._client = client
        self._wait_timeout = wait_timeout
        self.requests: OverwriteBuffer[MeetingLLMRequest] = OverwriteBuffer()
        self.results: OverwriteBuffer[MeetingLLMOutcome] = OverwriteBuffer()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="crewborg-meeting-llm")
        self._thread.start()

    def close(self) -> None:
        """Stop the worker without blocking the game loop.

        Deliberately no ``join``: close() runs on the inner loop (mode ``on_exit``),
        and a call in flight can take seconds. The daemon thread notices the closed
        request buffer / stop flag after the current call and exits on its own.
        """

        self._stop.set()
        self.requests.close()
        self.results.close()

    def _run(self) -> None:
        while not self._stop.is_set():
            request = self.requests.wait_take(timeout=self._wait_timeout)
            if request is None:
                continue
            try:
                result = self._client.decide(request.context, trigger=request.trigger)
            except Exception as exc:
                self.results.publish(
                    MeetingLLMOutcome(request_id=request.request_id, trigger=request.trigger, error=repr(exc))
                )
                continue
            self.results.publish(
                MeetingLLMOutcome(request_id=request.request_id, trigger=request.trigger, result=result)
            )
