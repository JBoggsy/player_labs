from __future__ import annotations

import asyncio
import sys
from collections import deque
from pathlib import Path

# wow_sdk ships in the v2 base image; for local test runs, use the read-only game-repo
# checkout's src/ when present. test_bridge.py importorskips wow_sdk if neither exists.
_GAME_REPO_SRC = Path.home() / "coding/coworlds/coworld-vanilla-wow/src"
if _GAME_REPO_SRC.is_dir() and str(_GAME_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_GAME_REPO_SRC))


class ScriptedTunnel:
    def __init__(self, chunks: list[bytes] | None = None) -> None:
        self._buffer = bytearray(b"".join(chunks or []))
        self.sent: list[bytes] = []
        self.closed = False

    async def send(self, data: bytes) -> None:
        self.sent.append(data)

    async def recv_exact(self, count: int) -> bytes:
        while len(self._buffer) < count:
            await asyncio.sleep(0)
        result = bytes(self._buffer[:count])
        del self._buffer[:count]
        return result

    def feed(self, data: bytes) -> None:
        self._buffer.extend(data)

    async def close(self) -> None:
        self.closed = True


class FakeWebSocket:
    def __init__(self, incoming: list[bytes | str] | None = None) -> None:
        self.incoming = deque(incoming or [])
        self.sent: list[bytes | str] = []
        self.closed = False

    async def send(self, data: bytes | str) -> None:
        self.sent.append(data)

    async def recv(self) -> bytes | str:
        while not self.incoming:
            await asyncio.sleep(0)
        item = self.incoming.popleft()
        if item == b"":
            raise EOFError("closed")
        return item

    async def close(self) -> None:
        self.closed = True

    def feed(self, data: bytes | str) -> None:
        self.incoming.append(data)
