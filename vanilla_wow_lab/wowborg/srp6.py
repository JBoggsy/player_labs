"""Vanilla WoW SRP6 auth proof, ported from ``game_client/srp.nim``."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os

from wowborg import opcodes


WIN_X86_BUILD_5875_HASH = bytes.fromhex("95EDB27C7823B363CBDDAB56A392E7CB73FCCA20")
OSX_BUILD_5875_HASH = bytes.fromhex("8D173CC381961EEBABF336F5E6675B101BB513E5")


@dataclass(frozen=True)
class SrpProof:
    """Fields sent in ``CMD_AUTH_LOGON_PROOF`` and reused for world auth."""

    A: bytes
    M1: bytes
    crc: bytes
    K: bytes


def _sha1(data: bytes) -> bytes:
    return hashlib.sha1(data).digest()


def _sha1_concat(*parts: bytes) -> bytes:
    h = hashlib.sha1()
    for part in parts:
        h.update(part)
    return h.digest()


def _le_to_int(value: bytes) -> int:
    return int.from_bytes(value, "little")


def _int_to_le(value: int, min_size: int = 0) -> bytes:
    if value == 0:
        raw = b""
    else:
        raw = value.to_bytes((value.bit_length() + 7) // 8, "little")
    if len(raw) < min_size:
        raw += b"\x00" * (min_size - len(raw))
    return raw


def _hash_bigint(value: int) -> bytes:
    return _sha1(_int_to_le(value))


def _hash_session_key(secret: int) -> bytes:
    secret_bytes = _int_to_le(secret, opcodes.SRP_NUMBER)
    even = bytes(secret_bytes[i * 2] for i in range(opcodes.SRP_NUMBER // 2))
    odd = bytes(secret_bytes[i * 2 + 1] for i in range(opcodes.SRP_NUMBER // 2))
    even_hash = _sha1(even)
    odd_hash = _sha1(odd)
    interleaved = bytearray(opcodes.SRP_SESSION)
    for i in range(opcodes.SRP_DIGEST):
        interleaved[i * 2] = even_hash[i]
        interleaved[i * 2 + 1] = odd_hash[i]
    return _int_to_le(_le_to_int(bytes(interleaved)))


def _integrity_hash(platform: str = "x86", os_name: str = "Win") -> bytes:
    if os_name == "Win" and platform == "x86":
        return WIN_X86_BUILD_5875_HASH
    if os_name == "OSX" and platform in {"x86", "PPC"}:
        return OSX_BUILD_5875_HASH
    return b"\x00" * opcodes.SRP_DIGEST


def crc_hash(A_32le: bytes, *, platform: str = "x86", os_name: str = "Win") -> bytes:
    """Return the VMaNGOS client version proof for the 5875 platform."""

    return _sha1_concat(A_32le, _integrity_hash(platform=platform, os_name=os_name))


def compute_x(username: str, password: str, salt: bytes) -> int:
    """Compute the WoW SRP password exponent ``x``."""

    user = username.upper()
    passwd = password.upper()
    return _le_to_int(_sha1_concat(_int_to_le(_le_to_int(salt)), _sha1(f"{user}:{passwd}".encode("ascii"))))


def compute_verifier(username: str, password: str, *, g: bytes, N: bytes, salt: bytes) -> bytes:
    """Compute ``v = g^x mod N`` as little-endian bytes."""

    verifier = pow(_le_to_int(g), compute_x(username, password, salt), _le_to_int(N))
    return _int_to_le(verifier, opcodes.SRP_NUMBER)


def compute_proof(
    username: str,
    password: str,
    *,
    B: bytes,
    g: bytes,
    N: bytes,
    salt: bytes,
    a: bytes | None = None,
    platform: str = "x86",
    os_name: str = "Win",
) -> SrpProof:
    """Compute the client SRP proof.

    This intentionally follows the Nim implementation's little-endian BigInt
    conversions, including minimal-byte SHA inputs for integer hashes and the
    session-key big-int round trip that can strip trailing high zero bytes.
    """

    private = bytearray(a if a is not None else os.urandom(opcodes.SRP_PRIVATE))
    if len(private) != opcodes.SRP_PRIVATE:
        raise ValueError(f"SRP private ephemeral must be {opcodes.SRP_PRIVATE} bytes")
    private[0] |= 1

    user = username.upper()
    passwd = password.upper()
    prime = _le_to_int(N)
    generator = _le_to_int(g)
    host_public = _le_to_int(B)
    salt_int = _le_to_int(salt)
    private_int = _le_to_int(private)

    public = pow(generator, private_int, prime)
    x = _le_to_int(_sha1_concat(_int_to_le(salt_int), _sha1(f"{user}:{passwd}".encode("ascii"))))
    verifier = pow(generator, x, prime)
    scramble = _le_to_int(_sha1_concat(_int_to_le(public), _int_to_le(host_public)))
    base = (host_public - opcodes.SRP_MULTIPLIER * verifier) % prime
    secret = pow(base, private_int + scramble * x, prime)
    session_key = _hash_session_key(secret)

    prime_hash = bytearray(_hash_bigint(prime))
    generator_hash = _hash_bigint(generator)
    for i in range(opcodes.SRP_DIGEST):
        prime_hash[i] ^= generator_hash[i]

    A = _int_to_le(public, opcodes.SRP_NUMBER)
    M1 = _sha1_concat(
        _int_to_le(_le_to_int(bytes(prime_hash))),
        _sha1(user.encode("ascii")),
        _int_to_le(salt_int),
        _int_to_le(public),
        _int_to_le(host_public),
        session_key,
    )
    return SrpProof(A=A, M1=M1, crc=crc_hash(A, platform=platform, os_name=os_name), K=session_key)
