"""WebSocket byte-tunnel transport for WoW TCP services."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import websockets


class TunnelEOF(EOFError):
    """Raised when the byte tunnel closes cleanly."""


class WowTunnel:
    """A raw-byte duplex channel carried over binary WebSocket frames."""

    def __init__(self, websocket: object | None = None) -> None:
        self.websocket = websocket
        self._buffer = bytearray()

    @classmethod
    async def connect(
        cls,
        base_ws_url: str,
        service: str,
        slot: int,
        token: str,
        *,
        connector: Callable[..., Awaitable[object]] | None = None,
    ) -> "WowTunnel":
        """Open ``/tcp/<service>?slot=&token=`` on the Coworld runner host."""

        connect = connector or websockets.connect
        url = tunnel_url(base_ws_url, service, slot, token)
        websocket = await connect(url, ping_interval=None)
        return cls(websocket)

    async def send(self, data: bytes) -> None:
        if self.websocket is None:
            raise TunnelEOF("tunnel is not connected")
        await self.websocket.send(data)

    async def recv_exact(self, count: int) -> bytes:
        """Return exactly ``count`` bytes, reassembling across WS frames."""

        if count < 0:
            raise ValueError("count must be non-negative")
        while len(self._buffer) < count:
            if self.websocket is None:
                raise TunnelEOF("tunnel is not connected")
            try:
                message = await self.websocket.recv()
            except websockets.ConnectionClosedOK as exc:
                raise TunnelEOF("tunnel closed") from exc
            except websockets.ConnectionClosed as exc:
                raise TunnelEOF("tunnel closed") from exc
            if isinstance(message, str):
                message = message.encode("utf-8")
            if message == b"":
                raise TunnelEOF("tunnel closed")
            self._buffer.extend(message)
        result = bytes(self._buffer[:count])
        del self._buffer[:count]
        return result

    async def close(self) -> None:
        if self.websocket is not None and hasattr(self.websocket, "close"):
            await self.websocket.close()


def tunnel_url(base_ws_url: str, service: str, slot: int, token: str) -> str:
    """Build the tunnel URL on the same origin as the player websocket."""

    parts = urlsplit(base_ws_url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key not in {"slot", "token"}]
    query.extend([("slot", str(slot)), ("token", token)])
    return urlunsplit(parts._replace(path=f"/tcp/{service}", query=urlencode(query)))
