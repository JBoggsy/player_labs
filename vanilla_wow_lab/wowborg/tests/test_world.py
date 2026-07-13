import asyncio

import pytest

from wowborg import opcodes
from wowborg.config import WowborgConfig
from wowborg.crypt import HeaderCrypt
from wowborg.wire import ByteReader, ByteWriter
from wowborg.world import build_auth_digest, build_auth_session, login_and_idle, parse_char_enum_body

from conftest import ScriptedTunnel


SESSION_KEY = bytes(range(1, 41))


def server_packet(opcode: int, body: bytes, crypt: HeaderCrypt | None = None) -> bytes:
    header = ByteWriter()
    header.add_u16_be(2 + len(body))
    header.add_u16_le(opcode)
    raw = bytearray(header.finish())
    if crypt is not None:
        crypt.encrypt_send(raw)
    return bytes(raw) + body


def char_enum_body() -> bytes:
    writer = ByteWriter()
    writer.add_u8(2)
    write_character(writer, 0x0102030405060708, "Other")
    write_character(writer, 0x8877665544332211, "Nightsun")
    return writer.finish()


def write_character(writer: ByteWriter, guid: int, name: str) -> None:
    writer.add_u64_le(guid)
    writer.add_cstring(name)
    writer.add_u8(2)
    writer.add_u8(8)
    writer.add_u8(1)
    writer.add_u8(3)
    writer.add_u8(4)
    writer.add_u8(5)
    writer.add_u8(6)
    writer.add_u8(7)
    writer.add_u8(12)
    writer.add_u32_le(14)
    writer.add_u32_le(1)
    writer.add_f32_le(10.5)
    writer.add_f32_le(20.25)
    writer.add_f32_le(30.125)
    writer.add_u32_le(0)
    writer.add_u32_le(0xAABBCCDD)
    writer.add_u8(0)
    writer.add_u32_le(0)
    writer.add_u32_le(0)
    writer.add_u32_le(0)
    for _ in range(20):
        writer.add_u32_le(0)
        writer.add_u8(0)


def decrypt_sent_world_packets(sent: list[bytes]) -> list[tuple[int, bytes]]:
    packets: list[tuple[int, bytes]] = []
    first = sent[0]
    size = int.from_bytes(first[:2], "big")
    packets.append((int.from_bytes(first[2:6], "little"), first[6 : 2 + size]))
    crypt = HeaderCrypt(SESSION_KEY)
    for raw_packet in sent[1:]:
        header = bytearray(raw_packet[:6])
        crypt.decrypt_recv(header)
        reader = ByteReader(bytes(header))
        size = reader.read_u16_be()
        opcode = reader.read_u32_le()
        packets.append((opcode, raw_packet[6 : 2 + size]))
    return packets


def test_auth_session_digest_vector() -> None:
    digest = build_auth_digest("COWORLD", 0x4B494E47, 0x11223344, SESSION_KEY)
    assert digest.hex() == "da740cdd65e948ed86a44a7eed00755fe9bd74c7"
    assert build_auth_session("coworld", 0x11223344, SESSION_KEY, WowborgConfig()).hex() == (
        "f316000000000000434f574f524c4400474e494bda740cdd65e948ed86a44a7eed00755fe9bd74c7"
    )


def test_char_enum_parser_selects_full_record_layout() -> None:
    characters = parse_char_enum_body(char_enum_body())
    assert [(c.guid, c.name, c.level, c.zone_id, c.map_id) for c in characters] == [
        (0x0102030405060708, "Other", 12, 14, 1),
        (0x8877665544332211, "Nightsun", 12, 14, 1),
    ]


@pytest.mark.asyncio
async def test_world_login_through_verify_and_ping() -> None:
    cfg = WowborgConfig(ping_interval_s=0.01)
    server_send = HeaderCrypt(SESSION_KEY)
    login_verify_body = ByteWriter()
    login_verify_body.add_u32_le(1)
    login_verify_body.add_f32_le(1.0)
    login_verify_body.add_f32_le(2.0)
    login_verify_body.add_f32_le(3.0)
    login_verify_body.add_f32_le(4.0)
    stream = b"".join(
        [
            server_packet(opcodes.SMSG_AUTH_CHALLENGE, (0x11223344).to_bytes(4, "little")),
            server_packet(opcodes.SMSG_AUTH_RESPONSE, b"\x0c", server_send),
            server_packet(opcodes.SMSG_CHAR_ENUM, char_enum_body(), server_send),
            server_packet(opcodes.SMSG_LOGIN_VERIFY_WORLD, login_verify_body.finish(), server_send),
        ]
    )
    tunnel = ScriptedTunnel([stream])
    stop_event = asyncio.Event()
    task = asyncio.create_task(
        login_and_idle(tunnel, "coworld", "nightsun", SESSION_KEY, config=cfg, stop_event=stop_event)
    )
    await asyncio.sleep(0.04)
    stop_event.set()
    location = await asyncio.wait_for(task, timeout=1)

    assert (location.map_id, location.x, location.y, location.z, location.orientation) == (1, 1.0, 2.0, 3.0, 4.0)
    packets = decrypt_sent_world_packets(tunnel.sent)
    assert packets[0] == (opcodes.CMSG_AUTH_SESSION, build_auth_session("coworld", 0x11223344, SESSION_KEY, cfg))
    assert packets[1] == (opcodes.CMSG_CHAR_ENUM, b"")
    assert packets[2] == (opcodes.CMSG_PLAYER_LOGIN, (0x8877665544332211).to_bytes(8, "little"))
    assert packets[3] == (opcodes.MSG_MOVE_WORLDPORT_ACK, b"")
    assert packets[4] == (opcodes.CMSG_SET_ACTIVE_MOVER, (0x8877665544332211).to_bytes(8, "little"))
    assert packets[5] == (opcodes.CMSG_PING, b"\x01\x00\x00\x00\x00\x00\x00\x00")
