"""Invite mode: seek a crowd and broadcast an invite to OUR party.

Only the host scores (``score = food × guests``), so pulling villagers to our
house is the whole scoring lever. Mechanic (see
`docs/villager-dinner-attendance.md` + [[heartleaf-villager-exploits]]): a
villager that HEARS our chat records it into its LLM conversation; if that line
names a house ("<Owner>'s house"), the villager can commit to attending it, and
its deterministic layer then locks it there. Chat has no radius — a hearer only
gets the bubble if it lands on their 320x200 viewport — so reaching *several*
villagers at once means going to where they are and speaking to the group.

Deterministic-floor behavior:
- **Seek a center of gravity.** Head toward the centroid of visible gnomes (the
  crowd); if none are visible yet, head to the map center to go find one.
- **Broadcast to the group, not the first passer-by.** Only chat once
  ``INVITE_MIN_AUDIENCE`` gnomes are in our viewport at once (a gnome hears our
  chat iff our bubble lands on their screen; cameras are self-centered so that's
  ~"the gnome is in view of us"), relaxing to "anyone in view" as the window
  closes. The line names our OWN house by owner display name — the form a
  hearer's LLM parses into a commitment to attend us.
- **Return home before the cutoff.** Past ``INVITE_RETURN_MINUTES`` head back to
  our own door, so we're never caught far away at the 5 PM host-enter cutoff.

An optional LLM layer (increment 3) will later pick specific targets and author
the line; this floor recruits the visible crowd with a fixed, effective template.
"""

from __future__ import annotations

from cady import navigator, occupancy
from cady.config import (
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
        """Where to move (blend live + learned):
        1. return time → back to our own door (never miss the host cutoff);
        2. gnomes visible → their live center of gravity (react to what we see);
        3. screen empty → the empirically-hottest spot for this game-hour from
           the baked occupancy heatmap (go where players usually are now);
        4. no heatmap baked → the map center (last-resort blind fallback)."""
        minutes = belief.last_time_minutes
        if minutes is not None and minutes >= INVITE_RETURN_MINUTES:
            return self._own_house_target(belief)
        if others:
            cx = sum(g.pos[0] for g in others) // len(others)
            cy = sum(g.pos[1] for g in others) // len(others)
            return (cx, cy)
        hot = occupancy.hottest_spot(minutes, avoid=belief.self_xy)
        return hot if hot is not None else INVITE_MAP_CENTER

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
