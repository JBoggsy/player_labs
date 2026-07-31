"""Tunable knobs and static game geometry for beacon.

Knobs live here, isolated from logic, so each iteration is attributable and can be
A/B'd (root AGENTS.md). Sweepable families use ``TUNABLE_REGISTRY`` entries that
directly construct their live values, so domains and defaults cannot drift from
runtime config. Geometry constants mirror ``src/ctf/sim.nim`` at the pinned
``CTF_REF`` and must match the deployed arena.
"""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

TunableType = Literal["boolean", "integer", "number"]
TunableValue = bool | int | float

# --- Static arena geometry (verbatim from sim.nim) --------------------------------
MAP_W = 1235
MAP_H = 659
CENTER_X = 617
CENTER_Y = 329
NAV_CELL = 8
GRID_W = 155
GRID_H = 83

#: Static flag pedestals (also the steal targets), by team.
PEDESTAL = {"red": (186, 329), "blue": (1049, 329)}
#: A point deep in each team's capture zone (the deliver target).
HOME_DEEP = {"red": (150, 329), "blue": (MAP_W - 1 - 150, 329)}

# --- Movement (sim.nim) -----------------------------------------------------------
#: Max player speed in px/tick PER AXIS: sim.nim MaxSpeed (704) / MotionScale (256).
#: velX/velY clamp independently, so diagonal movement reaches sqrt(2)x this. The
#: flag carrier moves at carrierSpeedPct (70%) of it.
MAX_SPEED_PX_TICK = 704 / 256  # 2.75

# --- Observation wire format --------------------------------------------------------
#: Wire pixels per map pixel on the PLAYER observation stream. The 0.6-0.7.7 "HD"
#: era carried 3x-scaled coordinates; **the 0.7.8 renderer restore put the player
#: wire back to 1x map pixels** (global.nim: boardScale stays 1 for every player/POV
#: stream; RenderScale supersampling is spectator/replay-only now; see also the
#: baseline's mapPos comment). Perception still divides at the seam so a future
#: scale change is a one-constant fix.
RENDER_SCALE = 1

# --- Aim / vision (sim.nim) -------------------------------------------------------
AIM_BRADS_TURN = 256  # brads per full turn
AIM_TURN_RATE = 5  # brads/tick a held rotate button turns aim (must match server)
#: Offline sightline-field contract. These are deliberately not env-overridable:
#: the runtime must interpret the shipped nav artifact exactly as it was baked.
SIGHTLINE_DIRECTIONS = 32
SIGHTLINE_STEP_PX = 4
SIGHTLINE_CAP_PX = 400
SIGHTLINE_DISTANCE_UNIT_PX = SIGHTLINE_STEP_PX
SIGHTLINE_BRADS_PER_DIRECTION = AIM_BRADS_TURN // SIGHTLINE_DIRECTIONS
#: Directional cover samples the two rays 45 degrees off the threat bearing.
POST_FLANK_ANGLE_DEG = 45
POST_FLANK_DIRECTION_OFFSET = SIGHTLINE_DIRECTIONS * POST_FLANK_ANGLE_DEG // 360
#: Forward wedge half-angle. The LEAGUE runs 45: episodes use the manifest's Default
#: variant game_config (visionConeDeg 45, verified in live episode.json at 0.7.69),
#: which overrides the repo config.json's 60. Was wrongly 60 here until the 2026-07-23
#: audit — that over-estimated our own vision in items._in_view (false "checked,
#: absent" item reads) and in any cone math.
VISION_CONE_HALF_DEG = 45
VISION_BUBBLE = 90  # omni bubble radius, px
#: Spawn aim by team: Red faces east (0), Blue faces west (128).
SPAWN_AIM = {"red": 0, "blue": AIM_BRADS_TURN // 2}

# --- Gun timing (sim.nim) -----------------------------------------------------------
#: Ticks from trigger pull (aim locks) to the bullet leaving (FireWindupTicks). The
#: bullet then travels instantly (hitscan), so the whole lead is the windup + the
#: sighting age — a strafing enemy moves ~windup * 2.75 px between pull and release.
FIRE_WINDUP_TICKS = 5

# --- Items (sim.nim spawn formulas + tuning) ----------------------------------------
#: The 8-bit controller's C button (bitworld ButtonC = 1 shl 7): hold to charge a
#: grenade throw, release to let it fly. NOT in the SDK Button enum (which stops at
#: B); the sprite bridge's 7-bit mask clamp is widened in main.py.
BUTTON_C = 128
_ITEM_INSET = 10 + 40  # ArenaBorder + GrenadeSpawnInset (= PlasmaArcSpawnInset)
#: Corner grenade pickups: two per side (sim.nim grenadeSpawnPoints).
GRENADE_SPAWNS = (
    (_ITEM_INSET, _ITEM_INSET),                    # left top
    (_ITEM_INSET, MAP_H - _ITEM_INSET),            # left bottom
    (MAP_W - _ITEM_INSET, _ITEM_INSET),            # right top
    (MAP_W - _ITEM_INSET, MAP_H - _ITEM_INSET),    # right bottom
)
#: Endzone shields: back columns, three quarters down (sim.nim resetShields; the
#: sim nudges to walkable floor — belief matches by proximity so the raw point is fine).
SHIELD_SPAWNS = ((_ITEM_INSET, 3 * MAP_H // 4), (MAP_W - _ITEM_INSET, 3 * MAP_H // 4))
#: Plasma arcs: same columns, one quarter down (sim.nim plasmaArcSpawnPoints).
ARC_SPAWNS = ((_ITEM_INSET, MAP_H // 4), (MAP_W - _ITEM_INSET, MAP_H // 4))
#: Center-line med kits at one/two thirds height (sim.nim resetMedKits).
MEDKIT_SPAWNS = ((MAP_W // 2, MAP_H // 3), (MAP_W // 2, 2 * MAP_H // 3))
#: Respawn intervals (ticks) after a pickup is taken (sim.nim *RespawnTicks).
GRENADE_RESPAWN_TICKS = 5 * 24
MEDKIT_RESPAWN_TICKS = 30 * 24
SHIELD_RESPAWN_TICKS = 30 * 24
ARC_RESPAWN_TICKS = 30 * 24
#: Grenade throw tuning (sim.nim): hold C GrenadeChargeTicks for a full-strength
#: throw; release flies from GRENADE_MIN_RANGE to GRENADE_MAX_RANGE along the aim.
GRENADE_CHARGE_TICKS = 24
GRENADE_MIN_RANGE = 30
GRENADE_MAX_RANGE = MAP_W // 5  # 247
GRENADE_BLAST_RADIUS = 52  # 40 -> 52 in GameVersion 17 (b571dd3, deployed 0.7.51)
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
            raise ValueError(
                f"{self.name} must be one of {list(self.choices)}"
            )
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


# Family-tagged so post, squad, or item knobs can join without changing the schema.
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
    name: str,
    env_var: str,
    default: bool,
    description: str,
    *,
    family: str,
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
SWEEP_HALF_ARC = _env_int("BEACON_SWEEP_HALF_ARC", 32)
#: Deadband: don't bother rotating to close an aim error smaller than this (brads).
#: With a five-brad turn step, two brads is the nearest attainable side of a
#: target bearing; stopping at three chooses the farther side and caused a large
#: measured accuracy cliff.
AIM_DEADBAND = _env_int("BEACON_AIM_DEADBAND", 2)
#: Resync the dead-reckoned aim to the observed self-sprite rotation only when they
#: disagree by more than this (brads). The 0.7.8-era readback is 16-step quantized:
#: soldierRotIndex rounds to the nearest step, so a correct estimate can disagree by
#: at most 8 — anything larger is real drift (dropped/duplicated frames desync the
#: rotation dead-reckoning; the server holds the last mask between inputs).
AIM_RESYNC_SLACK_BRADS = _env_int("BEACON_AIM_RESYNC_SLACK_BRADS", 8)
#: Fire only when the target is within this perpendicular slack of the aim ray (px),
#: i.e. range * sin(angle_error) <= this. The REAL hit corridor is 14px
#: (BulletHalfWidth 8 + PlayerHalf 6); 8 leaves margin for dead-reckoning error —
#: v11 fired at up to 22px perp miss (11 x the 2.0 close-range multiplier), which
#: is beyond the corridor: guaranteed misses the gate itself invited.
FIRE_SLACK_PX = _env_int("BEACON_FIRE_SLACK_PX", 8)
#: Below this range (px) an enemy is close enough to fire on with a looser gate.
CLOSE_RANGE_PX = _env_int("BEACON_CLOSE_RANGE_PX", 220)
#: Hold fire if a visible teammate is within this perpendicular distance (px) of the
#: shot ray and closer than the target (friendly fire is ON; the bullet stops at the
#: first body). A bit wider than the sim's ~14px corridor for safety margin.
FRIENDLY_FIRE_CORRIDOR_PX = _int_tunable(
    "FRIENDLY_FIRE_CORRIDOR_PX",
    "BEACON_FF_CORRIDOR_PX",
    22,
    "Friendly-fire veto corridor around the shot ray, in pixels.",
    family="firefight",
    minimum=14,
)
#: Re-plan the A* path if the goal cell moves more than this many cells.
REPLAN_GOAL_CELLS = _env_int("BEACON_REPLAN_GOAL_CELLS", 2)
#: Frames of no navigation progress before forcing a re-plan + jitter.
STUCK_TICKS = _env_int("BEACON_STUCK_TICKS", 8)
#: Diagnostics cadence (frames between full-state CTF_DIAG snapshots).
DIAG_EVERY_TICKS = _env_int("BEACON_DIAG_EVERY_TICKS", 96)

# --- Belief: player tracks + danger field (groundwork — nothing gates on these yet) -
#: Drop a player track this many ticks after its last sighting (~5 s at 24 tps,
#: matching the baseline's track TTL).
TRACK_TTL_TICKS = _env_int("BEACON_TRACK_TTL_TICKS", 120)
#: Track association slack (px) on top of how far the player could have moved since
#: last seen (dt * max speed). Sightings farther than the gate start a NEW track.
TRACK_MATCH_SLACK_PX = 16
#: Don't difference a velocity across a sighting gap larger than this (ticks) — the
#: average over a long unseen stretch says nothing about their current motion.
TRACK_VEL_MAX_GAP_TICKS = 8
#: EMA weight of the newest velocity sample when smoothing a track's velocity.
TRACK_VEL_EMA = 0.5
#: Danger-field spread speed as a fraction of max player speed — the hot zone around
#: a lost sighting grows at roughly the speed the enemy could actually flee. <1 so
#: the danger zone lingers behind the enemy's true reachable front.
DANGER_DIFFUSION_FACTOR = _env_float("BEACON_DANGER_DIFFUSION_FACTOR", 0.75)
#: Danger cools with this exponential half-life (ticks); ~2 s at 24 tps.
DANGER_DECAY_HALF_LIFE_TICKS = _env_int("BEACON_DANGER_HALF_LIFE_TICKS", 48)
#: Stamp full danger within this radius (px) of each currently-visible enemy.
DANGER_STAMP_RADIUS_PX = 16
#: Nav-cells-per-side folded into one cell when tracing the danger grid (4 -> 39x21).
DANGER_TRACE_DOWNSAMPLE = 4

# --- Peek-fire-duck micro (v7) ------------------------------------------------------
# The baseline/focusfire lineage's edge: spend the gun's cooldown BEHIND a wall, pay
# the aim traverse in cover, and re-emerge with the shot pre-laid. Constants mirror
# players/baseline/baseline.nim (DuckRange, FreshShotTicks, Duck/PeekSearchCells).
#: Master switch — the single A/B bit for the v7 iteration.
PEEK_DUCK = _env_int("BEACON_PEEK_DUCK", 1) == 1
#: Duck from remembered threats within this range (px) while the gun is down.
DUCK_RANGE_PX = _env_int("BEACON_DUCK_RANGE_PX", 340)
#: Only duck from tracks seen this recently (ticks) — stale tracks don't pin us.
DUCK_THREAT_FRESH_TICKS = _env_int("BEACON_DUCK_THREAT_FRESH_TICKS", 30)
#: Only peek at tracks seen this recently (ticks; baseline FreshShotTicks).
PEEK_TARGET_FRESH_TICKS = _env_int("BEACON_PEEK_TARGET_FRESH_TICKS", 24)
#: Search radius (nav cells) for the duck/peek sidestep cell.
PEEK_DUCK_SEARCH_CELLS = _env_int("BEACON_PEEK_DUCK_SEARCH_CELLS", 3)
#: Within this distance (px) of the steal target, never duck/peek — grab speed wins
#: (mirrors the baseline's pocket-rush exemption).
PEEK_DUCK_RUSH_EXEMPT_PX = _env_int("BEACON_PEEK_DUCK_RUSH_EXEMPT_PX", 90)

# --- Lead aim (v10) -----------------------------------------------------------------
#: Master switch for velocity-lead aiming — the v10 accuracy iteration's A/B bit.
LEAD_AIM = _env_int("BEACON_LEAD_AIM", 1) == 1
#: Aim this many ticks ahead of a moving target: the 5-tick windup releases the
#: bullet late, plus ~1 tick of perception latency (baseline LeadTicks = 6).
LEAD_TICKS = _env_float("BEACON_LEAD_TICKS", 3.5)
#: Only lead with a velocity estimated over at least this many sightings — a
#: 2-frame velocity is one noisy difference.
LEAD_MIN_FRAMES = _env_int("BEACON_LEAD_MIN_FRAMES", 3)
#: Target-scoring range band fades to zero here. This is deliberately not a fire
#: gate: exact aim, wall, and friendly-fire geometry decide whether any visible
#: target is shootable, including across long base sightlines.
FF_RANGE_SCORE_FALLOFF_PX = 350

# --- Firefight target selection + focus claims --------------------------------------
# Firefight is a combat overlay, never a strategy rung: it changes which visible
# enemy the gun watches, not where the bot moves. Both switches default OFF so one
# uploaded image can supply clean control / scoring / scoring+claims A/B arms.
FIREFIGHT = _bool_tunable(
    "FIREFIGHT",
    "BEACON_FIREFIGHT",
    False,
    "Enable firefight state and scored gun-target selection.",
    family="firefight",
)
FOCUS_CLAIMS = _bool_tunable(
    "FOCUS_CLAIMS",
    "BEACON_FOCUS_CLAIMS",
    False,
    "Enable local F target claims as a soft scoring bias.",
    family="firefight",
)
#: Enter when a visible enemy is this close (or whenever under_fire is true).
#: Visible-enemy radius that activates scored target selection.
FF_RADIUS_PX = _int_tunable(
    "FF_RADIUS_PX",
    "BEACON_FF_RADIUS_PX",
    400,
    "Visible-enemy radius that triggers firefight state, in map pixels.",
    family="firefight",
    minimum=FF_RANGE_SCORE_FALLOFF_PX,
    maximum=SIGHTLINE_CAP_PX,
)
#: Stay in firefight this long after the last trigger (~2s at 24 ticks/s).
FF_DWELL_TICKS = _int_tunable(
    "FF_DWELL_TICKS",
    "BEACON_FF_DWELL_TICKS",
    48,
    "Ticks firefight remains active after its last trigger.",
    family="firefight",
    minimum=1,
)
#: Target latch: pay a short commitment before a merely-better challenger can win.
FF_TARGET_MIN_DWELL_TICKS = _int_tunable(
    "FF_TARGET_MIN_DWELL_TICKS",
    "BEACON_FF_TARGET_MIN_DWELL_TICKS",
    8,
    "Minimum ticks on a shootable target before a scored switch.",
    family="firefight",
    minimum=1,
)
#: Challenger score advantage required after the minimum dwell. The 0.12 claim
#: bonus can break an exact latched tie; a one-segment wound edge (0.25) remains
#: materially larger.
FF_TARGET_SWITCH_MARGIN = _float_tunable(
    "FF_TARGET_SWITCH_MARGIN",
    "BEACON_FF_TARGET_SWITCH_MARGIN",
    0.10,
    "Minimum score advantage required to switch a shootable latched target.",
    family="firefight",
    minimum=0.0,
)
#: Preferred target-scoring band. Targets beyond it remain shootable.
FF_RANGE_CLOSE_PX = _int_tunable(
    "FF_RANGE_CLOSE_PX",
    "BEACON_FF_RANGE_CLOSE_PX",
    120,
    "Range at or below which the range-band score is zero, in pixels.",
    family="firefight",
    minimum=0,
    maximum=FF_RANGE_SCORE_FALLOFF_PX,
)
FF_RANGE_IDEAL_MIN_PX = _int_tunable(
    "FF_RANGE_IDEAL_MIN_PX",
    "BEACON_FF_RANGE_IDEAL_MIN_PX",
    220,
    "Near edge of the peak target-scoring range band.",
    family="firefight",
    minimum=0,
    maximum=FF_RANGE_SCORE_FALLOFF_PX,
)
FF_RANGE_IDEAL_MAX_PX = _int_tunable(
    "FF_RANGE_IDEAL_MAX_PX",
    "BEACON_FF_RANGE_IDEAL_MAX_PX",
    300,
    "Far edge of the peak target-scoring range band.",
    family="firefight",
    minimum=0,
    maximum=FF_RANGE_SCORE_FALLOFF_PX,
)
#: Normalized target-score weights. Shootability is signed (-1 blocked/+1 clear):
#: 0.35 gives a 0.70 clear-vs-blocked swing, decisive over one wound level (0.25)
#: without drowning out wound/range in the A/B.
FF_WOUND_WEIGHT = _float_tunable(
    "FF_WOUND_WEIGHT",
    "BEACON_FF_WOUND_WEIGHT",
    0.50,
    "Weight for preferring enemies with fewer lit health-bar segments.",
    family="firefight",
    minimum=0.0,
)
FF_WOUND_UNKNOWN = _float_tunable(
    "FF_WOUND_UNKNOWN",
    "BEACON_FF_WOUND_UNKNOWN",
    0.15,
    "Normalized wound value used when an enemy HP bar is unresolved.",
    family="firefight",
    minimum=0.0,
    maximum=1.0,
)
FF_RANGE_WEIGHT = _float_tunable(
    "FF_RANGE_WEIGHT",
    "BEACON_FF_RANGE_WEIGHT",
    0.30,
    "Weight for preferring targets in the effective gun range band.",
    family="firefight",
    minimum=0.0,
)
FF_CLAIM_WEIGHT = _float_tunable(
    "FF_CLAIM_WEIGHT",
    "BEACON_FF_CLAIM_WEIGHT",
    0.12,
    "Bounded score bonus for matching a fresh local focus claim.",
    family="firefight",
    minimum=0.0,
)
FF_SHOOTABILITY_WEIGHT = _float_tunable(
    "FF_SHOOTABILITY_WEIGHT",
    "BEACON_FF_SHOOTABILITY_WEIGHT",
    0.35,
    "Weight for signed clear-versus-blocked shootability.",
    family="firefight",
    minimum=0.0,
)
FF_AIM_COST_WEIGHT = _float_tunable(
    "FF_AIM_COST_WEIGHT",
    "BEACON_FF_AIM_COST_WEIGHT",
    0.18,
    "Penalty weight for normalized aim traverse to the target.",
    family="firefight",
    minimum=0.0,
)
FF_SHIELD_WEIGHT = _float_tunable(
    "FF_SHIELD_WEIGHT",
    "BEACON_FF_SHIELD_WEIGHT",
    0.10,
    "Penalty weight for a visibly shielded target.",
    family="firefight",
    minimum=0.0,
)
#: Focus-claim clocks. The global chat interval is also 30 ticks; this cadence
#: therefore refreshes at the first available F slot without consuming extra chat.
FF_CLAIM_REBROADCAST_TICKS = _int_tunable(
    "FF_CLAIM_REBROADCAST_TICKS",
    "BEACON_FF_CLAIM_REBROADCAST_TICKS",
    30,
    "Minimum ticks between this bot's focus-claim broadcasts.",
    family="firefight",
    minimum=1,
)
FF_CLAIM_TTL_TICKS = _int_tunable(
    "FF_CLAIM_TTL_TICKS",
    "BEACON_FF_CLAIM_TTL_TICKS",
    72,
    "Ticks without a broadcast before a focus claim expires.",
    family="firefight",
    minimum=1,
)
#: An anonymous cell claim can move ~83px between 30-tick broadcasts at max
#: per-axis speed; 96px includes one-cell quantization margin.
FF_CLAIM_MATCH_PX = _int_tunable(
    "FF_CLAIM_MATCH_PX",
    "BEACON_FF_CLAIM_MATCH_PX",
    96,
    "Maximum position error for associating an anonymous focus claim.",
    family="firefight",
    minimum=NAV_CELL,
)
#: Claims are exclusive only in this bot's local fight, never team-global.
FF_CLAIM_LOCALITY_PX = _int_tunable(
    "FF_CLAIM_LOCALITY_PX",
    "BEACON_FF_CLAIM_LOCALITY_PX",
    400,
    "Receiver-to-target radius that scopes focus-claim exclusivity.",
    family="firefight",
    minimum=NAV_CELL,
)
#: Release an unobserved target quickly; aggregate deaths provide a faster but
#: deliberately corroborative path because the scoreboard cannot name the victim.
FF_TARGET_MISSING_TICKS = _int_tunable(
    "FF_TARGET_MISSING_TICKS",
    "BEACON_FF_TARGET_MISSING_TICKS",
    36,
    "Ticks unseen before a claimed target is released as missing.",
    family="firefight",
    minimum=1,
)
FF_DEATH_MISSING_TICKS = _int_tunable(
    "FF_DEATH_MISSING_TICKS",
    "BEACON_FF_DEATH_MISSING_TICKS",
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
        "FF_RANGE_SCORE_FALLOFF_PX <= firefight radius <= SIGHTLINE_CAP_PX.",
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
    TunableInvariant(
        "post_facing_requires_posts",
        "POST_FACING may be enabled only when POSTS is enabled.",
        family="spacing",
    ),
    TunableInvariant(
        "post_separation_exceeds_squad_separation",
        "Post separation must exceed squad separation, or the push-apart floor "
        "fights the chosen posts.",
        family="spacing",
    ),
    TunableInvariant(
        "post_separation_within_search_radius",
        "Post separation must fit inside the search radius, or only one post "
        "can ever be chosen.",
        family="spacing",
    ),
)


def tunable_spec(name_or_env: str) -> TunableSpec:
    """Look up a registry entry by config name or environment variable."""
    by_name = TUNABLE_REGISTRY.get(name_or_env)
    if by_name is not None:
        return by_name
    by_env = next(
        (
            spec
            for spec in TUNABLE_REGISTRY.values()
            if spec.env_var == name_or_env
        ),
        None,
    )
    if by_env is None:
        raise ValueError(f"unknown tunable: {name_or_env}")
    return by_env


def validate_tunable_values(
    assignments: Mapping[str, object] | None = None,
) -> dict[str, TunableValue]:
    """Normalize a partial assignment against defaults and validate all invariants.

    Keys may be config names (``FF_WOUND_WEIGHT``) or environment names
    (``BEACON_FF_WOUND_WEIGHT``). The returned mapping always uses config names.
    """
    values = {
        name: spec.coerce(spec.default)
        for name, spec in TUNABLE_REGISTRY.items()
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
        FF_RANGE_SCORE_FALLOFF_PX
        <= values["FF_RADIUS_PX"]
        <= SIGHTLINE_CAP_PX,
        "firefight_radius_geometry",
    )
    require(
        values["FF_TARGET_MIN_DWELL_TICKS"] <= values["FF_DWELL_TICKS"],
        "target_latch_within_mode",
    )
    require(
        values["FF_CLAIM_REBROADCAST_TICKS"]
        < values["FF_CLAIM_TTL_TICKS"],
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
    # Spacing is the other half of the focus-fire friendly-fire tension: posts
    # decide how far apart converging shooters stand, and the separation bias is
    # the floor that unstacks them. If separation exceeded post spacing the two
    # would fight each other every tick; if post separation exceeded the search
    # radius only one post could ever qualify and the squad would restack.
    # These knobs register later in this module than the firefight family, so a
    # validate call made during import (before the spacing block runs) sees them
    # absent. Skip rather than KeyError; by the time any caller validates a real
    # sweep assignment the whole registry exists.
    if {"POSTS", "POST_FACING"} <= values.keys():
        require(
            values["POSTS"] or not values["POST_FACING"],
            "post_facing_requires_posts",
        )
    if {"POST_MIN_SEPARATION_PX", "SQUAD_SEPARATION_PX", "POST_SEARCH_RADIUS_PX"} <= values.keys():
        require(
            values["POST_MIN_SEPARATION_PX"] > values["SQUAD_SEPARATION_PX"],
            "post_separation_exceeds_squad_separation",
        )
        require(
            values["POST_MIN_SEPARATION_PX"] <= values["POST_SEARCH_RADIUS_PX"],
            "post_separation_within_search_radius",
        )
    return values


# Validate the actual environment-backed values too. A malformed hosted arm should
# fail at process startup, while the tuning CLI catches it before upload.
validate_tunable_values(
    {name: globals()[name] for name in TUNABLE_REGISTRY}
)

# --- Item skills (v10) ---------------------------------------------------------------
#: Master switch for the item system (fetch + use) — the other v10 A/B bit.
ITEMS = _env_int("BEACON_ITEMS", 1) == 1
#: Add nearby non-owner grenade pickups after legacy item decisions decline.
#: When disabled, the general route scorer remains sampled shadow telemetry.
ITEM_CONVENIENCE = _env_int("BEACON_ITEM_CONVENIENCE", 0) == 1
#: Shadow scoring is observability, not control; 2 Hz is enough to characterize
#: opportunities without bloating every dense action-frame snapshot.
ITEM_SHADOW_EVERY_TICKS = _env_int("BEACON_ITEM_SHADOW_EVERY_TICKS", 12)
#: Maximum extra walkable-route distance for an ordinary convenient pickup.
ITEM_CONVENIENT_DETOUR_PX = _env_int("BEACON_ITEM_CONVENIENT_DETOUR_PX", 48)
#: Additive convenience is deliberately limited to items only a few steps away.
ITEM_INCIDENTAL_ROUTE_PX = _env_int("BEACON_ITEM_INCIDENTAL_ROUTE_PX", 64)
#: Fresh respawns may reach a little farther for their nearby corner grenade.
ITEM_RESPAWN_INCIDENTAL_ROUTE_PX = _env_int(
    "BEACON_ITEM_RESPAWN_INCIDENTAL_ROUTE_PX", 96
)
#: A settled post is load-bearing; only take pickups that are nearly route-free.
ITEM_POST_DETOUR_PX = _env_int("BEACON_ITEM_POST_DETOUR_PX", 48)
#: Before rejoining after a respawn, own-side pickups receive this extra allowance.
ITEM_RESPAWN_BONUS_PX = _env_int("BEACON_ITEM_RESPAWN_BONUS_PX", 240)
#: Opening window in which a newly spawned bot can cheaply collect an own-side item.
ITEM_RESPAWN_WINDOW_TICKS = _env_int("BEACON_ITEM_RESPAWN_WINDOW_TICKS", 240)
#: Spray friendly-fire doctrine is not complete yet, so deliberate fetches remain
#: limited to pickups that are effectively underfoot.
ITEM_ARC_DETOUR_PX = _env_int("BEACON_ITEM_ARC_DETOUR_PX", 32)
#: Preserve v48's established shield/grenade owners while the generic scorer
#: broadens only genuinely cheap opportunities for the other seats.
ITEM_ASSIGNED_DETOUR_PX = _env_int("BEACON_ITEM_ASSIGNED_DETOUR_PX", 420)
#: Yield when a visible teammate has at least this much shorter a route to the item.
ITEM_YIELD_MARGIN_PX = _env_int("BEACON_ITEM_YIELD_MARGIN_PX", 16)
#: Low-health center occupants may take a somewhat larger marginal med-kit detour.
MEDKIT_CONVENIENT_DETOUR_PX = _env_int("BEACON_MEDKIT_CONVENIENT_DETOUR_PX", 420)
#: Grenade throwing (needs ITEMS): lob at wall-blocked remembered enemies.
GRENADE_THROW = _env_int("BEACON_GRENADE_THROW", 1) == 1
#: Never lob shorter than this (px) — the 40px blast hurts the thrower too.
GRENADE_MIN_THROW_PX = 90
#: Release the throw once aim is within this error (brads).
GRENADE_AIM_ERR_BRADS = _env_int("BEACON_GRENADE_AIM_ERR_BRADS", 4)
#: Abort insurance: force-release a charge this many ticks past full charge.
GRENADE_FORCE_RELEASE_TICKS = 16
#: Only lob at tracks seen this recently (ticks).
GRENADE_TARGET_FRESH_TICKS = _env_int("BEACON_GRENADE_TARGET_FRESH_TICKS", 30)
#: A teammate track must be this fresh to veto a predicted landing.
GRENADE_TEAMMATE_FRESH_TICKS = _env_int(
    "BEACON_GRENADE_TEAMMATE_FRESH_TICKS", 12
)
#: An open single is worth a cooldown throw only when the blast can finish it.
GRENADE_SINGLE_HP_MAX = _env_int("BEACON_GRENADE_SINGLE_HP_MAX", 2)
#: Spray-can geometry from sim.nim. Pickups are NOT assigned by default (the
#: spray disables the gun); these constants only govern fighting once carried.
ARC_FIRE_RANGE_PX = 136
ARC_MAX_WIDTH_PX = 68
#: Local fighting pursuit only: close on an already-visible spray target, but
#: never turn the weapon into a strategic movement objective across the map.
ARC_PURSUIT_RANGE_PX = 400
ARC_IDEAL_RANGE_PX = 100

# --- Hearing (v16) --------------------------------------------------------------------
#: Master switch for audio perception + its consumers — the v16 A/B bit.
HEARING = _env_int("BEACON_HEARING", 1) == 1
#: Sound rings are jittered up to ±20px from the true landing (SoundRingJitter) and
#: a ring is STABLE per event — sightings within this radius of a known event are
#: the same event, not a new shot. Slightly over 2*jitter*sqrt(2) would over-merge;
#: distinct shots land spread out, so one jitter-diameter is the sweet spot.
HEARD_MATCH_PX = _env_int("BEACON_HEARD_MATCH_PX", 40)
#: Forget a heard event this many ticks after its ring was last in frame. Rings
#: live ~12 ticks; this keeps the EVENT around long enough to inform behavior
#: (~2.5s — comparable to the danger half-life).
HEARD_TTL_TICKS = _env_int("BEACON_HEARD_TTL_TICKS", 60)
#: Danger stamped per heard event: weaker than a SEEN enemy's 1.0 stamp (a ring is
#: team-anonymous — it may be OUR OWN fire landing) and wider (jitter + "the shooter
#: is somewhere with LoS to this spot", not at the spot).
HEARD_DANGER_HEAT = _env_float("BEACON_HEARD_DANGER_HEAT", 0.5)
HEARD_DANGER_RADIUS_PX = _env_int("BEACON_HEARD_DANGER_RADIUS_PX", 32)
#: Duck-on-heard-fire (the v16 behavior consumer): while the gun is DOWN, a fresh
#: heard impact within this range of us counts as a duck threat even with no seen
#: enemy — bullets are landing near us, so someone has an angle on our area.
HEARD_DUCK_RANGE_PX = _env_int("BEACON_HEARD_DUCK_RANGE_PX", 180)
#: Only duck from impacts first heard this recently (ticks).
HEARD_DUCK_FRESH_TICKS = _env_int("BEACON_HEARD_DUCK_FRESH_TICKS", 24)

# --- Chat (v18) -----------------------------------------------------------------------
#: Master switch for the team-shout protocol (send + decode) — the v18 A/B bit.
CHAT = _env_int("BEACON_CHAT", 1) == 1
#: Self-imposed minimum ticks between our shouts (server enforces 24 = 1/s; a bit
#: above that keeps the single live bubble current for readers).
CHAT_MIN_INTERVAL_TICKS = _env_int("BEACON_CHAT_MIN_INTERVAL_TICKS", 30)
#: E (enemy seen) edge trigger: after shouting, don't re-shout until vision has
#: been enemy-free this long (re-arm) AND this long since the last E (cooldown) —
#: a peek-ducking enemy flickering in/out of the cone doesn't retrigger spam.
CHAT_ENEMY_REARM_TICKS = _env_int("BEACON_CHAT_ENEMY_REARM_TICKS", 48)
CHAT_ENEMY_RESHOUT_TICKS = _env_int("BEACON_CHAT_ENEMY_RESHOUT_TICKS", 72)
#: Decoded fixes expire this many ticks after they were heard.
CHAT_FIX_TTL_TICKS = _env_int("BEACON_CHAT_FIX_TTL_TICKS", 96)
#: A bubble persists ~3s (72 frames); the same (sender, text) within this window
#: is one shout, not a repeat. Just over bubble lifetime.
CHAT_BUBBLE_DEDUP_TICKS = _env_int("BEACON_CHAT_BUBBLE_DEDUP_TICKS", 80)
#: "Under fire": a heard impact within this range of us this recently.
UNDER_FIRE_RANGE_PX = _env_int("BEACON_UNDER_FIRE_RANGE_PX", 90)
UNDER_FIRE_FRESH_TICKS = _env_int("BEACON_UNDER_FIRE_FRESH_TICKS", 24)
#: Decode ENEMY shout positions as sighting-grade enemy fixes (their payload is
#: untrusted, but the bubble itself is a live position ±20px). Default ON.
CHAT_ENEMY_BUBBLE_FIX = _env_int("BEACON_CHAT_ENEMY_BUBBLE_FIX", 1) == 1
#: Grenade warnings from teammates: stay this far (px) from the shouted landing
#: cell until the warning ages out (blast 52px + margin).
GRENADE_WARN_CLEAR_PX = _env_int("BEACON_GRENADE_WARN_CLEAR_PX", 80)
GRENADE_WARN_TTL_TICKS = _env_int("BEACON_GRENADE_WARN_TTL_TICKS", 72)

# --- Squads (v19) ---------------------------------------------------------------------
#: Master switch for squad play (formation forces, wait-gating, aim sectors).
#: OFF by default since v29 (human call, 2026-07-27): the squad layer produced
#: stacked-then-scattered shapes vs h035's disciplined midline while several
#: members hung back on decay-backoff; rolled back to the pre-squad static role
#: split until the traced batches explain the coordination failure. Re-enable
#: via BEACON_SQUADS=1 / BEACON_SQUAD_COMMAND=1 for A/Bs.
SQUADS = _env_int("BEACON_SQUADS", 0) == 1
#: Cohesion: want >= MIN_BUDDIES teammates within COHESION_PX; below that, bias
#: movement toward the nearest teammate instead of pushing alone.
SQUAD_COHESION_PX = _env_int("BEACON_SQUAD_COHESION_PX", 120)
SQUAD_MIN_BUDDIES = _env_int("BEACON_SQUAD_MIN_BUDDIES", 1)
#: Separation: below this, steer apart (grenade blast 52px; bodies block shots).
#: Registered as a SPACING tunable: it is one of the two sides of the focus-fire
#: friendly-fire tension (converging fire on one target makes mutual corridor
#: blocking likelier), so it must be sweepable jointly with the firefight weights.
SQUAD_SEPARATION_PX = _int_tunable(
    "SQUAD_SEPARATION_PX",
    "BEACON_SQUAD_SEPARATION_PX",
    40,
    "Teammate distance below which a bot steers apart, in map pixels.",
    family="spacing",
    minimum=16,
    maximum=120,
)
#: Per-rank spread of a squad's ordered position (v25): members offset the shared
#: order point by rank along y (0 / +SPREAD / -SPREAD), so a 3-man squad holds a
#: short line instead of one cell. Must exceed SEPARATION_PX (or the separation
#: force fights the anchors) and the 52px grenade blast diameter matters too:
#: at 70px spacing one grenade can no longer hit two of us.
SQUAD_SPREAD_PX = _env_int("BEACON_SQUAD_SPREAD_PX", 70)
#: Attackers rally at this x on their own side before committing (mirror for blue).
SQUAD_RALLY_X = _env_int("BEACON_SQUAD_RALLY_X", 450)
#: Give up waiting for buddies after this long (dead mate: 72t respawn + walk).
SQUAD_WAIT_TIMEOUT_TICKS = _env_int("BEACON_SQUAD_WAIT_TIMEOUT_TICKS", 150)
#: Wave-gating (v19/v20): OFF by default since v21 (human call) — the tempo cost
#: under maxTicks=5000 outweighed the synchronization benefit, and squads now
#: cohere via nameplate identity instead. The tick-window machinery stays for a
#: future game-state-reactive gate; re-enable via BEACON_SQUAD_WAVE_GATE=1.
SQUAD_WAVE_GATE = _env_int("BEACON_SQUAD_WAVE_GATE", 0) == 1
SQUAD_WAVE_PERIOD_TICKS = _env_int("BEACON_SQUAD_WAVE_PERIOD_TICKS", 120)
SQUAD_WAVE_WINDOW_TICKS = _env_int("BEACON_SQUAD_WAVE_WINDOW_TICKS", 36)
#: Aim-sector offset per rank step (brads); 50 ≈ 70°, complements the ±45° cone.
SQUAD_SECTOR_BRADS = _env_int("BEACON_SQUAD_SECTOR_BRADS", 50)

# --- Squad command (v22): leader orders + presence pings + respawn discipline --------
#: Master switch for the leader/order/rejoin layer — the v22 A/B bit.
#: OFF by default since v29 (see SQUADS above; same rollback).
SQUAD_COMMAND = _env_int("BEACON_SQUAD_COMMAND", 0) == 1

# --- Battle-plan interpreter (v30) ----------------------------------------------------
#: The plan to execute, by name (beacon/plans/<name>.json baked into the image, or
#: the lab's battle_plans/ when running from the repo). Empty = no plan (static split).
PLAN_NAME = os.getenv("BEACON_PLAN", "staged_push_top").strip()
#: "I reached my phase target" radius (px) — the per-bot milestone.
PLAN_ARRIVE_PX = _env_int("BEACON_PLAN_ARRIVE_PX", 60)
#: Phase clock fallback: advance regardless after this many ticks in one phase
#: (the v19 rally-gate lesson — every stage gate needs a timeout). ~37s.
PLAN_PHASE_TIMEOUT_TICKS = _env_int("BEACON_PLAN_PHASE_TIMEOUT_TICKS", 900)
#: Buddy-wait (v31): a bot on a DANGEROUS plan move (target on the enemy half)
#: with no group-mate confirmed within this radius pauses instead of pushing
#: alone. Confirmation = a visible identity badge or a fresh identity track.
PLAN_BUDDY_RADIUS_PX = _env_int("BEACON_PLAN_BUDDY_RADIUS_PX", 170)
#: …but never forever (v19): per phase, wait at most this many ticks total,
#: then push regardless. ~6s.
PLAN_BUDDY_WAIT_TICKS = _env_int("BEACON_PLAN_BUDDY_WAIT_TICKS", 150)

#: Anti-turtle discipline. After 60% of a 5,000-tick game, a bot that has
#: established its terminal plan post treats an enemy seen outside its lineup
#: on at most this fraction of alive ticks as a base turtle. It then keeps the
#: rally as a defensive hold instead of converting that control into a base
#: assault. The separate life-gap gate applies immediately: three lives is one
#: whole player and is the smallest meaningful "handful" at team scale.
ANTI_TURTLE = _env_int("BEACON_ANTI_TURTLE", 1) == 1
ANTI_TURTLE_MIN_TICK = _env_int("BEACON_ANTI_TURTLE_MIN_TICK", 3000)
ANTI_TURTLE_OUTSIDE_RATE_MAX = _env_float(
    "BEACON_ANTI_TURTLE_OUTSIDE_RATE_MAX", 0.08
)
BASE_ASSAULT_LIFE_DEFICIT = _env_int("BEACON_BASE_ASSAULT_LIFE_DEFICIT", 3)
#: Inner edge of each lineup wall: beyond this boundary is the defended base.
BASE_FRONT_X = {"red": 295, "blue": 939}

# --- Posts: covered sightlines near tactical waypoints -----------------------------
#: Master switches. Position selection and facing are separate so one image can
#: isolate whether better ground or the narrower lane watch changes the outcome.
POSTS = _bool_tunable(
    "POSTS",
    "BEACON_POSTS",
    False,
    "Enable covered-post selection near plan/order/hold waypoints.",
    family="spacing",
)
POST_FACING = _bool_tunable(
    "POST_FACING",
    "BEACON_POST_FACING",
    False,
    "Centre the aim sweep on a settled post's watched sightline.",
    family="spacing",
)
#: Candidate geometry around the waypoint/search centre. Both are SPACING
#: tunables: post separation is how far apart converging shooters end up, which
#: is the other side of the focus-fire friendly-fire tension (see
#: SQUAD_SEPARATION_PX). Sweep them jointly with the firefight weights.
POST_SEARCH_RADIUS_PX = _int_tunable(
    "POST_SEARCH_RADIUS_PX",
    "BEACON_POST_SEARCH_RADIUS_PX",
    110,
    "Radius around a waypoint searched for candidate posts, in map pixels.",
    family="spacing",
    minimum=32,
    maximum=240,
)
POST_MIN_SEPARATION_PX = _int_tunable(
    "POST_MIN_SEPARATION_PX",
    "BEACON_POST_MIN_SEPARATION_PX",
    56,
    "Minimum distance between two chosen posts, in map pixels.",
    family="spacing",
    minimum=24,
    maximum=160,
)
#: Four-term score. Reach and cover retain the prototype weights; stance favors
#: ground forward along the watched lane for both push and hold posts, while
#: danger penalizes locally hot ground.
POST_REACH_WEIGHT = _env_float("BEACON_POST_REACH_WEIGHT", 0.55)
POST_COVER_WEIGHT = _env_float("BEACON_POST_COVER_WEIGHT", 0.45)
POST_STANCE_WEIGHT = _env_float("BEACON_POST_STANCE_WEIGHT", 0.18)
POST_DANGER_WEIGHT = _env_float("BEACON_POST_DANGER_WEIGHT", 0.20)
POST_EXPOSURE_WEIGHT = _env_float("BEACON_POST_EXPOSURE_WEIGHT", 1.25)
POST_COVER_CAP_PX = _env_int("BEACON_POST_COVER_CAP_PX", 64)
#: Reject an open firing lane with no flank wall, or a blind pocket with no
#: forward reach, instead of calling every nearby walkable cell a post.
POST_MIN_REACH_PX = _env_int("BEACON_POST_MIN_REACH_PX", 80)
POST_MIN_COVER_SCORE = _env_float("BEACON_POST_MIN_COVER_SCORE", 0.25)
POST_MIN_SCORE = _env_float("BEACON_POST_MIN_SCORE", 0.20)
#: A post is settled within this distance. Minimum dwell affects RE-SELECTION
#: only; plan milestones observe arrival at the post immediately.
POST_SETTLE_PX = _env_int("BEACON_POST_SETTLE_PX", 12)
POST_MIN_DWELL_TICKS = _env_int("BEACON_POST_MIN_DWELL_TICKS", 240)
POST_REEVALUATE_TICKS = _env_int("BEACON_POST_REEVALUATE_TICKS", 120)
POST_SWITCH_MARGIN = _env_float("BEACON_POST_SWITCH_MARGIN", 0.20)
#: Live threat evidence and direction hysteresis.
POST_THREAT_FRESH_TICKS = _env_int("BEACON_POST_THREAT_FRESH_TICKS", 48)
POST_THREAT_HYSTERESIS_DIRECTIONS = _env_int(
    "BEACON_POST_THREAT_HYSTERESIS_DIRECTIONS", 4
)
POST_DANGER_GRADIENT_PX = _env_int("BEACON_POST_DANGER_GRADIENT_PX", 64)
POST_DANGER_GRADIENT_MIN = _env_float("BEACON_POST_DANGER_GRADIENT_MIN", 0.10)
#: K-claim coordination. A dead or preempted claimant stops refreshing and frees
#: its post on the TTL clock.
POST_CLAIM_REBROADCAST_TICKS = _env_int(
    "BEACON_POST_CLAIM_REBROADCAST_TICKS", 48
)
POST_CLAIM_TTL_TICKS = _env_int("BEACON_POST_CLAIM_TTL_TICKS", 120)
#: A visible enemy actually standing on the candidate makes it contested ground,
#: not a post to path directly onto.
POST_ENEMY_OCCUPIED_PX = _env_int("BEACON_POST_ENEMY_OCCUPIED_PX", 24)
#: Settled posts dwell on the primary watched lane and the best open baked ray
#: on either side. Repeating the primary direction gives it half of scan time.
POST_SCAN_DWELL_TICKS = _env_int("BEACON_POST_SCAN_DWELL_TICKS", 18)
POST_SCAN_MIN_OFFSET_DIRECTIONS = _env_int(
    "BEACON_POST_SCAN_MIN_OFFSET_DIRECTIONS", 2
)
POST_SCAN_MAX_OFFSET_DIRECTIONS = _env_int(
    "BEACON_POST_SCAN_MAX_OFFSET_DIRECTIONS", 6
)
#: Convert trigger (v26): when the ENEMY team's lives remaining (24 - their deaths,
#: read off the fog-independent team scoreboard) drop to this or below, leaders
#: order an all-in HUNT — the wipe is in reach and under GV21 a draw pays -1 like a
#: loss, so once we're this far ahead aggression is nearly free (worst case the -1
#: we'd get anyway; upside +1). v25's draws all sat at enemy 1-3 lives, holding.
CONVERT_ENEMY_LIVES = _env_int("BEACON_CONVERT_ENEMY_LIVES", 6)
#: Total lives a full 8-player team starts with (8 x 3) — the deaths->lives base.
TEAM_TOTAL_LIVES = 24
#: An order (O message) is obeyed this long after it was heard/issued.
ORDER_TTL_TICKS = _env_int("BEACON_ORDER_TTL_TICKS", 240)
#: Leaders re-broadcast their current order at this cadence (also on change).
ORDER_REBROADCAST_TICKS = _env_int("BEACON_ORDER_REBROADCAST_TICKS", 72)
#: Presence pings (P message): each agent pings at this cadence when it has had
#: nothing higher-priority to say for the interval.
PING_INTERVAL_TICKS = _env_int("BEACON_PING_INTERVAL_TICKS", 60)
#: The leader treats a squadmate as DOWN when neither a badge sighting nor a
#: ping/order has been seen from that seat for this long (~3 ping periods).
PRESENCE_STALE_TICKS = _env_int("BEACON_PRESENCE_STALE_TICKS", 190)
#: Back-off: when a pushing squad loses a member, the leader orders HOLD at its
#: position stepped this far back toward home.
BACKOFF_STEP_PX = _env_int("BEACON_BACKOFF_STEP_PX", 70)
#: Rejoin (respawn discipline): a respawned agent moves to its rejoin point and
#: gives up after this long without squad contact, resuming normal orders.
REJOIN_TIMEOUT_TICKS = _env_int("BEACON_REJOIN_TIMEOUT_TICKS", 360)
#: Rejoin ends when a squadmate is confirmed within this range (badge or ping).
REJOIN_CONTACT_PX = _env_int("BEACON_REJOIN_CONTACT_PX", 160)
#: Default squad-hold anchors (v24): A holds the TOP side lane, B the BOTTOM,
#: both on the choke line; C pushes the middle. Y values match the map's lane
#: structure (obstacles column y-bands; map height 659).
SQUAD_SIDE_HOLD_Y_TOP = _env_int("BEACON_SQUAD_SIDE_HOLD_Y_TOP", 165)
SQUAD_SIDE_HOLD_Y_BOTTOM = _env_int("BEACON_SQUAD_SIDE_HOLD_Y_BOTTOM", 494)

# --- Roles (v2) -------------------------------------------------------------------
# CTF games (vs the baseline) are decided by WIPE, not capture (see TENTATIVE_LESSONS):
# nobody captures, so the team that keeps its lives wins. v1's 8 identical rushers died
# on the enemy's defended pedestal (far respawn walk-back). v2 splits seats into a
# defensive contingent that holds cover on OUR turf (close respawns; the enemy now dies
# attacking us) and attackers that still push the flag.
#: How many of the 8 per-team seats defend (seats 0..N-1). 3 defenders hold our turf;
#: 5 attackers push + ESCORT the carrier home (v5 — 5 solo attackers grabbed the flag vs
#: the baseline but died before delivery; more attackers moving the flag home together is
#: the fix). The enemy rarely attacks our flag (captures ~0 both sides), so heavy defense
#: was wasted bodies. A/B via BEACON_DEFENDERS.
DEFENDER_COUNT = _env_int("BEACON_DEFENDERS", 3)
#: Defender hold line — x on each team's own side (mirror of the baseline's choke).
CHOKE_X = {"red": 390, "blue": MAP_W - 1 - 390}
#: Defenders spread their hold points across this y-band (avoids stacking on one cell).
HOLD_Y_MIN = 150
HOLD_Y_MAX = 510
#: A defender within this distance (px) of its hold point stops advancing and holds.
HOLD_ARRIVE_PX = _env_int("BEACON_HOLD_ARRIVE_PX", 28)

__all__ = [name for name in dir() if name.isupper()]
