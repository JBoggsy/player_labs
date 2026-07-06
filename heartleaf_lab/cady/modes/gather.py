"""Gather mode: follow the baked garden circuit and harvest on arrival."""

from __future__ import annotations

import math

from cady import navigator
from cady.config import HARVEST_RADIUS
from cady.frame import to_map, to_world
from cady.mapdata import GARDEN_APPROACHES, GARDEN_CIRCUIT, GARDEN_RECTS
from cady.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode

Point = tuple[int, int]
Rect = tuple[int, int, int, int]


class GatherMode(Mode[Belief, ActionState, Intent]):
    """Walk the fixed garden circuit, pressing A at each reachable garden."""

    name = "gather"
    params_type = EmptyModeParams

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        if belief.self_xy is None:
            return Intent(kind="idle")

        garden_index = GARDEN_CIRCUIT[belief.circuit_index % len(GARDEN_CIRCUIT)]
        approach_world = to_world(GARDEN_APPROACHES[garden_index])
        garden_rect = GARDEN_RECTS[garden_index]

        if _point_rect_distance(to_map(belief.self_xy), garden_rect) <= HARVEST_RADIUS:
            belief.circuit_index += 1
            navigator.clear_navigation(belief)
            return Intent(kind="gather_at", point=approach_world)

        waypoint = navigator.next_waypoint(belief, belief.self_xy, approach_world)
        if waypoint is None:
            belief.circuit_index += 1
            navigator.clear_navigation(belief)
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


__all__ = ["GatherMode"]
