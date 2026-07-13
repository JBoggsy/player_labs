"""Byte-level Vanilla WoW wire primitives and world packet framing."""

from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Protocol


class WireError(ValueError):
    """Raised when packet bytes are malformed or incomplete."""


class HeaderCryptLike(Protocol):
    def encrypt_send(self, data: bytearray) -> None: ...

    def decrypt_recv(self, data: bytearray) -> None: ...


@dataclass
class ByteReader:
    """A small bounds-checking reader over packet bytes."""

    data: bytes
    pos: int = 0

    @property
    def remaining(self) -> int:
        return len(self.data) - self.pos

    def require(self, count: int) -> None:
        if self.remaining < count:
            raise WireError(f"packet ended early: needed {count}, had {self.remaining}")

    def read_u8(self) -> int:
        self.require(1)
        value = self.data[self.pos]
        self.pos += 1
        return value

    def read_u16_le(self) -> int:
        self.require(2)
        value = int.from_bytes(self.data[self.pos : self.pos + 2], "little")
        self.pos += 2
        return value

    def read_u16_be(self) -> int:
        self.require(2)
        value = int.from_bytes(self.data[self.pos : self.pos + 2], "big")
        self.pos += 2
        return value

    def read_u32_le(self) -> int:
        self.require(4)
        value = int.from_bytes(self.data[self.pos : self.pos + 4], "little")
        self.pos += 4
        return value

    def read_u32_be(self) -> int:
        self.require(4)
        value = int.from_bytes(self.data[self.pos : self.pos + 4], "big")
        self.pos += 4
        return value

    def read_u64_le(self) -> int:
        self.require(8)
        value = int.from_bytes(self.data[self.pos : self.pos + 8], "little")
        self.pos += 8
        return value

    def read_f32_le(self) -> float:
        self.require(4)
        value = struct.unpack_from("<f", self.data, self.pos)[0]
        self.pos += 4
        return value

    def read_cstring(self) -> str:
        end = self.data.find(b"\x00", self.pos)
        if end < 0:
            raise WireError("packet ended before C string terminator")
        value = self.data[self.pos : end].decode("ascii")
        self.pos = end + 1
        return value

    def read_bytes(self, count: int) -> bytes:
        self.require(count)
        value = self.data[self.pos : self.pos + count]
        self.pos += count
        return value

    def skip(self, count: int) -> None:
        self.require(count)
        self.pos += count


class ByteWriter:
    """A small writer matching the Nim ``ByteWriter`` packet helpers."""

    def __init__(self) -> None:
        self.bytes = bytearray()

    def add_u8(self, value: int) -> None:
        self.bytes.append(value & 0xFF)

    def add_u16_le(self, value: int) -> None:
        self.bytes.extend((value & 0xFFFF).to_bytes(2, "little"))

    def add_u16_be(self, value: int) -> None:
        self.bytes.extend((value & 0xFFFF).to_bytes(2, "big"))

    def add_u32_le(self, value: int) -> None:
        self.bytes.extend((value & 0xFFFFFFFF).to_bytes(4, "little"))

    def add_u32_be(self, value: int) -> None:
        self.bytes.extend((value & 0xFFFFFFFF).to_bytes(4, "big"))

    def add_u64_le(self, value: int) -> None:
        self.bytes.extend((value & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little"))

    def add_f32_le(self, value: float) -> None:
        self.bytes.extend(struct.pack("<f", value))

    def add_bytes(self, value: bytes | bytearray) -> None:
        self.bytes.extend(value)

    def add_ascii(self, value: str) -> None:
        self.bytes.extend(value.encode("ascii"))

    def add_cstring(self, value: str) -> None:
        self.add_ascii(value)
        self.add_u8(0)

    def add_fixed_ascii(self, value: str, width: int) -> None:
        encoded = value.encode("ascii")
        self.bytes.extend(encoded[:width])
        self.bytes.extend(b"\x00" * max(width - len(encoded), 0))

    def add_reversed_fourcc(self, value: str) -> None:
        encoded = value.encode("ascii")
        self.bytes.extend(encoded[::-1][:4])
        self.bytes.extend(b"\x00" * max(4 - len(encoded), 0))

    def finish(self) -> bytes:
        return bytes(self.bytes)


@dataclass(frozen=True)
class WorldPacket:
    opcode: int
    body: bytes


def cstring(value: str) -> bytes:
    writer = ByteWriter()
    writer.add_cstring(value)
    return writer.finish()


def build_client_packet(
    opcode: int,
    body: bytes,
    crypt: HeaderCryptLike | None = None,
    *,
    encrypted: bool = False,
) -> bytes:
    """Build a client world packet.

    Client headers are ``u16 BE`` size counting the 4-byte opcode plus body,
    followed by a ``u32 LE`` opcode. Only the header is encrypted.
    """

    header_size = 4 + len(body)
    if header_size > 0xFFFF:
        raise WireError(f"world packet too large: {header_size}")
    header = ByteWriter()
    header.add_u16_be(header_size)
    header.add_u32_le(opcode)
    header_bytes = bytearray(header.finish())
    if encrypted:
        if crypt is None:
            raise WireError("encrypted packet requested without header crypt")
        crypt.encrypt_send(header_bytes)
    return bytes(header_bytes) + body


def parse_server_header(header: bytes, crypt: HeaderCryptLike | None = None, *, encrypted: bool = False) -> tuple[int, int]:
    """Parse a 4-byte server header into ``(opcode, body_len)``."""

    if len(header) != 4:
        raise WireError(f"server header must be 4 bytes, got {len(header)}")
    raw = bytearray(header)
    if encrypted:
        if crypt is None:
            raise WireError("encrypted header requested without header crypt")
        crypt.decrypt_recv(raw)
    reader = ByteReader(bytes(raw))
    size = reader.read_u16_be()
    opcode = reader.read_u16_le()
    if size < 2:
        raise WireError(f"server packet size was invalid: {size}")
    return opcode, size - 2


def read_server_packet_from_bytes(
    data: bytes,
    crypt: HeaderCryptLike | None = None,
    *,
    encrypted: bool = False,
) -> tuple[WorldPacket, bytes]:
    """Parse one complete server packet from ``data`` and return leftovers."""

    if len(data) < 4:
        raise WireError("not enough bytes for server header")
    opcode, body_len = parse_server_header(data[:4], crypt, encrypted=encrypted)
    total = 4 + body_len
    if len(data) < total:
        raise WireError("not enough bytes for server body")
    return WorldPacket(opcode, data[4:total]), data[total:]
