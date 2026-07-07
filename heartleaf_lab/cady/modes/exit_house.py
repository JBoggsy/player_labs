"""Exit-house mode: leave the shared Heartleaf home interior."""

from __future__ import annotations

import math

from cady import navigator
from cady.config import EXIT_RADIUS
from cady.frame import to_map, to_world
from cady.mapdata import HOME_EXIT, HOME_EXIT_RECT, HOME_WALK_GRID
from cady.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode

Point = tuple[int, int]
Rect = tuple[int, int, int, int]


class ExitHouseMode(Mode[Belief, ActionState, Intent]):
    """Route to the home-interior exit and press A at the door."""

    name = "exit_house"
    params_type = EmptyModeParams

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        if belief.self_xy is None:
            return Intent(kind="idle")

        exit_world = to_world(HOME_EXIT)
        if _point_rect_distance(to_map(belief.self_xy), HOME_EXIT_RECT) <= EXIT_RADIUS:
            return Intent(kind="gather_at", point=exit_world)

        waypoint = navigator.next_waypoint(belief, belief.self_xy, exit_world, grid=HOME_WALK_GRID)
        if waypoint is None:
            return Intent(kind="idle")
        return Intent(kind="navigate_to", point=waypoint)


def _point_rect_distance(point: Point, rect: Rect) -> float:
    x, y = point
    left, top, width, height = rect
    right = left + width
    bottom = top + height
    dx = max(left - x, 0, x - right)
    dy = max(top - y, 0, y - bottom)
    return math.hypot(dx, dy)


__all__ = ["ExitHouseMode"]
