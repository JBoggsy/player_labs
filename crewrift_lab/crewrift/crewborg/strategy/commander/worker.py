"""Background daemon worker for gameplay commander LLM calls."""

from __future__ import annotations

import threading
from time import perf_counter
from typing import Any

from crewrift.crewborg.strategy.commander.llm import CommanderLLMClient
from crewrift.crewborg.strategy.commander.trace import CommanderTrace
from players.player_sdk import OverwriteBuffer


class CommanderWorker:
    """Take latest serialized context, call the LLM client, publish raw priorities.

    The worker never touches live belief. Both directions use latest-value buffers
    so the inner loop cannot block on an LLM call and stale snapshots are overwritten.
    """

    def __init__(
        self,
        client: CommanderLLMClient,
        *,
        wait_timeout: float = 0.1,
        trace: CommanderTrace | None = None,
    ) -> None:
        self._client = client
        self._wait_timeout = wait_timeout
        self._trace = trace
        self.snapshots: OverwriteBuffer[dict[str, Any]] = OverwriteBuffer()
        self.priorities: OverwriteBuffer[dict[str, Any]] = OverwriteBuffer()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_recorded = False
        self._stopped_recorded = False

    @property
    def enabled(self) -> bool:
        return self._client.enabled

    def start(self) -> None:
        if self._thread is not None:
            return
        self._record_started()
        if not self._client.enabled:
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="crewborg-commander")
        self._thread.start()

    def close(self) -> None:
        self._record_stopped()
        self._stop.set()
        self.snapshots.close()
        self.priorities.close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            context = self.snapshots.wait_take(timeout=self._wait_timeout)
            if context is None:
                continue
            self._record("commander_call_start", _context_summary(context))
            started = perf_counter()
            try:
                result = self._client.decide(context)
            except Exception as exc:
                self._record(
                    "commander_call",
                    {
                        "outcome": "error",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "latency_ms": (perf_counter() - started) * 1000,
                    },
                )
                continue
            data: dict[str, Any] = {
                "outcome": "ok",
                "latency_ms": result.latency_ms,
                "model": result.model,
                "priorities": result.priorities,
            }
            if result.usage is not None:
                data["usage"] = result.usage
            if result.raw_request is not None:
                data["raw_request"] = result.raw_request
            if result.raw_response is not None:
                data["raw_response"] = result.raw_response
            self._record("commander_call", data)
            self.priorities.publish(result.priorities)

    def _record_started(self) -> None:
        if self._started_recorded:
            return
        self._started_recorded = True
        self._record(
            "commander_started",
            {
                "enabled": self._client.enabled,
                "backend": _client_backend(self._client),
                "model": _client_model(self._client),
                "disabled_reason": self._client.disabled_reason,
            },
        )

    def _record_stopped(self) -> None:
        if self._stopped_recorded:
            return
        self._stopped_recorded = True
        self._record("commander_stopped", {})

    def _record(self, event: str, data: dict[str, Any]) -> None:
        if self._trace is not None:
            self._trace.record(event, data)


def _context_summary(context: dict[str, Any]) -> dict[str, Any]:
    self_context = context.get("self")
    return {
        "phase": context.get("phase"),
        "role": self_context.get("role") if isinstance(self_context, dict) else None,
    }


def _client_backend(client: CommanderLLMClient) -> str | None:
    config = getattr(client, "config", None)
    if not client.enabled or config is None:
        return None
    return "bedrock" if bool(getattr(config, "use_bedrock", False)) else "anthropic"


def _client_model(client: CommanderLLMClient) -> str | None:
    config = getattr(client, "config", None)
    if not client.enabled or config is None:
        return None
    model = getattr(config, "model", None)
    return model if isinstance(model, str) else None
