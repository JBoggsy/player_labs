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
    """A visible player (enemy or teammate) resolved from its labeled sprite this frame.

    ``identity`` is the player's nameplate seat index (0=alpha .. 7=theta, from the
    0.7.69 identity badges — slot order within team, i.e. exactly our seat notion),
    or None when no badge resolved (badge fog-gated separately, association miss)."""

    pos: tuple[int, int]
    facing: str  # "left" | "right"
    identity: int | None = None


@dataclass
class HeardImpact:
    """One deduplicated heard sound event (belief.py folds ring sightings).

    A ring sprite persists ~12 ticks, so the same event is sighted many frames;
    belief matches sightings to existing events by position (rings are jittered
    but STABLE per event) and keeps `first_tick` as the event time. Team-anonymous:
    the ring never says who fired."""

    kind: str  # "shot" | "grenade"
    pos: tuple[int, int]  # ring centre (true landing ±20px jitter)
    first_tick: int  # when we first heard it
    last_tick: int  # most recent frame the ring was still in view


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
    #: nameplate identity (0=alpha..7=theta) from the 0.7.69 badges; None if the
    #: track has never had a badge resolve. Sticky: kept once known.
    identity: int | None = None


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
    # Items (v10): fog-gated pickup sightings + our own overhead-marker state.
    visible_items: tuple[tuple[str, tuple[int, int]], ...] = ()  # (kind, pos)
    # Hearing (v16): sound rings in this frame — "shot impact" / "grenade sound"
    # sprites. Audible map-wide through walls/fog, jittered ±20px, team-anonymous.
    # Raw per-frame positions; belief dedups them into HeardImpact events.
    heard_impacts: tuple[tuple[str, tuple[int, int]], ...] = ()  # (kind, pos)
    # Chat (v18): shout bubbles heard this frame, parsed from their sprite label
    # ``<team> shout <address>: <text>`` — (team, address, text, bubble pos).
    heard_shouts: tuple[tuple[str, str, str, tuple[int, int]], ...] = ()
    hp_pips: int | None = None  # our "hp N/3" bar segments; None = bar not resolved
    i_have_grenade: bool = False
    i_have_shield: bool = False
    i_have_arc: bool = False
    # Team scoreboard (v26): both teams' aggregate (kills, deaths) from the
    # top-center "team score RED k/d" labels — fog-independent, every frame.
    own_team_score: tuple[int, int] | None = None
    enemy_team_score: tuple[int, int] | None = None


Role = Literal["attacker", "defender"]

ItemKind = Literal["grenade", "shield", "arc", "medkit"]


@dataclass
class ItemSpawn:
    """Belief about one fixed item spawn point (items.py owns the spawn table).

    Optimistic-by-default: a spawn is believed ``present`` unless we recently
    OBSERVED it empty, in which case ``absent_until`` backs off roughly one respawn
    interval before we try it again (we can't know when it was actually taken)."""

    kind: ItemKind
    pos: tuple[int, int]
    present: bool = True
    absent_until: int = 0  # believed-absent until this tick when present=False
    last_seen: int = -1


@dataclass(frozen=True)
class PostClaim:
    """A teammate's fresh K claim on one nav-cell-centred fighting post."""

    seat: int
    cell: tuple[int, int]
    tick: int


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
    # the spawn aim, dead-reckoned by the rotation we commanded last frame, calibrated
    # against the self sprite's 16-step rotation readback (belief.py: boundary-crossing
    # calibration to ~±3 brads, coarse resync for large drift).
    aim_brads: int = 0
    # The previous frame's observed 16-step aim readback (brads, a multiple of 16),
    # for boundary-crossing calibration. None until first observed.
    prev_observed_aim: int | None = None
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
    # True when this tick's duck was triggered by a HEARD impact (no seen track) —
    # the v16 activation bit, reset alongside micro each tick.
    heard_duck: bool = False
    # Items (v10): fixed-spawn belief table + our own carried/hp state (perception).
    item_spawns: list[ItemSpawn] = field(default_factory=list)
    hp_pips: int | None = None  # our hp bar segments 1..3; None = unresolved
    # Team scoreboard (v26): both teams' aggregate (kills, deaths), folded from the
    # fog-independent "team score" labels. enemy_lives_left derives from deaths:
    # 8 players x 3 lives - enemy deaths (exact while all 16 slots stay connected).
    own_team_score: tuple[int, int] | None = None
    enemy_team_score: tuple[int, int] | None = None
    i_have_grenade: bool = False
    i_have_shield: bool = False
    i_have_arc: bool = False
    # Hearing (v16): deduplicated sound events, freshest last. Folded from
    # percept.heard_impacts; expire HEARD_TTL_TICKS after last_tick.
    heard_events: list[HeardImpact] = field(default_factory=list)
    # Under fire (v18): fresh impacts landed near us recently (set by belief).
    under_fire: bool = False
    # Chat (v18) — send-side bookkeeping (chat.choose_shout):
    chat_last_sent_tick: int = -10_000
    chat_enemy_armed: bool = True  # edge trigger for E; re-arms after clear vision
    chat_last_enemy_tick: int = -10_000
    chat_enemy_seen_tick: int = -10_000
    chat_sent_counts: dict[str, int] = field(default_factory=dict)
    # Chat (v18) — receive-side decoded state:
    #: teammate carrier fix from a C shout: (pos, heading octant, tick heard).
    carrier_fix: tuple[tuple[int, int], int, int] | None = None
    #: enemy thief fix from a T shout (or our own eyes): (pos, tick).
    thief_fix: tuple[tuple[int, int], int] | None = None
    #: teammate grenade landing zones to keep clear of: [(pos, tick heard)].
    grenade_warnings: list[tuple[tuple[int, int], int]] = field(default_factory=list)
    chat_heard_counts: dict[str, int] = field(default_factory=dict)
    #: bubble dedup: sender address -> (text, last tick processed). A bubble
    #: persists ~3s, so the same shout is in frame ~72 times; process it once.
    chat_processed: dict[str, tuple[str, int]] = field(default_factory=dict)
    #: our own last-sent payload (to skip our own bubble coming back at us).
    chat_last_sent_text: str | None = None
    # Squads (v19): wait-gate state + activation counters (traced).
    squad_wait_since: int = -1  # tick we started holding at the rally; -1 = not waiting
    squad_wait_ticks: int = 0  # cumulative ticks spent waiting for buddies
    squad_cohesion_ticks: int = 0  # cumulative ticks a formation bias was applied
    # Squad command (v22) — the order I currently obey: (goal letter, target pos,
    # tick set). Set by my own leader logic (if I lead) or a heard O message.
    order: tuple[str, tuple[int, int], int] | None = None
    #: How the current order arrived (v27 tracing): "leader" (own lead_squad rule),
    #: "heard" (a squadmate leader's O message), "decay" (stale order -> self-issued
    #: backoff-hold), "convert" (stale order + wipe in reach -> self-issued hunt).
    order_source: str | None = None
    #: presence table: squadmate seat -> last tick we confirmed them alive (badge
    #: sighting or heard ping/order). Leaders read this for strength estimates.
    presence: dict[int, int] = field(default_factory=dict)
    #: my last presence ping tick (send-side cadence).
    last_ping_tick: int = -10_000
    #: leader bookkeeping: last order broadcast tick + the goal it carried.
    last_order_sent_tick: int = -10_000
    #: rejoin (respawn discipline): where to regroup after respawn, or None.
    rejoin_point: tuple[int, int] | None = None
    rejoin_until: int = -1  # give-up deadline (tick); -1 = not rejoining
    # v22 activation counters (traced).
    orders_sent: int = 0
    orders_heard: int = 0
    pings_sent: int = 0
    pings_heard: int = 0
    backoff_events: int = 0
    rejoin_ticks: int = 0
    convert_events: int = 0  # v26: times a leader flipped into the convert hunt
    converting: bool = False  # v29: currently in the standalone convert-hunt rung
    # Battle-plan interpreter (v30) — per-bot phase pointer (no comms; the shared
    # tick clock + shared milestones keep the team roughly aligned).
    plan_phase: int = 0
    plan_phase_tick: int = 0        # tick my current phase began
    plan_milestone_hit: bool = False  # last advance was milestone (vs timeout)
    plan_fell_back: bool = False    # hold-order fallback tripped this phase
    plan_advances: int = 0          # cumulative phase advances (traced)
    plan_buddy_wait_ticks: int = 0  # v31: ticks spent buddy-waiting this phase
    plan_buddy_waiting: bool = False  # v31: currently paused for a group-mate
    # Posts: one latched covered sightline near the current tactical waypoint.
    # `post_active` is per-tick: higher strategy rungs leave it false, which
    # suspends both K claims and post-facing without destroying the reusable latch.
    post_active: bool = False
    post_cell: tuple[int, int] | None = None
    post_direction: int | None = None
    post_center: tuple[int, int] | None = None
    post_mode: str | None = None  # "push" | "hold"
    post_context: str | None = None  # "plan" | "order" | "static_hold"
    # Score components are retained for activation tracing and A/B diagnosis.
    post_score: float | None = None
    post_reach: float | None = None
    post_cover: float | None = None
    post_stance: float | None = None
    post_danger: float | None = None
    post_threat_source: str | None = None
    post_claim_source: str | None = None
    # Dwell affects re-selection only. Plan milestones observe post arrival
    # directly and never wait for this counter.
    post_selected_tick: int = -1
    post_last_evaluated_tick: int = -1
    post_settled_ticks: int = 0
    post_ticks_total: int = 0
    # Same-team K claims, keyed by claimant seat; stale entries decay on a clock.
    post_claims: dict[int, PostClaim] = field(default_factory=dict)
    post_last_claim_sent_tick: int = -10_000
    post_claims_sent: int = 0
    post_claims_heard: int = 0
    # Lead-aim activation state this tick, for tracing: brads of lead applied to the
    # snap aim (0 = no lead / target treated as stationary).
    lead_brads: int = 0
    # Grenade-throw state machine: ticks C has been held this charge (0 = idle), and
    # the landing point the current charge is aimed at.
    throw_charge_ticks: int = 0
    throw_target: tuple[int, int] | None = None


@dataclass
class ActionState:
    """Mutable action bookkeeping across frames."""

    # Rotation we commanded last frame (+1 CCW via B, -1 CW via Select, 0 none),
    # used to dead-reckon the aim estimate when the aim-dot isn't visible.
    last_rot: int = 0
    # Edge-triggered fire: A must be released for a frame between shots, so a held
    # trigger doesn't re-lock aim every tick.
    a_held: bool = False
    # Ticks left of the post-trigger movement freeze (v12): the bullet leaves
    # FIRE_WINDUP_TICKS after the pull FROM THE SHOOTER'S CURRENT POSITION, so
    # moving during the windup shifts our own ray off the target.
    fire_hold_ticks: int = 0


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
    "HeardImpact",
    "Intent",
    "IntentKind",
    "ItemKind",
    "ItemSpawn",
    "Observation",
    "PlayerTrack",
    "PostClaim",
    "Role",
    "Team",
]
