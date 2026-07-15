"""Shared beacon runtime types — the six AgentRuntime type parameters.

``Observation`` (raw SDK world) -> ``CtfState`` (per-frame percept) -> ``Belief``
(folded state) -> ``ActionState`` (press bookkeeping) -> ``Intent`` (symbolic
request) -> ``Command`` (button mask).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from players.player_sdk import SpriteWorld

Team = Literal["red", "blue"]


@dataclass(frozen=True)
class Observation:
    """Raw SDK world plus the bridge frame number."""

    world: SpriteWorld
    frame: int


@dataclass(frozen=True)
class Enemy:
    """A visible player (enemy or teammate) resolved from its labeled sprite this frame."""

    pos: tuple[int, int]
    facing: str  # "left" | "right"


@dataclass
class PlayerTrack:
    """Last-seen memory of one other player, folded across frames (belief.py).

    Tracks outlive the sighting: a player that leaves the cone keeps its track (with
    the position/heading we last saw) until ``TRACK_TTL_TICKS`` stale. Not gated on
    yet — belief-state groundwork for pursuit / exposure-aware routing."""

    pos: tuple[int, int]
    last_tick: int  # tick of the most recent sighting
    facing: str  # "left" | "right" — sprite heading at last sighting
    #: px/tick, EMA-smoothed; None until the track has two sightings close enough in
    #: time to difference (frames_seen >= 2 with a small tick gap).
    vel: tuple[float, float] | None = None
    frames_seen: int = 1


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
    tick: int = 0  # current runtime tick, for aging tracks at decision time
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
    # Player tracks + danger field (folded in belief.py; nothing gates on them yet):
    enemy_tracks: list[PlayerTrack] = field(default_factory=list)
    teammate_tracks: list[PlayerTrack] = field(default_factory=list)
    #: Danger scalar field over the nav grid, float32 [GRID_H, GRID_W] in 0..1 —
    #: stamped hot by visible enemies, spreading at DANGER_DIFFUSION_FACTOR x max
    #: player speed, cooling with a half-life. Initialized hot on the enemy half.
    danger: np.ndarray | None = None
    #: Fractional nav-cells of danger spread owed; dilate one ring per whole unit.
    danger_spread_carry: float = 0.0
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
    # Active combat-micro state this tick, for activation tracing: "duck" / "peek" /
    # None. Behavior changes MUST be observable — a null A/B without activation
    # counts can't distinguish "never fired" from "fired and didn't help".
    micro: str | None = None


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
    "PlayerTrack",
    "Role",
    "Team",
]
