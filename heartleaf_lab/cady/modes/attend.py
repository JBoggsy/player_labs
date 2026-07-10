"""Attend mode: go to another gnome's party and be counted as a guest.

Guests score 0 (only the host scores), so attending is a **reciprocity** move,
not a points grab — Cady attends only when her own food is low (hosting would
score little anyway; see the strategy's ATTEND_MAX_FOOD gate). It also keeps
self-play non-degenerate: without it, 9 host-only Cadys throw 9 empty parties.

Mechanically identical to HostMode's entry, but targets ``committed_party_house``
(the house whose invite we accepted) instead of our own: on the main map, walk to
that house's footprint and press A to enter; once on its home map, hold inside
until the dinner resolves. ``HOUSE_TARGETS[i]`` is a walkable point inside house
``i``, and A on a house footprint enters it (the overloaded-A mechanic).
"""

from __future__ import annotations

from cady import navigator
from cady.frame import to_map, to_world
from cady.mapdata import HOUSE_TARGETS, WALK_GRID
from cady.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode


class AttendMode(Mode[Belief, ActionState, Intent]):
    """Enter the committed party house and hold inside as a guest."""

    name = "attend"
    params_type = EmptyModeParams

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        if belief.self_xy is None:
            return Intent(kind="idle")

        # Already inside a home map -> we're in position as a guest; hold.
        if belief.map_context == "home":
            return Intent(kind="hold")

        target_map = self._party_target(belief)
        if target_map is None:
            return Intent(kind="idle")

        target_world = to_world(target_map)
        if _near(to_map(belief.self_xy), target_map):
            # Standing on the host's house footprint: press A to go inside.
            return Intent(kind="gather_at", point=target_world)
        waypoint = navigator.next_waypoint(belief, belief.self_xy, target_world, grid=WALK_GRID)
        if waypoint is None:
            return Intent(kind="idle")
        return Intent(kind="navigate_to", point=waypoint)

    def _party_target(self, belief: Belief) -> tuple[int, int] | None:
        house = belief.committed_party_house
        if house is None or not 0 <= house < len(HOUSE_TARGETS):
            return None
        return HOUSE_TARGETS[house]


def _near(a: tuple[int, int], b: tuple[int, int], radius: int = 6) -> bool:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= radius * radius


__all__ = ["AttendMode"]
