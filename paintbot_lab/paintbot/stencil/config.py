"""Tunable knobs and static game constants for stencil.

Knobs live here, isolated from logic, so each iteration is attributable and can be
A/B'd (root AGENTS.md). Sweepable families use ``TUNABLE_REGISTRY`` entries that
directly construct their live values, so domains and defaults cannot drift from
runtime config.

Unlike beacon (the CTF ancestor), there are **no map geometry constants** here:
Paintbot maps are procedurally generated per episode, so every map fact (size,
walls, endzones, pedestals, chokes, rally lines) lives on the episode-scoped
``WorldMap`` (worldmap.py) built online from the walkability sprite. Only
sim-rule constants that hold on every map (speeds, aim, gun timing, item ranges)
belong here.
"""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

TunableType = Literal["boolean", "integer", "number"]
TunableValue = bool | int | float

# --- Grid ---------------------------------------------------------------------------
#: Nav grid cell size in map pixels (matches the Nim baseline's NavCell).
NAV_CELL = 8

# --- Movement (sim.nim) -----------------------------------------------------------
#: Max player speed in px/tick PER AXIS: sim.nim MaxSpeed (704) / MotionScale (256).
#: velX/velY clamp independently, so diagonal movement reaches sqrt(2)x this. The
#: heart carrier moves at carrierSpeedPct (70%) of it.
MAX_SPEED_PX_TICK = 704 / 256  # 2.75

# --- Observation wire format --------------------------------------------------------
#: Wire pixels per map pixel on the PLAYER observation stream (1x since the 0.7.8
#: renderer restore; kept at this seam so a future scale change is a one-constant fix).
RENDER_SCALE = 1

# --- Teams --------------------------------------------------------------------------
#: All team color tokens the engine knows; active teams are always a prefix
#: (labels.nim / baseline.nim TeamColorNames).
TEAM_COLORS = ("red", "blue", "green", "yellow")
#: Lives per player (manifest ``lives``; all paintbot variants use 3).
LIVES_PER_PLAYER = 3

# --- Aim / vision (sim.nim) -------------------------------------------------------
AIM_BRADS_TURN = 256  # brads per full turn
AIM_TURN_RATE = 5  # brads/tick a held rotate button turns aim (must match server)
#: Forward wedge half-angle. Paintbot variants run visionConeDeg 60 except 4ffa8
#: (45). Used only for self-view estimates (item refutation); worldmap narrows it
#: for the 4ffa8 signature (4 teams on a giant board).
VISION_CONE_HALF_DEG = 60
VISION_BUBBLE = 90  # omni bubble radius, px

# --- Gun timing (sim.nim) -----------------------------------------------------------
#: Ticks from trigger pull (aim locks) to the bullet leaving (FireWindupTicks). The
#: bullet then travels instantly (hitscan), so the whole lead is the windup + the
#: sighting age — a strafing enemy moves ~windup * 2.75 px between pull and release.
FIRE_WINDUP_TICKS = 5

# --- Items (sim.nim tuning; positions are per-map, learned from sightings) ----------
#: The 8-bit controller's C button (bitworld ButtonC = 1 shl 7): hold to charge a
#: grenade throw, release to let it fly. NOT in the SDK Button enum (which stops at
#: B); the sprite bridge's 7-bit mask clamp is widened in main.py.
BUTTON_C = 128
#: Respawn intervals (ticks) after a pickup is taken (sim.nim *RespawnTicks).
GRENADE_RESPAWN_TICKS = 5 * 24
MEDKIT_RESPAWN_TICKS = 30 * 24
SHIELD_RESPAWN_TICKS = 30 * 24
ARC_RESPAWN_TICKS = 30 * 24
#: Grenade throw tuning (sim.nim): hold C GrenadeChargeTicks for a full-strength
#: throw; release flies from GRENADE_MIN_RANGE up to ~map_width/5 along the aim
#: (the max range is map-dependent — worldmap.grenade_max_range).
GRENADE_CHARGE_TICKS = 24
GRENADE_MIN_RANGE = 30
GRENADE_BLAST_RADIUS = 52
GRENADE_FLIGHT_TICKS = 2 * FIRE_WINDUP_TICKS
#: A pickup is grabbed by touch within this radius (sim.nim *PickupRange).
ITEM_PICKUP_RANGE = 12


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, ""))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, ""))
    except ValueError:
        return default


@dataclass(frozen=True)
class TunableSpec:
    """One sweepable policy parameter and its machine-readable domain."""

    name: str
    family: str
    env_var: str
    default: TunableValue
    value_type: TunableType
    description: str
    minimum: int | float | None = None
    maximum: int | float | None = None
    choices: tuple[TunableValue, ...] | None = None

    def coerce(self, value: object) -> TunableValue:
        """Parse one assignment and enforce this knob's independent domain."""
        if self.value_type == "boolean":
            if isinstance(value, bool):
                parsed: TunableValue = value
            elif isinstance(value, int) and value in (0, 1):
                parsed = bool(value)
            elif isinstance(value, str) and value.strip().lower() in {
                "0",
                "1",
                "false",
                "true",
                "off",
                "on",
            }:
                parsed = value.strip().lower() in {"1", "true", "on"}
            else:
                raise ValueError(f"{self.name} must be boolean")
        elif self.value_type == "integer":
            if isinstance(value, bool):
                raise ValueError(f"{self.name} must be an integer")
            try:
                parsed = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{self.name} must be an integer") from exc
            if isinstance(value, float) and not value.is_integer():
                raise ValueError(f"{self.name} must be an integer")
            if isinstance(value, str) and str(parsed) != value.strip():
                raise ValueError(f"{self.name} must be an integer")
        else:
            if isinstance(value, bool):
                raise ValueError(f"{self.name} must be a number")
            try:
                parsed = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{self.name} must be a number") from exc
            if not math.isfinite(parsed):
                raise ValueError(f"{self.name} must be finite")

        if self.choices is not None and parsed not in self.choices:
            raise ValueError(f"{self.name} must be one of {list(self.choices)}")
        if self.minimum is not None and parsed < self.minimum:
            raise ValueError(f"{self.name} must be >= {self.minimum}")
        if self.maximum is not None and parsed > self.maximum:
            raise ValueError(f"{self.name} must be <= {self.maximum}")
        return parsed

    def to_dict(self) -> dict[str, object]:
        """JSON-safe registry row."""
        return {
            "name": self.name,
            "family": self.family,
            "env_var": self.env_var,
            "default": self.default,
            "type": self.value_type,
            "range": (
                {"minimum": self.minimum, "maximum": self.maximum}
                if self.choices is None
                else None
            ),
            "choices": list(self.choices) if self.choices is not None else None,
            "description": self.description,
        }


@dataclass(frozen=True)
class TunableInvariant:
    """A named cross-knob constraint exposed alongside the registry."""

    name: str
    description: str
    family: str = "firefight"

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "family": self.family,
            "description": self.description,
        }


TUNABLE_REGISTRY: dict[str, TunableSpec] = {}


def _tunable(
    name: str,
    env_var: str,
    default: TunableValue,
    value_type: TunableType,
    description: str,
    *,
    family: str,
    minimum: int | float | None = None,
    maximum: int | float | None = None,
    choices: tuple[TunableValue, ...] | None = None,
) -> TunableValue:
    """Register one knob and resolve its current environment-backed value."""
    if name in TUNABLE_REGISTRY:
        raise ValueError(f"duplicate tunable name: {name}")
    if any(spec.env_var == env_var for spec in TUNABLE_REGISTRY.values()):
        raise ValueError(f"duplicate tunable env var: {env_var}")
    spec = TunableSpec(
        name=name,
        family=family,
        env_var=env_var,
        default=default,
        value_type=value_type,
        description=description,
        minimum=minimum,
        maximum=maximum,
        choices=choices,
    )
    spec.coerce(default)
    TUNABLE_REGISTRY[name] = spec
    raw = os.getenv(env_var)
    return default if raw is None or raw == "" else spec.coerce(raw)


def _bool_tunable(
    name: str, env_var: str, default: bool, description: str, *, family: str
) -> bool:
    return bool(
        _tunable(
            name,
            env_var,
            default,
            "boolean",
            description,
            family=family,
            choices=(False, True),
        )
    )


def _int_tunable(
    name: str,
    env_var: str,
    default: int,
    description: str,
    *,
    family: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    return int(
        _tunable(
            name,
            env_var,
            default,
            "integer",
            description,
            family=family,
            minimum=minimum,
            maximum=maximum,
        )
    )


def _float_tunable(
    name: str,
    env_var: str,
    default: float,
    description: str,
    *,
    family: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    return float(
        _tunable(
            name,
            env_var,
            default,
            "number",
            description,
            family=family,
            minimum=minimum,
            maximum=maximum,
        )
    )


# --- Tunable behaviour knobs (env-overridable for A/B at upload time) -------------
#: Lighthouse sweep half-arc, in brads (±). 32 brads ≈ ±45°.
SWEEP_HALF_ARC = _env_int("STENCIL_SWEEP_HALF_ARC", 32)
#: Deadband: don't bother rotating to close an aim error smaller than this (brads).
AIM_DEADBAND = _env_int("STENCIL_AIM_DEADBAND", 2)
#: Resync the dead-reckoned aim to the observed self-sprite rotation only when they
#: disagree by more than this (brads; the readback is 16-step quantized).
AIM_RESYNC_SLACK_BRADS = _env_int("STENCIL_AIM_RESYNC_SLACK_BRADS", 8)
#: Fire only when the target is within this perpendicular slack of the aim ray (px).
FIRE_SLACK_PX = _env_int("STENCIL_FIRE_SLACK_PX", 8)
#: Below this range (px) an enemy is close enough to fire on with a looser gate.
CLOSE_RANGE_PX = _env_int("STENCIL_CLOSE_RANGE_PX", 220)
#: Hold fire if a visible teammate is within this perpendicular distance (px) of the
#: shot ray and closer than the target (friendly fire is ON).
FRIENDLY_FIRE_CORRIDOR_PX = _int_tunable(
    "FRIENDLY_FIRE_CORRIDOR_PX",
    "STENCIL_FF_CORRIDOR_PX",
    22,
    "Friendly-fire veto corridor around the shot ray, in pixels.",
    family="firefight",
    minimum=14,
)
#: Re-plan the A* path if the goal cell moves more than this many cells.
REPLAN_GOAL_CELLS = _env_int("STENCIL_REPLAN_GOAL_CELLS", 2)
#: Frames of no navigation progress before forcing a re-plan + jitter.
STUCK_TICKS = _env_int("STENCIL_STUCK_TICKS", 8)
#: Diagnostics cadence (frames between full-state trace snapshots).
DIAG_EVERY_TICKS = _env_int("STENCIL_DIAG_EVERY_TICKS", 96)

# --- Belief: player tracks + danger field ------------------------------------------
TRACK_TTL_TICKS = _env_int("STENCIL_TRACK_TTL_TICKS", 120)
TRACK_MATCH_SLACK_PX = 16
TRACK_VEL_MAX_GAP_TICKS = 8
TRACK_VEL_EMA = 0.5
DANGER_DIFFUSION_FACTOR = _env_float("STENCIL_DANGER_DIFFUSION_FACTOR", 0.75)
DANGER_DECAY_HALF_LIFE_TICKS = _env_int("STENCIL_DANGER_HALF_LIFE_TICKS", 48)
DANGER_STAMP_RADIUS_PX = 16
#: Nav-cells-per-side folded into one cell when tracing the danger grid.
DANGER_TRACE_DOWNSAMPLE = 4

# --- Peek-fire-duck micro -----------------------------------------------------------
PEEK_DUCK = _env_int("STENCIL_PEEK_DUCK", 1) == 1
DUCK_RANGE_PX = _env_int("STENCIL_DUCK_RANGE_PX", 340)
DUCK_THREAT_FRESH_TICKS = _env_int("STENCIL_DUCK_THREAT_FRESH_TICKS", 30)
PEEK_TARGET_FRESH_TICKS = _env_int("STENCIL_PEEK_TARGET_FRESH_TICKS", 24)
PEEK_DUCK_SEARCH_CELLS = _env_int("STENCIL_PEEK_DUCK_SEARCH_CELLS", 3)
#: Within this distance (px) of the steal target, never duck/peek — grab speed wins.
PEEK_DUCK_RUSH_EXEMPT_PX = _env_int("STENCIL_PEEK_DUCK_RUSH_EXEMPT_PX", 90)

# --- Lead aim -----------------------------------------------------------------------
LEAD_AIM = _env_int("STENCIL_LEAD_AIM", 1) == 1
LEAD_TICKS = _env_float("STENCIL_LEAD_TICKS", 3.5)
LEAD_MIN_FRAMES = _env_int("STENCIL_LEAD_MIN_FRAMES", 3)
#: Target-scoring range band fades to zero here (soft preference, not a fire gate).
FF_RANGE_SCORE_FALLOFF_PX = 350
#: Ceiling for the firefight trigger radius (was the baked sightline cap in beacon).
FF_RADIUS_MAX_PX = 400

# --- Firefight target selection + focus claims --------------------------------------
FIREFIGHT = _bool_tunable(
    "FIREFIGHT",
    "STENCIL_FIREFIGHT",
    True,
    "Enable firefight state and scored gun-target selection.",
    family="firefight",
)
FOCUS_CLAIMS = _bool_tunable(
    "FOCUS_CLAIMS",
    "STENCIL_FOCUS_CLAIMS",
    True,
    "Enable local F target claims as a soft scoring bias.",
    family="firefight",
)
FF_RADIUS_PX = _int_tunable(
    "FF_RADIUS_PX",
    "STENCIL_FF_RADIUS_PX",
    400,
    "Visible-enemy radius that triggers firefight state, in map pixels.",
    family="firefight",
    minimum=FF_RANGE_SCORE_FALLOFF_PX,
    maximum=FF_RADIUS_MAX_PX,
)
FF_DWELL_TICKS = _int_tunable(
    "FF_DWELL_TICKS",
    "STENCIL_FF_DWELL_TICKS",
    48,
    "Ticks firefight remains active after its last trigger.",
    family="firefight",
    minimum=1,
)
FF_TARGET_MIN_DWELL_TICKS = _int_tunable(
    "FF_TARGET_MIN_DWELL_TICKS",
    "STENCIL_FF_TARGET_MIN_DWELL_TICKS",
    8,
    "Minimum ticks on a shootable target before a scored switch.",
    family="firefight",
    minimum=1,
)
FF_TARGET_SWITCH_MARGIN = _float_tunable(
    "FF_TARGET_SWITCH_MARGIN",
    "STENCIL_FF_TARGET_SWITCH_MARGIN",
    0.10,
    "Minimum score advantage required to switch a shootable latched target.",
    family="firefight",
    minimum=0.0,
)
FF_RANGE_CLOSE_PX = _int_tunable(
    "FF_RANGE_CLOSE_PX",
    "STENCIL_FF_RANGE_CLOSE_PX",
    120,
    "Range at or below which the range-band score is zero, in pixels.",
    family="firefight",
    minimum=0,
    maximum=FF_RANGE_SCORE_FALLOFF_PX,
)
FF_RANGE_IDEAL_MIN_PX = _int_tunable(
    "FF_RANGE_IDEAL_MIN_PX",
    "STENCIL_FF_RANGE_IDEAL_MIN_PX",
    220,
    "Near edge of the peak target-scoring range band.",
    family="firefight",
    minimum=0,
    maximum=FF_RANGE_SCORE_FALLOFF_PX,
)
FF_RANGE_IDEAL_MAX_PX = _int_tunable(
    "FF_RANGE_IDEAL_MAX_PX",
    "STENCIL_FF_RANGE_IDEAL_MAX_PX",
    300,
    "Far edge of the peak target-scoring range band.",
    family="firefight",
    minimum=0,
    maximum=FF_RANGE_SCORE_FALLOFF_PX,
)
FF_WOUND_WEIGHT = _float_tunable(
    "FF_WOUND_WEIGHT",
    "STENCIL_FF_WOUND_WEIGHT",
    0.50,
    "Weight for preferring enemies with fewer lit health-bar segments.",
    family="firefight",
    minimum=0.0,
)
FF_WOUND_UNKNOWN = _float_tunable(
    "FF_WOUND_UNKNOWN",
    "STENCIL_FF_WOUND_UNKNOWN",
    0.15,
    "Normalized wound value used when an enemy HP bar is unresolved.",
    family="firefight",
    minimum=0.0,
    maximum=1.0,
)
FF_RANGE_WEIGHT = _float_tunable(
    "FF_RANGE_WEIGHT",
    "STENCIL_FF_RANGE_WEIGHT",
    0.30,
    "Weight for preferring targets in the effective gun range band.",
    family="firefight",
    minimum=0.0,
)
FF_CLAIM_WEIGHT = _float_tunable(
    "FF_CLAIM_WEIGHT",
    "STENCIL_FF_CLAIM_WEIGHT",
    0.12,
    "Bounded score bonus for matching a fresh local focus claim.",
    family="firefight",
    minimum=0.0,
)
FF_SHOOTABILITY_WEIGHT = _float_tunable(
    "FF_SHOOTABILITY_WEIGHT",
    "STENCIL_FF_SHOOTABILITY_WEIGHT",
    0.35,
    "Weight for signed clear-versus-blocked shootability.",
    family="firefight",
    minimum=0.0,
)
FF_AIM_COST_WEIGHT = _float_tunable(
    "FF_AIM_COST_WEIGHT",
    "STENCIL_FF_AIM_COST_WEIGHT",
    0.18,
    "Penalty weight for normalized aim traverse to the target.",
    family="firefight",
    minimum=0.0,
)
FF_SHIELD_WEIGHT = _float_tunable(
    "FF_SHIELD_WEIGHT",
    "STENCIL_FF_SHIELD_WEIGHT",
    0.10,
    "Penalty weight for a visibly shielded target.",
    family="firefight",
    minimum=0.0,
)
FF_CLAIM_REBROADCAST_TICKS = _int_tunable(
    "FF_CLAIM_REBROADCAST_TICKS",
    "STENCIL_FF_CLAIM_REBROADCAST_TICKS",
    30,
    "Minimum ticks between this bot's focus-claim broadcasts.",
    family="firefight",
    minimum=1,
)
FF_CLAIM_TTL_TICKS = _int_tunable(
    "FF_CLAIM_TTL_TICKS",
    "STENCIL_FF_CLAIM_TTL_TICKS",
    72,
    "Ticks without a broadcast before a focus claim expires.",
    family="firefight",
    minimum=1,
)
FF_CLAIM_MATCH_PX = _int_tunable(
    "FF_CLAIM_MATCH_PX",
    "STENCIL_FF_CLAIM_MATCH_PX",
    96,
    "Maximum position error for associating an anonymous focus claim.",
    family="firefight",
    minimum=NAV_CELL,
)
FF_CLAIM_LOCALITY_PX = _int_tunable(
    "FF_CLAIM_LOCALITY_PX",
    "STENCIL_FF_CLAIM_LOCALITY_PX",
    400,
    "Receiver-to-target radius that scopes focus-claim exclusivity.",
    family="firefight",
    minimum=NAV_CELL,
)
FF_TARGET_MISSING_TICKS = _int_tunable(
    "FF_TARGET_MISSING_TICKS",
    "STENCIL_FF_TARGET_MISSING_TICKS",
    36,
    "Ticks unseen before a claimed target is released as missing.",
    family="firefight",
    minimum=1,
)
FF_DEATH_MISSING_TICKS = _int_tunable(
    "FF_DEATH_MISSING_TICKS",
    "STENCIL_FF_DEATH_MISSING_TICKS",
    8,
    "Minimum unseen ticks before an enemy death can release a claim.",
    family="firefight",
    minimum=1,
)

TUNABLE_INVARIANTS: tuple[TunableInvariant, ...] = (
    TunableInvariant(
        "range_band_order",
        "0 <= close < ideal_min <= ideal_max <= FF_RANGE_SCORE_FALLOFF_PX.",
    ),
    TunableInvariant(
        "firefight_radius_geometry",
        "FF_RANGE_SCORE_FALLOFF_PX <= firefight radius <= FF_RADIUS_MAX_PX.",
    ),
    TunableInvariant(
        "target_latch_within_mode",
        "Target minimum dwell must not exceed firefight dwell.",
    ),
    TunableInvariant(
        "claim_refresh_before_expiry",
        "Claim rebroadcast interval must be shorter than claim TTL.",
    ),
    TunableInvariant(
        "claim_release_clock_order",
        "Death-missing ticks < target-missing ticks < claim TTL.",
    ),
    TunableInvariant(
        "claim_match_within_locality",
        "Anonymous claim match radius must not exceed claim locality.",
    ),
    TunableInvariant(
        "focus_requires_firefight",
        "FOCUS_CLAIMS may be enabled only when FIREFIGHT is enabled.",
    ),
    TunableInvariant(
        "claim_bias_bounded_by_wound",
        "Claim bonus may not exceed one health-bar segment of wound score.",
    ),
)


def tunable_spec(name_or_env: str) -> TunableSpec:
    """Look up a registry entry by config name or environment variable."""
    by_name = TUNABLE_REGISTRY.get(name_or_env)
    if by_name is not None:
        return by_name
    by_env = next(
        (spec for spec in TUNABLE_REGISTRY.values() if spec.env_var == name_or_env),
        None,
    )
    if by_env is None:
        raise ValueError(f"unknown tunable: {name_or_env}")
    return by_env


def validate_tunable_values(
    assignments: Mapping[str, object] | None = None,
) -> dict[str, TunableValue]:
    """Normalize a partial assignment against defaults and validate all invariants."""
    values = {
        name: spec.coerce(spec.default) for name, spec in TUNABLE_REGISTRY.items()
    }
    assigned_names: set[str] = set()
    for key, raw_value in (assignments or {}).items():
        spec = tunable_spec(key)
        if spec.name in assigned_names:
            raise ValueError(f"duplicate assignment for {spec.name}")
        assigned_names.add(spec.name)
        values[spec.name] = spec.coerce(raw_value)

    def require(condition: bool, invariant: str) -> None:
        if not condition:
            description = next(
                item.description
                for item in TUNABLE_INVARIANTS
                if item.name == invariant
            )
            raise ValueError(f"{invariant}: {description}")

    require(
        0
        <= values["FF_RANGE_CLOSE_PX"]
        < values["FF_RANGE_IDEAL_MIN_PX"]
        <= values["FF_RANGE_IDEAL_MAX_PX"]
        <= FF_RANGE_SCORE_FALLOFF_PX,
        "range_band_order",
    )
    require(
        FF_RANGE_SCORE_FALLOFF_PX <= values["FF_RADIUS_PX"] <= FF_RADIUS_MAX_PX,
        "firefight_radius_geometry",
    )
    require(
        values["FF_TARGET_MIN_DWELL_TICKS"] <= values["FF_DWELL_TICKS"],
        "target_latch_within_mode",
    )
    require(
        values["FF_CLAIM_REBROADCAST_TICKS"] < values["FF_CLAIM_TTL_TICKS"],
        "claim_refresh_before_expiry",
    )
    require(
        values["FF_DEATH_MISSING_TICKS"]
        < values["FF_TARGET_MISSING_TICKS"]
        < values["FF_CLAIM_TTL_TICKS"],
        "claim_release_clock_order",
    )
    require(
        values["FF_CLAIM_MATCH_PX"] <= values["FF_CLAIM_LOCALITY_PX"],
        "claim_match_within_locality",
    )
    require(
        not values["FOCUS_CLAIMS"] or bool(values["FIREFIGHT"]),
        "focus_requires_firefight",
    )
    require(
        values["FF_CLAIM_WEIGHT"] <= values["FF_WOUND_WEIGHT"] * 0.5,
        "claim_bias_bounded_by_wound",
    )
    return values


# Validate the actual environment-backed values too. A malformed hosted arm should
# fail at process startup, while the tuning CLI catches it before upload.
validate_tunable_values({name: globals()[name] for name in TUNABLE_REGISTRY})

# --- Item skills ---------------------------------------------------------------------
ITEMS = _env_int("STENCIL_ITEMS", 1) == 1
#: Maximum extra walkable-route distance for a convenient pickup.
ITEM_CONVENIENT_DETOUR_PX = _env_int("STENCIL_ITEM_CONVENIENT_DETOUR_PX", 48)
#: A hurt bot may take a larger med-kit detour.
MEDKIT_CONVENIENT_DETOUR_PX = _env_int("STENCIL_MEDKIT_CONVENIENT_DETOUR_PX", 420)
#: Spray-can pickups only when effectively underfoot (the spray disables the gun).
ITEM_ARC_DETOUR_PX = _env_int("STENCIL_ITEM_ARC_DETOUR_PX", 32)
#: Yield when a visible teammate has at least this much shorter a route to the item.
ITEM_YIELD_MARGIN_PX = _env_int("STENCIL_ITEM_YIELD_MARGIN_PX", 16)
#: Grenade throwing (needs ITEMS): lob at wall-blocked remembered enemies.
GRENADE_THROW = _env_int("STENCIL_GRENADE_THROW", 1) == 1
GRENADE_MIN_THROW_PX = 90
GRENADE_AIM_ERR_BRADS = _env_int("STENCIL_GRENADE_AIM_ERR_BRADS", 4)
GRENADE_FORCE_RELEASE_TICKS = 16
GRENADE_TARGET_FRESH_TICKS = _env_int("STENCIL_GRENADE_TARGET_FRESH_TICKS", 30)
GRENADE_TEAMMATE_FRESH_TICKS = _env_int("STENCIL_GRENADE_TEAMMATE_FRESH_TICKS", 12)
GRENADE_SINGLE_HP_MAX = _env_int("STENCIL_GRENADE_SINGLE_HP_MAX", 2)
#: Spray-can geometry (sim.nim GV30): reach 170px, max width 85px.
ARC_FIRE_RANGE_PX = 170
ARC_MAX_WIDTH_PX = 85
ARC_PURSUIT_RANGE_PX = 400
ARC_IDEAL_RANGE_PX = 100

# --- Hearing --------------------------------------------------------------------------
HEARING = _env_int("STENCIL_HEARING", 1) == 1
HEARD_MATCH_PX = _env_int("STENCIL_HEARD_MATCH_PX", 40)
HEARD_TTL_TICKS = _env_int("STENCIL_HEARD_TTL_TICKS", 60)
HEARD_DANGER_HEAT = _env_float("STENCIL_HEARD_DANGER_HEAT", 0.5)
HEARD_DANGER_RADIUS_PX = _env_int("STENCIL_HEARD_DANGER_RADIUS_PX", 32)
HEARD_DUCK_RANGE_PX = _env_int("STENCIL_HEARD_DUCK_RANGE_PX", 180)
HEARD_DUCK_FRESH_TICKS = _env_int("STENCIL_HEARD_DUCK_FRESH_TICKS", 24)

# --- Chat -----------------------------------------------------------------------------
CHAT = _env_int("STENCIL_CHAT", 1) == 1
CHAT_MIN_INTERVAL_TICKS = _env_int("STENCIL_CHAT_MIN_INTERVAL_TICKS", 30)
CHAT_ENEMY_REARM_TICKS = _env_int("STENCIL_CHAT_ENEMY_REARM_TICKS", 48)
CHAT_ENEMY_RESHOUT_TICKS = _env_int("STENCIL_CHAT_ENEMY_RESHOUT_TICKS", 72)
CHAT_FIX_TTL_TICKS = _env_int("STENCIL_CHAT_FIX_TTL_TICKS", 96)
CHAT_BUBBLE_DEDUP_TICKS = _env_int("STENCIL_CHAT_BUBBLE_DEDUP_TICKS", 80)
UNDER_FIRE_RANGE_PX = _env_int("STENCIL_UNDER_FIRE_RANGE_PX", 90)
UNDER_FIRE_FRESH_TICKS = _env_int("STENCIL_UNDER_FIRE_FRESH_TICKS", 24)
CHAT_ENEMY_BUBBLE_FIX = _env_int("STENCIL_CHAT_ENEMY_BUBBLE_FIX", 1) == 1
GRENADE_WARN_CLEAR_PX = _env_int("STENCIL_GRENADE_WARN_CLEAR_PX", 80)
GRENADE_WARN_TTL_TICKS = _env_int("STENCIL_GRENADE_WARN_TTL_TICKS", 72)

# --- Squads (formation floor; command layer OFF by default, as in beacon v29+) -------
SQUADS = _env_int("STENCIL_SQUADS", 0) == 1
SQUAD_COHESION_PX = _env_int("STENCIL_SQUAD_COHESION_PX", 120)
SQUAD_MIN_BUDDIES = _env_int("STENCIL_SQUAD_MIN_BUDDIES", 1)
SQUAD_SEPARATION_PX = _int_tunable(
    "SQUAD_SEPARATION_PX",
    "STENCIL_SQUAD_SEPARATION_PX",
    40,
    "Teammate distance below which a bot steers apart, in map pixels.",
    family="spacing",
    minimum=16,
    maximum=120,
)
SQUAD_SPREAD_PX = _env_int("STENCIL_SQUAD_SPREAD_PX", 70)
SQUAD_WAIT_TIMEOUT_TICKS = _env_int("STENCIL_SQUAD_WAIT_TIMEOUT_TICKS", 150)
SQUAD_SECTOR_BRADS = _env_int("STENCIL_SQUAD_SECTOR_BRADS", 50)
SQUAD_COMMAND = _env_int("STENCIL_SQUAD_COMMAND", 0) == 1
#: Fractions of the home->center axis for derived tactical anchors (worldmap):
#: the defender choke line and the attacker rally line.
CHOKE_FRACTION = _env_float("STENCIL_CHOKE_FRACTION", 0.45)
RALLY_FRACTION = _env_float("STENCIL_RALLY_FRACTION", 0.65)

# --- Convert trigger (the single biggest measured win in the beacon lineage) ---------
#: When the weakest enemy team's lives remaining drop to this or below, hunt the
#: wipe — under pot scoring a draw pays -1 like a loss, so aggression is ~free.
CONVERT_ENEMY_LIVES = _env_int("STENCIL_CONVERT_ENEMY_LIVES", 6)
ORDER_TTL_TICKS = _env_int("STENCIL_ORDER_TTL_TICKS", 240)
ORDER_REBROADCAST_TICKS = _env_int("STENCIL_ORDER_REBROADCAST_TICKS", 72)
PING_INTERVAL_TICKS = _env_int("STENCIL_PING_INTERVAL_TICKS", 60)
PRESENCE_STALE_TICKS = _env_int("STENCIL_PRESENCE_STALE_TICKS", 190)
BACKOFF_STEP_PX = _env_int("STENCIL_BACKOFF_STEP_PX", 70)
REJOIN_TIMEOUT_TICKS = _env_int("STENCIL_REJOIN_TIMEOUT_TICKS", 360)
REJOIN_CONTACT_PX = _env_int("STENCIL_REJOIN_CONTACT_PX", 160)

# --- Roles ---------------------------------------------------------------------------
#: How many of the per-team seats defend (seats 0..N-1). With 4-agent variants the
#: fraction is applied to the actual seat count (roles.py), so 4-seat teams get 1-2
#: defenders instead of 3-of-4.
DEFENDER_COUNT = _env_int("STENCIL_DEFENDERS", 3)
#: A defender within this distance (px) of its hold point stops advancing and holds.
HOLD_ARRIVE_PX = _env_int("STENCIL_HOLD_ARRIVE_PX", 28)

__all__ = [name for name in dir() if name.isupper()]
