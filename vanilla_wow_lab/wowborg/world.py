"""Mangosd world login and idle loop."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib

from wowborg import opcodes
from wowborg.config import WowborgConfig
from wowborg.crypt import HeaderCrypt
from wowborg.wire import ByteReader, ByteWriter, WorldPacket, build_client_packet, parse_server_header


AUTH_OK = 12
AUTH_WAIT_QUEUE = 27


class WorldError(RuntimeError):
    """Raised for rejected or malformed world-server login."""


@dataclass(frozen=True)
class CharacterSummary:
    guid: int
    name: str
    race: int
    class_id: int
    gender: int
    level: int
    zone_id: int
    map_id: int
    x: float
    y: float
    z: float
    flags: int


@dataclass(frozen=True)
class LoginLocation:
    map_id: int
    x: float
    y: float
    z: float
    orientation: float


async def read_world_packet(tunnel, crypt: HeaderCrypt | None = None, *, encrypted: bool = False) -> WorldPacket:
    header = await tunnel.recv_exact(4)
    opcode, body_len = parse_server_header(header, crypt, encrypted=encrypted)
    body = await tunnel.recv_exact(body_len)
    return WorldPacket(opcode, body)


async def send_world_packet(tunnel, opcode: int, body: bytes, crypt: HeaderCrypt | None = None, *, encrypted: bool = False) -> None:
    await tunnel.send(build_client_packet(opcode, body, crypt, encrypted=encrypted))


def build_auth_digest(account: str, client_seed: int, server_seed: int, session_key: bytes) -> bytes:
    writer = ByteWriter()
    writer.add_ascii(account.upper())
    writer.add_u32_le(0)
    writer.add_u32_le(client_seed)
    writer.add_u32_le(server_seed)
    writer.add_bytes(session_key)
    return hashlib.sha1(writer.finish()).digest()


def build_auth_session(account: str, server_seed: int, session_key: bytes, cfg: WowborgConfig) -> bytes:
    username = account.upper()
    writer = ByteWriter()
    writer.add_u32_le(opcodes.CLIENT_BUILD)
    writer.add_u32_le(0)
    writer.add_cstring(username)
    writer.add_u32_le(cfg.client_seed)
    writer.add_bytes(build_auth_digest(username, cfg.client_seed, server_seed, session_key))
    return writer.finish()


def parse_auth_challenge(packet: WorldPacket) -> int:
    if packet.opcode != opcodes.SMSG_AUTH_CHALLENGE:
        raise WorldError(f"expected SMSG_AUTH_CHALLENGE, got {packet.opcode}")
    return ByteReader(packet.body).read_u32_le()


def parse_auth_response(packet: WorldPacket) -> None:
    if packet.opcode != opcodes.SMSG_AUTH_RESPONSE:
        raise WorldError(f"expected SMSG_AUTH_RESPONSE, got {packet.opcode}")
    reader = ByteReader(packet.body)
    status = reader.read_u8()
    if status == AUTH_OK:
        return
    if status == AUTH_WAIT_QUEUE:
        detail = "world auth queued"
        if reader.remaining >= 4:
            detail = f"{detail} at position {reader.read_u32_le()}"
        raise WorldError(detail)
    raise WorldError(f"world auth failed with status {status}")


def parse_char_enum_body(body: bytes) -> list[CharacterSummary]:
    reader = ByteReader(body)
    count = reader.read_u8()
    characters: list[CharacterSummary] = []
    for _ in range(count):
        guid = reader.read_u64_le()
        name = reader.read_cstring()
        race = reader.read_u8()
        class_id = reader.read_u8()
        gender = reader.read_u8()
        reader.skip(5)
        level = reader.read_u8()
        zone_id = reader.read_u32_le()
        map_id = reader.read_u32_le()
        x = reader.read_f32_le()
        y = reader.read_f32_le()
        z = reader.read_f32_le()
        reader.skip(4)
        flags = reader.read_u32_le()
        reader.skip(1)
        reader.skip(4)
        reader.skip(4)
        reader.skip(4)
        for _slot in range(20):
            reader.skip(4 + 1)
        characters.append(CharacterSummary(guid, name, race, class_id, gender, level, zone_id, map_id, x, y, z, flags))
    return characters


def parse_char_enum(packet: WorldPacket) -> list[CharacterSummary]:
    if packet.opcode != opcodes.SMSG_CHAR_ENUM:
        raise WorldError(f"expected SMSG_CHAR_ENUM, got {packet.opcode}")
    return parse_char_enum_body(packet.body)


def select_character(characters: list[CharacterSummary], character_name: str) -> CharacterSummary:
    for character in characters:
        if character.name.lower() == character_name.lower():
            return character
    names = ", ".join(character.name for character in characters) or "<none>"
    raise WorldError(f"character {character_name!r} not found in enum: {names}")


def parse_login_verify(packet: WorldPacket) -> LoginLocation:
    if packet.opcode != opcodes.SMSG_LOGIN_VERIFY_WORLD:
        raise WorldError(f"expected SMSG_LOGIN_VERIFY_WORLD, got {packet.opcode}")
    reader = ByteReader(packet.body)
    return LoginLocation(
        map_id=reader.read_u32_le(),
        x=reader.read_f32_le(),
        y=reader.read_f32_le(),
        z=reader.read_f32_le(),
        orientation=reader.read_f32_le(),
    )


def build_guid_body(guid: int) -> bytes:
    writer = ByteWriter()
    writer.add_u64_le(guid)
    return writer.finish()


def build_ping(sequence: int) -> bytes:
    writer = ByteWriter()
    writer.add_u32_le(sequence)
    writer.add_u32_le(0)
    return writer.finish()


async def login_and_idle(tunnel, account: str, character_name: str, session_key: bytes, *, config: WowborgConfig | None = None, stop_event: asyncio.Event) -> LoginLocation:
    """Log the selected character into the world, then CMSG_PING until stopped."""

    if not character_name:
        raise WorldError("wow_session character_name was null or empty; wowborg v1 requires a seeded character")
    cfg = config or WowborgConfig()
    packet = await read_world_packet(tunnel)
    server_seed = parse_auth_challenge(packet)
    await send_world_packet(tunnel, opcodes.CMSG_AUTH_SESSION, build_auth_session(account, server_seed, session_key, cfg), encrypted=False)

    crypt = HeaderCrypt(session_key)
    parse_auth_response(await read_world_packet(tunnel, crypt, encrypted=True))
    await send_world_packet(tunnel, opcodes.CMSG_CHAR_ENUM, b"", crypt, encrypted=True)
    character = select_character(parse_char_enum(await read_world_packet(tunnel, crypt, encrypted=True)), character_name)
    await send_world_packet(tunnel, opcodes.CMSG_PLAYER_LOGIN, build_guid_body(character.guid), crypt, encrypted=True)

    location: LoginLocation | None = None
    for _ in range(cfg.login_packet_limit):
        packet = await read_world_packet(tunnel, crypt, encrypted=True)
        if packet.opcode == opcodes.SMSG_CHARACTER_LOGIN_FAILED:
            status = ByteReader(packet.body).read_u8()
            raise WorldError(f"character login failed with status {status}")
        if packet.opcode == opcodes.SMSG_LOGIN_VERIFY_WORLD:
            location = parse_login_verify(packet)
            break
    if location is None:
        raise WorldError("did not receive SMSG_LOGIN_VERIFY_WORLD after player login")

    await send_world_packet(tunnel, opcodes.MSG_MOVE_WORLDPORT_ACK, b"", crypt, encrypted=True)
    await send_world_packet(tunnel, opcodes.CMSG_SET_ACTIVE_MOVER, build_guid_body(character.guid), crypt, encrypted=True)

    ping_task = asyncio.create_task(_ping_loop(tunnel, crypt, cfg, stop_event))
    drain_task = asyncio.create_task(_drain_loop(tunnel, crypt, stop_event))
    try:
        await stop_event.wait()
    finally:
        ping_task.cancel()
        drain_task.cancel()
        await asyncio.gather(ping_task, drain_task, return_exceptions=True)
    return location


async def _ping_loop(tunnel, crypt: HeaderCrypt, cfg: WowborgConfig, stop_event: asyncio.Event) -> None:
    sequence = 1
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=cfg.ping_interval_s)
            break
        except TimeoutError:
            await send_world_packet(tunnel, opcodes.CMSG_PING, build_ping(sequence), crypt, encrypted=True)
            sequence = (sequence + 1) & 0xFFFFFFFF


async def _drain_loop(tunnel, crypt: HeaderCrypt, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        await read_world_packet(tunnel, crypt, encrypted=True)
