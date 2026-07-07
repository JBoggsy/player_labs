"""Invite mode: seek a crowd and broadcast an invite to OUR party.

Only the host scores (``score = food × guests``), so pulling villagers to our
house is the whole scoring lever. Mechanic (see
`docs/villager-dinner-attendance.md` + [[heartleaf-villager-exploits]]): a
villager that HEARS our chat records it into its LLM conversation; if that line
names a house ("<Owner>'s house"), the villager can commit to attending it, and
its deterministic layer then locks it there. Chat has no radius — a hearer only
gets the bubble if it lands on their 320x200 viewport — so reaching *several*
villagers at once means going to where they are and speaking to the group.

Deterministic-floor behavior — a fast door-to-door tour:
- **Rush the other houses.** From 3 PM, visit the 8 OTHER houses in a
  greedy-nearest order (skip our own — we host there). Villagers stand at their
  own doors 3-5 PM (occupancy heatmap) and their souls only start hosting/
  double-booking at 4 PM, so we hit them early, while they're still "free" to
  accept — first invite heard wins (they won't promise two dinners).
- **Broadcast to anyone in view, en route and at each door.** The moment
  ``INVITE_MIN_AUDIENCE`` (=1) gnome is in our viewport we send the invite (a
  gnome hears our chat iff our bubble lands on their screen ≈ they're in view of
  us). We pass through, not dwell — coverage over thoroughness. The line names
  our OWN house by owner display name — the form a hearer's LLM parses into a
  commitment to attend us.
- **Return home before the cutoff.** Past ``INVITE_RETURN_MINUTES`` (4:45 PM)
  head to our own door, so we're inside to host by the 5 PM enter cutoff.

We do NOT track who we invited or chase individual gnomes this round — just rush
and blanket-invite before 4 PM. (Per-player memory / conversations are a later
layer.) An optional LLM layer will later pick targets and author the line.
"""

from __future__ import annotations

from cady import navigator, occupancy
from cady.config import (
    DOOR_REACH_RADIUS,
    INVITE_BROADCAST_DEADLINE_MINUTES,
    INVITE_MAP_CENTER,
    INVITE_MIN_AUDIENCE,
    INVITE_MIN_INTERVAL_TICKS,
    INVITE_RETURN_MINUTES,
    INVITE_VIEW_HALF_H,
    INVITE_VIEW_HALF_W,
    PLAYER_NAMES,
)
from cady.frame import to_world
from cady.mapdata import HOUSE_TARGETS, WALK_GRID
from cady.types import ActionState, Belief, Gnome, Intent
from players.player_sdk import EmptyModeParams, Mode

Point = tuple[int, int]


class InviteMode(Mode[Belief, ActionState, Intent]):
    """Seek the crowd, broadcast an invite to the group, return home in time."""

    name = "invite"
    params_type = EmptyModeParams

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        if belief.self_xy is None or belief.own_house_index is None:
            return Intent(kind="idle")

        if action_state.invite_cooldown > 0:
            action_state.invite_cooldown -= 1

        others = self._other_gnomes(belief)
        chat = self._maybe_invite(belief, action_state, others)
        goal = self._seek_goal(belief, others)

        if goal is None or _near(belief.self_xy, goal):
            return Intent(kind="hold", chat=chat)
        waypoint = navigator.next_waypoint(belief, belief.self_xy, goal, grid=WALK_GRID)
        if waypoint is None:
            return Intent(kind="hold", chat=chat)
        return Intent(kind="navigate_to", point=waypoint, chat=chat)

    def _seek_goal(self, belief: Belief, others: list[Gnome]) -> Point | None:
        """Where to move — a fast door-to-door tour of the OTHER houses:
        1. return time (>= 4:45 PM) → head to our own door to host in time;
        2. else → the nearest not-yet-reached other-house door (greedy tour),
           marking a door reached once we're on it, and broadcasting to anyone
           in view the whole way (handled in decide, threshold 1);
        3. all doors done with time to spare → the occupancy hot spot / map
           center, to keep working whoever's still out.
        We do NOT chase the live centroid here: the doors are provably where the
        villagers are 3-5 PM, so a fixed rush covers more of them than reacting."""
        del others  # broadcasting keys off visibility in decide, not the goal
        self_xy = belief.self_xy
        assert self_xy is not None  # guarded by caller

        minutes = belief.last_time_minutes
        if minutes is not None and minutes >= INVITE_RETURN_MINUTES:
            return self._own_house_target(belief)

        # Mark the door we're standing on as reached, then aim at the nearest one
        # we haven't reached yet (excluding our own house).
        self._mark_reached_door(belief, self_xy)
        target = self._nearest_unreached_door(belief, self_xy)
        if target is not None:
            return target

        # Every door covered — keep advertising from the busy spots.
        hot = occupancy.hottest_spot(minutes, avoid=self_xy)
        return hot if hot is not None else INVITE_MAP_CENTER

    def _mark_reached_door(self, belief: Belief, self_xy: Point) -> None:
        for i, target in enumerate(HOUSE_TARGETS):
            if i == belief.own_house_index:
                continue
            if _near(self_xy, target, radius=DOOR_REACH_RADIUS):
                belief.invited_houses.add(i)

    def _nearest_unreached_door(self, belief: Belief, self_xy: Point) -> Point | None:
        best: Point | None = None
        best_d2 = None
        for i, target in enumerate(HOUSE_TARGETS):
            if i == belief.own_house_index or i in belief.invited_houses:
                continue
            d2 = (target[0] - self_xy[0]) ** 2 + (target[1] - self_xy[1]) ** 2
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best = target
        return best

    def _maybe_invite(
        self, belief: Belief, action_state: ActionState, others: list[Gnome]
    ) -> str | None:
        """Broadcast once enough gnomes can see our bubble (relaxing to one as the
        window closes), respecting the rate limit."""
        if action_state.invite_cooldown > 0:
            return None
        audience = self._audience_count(belief, others)
        needed = self._required_audience(belief)
        if audience < needed:
            return None
        action_state.invite_cooldown = INVITE_MIN_INTERVAL_TICKS
        return self._invite_line(belief.own_house_index)

    def _audience_count(self, belief: Belief, others: list[Gnome]) -> int:
        """How many other gnomes would see our chat bubble = are within our
        viewport box (they hear us iff our bubble lands on their screen; each
        camera is self-centered, so this is symmetric with "in view of us")."""
        sx, sy = belief.self_xy  # type: ignore[misc]  # guarded by caller
        return sum(
            1
            for g in others
            if abs(g.pos[0] - sx) <= INVITE_VIEW_HALF_W and abs(g.pos[1] - sy) <= INVITE_VIEW_HALF_H
        )

    def _required_audience(self, belief: Belief) -> int:
        minutes = belief.last_time_minutes
        if minutes is not None and minutes >= INVITE_BROADCAST_DEADLINE_MINUTES:
            return 1  # window closing: take whoever we can reach
        return INVITE_MIN_AUDIENCE

    def _other_gnomes(self, belief: Belief) -> list[Gnome]:
        return [g for g in belief.gnomes if g.index != belief.own_house_index]

    def _own_house_target(self, belief: Belief) -> Point | None:
        index = belief.own_house_index
        if index is None or not 0 <= index < len(HOUSE_TARGETS):
            return None
        return HOUSE_TARGETS[index]

    def _invite_line(self, own_house_index: int) -> str:
        """A ≤48-char invite naming OUR house by owner display name — the form a
        hearer's LLM parses into a house commitment."""
        owner = PLAYER_NAMES[own_house_index] if 0 <= own_house_index < len(PLAYER_NAMES) else "my"
        return f"Party at {owner}'s house at 6! Lots of food, come!"[:48]


def _near(a: Point, b: Point, radius: int = 6) -> bool:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= radius * radius


__all__ = ["InviteMode"]
