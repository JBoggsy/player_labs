"""Background daemon worker for gameplay commander LLM calls."""

from __future__ import annotations

import threading
from typing import Any

from crewrift.crewborg.strategy.commander.llm import CommanderLLMClient
from players.player_sdk import OverwriteBuffer


class CommanderWorker:
    """Take latest serialized context, call the LLM client, publish raw priorities.

    The worker never touches live belief. Both directions use latest-value buffers
    so the inner loop cannot block on an LLM call and stale snapshots are overwritten.
    """

    def __init__(self, client: CommanderLLMClient, *, wait_timeout: float = 0.1) -> None:
        self._client = client
        self._wait_timeout = wait_timeout
        self.snapshots: OverwriteBuffer[dict[str, Any]] = OverwriteBuffer()
        self.priorities: OverwriteBuffer[dict[str, Any]] = OverwriteBuffer()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return self._client.enabled

    def start(self) -> None:
        if not self._client.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="crewborg-commander")
        self._thread.start()

    def close(self) -> None:
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
            try:
                result = self._client.decide(context)
            except Exception:
                continue
            self.priorities.publish(result.priorities)
