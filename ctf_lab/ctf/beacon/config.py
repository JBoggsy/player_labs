"""Tunable knobs and static game geometry for beacon.

Knobs live here, isolated from logic, so each iteration is attributable and can be
A/B'd (root AGENTS.md). Geometry constants mirror ``src/ctf/sim.nim`` at the pinned
``CTF_REF`` and must match the deployed arena.
"""

from __future__ import annotations

import os

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

# --- Observation wire format (hd.nim, game >= 0.6.0) -------------------------------
#: HD pixels per map pixel on the zoomable map/fog layers (hd.nim RenderScale).
#: Object coordinates and sprite sizes arrive multiplied by this; perception divides
#: once at the seam (perception._center) so everything downstream — nav.npz, all
#: thresholds, belief, traces — stays in map pixels. (The invisible "walkability map"
#: sprite is documented unscaled, but we never read it: nav is baked offline.)
RENDER_SCALE = 3

# --- Aim / vision (sim.nim) -------------------------------------------------------
AIM_BRADS_TURN = 256  # brads per full turn
AIM_TURN_RATE = 5  # brads/tick a held rotate button turns aim (must match server)
VISION_CONE_HALF_DEG = 45  # forward wedge half-angle
VISION_BUBBLE = 90  # omni bubble radius, px
#: Spawn aim by team: Red faces east (0), Blue faces west (128).
SPAWN_AIM = {"red": 0, "blue": AIM_BRADS_TURN // 2}


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


# --- Tunable behaviour knobs (env-overridable for A/B at upload time) -------------
#: Lighthouse sweep half-arc, in brads (±). 32 brads ≈ ±45°.
SWEEP_HALF_ARC = _env_int("BEACON_SWEEP_HALF_ARC", 32)
#: Deadband: don't bother rotating to close an aim error smaller than this (brads).
AIM_DEADBAND = _env_int("BEACON_AIM_DEADBAND", 3)
#: Fire only when the target is within this perpendicular slack of the aim ray (px),
#: i.e. range * sin(angle_error) <= this. Matches the baseline's fire-gate idea.
FIRE_SLACK_PX = _env_int("BEACON_FIRE_SLACK_PX", 11)
#: Below this range (px) an enemy is close enough to fire on with a looser gate.
CLOSE_RANGE_PX = _env_int("BEACON_CLOSE_RANGE_PX", 220)
#: Hold fire if a visible teammate is within this perpendicular distance (px) of the
#: shot ray and closer than the target (friendly fire is ON; the bullet stops at the
#: first body). A bit wider than the sim's ~14px corridor for safety margin.
FRIENDLY_FIRE_CORRIDOR_PX = _env_int("BEACON_FF_CORRIDOR_PX", 22)
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
