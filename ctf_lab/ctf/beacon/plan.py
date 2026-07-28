"""Battle-plan interpreter (v30): execute a co-general plan as OBJECTIVES.

Loads a battle plan (battle_plans/SCHEMA.md — authored in tools/plan_editor.html)
and turns it into per-tick strategy intents. The governing principle: **the plan
supplies goals, never motion**. A plan order becomes the same ``navigate_to`` /
``hold`` intent the static role split emits, at the same rung altitude — so every
existing skill still applies on the way: A* with the danger cost field, peek/duck
micro, cover routing, the combat overlay, windup freeze, item detours. And every
EMERGENCY rung stays above the plan: carrying the flag, intercepting a thief,
escorting a carrier, grabbing a medkit when hurt, and the convert trigger all
preempt plan orders. The plan is what a bot does when nothing more urgent is
happening — goalposts, not a death march.

Phase advancement is per-bot (no comms protocol) and never deadlocks:
  * MILESTONE — I reached my group's target for this phase (arrive radius), or
  * TIMEOUT — the phase has run BEACON_PLAN_PHASE_TIMEOUT_TICKS (the v19 rally-
    gate lesson: any stage gate must have a clock fallback), and
  * the NEXT phase's entry tag, when machine-evaluable (tick>=N, enemy_lives<=N,
    own_deaths>=N), must also hold — un-evaluable tags (presence(...) needs the
    squad presence table; prose-only) gate on milestone/timeout alone.
Bots advance independently; the shared tick clock and shared milestones keep
them roughly aligned, and divergence self-heals at the next timeout.

Mirroring: plans are authored red-frame; ``poi.resolve(loc, team)`` flips for
blue, so one plan file drives both sides.

Not yet executed (traced only): ``watch`` orders (aim-bias hooks come later)
and multi-group coordination conditions. ``fallback`` on a hold IS live: under
fire with 2+ enemies visible while holding, the group's target becomes the
fallback location for the rest of the phase.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ctf.beacon import poi
from ctf.beacon.config import (
    PLAN_ARRIVE_PX,
    PLAN_PHASE_TIMEOUT_TICKS,
)
from ctf.beacon.types import Belief, Team

#: Plan search path: baked into the image (beacon/plans/) first, then the lab's
#: live battle_plans/ dir (local `uv run` from the repo).
_PLAN_DIRS = (
    Path(__file__).resolve().parent / "plans",
    Path(__file__).resolve().parents[2] / "battle_plans",
)


@dataclass(frozen=True)
class Order:
    group: str
    kind: str                      # "move" | "hold" | "watch"
    target: object                 # POI name or {"x","y"} (red frame)
    via: tuple = ()
    facing: object = None
    fallback: object = None


@dataclass
class PlanBook:
    """One loaded plan + per-phase lookup tables."""

    name: str
    doc: dict
    phases: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls, name: str) -> "PlanBook | None":
        return _load_book(name)

    def groups_at(self, phase_idx: int) -> dict[str, list[int]]:
        """Group -> seats after applying splits through phase_idx (editor semantics)."""
        g = {k: list(v) for k, v in (self.doc.get("groups") or {}).items()}
        for i in range(min(phase_idx, len(self.phases) - 1) + 1):
            for parent, kids in (self.phases[i].get("splits") or {}).items():
                if parent in g:
                    del g[parent]
                    for k, seats in kids.items():
                        g[k] = list(seats)
        return g

    def group_of(self, seat: int, phase_idx: int) -> str | None:
        for name, seats in self.groups_at(phase_idx).items():
            if seat in seats:
                return name
        return None

    def orders_for(self, group: str, phase_idx: int) -> list[Order]:
        if not (0 <= phase_idx < len(self.phases)):
            return []
        out = []
        for o in self.phases[phase_idx].get("orders") or []:
            if o.get("group") != group:
                continue
            out.append(Order(
                group=group,
                kind=o.get("kind", "move"),
                target=o.get("to") if o.get("to") is not None else o.get("at"),
                via=tuple(o.get("via") or ()),
                facing=o.get("facing"),
                fallback=o.get("fallback"),
            ))
        return out

    def primary_order(self, group: str, phase_idx: int) -> Order | None:
        """The order that drives movement: move beats hold beats watch."""
        orders = self.orders_for(group, phase_idx)
        for kind in ("move", "hold"):
            for o in orders:
                if o.kind == kind:
                    return o
        return None


_BOOK_CACHE: dict[str, "PlanBook | None"] = {}


def _load_book(name: str) -> "PlanBook | None":
    if name not in _BOOK_CACHE:
        book = None
        for d in _PLAN_DIRS:
            p = d / f"{name}.json"
            if p.exists():
                doc = json.loads(p.read_text())
                book = PlanBook(name=doc.get("name", name), doc=doc,
                                phases=doc.get("phases", []))
                break
        _BOOK_CACHE[name] = book
    return _BOOK_CACHE[name]


_TAG_RE = re.compile(r"^\s*(tick|enemy_lives|own_deaths)\s*(<=|>=)\s*(\d+)\s*$")


def entry_tag_holds(belief: Belief, phase: dict) -> bool | None:
    """Evaluate a phase's entry tag. True/False when evaluable, None otherwise
    (absent tag, prose-only, or a signal we can't read — e.g. presence())."""
    tag = (phase.get("entry") or {}).get("tag")
    if not tag:
        return None
    m = _TAG_RE.match(tag)
    if not m:
        return None
    signal, op, num = m.group(1), m.group(2), int(m.group(3))
    if signal == "tick":
        val = belief.tick
    elif signal == "enemy_lives":
        from ctf.beacon import squads
        lives = squads.enemy_lives_left(belief)
        if lives is None:
            return None
        val = lives
    else:  # own_deaths
        if belief.own_team_score is None:
            return None
        val = belief.own_team_score[1]
    return val <= num if op == "<=" else val >= num


def _arrived(belief: Belief, target_xy: tuple[int, int]) -> bool:
    if belief.self_xy is None:
        return False
    dx = belief.self_xy[0] - target_xy[0]
    dy = belief.self_xy[1] - target_xy[1]
    return dx * dx + dy * dy <= PLAN_ARRIVE_PX * PLAN_ARRIVE_PX


def advance(belief: Belief, book: PlanBook) -> None:
    """Per-tick phase bookkeeping: advance my phase pointer when my milestone is
    hit (or the phase times out) AND the next phase's entry tag (if evaluable)
    holds. Monotonic; never blocks forever (timeout is unconditional-eligible)."""
    if belief.plan_phase >= len(book.phases) - 1:
        return  # terminal phase: ride it out
    team: Team = belief.team or "red"
    group = book.group_of(belief.seat, belief.plan_phase)
    order = book.primary_order(group, belief.plan_phase) if group else None

    milestone = False
    if order is not None:
        target = poi.resolve(order.target, team)
        milestone = target is not None and _arrived(belief, target)
    timeout = belief.tick - belief.plan_phase_tick >= PLAN_PHASE_TIMEOUT_TICKS

    if not (milestone or timeout):
        return
    nxt = entry_tag_holds(belief, book.phases[belief.plan_phase + 1])
    if nxt is False and not timeout:
        return  # tagged condition not met yet; timeout still overrides eventually
    belief.plan_phase += 1
    belief.plan_phase_tick = belief.tick
    belief.plan_milestone_hit = milestone
    belief.plan_fell_back = False
    belief.plan_advances += 1


def current_objective(belief: Belief, book: PlanBook) -> tuple[str, tuple[int, int], object] | None:
    """My (kind, target_xy, order) for this tick, fallback-adjusted; None when
    the plan has nothing for my seat (fall through to the static role split)."""
    team: Team = belief.team or "red"
    group = book.group_of(belief.seat, belief.plan_phase)
    if group is None:
        return None
    order = book.primary_order(group, belief.plan_phase)
    if order is None:
        return None
    target = order.target
    # Live contingency: a pressed hold retreats to its fallback for the phase.
    if (
        order.kind == "hold"
        and order.fallback is not None
        and belief.under_fire
        and len(belief.enemies) >= 2
    ):
        belief.plan_fell_back = True
    if order.kind == "hold" and belief.plan_fell_back and order.fallback is not None:
        target = order.fallback
    xy = poi.resolve(target, team)
    if xy is None:
        return None
    return (order.kind, xy, order)


__all__ = ["PlanBook", "Order", "advance", "current_objective", "entry_tag_holds"]
