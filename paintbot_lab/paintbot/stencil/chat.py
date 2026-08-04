"""Team chat: the 10-char shout protocol — encode, decode, and send arbitration.

Shouts: ≤10 printable-ASCII chars, audible to ANYONE (all teams) within
~map_width/5 px, through walls and fog, at jittered ±20px coordinates; one shout
per second per player and one live bubble each. A heard shout arrives as a
sprite labeled ``<team> shout <name>: <text>`` (the name is the anonymized
per-team slot letter) — so messages are team-attributable and same-team payloads
can be trusted.

The protocol packs one message type + a coarse position (8px nav-grid cell) into
a compact code. Cells are ``x2(base36) + y2(base36)`` — the largest generated
board (giant 2-team, 3211px) has 402 cells per axis, comfortably under the
1295-per-digit-pair cap, so every message stays ≤8 chars:

  ``E<cell>``       enemy seen at cell (edge-triggered per sighting burst)
  ``U<cell>``       I'm taking fire at cell
  ``G<cell>``       my grenade is en route to cell — clear the blast
  ``C<cell><h>``    I carry an enemy heart at cell, heading octant h (0-7)
  ``T<cell>``       an enemy THIEF (carrying OUR heart) is at cell
  ``O<s><g><cell>`` ORDER: leader seat s sets squad goal g at cell
  ``FI<s><i><cell>`` seat s focuses enemy identity i, last seen at cell
  ``FC<s><cell>``   seat s focuses the anonymous enemy last seen at cell
  ``P<s><cell>``    presence ping: seat s is alive at cell

Sender arbitration priority: C > T > O > G > U > F > E > P.
Grid dimensions come from the episode WorldMap — both ends of the protocol are
our own seats on the same map, so encode/decode always agree.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from paintbot.stencil import fight, squads
from paintbot.stencil.config import (
    CHAT_ENEMY_REARM_TICKS,
    CHAT_ENEMY_RESHOUT_TICKS,
    CHAT_MIN_INTERVAL_TICKS,
    NAV_CELL,
    ORDER_REBROADCAST_TICKS,
    PING_INTERVAL_TICKS,
    SQUAD_COMMAND,
)
from paintbot.stencil.types import Belief, TargetRef
from paintbot.stencil.worldmap import WorldMap

_B36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def _enc2(v: int) -> str:
    """Two-digit base-36 (0..1295); generated grids stay well under this."""
    return _B36[(v // 36) % 36] + _B36[v % 36]


def _dec2(s: str) -> int | None:
    try:
        return _B36.index(s[0]) * 36 + _B36.index(s[1])
    except (ValueError, IndexError):
        return None


def encode_cell(wm: WorldMap, pos: tuple[int, int]) -> str:
    gx = min(max(pos[0] // NAV_CELL, 0), wm.grid_w - 1)
    gy = min(max(pos[1] // NAV_CELL, 0), wm.grid_h - 1)
    return _enc2(gx) + _enc2(gy)


def decode_cell(wm: WorldMap, code: str) -> tuple[int, int] | None:
    """Cell code -> map-px cell centre, or None if malformed/out of range."""
    if len(code) < 4:
        return None
    gx, gy = _dec2(code[0:2]), _dec2(code[2:4])
    if gx is None or gy is None or gx >= wm.grid_w or gy >= wm.grid_h:
        return None
    return (gx * NAV_CELL + NAV_CELL // 2, gy * NAV_CELL + NAV_CELL // 2)


#: Order goal letters: what a leader can set a squad to do.
ORDER_GOALS = ("H", "S", "P", "F", "T")  # hold / scout / push / heart / thief-hunt


@dataclass(frozen=True)
class ChatMessage:
    """One decoded same-team message."""

    kind: str  # enemy|under_fire|grenade|carrier|thief|order|focus_claim|ping
    pos: tuple[int, int]
    heading: int | None = None
    seat: int | None = None
    goal: str | None = None
    target_identity: int | None = None


def encode(wm: WorldMap, kind: str, pos: tuple[int, int], heading: int | None = None) -> str:
    prefix = {"enemy": "E", "under_fire": "U", "grenade": "G",
              "carrier": "C", "thief": "T"}[kind]
    code = prefix + encode_cell(wm, pos)
    if kind == "carrier":
        code += str((heading or 0) % 8)
    return code


def encode_order(wm: WorldMap, seat: int, goal: str, pos: tuple[int, int]) -> str:
    assert goal in ORDER_GOALS
    return f"O{seat % 8}{goal}" + encode_cell(wm, pos)


def encode_ping(wm: WorldMap, seat: int, pos: tuple[int, int]) -> str:
    return f"P{seat % 8}" + encode_cell(wm, pos)


def encode_focus_claim(wm: WorldMap, seat: int, target: TargetRef) -> str:
    if target.identity is not None:
        return f"FI{seat % 8}{target.identity % 8}" + encode_cell(wm, target.pos)
    return f"FC{seat % 8}" + encode_cell(wm, target.pos)


def decode(wm: WorldMap, text: str) -> ChatMessage | None:
    """Parse one same-team shout payload; None if it isn't protocol traffic."""
    if not text:
        return None
    if (
        text.startswith("FI")
        and len(text) >= 8
        and text[2].isdigit()
        and text[3].isdigit()
    ):
        pos = decode_cell(wm, text[4:8])
        if pos is None:
            return None
        return ChatMessage(
            kind="focus_claim",
            pos=pos,
            seat=int(text[2]),
            target_identity=int(text[3]),
        )
    if text.startswith("FC") and len(text) >= 7 and text[2].isdigit():
        pos = decode_cell(wm, text[3:7])
        if pos is None:
            return None
        return ChatMessage(kind="focus_claim", pos=pos, seat=int(text[2]))
    if text[0] == "O" and len(text) >= 7 and text[1].isdigit() and text[2] in ORDER_GOALS:
        pos = decode_cell(wm, text[3:7])
        if pos is None:
            return None
        return ChatMessage(kind="order", pos=pos, seat=int(text[1]), goal=text[2])
    if text[0] == "P" and len(text) >= 6 and text[1].isdigit():
        pos = decode_cell(wm, text[2:6])
        if pos is None:
            return None
        return ChatMessage(kind="ping", pos=pos, seat=int(text[1]))
    kind = {"E": "enemy", "U": "under_fire", "G": "grenade",
            "C": "carrier", "T": "thief"}.get(text[0])
    if kind is None:
        return None
    pos = decode_cell(wm, text[1:5])
    if pos is None:
        return None
    heading = None
    if kind == "carrier" and len(text) >= 6 and text[5].isdigit():
        heading = int(text[5]) % 8
    return ChatMessage(kind=kind, pos=pos, heading=heading)


def heading_octant(vel: tuple[float, float] | None) -> int:
    """Velocity -> heading octant 0-7 (0=E, 2=N, 4=W, 6=S; CCW like brads/32)."""
    if vel is None or (abs(vel[0]) < 0.2 and abs(vel[1]) < 0.2):
        return 0
    ang = math.atan2(-vel[1], vel[0])  # screen y down
    return round(ang / (math.pi / 4)) % 8


# --- Sender arbitration ---------------------------------------------------------------


def choose_shout(belief: Belief) -> str | None:
    """The one message worth this tick's bubble, or None. Mutates the belief's
    chat bookkeeping. Priority C > T > O > G > U > F > E > P."""
    if belief.self_xy is None or belief.worldmap is None:
        return None
    wm = belief.worldmap
    tick = belief.tick
    if tick - belief.chat_last_sent_tick < CHAT_MIN_INTERVAL_TICKS:
        return None

    msg: str | None = None
    kind: str | None = None

    def _order_due() -> bool:
        if not SQUAD_COMMAND or belief.order is None:
            return False
        if squads.leader_of(belief) != belief.seat:
            return False
        return tick - belief.last_order_sent_tick >= ORDER_REBROADCAST_TICKS

    # C: carrier heartbeat — while carrying, this is ALL we say.
    if belief.i_carry_heart_of is not None:
        vel = None
        if belief.nav_last_xy is not None:
            vel = (belief.self_xy[0] - belief.nav_last_xy[0],
                   belief.self_xy[1] - belief.nav_last_xy[1])
        msg = encode(wm, "carrier", belief.self_xy, heading_octant(vel))
        kind = "carrier"
    # T: we can SEE an enemy thief carrying our heart.
    elif belief.own_heart_stolen and belief.own_heart_thief_pos is not None:
        msg = encode(wm, "thief", belief.own_heart_thief_pos)
        kind = "thief"
    elif _order_due():
        goal, pos, _ = belief.order
        msg = encode_order(wm, belief.seat, goal, pos)
        kind = "order"
        belief.last_order_sent_tick = tick
        belief.orders_sent += 1
    # G: our grenade is in the air / charging toward a target.
    elif belief.throw_target is not None and belief.throw_charge_ticks > 0:
        msg = encode(wm, "grenade", belief.throw_target)
        kind = "grenade"
    # U: fire is landing near us and we can't see the shooter.
    elif belief.under_fire and not belief.enemies:
        msg = encode(wm, "under_fire", belief.self_xy)
        kind = "under_fire"
    # F: claim the selected firefight target.
    elif (focus_target := fight.focus_claim_to_send(belief)) is not None:
        msg = encode_focus_claim(wm, belief.seat, focus_target)
        kind = "focus_claim"
        fight.note_focus_claim_sent(belief, focus_target)
    # E: enemies in view — edge-triggered.
    elif belief.enemies:
        if belief.chat_enemy_armed and tick - belief.chat_last_enemy_tick >= CHAT_ENEMY_RESHOUT_TICKS:
            nearest = min(
                belief.enemies,
                key=lambda e: (e.pos[0] - belief.self_xy[0]) ** 2 + (e.pos[1] - belief.self_xy[1]) ** 2,
            )
            msg = encode(wm, "enemy", nearest.pos)
            kind = "enemy"
            belief.chat_enemy_armed = False
            belief.chat_last_enemy_tick = tick
    # P: presence ping — lowest priority; the squad's heartbeat.
    elif SQUAD_COMMAND and tick - belief.last_ping_tick >= PING_INTERVAL_TICKS:
        msg = encode_ping(wm, belief.seat, belief.self_xy)
        kind = "ping"
        belief.last_ping_tick = tick
        belief.pings_sent += 1

    if belief.enemies:
        belief.chat_enemy_seen_tick = tick
    elif tick - belief.chat_enemy_seen_tick > CHAT_ENEMY_REARM_TICKS:
        belief.chat_enemy_armed = True

    if msg is not None:
        belief.chat_last_sent_tick = tick
        belief.chat_sent_counts[kind] = belief.chat_sent_counts.get(kind, 0) + 1
    return msg


__all__ = [
    "ChatMessage",
    "choose_shout",
    "decode",
    "decode_cell",
    "encode",
    "encode_cell",
    "encode_focus_claim",
    "heading_octant",
]
