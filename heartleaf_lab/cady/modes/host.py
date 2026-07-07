"""Host mode: go to our own house and hold inside it to host dinner.

To score, the host must be INSIDE their own home map at dinner with >=1 guest
also inside (heartleaf ``startDinnerParties``: ``host.mapIndex != mapIndex`` is
skipped). So hosting is: on the main map, walk to our own house's footprint and
press A to enter; once on the home map, hold inside until dinner resolves.

Our house index == our gnome index (heartleaf ``addPlayer``:
``gnomeIndex = houseIndex mod gnomes.len``), which perception reports as
``own_house_index`` — so no seat calibration is needed. ``HOUSE_TARGETS[i]`` is a
walkable point inside house ``i``'s footprint, and A on a house footprint enters
it (the overloaded-A mechanic), which is exactly the entry action we want.
"""

from __future__ import annotations

from cady import navigator
from cady.frame import to_map, to_world
from cady.mapdata import HOUSE_TARGETS, WALK_GRID
from cady.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode


class HostMode(Mode[Belief, ActionState, Intent]):
    """Enter our own house and hold inside it to host."""

    name = "host"
    params_type = EmptyModeParams

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        if belief.self_xy is None:
            return Intent(kind="idle")

        # Already inside a home map -> we're in position to host; hold.
        if belief.map_context == "home":
            return Intent(kind="hold")

        # On the main map: head to our own house and enter it. Fall back to the
        # recorded home anchor if we don't yet know our house index.
        target_map = self._own_house_target(belief)
        if target_map is None:
            return self._navigate_or_idle(belief, belief.home_anchor)

        target_world = to_world(target_map)
        if to_map(belief.self_xy) == target_map or _near(to_map(belief.self_xy), target_map):
            # Standing on our house footprint: press A to go inside.
            return Intent(kind="gather_at", point=target_world)
        return self._navigate_or_idle(belief, target_world)

    def _own_house_target(self, belief: Belief) -> tuple[int, int] | None:
        index = belief.own_house_index
        if index is None or not 0 <= index < len(HOUSE_TARGETS):
            return None
        return HOUSE_TARGETS[index]

    def _navigate_or_idle(self, belief: Belief, goal_world: tuple[int, int] | None) -> Intent:
        if goal_world is None or belief.self_xy is None:
            return Intent(kind="idle")
        waypoint = navigator.next_waypoint(belief, belief.self_xy, goal_world, grid=WALK_GRID)
        if waypoint is None:
            return Intent(kind="idle")
        return Intent(kind="navigate_to", point=waypoint)


def _near(a: tuple[int, int], b: tuple[int, int], radius: int = 6) -> bool:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= radius * radius


__all__ = ["HostMode"]
