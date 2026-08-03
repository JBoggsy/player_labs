"""Squad play: membership, formation forces, aim sectors, and the convert trigger.

Ported from beacon with two structural changes:

  * **Roster-aware membership** — paintbot deals 4 or 8 seats per team, so the
    squad tables derive from the actual seat count instead of assuming 8.
  * **Derived geometry** — rally lines, chokes, and home steps come from the
    episode WorldMap (home->center axis fractions), not authored constants.

The formation floor (separation/cohesion) and the CONVERT trigger (hunt the
wipe when an enemy team's lives run low — the single biggest measured win in
the beacon lineage) stay always-available; the leader/order command layer stays
OFF by default (beacon v29 rollback).

Multi-team: "enemy lives" generalizes to the WEAKEST live enemy team — under
GV32/33 eliminating any one team removes a rival and its heart, and under pot
scoring a timeout draw pays -1 like a loss, so finishing the weakest team is
nearly free aggression.
"""

from __future__ import annotations

import math

from paintbot.stencil.config import (
    BACKOFF_STEP_PX,
    CONVERT_ENEMY_LIVES,
    PRESENCE_STALE_TICKS,
    REJOIN_CONTACT_PX,
    SQUAD_COHESION_PX,
    SQUAD_MIN_BUDDIES,
    SQUAD_SECTOR_BRADS,
    SQUAD_SEPARATION_PX,
    SQUAD_SPREAD_PX,
    TRACK_TTL_TICKS,
)
from paintbot.stencil.types import Belief, Team


def _seats_per_team(belief: Belief) -> int:
    if belief.worldmap is not None:
        return belief.worldmap.seats_per_team()
    return 8


def _squad_table(seats: int) -> tuple[tuple[str, tuple[int, ...]], ...]:
    if seats <= 4:
        return (("A", (0, 1)), ("B", (2, 3)))
    return (("A", (0, 1, 2)), ("C", (3, 4)), ("B", (5, 6, 7)))


def squad_of(belief: Belief, seat: int | None = None) -> tuple[str, tuple[int, ...]]:
    """(squad name, member seats in rank order) for a seat on this roster."""
    seat = belief.seat if seat is None else seat
    for name, seats in _squad_table(_seats_per_team(belief)):
        if seat in seats:
            return (name, seats)
    name, seats = _squad_table(_seats_per_team(belief))[-1]
    return (name, seats)


def rank_of(belief: Belief, seat: int | None = None) -> int:
    """My index within my squad (0 = point)."""
    seat = belief.seat if seat is None else seat
    _name, seats = squad_of(belief, seat)
    return seats.index(seat) if seat in seats else 0


def squad_size(belief: Belief) -> int:
    return len(squad_of(belief)[1])


def leader_of(belief: Belief, seat: int | None = None) -> int:
    """The squad's leader seat: the LOWEST seat in the squad."""
    return min(squad_of(belief, seat)[1])


def sector_offset_brads(belief: Belief) -> int:
    """Lighthouse-sweep centre offset for my rank: 0, +SECTOR, -SECTOR, ..."""
    rank = rank_of(belief)
    if rank == 0:
        return 0
    sign = 1 if rank % 2 == 1 else -1
    return sign * SQUAD_SECTOR_BRADS * ((rank + 1) // 2)


# --- Anonymous teammate proximity -----------------------------------------------------


def _teammate_positions(belief: Belief, squad_only: bool = False) -> list[tuple[int, int]]:
    """Positions of teammates we can see or remember (fresh tracks)."""
    my_squad = set(squad_of(belief)[1]) - {belief.seat}
    out: list[tuple[int, int]] = []
    for e in belief.teammates:
        if squad_only and e.identity not in my_squad:
            continue
        out.append(e.pos)
    for t in belief.teammate_tracks:
        if belief.tick - t.last_tick > TRACK_TTL_TICKS // 2 or t.pos in out:
            continue
        if squad_only and t.identity not in my_squad:
            continue
        out.append(t.pos)
    return out


def buddies_near(belief: Belief, radius_px: float) -> int:
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    return sum(
        1
        for (x, y) in _teammate_positions(belief)
        if math.hypot(x - sx, y - sy) <= radius_px
    )


# --- Formation forces -------------------------------------------------------------


def separation_bias(belief: Belief) -> tuple[float, float] | None:
    """A unit push-apart vector when ANY teammate is closer than SEPARATION_PX."""
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
    return None


def formation_bias(belief: Belief) -> tuple[float, float] | None:
    """A movement-bias vector from cohesion + separation, or None."""
    if belief.self_xy is None:
        return None
    sx, sy = belief.self_xy
    mates = _teammate_positions(belief)
    if not mates:
        return None

    sep = separation_bias(belief)
    if sep is not None:
        return sep

    nearest = min(mates, key=lambda p: (p[0] - sx) ** 2 + (p[1] - sy) ** 2)
    d = math.hypot(nearest[0] - sx, nearest[1] - sy)

    if buddies_near(belief, SQUAD_COHESION_PX) < SQUAD_MIN_BUDDIES and d > SQUAD_COHESION_PX:
        squadmates = _teammate_positions(belief, squad_only=True)
        target = (
            min(squadmates, key=lambda p: (p[0] - sx) ** 2 + (p[1] - sy) ** 2)
            if squadmates
            else nearest
        )
        td = math.hypot(target[0] - sx, target[1] - sy)
        if td < 0.5:
            return None
        return ((target[0] - sx) / td, (target[1] - sy) / td)

    return None


def spread_point(belief: Belief, pos: tuple[int, int]) -> tuple[int, int]:
    """``pos`` offset by my rank so squadmates sharing a point fan out."""
    rank = rank_of(belief)
    if rank == 0:
        offset = 0
    else:
        sign = 1 if rank % 2 == 1 else -1
        offset = sign * SQUAD_SPREAD_PX * ((rank + 1) // 2)
    wm = belief.worldmap
    max_y = (wm.height - 21) if wm is not None else pos[1]
    x, y = pos[0], min(max(pos[1] + offset, 20), max_y)
    if offset == 0 or wm is None:
        return (x, y)
    cover = wm.nearest_cover(x, y)
    return cover if cover is not None else (x, y)


# --- Squad command: leader decisions + respawn discipline -----------------------------


def update_presence(belief: Belief) -> None:
    """Refresh the presence table from badge sightings (identity == seat)."""
    my_squad = set(squad_of(belief)[1]) - {belief.seat}
    for e in belief.teammates:
        if e.identity in my_squad:
            belief.presence[e.identity] = belief.tick


def enemy_lives_left(belief: Belief) -> int | None:
    """Lives remaining of the WEAKEST live enemy team, from the scoreboard.

    Per-team lives = seats*LIVES_PER_PLAYER - that team's aggregate deaths.
    Teams whose lives are exhausted (eliminated) are skipped. None before the
    first scoreboard parse."""
    if belief.worldmap is None or not belief.team_scores:
        return None
    total = belief.worldmap.team_total_lives()
    lives = [
        max(0, total - deaths)
        for color, (_kills, deaths) in belief.team_scores.items()
        if color != belief.team and max(0, total - deaths) > 0
    ]
    if not lives:
        return None
    return min(lives)


def weakest_enemy_color(belief: Belief) -> Team | None:
    """The live enemy color with the fewest lives remaining, or None."""
    if belief.worldmap is None or not belief.team_scores:
        return None
    total = belief.worldmap.team_total_lives()
    best: Team | None = None
    best_lives = None
    for color, (_kills, deaths) in belief.team_scores.items():
        if color == belief.team:
            continue
        remaining = max(0, total - deaths)
        if remaining <= 0:
            continue
        if best_lives is None or remaining < best_lives:
            best_lives = remaining
            best = color
    return best


def wipe_in_reach(belief: Belief) -> bool:
    """Whether the weakest enemy team is close enough to finished to hunt."""
    lives = enemy_lives_left(belief)
    return lives is not None and lives <= CONVERT_ENEMY_LIVES


def convert_hunt_point(belief: Belief) -> tuple[int, int]:
    """Where the all-in should converge: the freshest enemy evidence, else the
    weakest enemy team's pedestal."""
    if belief.enemies:
        return belief.enemies[0].pos
    fresh = [t for t in belief.enemy_tracks
             if belief.tick - t.last_tick <= TRACK_TTL_TICKS]
    if fresh:
        newest = max(fresh, key=lambda t: t.last_tick)
        return newest.pos
    wm = belief.worldmap
    target = weakest_enemy_color(belief)
    if wm is not None and target is not None:
        return wm.pedestal(target)
    if wm is not None:
        return wm.center
    return belief.self_xy or (0, 0)


def squadmates_alive(belief: Belief) -> int:
    my_squad = set(squad_of(belief)[1]) - {belief.seat}
    return sum(
        1
        for s in my_squad
        if belief.tick - belief.presence.get(s, -10_000) <= PRESENCE_STALE_TICKS
    )


def lead_squad(belief: Belief) -> None:
    """The leader's per-tick rule engine: set/refresh ``belief.order``."""
    if leader_of(belief) != belief.seat or belief.self_xy is None:
        return
    wm = belief.worldmap
    team = belief.team
    if wm is None or team is None:
        return
    tick = belief.tick
    name, _seats = squad_of(belief)

    goal: str
    pos: tuple[int, int]
    if belief.own_heart_stolen and (
        belief.own_heart_thief_pos is not None or belief.thief_fix is not None
    ):
        goal = "T"
        pos = belief.own_heart_thief_pos or belief.thief_fix[0]
    elif belief.carrier_fix is not None:
        goal = "F"
        pos = belief.carrier_fix[0]
    elif wipe_in_reach(belief):
        goal = "T"
        pos = convert_hunt_point(belief)
        if belief.order is None or belief.order[0] != "T":
            belief.convert_events += 1
    elif (
        wm.past_rally(team, belief.self_xy)
        and squadmates_alive(belief) < squad_size(belief) - 1
    ):
        goal = "H"
        pos = wm.home_step(team, belief.self_xy, BACKOFF_STEP_PX)
        if belief.order is None or belief.order[0] != "H":
            belief.backoff_events += 1
    else:
        # Defaults: side squads hold spread choke anchors; the middle squad
        # pushes the map centre.
        choke = wm.choke_point(team)
        if name == "A":
            goal, pos = "H", spread_point(belief, choke)
        elif name == "B":
            goal, pos = "H", spread_point(belief, choke)
        else:
            goal, pos = "P", wm.center

    if belief.order is None or belief.order[0] != goal or belief.order[1] != pos:
        belief.order = (goal, pos, tick)
        belief.order_source = "leader"


def decay_hold_point(belief: Belief) -> tuple[int, int]:
    """Where a member whose ORDER went stale backs off to and holds."""
    assert belief.self_xy is not None and belief.team is not None
    wm = belief.worldmap
    if wm is not None and wm.past_rally(belief.team, belief.self_xy):
        return wm.home_step(belief.team, belief.self_xy, BACKOFF_STEP_PX)
    return belief.self_xy


def rejoin_target(belief: Belief) -> tuple[int, int] | None:
    """Where a dead agent should regroup on respawn."""
    my_squad = set(squad_of(belief)[1]) - {belief.seat}
    best: tuple[int, int] | None = None
    best_tick = -1
    for t in belief.teammate_tracks:
        if t.identity in my_squad and t.last_tick > best_tick:
            best_tick = t.last_tick
            best = t.pos
    if best is not None:
        return best
    if belief.self_xy is not None and belief.team is not None and belief.worldmap is not None:
        return belief.worldmap.home_step(belief.team, belief.self_xy, BACKOFF_STEP_PX * 2)
    return None


def in_squad_contact(belief: Belief) -> bool:
    """Rejoin exit test: a squadmate confirmed near us."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    my_squad = set(squad_of(belief)[1]) - {belief.seat}
    for e in belief.teammates:
        if e.identity in my_squad and math.hypot(e.pos[0] - sx, e.pos[1] - sy) <= REJOIN_CONTACT_PX:
            return True
    return False


__all__ = [
    "buddies_near",
    "convert_hunt_point",
    "decay_hold_point",
    "enemy_lives_left",
    "formation_bias",
    "in_squad_contact",
    "lead_squad",
    "leader_of",
    "rank_of",
    "rejoin_target",
    "sector_offset_brads",
    "separation_bias",
    "spread_point",
    "squad_of",
    "squad_size",
    "squadmates_alive",
    "update_presence",
    "weakest_enemy_color",
    "wipe_in_reach",
]
