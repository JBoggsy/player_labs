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

# --- Roles (v2) -------------------------------------------------------------------
# CTF games (vs the baseline) are decided by WIPE, not capture (see TENTATIVE_LESSONS):
# nobody captures, so the team that keeps its lives wins. v1's 8 identical rushers died
# on the enemy's defended pedestal (far respawn walk-back). v2 splits seats into a
# defensive contingent that holds cover on OUR turf (close respawns; the enemy now dies
# attacking us) and attackers that still push the flag.
#: How many of the 8 per-team seats defend (seats 0..N-1). Default 5 = defensive bias.
DEFENDER_COUNT = _env_int("BEACON_DEFENDERS", 5)
#: Defender hold line — x on each team's own side (mirror of the baseline's choke).
CHOKE_X = {"red": 390, "blue": MAP_W - 1 - 390}
#: Defenders spread their hold points across this y-band (avoids stacking on one cell).
HOLD_Y_MIN = 150
HOLD_Y_MAX = 510
#: A defender within this distance (px) of its hold point stops advancing and holds.
HOLD_ARRIVE_PX = _env_int("BEACON_HOLD_ARRIVE_PX", 28)

__all__ = [name for name in dir() if name.isupper()]
