from __future__ import annotations

import time

from crewrift.crewborg.strategy.commander.llm import (
    CommanderLLMResult,
    DisabledCommanderClient,
    build_commander_client_from_env,
)
from crewrift.crewborg.strategy.commander.prompts import system_prompt_for_role
from crewrift.crewborg.strategy.commander.worker import CommanderWorker


class _FakeClient:
    enabled = True
    disabled_reason = None

    def decide(self, context: dict) -> CommanderLLMResult:
        return CommanderLLMResult(
            priorities={"hunt_room": context["legal_rooms"][0], "reason": "fake"},
            model="fake",
            latency_ms=1.0,
        )


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
