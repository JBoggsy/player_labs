"""Invite mode: draw guests to OUR party by broadcasting an invite.

Only the host scores (``score = food × guests``), so getting villagers to come
to our house is the whole scoring lever. Mechanic (see
`docs/villager-dinner-attendance.md` + [[heartleaf-villager-exploits]]): a
villager that HEARS our chat records it into its LLM conversation; if that line
names a house ("<Owner>'s house"), the villager can commit to attending it, and
its deterministic layer then locks it there. Chat has no radius — a hearer only
gets the bubble if it lands on their 320x200 viewport — so we broadcast when
players are near.

Strategy (deterministic floor): stand just outside our OWN house and repeatedly
broadcast an invite that names our house by its owner display name
(``PLAYER_NAMES[own_house_index]``). Standing at our door means anyone who hears
also SEES the party forming there, which snowballs the crowd. An optional LLM
layer will later choose specific (food-poor) targets and author the line; this
floor invites everyone nearby with a fixed, effective template.
"""

from __future__ import annotations

from cady import navigator
from cady.config import (
    INVITE_HEARING_RADIUS,
    INVITE_MIN_INTERVAL_TICKS,
    PLAYER_NAMES,
)
from cady.frame import to_map, to_world
from cady.mapdata import HOUSE_TARGETS, WALK_GRID
from cady.types import ActionState, Belief, Gnome, Intent
from players.player_sdk import EmptyModeParams, Mode

Point = tuple[int, int]


class InviteMode(Mode[Belief, ActionState, Intent]):
    """Broadcast an invite from our own doorstep to pull guests to our party."""

    name = "invite"
    params_type = EmptyModeParams

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        if belief.self_xy is None or belief.own_house_index is None:
            return Intent(kind="idle")

        target = self._own_house_target(belief)
        if target is None:
            return Intent(kind="idle")
        target_world = to_world(target)

        # Rate-limit the broadcast (bubbles linger ~5s); tick the cooldown here
        # since invite is the only speaker.
        if action_state.invite_cooldown > 0:
            action_state.invite_cooldown -= 1

        chat = None
        if action_state.invite_cooldown == 0 and self._someone_in_earshot(belief):
            chat = self._invite_line(belief.own_house_index)
            action_state.invite_cooldown = INVITE_MIN_INTERVAL_TICKS

        # Hold at our doorstep once there, else walk to it — broadcasting either
        # way when someone's in range.
        if _near(belief.self_xy, target_world):
            return Intent(kind="hold", chat=chat)
        waypoint = navigator.next_waypoint(belief, belief.self_xy, target_world, grid=WALK_GRID)
        if waypoint is None:
            return Intent(kind="hold", chat=chat)
        return Intent(kind="navigate_to", point=waypoint, chat=chat)

    def _own_house_target(self, belief: Belief) -> Point | None:
        index = belief.own_house_index
        if index is None or not 0 <= index < len(HOUSE_TARGETS):
            return None
        return HOUSE_TARGETS[index]

    def _someone_in_earshot(self, belief: Belief) -> bool:
        """True if any other gnome is within hearing range of us (so the invite
        bubble would land on their screen)."""
        sx, sy = belief.self_xy  # type: ignore[misc]  # guarded by caller
        for gnome in belief.gnomes:
            if _is_self(gnome, belief.own_house_index):
                continue
            gx, gy = gnome.pos
            if (gx - sx) ** 2 + (gy - sy) ** 2 <= INVITE_HEARING_RADIUS ** 2:
                return True
        return False

    def _invite_line(self, own_house_index: int) -> str:
        """A ≤48-char invite naming OUR house by owner display name — the form a
        hearer's LLM parses into a house commitment."""
        owner = PLAYER_NAMES[own_house_index] if 0 <= own_house_index < len(PLAYER_NAMES) else "my"
        return f"Party at {owner}'s house at 6! Lots of food, come!"[:48]


def _is_self(gnome: Gnome, own_house_index: int | None) -> bool:
    return own_house_index is not None and gnome.index == own_house_index


def _near(a: Point, b: Point, radius: int = 6) -> bool:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= radius * radius


__all__ = ["InviteMode"]
