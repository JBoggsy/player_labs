"""Vanilla realmd authentication leg."""

from __future__ import annotations

from dataclasses import dataclass

from wowborg import opcodes
from wowborg.config import WowborgConfig
from wowborg.srp6 import compute_proof
from wowborg.wire import ByteReader, ByteWriter


WOW_SUCCESS = 0


class RealmdError(RuntimeError):
    """Raised for rejected or malformed realmd auth."""


@dataclass(frozen=True)
class RealmInfo:
    name: str
    address: str
    icon: int
    flags: int
    population: float
    character_count: int
    category: int


@dataclass(frozen=True)
class RealmChallenge:
    B: bytes
    g: bytes
    N: bytes
    salt: bytes
    version_challenge: bytes
    security_flags: int


def build_logon_challenge(username: str, cfg: WowborgConfig) -> bytes:
    user = username.upper()
    body_size = 30 + len(user)
    writer = ByteWriter()
    writer.add_u8(opcodes.CMD_AUTH_LOGON_CHALLENGE)
    writer.add_u8(opcodes.AUTH_PROTOCOL_VERSION)
    writer.add_u16_le(body_size)
    writer.add_fixed_ascii("WoW", 4)
    writer.add_u8(1)
    writer.add_u8(12)
    writer.add_u8(1)
    writer.add_u16_le(opcodes.CLIENT_BUILD)
    writer.add_reversed_fourcc(cfg.platform)
    writer.add_reversed_fourcc(cfg.os_name)
    writer.add_reversed_fourcc(cfg.locale)
    writer.add_u32_le(0)
    writer.add_u32_le(0)
    writer.add_u8(len(user))
    writer.add_ascii(user)
    return writer.finish()


def build_realm_list_request() -> bytes:
    writer = ByteWriter()
    writer.add_u8(opcodes.CMD_REALM_LIST)
    writer.add_u32_le(0)
    return writer.finish()


async def read_challenge(tunnel) -> RealmChallenge:
    header = ByteReader(await tunnel.recv_exact(3))
    command = header.read_u8()
    protocol_error = header.read_u8()
    auth_result = header.read_u8()
    if command != opcodes.CMD_AUTH_LOGON_CHALLENGE:
        raise RealmdError(f"expected CMD_AUTH_LOGON_CHALLENGE, got {command}")
    if protocol_error != 0:
        raise RealmdError(f"realmd returned protocol error {protocol_error}")
    if auth_result != WOW_SUCCESS:
        raise RealmdError(f"realmd rejected challenge with status {auth_result}")
    B = await tunnel.recv_exact(opcodes.SRP_NUMBER)
    g_len = (await tunnel.recv_exact(1))[0]
    g = await tunnel.recv_exact(g_len)
    N_len = (await tunnel.recv_exact(1))[0]
    N = await tunnel.recv_exact(N_len)
    salt = await tunnel.recv_exact(opcodes.SRP_NUMBER)
    version_challenge = await tunnel.recv_exact(16)
    security_flags = (await tunnel.recv_exact(1))[0]
    return RealmChallenge(B=B, g=g, N=N, salt=salt, version_challenge=version_challenge, security_flags=security_flags)


def build_logon_proof(username: str, password: str, challenge: RealmChallenge, cfg: WowborgConfig, *, a: bytes | None = None) -> tuple[bytes, bytes]:
    proof = compute_proof(
        username,
        password,
        B=challenge.B,
        g=challenge.g,
        N=challenge.N,
        salt=challenge.salt,
        a=a,
        platform=cfg.platform,
        os_name=cfg.os_name,
    )
    writer = ByteWriter()
    writer.add_u8(opcodes.CMD_AUTH_LOGON_PROOF)
    writer.add_bytes(proof.A)
    writer.add_bytes(proof.M1)
    writer.add_bytes(proof.crc)
    writer.add_u8(0)
    writer.add_u8(0)
    return writer.finish(), proof.K


async def read_proof_response(tunnel) -> bytes:
    header = await tunnel.recv_exact(2)
    command = header[0]
    auth_result = header[1]
    if command != opcodes.CMD_AUTH_LOGON_PROOF:
        raise RealmdError(f"expected CMD_AUTH_LOGON_PROOF, got {command}")
    if auth_result != WOW_SUCCESS:
        raise RealmdError(f"realmd rejected proof with status {auth_result}")
    M2 = await tunnel.recv_exact(opcodes.SRP_DIGEST)
    await tunnel.recv_exact(4)
    return M2


async def read_realm_list(tunnel) -> list[RealmInfo]:
    header = ByteReader(await tunnel.recv_exact(3))
    command = header.read_u8()
    size = header.read_u16_le()
    if command != opcodes.CMD_REALM_LIST:
        raise RealmdError(f"expected CMD_REALM_LIST, got {command}")
    body = ByteReader(await tunnel.recv_exact(size))
    body.read_u32_le()
    realm_count = body.read_u8()
    realms: list[RealmInfo] = []
    for _ in range(realm_count):
        icon = body.read_u32_le()
        flags = body.read_u8()
        name = body.read_cstring()
        address = body.read_cstring()
        population = body.read_f32_le()
        character_count = body.read_u8()
        category = body.read_u8()
        body.skip(1)
        realms.append(RealmInfo(name, address, icon, flags, population, character_count, category))
    body.skip(2)
    return realms


async def authenticate(tunnel, username: str, password: str, *, config: WowborgConfig | None = None, a: bytes | None = None) -> bytes:
    """Authenticate with realmd, request realm list, and return session key ``K``."""

    cfg = config or WowborgConfig()
    await tunnel.send(build_logon_challenge(username, cfg))
    challenge = await read_challenge(tunnel)
    proof_packet, session_key = build_logon_proof(username, password, challenge, cfg, a=a)
    await tunnel.send(proof_packet)
    await read_proof_response(tunnel)
    await tunnel.send(build_realm_list_request())
    await read_realm_list(tunnel)
    return session_key
