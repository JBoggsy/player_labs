"""Shared imposter victim-selection and witness logic (design §7.2, §10).

Hunt commits to a *victim* and stalks it, striking only when the kill would go
**unwitnessed**. This module is the single source of truth for: which crewmate to
commit to (``select_victim`` — the most-isolated visible straggler, easiest to
finish off unseen), whether a kill on a given target is currently unwitnessed
(``unwitnessed``), and whether any victim is visible or trackable right now.

A witness is definitional, not a distance/recency estimate: ``belief.roster`` only
records another player's position on ticks where *our own* vision actually saw them
(``types.py``'s ``PlayerRecord.record`` is fed straight from the percept), and Crewrift
vision is symmetric (same camera-frame + line-of-sight check run from either side — see
``docs/designs/vision-model.md``). So a currently-visible live non-teammate crewmate can
see the kill too, and counting how many are visible right now is exact — no radius or
staleness window is needed to approximate "nearby and probably still watching."

The witness *tolerance* is not fixed: at zero urgency a kill still proceeds with up to
``allowed_witnesses_min()`` (1) witnesses visible — a single onlooker no longer vetoes a
strike — ramping linearly as urgency builds (``kill_urgency_ticks``) to
``allowed_witnesses_max()`` (6) by full urgency. Since this game's fixed 6-crew format
means at most 5 OTHER live crew can ever witness a kill, 6 is an effective "always
strike" ceiling — so a cautious imposter that never finds a clean opening still
escalates rather than stalling forever (design §10 "act with urgency").
"""

from __future__ import annotations

import math
import os

from crewrift.crewborg.nav import plan_route
from crewrift.crewborg.strategy.trajectory import AGENT_SPEED_PX
from crewrift.crewborg.types import Belief, PlayerRecord

# Ticks of being able-to-kill-without-killing at which witness tolerance reaches its
# maximum (~10s at 24 Hz).
URGENCY_FULL_TICKS = 240

# Witnesses tolerated at zero urgency: a kill still proceeds with up to this many
# OTHER live non-teammate crewmates currently visible.
ALLOWED_WITNESSES_MIN = 1

# Witnesses tolerated at full urgency. This game's fixed 6-crew format means at most
# 5 other live crew can ever witness a kill, so 6 is an "always strike" ceiling --
# same guarantee as the old hard cutover, reached by a ramp instead of a cliff.
ALLOWED_WITNESSES_MAX = 6

# A non-teammate seen within this many ticks is still "trackable" — Search can
# follow it to its last-known position even while it is briefly out of view.
TRACK_WINDOW_TICKS = 120

# If a fellow imposter was seen closer than us to a victim within this radius, treat
# that victim as "claimed" and prefer another target when one exists.
TEAMMATE_CLAIM_RADIUS = 80

# The kill cooldown fallback before HUD measurement: Crewrift Prime (0.3.9, our
# target league) uses 500 ticks; regular Crewrift (0.1.58) uses 800. We still learn
# the true value from the HUD once a cooldown runs to ready.
DEFAULT_KILL_COOLDOWN_TICKS = 500

# Enter Search this many ticks before the kill comes off cooldown. Search finds
# and follows a victim; Hunt only activates once the kill is ready and a victim is
# visible. Raised from 100 → 250 (half the 500-tick cooldown): we want to be already
# shadowing an isolated victim when the kill comes ready, so the cooldown window
# converts to a kill ASAP — a partner's kill→report can reset our cooldown, so banking
# our own kill quickly is the only lever on our side (see tentative lessons). 250
# deliberately stops short of "search the whole cooldown": the BE_DUMB ceiling arm
# (search ~97% of ticks) tripled our ejection rate (14%→40%) for only +10% kills, so we
# keep a Pretend window for cover.
SEARCH_LEAD_TICKS = 250

# Backwards-compatible name for docs/tests that still refer to the old Hunt lead
# term. New code should use SEARCH_LEAD_TICKS.
HUNT_LEAD_TICKS = SEARCH_LEAD_TICKS


def urgency_full_ticks() -> int:
    """Ticks of kill-ready-without-killing at which witness tolerance reaches its
    maximum, env-overridable via ``CREWBORG_URGENCY_FULL_TICKS`` so it can be swept
    without a rebuild. Clamped to >= 1 (it is a divisor); invalid values fall back to
    the default ``URGENCY_FULL_TICKS``."""

    raw = os.environ.get("CREWBORG_URGENCY_FULL_TICKS")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return URGENCY_FULL_TICKS


def allowed_witnesses_min() -> int:
    """Witnesses tolerated at zero urgency, env-overridable via
    ``CREWBORG_ALLOWED_WITNESSES_MIN`` so it can be swept without a rebuild."""

    return _env_ticks("CREWBORG_ALLOWED_WITNESSES_MIN", ALLOWED_WITNESSES_MIN)


def allowed_witnesses_max() -> int:
    """Witnesses tolerated at full urgency, env-overridable via
    ``CREWBORG_ALLOWED_WITNESSES_MAX`` so it can be swept without a rebuild."""

    return _env_ticks("CREWBORG_ALLOWED_WITNESSES_MAX", ALLOWED_WITNESSES_MAX)


def kill_urgency_ticks(belief: Belief) -> int:
    """How long we have been able to kill without doing so (0 if not kill-ready)."""

    if not belief.self_kill_ready or belief.kill_ready_since_tick is None:
        return 0
    return max(0, belief.last_tick - belief.kill_ready_since_tick)


def ticks_until_kill_ready(belief: Belief) -> int:
    """Estimated ticks until the kill becomes available (0 if ready now).

    The HUD is binary (ready / cooldown, no countdown), so this reconstructs the
    countdown from the tracked cooldown start (`kill_cooldown_start_tick`) plus the
    learned duration (`kill_cooldown_estimate`, falling back to the game default
    before anything has been measured). With no cooldown start observed yet it
        assumes a full cooldown remains, so callers won't enter Search on no
        information.
    """

    if belief.self_kill_ready:
        return 0
    if belief.kill_cooldown_start_tick is None:
        return DEFAULT_KILL_COOLDOWN_TICKS
    duration = belief.kill_cooldown_estimate or DEFAULT_KILL_COOLDOWN_TICKS
    return max(0, belief.kill_cooldown_start_tick + duration - belief.last_tick)


def has_trackable_victim(belief: Belief) -> bool:
    """Whether any non-teammate has been seen recently enough for Search to follow.

    Kept as a useful readout; Hunt itself requires current visibility.
    """

    return any(
        entry.color not in belief.teammate_colors
        and entry.life_status != "dead"
        and belief.last_tick - entry.last_seen_tick <= TRACK_WINDOW_TICKS
        for entry in belief.roster.values()
    )


def visible_victims(belief: Belief) -> list[PlayerRecord]:
    """Live non-teammates visible on the current tick."""

    return [
        entry
        for entry in belief.roster.values()
        if entry.color not in belief.teammate_colors
        and entry.life_status != "dead"
        and entry.last_seen_tick == belief.last_tick
    ]


def has_visible_victim(belief: Belief) -> bool:
    """Whether a live non-teammate crewmate is visible right now."""

    return bool(visible_victims(belief))


def select_victim(belief: Belief) -> PlayerRecord | None:
    """The crewmate to commit to hunting: the most-isolated reachable visible
    crewmate (a straggler — easiest to finish off unwitnessed), tie-broken by
    nearest to us. ``None`` when no non-teammate is visible/reachable."""

    self_xy = _self_xy(belief)
    if self_xy is None:
        return None
    crew = visible_victims(belief)
    if not crew:
        return None
    candidates = crew
    if belief.nav is not None:
        candidates = [t for t in crew if plan_route(belief.nav, self_xy, (t.world_x, t.world_y))]
        if not candidates:
            return None
    unclaimed = [target for target in candidates if not _claimed_by_teammate(target, belief, self_xy)]
    if unclaimed:
        candidates = unclaimed
    # Prefer the most isolated (largest gap to its nearest other crewmate), then nearest.
    return max(candidates, key=lambda t: (_isolation(t, belief), -_dist2(self_xy, (t.world_x, t.world_y))))


def unwitnessed(belief: Belief, target: PlayerRecord) -> bool:
    """Whether killing ``target`` now would go unseen, at the current urgency level.

    Not a yes/no gate on any witness at all: the number of OTHER live non-teammate
    crewmates currently visible to us must be at or below the urgency-ramped
    tolerance (``witness_tolerance`` — 1 at zero urgency, ramping to 6, effectively
    "always strike," by full urgency). See the module docstring and
    ``docs/designs/vision-model.md`` for why current visibility is an exact witness
    count, not a distance/staleness proxy.
    """

    return _witness_count(belief, target) <= witness_tolerance(belief)


def witness_tolerance(belief: Belief) -> int:
    """The witness count tolerated right now: ramps linearly from
    ``allowed_witnesses_min()`` at zero urgency to ``allowed_witnesses_max()`` at
    full urgency (``kill_urgency_ticks >= urgency_full_ticks()``)."""

    frac = min(1.0, kill_urgency_ticks(belief) / urgency_full_ticks())
    lo, hi = allowed_witnesses_min(), allowed_witnesses_max()
    return int(lo + (hi - lo) * frac)


def _isolation(target: PlayerRecord, belief: Belief) -> float:
    """Distance² to the nearest *other* live non-teammate — higher means more isolated."""

    target_xy = (target.world_x, target.world_y)
    gaps = [
        _dist2(target_xy, (o.world_x, o.world_y))
        for o in belief.roster.values()
        if o.color != target.color and o.color not in belief.teammate_colors and o.life_status != "dead"
    ]
    return min(gaps) if gaps else float("inf")


def _witness_count(belief: Belief, target: PlayerRecord) -> int:
    """How many OTHER live non-teammate crewmates are visible to us THIS tick.

    Vision is symmetric (see the module docstring), so "visible to us now" already
    means "could see the kill" -- no separate distance or recency check is needed.
    """

    return sum(
        1
        for other in belief.roster.values()
        if other.color != target.color
        and other.color not in belief.teammate_colors
        and other.life_status != "dead"
        and other.last_seen_tick == belief.last_tick
    )


def _claimed_by_teammate(target: PlayerRecord, belief: Belief, self_xy: tuple[int, int]) -> bool:
    target_xy = (target.world_x, target.world_y)
    self_dist = _dist2(self_xy, target_xy)
    for teammate in belief.roster.values():
        if teammate.color not in belief.teammate_colors:
            continue
        if teammate.life_status == "dead":
            continue
        if belief.last_tick - teammate.last_seen_tick > TRACK_WINDOW_TICKS:
            continue
        teammate_dist = _dist2((teammate.world_x, teammate.world_y), target_xy)
        if teammate_dist < self_dist and teammate_dist <= TEAMMATE_CLAIM_RADIUS**2:
            return True
    return False


# --- Recon (pre-position on a crewmate just before the kill comes off cooldown) ----
#
# Diagnosis (2026-06-25 warehouse head-to-head vs crewborg-aaln): at the moment our
# cooldown comes off we have a crewmate in view only ~53% of the time (Aaron: 83%) —
# we drift away from crew we saw earlier in the cooldown cycle. Recon closes that gap:
# beeline to a target timed so we ARRIVE the instant the cooldown clears, not before
# (holding position — WATCH's job — until then avoids the over-extension that gets
# an early-committing imposter caught).
#
# Reworked 2026-07-06 (James): the entry trigger used to be a fixed
# ``RECON_WINDOW_TICKS`` (100) regardless of how far the target actually was, and the
# target was simply the most-recently-seen crewmate. Now both are computed: the
# target is the most ISOLATED fresh sighting (farthest from every other candidate —
# least likely another crewmate or teammate interferes with the approach or the
# kill), and the trigger fires exactly when the remaining cooldown drops to the
# real travel time to that target (via the nav route when available, straight-line
# distance / speed otherwise) — so we start moving only once "close enough" that we
# hit them right as the cooldown clears, not any earlier.

# A recon target whose freshest sighting is older than this is STALE — its last-seen
# point carries no victim information anymore, so beelining there is worse than running
# Search's room-checking FSM (the measured failure: parking on minutes-old points — see
# the 2026-07-02 movement diagnosis in tools/imposter_movement/README.md). Default 360
# (~15 s at 24 Hz) = 3× the 120-tick TRACK/FOLLOW windows (beyond which the codebase
# already treats a sighting as un-followable) ≈ 2-3 room transits: within it the target
# is plausibly still near its last-seen room; past it the point is just history.
RECON_STALENESS_TICKS = 360

# Radius (px) at which a recon point counts as reached. Shared by ReconMode's own
# arrival handling and the selector's spent-target check (rule_based).
RECON_REACHED_RADIUS_SQ = 24**2


def recon_staleness_ticks() -> int:
    """The recon target staleness bound (ticks since the freshest sighting),
    env-overridable via ``CREWBORG_RECON_STALENESS_TICKS``."""

    return _env_ticks("CREWBORG_RECON_STALENESS_TICKS", RECON_STALENESS_TICKS)


def _env_ticks(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return default


def travel_ticks(belief: Belief, self_xy: tuple[int, int], target_xy: tuple[int, int]) -> float:
    """Estimated ticks to walk from ``self_xy`` to ``target_xy`` at ``AGENT_SPEED_PX``,
    via the real nav route when one exists (respects walls/corridors — a straight line
    through a wall would understate the real travel time), else straight-line distance."""

    if belief.nav is not None:
        route = plan_route(belief.nav, self_xy, target_xy)
        if route:
            points = [self_xy, *route]
            distance = sum(math.dist(points[i], points[i + 1]) for i in range(len(points) - 1))
            return distance / AGENT_SPEED_PX
    return math.dist(self_xy, target_xy) / AGENT_SPEED_PX


def most_isolated_recon_candidate(belief: Belief) -> PlayerRecord | None:
    """Among fresh (``recon_staleness_ticks()``) live non-teammate crew, the one
    farthest from every OTHER such candidate — the target least likely to have
    another crewmate (or us) complicate the approach or the kill. ``None`` when no
    sighting is fresh enough. Ties broken toward the more recently seen (more
    reliable position), then toward the existing roster order."""

    fresh = [
        rec for rec in belief.roster.values()
        if rec.color not in belief.teammate_colors
        and rec.life_status != "dead"
        and belief.last_tick - rec.last_seen_tick <= recon_staleness_ticks()
    ]
    if not fresh:
        return None
    if len(fresh) == 1:
        return fresh[0]

    def isolation(rec: PlayerRecord) -> float:
        xy = (rec.world_x, rec.world_y)
        gaps = [
            _dist2(xy, (other.world_x, other.world_y))
            for other in fresh
            if other.color != rec.color
        ]
        return min(gaps) if gaps else float("inf")

    return max(fresh, key=lambda rec: (isolation(rec), rec.last_seen_tick))


def recon_target(belief: Belief) -> PlayerRecord | None:
    """The crewmate to close on during recon: ``most_isolated_recon_candidate``,
    which already bounds itself to fresh (``recon_staleness_ticks()``) sightings —
    ``None`` when nothing is fresh enough (→ the selector falls through to Search)."""

    return most_isolated_recon_candidate(belief)


def most_recent_victim(belief: Belief) -> PlayerRecord | None:
    """The most-recently-seen live non-teammate crewmate (its ``world_x/y`` is the
    live position when visible, else last-known). ``None`` when no crewmate has been
    seen at all. Used by Evade's cold-start fallback (no occupancy data yet) — NOT
    by Recon, which targets the most *isolated* fresh sighting instead (see
    ``most_isolated_recon_candidate``)."""

    crew = [
        entry
        for entry in belief.roster.values()
        if entry.color not in belief.teammate_colors and entry.life_status != "dead"
    ]
    if not crew:
        return None
    return max(crew, key=lambda entry: entry.last_seen_tick)


def _self_xy(belief: Belief) -> tuple[int, int] | None:
    if belief.self_world_x is None or belief.self_world_y is None:
        return None
    return belief.self_world_x, belief.self_world_y


def _dist2(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
