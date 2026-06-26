"""Search mode — the imposter's always-on seeking stance (design §7.2).

Replaces the retired occupancy-density Pretend/Search (cold-stored at
``modes/_deprecated/``). Its job is to keep us *near crew* so a kill window opens —
the measured imposter gap was being near crew about half as often as the top
imposters. It does NOT kill: when the kill is ready and a victim is visible the
strategy gate switches to Hunt.

The algorithm (James, 2026-06-24) — a small FSM:

  PICK_ROOM   choose a random nearby reachable room (not the current/just-left one)
                → GO_TO_ROOM
  GO_TO_ROOM  navigate to the room CENTRE (go fully inside to check it)
                • arrived, crew in the room  → WATCH
                • arrived, room empty         → PICK_ROOM
  WATCH       hold the in-room VANTAGE POINT with line-of-sight to the most crew —
              recomputed as they move, so we keep crewmates in sight instead of
              standing at the entrance letting them walk out of view
                • a crewmate leaves the room  → FOLLOW(that crewmate)
                • no crew left in the room     → PICK_ROOM
  FOLLOW(c)   chase ``c`` to their next room, using path prediction to keep going
              down the right hallway after they leave view
                • c settles in a room we reach → WATCH (loop)
                • c lost (prediction exhausted) → PICK_ROOM

Never follows the teammate imposter. The path predictor is fed only what we actually
see (the target's position when visible this tick, ``None`` otherwise), exactly as it
is scored offline (``strategy.path_prediction`` + ``tools/path_prediction_*``).
"""

from __future__ import annotations

import random

from crewrift.crewborg.modes import imposter_common as ic
from crewrift.crewborg.map.types import Room
from crewrift.crewborg.nav import _segment_clear
from crewrift.crewborg.strategy.commander.bias import commander_of, filter_or_fallback
from crewrift.crewborg.strategy.path_prediction import PathPredictor
from crewrift.crewborg.types import ActionState, Belief, Intent, PlayerRecord
from players.player_sdk import EmptyModeParams, Mode, ModeParams

ARRIVE_RADIUS_SQ = 24**2
# Consider only the few nearest rooms as "nearby" when picking a random one to sweep.
NEARBY_ROOMS = 4
# Drop a follow once the target has been unseen this long with no live prediction.
FOLLOW_LOST_TICKS = 120
# A crewmate counts as "still watchable" from a vantage if seen within this window.
WATCH_RECENT_TICKS = 36
# Line-of-sight range (px) for vantage scoring — generous; LOS through walls is the
# real gate. (Crewrift vision is the shadow overlay; no exact range constant.)
VANTAGE_RANGE = 360
VANTAGE_RANGE_SQ = VANTAGE_RANGE**2
# Coarse grid step (px) for candidate vantage points within a room.
VANTAGE_STEP = 40
# Recompute the vantage at most this often (crew move; LOS scans cost a little).
VANTAGE_REFRESH_TICKS = 18
# Only move to a new vantage if it sees at least this many MORE crew (hysteresis).
VANTAGE_SWITCH_MARGIN = 1


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
        self._vantage: ic.Point | None = None       # current watch position (max crew in sight)
        self._vantage_tick: int | None = None       # when the vantage was last recomputed
        self._follow_color: str | None = None
        self._predictor: PathPredictor | None = None
        self._last_seen_tick: int | None = None
        self._rng = random.Random(0xC0FFEE)

    # --- entry ----------------------------------------------------------------
    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        self_xy = ic.self_xy(belief)
        if self_xy is None or belief.map is None:
            return Intent(kind="idle", reason="no self position / map")

        if self._state == "pick_room":
            return self._pick_room(belief, self_xy)
        if self._state == "go_to_room":
            return self._go_to_room(belief, self_xy)
        if self._state == "watch":
            return self._watch(belief, self_xy)
        if self._state == "follow":
            return self._follow(belief, self_xy)
        return self._pick_room(belief, self_xy)

    # --- states ---------------------------------------------------------------
    def _pick_room(self, belief: Belief, self_xy: ic.Point) -> Intent:
        current = ic.room_containing(belief, self_xy)
        current_name = current.name if current is not None else None
        rooms = self._nearby_task_rooms(belief, self_xy, exclude={current_name, self._prev_room})
        if not rooms:  # fall back to any task room if all excluded
            rooms = self._nearby_task_rooms(belief, self_xy, exclude=set())
        if not rooms:
            return Intent(kind="idle", reason="search: no task rooms")
        cmd = commander_of(belief)
        hunt_room = cmd.hunt_room if cmd is not None else None
        room = next((candidate for candidate in rooms if candidate.name == hunt_room), None)
        if room is None:
            room = self._rng.choice(rooms)
        self._target_room = room.name
        # Head to the room CENTRE (go fully inside to check it), not a task spot by
        # the door — standing at the entrance misses crew and exits.
        self._goto_point = ic.reachable_point(belief, (room.center.x, room.center.y))
        self._room_crew = set()
        self._vantage = None
        self._vantage_tick = None
        self._state = "go_to_room"
        return self._go_to_room(belief, self_xy)

    def _go_to_room(self, belief: Belief, self_xy: ic.Point) -> Intent:
        room = self._room(belief, self._target_room)
        if room is None or self._goto_point is None:
            self._state = "pick_room"
            return self._pick_room(belief, self_xy)
        # A crewmate leaving anywhere we can see is worth chasing before we even arrive.
        leaver = self._a_crewmate_left(belief, room)
        if leaver is not None:
            return self._begin_follow(belief, leaver)
        if ic.dist2(self_xy, self._goto_point) <= ARRIVE_RADIUS_SQ or ic.in_rect(self_xy, room):
            crew = self._crew_in_room(belief, room)
            if not crew:
                self._prev_room = self._target_room
                self._state = "pick_room"
                return self._pick_room(belief, self_xy)
            self._room_crew = {c.color for c in crew}
            self._state = "watch"
            return self._watch(belief, self_xy)
        return Intent(kind="navigate_to", point=self._goto_point, reason="search: heading to a room to watch")

    def _watch(self, belief: Belief, self_xy: ic.Point) -> Intent:
        room = self._room(belief, self._target_room)
        if room is None:
            self._state = "pick_room"
            return self._pick_room(belief, self_xy)
        crew = self._crew_in_room(belief, room)
        self._room_crew |= {c.color for c in crew}
        leaver = self._a_crewmate_left(belief, room)
        if leaver is not None:
            return self._begin_follow(belief, leaver)
        if not self._room_crew_still_around(belief, room):
            self._prev_room = self._target_room
            self._state = "pick_room"
            return self._pick_room(belief, self_xy)

        # Hold the in-room vantage that sees the MOST crew — recomputed as they move,
        # so we keep crewmates in sight rather than standing at the entrance. (The old
        # door/task-spot habit let crew walk out of view; that was killing kills.)
        self._refresh_vantage(belief, room, self_xy)
        if self._vantage is not None and ic.dist2(self_xy, self._vantage) > ARRIVE_RADIUS_SQ:
            return Intent(kind="navigate_to", point=self._vantage, reason="search: moving to a vantage over the crew")
        return Intent(kind="idle", reason="search: watching the crew from a vantage")

    def _refresh_vantage(self, belief: Belief, room: Room, self_xy: ic.Point) -> None:
        """(Re)pick the point in ``room`` with line-of-sight to the most watchable
        crew, throttled, with hysteresis so we don't jitter between equal vantages."""

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
        """Argmax over a coarse grid of reachable in-room points of how many crew
        each has line-of-sight to. Ties broken toward staying put (less movement)."""

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
            return Intent(kind="navigate_to", point=(target.world_x, target.world_y),
                          reason="search: following a leaver (visible)")

        # Out of view: chase down the predicted hallway toward the top route's position.
        if self._last_seen_tick is not None and belief.last_tick - self._last_seen_tick > FOLLOW_LOST_TICKS:
            return self._stop_follow(belief, self_xy)
        best = self._predictor.best()
        if best is None:
            return self._stop_follow(belief, self_xy)
        return Intent(kind="navigate_to", point=tuple(best.pred_pos),
                      reason="search: chasing predicted path (occluded)")

    # --- follow lifecycle -----------------------------------------------------
    def _begin_follow(self, belief: Belief, leaver: PlayerRecord) -> Intent:
        self._follow_color = leaver.color
        self._predictor = PathPredictor(nav=belief.nav, map=belief.map)
        self._last_seen_tick = belief.last_tick if leaver.last_seen_tick == belief.last_tick else None
        self._state = "follow"
        if leaver.last_seen_tick == belief.last_tick:
            self._predictor.observe(belief.last_tick, (leaver.world_x, leaver.world_y))
        return Intent(kind="navigate_to", point=(leaver.world_x, leaver.world_y),
                      reason="search: a crewmate left — follow")

    def _stop_follow(self, belief: Belief, self_xy: ic.Point) -> Intent:
        # If we ended up in a room with crew, watch it; else pick a new room.
        self._follow_color = None
        self._predictor = None
        self._last_seen_tick = None
        room = ic.room_containing(belief, self_xy)
        if room is not None and self._crew_in_room(belief, room):
            self._target_room = room.name
            self._room_crew = {c.color for c in self._crew_in_room(belief, room)}
            self._vantage = None
            self._vantage_tick = None
            self._state = "watch"
            return self._watch(belief, self_xy)
        self._prev_room = room.name if room is not None else self._prev_room
        self._state = "pick_room"
        return self._pick_room(belief, self_xy)

    # --- helpers --------------------------------------------------------------
    def _crew_in_room(self, belief: Belief, room: Room) -> list[PlayerRecord]:
        return [c for c in ic.visible_crew(belief) if ic.in_rect((c.world_x, c.world_y), room)]

    def _a_crewmate_left(self, belief: Belief, room: Room) -> PlayerRecord | None:
        """A crew member we had seen inside ``room`` that is now leaving — visible
        outside the room, or no longer visible (likely out a door). Returns the one
        to follow, or ``None``."""

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

    def _room_crew_still_around(self, belief: Belief, room: Room) -> bool:
        if not self._room_crew:
            return False
        for color in self._room_crew:
            rec = belief.roster.get(color)
            if rec is None or rec.life_status == "dead":
                continue
            if belief.last_tick - rec.last_seen_tick <= 48:
                return True
        return False

    def _nearby_task_rooms(self, belief: Belief, self_xy: ic.Point, exclude: set) -> list[Room]:
        start = ic.starting_room(belief)
        start_name = start.name if start is not None else None
        rooms = []
        for room in belief.map.rooms:
            if room.name in exclude or room.name == start_name:
                continue
            if not self._room_task_indices(belief, room):
                continue  # only rooms with a task station to idle/blend at
            rooms.append(room)
        rooms.sort(key=lambda r: ic.dist2(self_xy, (r.center.x, r.center.y)))
        rooms = rooms[:NEARBY_ROOMS]
        cmd = commander_of(belief)
        if cmd is None or cmd.avoid_room is None:
            candidates = rooms
        else:
            candidates = filter_or_fallback(rooms, lambda room: room.name != cmd.avoid_room)
        if cmd is not None and cmd.strength == "hard" and cmd.hunt_room is not None:
            hunt_room = self._room(belief, cmd.hunt_room)
            if (
                hunt_room is not None
                and self._room_task_indices(belief, hunt_room)
                and all(room.name != hunt_room.name for room in candidates)
            ):
                candidates.append(hunt_room)
        return candidates

    def _room_task_indices(self, belief: Belief, room: Room) -> list[int]:
        tasks = belief.map.tasks if belief.map is not None else ()
        return [i for i in range(len(tasks)) if ic.in_rect((tasks[i].center.x, tasks[i].center.y), room)]

    def _room(self, belief: Belief, name: str | None) -> Room | None:
        if name is None or belief.map is None:
            return None
        return next((r for r in belief.map.rooms if r.name == name), None)
