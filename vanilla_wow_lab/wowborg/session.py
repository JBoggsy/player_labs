"""Coworld ``/player`` control-plane supervisor."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from urllib.parse import parse_qs, urlsplit

import websockets


SESSION_PROTOCOL = "vanilla_wow.session.v1"


class SessionClosed(EOFError):
    """Raised when the Coworld control plane closes."""


@dataclass(frozen=True)
class WowSession:
    slot: int
    account_username: str
    account_password: str
    character_name: str
    token: str
    deadline_seconds: float | None = None


def token_from_url(url: str) -> str:
    values = parse_qs(urlsplit(url).query)
    return values.get("token", [""])[0]


async def read_wow_session(websocket, *, token: str) -> WowSession:
    while True:
        try:
            raw = await websocket.recv()
        except websockets.ConnectionClosedOK as exc:
            raise SessionClosed("session closed before wow_session") from exc
        message = json.loads(raw)
        if message.get("type") == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
            continue
        if message.get("protocol") != SESSION_PROTOCOL or message.get("type") != "wow_session":
            continue
        character_name = message.get("character_name")
        if not character_name:
            raise ValueError("wow_session character_name is null; wowborg v1 requires a seeded character")
        return WowSession(
            slot=int(message["slot"]),
            account_username=str(message["account_username"]),
            account_password=str(message["account_password"]),
            character_name=str(character_name),
            token=token,
            deadline_seconds=message.get("deadline_seconds"),
        )


async def supervise(websocket, slot: int, stop_event: asyncio.Event, *, detail: str = "loaded into world and idled") -> None:
    """Answer pings and set ``stop_event`` on final/close, then send done."""

    try:
        while not stop_event.is_set():
            try:
                raw = await websocket.recv()
            except websockets.ConnectionClosed:
                stop_event.set()
                return
            message = json.loads(raw)
            message_type = message.get("type")
            if message_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
            elif message_type == "final":
                stop_event.set()
                break
    finally:
        done = {
            "protocol": SESSION_PROTOCOL,
            "type": "done",
            "slot": slot,
            "success": True,
            "detail": detail,
        }
        try:
            await websocket.send(json.dumps(done))
        except Exception:
            pass
