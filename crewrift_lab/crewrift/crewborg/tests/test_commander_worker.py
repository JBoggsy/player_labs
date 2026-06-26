from __future__ import annotations

import time

from crewrift.crewborg.strategy.commander.llm import (
    CommanderLLMConfig,
    CommanderLLMResult,
    DisabledCommanderClient,
    build_commander_client_from_env,
)
from crewrift.crewborg.strategy.commander.prompts import system_prompt_for_role
from crewrift.crewborg.strategy.commander.trace import CommanderTrace
from crewrift.crewborg.strategy.commander.worker import CommanderWorker


class _FakeClient:
    enabled = True
    disabled_reason = None
    config = CommanderLLMConfig(model="fake-model", use_bedrock=True, trace_raw=True)

    def decide(self, context: dict) -> CommanderLLMResult:
        return CommanderLLMResult(
            priorities={"hunt_room": context["legal_rooms"][0], "reason": "fake"},
            model="fake",
            latency_ms=1.0,
            raw_request={"context": context},
            raw_response='{"hunt_room":"electrical"}',
        )


class _ErrorClient(_FakeClient):
    def decide(self, context: dict) -> CommanderLLMResult:
        del context
        raise PermissionError("bedrock 403")


def test_worker_publishes_priorities() -> None:
    worker = CommanderWorker(_FakeClient())
    worker.start()
    try:
        worker.snapshots.publish({"legal_rooms": ["electrical"], "legal_players": []})

        output = None
        for _ in range(50):
            output = worker.priorities.take()
            if output is not None:
                break
            time.sleep(0.02)

        assert output is not None
        assert output["hunt_room"] == "electrical"
    finally:
        worker.close()


def test_worker_records_enabled_start_success_and_stop() -> None:
    trace = CommanderTrace()
    worker = CommanderWorker(_FakeClient(), trace=trace)
    worker.start()
    try:
        worker.snapshots.publish({"phase": "Playing", "self": {"role": "imposter"}, "legal_rooms": ["electrical"]})

        output = None
        for _ in range(50):
            output = worker.priorities.take()
            if output is not None:
                break
            time.sleep(0.02)
    finally:
        worker.close()

    assert output is not None
    events = trace.drain()
    assert events[0] == (
        "commander_started",
        {
            "enabled": True,
            "backend": "bedrock",
            "model": "fake-model",
            "disabled_reason": None,
        },
    )
    assert ("commander_call_start", {"phase": "Playing", "role": "imposter"}) in events
    call = [data for event, data in events if event == "commander_call"][0]
    assert call == {
        "outcome": "ok",
        "latency_ms": 1.0,
        "model": "fake",
        "priorities": {"hunt_room": "electrical", "reason": "fake"},
        "raw_request": {
            "context": {"phase": "Playing", "self": {"role": "imposter"}, "legal_rooms": ["electrical"]}
        },
        "raw_response": '{"hunt_room":"electrical"}',
    }
    assert events[-1] == ("commander_stopped", {})


def test_worker_records_disabled_start() -> None:
    trace = CommanderTrace()
    worker = CommanderWorker(DisabledCommanderClient("disabled"), trace=trace)

    worker.start()

    assert trace.drain() == [
        (
            "commander_started",
            {
                "enabled": False,
                "backend": None,
                "model": None,
                "disabled_reason": "disabled",
            },
        )
    ]


def test_worker_records_call_errors_without_stopping() -> None:
    trace = CommanderTrace()
    worker = CommanderWorker(_ErrorClient(), trace=trace)
    worker.start()
    calls: list[dict] = []
    try:
        worker.snapshots.publish({"phase": "Playing", "self": {"role": "crewmate"}})
        for _ in range(50):
            calls = [data for event, data in trace.drain() if event == "commander_call"]
            if calls:
                break
            time.sleep(0.02)
    finally:
        worker.close()

    [call] = calls
    assert call["outcome"] == "error"
    assert call["error_type"] == "PermissionError"
    assert call["error"] == "bedrock 403"
    assert call["latency_ms"] >= 0


def test_disabled_worker_never_runs() -> None:
    worker = CommanderWorker(DisabledCommanderClient("disabled"))
    worker.start()
    try:
        worker.snapshots.publish({"legal_rooms": ["x"], "legal_players": []})
        time.sleep(0.1)

        assert worker.priorities.take() is None
    finally:
        worker.close()


def test_build_commander_client_disabled_without_flag() -> None:
    client = build_commander_client_from_env({})

    assert client.enabled is False
    assert "CREWBORG_LLM_COMMANDER" in (client.disabled_reason or "")


def test_build_commander_client_disabled_without_backend() -> None:
    client = build_commander_client_from_env({"CREWBORG_LLM_COMMANDER": "1"})

    assert client.enabled is False
    assert client.disabled_reason == "no LLM backend configured"


def test_prompt_loader_uses_baked_fallback_for_missing_prompt_dir() -> None:
    prompt = system_prompt_for_role("imposter", prompt_dir="/does/not/exist")

    assert "Choose exactly one JSON object" in prompt
    assert "DANGER fields" in prompt
