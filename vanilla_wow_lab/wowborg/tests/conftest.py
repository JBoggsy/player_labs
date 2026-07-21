from __future__ import annotations

import asyncio
import sys
from collections import deque
from pathlib import Path

# wow_sdk ships in the v2 base image; local tests MUST validate against the PINNED
# image's copy, not the game-repo checkout's HEAD (whose file-bridge contract drifts —
# e.g. HEAD dropped action_file on 2026-07 while our pinned 0.1.19 base still has it).
# The snapshot is extracted from the digest-pinned base by:
#   source vanilla_wow_lab/tools/versions.env
#   CID=$(docker create --platform=linux/amd64 "$WOWBORG_BASE_IMAGE")
#   docker cp "$CID:/usr/local/lib/python3.12/site-packages/wow_sdk" vanilla_wow_lab/.sdk-snapshot/
#   docker rm "$CID"
# Re-extract whenever versions.env bumps. test_bridge.py importorskips if absent.
_SDK_SNAPSHOT = Path(__file__).resolve().parents[2] / ".sdk-snapshot"
if (_SDK_SNAPSHOT / "wow_sdk").is_dir() and str(_SDK_SNAPSHOT) not in sys.path:
    sys.path.insert(0, str(_SDK_SNAPSHOT))


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
