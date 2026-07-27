"""Squad play (v19): membership, formation forces, wait-gating, aim sectors.

Design: docs/designs/ctf-squad-play-design.md. The load-bearing constraint is that
visible teammates are ANONYMOUS (`player <color> <side>` — no identity), so squad
logic splits into:

  * **membership** — a pure function of seat (like roles and item claims): every
    agent computes the same table, no negotiation. A = seats 0-2 and B = 5-7
    (the 3-person side squads), C = 3-4 (the 2-person middle squad, v24).
    Within-squad **rank** = my
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

from ctf.beacon import mapdata
from ctf.beacon.config import (
    BACKOFF_STEP_PX,
    CHOKE_X,
    CONVERT_ENEMY_LIVES,
    MAP_H,
    MAP_W,
    PEDESTAL,
    PRESENCE_STALE_TICKS,
    REJOIN_CONTACT_PX,
    SQUAD_COHESION_PX,
    SQUAD_MIN_BUDDIES,
    SQUAD_RALLY_X,
    SQUAD_SECTOR_BRADS,
    SQUAD_SEPARATION_PX,
    SQUAD_SIDE_HOLD_Y_BOTTOM,
    SQUAD_SIDE_HOLD_Y_TOP,
    SQUAD_SPREAD_PX,
    SQUAD_WAVE_GATE,
    SQUAD_WAVE_PERIOD_TICKS,
    SQUAD_WAVE_WINDOW_TICKS,
    TEAM_TOTAL_LIVES,
    TRACK_TTL_TICKS,
)
from ctf.beacon.types import Belief, Team

#: The squad tables: seat -> (squad name, member seats in rank order).
#: A and B are the 3-person side squads; C is the 2-person middle squad (v24).
_SQUAD_OF: dict[int, tuple[str, tuple[int, ...]]] = {}
for _name, _seats in (("A", (0, 1, 2)), ("C", (3, 4)), ("B", (5, 6, 7))):
    for _s in _seats:
        _SQUAD_OF[_s] = (_name, _seats)


def squad_of(seat: int) -> tuple[str, tuple[int, ...]]:
    """(squad name, member seats in rank order) for a seat."""
    return _SQUAD_OF.get(seat, ("B", (5, 6, 7)))


def rank_of(seat: int) -> int:
    """My index within my squad (0 = point)."""
    name, seats = squad_of(seat)
    return seats.index(seat) if seat in seats else 0


def squad_size(seat: int) -> int:
    return len(squad_of(seat)[1])


def leader_of(seat: int) -> int:
    """The squad's leader seat: the LOWEST seat in the squad (static, so every
    member knows its leader with zero negotiation)."""
    return min(squad_of(seat)[1])


def sector_offset_brads(seat: int) -> int:
    """Lighthouse-sweep centre offset for my rank: 0, +SECTOR, -SECTOR, ...

    Rank 0 watches the threat axis; ranks 1/2 take the shoulders. With the 45°
    half-angle vision cone (league variant config) this yields complementary
    coverage with a small overlap."""
    rank = rank_of(seat)
    if rank == 0:
        return 0
    sign = 1 if rank % 2 == 1 else -1
    return sign * SQUAD_SECTOR_BRADS * ((rank + 1) // 2)


# --- Anonymous teammate proximity -----------------------------------------------------


def _teammate_positions(belief: Belief, squad_only: bool = False) -> list[tuple[int, int]]:
    """Positions of teammates we can see or remember (fresh tracks).

    With ``squad_only`` (0.7.69 nameplates), restrict to identified SQUADMATES —
    identity index == seat (both are slot-order-within-team). Unidentified
    sightings are excluded in squad_only mode; falls back to all teammates when
    no squadmate is identifiable (badges fog with their player)."""
    my_squad = set(squad_of(belief.seat)[1]) - {belief.seat}
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
    """How many teammates are within ``radius_px`` of us (sight + fresh tracks)."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    return sum(
        1
        for (x, y) in _teammate_positions(belief)
        if math.hypot(x - sx, y - sy) <= radius_px
    )


# --- Formation forces -------------------------------------------------------------


def separation_bias(belief: Belief) -> tuple[float, float] | None:
    """A unit push-apart vector when ANY teammate is closer than SEPARATION_PX,
    else None. (One grenade blast is 52px; stacked bodies block each other's
    shots and eat friendly fire.) Split out of formation_bias (v25) so HOLDING
    agents — which emit no other movement — can still unstack."""
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
    """A movement-bias vector (unit-ish) from cohesion + separation, or None.

    Separation: ANY teammate closer than SQUAD_SEPARATION_PX -> push apart (one
    grenade blast is 52px; stacked bodies also block each other's shots).
    Cohesion: too few buddies nearby -> pull toward the nearest identified
    SQUADMATE (0.7.69 nameplates) when one is known, else the nearest teammate.
    Separation wins when both apply."""
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


def spread_point(seat: int, pos: tuple[int, int]) -> tuple[int, int]:
    """``pos`` offset by my rank so squadmates sharing an order fan out (v25).

    Every member of a squad receives the SAME order point, and every member's A*
    converges on the same cell — the root cause of the v24 stack-ups (teammates
    body-blocking shots, FF kills at <15px, one grenade hitting the pile).
    Rank-offset the point along y (0 / +SPREAD / -SPREAD — same scheme as the aim
    sectors) so a 3-man squad holds a short vertical line across its lane instead
    of one cell. Pure seat math, zero coordination; snapped to the nearest cover
    cell so the spread doesn't push anyone into the open (falls back to the raw
    offset point clamped on-map)."""
    rank = rank_of(seat)
    if rank == 0:
        offset = 0
    else:
        sign = 1 if rank % 2 == 1 else -1
        offset = sign * SQUAD_SPREAD_PX * ((rank + 1) // 2)
    x, y = pos[0], min(max(pos[1] + offset, 20), MAP_H - 21)
    if offset == 0:
        return (x, y)
    cover = mapdata.nearest_cover(x, y)
    return cover if cover is not None else (x, y)


# --- Wait-for-squad gating ----------------------------------------------------------


def rally_line_x(team: Team) -> int:
    return SQUAD_RALLY_X if team == "red" else MAP_W - 1 - SQUAD_RALLY_X


def past_rally(team: Team, x: int) -> bool:
    """Whether ``x`` is on the enemy side of our rally line."""
    return x > rally_line_x(team) if team == "red" else x < rally_line_x(team)


def should_wait_for_squad(belief: Belief) -> bool:
    """True when an ATTACKER at the rally line should hold for the next wave window.

    v19's buddy-SENSING gate deadlocked: teammates are fog-gated (everyone at the
    rally aims enemy-ward, so squadmates 60px apart see nothing), buddies_near read
    0, and every attacker burned the full timeout every push. v19.1 uses the one
    squad signal fog can't hide: the TICK. Waves are synchronized windows — a pure
    function of tick every agent computes identically — so attackers arriving at
    the rally hold until the window opens, then all commit together. Cost: up to
    one window period of tempo; traced via squad_wait_ticks.
    """
    if not SQUAD_WAVE_GATE:
        return False  # v21: gating off by default (tempo cost > sync benefit)
    if belief.self_xy is None or belief.team is None:
        return False
    x = belief.self_xy[0]
    if past_rally(belief.team, x):
        return False  # committed; don't re-gate mid-push
    if abs(x - rally_line_x(belief.team)) > 90:
        return False  # not at the line yet
    return belief.tick % SQUAD_WAVE_PERIOD_TICKS >= SQUAD_WAVE_WINDOW_TICKS


# --- Squad command (v22): leader decisions + respawn discipline -----------------------


def update_presence(belief: Belief) -> None:
    """Refresh the presence table from badge sightings (identity == seat). Pings
    and orders refresh it in belief._update_chat when heard."""
    my_squad = set(squad_of(belief.seat)[1]) - {belief.seat}
    for e in belief.teammates:
        if e.identity in my_squad:
            belief.presence[e.identity] = belief.tick


def enemy_lives_left(belief: Belief) -> int | None:
    """The enemy team's total lives remaining, from the team scoreboard (v26).

    24 (8 players x 3 lives) minus their aggregate deaths — exact while all 16
    slots stay connected, an overcount if an enemy disconnected (safe direction:
    we under-trigger the convert, never over-trigger). None before the first
    scoreboard parse."""
    if belief.enemy_team_score is None:
        return None
    _kills, deaths = belief.enemy_team_score
    return max(0, TEAM_TOTAL_LIVES - deaths)


def wipe_in_reach(belief: Belief) -> bool:
    """Whether the enemy is weak enough that leaders should order the all-in
    hunt (v26 convert trigger): their lives at or below CONVERT_ENEMY_LIVES.
    Under GV21 a draw pays -1 exactly like a loss, so once the wipe is this
    close the downside of committing is ~zero and the upside is +1."""
    lives = enemy_lives_left(belief)
    return lives is not None and lives <= CONVERT_ENEMY_LIVES


def convert_hunt_point(belief: Belief) -> tuple[int, int]:
    """Where the all-in should converge: the freshest enemy evidence, else their
    pedestal (respawns walk from the home edge; the pedestal is the anchor all
    remaining enemies must eventually defend or abandon)."""
    team = belief.team
    assert team is not None
    if belief.enemies:
        return belief.enemies[0].pos
    fresh = [t for t in belief.enemy_tracks
             if belief.tick - t.last_tick <= TRACK_TTL_TICKS]
    if fresh:
        newest = max(fresh, key=lambda t: t.last_tick)
        return newest.pos
    return PEDESTAL["blue" if team == "red" else "red"]


def squadmates_alive(belief: Belief) -> int:
    """Squadmates confirmed alive recently (badge/ping/order within the stale
    window). Conservative: an unconfirmed mate counts as DOWN — the cheap error
    under lives>captures is holding when we didn't need to."""
    my_squad = set(squad_of(belief.seat)[1]) - {belief.seat}
    return sum(
        1
        for s in my_squad
        if belief.tick - belief.presence.get(s, -10_000) <= PRESENCE_STALE_TICKS
    )


def _home_step(team: Team, pos: tuple[int, int], step: int) -> tuple[int, int]:
    """``pos`` stepped ``step`` px toward our home edge (clamped to the map)."""
    x = pos[0] - step if team == "red" else pos[0] + step
    return (min(max(x, 12), MAP_W - 13), pos[1])


def lead_squad(belief: Belief) -> None:
    """The leader's per-tick rule engine: set/refresh ``belief.order``.

    Runs only on the squad's leader (lowest seat). Rules, first match wins:
      1. Own flag stolen + a thief fix known -> T (thief hunt) at the fix.
      2. A teammate carries the enemy flag -> F (escort/flag) at the carrier fix.
      3. CONVERT (v26): the wipe is in reach (enemy lives <= CONVERT_ENEMY_LIVES
         off the team scoreboard) -> T at the freshest enemy evidence — all
         squads collapse and finish. Preempts backoff/holds: v25's A/B showed
         spread holders sitting 1-2 kills from the wipe for whole halves, and a
         GV21 draw pays -1 exactly like a loss, so committing here risks nothing.
      4. Mid-push squad LOST a member (presence went stale while we're past the
         rally line) -> H at our position stepped back toward home: hold the
         ground we gained instead of feeding the enemy 1-by-1 (lives>captures).
      5. Defaults by squad: A/B hold their side chokes, C pushes mid.
    An existing order is kept until its rule stops applying (hysteresis via the
    rebroadcast cadence; rules are ordered so upgrades preempt defaults).
    """
    if leader_of(belief.seat) != belief.seat or belief.self_xy is None:
        return
    team = belief.team
    assert team is not None
    tick = belief.tick
    name, _seats = squad_of(belief.seat)

    goal: str
    pos: tuple[int, int]
    if belief.own_flag_stolen and (
        belief.own_flag_thief_pos is not None or belief.thief_fix is not None
    ):
        goal = "T"
        pos = belief.own_flag_thief_pos or belief.thief_fix[0]
    elif belief.carrier_fix is not None or (
        not belief.enemy_flag_on_pedestal
        and belief.enemy_flag_pos is not None
        and not belief.i_carry_enemy_flag
    ):
        goal = "F"
        pos = belief.carrier_fix[0] if belief.carrier_fix else belief.enemy_flag_pos
    elif wipe_in_reach(belief):
        # 3 (v26 convert): finish it — all squads hunt the freshest enemy fix.
        goal = "T"
        pos = convert_hunt_point(belief)
        if belief.order is None or belief.order[0] != "T":
            belief.convert_events += 1
    elif (
        past_rally(team, belief.self_xy[0])
        and squadmates_alive(belief) < squad_size(belief.seat) - 1
    ):
        # 3: we're committed forward and at least one mate is down/silent.
        goal = "H"
        pos = _home_step(team, belief.self_xy, BACKOFF_STEP_PX)
        if belief.order is None or belief.order[0] != "H":
            belief.backoff_events += 1
    else:
        # Defaults (v24): the two 3-person squads HOLD the two side lanes on our
        # choke line (top for A, bottom for B — sectors watch the approaches);
        # the 2-person C squad PUSHES the middle. Side-holds anchor the field
        # and punish flanking blitzes; C probes and creates flag pressure.
        if name == "A":
            goal, pos = "H", (CHOKE_X[team], SQUAD_SIDE_HOLD_Y_TOP)
        elif name == "B":
            goal, pos = "H", (CHOKE_X[team], SQUAD_SIDE_HOLD_Y_BOTTOM)
        else:  # C: push the middle
            goal, pos = "P", (617, 329)

    if belief.order is None or belief.order[0] != goal or belief.order[1] != pos:
        belief.order = (goal, pos, tick)
        belief.order_source = "leader"


def decay_hold_point(belief: Belief) -> tuple[int, int]:
    """Where a member whose ORDER went stale should back off to and hold (v24):
    its own position stepped toward home — the same posture as a squad losing a
    member. A stale order means the leader is dead or out of earshot; without
    coordination, holding beats pushing (lives > captures).

    The step applies only FORWARD of the rally line; behind it we hold in place —
    otherwise repeated decays (leader stays dead) would creep us all the way to
    our own wall."""
    assert belief.self_xy is not None and belief.team is not None
    if past_rally(belief.team, belief.self_xy[0]):
        return _home_step(belief.team, belief.self_xy, BACKOFF_STEP_PX)
    return belief.self_xy


def rejoin_target(belief: Belief) -> tuple[int, int] | None:
    """Where a dead agent should regroup on respawn: the freshest squadmate
    position we know (ping table has no positions — use identity-tagged teammate
    tracks), else our own last position stepped toward home."""
    my_squad = set(squad_of(belief.seat)[1]) - {belief.seat}
    best: tuple[int, int] | None = None
    best_tick = -1
    for t in belief.teammate_tracks:
        if t.identity in my_squad and t.last_tick > best_tick:
            best_tick = t.last_tick
            best = t.pos
    if best is not None:
        return best
    if belief.self_xy is not None and belief.team is not None:
        return _home_step(belief.team, belief.self_xy, BACKOFF_STEP_PX * 2)
    return None


def in_squad_contact(belief: Belief) -> bool:
    """Rejoin exit test: a squadmate confirmed near us (badge sighting within
    contact range, or a fresh ping placing one nearby via presence freshness +
    any teammate visibly close)."""
    assert belief.self_xy is not None
    sx, sy = belief.self_xy
    my_squad = set(squad_of(belief.seat)[1]) - {belief.seat}
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
    "past_rally",
    "rally_line_x",
    "rank_of",
    "rejoin_target",
    "sector_offset_brads",
    "separation_bias",
    "should_wait_for_squad",
    "spread_point",
    "squad_of",
    "squad_size",
    "squadmates_alive",
    "update_presence",
    "wipe_in_reach",
]
