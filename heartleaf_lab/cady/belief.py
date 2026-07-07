"""Long-lived Cady belief state updates."""

from __future__ import annotations

from cady import navigator
from cady.types import Belief, HeartleafState

MORNING_CUTOFF_MINUTES = 120


def update_belief(belief: Belief, percept: HeartleafState) -> None:
    """Fold one perception frame into mutable belief.

    A first ready frame records a fallback ``home_anchor``. If a later true
    morning frame appears, the fallback is upgraded once; after a morning anchor
    exists it is stable for the episode.
    """

    _update_map_context(belief, percept)
    if not percept.ready:
        belief.food_gardens = ()
        return

    belief.self_xy = percept.self_xy
    belief.food_gardens = percept.gardens
    belief.gnomes = percept.gnomes
    _update_home_anchor(belief, percept)
    for garden in percept.gardens:
        belief.garden_positions[garden.object_id] = garden.pos

    if percept.own_house_index is not None:
        belief.own_house_index = percept.own_house_index
    belief.last_time_minutes = percept.time_minutes
    belief.inventory_count = percept.inventory_count


def _update_map_context(belief: Belief, percept: HeartleafState) -> None:
    if percept.map_context == "unknown":
        return
    if belief.map_context != percept.map_context:
        navigator.clear_navigation(belief)
    belief.map_context = percept.map_context


def _update_home_anchor(belief: Belief, percept: HeartleafState) -> None:
    if percept.self_xy is None:
        return

    morning = _is_morning(percept)
    if belief.home_anchor is None:
        belief.home_anchor = percept.self_xy
        belief.home_anchor_is_morning = morning
    elif morning and not belief.home_anchor_is_morning:
        belief.home_anchor = percept.self_xy
        belief.home_anchor_is_morning = True


def _is_morning(percept: HeartleafState) -> bool:
    return percept.time_minutes is not None and percept.time_minutes <= MORNING_CUTOFF_MINUTES


__all__ = ["Belief", "MORNING_CUTOFF_MINUTES", "update_belief"]
