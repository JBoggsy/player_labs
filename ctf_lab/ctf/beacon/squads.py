"""Squad play (v19): membership, formation forces, wait-gating, aim sectors.

Design: docs/designs/ctf-squad-play-design.md. The load-bearing constraint is that
visible teammates are ANONYMOUS (`player <color> <side>` — no identity), so squad
logic splits into:

  * **membership** — a pure function of seat (like roles and item claims): every
    agent computes the same table, no negotiation. D = seats 0-2 (defenders),
    A1 = 3-4 (steal pair), A2 = 5-7 (second wave). Within-squad **rank** = my
    index in the squad tuple; rank drives aim sectors.
  * **anonymous flocking** — cohesion/separation forces computed from visible or
    tracked teammates; any nearby teammate is squad-enough. (When nameplates land
    upstream, cohesion upgrades to true squadmate identity here, locally.)
  * **wait-gating** — attackers HOLD at a rally line until enough teammates are
    near (converts the dribble-in attack into waves), with a timeout so a dead
    squadmate never deadlocks the push.
  * **aim sectors** — each rank offsets its lighthouse sweep centre so a squad
    covers a forward cone + two shoulders instead of three copies of one arc.

Squad OBJECTIVES must be computed only from globally-observable inputs (flag
state, geometry, tick) — never per-agent belief — or members silently diverge;
this module keeps to formation/micro concerns where local belief is safe.
"""

from __future__ import annotations

import math

from ctf.beacon.config import (
    MAP_W,
    SQUAD_COHESION_PX,
    SQUAD_MIN_BUDDIES,
    SQUAD_RALLY_X,
    SQUAD_SECTOR_BRADS,
    SQUAD_SEPARATION_PX,
    SQUAD_WAIT_TIMEOUT_TICKS,
    TRACK_TTL_TICKS,
)
from ctf.beacon.types import Belief, Team

#: The squad tables: seat -> (squad name, member seats in rank order).
_SQUAD_OF: dict[int, tuple[str, tuple[int, ...]]] = {}
for _name, _seats in (("D", (0, 1, 2)), ("A1", (3, 4)), ("A2", (5, 6, 7))):
    for _s in _seats:
        _SQUAD_OF[_s] = (_name, _seats)


def squad_of(seat: int) -> tuple[str, tuple[int, ...]]:
    """(squad name, member seats in rank order) for a seat."""
    return _SQUAD_OF.get(seat, ("A2", (5, 6, 7)))


def rank_of(seat: int) -> int:
    """My index within my squad (0 = point)."""
    name, seats = squad_of(seat)
    return seats.index(seat) if seat in seats else 0


def squad_size(seat: int) -> int:
    return len(squad_of(seat)[1])


def sector_offset_brads(seat: int) -> int:
    """Lighthouse-sweep centre offset for my rank: 0, +SECTOR, -SECTOR, ...

    Rank 0 watches the threat axis; ranks 1/2 take the shoulders. With the 60°
    half-angle vision cone this yields overlapping-but-complementary coverage."""
    rank = rank_of(seat)
    if rank == 0:
        return 0
    sign = 1 if rank % 2 == 1 else -1
    return sign * SQUAD_SECTOR_BRADS * ((rank + 1) // 2)


# --- Anonymous teammate proximity -----------------------------------------------------


def _teammate_positions(belief: Belief) -> list[tuple[int, int]]:
    """Positions of teammates we can see or remember (fresh tracks). Anonymous —
    that's fine: any teammate near me is squad-enough for cohesion/wait purposes."""
    out = [e.pos for e in belief.teammates]
    for t in belief.teammate_tracks:
        if belief.tick - t.last_tick <= TRACK_TTL_TICKS // 2 and t.pos not in out:
            out.append(t.pos)
    return out


def buddies_near(belief: Belief, radius_px: float) -> int:
    """How many teammates are within ``radius_px`` of us (sight + fresh tracks)."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    return sum(
        1
        for (x, y) in _teammate_positions(belief)
        if math.hypot(x - sx, y - sy) <= radius_px
    )


# --- Formation forces -------------------------------------------------------------


def formation_bias(belief: Belief) -> tuple[float, float] | None:
    """A movement-bias vector (unit-ish) from cohesion + separation, or None.

    Cohesion: too few buddies nearby -> pull toward the nearest teammate.
    Separation: a teammate closer than SQUAD_SEPARATION_PX -> push apart (one
    grenade blast is 52px; stacked bodies also block each other's shots).
    Separation wins when both apply."""
    if belief.self_xy is None:
        return None
    sx, sy = belief.self_xy
    mates = _teammate_positions(belief)
    if not mates:
        return None

    nearest = min(mates, key=lambda p: (p[0] - sx) ** 2 + (p[1] - sy) ** 2)
    d = math.hypot(nearest[0] - sx, nearest[1] - sy)

    if 0.5 < d < SQUAD_SEPARATION_PX:
        return ((sx - nearest[0]) / d, (sy - nearest[1]) / d)

    if buddies_near(belief, SQUAD_COHESION_PX) < SQUAD_MIN_BUDDIES and d > SQUAD_COHESION_PX:
        return ((nearest[0] - sx) / d, (nearest[1] - sy) / d)

    return None


# --- Wait-for-squad gating ----------------------------------------------------------


def rally_line_x(team: Team) -> int:
    return SQUAD_RALLY_X if team == "red" else MAP_W - 1 - SQUAD_RALLY_X


def past_rally(team: Team, x: int) -> bool:
    """Whether ``x`` is on the enemy side of our rally line."""
    return x > rally_line_x(team) if team == "red" else x < rally_line_x(team)


def should_wait_for_squad(belief: Belief) -> bool:
    """True when an ATTACKER about to cross the rally line should hold for buddies.

    Gate: I'm alive, attacking (steal objective handles this at the call site),
    near-but-not-past the rally line, with fewer than (squad size - 1) buddies
    nearby, and I haven't already waited past the timeout (a dead squadmate takes
    72t to respawn + walk; waiting forever loses tempo — cap and go).
    """
    if belief.self_xy is None or belief.team is None:
        return False
    x = belief.self_xy[0]
    if past_rally(belief.team, x):
        belief.squad_wait_since = -1  # committed; don't re-gate mid-push
        return False
    dist_to_line = abs(x - rally_line_x(belief.team))
    if dist_to_line > 90:
        belief.squad_wait_since = -1  # not at the line yet
        return False
    need = squad_size(belief.seat) - 1
    if buddies_near(belief, SQUAD_COHESION_PX) >= need:
        belief.squad_wait_since = -1
        return False
    if belief.squad_wait_since < 0:
        belief.squad_wait_since = belief.tick
    if belief.tick - belief.squad_wait_since > SQUAD_WAIT_TIMEOUT_TICKS:
        return False  # timeout: push anyway
    return True


__all__ = [
    "buddies_near",
    "formation_bias",
    "past_rally",
    "rally_line_x",
    "rank_of",
    "sector_offset_brads",
    "should_wait_for_squad",
    "squad_of",
    "squad_size",
]
