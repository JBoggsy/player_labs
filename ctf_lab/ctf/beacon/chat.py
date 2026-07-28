"""Team chat (v18): the 10-char shout protocol — encode, decode, and send arbitration.

CTF shouts (RULES.md "Shouts"): ≤10 printable-ASCII chars, audible to ANYONE (both
teams) within ~247px, through walls and fog, at jittered ±20px coordinates; one
shout per second per player and one live bubble each (a new shout replaces the
old). A heard shout arrives as a sprite labeled ``<team> shout <address>: <text>``
— so messages are team-attributable and same-team payloads can be trusted.

The protocol packs one message type + a coarse position (8px nav-grid cell) into a
compact code. Cells are ``x2(base36) + y2(base36)`` — GRID_W=155 and GRID_H=83 both
fit in two base-36 digits, so every message is ≤6 chars, well under the cap:

  ``E<cell>``    enemy seen at cell (edge-triggered per sighting burst)
  ``U<cell>``    I'm taking fire at cell (my position; shooter unknown)
  ``G<cell>``    my grenade is en route to cell — clear the blast
  ``C<cell><h>`` I carry the enemy flag at cell, heading octant h (0-7)
  ``T<cell>``    the enemy THIEF (carrying OUR flag) is at cell
  ``O<s><g><cell>`` ORDER (v22): leader seat s sets squad goal g at cell
                    (g: H hold / S scout / P push / F flag / T thief-hunt)
  ``K<s><cell>`` seat s is taking the fighting post at cell
  ``P<s><cell>`` presence ping (v22): seat s is alive at cell

Sender arbitration: one bubble/sec, so one message wins per window — priority
C > T > O > G > U > K > E > P (carrier state beats intel; squad orders retain
their existing priority; a post claim beats chatter/presence only). Messages are
events, not state: the decoder turns them into belief updates (phantom tracks /
danger stamps / carrier fixes / expiring post claims) and drops the message.

Enemy shouts are heard too. We do NOT decode enemy payloads as truth (they could
lie), but an enemy shout is at least a live-enemy position fix (±20px) — the
decoder returns it as a plain sighting-grade event.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ctf.beacon.config import (
    CHAT_ENEMY_REARM_TICKS,
    CHAT_ENEMY_RESHOUT_TICKS,
    CHAT_MIN_INTERVAL_TICKS,
    GRID_H,
    GRID_W,
    NAV_CELL,
    ORDER_REBROADCAST_TICKS,
    PING_INTERVAL_TICKS,
    POSTS,
    POST_CLAIM_REBROADCAST_TICKS,
    SQUAD_COMMAND,
)
from ctf.beacon.types import Belief, Team
from ctf.beacon import squads

_B36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def _enc2(v: int) -> str:
    """Two-digit base-36 (0..1295); grid coords are ≤154 so this always fits."""
    return _B36[(v // 36) % 36] + _B36[v % 36]


def _dec2(s: str) -> int | None:
    try:
        return _B36.index(s[0]) * 36 + _B36.index(s[1])
    except (ValueError, IndexError):
        return None


def encode_cell(pos: tuple[int, int]) -> str:
    gx = min(max(pos[0] // NAV_CELL, 0), GRID_W - 1)
    gy = min(max(pos[1] // NAV_CELL, 0), GRID_H - 1)
    return _enc2(gx) + _enc2(gy)


def decode_cell(code: str) -> tuple[int, int] | None:
    """Cell code -> map-px cell centre, or None if malformed/out of range."""
    if len(code) < 4:
        return None
    gx, gy = _dec2(code[0:2]), _dec2(code[2:4])
    if gx is None or gy is None or gx >= GRID_W or gy >= GRID_H:
        return None
    return (gx * NAV_CELL + NAV_CELL // 2, gy * NAV_CELL + NAV_CELL // 2)


#: Order goal letters (v22): what a leader can set a squad to do.
ORDER_GOALS = ("H", "S", "P", "F", "T")  # hold / scout / push / flag / thief-hunt


@dataclass(frozen=True)
class ChatMessage:
    """One decoded same-team message."""

    kind: str  # enemy|under_fire|grenade|carrier|thief|order|post_claim|ping
    pos: tuple[int, int]
    heading: int | None = None  # carrier heading octant 0-7 (E, NE, N, ... CCW)
    seat: int | None = None  # sender seat (order/ping)
    goal: str | None = None  # order goal letter (H/S/P/F/T)


def encode(kind: str, pos: tuple[int, int], heading: int | None = None) -> str:
    prefix = {"enemy": "E", "under_fire": "U", "grenade": "G",
              "carrier": "C", "thief": "T"}[kind]
    code = prefix + encode_cell(pos)
    if kind == "carrier":
        code += str((heading or 0) % 8)
    return code


def encode_order(seat: int, goal: str, pos: tuple[int, int]) -> str:
    """``O<seat><goal><cell>`` — 7 chars."""
    assert goal in ORDER_GOALS
    return f"O{seat % 8}{goal}" + encode_cell(pos)


def encode_ping(seat: int, pos: tuple[int, int]) -> str:
    """``P<seat><cell>`` — 6 chars."""
    return f"P{seat % 8}" + encode_cell(pos)


def encode_claim(seat: int, pos: tuple[int, int]) -> str:
    """``K<seat><cell>`` — 6 chars."""
    return f"K{seat % 8}" + encode_cell(pos)


def decode(text: str) -> ChatMessage | None:
    """Parse one same-team shout payload; None if it isn't protocol traffic."""
    if not text:
        return None
    if text[0] == "O" and len(text) >= 7 and text[1].isdigit() and text[2] in ORDER_GOALS:
        pos = decode_cell(text[3:7])
        if pos is None:
            return None
        return ChatMessage(kind="order", pos=pos, seat=int(text[1]), goal=text[2])
    if text[0] == "P" and len(text) >= 6 and text[1].isdigit():
        pos = decode_cell(text[2:6])
        if pos is None:
            return None
        return ChatMessage(kind="ping", pos=pos, seat=int(text[1]))
    if text[0] == "K" and len(text) >= 6 and text[1].isdigit():
        pos = decode_cell(text[2:6])
        if pos is None:
            return None
        return ChatMessage(kind="post_claim", pos=pos, seat=int(text[1]))
    kind = {"E": "enemy", "U": "under_fire", "G": "grenade",
            "C": "carrier", "T": "thief"}.get(text[0])
    if kind is None:
        return None
    pos = decode_cell(text[1:5])
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
    chat bookkeeping (last-sent ticks, seen-enemy edge state).

    Priority C > T > O > G > U > K > E > P. Rate: the server enforces 1/s; we
    self-limit to CHAT_MIN_INTERVAL_TICKS so the bubble a teammate reads is
    usually current.
    """
    if belief.self_xy is None:
        return None
    tick = belief.tick
    if tick - belief.chat_last_sent_tick < CHAT_MIN_INTERVAL_TICKS:
        return None

    msg: str | None = None
    kind: str | None = None

    # O: leader order broadcast (v22) — on change or on cadence. Sits below the
    # carrier heartbeat / thief fix (those are the two live-or-die messages) and
    # above everything else: a squad without orders is a squad without shape.
    def _order_due() -> bool:
        if not SQUAD_COMMAND or belief.order is None:
            return False
        if squads.leader_of(belief.seat) != belief.seat:
            return False  # only the leader broadcasts
        return tick - belief.last_order_sent_tick >= ORDER_REBROADCAST_TICKS

    # C: carrier heartbeat — while carrying, this is ALL we say (escorts need it
    # fresh, and our position is already blazing via the carried-flag sprite, so
    # the shout's position leak costs nothing).
    if belief.i_carry_enemy_flag:
        vel = None
        # our own heading: difference of recent positions is tracked by nav;
        # cheapest robust source is the last movement octant we don't store, so
        # derive from nav progress point if present.
        if belief.nav_last_xy is not None:
            vel = (belief.self_xy[0] - belief.nav_last_xy[0],
                   belief.self_xy[1] - belief.nav_last_xy[1])
        msg = encode("carrier", belief.self_xy, heading_octant(vel))
        kind = "carrier"
    # T: we can SEE the enemy thief carrying our flag.
    elif belief.own_flag_stolen and belief.own_flag_thief_pos is not None:
        msg = encode("thief", belief.own_flag_thief_pos)
        kind = "thief"
    # O: leader broadcasts the squad order (v22).
    elif _order_due():
        goal, pos, _ = belief.order
        msg = encode_order(belief.seat, goal, pos)
        kind = "order"
        belief.last_order_sent_tick = tick
        belief.orders_sent += 1
    # G: our grenade is in the air / charging toward a target.
    elif belief.throw_target is not None and belief.throw_charge_ticks > 0:
        msg = encode("grenade", belief.throw_target)
        kind = "grenade"
    # U: fire is landing near us and we can't see the shooter.
    elif belief.under_fire and not belief.enemies:
        msg = encode("under_fire", belief.self_xy)
        kind = "under_fire"
    # K: while a post objective is actually active, refresh our claim. It sits
    # below live intel and above enemy chatter/presence; a higher strategy rung
    # leaves post_active false and releases the claim on the receiver TTL.
    elif (
        POSTS
        and belief.post_active
        and belief.post_cell is not None
        and tick - belief.post_last_claim_sent_tick >= POST_CLAIM_REBROADCAST_TICKS
    ):
        msg = encode_claim(belief.seat, belief.post_cell)
        kind = "post_claim"
        belief.post_last_claim_sent_tick = tick
        belief.post_claims_sent += 1
    # E: enemies in view — edge-triggered: shout on a FRESH sighting burst, then
    # stay quiet until vision has been enemy-free for a while (re-arm), so a
    # peek-ducking enemy doesn't retrigger spam.
    elif belief.enemies:
        if belief.chat_enemy_armed and tick - belief.chat_last_enemy_tick >= CHAT_ENEMY_RESHOUT_TICKS:
            nearest = min(
                belief.enemies,
                key=lambda e: (e.pos[0] - belief.self_xy[0]) ** 2 + (e.pos[1] - belief.self_xy[1]) ** 2,
            )
            msg = encode("enemy", nearest.pos)
            kind = "enemy"
            belief.chat_enemy_armed = False
            belief.chat_last_enemy_tick = tick
    # P: presence ping (v22) — lowest priority; the squad's heartbeat. Feeds the
    # leader's strength table and the rejoin contact check.
    elif SQUAD_COMMAND and tick - belief.last_ping_tick >= PING_INTERVAL_TICKS:
        msg = encode_ping(belief.seat, belief.self_xy)
        kind = "ping"
        belief.last_ping_tick = tick
        belief.pings_sent += 1

    if belief.enemies:
        belief.chat_enemy_seen_tick = tick
    elif tick - belief.chat_enemy_seen_tick > CHAT_ENEMY_REARM_TICKS:
        belief.chat_enemy_armed = True  # vision has been clear long enough

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
    "encode_claim",
    "heading_octant",
]
