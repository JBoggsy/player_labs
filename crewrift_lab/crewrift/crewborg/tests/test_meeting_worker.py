"""Async meeting-LLM worker: non-blocking publish, late delivery, error ferrying."""

from __future__ import annotations

import time

from crewrift.crewborg.strategy.meeting import MeetingDecision, MeetingLLMResult
from crewrift.crewborg.strategy.meeting.worker import MeetingLLMOutcome, MeetingLLMRequest, MeetingLLMWorker


class _SlowClient:
    enabled = True
    disabled_reason = None

    def __init__(self, decision: MeetingDecision, *, delay: float = 0.15) -> None:
        self._decision = decision
        self._delay = delay

    def decide(self, context: dict, *, trigger: str) -> MeetingLLMResult:
        time.sleep(self._delay)
        return MeetingLLMResult(decision=self._decision, model="fake-haiku", latency_ms=self._delay * 1000)


class _FailingClient:
    enabled = True
    disabled_reason = None

    def decide(self, context: dict, *, trigger: str) -> MeetingLLMResult:
        raise RuntimeError("429 Too many tokens per day")


def _wait_outcome(worker: MeetingLLMWorker, timeout: float = 2.0) -> MeetingLLMOutcome:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        outcome = worker.results.take()
        if outcome is not None:
            return outcome
        time.sleep(0.005)
    raise AssertionError("no outcome delivered within timeout")


def test_worker_delivers_late_decision_without_blocking_publisher() -> None:
    worker = MeetingLLMWorker(_SlowClient(MeetingDecision(action="wait"), delay=0.15), wait_timeout=0.01)
    worker.start()
    try:
        started = time.perf_counter()
        worker.requests.publish(MeetingLLMRequest(request_id=1, trigger="meeting_start", context={}))
        assert time.perf_counter() - started < 0.05  # publish never blocks on the call
        assert worker.results.take() is None  # the slow call has not delivered yet

        outcome = _wait_outcome(worker)
        assert outcome.request_id == 1
        assert outcome.trigger == "meeting_start"
        assert outcome.error is None
        assert outcome.result is not None and outcome.result.decision.action == "wait"
    finally:
        worker.close()


def test_worker_ferries_call_errors_as_outcomes() -> None:
    worker = MeetingLLMWorker(_FailingClient(), wait_timeout=0.01)
    worker.start()
    try:
        worker.requests.publish(MeetingLLMRequest(request_id=7, trigger="deadline", context={}))
        outcome = _wait_outcome(worker)
        assert outcome.request_id == 7
        assert outcome.result is None
        assert outcome.error is not None and "429" in outcome.error
    finally:
        worker.close()


def test_worker_close_does_not_block_on_an_inflight_call() -> None:
    worker = MeetingLLMWorker(_SlowClient(MeetingDecision(action="wait"), delay=0.3), wait_timeout=0.01)
    worker.start()
    worker.requests.publish(MeetingLLMRequest(request_id=1, trigger="meeting_start", context={}))
    time.sleep(0.02)  # let the worker pick the request up

    started = time.perf_counter()
    worker.close()
    assert time.perf_counter() - started < 0.05  # close (mode on_exit) never waits for the call
