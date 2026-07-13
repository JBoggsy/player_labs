import asyncio
import json

import pytest

from wowborg import run as run_module

from conftest import FakeWebSocket, ScriptedTunnel


@pytest.mark.asyncio
async def test_run_orchestrates_session_tunnels_and_done(monkeypatch) -> None:
    player_ws = FakeWebSocket(
        [
            json.dumps(
                {
                    "protocol": "vanilla_wow.session.v1",
                    "type": "wow_session",
                    "slot": 3,
                    "account_username": "COWORLD",
                    "account_password": "secret",
                    "character_name": "Nightsun",
                    "deadline_seconds": 60.0,
                }
            ),
            json.dumps({"protocol": "vanilla_wow.session.v1", "type": "final"}),
        ]
    )
    realmd_tunnel = ScriptedTunnel()
    world_tunnel = ScriptedTunnel()
    connected_urls: list[str] = []

    async def fake_connect(url: str, **kwargs):
        connected_urls.append(url)
        return player_ws

    async def fake_tunnel_connect(base_ws_url: str, service: str, slot: int, token: str, **kwargs):
        assert base_ws_url == "ws://runner/player?slot=3&token=tok"
        assert slot == 3
        assert token == "tok"
        return realmd_tunnel if service == "realmd" else world_tunnel

    async def fake_authenticate(tunnel, username: str, password: str, **kwargs) -> bytes:
        assert tunnel is realmd_tunnel
        assert (username, password) == ("COWORLD", "secret")
        return bytes(range(40))

    async def fake_login_and_idle(tunnel, account: str, character_name: str, session_key: bytes, *, config, stop_event):
        assert tunnel is world_tunnel
        assert (account, character_name, session_key) == ("COWORLD", "Nightsun", bytes(range(40)))
        await stop_event.wait()
        return None

    monkeypatch.setattr(run_module.WowTunnel, "connect", fake_tunnel_connect)
    monkeypatch.setattr(run_module, "authenticate", fake_authenticate)
    monkeypatch.setattr(run_module, "login_and_idle", fake_login_and_idle)

    assert await run_module.run("ws://runner/player?slot=3&token=tok", websocket_connector=fake_connect) == 0
    assert connected_urls == ["ws://runner/player?slot=3&token=tok"]
    done_messages = [json.loads(item) for item in player_ws.sent if isinstance(item, str)]
    assert done_messages[-1] == {
        "protocol": "vanilla_wow.session.v1",
        "type": "done",
        "slot": 3,
        "success": True,
        "detail": "loaded into world and idled",
    }
