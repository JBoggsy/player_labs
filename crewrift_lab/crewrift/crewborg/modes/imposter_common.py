"""Shared geometry + crew helpers for the imposter Pretend FSM (design §7.2).

Pretend's follow / recover / wander / fake-task states lean on the same primitives:
locating the room a point sits in, the starting room, task-station anchors, snapping
to a reachable nav node, and the set of crewmates visible this tick. They live here
so the mode stays focused on its state machine.
"""

from __future__ import annotations

import os

from crewrift.crewborg.map.types import Room
from crewrift.crewborg.types import Belief, Intent, PlayerRecord

Point = tuple[int, int]

# One task-time hold (≈ the 72-tick task progress in sim.nim) — how long a crewmate
# takes to complete a task. The fake-task duration Pretend used; now the WATCH
# camouflage hold (see docs/designs/watch-camouflage.md).
FAKE_TASK_TICKS = 72

# Consecutive kill-ready Playing ticks of a zero-length navigation target (or idle)
# before the parked guard forces a state change. ~0.5 s at 24 Hz: tolerant of the
# movement controller's coast-to-rest ticks, but orders of magnitude below the
# measured multi-hundred-tick ready-state parks. Env-tunable for sweeps.
PARKED_GUARD_TICKS = 12

# A navigation target within this radius (px) of self is a zero-length route — the
# action layer has nothing to do and the agent stands still.
PARKED_ARRIVE_RADIUS_SQ = 24**2


def parked_guard_ticks() -> int:
    raw = os.environ.get("CREWBORG_PARKED_GUARD_TICKS")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return PARKED_GUARD_TICKS


def would_park(belief: Belief, self_xy: Point, intent: Intent) -> bool:
    """Whether this tick has the parked shape the guard counts: a kill-ready
    Playing tick whose intent is idle or a zero-length navigate."""

    return (
        belief.phase == "Playing"
        and belief.self_kill_ready
        and (
            intent.kind == "idle"
            or (intent.kind == "navigate_to" and intent.point is not None
                and dist2(self_xy, intent.point) <= PARKED_ARRIVE_RADIUS_SQ)
        )
    )


class ParkedGuard:
    """Escape hatch against kill-ready parking (the standing "idling is dangerous"
    lab principle: every idle needs an escape).

    A kill-ready imposter standing still is a wasted kill window — the exact
    signature of the measured ready-state parks (2026-07-02 movement diagnosis).
    Modes that navigate while an imposter can be kill-ready (Search, Recon) run
    their outgoing intent through :meth:`fires`; when it reports True the mode must
    force a state change to a *different* target rather than keep emitting the
    same zero-length route. Hunt is deliberately not guarded: its in-range hold
    ("lying in wait") already escapes via the urgency relaxation, and Evade can't
    be kill-ready (our own kill just reset the cooldown).
    """

    def __init__(self) -> None:
        self._streak = 0

    def fires(self, belief: Belief, self_xy: Point, intent: Intent, *, intentional_idle: bool = False) -> bool:
        """True when the guard trips: ``parked_guard_ticks()`` consecutive
        kill-ready Playing ticks whose intent is idle or a zero-length navigate.
        Resets its streak whenever the condition breaks (or after firing).

        ``intentional_idle`` exempts a *deliberate* idle — Search's WATCH
        camouflage (a fake task with its own escapes; see
        docs/designs/watch-camouflage.md) — from accruing: the guard exists to
        catch unintentional parking, not to defeat intentional blending. The
        exemption should be unreachable on a kill-ready tick (camo's kill-soon
        escape ends it first); Search traces ``camo_guard_exempt`` if not.
        """

        parked_now = would_park(belief, self_xy, intent)
        if parked_now and intentional_idle:
            self._streak = 0
            return False
        if not parked_now:
            self._streak = 0
            return False
        self._streak += 1
        if self._streak < parked_guard_ticks():
            return False
        self._streak = 0
        return True


def self_xy(belief: Belief) -> Point | None:
    if belief.self_world_x is None or belief.self_world_y is None:
        return None
    return belief.self_world_x, belief.self_world_y


def dist2(a: Point, b: Point) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def in_rect(point: Point, rect: Room) -> bool:
    return rect.x <= point[0] < rect.x + rect.w and rect.y <= point[1] < rect.y + rect.h


def room_containing(belief: Belief, point: Point) -> Room | None:
    """The room whose rect strictly contains ``point``, or ``None`` (e.g. a hallway)."""

    rooms = belief.map.rooms if belief.map is not None else ()
    for room in rooms:
        if in_rect(point, room):
            return room
    return None


def starting_room(belief: Belief) -> Room | None:
    """The room containing the spawn (``home``); never a fake-task location."""

    if belief.map is None:
        return None
    home = (belief.map.home.x, belief.map.home.y)
    return room_containing(belief, home)


def reachable_point(belief: Belief, point: Point) -> Point:
    """Snap ``point`` to the nearest reachable nav node (a stable, walkable goal)."""

    if belief.nav is None:
        return point
    cell = belief.nav.nearest_reachable_node(*point)
    if cell is None:
        return point
    return belief.nav.node_point[cell]


def task_point(belief: Belief, index: int) -> Point:
    """A task station's baked reachable anchor, or its centre before the graph exists."""

    if belief.nav is not None:
        anchor = belief.nav.task_anchor(index)
        if anchor is not None:
            return anchor
    task = belief.map.tasks[index]
    return task.center.x, task.center.y


def visible_crew(belief: Belief) -> list[PlayerRecord]:
    """Live non-teammate players seen this very tick (the candidates to follow)."""

    return [
        e
        for e in belief.roster.values()
        if e.last_seen_tick == belief.last_tick
        and e.color not in belief.teammate_colors
        and e.life_status != "dead"
    ]
