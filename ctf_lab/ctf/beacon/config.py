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
VISION_CONE_HALF_DEG = 60  # forward wedge half-angle (config.json, 60 since 0.7.4x)
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


# --- Tunable behaviour knobs (env-overridable for A/B at upload time) -------------
#: Lighthouse sweep half-arc, in brads (±). 32 brads ≈ ±45°.
SWEEP_HALF_ARC = _env_int("BEACON_SWEEP_HALF_ARC", 32)
#: Deadband: don't bother rotating to close an aim error smaller than this (brads).
AIM_DEADBAND = _env_int("BEACON_AIM_DEADBAND", 3)
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
LEAD_TICKS = _env_float("BEACON_LEAD_TICKS", 6.0)
#: Only lead with a velocity estimated over at least this many sightings — a
#: 2-frame velocity is one noisy difference.
LEAD_MIN_FRAMES = _env_int("BEACON_LEAD_MIN_FRAMES", 3)
#: Hold fire beyond this range (px). The hit corridor is 14px (BulletHalfWidth 8 +
#: PlayerHalf 6) and aim settles only to ~2-3 brads (5-brad rotation steps, 3-brad
#: deadband), so beyond ~350px the expected angular miss exceeds the corridor and a
#: shot is luck — v10 sprayed 260 shots/ep at 0.23 accuracy, mostly long-range
#: defender fire. Withholding those shots trades spray for hit rate (the gun is
#: still map-wide for reactive snap shots INSIDE the gate).
FIRE_MAX_RANGE_PX = _env_int("BEACON_FIRE_MAX_RANGE_PX", 350)

# --- Item skills (v10) ---------------------------------------------------------------
#: Master switch for the item system (fetch + use) — the other v10 A/B bit.
ITEMS = _env_int("BEACON_ITEMS", 1) == 1
#: Max detour (px, straight-line) an agent diverts to fetch its ASSIGNED item.
ITEM_DETOUR_PX = _env_int("BEACON_ITEM_DETOUR_PX", 420)
#: Max detour (px) a HURT agent diverts to a center-line med kit.
MEDKIT_DETOUR_PX = _env_int("BEACON_MEDKIT_DETOUR_PX", 420)
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
#: Plasma arc: fire the cone when a visible enemy is inside this range (px;
#: sim reach is 136 — use a bit less so the cone's width has caught up) and
#: within this aim error (brads). Arc pickups are NOT assigned by default (the
#: arc disables the gun); this only governs use if one is somehow carried.
ARC_FIRE_RANGE_PX = 120
ARC_AIM_ERR_BRADS = 6

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
SQUADS = _env_int("BEACON_SQUADS", 1) == 1
#: Cohesion: want >= MIN_BUDDIES teammates within COHESION_PX; below that, bias
#: movement toward the nearest teammate instead of pushing alone.
SQUAD_COHESION_PX = _env_int("BEACON_SQUAD_COHESION_PX", 120)
SQUAD_MIN_BUDDIES = _env_int("BEACON_SQUAD_MIN_BUDDIES", 1)
#: Separation: below this, steer apart (grenade blast 52px; bodies block shots).
SQUAD_SEPARATION_PX = _env_int("BEACON_SQUAD_SEPARATION_PX", 40)
#: Attackers rally at this x on their own side before committing (mirror for blue).
SQUAD_RALLY_X = _env_int("BEACON_SQUAD_RALLY_X", 450)
#: Give up waiting for buddies after this long (dead mate: 72t respawn + walk).
SQUAD_WAIT_TIMEOUT_TICKS = _env_int("BEACON_SQUAD_WAIT_TIMEOUT_TICKS", 150)
#: Wave windows (v19.1): pushes commit only during the first WINDOW ticks of each
#: PERIOD (tick-synchronized — the one squad signal fog can't hide). An attacker
#: reaching the rally mid-period holds up to PERIOD-WINDOW ticks; everyone who
#: gathered commits together at the window edge.
SQUAD_WAVE_PERIOD_TICKS = _env_int("BEACON_SQUAD_WAVE_PERIOD_TICKS", 120)
SQUAD_WAVE_WINDOW_TICKS = _env_int("BEACON_SQUAD_WAVE_WINDOW_TICKS", 36)
#: Aim-sector offset per rank step (brads); 50 ≈ 70°, complements the 60° cone.
SQUAD_SECTOR_BRADS = _env_int("BEACON_SQUAD_SECTOR_BRADS", 50)

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
