"""Evade mode: after a kill, LEAVE the scene toward a crew-dense room (design §7.2).

Rewritten 2026-06-26 (James) to head toward where the crew most likely are (the
expected-crew occupancy grid, ``agent_tracking`` §10.2) instead of fleeing blindly,
so a victim cluster is nearby when the post-kill window hands back to Search/Recon.

Amended 2026-07-21 (kill→WIN thread, design
docs/designs/2026-07-21-imposter-kill-to-win-design.md): the crew-seeking target must
also be **away from the kill scene**. The unconstrained densest-crew target was
usually the room we just killed in (we kill where the crew are; room hysteresis then
pinned it), so the imposter moved a median 4px in the 60 ticks after its own kill vs
the field's 23–40px — it lay in wait ON the body, collected near-body sightings, and
was ejected after 62% of witnessed kills (field 32%). Now Evade latches the kill
scene and prefers, in order:

1. the densest crew *room* whose center is at least ``FLEE_SCENE_RADIUS`` from the
   scene (croatoan room centers sit ~190–280px apart, so this excludes the kill room
   while keeping adjacent rooms eligible — leave the scene, not cross the map);
2. the hottest occupancy *cell* that far from the scene (no room has crew mass);
3. the room center *farthest* from the scene (occupancy cold: a plausible
   destination beats standing over the body);
4. the most-recently-seen crewmate (cold start, before the map/occupancy exist).

We WALK (``navigate_to``), never vent: a witnessed vent is citable evidence, while
walking toward a task room is the anti-tell. This stays deliberately paired with
Hunt's **drop the witness requirement after the first kill** (`modes/hunt.py`):
re-approaching crew is a poor place to land an *unwitnessed* kill, but once
witnesses no longer veto the second kill, the crowd is target-rich exactly when we
need it.
"""

from __future__ import annotations

import math

from crewrift.crewborg import agent_tracking as at
from crewrift.crewborg.modes import imposter_common as ic
from crewrift.crewborg.strategy.opportunity import most_recent_victim
from crewrift.crewborg.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode, ModeParams

# Min distance (world px) from the kill scene for a flee destination. Sized off the
# croatoan room grid (centers ~190-280px apart): the kill room's own center is always
# closer than this, adjacent rooms are not — so the filter means "a different room".
FLEE_SCENE_RADIUS = 160
FLEE_SCENE_RADIUS_SQ = FLEE_SCENE_RADIUS**2


class EvadeMode(Mode[Belief, ActionState, Intent]):
    name = "evade"
    params_type = EmptyModeParams

    def __init__(self, params: ModeParams | None = None) -> None:
        super().__init__(params)
        # The kill scene, latched from our position on the first Evade tick after
        # each kill (keyed by last_kill_tick so a reused instance re-latches).
        self._scene_kill_tick: int | None = None
        self._scene_xy: tuple[int, int] | None = None
        self._flee_traced_kill_tick: int | None = None

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        self_xy = ic.self_xy(belief)
        scene = self._latch_scene(belief, self_xy)

        if self_xy is not None:
            room = at.best_pretend_room_target(
                belief, self_xy, eligible_room_names=_rooms_away_from(belief, scene)
            )
            if room is not None:
                self._trace_flee(belief, scene, room.point, "crew_room")
                return Intent(
                    kind="navigate_to",
                    point=room.point,
                    reason=f"evade: leave the scene for the densest crew area ({room.room_name})",
                )
            cell = _seek_point_away_from(belief, scene)
            if cell is not None:
                self._trace_flee(belief, scene, cell, "occupancy_cell")
                return Intent(kind="navigate_to", point=cell, reason="evade: hottest occupancy cell off the scene")
            fallback = _farthest_room_center(belief, scene)
            if fallback is not None:
                self._trace_flee(belief, scene, fallback, "farthest_room")
                return Intent(
                    kind="navigate_to",
                    point=fallback,
                    reason="evade: occupancy cold, leave the scene for the farthest room",
                )

        victim = most_recent_victim(belief)
        if victim is not None:
            return Intent(
                kind="navigate_to",
                point=(victim.world_x, victim.world_y),
                reason="evade: no occupancy yet, close on the last-seen crewmate",
            )
        return Intent(kind="idle", reason="evade: no crew area to approach")

    def _latch_scene(self, belief: Belief, self_xy: tuple[int, int] | None) -> tuple[int, int] | None:
        """The kill scene for the current Evade window (our position when it opened).

        ``None`` before a kill is known or before we know our own position — the
        scene filter then passes everything, matching the pre-flee behavior.
        """

        if belief.last_kill_tick is None:
            return None
        if self._scene_kill_tick != belief.last_kill_tick and self_xy is not None:
            self._scene_kill_tick = belief.last_kill_tick
            self._scene_xy = self_xy
        return self._scene_xy if self._scene_kill_tick == belief.last_kill_tick else None

    def _trace_flee(self, belief: Belief, scene: tuple[int, int] | None, dest: tuple[int, int], kind: str) -> None:
        """One ``post_kill_flee`` record per kill — the A/B mechanism check."""

        if scene is None or self._flee_traced_kill_tick == belief.last_kill_tick:
            return
        self._flee_traced_kill_tick = belief.last_kill_tick
        self.emit.event(
            "post_kill_flee",
            {
                "kill_tick": belief.last_kill_tick,
                "scene": list(scene),
                "dest": list(dest),
                "dest_kind": kind,
                "dest_dist": round(math.dist(scene, dest), 1),
            },
        )
        self.emit.counter("post_kill_flee", tags={"dest_kind": kind})


def _rooms_away_from(belief: Belief, scene: tuple[int, int] | None) -> set[str] | None:
    """Room names whose center clears ``FLEE_SCENE_RADIUS`` from the scene, or
    ``None`` (no filter) when there is no scene/map. An empty set is possible on a
    tiny (test) map — ``best_pretend_room_target`` then returns None and the caller
    falls through to the non-room targets."""

    if scene is None or belief.map is None:
        return None
    return {
        room.name
        for room in belief.map.rooms
        if _dist2((room.center.x, room.center.y), scene) >= FLEE_SCENE_RADIUS_SQ
    }


def _seek_point_away_from(belief: Belief, scene: tuple[int, int] | None) -> tuple[int, int] | None:
    """The hottest occupancy cell off the scene (all cells when there is no scene)."""

    for point in at.ranked_seek_points(belief):
        if scene is None or _dist2(point, scene) >= FLEE_SCENE_RADIUS_SQ:
            return point
    return None


def _farthest_room_center(belief: Belief, scene: tuple[int, int] | None) -> tuple[int, int] | None:
    """The room center farthest from the scene — the plausible-destination flee when
    occupancy has no mass to steer by. ``None`` with no scene (pre-flee Evade never
    had a blind target; keep that) or no rooms."""

    if scene is None or belief.map is None or not belief.map.rooms:
        return None
    center = max(belief.map.rooms, key=lambda room: _dist2((room.center.x, room.center.y), scene)).center
    return (center.x, center.y)


def _dist2(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
