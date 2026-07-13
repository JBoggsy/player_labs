"""Shared beacon runtime types — the six AgentRuntime type parameters.

``Observation`` (raw SDK world) -> ``CtfState`` (per-frame percept) -> ``Belief``
(folded state) -> ``ActionState`` (press bookkeeping) -> ``Intent`` (symbolic
request) -> ``Command`` (button mask).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from players.player_sdk import SpriteWorld

Team = Literal["red", "blue"]


@dataclass(frozen=True)
class Observation:
    """Raw SDK world plus the bridge frame number."""

    world: SpriteWorld
    frame: int


@dataclass(frozen=True)
class Enemy:
    """A visible enemy player resolved from its labeled sprite this frame."""

    pos: tuple[int, int]
    facing: str  # "left" | "right"


@dataclass(frozen=True)
class CtfState:
    """Per-frame, label-only CTF percept (no memory)."""

    ready: bool
    self_xy: tuple[int, int] | None  # None => dead / not yet visible
    self_facing: str | None
    observed_aim: int | None  # aim brads read back from the aim-dot sprite, if seen
    fire_ready: bool
    enemies: tuple[Enemy, ...]
    teammates: tuple[Enemy, ...]  # visible same-team players (for the friendly-fire gate)
    # Flag world-state, always observable (pedestals never fog):
    i_carry_enemy_flag: bool
    enemy_flag_on_pedestal: bool
    enemy_flag_pos: tuple[int, int] | None  # where the enemy flag is, if visible
    own_flag_stolen: bool
    own_flag_thief_pos: tuple[int, int] | None  # a live thief fix, when in view


Role = Literal["attacker", "defender"]


@dataclass
class Belief:
    """Long-lived state folded across frames."""

    team: Team | None = None
    seat: int = 0  # slot // 2, in 0..7 — fixes the role and defensive hold point
    role: Role = "attacker"
    hold_point: tuple[int, int] | None = None  # defender's assigned hold cell
    self_xy: tuple[int, int] | None = None
    alive: bool = False
    # Aim tracking: our best estimate of the current aim angle in brads. Seeded from
    # the spawn aim, resynced to observed_aim whenever the aim-dot is visible, and
    # dead-reckoned by the rotation we commanded last frame otherwise.
    aim_brads: int = 0
    fire_ready: bool = False
    enemies: tuple[Enemy, ...] = ()
    teammates: tuple[Enemy, ...] = ()
    # Flag state (folded, but effectively per-frame since flags never fog):
    i_carry_enemy_flag: bool = False
    enemy_flag_on_pedestal: bool = True
    enemy_flag_pos: tuple[int, int] | None = None
    own_flag_stolen: bool = False
    own_flag_thief_pos: tuple[int, int] | None = None
    # Navigation:
    nav_goal: tuple[int, int] | None = None
    nav_path: list[tuple[int, int]] | None = None
    nav_cursor: int = 0
    nav_last_xy: tuple[int, int] | None = None
    nav_stuck_ticks: int = 0
    # Lighthouse aim sweep phase: current signed offset from the threat axis, in
    # brads, and the sweep direction (+1 / -1). Reset while dead.
    sweep_offset: int = 0
    sweep_dir: int = 1


@dataclass
class ActionState:
    """Mutable action bookkeeping across frames."""

    # Rotation we commanded last frame (+1 CCW via B, -1 CW via Select, 0 none),
    # used to dead-reckon the aim estimate when the aim-dot isn't visible.
    last_rot: int = 0
    # Edge-triggered fire: A must be released for a frame between shots, so a held
    # trigger doesn't re-lock aim every tick.
    a_held: bool = False


IntentKind = Literal["navigate_to", "hold"]


@dataclass(frozen=True)
class Intent:
    """A symbolic movement request; combat/aim are resolved as an overlay."""

    kind: IntentKind
    point: tuple[int, int] | None = None
    reason: str = ""


@dataclass(frozen=True)
class Command:
    """Bridge command produced by action resolution."""

    held_mask: int = 0
    chat: str | None = None


__all__ = [
    "ActionState",
    "Belief",
    "Command",
    "CtfState",
    "Enemy",
    "Intent",
    "IntentKind",
    "Observation",
    "Role",
    "Team",
]
