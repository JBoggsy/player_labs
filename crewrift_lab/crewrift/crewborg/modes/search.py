"""Search mode — the imposter's always-on seeking stance (design §7.2; reworked 2026-07-01).

Its job is to keep us NEAR crew so a kill window opens — **always moving with intent, never
parking.** A 5-state FSM (see the imposter-FSM doc §8):

  PICK_ROOM    Choose a reachable room to sweep, biased toward where crew are. **Always
               picks a room — never idles** (fallback ladder below). -> GO_TO_ROOM
  GO_TO_ROOM   Navigate to the room centre. Seeing ANY live non-teammate crewmate — room
               OR hallway — -> FOLLOW it (so we pick up hallway encounters en route).
               Arriving in the room -> SEARCH_ROOM.
  SEARCH_ROOM  Sweep the room's interior so crew hidden from the door are found. Crew in
               the room -> WATCH; a crewmate seen elsewhere -> FOLLOW; swept empty ->
               PICK_ROOM.
  WATCH        Only entered with crew confirmed in the room. CAMOUFLAGE first (2026-07-02,
               docs/designs/watch-camouflage.md): when the kill is >CREWBORG_CAMO_MIN_CD_TICKS
               (100) from ready, fake a task — idle one task duration (+buffer) at the in-room
               task spot whose BAKED vision covers the most visible crew — instead of hovering
               suspiciously; escapes on kill-soon / crew-lost / travel-cap / preemption. Then:
               MULTIPLE crew visible -> hold the vantage seeing the most (recomputed as they
               move). A SINGLE crew -> close on it: a task site beside it if one is near, else
               approach to ``kill_range + 15px`` (just outside kill range, poised to strike).
               Self-loops (holds) only while >=1 crew is in view; the LAST crewmate leaving
               view -> FOLLOW; no crew in view AND none seen to leave -> PICK_ROOM (rare
               fallback).
  FOLLOW       Persistent chase of a leaver using path prediction — keeps going down the
               predicted hallway while the target is occluded, up to FOLLOW_LOST_TICKS (240
               for a hard-commander target). While the target is visible we chase its live
               position; the moment we are in the SAME room as it (we've run it down) we hand
               off to SEARCH_ROOM (-> WATCH). When the follow instead ends occluded (lost past
               the window) we re-scan the room we ended up in (-> SEARCH_ROOM) or -> PICK_ROOM.

Kill hand-off is automatic and lives in the selector (``rule_based``): the instant the kill
is ready and a victim is visible, the strategy gate switches to Hunt. So Search never idles a
ready kill away — a lone target is *approached* to within a step, a crowd is *watched* only
until one peels off. The only ``idle`` this mode can emit is the deliberate multi-crew
vantage hold (and the startup no-op before the camera/map exist).

Two ready-state safeguards (2026-07-02 movement diagnosis):

- PICK_ROOM blends an **empirical density prior** (``strategy/room_prior.py``: each room's
  measured live-crew share by 600-tick game band) with live occupancy — live evidence
  dominates when present; the prior steers when blind. See the weight comments below.
- A **parked guard** (``imposter_common.ParkedGuard``): any run of kill-ready Playing ticks
  spent on a zero-length route (or idle) forces a fresh room pick and emits a
  ``parked_guard`` trace event, so no state can ever park a ready kill again.

Never follows the teammate imposter. The path predictor is fed only what we actually see.
"""

from __future__ import annotations

import math
import os
import random

from crewrift.crewborg.agent_tracking import best_seek_point, room_occupancy
from crewrift.crewborg.modes import imposter_common as ic
from crewrift.crewborg.map.types import Room
from crewrift.crewborg.nav import _segment_clear
from crewrift.crewborg.strategy.commander.bias import commander_of
from crewrift.crewborg.strategy.opportunity import ticks_until_kill_ready
from crewrift.crewborg.strategy.path_prediction import PathPredictor
from crewrift.crewborg.strategy.room_prior import room_share_prior
from crewrift.crewborg.types import ActionState, Belief, Intent, PlayerRecord
from crewrift.crewborg.visionbake import TaskVisionBake, load_visionbake
from players.player_sdk import EmptyModeParams, Mode, ModeDirective, ModeParams

ARRIVE_RADIUS_SQ = 24**2
# Drop a follow once the target has been unseen this long with no live prediction.
FOLLOW_LOST_TICKS = 120
# Hard commander target-player follows get a little more persistence before Search gives up.
COMMANDER_FOLLOW_LOST_TICKS = 240
# A crewmate counts as "still watchable" from a vantage if seen within this window.
WATCH_RECENT_TICKS = 36
# Line-of-sight range (px) for vantage scoring — generous; LOS through walls is the real gate.
VANTAGE_RANGE = 360
VANTAGE_RANGE_SQ = VANTAGE_RANGE**2
# Coarse grid step (px) for candidate vantage points within a room.
VANTAGE_STEP = 40
# Recompute the vantage at most this often (crew move; LOS scans cost a little).
VANTAGE_REFRESH_TICKS = 18
# Only move to a new vantage if it sees at least this many MORE crew (hysteresis).
VANTAGE_SWITCH_MARGIN = 1
# Single-crew close-in target: kill_range (20px) + 15px margin — just outside kill range,
# poised to dart in the instant the cooldown lifts (the selector flips us to Hunt then).
SINGLE_APPROACH_PX = 35
# A task station this close (px) to a lone target is a natural place to stand and blend.
TASK_SITE_NEAR_SQ = 56**2


def _wenv(name: str, default: float) -> float:
    """A tunable PICK_ROOM weight/constant, overridable via env for offline sweeps."""
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# --- PICK_ROOM scoring weights (all env-tunable so they can be swept/learned) --------------
# Occupancy (go where crew are expected) is the strongest positive signal. Unvisitedness is
# also strong and GROWS with time-since-visit so peripheral rooms get swept occasionally.
# Recency is a strong penalty that DECAYS quickly (anti-ping-pong between two rooms).
# The empirical density PRIOR (strategy/room_prior.py: per-room live-crew share by game
# band, from 247 real episodes) is deliberately HALF the live-occupancy weight: both terms
# are max-normalized to 0..1, so when the tracker has live evidence it dominates 2:1, and
# when we're blind (occupancy ≈ 0 everywhere, early game / long no-contact stretches) the
# prior is the crew-seeking signal that breaks ties between otherwise-equal rooms.
W_OCCUPANCY = _wenv("CREWBORG_PICKROOM_W_OCCUPANCY", 3.0)   # where crew are expected — strongest
W_UNVISITED = _wenv("CREWBORG_PICKROOM_W_UNVISITED", 2.5)   # long-unvisited rooms — grows over time
W_RECENCY = _wenv("CREWBORG_PICKROOM_W_RECENCY", 3.0)       # just-visited penalty — decays fast
W_DISTANCE = _wenv("CREWBORG_PICKROOM_W_DISTANCE", 1.0)     # discount far rooms (time-bound windows)
W_TEAMMATE = _wenv("CREWBORG_PICKROOM_W_TEAMMATE", 1.5)     # don't converge with our co-imposter
W_TASKBONUS = _wenv("CREWBORG_PICKROOM_W_TASKBONUS", 0.4)   # small blend bonus for task rooms
W_COMMANDER = _wenv("CREWBORG_PICKROOM_W_COMMANDER", 1.0)   # soft commander hunt-room nudge
W_PRIOR = _wenv("CREWBORG_PICKROOM_W_PRIOR", 1.5)           # empirical density prior — see above
# Recency penalty is gone after ~this many ticks; unvisitedness maxes out after ~this many.
RECENCY_DECAY_TICKS = _wenv("CREWBORG_PICKROOM_RECENCY_DECAY", 150.0)
UNVISITED_FULL_TICKS = _wenv("CREWBORG_PICKROOM_UNVISITED_FULL", 800.0)


# --- WATCH camouflage (docs/designs/watch-camouflage.md) -----------------------------------
# When the kill is far from ready, hovering near crew is pure suspicion cost — there is
# nothing to convert yet. Blend in instead: fake a task (idle one crewmate task duration
# + buffer) at the in-room task spot whose BAKED vision covers the most visible crew
# (visionbake.py; nearest task spot when the bake is unusable). The default minimum-
# cooldown gate equals RECON_WINDOW_TICKS, so camo never eats the near-ready window that
# Recon/Hunt own. Every camo tick has an escape: kill-soon, crew-lost, travel cap, hold
# deadline, mode preemption (on_exit), and the parked guard as last-resort insurance.

# Bound the walk to the camo spot (an in-room hop; ~360px at ~3px/tick with slack).
CAMO_TRAVEL_CAP_TICKS = 120


def _ienv(name: str, default: int, minimum: int = 0) -> int:
    """An int env knob with a safe fallback (bad values -> default)."""

    raw = os.environ.get(name)
    if raw:
        try:
            return max(minimum, int(raw))
        except ValueError:
            pass
    return default


def camo_enabled() -> bool:
    """Kill switch: CREWBORG_CAMO=0 disables the WATCH camouflage entirely."""

    return os.environ.get("CREWBORG_CAMO", "1").strip().lower() not in {"0", "false", "off", "no"}


def camo_min_cd_ticks() -> int:
    """Camo only when MORE than this many ticks remain until the kill is ready;
    doubles as the kill-soon escape threshold once camo is running."""

    return _ienv("CREWBORG_CAMO_MIN_CD_TICKS", 100)


def camo_buffer_ticks() -> int:
    """Small buffer added to the one-task fake hold (James: 'plus a small buffer')."""

    return _ienv("CREWBORG_CAMO_BUFFER_TICKS", 12)


def camo_crew_lost_ticks() -> int:
    """All crew unseen for this long during camo -> abandon it (the room emptied)."""

    return _ienv("CREWBORG_CAMO_CREW_LOST_TICKS", WATCH_RECENT_TICKS, minimum=1)


# The vendored task-vision bake, loaded once per process. The sentinel keeps a genuine
# "no usable bake" (None) from being re-attempted every tick.
_VISION_UNSET = object()
_vision_cache: object = _VISION_UNSET


def _camo_vision(belief: Belief) -> TaskVisionBake | None:
    """The task-vision bake validated against this game's map, or ``None`` (fallback)."""

    global _vision_cache
    if _vision_cache is _VISION_UNSET:
        if belief.nav is None or belief.map is None:
            return None  # don't memoize before the nav/map exist
        _vision_cache = load_visionbake(belief.nav.walkability, len(belief.map.tasks))
    return _vision_cache if isinstance(_vision_cache, TaskVisionBake) else None


class SearchMode(Mode[Belief, ActionState, Intent]):
    name = "search"
    params_type = EmptyModeParams

    def __init__(self, params: ModeParams | None = None) -> None:
        super().__init__(params)
        self._state = "pick_room"
        self._target_room: str | None = None
        self._prev_room: str | None = None          # avoid immediately re-picking
        self._goto_point: ic.Point | None = None
        self._room_crew: set[str] = set()           # crew colors seen inside the watched room
        self._scan_points: list[ic.Point] = []      # SEARCH_ROOM sweep waypoints
        self._scan_idx = 0
        self._vantage: ic.Point | None = None       # current watch position (max crew in sight)
        self._vantage_tick: int | None = None       # when the vantage was last recomputed
        self._follow_color: str | None = None
        self._predictor: PathPredictor | None = None
        self._last_seen_tick: int | None = None
        self._last_visit_tick: dict[str, int] = {}   # room name -> last tick we were inside it
        self._rng = random.Random(0xC0FFEE)
        self._parked_guard = ic.ParkedGuard()
        # WATCH camouflage state (docs/designs/watch-camouflage.md).
        self._camo_spot: ic.Point | None = None      # non-None ⇔ a camo is active
        self._camo_task_index: int | None = None
        self._camo_enter_tick: int | None = None
        self._camo_idle_until: int | None = None     # set on arrival at the spot
        self._camo_done = False                      # one fake task per room visit
        self._camo_intent_tick: int | None = None    # tick whose outgoing intent was a camo idle

    # --- entry ----------------------------------------------------------------
    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        self_xy = ic.self_xy(belief)
        if self_xy is None or belief.map is None:
            # The only unavoidable idle: no camera / map yet (a startup no-op).
            return Intent(kind="idle", reason="no self position / map")

        # Remember which room we're standing in — feeds PICK_ROOM's recency/unvisited scoring.
        here = ic.room_containing(belief, self_xy)
        if here is not None:
            self._last_visit_tick[here.name] = belief.last_tick

        intent = self._dispatch(belief, self_xy)
        # PARKED GUARD: a kill-ready tick must never stand on a zero-length route.
        # Whatever state produced it, force a fresh room pick (the current room is
        # excluded by PICK_ROOM, so the new target is always somewhere else). The one
        # exemption is a camo idle — INTENTIONAL idling with its own escapes. It should
        # be unreachable while kill-ready (camo's kill-soon escape ends it first); if
        # that invariant ever breaks, trace the suppressed park loudly.
        intentional = self._camo_intent_tick == belief.last_tick
        if intentional and ic.would_park(belief, self_xy, intent):
            self.emit.event(
                "camo_guard_exempt",
                {"mode": self.name, "state": self._state, "intent": intent.kind, "reason": intent.reason},
            )
        if self._parked_guard.fires(belief, self_xy, intent, intentional_idle=intentional):
            self.emit.event(
                "parked_guard",
                {"mode": self.name, "state": self._state, "intent": intent.kind, "reason": intent.reason},
            )
            if self._camo_active():
                self._camo_exit(belief, "parked_guard")
            self._prev_room = self._target_room
            self._follow_color = None
            self._predictor = None
            self._last_seen_tick = None
            self._state = "pick_room"
            intent = self._pick_room(belief, self_xy)
        return intent

    def on_exit(self, belief: Belief, action_state: ActionState, next_directive: ModeDirective) -> None:
        # Mode preemption (meeting → attend_meeting; kill window → Recon/Hunt/Evade)
        # replaces this instance outright — close an active camo visibly so every
        # camo_idle enter pairs with an exit (the meeting-start escape, among others).
        del action_state, next_directive
        if self._camo_active():
            self._camo_exit(belief, "preempted")

    def _dispatch(self, belief: Belief, self_xy: ic.Point) -> Intent:
        if self._state == "go_to_room":
            return self._go_to_room(belief, self_xy)
        if self._state == "search_room":
            return self._search_room(belief, self_xy)
        if self._state == "watch":
            return self._watch(belief, self_xy)
        if self._state == "follow":
            return self._follow(belief, self_xy)
        return self._pick_room(belief, self_xy)

    # --- PICK_ROOM ------------------------------------------------------------
    def _pick_room(self, belief: Belief, self_xy: ic.Point) -> Intent:
        """Score every reachable room and commit to the best — NEVER idle. The score blends
        (tunable, env-overridable weights): expected crew occupancy (strongest), unvisitedness
        (grows with time-since-visit -> peripheral coverage), a fast-decaying recency penalty
        (anti ping-pong), travel cost, teammate-pressure subtraction, a task-room blend bonus,
        and a soft commander hunt-room nudge. Hard commander directives stay hard constraints."""

        rooms = list(belief.map.rooms)
        if not rooms:
            # Degenerate (no rooms) — head to the hottest occupancy cell so we still MOVE.
            seek = best_seek_point(belief)
            point = ic.reachable_point(belief, seek) if seek is not None else self_xy
            self._target_room = None
            self._goto_point = point
            self._state = "go_to_room"
            return Intent(kind="navigate_to", point=point, reason="search: no rooms — seek crew")

        cmd = commander_of(belief)
        # A HARD commander hunt-room is an override, not a nudge.
        if cmd is not None and cmd.strength == "hard" and cmd.hunt_room is not None:
            forced = self._room(belief, cmd.hunt_room)
            if forced is not None:
                return self._commit_room(belief, self_xy, forced)

        current = ic.room_containing(belief, self_xy)
        current_name = current.name if current is not None else None
        start = ic.starting_room(belief)
        start_name = start.name if start is not None else None
        avoid = cmd.avoid_room if cmd is not None else None
        # Prefer to exclude the room we're standing in, the spawn room, and a commander
        # avoid-room; peel those back only if excluding them would leave nothing to pick.
        candidates: list[Room] = []
        for exclude in ({current_name, start_name, avoid}, {current_name, start_name}, {current_name}, set()):
            candidates = [room for room in rooms if room.name not in exclude]
            if candidates:
                break

        occ = room_occupancy(belief)
        max_density = max((crew for crew, _ in occ.values()), default=0.0) or 1.0
        diag = math.hypot(belief.map.width, belief.map.height) or 1.0
        best = max(candidates, key=lambda room: (
            self._room_score(belief, room, self_xy, occ, max_density, diag, cmd),
            -ic.dist2(self_xy, (room.center.x, room.center.y)),
            room.name,
        ))
        return self._commit_room(belief, self_xy, best)

    def _room_score(self, belief, room, self_xy, occ, max_density, diag, cmd) -> float:
        now = belief.last_tick
        crew_density, teammate_density = occ.get(room.name, (0.0, 0.0))
        occupancy = crew_density / max_density                    # 0..1 — where crew are expected
        teammate = teammate_density / max_density                 # 0..1 — subtract (don't converge)
        last = self._last_visit_tick.get(room.name)
        if last is None:
            unvisited, recency = 1.0, 0.0                          # never seen -> maximally worth a look
        else:
            age = now - last
            unvisited = min(1.0, age / UNVISITED_FULL_TICKS)      # grows with time since we visited
            recency = max(0.0, 1.0 - age / RECENCY_DECAY_TICKS)   # strong right after, decays fast
        distance = math.hypot(room.center.x - self_xy[0], room.center.y - self_xy[1]) / diag
        score = (
            W_OCCUPANCY * occupancy
            + W_PRIOR * room_share_prior(room.name, now)
            + W_UNVISITED * unvisited
            - W_RECENCY * recency
            - W_DISTANCE * distance
            - W_TEAMMATE * teammate
            + (W_TASKBONUS if self._room_task_indices(belief, room) else 0.0)
        )
        if cmd is not None and cmd.hunt_room == room.name:
            score += W_COMMANDER                                   # soft hunt-room nudge
        return score

    def _commit_room(self, belief: Belief, self_xy: ic.Point, room: Room) -> Intent:
        self._target_room = room.name
        # Head to the room CENTRE (go fully inside to check it), not a task spot by the door.
        self._goto_point = ic.reachable_point(belief, (room.center.x, room.center.y))
        self._room_crew = set()
        self._vantage = None
        self._vantage_tick = None
        self._camo_reset(belief)
        self._state = "go_to_room"
        return self._go_to_room(belief, self_xy)

    # --- GO_TO_ROOM -----------------------------------------------------------
    def _go_to_room(self, belief: Belief, self_xy: ic.Point) -> Intent:
        # Seeing ANY live non-teammate — room or hallway — is worth chasing right now.
        leaver = self._nearest_visible_crew(belief, self_xy)
        if leaver is not None:
            return self._begin_follow(belief, leaver)

        room = self._room(belief, self._target_room)
        if room is None:
            # Seek-a-point fallback (no room target — the degenerate PICK_ROOM branch).
            if self._goto_point is not None and ic.dist2(self_xy, self._goto_point) > ARRIVE_RADIUS_SQ:
                return Intent(kind="navigate_to", point=self._goto_point, reason="search: heading toward crew")
            self._state = "pick_room"
            return self._pick_room(belief, self_xy)
        if self._goto_point is None:
            self._state = "pick_room"
            return self._pick_room(belief, self_xy)
        if ic.dist2(self_xy, self._goto_point) <= ARRIVE_RADIUS_SQ or ic.in_rect(self_xy, room):
            return self._enter_search_room(belief, self_xy, room.name)
        return Intent(kind="navigate_to", point=self._goto_point, reason="search: heading to a room to scan")

    # --- SEARCH_ROOM ----------------------------------------------------------
    def _enter_search_room(self, belief: Belief, self_xy: ic.Point, room_name: str) -> Intent:
        self._target_room = room_name
        room = self._room(belief, room_name)
        self._scan_points = self._room_scan_points(belief, room, self_xy) if room is not None else []
        self._scan_idx = 0
        self._room_crew = set()
        self._vantage = None
        self._vantage_tick = None
        self._camo_reset(belief)
        self._state = "search_room"
        return self._search_room(belief, self_xy)

    def _search_room(self, belief: Belief, self_xy: ic.Point) -> Intent:
        room = self._room(belief, self._target_room)
        if room is None:
            self._state = "pick_room"
            return self._pick_room(belief, self_xy)

        crew_in = self._crew_in_room(belief, room)
        if crew_in:
            self._room_crew = {c.color for c in crew_in}
            self._state = "watch"
            return self._watch(belief, self_xy)

        # A crewmate visible elsewhere (hallway / adjacent room) — go follow it.
        leaver = self._nearest_visible_crew(belief, self_xy)
        if leaver is not None:
            return self._begin_follow(belief, leaver)

        # Keep sweeping the room's interior scan points so hidden crew are revealed.
        while self._scan_idx < len(self._scan_points):
            point = self._scan_points[self._scan_idx]
            if ic.dist2(self_xy, point) <= ARRIVE_RADIUS_SQ:
                self._scan_idx += 1
                continue
            return Intent(kind="navigate_to", point=point, reason="search: scanning the room for crew")

        # Swept the whole room, nobody here.
        self._prev_room = self._target_room
        self._state = "pick_room"
        return self._pick_room(belief, self_xy)

    def _room_scan_points(self, belief: Belief, room: Room, self_xy: ic.Point) -> list[ic.Point]:
        """A short ordered set of reachable interior points that between them break the
        room's line-of-sight occlusion, so crew tucked out of the door's view are found."""

        raw = [
            (room.x + room.w * 0.25, room.y + room.h * 0.25),
            (room.x + room.w * 0.75, room.y + room.h * 0.25),
            (room.x + room.w * 0.75, room.y + room.h * 0.75),
            (room.x + room.w * 0.25, room.y + room.h * 0.75),
            (room.center.x, room.center.y),
        ]
        points: list[ic.Point] = []
        for gx, gy in raw:
            point = ic.reachable_point(belief, (int(gx), int(gy)))
            if ic.in_rect(point, room) and point not in points:
                points.append(point)
        points.sort(key=lambda p: ic.dist2(self_xy, p))
        return points

    # --- WATCH ----------------------------------------------------------------
    def _watch(self, belief: Belief, self_xy: ic.Point) -> Intent:
        room = self._room(belief, self._target_room)
        if room is None:
            self._state = "pick_room"
            return self._pick_room(belief, self_xy)

        visible_here = self._crew_in_room(belief, room)
        if visible_here:
            self._room_crew |= {c.color for c in visible_here}

        # CAMOUFLAGE: with crew here and the kill far from ready, don't hover — fake a
        # task at the spot with the best view over them (docs/designs/watch-camouflage.md).
        # While camo runs it owns the tick (leaver chases resume after it ends; the
        # crew-lost escape covers the room emptying under us).
        if self._camo_active():
            camo = self._camo_tick(belief, self_xy)
            if camo is not None:
                return camo
            # camo just ended — resume normal WATCH behaviour this same tick
        elif (
            visible_here
            and not self._camo_done
            and camo_enabled()
            and ticks_until_kill_ready(belief) > camo_min_cd_ticks()
        ):
            camo = self._camo_start(belief, room, self_xy, visible_here)
            if camo is not None:
                return camo
            # no task spot in this room — normal WATCH

        if visible_here:
            if len(visible_here) >= 2:
                # MULTIPLE crew: hold the in-room vantage with line-of-sight to the most of
                # them (recomputed as they move). This is the one deliberate hold in Search.
                self._refresh_vantage(belief, room, self_xy)
                if self._vantage is not None and ic.dist2(self_xy, self._vantage) > ARRIVE_RADIUS_SQ:
                    return Intent(kind="navigate_to", point=self._vantage, reason="search: moving to a vantage over the crew")
                return Intent(kind="idle", reason="search: watching multiple crew from a vantage")
            # SINGLE crew: don't watch from afar — close on it so Hunt can strike at ready.
            target = visible_here[0]
            point = self._single_target_point(belief, target, self_xy)
            return Intent(kind="navigate_to", point=point, reason="search: closing on the lone crewmate")

        # No crew in view right now. Did the last one just leave? Then chase it.
        leaver = self._a_crewmate_left(belief, room)
        if leaver is not None:
            return self._begin_follow(belief, leaver)

        # No crew visible and none seen to leave — re-pick (rare: WATCH starts with crew).
        self._prev_room = self._target_room
        self._state = "pick_room"
        return self._pick_room(belief, self_xy)

    def _single_target_point(self, belief: Belief, target: PlayerRecord, self_xy: ic.Point) -> ic.Point:
        """Where to stand to shadow a lone crewmate: a nearby task site (natural blend),
        else a point ``SINGLE_APPROACH_PX`` from the target on our side (just out of range)."""

        target_xy = (target.world_x, target.world_y)
        site = self._nearest_task_site(belief, target_xy)
        if site is not None:
            return site
        dx = self_xy[0] - target_xy[0]
        dy = self_xy[1] - target_xy[1]
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return ic.reachable_point(belief, target_xy)
        px = target_xy[0] + dx / dist * SINGLE_APPROACH_PX
        py = target_xy[1] + dy / dist * SINGLE_APPROACH_PX
        return ic.reachable_point(belief, (int(px), int(py)))

    def _nearest_task_site(self, belief: Belief, xy: ic.Point) -> ic.Point | None:
        tasks = belief.map.tasks if belief.map is not None else ()
        best: ic.Point | None = None
        best_d = TASK_SITE_NEAR_SQ + 1
        for task in tasks:
            task_xy = (task.center.x, task.center.y)
            d = ic.dist2(xy, task_xy)
            if d < best_d:
                best_d, best = d, task_xy
        return best if best is not None and best_d <= TASK_SITE_NEAR_SQ else None

    # --- WATCH camouflage (docs/designs/watch-camouflage.md) --------------------
    def _camo_active(self) -> bool:
        return self._camo_spot is not None

    def _camo_start(self, belief: Belief, room: Room, self_xy: ic.Point,
                    visible_here: list[PlayerRecord]) -> Intent | None:
        """Begin a camo fake-task in ``room``, or ``None`` when it has no task spot.

        Spot = the in-room task station whose baked vision covers the most
        currently-visible crew (tie-break: larger total visible area, then
        nearest). With no usable bake: the nearest in-room task spot.
        """

        indices = self._room_task_indices(belief, room)
        if not indices:
            return None
        vision = _camo_vision(belief)
        if vision is None:
            index = min(indices, key=lambda i: ic.dist2(self_xy, ic.task_point(belief, i)))
        else:
            crew_xy = [(c.world_x, c.world_y) for c in visible_here]
            index = max(indices, key=lambda i: (
                sum(1 for xy in crew_xy if vision.visible_from(i, xy)),
                vision.visible_area(i),
                -ic.dist2(self_xy, ic.task_point(belief, i)),
            ))
        self._camo_task_index = index
        self._camo_spot = ic.task_point(belief, index)
        self._camo_enter_tick = belief.last_tick
        self._camo_idle_until = None
        self.emit.event(
            "camo_idle",
            {
                "phase": "enter",
                "spot": list(self._camo_spot),
                "task_index": index,
                "visible_crew": len(visible_here),
                "planned_hold_ticks": ic.FAKE_TASK_TICKS + camo_buffer_ticks(),
                "ticks_until_ready": ticks_until_kill_ready(belief),
                "bake_used": vision is not None,
            },
        )
        return self._camo_tick(belief, self_xy)

    def _camo_tick(self, belief: Belief, self_xy: ic.Point) -> Intent | None:
        """One tick of the active camo; ``None`` when it just ended (resume WATCH)."""

        # Escapes, in priority order (every idle needs one — lab standing principle).
        if ticks_until_kill_ready(belief) <= camo_min_cd_ticks():
            return self._camo_exit(belief, "kill_soon")
        if not self._camo_crew_recent(belief):
            return self._camo_exit(belief, "crew_lost")
        if self._camo_idle_until is not None and belief.last_tick >= self._camo_idle_until:
            return self._camo_exit(belief, "done")
        if self._camo_idle_until is None:
            if belief.last_tick - self._camo_enter_tick >= CAMO_TRAVEL_CAP_TICKS:
                return self._camo_exit(belief, "travel_timeout")
            if ic.dist2(self_xy, self._camo_spot) > ARRIVE_RADIUS_SQ:
                return Intent(kind="navigate_to", point=self._camo_spot,
                              reason="search: camo — heading to a task spot in view of the crew")
            # Arrived: the fake-task hold starts now.
            self._camo_idle_until = belief.last_tick + ic.FAKE_TASK_TICKS + camo_buffer_ticks()
        self._camo_intent_tick = belief.last_tick  # marks this idle as INTENTIONAL (guard exemption)
        return Intent(kind="idle", reason="search: camo — faking a task with eyes on the crew")

    def _camo_exit(self, belief: Belief, reason: str) -> None:
        """End the active camo (traced); returns ``None`` so callers can tail-return it."""

        self.emit.event(
            "camo_idle",
            {
                "phase": "exit",
                "reason": reason,
                "task_index": self._camo_task_index,
                "held_ticks": belief.last_tick - (self._camo_enter_tick or belief.last_tick),
                "arrived": self._camo_idle_until is not None,
            },
        )
        self._camo_spot = None
        self._camo_task_index = None
        self._camo_enter_tick = None
        self._camo_idle_until = None
        self._camo_done = True
        return None

    def _camo_reset(self, belief: Belief) -> None:
        """A fresh room visit re-arms camo (and closes out a stale active one)."""

        if self._camo_active():
            self._camo_exit(belief, "room_change")
        self._camo_done = False

    def _camo_crew_recent(self, belief: Belief) -> bool:
        """Whether ANY live non-teammate has been seen within the crew-lost window."""

        lost = camo_crew_lost_ticks()
        return any(
            rec.color not in belief.teammate_colors
            and rec.life_status != "dead"
            and belief.last_tick - rec.last_seen_tick <= lost
            for rec in belief.roster.values()
        )

    def _refresh_vantage(self, belief: Belief, room: Room, self_xy: ic.Point) -> None:
        """(Re)pick the point in ``room`` with line-of-sight to the most watchable crew,
        throttled, with hysteresis so we don't jitter between equal vantages."""

        if (
            self._vantage is not None
            and self._vantage_tick is not None
            and belief.last_tick - self._vantage_tick < VANTAGE_REFRESH_TICKS
        ):
            return
        crew_xy = self._watchable_crew_xy(belief)
        if not crew_xy:
            return
        best = self._best_vantage(belief, room, crew_xy, self_xy)
        if best is None:
            return
        best_point, best_score = best
        current_score = self._visible_count(belief, self._vantage, crew_xy) if self._vantage else -1
        if self._vantage is None or best_score >= current_score + VANTAGE_SWITCH_MARGIN:
            self._vantage = best_point
        self._vantage_tick = belief.last_tick

    def _best_vantage(self, belief: Belief, room: Room, crew_xy, self_xy):
        """Argmax over a coarse grid of reachable in-room points of how many crew each has
        line-of-sight to. Ties broken toward staying put (less movement)."""

        best_point = None
        best_score = -1
        best_move = 0
        x0, y0 = room.x, room.y
        for gx in range(x0 + VANTAGE_STEP // 2, x0 + room.w, VANTAGE_STEP):
            for gy in range(y0 + VANTAGE_STEP // 2, y0 + room.h, VANTAGE_STEP):
                point = ic.reachable_point(belief, (gx, gy))
                if not ic.in_rect(point, room):
                    continue
                score = self._visible_count(belief, point, crew_xy)
                move = ic.dist2(self_xy, point)
                if score > best_score or (score == best_score and move < best_move):
                    best_point, best_score, best_move = point, score, move
        return (best_point, best_score) if best_point is not None else None

    def _visible_count(self, belief: Belief, point: ic.Point | None, crew_xy) -> int:
        """How many of ``crew_xy`` have clear line-of-sight from ``point`` in range."""

        if point is None or belief.nav is None:
            return 0
        walk = belief.nav.walkability
        n = 0
        for cxy in crew_xy:
            if ic.dist2(point, cxy) <= VANTAGE_RANGE_SQ and _segment_clear(walk, point, cxy):
                n += 1
        return n

    def _watchable_crew_xy(self, belief: Belief) -> list[ic.Point]:
        """Recently-seen live non-teammate crew positions — who we want to keep in view."""

        out = []
        for rec in belief.roster.values():
            if rec.color in belief.teammate_colors or rec.life_status == "dead":
                continue
            if belief.last_tick - rec.last_seen_tick <= WATCH_RECENT_TICKS:
                out.append((rec.world_x, rec.world_y))
        return out

    # --- FOLLOW ---------------------------------------------------------------
    def _follow(self, belief: Belief, self_xy: ic.Point) -> Intent:
        if self._follow_color is None or self._predictor is None:
            self._state = "pick_room"
            return self._pick_room(belief, self_xy)
        target = belief.roster.get(self._follow_color)
        if target is None or target.life_status == "dead" or self._follow_color in belief.teammate_colors:
            return self._stop_follow(belief, self_xy)

        visible = target.last_seen_tick == belief.last_tick
        observed = (target.world_x, target.world_y) if visible else None
        self._predictor.observe(belief.last_tick, observed)
        if visible:
            self._last_seen_tick = belief.last_tick
            # Caught up ("settled"): we're in the SAME room as the visible target -> hand off
            # to SEARCH_ROOM. It re-scans the room (picks up anyone else) and routes to WATCH,
            # so a lone target is approached to ~35px rather than walked onto. On a real
            # (corridor'd) map this only fires once we've actually run the leaver down into a
            # room; while chasing through hallways we keep following its live position.
            our_room = ic.room_containing(belief, self_xy)
            if our_room is not None and ic.in_rect((target.world_x, target.world_y), our_room):
                return self._enter_search_room(belief, self_xy, our_room.name)
            return Intent(kind="navigate_to", point=(target.world_x, target.world_y),
                          reason="search: following a leaver (visible)")

        # Out of view: chase down the predicted hallway toward the top route's position.
        if self._last_seen_tick is not None and belief.last_tick - self._last_seen_tick > self._follow_lost_ticks(belief):
            return self._stop_follow(belief, self_xy)
        best = self._predictor.best()
        if best is None:
            return self._stop_follow(belief, self_xy)
        return Intent(kind="navigate_to", point=tuple(best.pred_pos),
                      reason="search: chasing predicted path (occluded)")

    def _begin_follow(self, belief: Belief, leaver: PlayerRecord) -> Intent:
        self._follow_color = leaver.color
        self._predictor = PathPredictor(nav=belief.nav, map=belief.map)
        self._last_seen_tick = belief.last_tick if leaver.last_seen_tick == belief.last_tick else None
        self._state = "follow"
        if leaver.last_seen_tick == belief.last_tick:
            self._predictor.observe(belief.last_tick, (leaver.world_x, leaver.world_y))
        return Intent(kind="navigate_to", point=(leaver.world_x, leaver.world_y),
                      reason="search: a crewmate is in view — follow")

    def _stop_follow(self, belief: Belief, self_xy: ic.Point) -> Intent:
        # Re-scan the room we ended up in (finds hidden crew); else pick a new room.
        self._follow_color = None
        self._predictor = None
        self._last_seen_tick = None
        room = ic.room_containing(belief, self_xy)
        if room is not None:
            return self._enter_search_room(belief, self_xy, room.name)
        self._state = "pick_room"
        return self._pick_room(belief, self_xy)

    def _follow_lost_ticks(self, belief: Belief) -> int:
        cmd = commander_of(belief)
        if (
            cmd is not None
            and cmd.strength == "hard"
            and self._follow_color is not None
            and self._follow_color == cmd.target_player
        ):
            return COMMANDER_FOLLOW_LOST_TICKS
        return FOLLOW_LOST_TICKS

    # --- helpers --------------------------------------------------------------
    def _nearest_visible_crew(self, belief: Belief, self_xy: ic.Point) -> PlayerRecord | None:
        """The nearest live non-teammate crewmate visible THIS tick, or ``None``."""

        crew = ic.visible_crew(belief)
        if not crew:
            return None
        return min(crew, key=lambda c: ic.dist2(self_xy, (c.world_x, c.world_y)))

    def _crew_in_room(self, belief: Belief, room: Room) -> list[PlayerRecord]:
        return [c for c in ic.visible_crew(belief) if ic.in_rect((c.world_x, c.world_y), room)]

    def _a_crewmate_left(self, belief: Belief, room: Room) -> PlayerRecord | None:
        """A crew member we had seen inside ``room`` that is now leaving — visible outside
        the room, or no longer visible (likely out a door). Returns the one to follow, or
        ``None``."""

        leavers = []
        for color in self._room_crew:
            if color in belief.teammate_colors:
                continue
            rec = belief.roster.get(color)
            if rec is None or rec.life_status == "dead":
                continue
            inside = ic.in_rect((rec.world_x, rec.world_y), room)
            recently = belief.last_tick - rec.last_seen_tick
            if not inside and recently <= 8:
                leavers.append(rec)  # last-known position is now outside the watched room
        if not leavers:
            return None
        cmd = commander_of(belief)
        target_player = cmd.target_player if cmd is not None else None
        return next((rec for rec in leavers if rec.color == target_player), leavers[0])

    def _room_task_indices(self, belief: Belief, room: Room) -> list[int]:
        tasks = belief.map.tasks if belief.map is not None else ()
        return [i for i in range(len(tasks)) if ic.in_rect((tasks[i].center.x, tasks[i].center.y), room)]

    def _room(self, belief: Belief, name: str | None) -> Room | None:
        if name is None or belief.map is None:
            return None
        return next((r for r in belief.map.rooms if r.name == name), None)
