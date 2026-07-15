#!/usr/bin/env python3
"""Decode Vanilla WoW CWREPLAY artifacts: summary, per-member stats, packet JSONL.

Standalone (stdlib only) so it runs in any env — the game package's own decoder
(`vanilla_wow_coworld.replay_format`) isn't installed locally and hard-fails on
game-version mismatch, which a report tool must not. Format per the game repo's
`docs/protocol/cwreplay.md` + `replay_format.py`/`party_wire.py` (verified 2026-07-15):

  CWREPLAY: magic "CWREPLAY" · u16 version=1 · str game · str game_version ·
            u64 start_ms · u32 header_len · JSON header · records until EOF
  record:   u8 type (0x01 godview JSONL | 0x02 party wire) · u64 raw · u64 comp ·
            32B sha256(raw) · zlib payload
  CWPARTY4: magic · u16 version=1 · u32 map_id · u32 instance_id · u16 n_segments;
            per segment: u64 guid · str name · u64 start_ms · u32 n_packets ·
            u64 n_bytes · 32B sha256 · PKT bytes
  PKT 2.1:  magic "PKT" · u16 0x0201 · u16 build(5875) · 40B reserved; per packet:
            u8 dir (0x00 client/0xFF server) · u32 unix_s · u32 server_ms ·
            u32 size · opcode (u32 client / u16 server) · body

Usage:
  cwreplay.py summary    <replay> [--json]
  cwreplay.py packets    <replay> [--member NAME] [--opcode N ...] [--say-only] [--limit N]
  cwreplay.py trajectory <replay> [--member NAME] [--limit N]
  cwreplay.py members    <replay>
  cwreplay.py header     <replay>

`packets` emits JSONL rows: {member, from_client, unix_s, server_ms, opcode,
opcode_name?, size, text?} — chat text decoded for SMSG_MESSAGECHAT/CMSG_MESSAGECHAT.
`trajectory` emits the member's OWN position stream from its outbound MSG_MOVE_*
MovementInfo bodies (client-authoritative movement ⇒ plaintext x/y/z/o in every
movement packet — no client-state reduction needed for the self-trajectory).

Knowability boundary (be honest about it): this tool decodes packet framing and
SELF-DESCRIBING bodies (chat, login verify, own movement, XP events). Facts that
require accumulating client state across packets — other units' positions/health,
update-field values, aura/death transitions — need the stateful reducer; the game
repo's `player/tools/inspect_party_wire_replay.nim` (replay → PlayerStateMirror) is
that path, deliberately deferred (see docs/recon/replay-tooling-2026-07-15.md).
All integers little-endian; strings u16-length-prefixed UTF-8.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

GODVIEW_RECORD = 0x01
PARTY_WIRE_RECORD = 0x02

# The opcodes our T0/T1 reporting cares about, named. Grown incrementally; unknown
# opcodes still export numerically. Values from wowborg/opcodes.py + the protocol doc.
OPCODE_NAMES_SERVER = {
    62: "SMSG_NEW_WORLD",
    150: "SMSG_MESSAGECHAT",
    169: "SMSG_UPDATE_OBJECT",
    170: "SMSG_DESTROY_OBJECT",
    199: "MSG_MOVE_TELEPORT_ACK",
    221: "SMSG_MONSTER_MOVE",
    226: "SMSG_FORCE_RUN_SPEED_CHANGE",
    304: "SMSG_CAST_RESULT",
    305: "SMSG_SPELL_START",
    306: "SMSG_SPELL_GO",
    330: "SMSG_ATTACKERSTATEUPDATE",
    464: "SMSG_LOG_XPGAIN",
    468: "SMSG_LEVELUP_INFO",
    492: "SMSG_AUTH_CHALLENGE",
    494: "SMSG_AUTH_RESPONSE",
    502: "SMSG_COMPRESSED_UPDATE_OBJECT",
    508: "SMSG_ENVIRONMENTALDAMAGELOG",
    566: "SMSG_LOGIN_VERIFY_WORLD",
    763: "SMSG_COMPRESSED_MOVES",
}
OPCODE_NAMES_CLIENT = {
    55: "CMSG_CHAR_ENUM",
    61: "CMSG_PLAYER_LOGIN",
    149: "CMSG_MESSAGECHAT",
    181: "MSG_MOVE_START_FORWARD",
    183: "MSG_MOVE_STOP",
    218: "MSG_MOVE_SET_FACING",
    220: "MSG_MOVE_WORLDPORT_ACK",
    238: "MSG_MOVE_HEARTBEAT",
    476: "CMSG_PING",
    493: "CMSG_AUTH_SESSION",
    618: "CMSG_SET_ACTIVE_MOVER",
}
MOVE_OPCODES_CLIENT = set(range(181, 220)) | {238, 201, 202, 203}
CHAT_OPCODES = {149, 150}


class ReplayError(ValueError):
    pass


class _Reader:
    def __init__(self, data: bytes, source: str) -> None:
        self.data = data
        self.offset = 0
        self.source = source

    def read(self, count: int, what: str) -> bytes:
        end = self.offset + count
        if end > len(self.data):
            raise ReplayError(f"{self.source}: truncated reading {what}")
        chunk = self.data[self.offset : end]
        self.offset = end
        return chunk

    def u8(self, what: str) -> int:
        return self.read(1, what)[0]

    def u16(self, what: str) -> int:
        return struct.unpack("<H", self.read(2, what))[0]

    def u32(self, what: str) -> int:
        return struct.unpack("<I", self.read(4, what))[0]

    def u64(self, what: str) -> int:
        return struct.unpack("<Q", self.read(8, what))[0]

    def string(self, what: str) -> str:
        return self.read(self.u16(f"{what} length"), what).decode("utf-8")


@dataclass
class Packet:
    from_client: bool
    unix_seconds: int
    server_ms: int
    opcode: int
    body: bytes

    @property
    def opcode_name(self) -> str | None:
        table = OPCODE_NAMES_CLIENT if self.from_client else OPCODE_NAMES_SERVER
        return table.get(self.opcode)


@dataclass
class MemberStream:
    guid: int
    name: str
    start_ms: int
    packets: list[Packet] = field(default_factory=list)


@dataclass
class Replay:
    game: str
    game_version: str
    started_ms: int
    header: dict
    members: list[MemberStream]
    godview_jsonl: bytes | None


def _decode_record_payload(reader: _Reader, label: str) -> bytes:
    raw_size = reader.u64(f"{label} raw size")
    comp_size = reader.u64(f"{label} compressed size")
    digest = reader.read(32, f"{label} sha256")
    payload = zlib.decompress(reader.read(comp_size, f"{label} payload"))
    if len(payload) != raw_size:
        raise ReplayError(f"{label}: size mismatch ({len(payload)} != {raw_size})")
    if hashlib.sha256(payload).digest() != digest:
        raise ReplayError(f"{label}: sha256 mismatch")
    return payload


def _decode_pkt(payload: bytes, source: str) -> list[Packet]:
    reader = _Reader(payload, source)
    if reader.read(3, "PKT magic") != b"PKT":
        raise ReplayError(f"{source}: bad PKT magic")
    if reader.u16("PKT version") != 0x0201:
        raise ReplayError(f"{source}: unsupported PKT version")
    reader.u16("client build")
    reader.read(40, "reserved")
    packets: list[Packet] = []
    while reader.offset < len(payload):
        direction = reader.u8("direction")
        if direction not in (0x00, 0xFF):
            raise ReplayError(f"{source}: bad direction 0x{direction:02x}")
        unix_seconds = reader.u32("unix time")
        server_ms = reader.u32("server ms")
        size = reader.u32("size")
        from_client = direction == 0x00
        opcode = reader.u32("opcode") if from_client else reader.u16("opcode")
        body = reader.read(size - (4 if from_client else 2), "body")
        packets.append(Packet(from_client, unix_seconds, server_ms, opcode, body))
    return packets


def _decode_party_wire(payload: bytes) -> list[MemberStream]:
    reader = _Reader(payload, "CWPARTY4")
    if reader.read(8, "magic") != b"CWPARTY4":
        raise ReplayError("CWPARTY4 magic does not match")
    if reader.u16("version") != 1:
        raise ReplayError("unsupported CWPARTY4 version")
    reader.u32("map id")
    reader.u32("instance id")
    members: list[MemberStream] = []
    for _ in range(reader.u16("segment count")):
        guid = reader.u64("guid")
        name = reader.string("name")
        start_ms = reader.u64("start ms")
        reader.u32("packet count")
        byte_count = reader.u64("byte count")
        reader.read(32, "segment sha256")
        pkt = reader.read(byte_count, "PKT bytes")
        members.append(MemberStream(guid, name, start_ms, _decode_pkt(pkt, f"member {name}")))
    return members


def decode_replay(path: Path) -> Replay:
    data = path.read_bytes()
    reader = _Reader(data, str(path))
    if reader.read(8, "magic") != b"CWREPLAY":
        raise ReplayError(f"{path}: not a CWREPLAY file")
    version = reader.u16("format version")
    if version != 1:
        raise ReplayError(f"{path}: unsupported format version {version}")
    game = reader.string("game")
    game_version = reader.string("game version")
    started_ms = reader.u64("start ms")
    header = json.loads(reader.read(reader.u32("header length"), "header"))
    godview: bytes | None = None
    party_wire: bytes | None = None
    while reader.offset < len(data):
        record_type = reader.u8("record type")
        if record_type == GODVIEW_RECORD:
            godview = _decode_record_payload(reader, "godview")
        elif record_type == PARTY_WIRE_RECORD:
            party_wire = _decode_record_payload(reader, "party wire")
        else:
            raise ReplayError(f"{path}: unknown record type 0x{record_type:02x}")
    members = _decode_party_wire(party_wire) if party_wire is not None else []
    return Replay(game, game_version, started_ms, header, members, godview)


def _movement_info(packet: Packet) -> dict | None:
    """Decode the MovementInfo body of an outbound MSG_MOVE_* packet.

    Client layout (game repo `buildMovement`, movement.nim:1057-1103):
    u32 flags · u32 time_ms · f32 x · f32 y · f32 z · f32 o · [conditional blocks].
    We read only the unconditional prefix — position truth needs nothing more.
    """
    if not packet.from_client or packet.opcode not in MOVE_OPCODES_CLIENT:
        return None
    body = packet.body
    if len(body) < 24:
        return None
    flags, time_ms = struct.unpack_from("<II", body, 0)
    x, y, z, o = struct.unpack_from("<ffff", body, 8)
    return {
        "move_flags": flags,
        "move_time_ms": time_ms,
        "x": round(x, 2),
        "y": round(y, 2),
        "z": round(z, 2),
        "o": round(o, 3),
    }


def cmd_trajectory(replay: Replay, args: argparse.Namespace) -> None:
    """Emit each member's own position stream (outbound MovementInfo prefixes)."""
    emitted = 0
    for member in replay.members:
        if args.member and member.name.lower() != args.member.lower():
            continue
        previous: tuple[float, float] | None = None
        travelled = 0.0
        for packet in member.packets:
            info = _movement_info(packet)
            if info is None:
                continue
            if previous is not None:
                travelled += (
                    (info["x"] - previous[0]) ** 2 + (info["y"] - previous[1]) ** 2
                ) ** 0.5
            previous = (info["x"], info["y"])
            row = {
                "member": member.name,
                "server_ms": packet.server_ms,
                "opcode": packet.opcode,
                **({"opcode_name": packet.opcode_name} if packet.opcode_name else {}),
                **info,
                "travelled_yd": round(travelled, 1),
            }
            print(json.dumps(row, separators=(",", ":")))
            emitted += 1
            if args.limit and emitted >= args.limit:
                return


def _chat_text(packet: Packet) -> str | None:
    """Best-effort chat text extraction (SMSG_MESSAGECHAT 150 / CMSG_MESSAGECHAT 149)."""
    body = packet.body
    try:
        if packet.from_client:
            # CMSG: u32 type, u32 language, [target for whisper/channel], cstring text
            text = body[8:].split(b"\x00", 1)[0]
            return text.decode("utf-8", "replace") or None
        # SMSG: u8 type, u32 language, sender fields vary; text is u32-length-prefixed
        # near the end: scan for a plausible length-prefixed UTF-8 run instead of fully
        # modeling every chat-type layout (report tool: lenient beats exact).
        for start in range(5, min(len(body), 64)):
            (length,) = struct.unpack_from("<I", body, start)
            if 0 < length <= len(body) - start - 4 - 1:
                candidate = body[start + 4 : start + 4 + length]
                if candidate.endswith(b"\x00"):
                    candidate = candidate[:-1]
                try:
                    decoded = candidate.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if decoded and all(ch.isprintable() or ch.isspace() for ch in decoded):
                    return decoded
        return None
    except Exception:  # noqa: BLE001 — lenient by design
        return None


def cmd_summary(replay: Replay, *, as_json: bool) -> None:
    per_member = []
    for member in replay.members:
        client = sum(1 for p in member.packets if p.from_client)
        server = len(member.packets) - client
        moves = sum(
            1 for p in member.packets if p.from_client and p.opcode in MOVE_OPCODES_CLIENT
        )
        says = sum(1 for p in member.packets if p.opcode in CHAT_OPCODES)
        logged_in = any(
            not p.from_client and p.opcode == 566 for p in member.packets
        )
        duration_s = 0.0
        if member.packets:
            duration_s = round(
                (member.packets[-1].server_ms - member.packets[0].server_ms) / 1000.0, 1
            )
        per_member.append(
            {
                "name": member.name,
                "packets_from_client": client,
                "packets_from_server": server,
                "movement_packets": moves,
                "chat_packets": says,
                "login_verified": logged_in,
                "duration_s": duration_s,
            }
        )
    summary = {
        "game": replay.game,
        "game_version": replay.game_version,
        "protocol": replay.header.get("protocol"),
        "scope": replay.header.get("scope"),
        "started_ms": replay.started_ms,
        "members": per_member,
        "godview_frames": (
            len(replay.godview_jsonl.splitlines()) if replay.godview_jsonl else 0
        ),
        "lifecycle_events": replay.header.get("events", replay.header.get("lifecycle", [])),
    }
    if as_json:
        print(json.dumps(summary, indent=2))
        return
    print(f"{replay.game} {replay.game_version}  protocol={summary['protocol']}  scope={summary['scope']}")
    print(f"members: {len(per_member)}   godview frames: {summary['godview_frames']}")
    for m in per_member:
        print(
            f"  {m['name']:<14} in={m['packets_from_server']:<6} out={m['packets_from_client']:<6} "
            f"moves={m['movement_packets']:<5} chats={m['chat_packets']:<3} "
            f"login_verified={m['login_verified']} duration={m['duration_s']}s"
        )


def cmd_packets(replay: Replay, args: argparse.Namespace) -> None:
    emitted = 0
    for member in replay.members:
        if args.member and member.name.lower() != args.member.lower():
            continue
        for packet in member.packets:
            if args.opcode and packet.opcode not in args.opcode:
                continue
            if args.say_only and packet.opcode not in CHAT_OPCODES:
                continue
            row: dict = {
                "member": member.name,
                "from_client": packet.from_client,
                "unix_s": packet.unix_seconds,
                "server_ms": packet.server_ms,
                "opcode": packet.opcode,
                "size": len(packet.body),
            }
            if (name := packet.opcode_name) is not None:
                row["opcode_name"] = name
            if packet.opcode in CHAT_OPCODES and (text := _chat_text(packet)):
                row["text"] = text
            print(json.dumps(row, separators=(",", ":")))
            emitted += 1
            if args.limit and emitted >= args.limit:
                return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("summary", "packets", "trajectory", "members", "header"):
        p = sub.add_parser(name)
        p.add_argument("replay", type=Path)
        if name == "summary":
            p.add_argument("--json", action="store_true")
        if name == "packets":
            p.add_argument("--member")
            p.add_argument("--opcode", type=int, action="append")
            p.add_argument("--say-only", action="store_true")
            p.add_argument("--limit", type=int, default=0)
        if name == "trajectory":
            p.add_argument("--member")
            p.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)

    try:
        replay = decode_replay(args.replay)
    except ReplayError as exc:
        print(f"cwreplay: {exc}", file=sys.stderr)
        return 1

    if args.command == "summary":
        cmd_summary(replay, as_json=args.json)
    elif args.command == "packets":
        cmd_packets(replay, args)
    elif args.command == "trajectory":
        cmd_trajectory(replay, args)
    elif args.command == "members":
        for member in replay.members:
            print(f"{member.name}\tguid=0x{member.guid:x}\tpackets={len(member.packets)}")
    elif args.command == "header":
        print(json.dumps(replay.header, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
