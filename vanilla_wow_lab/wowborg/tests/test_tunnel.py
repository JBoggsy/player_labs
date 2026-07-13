import pytest

from wowborg.tunnel import WowTunnel, tunnel_url


def test_tunnel_url_reuses_origin_and_token() -> None:
    assert tunnel_url("ws://runner.example/player?slot=2&token=abc&x=1", "world", 4, "tok").startswith(
        "ws://runner.example/tcp/world?"
    )
    assert tunnel_url("ws://runner.example/player?slot=2&token=abc&x=1", "world", 4, "tok").endswith(
        "x=1&slot=4&token=tok"
    )


@pytest.mark.asyncio
async def test_recv_exact_reassembles_websocket_frames() -> None:
    class FakeWebSocket:
        def __init__(self) -> None:
            self.frames = [b"ab", b"cdef", b"ghi"]
            self.sent = []

        async def recv(self):
            return self.frames.pop(0)

        async def send(self, data):
            self.sent.append(data)

    ws = FakeWebSocket()
    tunnel = WowTunnel(ws)
    assert await tunnel.recv_exact(3) == b"abc"
    assert await tunnel.recv_exact(4) == b"defg"
    await tunnel.send(b"out")
    assert ws.sent == [b"out"]
