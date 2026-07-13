"""Gather mode: follow the baked garden circuit and harvest on arrival."""

from __future__ import annotations

import math

from cady import navigator
from cady.config import HARVEST_RADIUS, MARKER_SIGHT_RADIUS, MAX_GATHER_TICKS
from cady.frame import to_map, to_world
from cady.mapdata import (
    GARDEN_APPROACHES,
    GARDEN_CIRCUIT,
    GARDEN_RECTS,
    HOUSE_RECTS,
    WALK_GRID,
)
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
            # Reached the circuit garden. Only press A if there's an actual food
            # marker in range: a marker only appears when a garden holds food, so
            # this skips depleted gardens AND avoids pressing A on a spot whose
            # harvest radius overlaps a house footprint (where A would ENTER the
            # house, not harvest — the game overloads A: harvest / enter / exit).
            if not _food_marker_in_range(belief):
                belief.circuit_index += 1
                belief.gather_active_index = None
                navigator.clear_navigation(belief)
                return Intent(kind="idle")

            # Food is here, but if our foot is on a house footprint an A press
            # would ENTER the house instead of harvesting — step toward the
            # approach point to clear the house first, then harvest.
            if _foot_on_house(to_map(belief.self_xy)):
                belief.gather_active_index = None
                waypoint = navigator.next_waypoint(
                    belief, belief.self_xy, approach_world, grid=WALK_GRID
                )
                if waypoint is None:
                    belief.circuit_index += 1
                    navigator.clear_navigation(belief)
                    return Intent(kind="idle")
                return Intent(kind="navigate_to", point=waypoint)

            # In range with food: press A and STAY until a pickup is confirmed
            # (inventory rose) or we time out — rather than firing one press and
            # advancing, which lost the garden on any marginal miss.
            if belief.gather_active_index != garden_index:
                belief.gather_active_index = garden_index
                belief.gather_inv_baseline = belief.inventory_count
                belief.gather_ticks = 0
            belief.gather_ticks += 1

            harvested = belief.inventory_count > belief.gather_inv_baseline
            if harvested or belief.gather_ticks >= MAX_GATHER_TICKS:
                belief.circuit_index += 1
                belief.gather_active_index = None
                navigator.clear_navigation(belief)
                return Intent(kind="idle")
            return Intent(kind="gather_at", point=approach_world)

        # Out of range: abandon any in-progress attempt and walk to the garden.
        belief.gather_active_index = None
        waypoint = navigator.next_waypoint(belief, belief.self_xy, approach_world, grid=WALK_GRID)
        if waypoint is None:
            belief.circuit_index += 1
            navigator.clear_navigation(belief)
            return Intent(kind="idle")
        return Intent(kind="navigate_to", point=waypoint)


def _food_marker_in_range(belief: Belief) -> bool:
    """True if a visible garden marker with food is within harvesting sight.

    Garden markers (``belief.food_gardens``) only appear while a garden holds
    food, so their presence is the ground truth for "there is something to
    harvest here" — more reliable than the baked circuit, which can point at a
    now-empty garden or a spot near a house."""
    if belief.self_xy is None:
        return False
    sx, sy = belief.self_xy
    for garden in belief.food_gardens:
        if not garden.has_food:
            continue
        gx, gy = garden.pos
        if math.hypot(gx - sx, gy - sy) <= MARKER_SIGHT_RADIUS:
            return True
    return False


def _foot_on_house(point: Point) -> bool:
    """True when a map-coord point sits inside any house footprint."""
    x, y = point
    for hx, hy, hw, hh in HOUSE_RECTS:
        if hx <= x <= hx + hw and hy <= y <= hy + hh:
            return True
    return False


def _point_rect_distance(point: Point, rect: Rect) -> float:
    x, y = point
    left, top, width, height = rect
    right = left + width
    bottom = top + height
    dx = max(left - x, 0, x - right)
    dy = max(top - y, 0, y - bottom)
    return math.hypot(dx, dy)


__all__ = ["GatherMode"]
