"""Top-level wowborg orchestration."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Callable

import websockets

from wowborg.config import WowborgConfig, from_env
from wowborg.realmd import authenticate
from wowborg.session import read_wow_session, supervise, token_from_url
from wowborg.tunnel import TunnelEOF, WowTunnel
from wowborg.world import login_and_idle


async def run(
    player_ws_url: str,
    *,
    trace_outputs: Any | None = None,
    config: WowborgConfig | None = None,
    websocket_connector: Callable[..., Any] | None = None,
) -> int:
    """Run one Coworld slot to completion.

    Coworld treats abrupt websocket close as normal game termination for player
    processes, so this function returns ``0`` for closes and handled failures.
    """

    cfg = config or from_env()
    connect = websocket_connector or websockets.connect
    stop_event = asyncio.Event()
    try:
        player_ws = await connect(player_ws_url, ping_interval=None)
        session = await read_wow_session(player_ws, token=token_from_url(player_ws_url))
        realmd_tunnel = await WowTunnel.connect(player_ws_url, "realmd", session.slot, session.token, connector=connect)
        session_key = await authenticate(realmd_tunnel, session.account_username, session.account_password, config=cfg)
        await realmd_tunnel.close()
        world_tunnel = await WowTunnel.connect(player_ws_url, "world", session.slot, session.token, connector=connect)
        supervisor = asyncio.create_task(supervise(player_ws, session.slot, stop_event))
        world = asyncio.create_task(
            login_and_idle(
                world_tunnel,
                session.account_username,
                session.character_name,
                session_key,
                config=cfg,
                stop_event=stop_event,
            )
        )
        done, pending = await asyncio.wait({supervisor, world}, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
        stop_event.set()
        await asyncio.gather(*pending, return_exceptions=True)
        await world_tunnel.close()
    except (TunnelEOF, websockets.ConnectionClosed, EOFError):
        return 0
    except Exception as exc:
        print(f"wowborg exiting after handled error: {exc}", file=sys.stderr, flush=True)
        return 0
    return 0


def dumps_message(message: dict[str, Any]) -> str:
    """Stable JSON helper used by tests."""

    return json.dumps(message, separators=(",", ":"))
