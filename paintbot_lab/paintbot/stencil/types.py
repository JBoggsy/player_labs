"""Shared stencil runtime types.

``Observation`` (raw SDK world) -> ``PaintState`` (per-frame percept) -> ``Belief``
(folded state) -> ``ActionState`` (press bookkeeping) -> ``Intent`` (symbolic
request) -> ``Command`` (button mask).

Multi-team: ``Team`` is a color token from red/blue/green/yellow; the active
prefix (2 or 4 colors) comes off the wire (``game teams`` marker). "Enemy" means
every active color that isn't ours — 4-team play is pure FFA.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import numpy as np

from players.player_sdk import SpriteWorld

if TYPE_CHECKING:
    from paintbot.stencil.worldmap import WorldMap

#: A team color token: "red" | "blue" | "green" | "yellow".
Team = str


@dataclass(frozen=True)
class Observation:
    """Raw SDK world plus the bridge frame number."""

    world: SpriteWorld
    frame: int


@dataclass(frozen=True)
class Enemy:
    """A visible player resolved from its labeled sprite this frame.

    ``color`` is the player's team color token. ``identity`` is the nameplate
    seat index (0=alpha..7=theta, slot order within team), or None when no badge
    resolved."""

    pos: tuple[int, int]
    facing: str  # "left" | "right"
    color: Team = "red"
    identity: int | None = None
    #: Ordinal lit-bar segments from ``hp <lit>/<total>``; includes shield health.
    hp_segments: int | None = None
    #: A visible ``shield carried`` marker is attached to this player.
    shielded: bool = False


@dataclass
class HeardImpact:
    """One deduplicated heard sound event (belief.py folds ring sightings)."""

    kind: str  # "shot" | "grenade"
    pos: tuple[int, int]  # ring centre (true landing ±20px jitter)
    first_tick: int
    last_tick: int


@dataclass
class PlayerTrack:
    """Last-seen memory of one other player, folded across frames (belief.py)."""

    pos: tuple[int, int]
    last_tick: int
    facing: str
    color: Team = "red"
    vel: tuple[float, float] | None = None
    frames_seen: int = 1
    identity: int | None = None
    hp_segments: int | None = None
    shielded: bool = False


@dataclass(frozen=True)
class TargetRef:
    """Cross-frame handle for one enemy."""

    identity: int | None
    pos: tuple[int, int]


@dataclass(frozen=True)
class FocusClaim:
    """The one first-heard local focus-fire claim this bot currently recognizes."""

    claimant_seat: int
    target: TargetRef
    first_tick: int
    refreshed_tick: int
    last_seen_tick: int
    enemy_deaths_at_last_seen: int | None


@dataclass(frozen=True)
class TargetCandidate:
    """One visible enemy plus the per-shooter geometry needed for scoring."""

    enemy: Enemy
    target: TargetRef
    aim_pos: tuple[int, int]
    lead_brads: int
    distance_px: float
    aim_cost: float
    line_clear: bool
    teammate_blocked: bool
    shootable: bool


@dataclass(frozen=True)
class TargetScore:
    """A target's weighted total plus normalized, traceable score terms."""

    candidate: TargetCandidate
    score: float
    wound: float
    range_band: float
    claim: float
    shootability: float
    aim_cost: float
    shield: float


@dataclass(frozen=True)
class HeartState:
    """One color's heart, as read from the flag sprites this frame.

    ``planted`` — resting on its pedestal (position known; pedestals never fog).
    ``carried_pos`` — where a carried heart sprite is visible, else None.
    ``in_play`` — False once the heart is captured/retired (team eliminated):
    neither sprite exists AND the team's lives are exhausted."""

    planted: bool
    pos: tuple[int, int] | None
    carried_pos: tuple[int, int] | None


@dataclass(frozen=True)
class PaintState:
    """Per-frame, label-only percept (no memory)."""

    ready: bool
    self_xy: tuple[int, int] | None  # None => dead / not yet visible
    self_color: Team | None  # our color as confirmed by a self sprite
    self_facing: str | None
    observed_aim: int | None
    fire_ready: bool
    enemies: tuple[Enemy, ...]
    teammates: tuple[Enemy, ...]
    #: Per-color heart state (all active colors, including our own).
    hearts: dict[Team, HeartState]
    #: Which enemy color's heart we are carrying, if any.
    i_carry_heart_of: Team | None
    # Episode parameters, present from the init snapshot on:
    game_teams: int | None = None  # 2 or 4, from the "game teams" marker
    map_size: tuple[int, int] | None = None  # exact map pixels, same marker
    #: Parsed endzone markers: color -> (shape, (x0, y0, x1, y1)).
    endzones: dict[Team, tuple[str, tuple[int, int, int, int]]] = field(
        default_factory=dict
    )
    #: Decoded walkability mask (bool [H, W]), when the sprite has arrived.
    walkability: np.ndarray | None = None
    #: One-time snappy decode + bool-mask conversion cost for that map.
    walkability_decode_ms: float = 0.0
    visible_items: tuple[tuple[str, tuple[int, int]], ...] = ()
    heard_impacts: tuple[tuple[str, tuple[int, int]], ...] = ()
    #: Shout bubbles heard this frame: (team color, sender address, text, pos).
    heard_shouts: tuple[tuple[str, str, str, tuple[int, int]], ...] = ()
    hp_pips: int | None = None
    i_have_grenade: bool = False
    i_have_shield: bool = False
    i_have_arc: bool = False
    #: Per-color aggregate (kills, deaths) from the team-score chips.
    team_scores: dict[Team, tuple[int, int]] = field(default_factory=dict)


Role = Literal["attacker", "defender"]

ItemKind = Literal["grenade", "shield", "arc", "medkit"]


@dataclass
class ItemSpawn:
    """Belief about one item spawn point, DISCOVERED from sightings.

    Paintbot item positions are per-map (the generator places them), so the
    table starts empty and grows as pickups are sighted; a discovered spawn is
    permanent for the episode (items respawn in place). ``present`` follows the
    optimistic model: present unless recently observed empty."""

    kind: ItemKind
    pos: tuple[int, int]
    present: bool = True
    absent_until: int = 0
    last_seen: int = -1


@dataclass(frozen=True)
class ItemOption:
    """One evaluated pickup opportunity relative to the current objective."""

    spawn: ItemSpawn
    anchor: tuple[int, int]
    anchor_kind: str
    route_to_item_px: float
    route_via_item_px: float
    direct_route_px: float
    detour_px: float
    threshold_px: float
    accepted: bool
    reason: str


@dataclass
class Belief:
    """Long-lived state folded across frames."""

    team: Team | None = None
    seat: int = 0  # slot // teams, in 0..7 — fixes the role and hold point
    slot: int = 0  # raw connection slot
    tick: int = 0
    role: Role = "attacker"
    hold_point: tuple[int, int] | None = None
    self_xy: tuple[int, int] | None = None
    alive: bool = False
    #: The episode's world model; None until the init markers + walkability
    #: sprite have all arrived (runtime builds it, belief consumes it).
    worldmap: "WorldMap | None" = None
    #: Active color tokens this episode (a prefix of TEAM_COLORS).
    colors: tuple[Team, ...] = ("red", "blue")
    #: Locked once a `self <color>` sprite confirms our real color.
    color_locked: bool = False
    #: The enemy color whose heart we are currently trying to steal.
    steal_target: Team | None = None
    # Aim tracking (dead-reckoned; calibrated against the self-sprite readback).
    aim_brads: int = 0
    prev_observed_aim: int | None = None
    fire_ready: bool = False
    enemies: tuple[Enemy, ...] = ()
    teammates: tuple[Enemy, ...] = ()
    # Heart state (folded, but effectively per-frame since pedestals never fog):
    hearts: dict[Team, HeartState] = field(default_factory=dict)
    i_carry_heart_of: Team | None = None
    #: Colors whose hearts are out of play (captured/retired or team wiped).
    hearts_retired: set[Team] = field(default_factory=set)
    own_heart_stolen: bool = False
    own_heart_thief_pos: tuple[int, int] | None = None
    # Player tracks + danger field:
    enemy_tracks: list[PlayerTrack] = field(default_factory=list)
    teammate_tracks: list[PlayerTrack] = field(default_factory=list)
    danger: np.ndarray | None = None
    danger_spread_carry: float = 0.0
    # Navigation:
    nav_goal: tuple[int, int] | None = None
    nav_path: list[tuple[int, int]] | None = None
    nav_cursor: int = 0
    nav_last_xy: tuple[int, int] | None = None
    nav_stuck_ticks: int = 0
    # Lighthouse aim sweep phase:
    sweep_offset: int = 0
    sweep_dir: int = 1
    micro: str | None = None
    heard_duck: bool = False
    # Items: discovered spawn table + our own carried/hp state.
    item_spawns: list[ItemSpawn] = field(default_factory=list)
    item_options: list[ItemOption] = field(default_factory=list)
    item_choice: ItemOption | None = None
    item_opportunity_ticks: int = 0
    item_fetch_ticks: int = 0
    item_yield_ticks: int = 0
    item_option_ticks: dict[str, int] = field(default_factory=dict)
    item_reason_ticks: dict[str, int] = field(default_factory=dict)
    hp_pips: int | None = None
    #: Per-color aggregate (kills, deaths) folded from the team-score chips.
    team_scores: dict[Team, tuple[int, int]] = field(default_factory=dict)
    i_have_grenade: bool = False
    i_have_shield: bool = False
    i_have_arc: bool = False
    # Hearing:
    heard_events: list[HeardImpact] = field(default_factory=list)
    under_fire: bool = False
    # Firefight overlay:
    firefight_active: bool = False
    firefight_entered_tick: int = -1
    firefight_last_trigger_tick: int = -10_000
    firefight_ticks_total: int = 0
    firefight_engagements: int = 0
    firefight_target: TargetRef | None = None
    firefight_target_score: TargetScore | None = None
    firefight_target_selected_tick: int = -1
    firefight_target_last_seen_tick: int = -1
    firefight_target_switches: int = 0
    focus_claim: FocusClaim | None = None
    focus_last_claim_sent_tick: int = -10_000
    focus_claims_sent: int = 0
    focus_claims_heard: int = 0
    focus_claims_suppressed: int = 0
    focus_claim_release_counts: dict[str, int] = field(default_factory=dict)
    focus_last_release_reason: str | None = None
    friendly_fire_suppressed: int = 0
    aim_resyncs: int = 0
    firing_turns: int = 0
    spray_pursuit_ticks: int = 0
    visible_grenade_starts: int = 0
    visible_grenade_releases: int = 0
    grenade_target_starts: dict[str, int] = field(default_factory=dict)
    grenade_target_releases: dict[str, int] = field(default_factory=dict)
    grenade_targeted_enemies: int = 0
    grenade_safety_vetoes: int = 0
    grenade_force_releases: int = 0
    firefight_target_range_counts: dict[str, int] = field(default_factory=dict)
    firefight_shot_range_counts: dict[str, int] = field(default_factory=dict)
    firefight_arc_exempt_ticks: int = 0
    # Chat — send-side bookkeeping:
    chat_last_sent_tick: int = -10_000
    chat_enemy_armed: bool = True
    chat_last_enemy_tick: int = -10_000
    chat_enemy_seen_tick: int = -10_000
    chat_sent_counts: dict[str, int] = field(default_factory=dict)
    # Chat — receive-side decoded state:
    carrier_fix: tuple[tuple[int, int], int, int] | None = None
    thief_fix: tuple[tuple[int, int], int] | None = None
    grenade_warnings: list[tuple[tuple[int, int], int]] = field(default_factory=list)
    chat_heard_counts: dict[str, int] = field(default_factory=dict)
    chat_processed: dict[str, tuple[str, int]] = field(default_factory=dict)
    chat_last_sent_text: str | None = None
    # Squads (formation floor + optional command layer):
    squad_wait_since: int = -1
    squad_wait_ticks: int = 0
    squad_cohesion_ticks: int = 0
    order: tuple[str, tuple[int, int], int] | None = None
    order_source: str | None = None
    presence: dict[int, int] = field(default_factory=dict)
    last_ping_tick: int = -10_000
    last_order_sent_tick: int = -10_000
    rejoin_point: tuple[int, int] | None = None
    rejoin_until: int = -1
    respawned_tick: int = -10_000
    orders_sent: int = 0
    orders_heard: int = 0
    pings_sent: int = 0
    pings_heard: int = 0
    backoff_events: int = 0
    rejoin_ticks: int = 0
    convert_events: int = 0
    converting: bool = False
    # Lead-aim / grenade state:
    lead_brads: int = 0
    throw_charge_ticks: int = 0
    throw_target: tuple[int, int] | None = None
    throw_reason: str | None = None
    throw_enemy_count: int = 0
    throw_live_target: bool = False


@dataclass
class ActionState:
    """Mutable action bookkeeping across frames."""

    last_rot: int = 0
    a_held: bool = False
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
    "Enemy",
    "FocusClaim",
    "HeardImpact",
    "HeartState",
    "Intent",
    "IntentKind",
    "ItemKind",
    "ItemOption",
    "ItemSpawn",
    "Observation",
    "PaintState",
    "PlayerTrack",
    "Role",
    "TargetCandidate",
    "TargetRef",
    "TargetScore",
    "Team",
]
