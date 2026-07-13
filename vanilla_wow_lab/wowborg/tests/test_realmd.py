import struct

import pytest

from wowborg.config import WowborgConfig
from wowborg.realmd import authenticate, build_logon_challenge, build_realm_list_request
from wowborg.wire import ByteWriter

from conftest import ScriptedTunnel
N = int(
    "e487eb3bce8c142837159563d838a86fd17419c6cdc7d9d636b5b7d7550a54dd",
    16,
).to_bytes(32, "little")
G = b"\x07"
SALT = bytes.fromhex("00112233445566778899aabbccddeeff102132435465768798a9bacbdcedfe0f")
A_PRIVATE = bytes.fromhex("0102030405060708090a0b0c0d0e0f10111213")
B = bytes.fromhex("9a48b0bf4467e27726ac9d76d620cba0e92356fb425c693f3e58644da785390f")


def challenge_bytes() -> bytes:
    return b"\x00\x00\x00" + B + bytes([len(G)]) + G + bytes([len(N)]) + N + SALT + (b"\x00" * 16) + b"\x00"


def proof_response_bytes() -> bytes:
    return b"\x01\x00" + (b"\x11" * 20) + (b"\x00" * 4)


def realm_list_bytes() -> bytes:
    body = ByteWriter()
    body.add_u32_le(0)
    body.add_u8(1)
    body.add_u32_le(1)
    body.add_u8(0)
    body.add_cstring("Coworld Vanilla")
    body.add_cstring("127.0.0.1:8085")
    body.add_bytes(struct.pack("<f", 0.5))
    body.add_u8(1)
    body.add_u8(0)
    body.add_u8(0)
    body.add_u16_le(0)
    payload = body.finish()
    header = ByteWriter()
    header.add_u8(0x10)
    header.add_u16_le(len(payload))
    return header.finish() + payload


@pytest.mark.asyncio
async def test_authenticate_scripted_realmd() -> None:
    cfg = WowborgConfig()
    tunnel = ScriptedTunnel([challenge_bytes(), proof_response_bytes(), realm_list_bytes()])
    session_key = await authenticate(tunnel, "coworld", "secret", config=cfg, a=A_PRIVATE)

    assert tunnel.sent[0] == build_logon_challenge("coworld", cfg)
    assert tunnel.sent[0].hex() == "00082500576f5700010c01f316363878006e69570053556e65000000000000000007434f574f524c44"
    assert tunnel.sent[1].hex() == (
        "01"
        "dc269f97127055f57db20231a3cd206b41dfed8ed0978492d1377c19016e6448"
        "320feca9fef01dba6427e1e786b15eea60556086"
        "5c4920425702f62f49c165032e3bc31d7cb00cf1"
        "0000"
    )
    assert tunnel.sent[2] == build_realm_list_request()
    assert session_key.hex() == "512b847161cbf04c92195f23f8d7ab23eb864c39524f61728c5b6033a87b073d2fd8788ea8388d39"
