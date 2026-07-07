"""Tests for Cady belief folding."""

from __future__ import annotations

from cady.belief import Belief, update_belief
from cady.types import Garden, HeartleafState


def _state(
    *,
    ready: bool = True,
    self_xy: tuple[int, int] | None = (10, 20),
    time_minutes: int | None = 0,
    gardens: tuple[Garden, ...] = (),
    inventory_count: int = 0,
    map_context: str = "unknown",
) -> HeartleafState:
    return HeartleafState(
        ready=ready,
        self_xy=self_xy,
        time_minutes=time_minutes,
        gardens=gardens,
        gnomes=(),
        own_house_index=None,
        houses=(),
        inventory_count=inventory_count,
        map_context=map_context,
    )


def test_first_ready_morning_frame_sets_home_anchor() -> None:
    belief = Belief()

    update_belief(belief, _state(self_xy=(12, 34), time_minutes=0))

    assert belief.self_xy == (12, 34)
    assert belief.home_anchor == (12, 34)
    assert belief.home_anchor_is_morning


def test_later_ready_frame_does_not_move_morning_home_anchor() -> None:
    belief = Belief()
    update_belief(belief, _state(self_xy=(12, 34), time_minutes=0))

    update_belief(belief, _state(self_xy=(90, 91), time_minutes=300))

    assert belief.home_anchor == (12, 34)
    assert belief.home_anchor_is_morning


def test_fallback_home_anchor_upgrades_to_first_morning_anchor() -> None:
    belief = Belief()
    update_belief(belief, _state(self_xy=(90, 91), time_minutes=None))

    update_belief(belief, _state(self_xy=(12, 34), time_minutes=10))

    assert belief.home_anchor == (12, 34)
    assert belief.home_anchor_is_morning


def test_garden_positions_accumulate_and_scalar_fields_update() -> None:
    belief = Belief()
    first_garden = Garden(object_id=4000, pos=(1, 2), has_food=True)
    second_garden = Garden(object_id=4001, pos=(3, 4), has_food=True)
    update_belief(
        belief,
        _state(
            time_minutes=10,
            gardens=(first_garden,),
            inventory_count=1,
        ),
    )
    assert belief.food_gardens == (first_garden,)

    update_belief(
        belief,
        _state(
            time_minutes=20,
            gardens=(second_garden,),
            inventory_count=2,
        ),
    )

    assert belief.food_gardens == (second_garden,)
    assert belief.garden_positions == {4000: (1, 2), 4001: (3, 4)}
    assert belief.last_time_minutes == 20
    assert belief.inventory_count == 2


def test_not_ready_frame_is_no_op() -> None:
    belief = Belief()

    update_belief(
        belief,
        _state(
            ready=False,
            self_xy=None,
            time_minutes=10,
            gardens=(Garden(object_id=4000, pos=(1, 2), has_food=True),),
            inventory_count=3,
        ),
    )

    assert belief.home_anchor is None
    assert belief.garden_positions == {}
    assert belief.last_time_minutes is None
    assert belief.inventory_count == 0


def test_not_ready_frame_clears_current_food_gardens() -> None:
    belief = Belief(food_gardens=(Garden(object_id=4000, pos=(1, 2), has_food=True),))

    update_belief(belief, _state(ready=False, self_xy=None))

    assert belief.food_gardens == ()


def test_unknown_map_context_preserves_last_known_context() -> None:
    belief = Belief(map_context="home")

    update_belief(belief, _state(map_context="unknown"))

    assert belief.map_context == "home"


def test_map_context_change_clears_navigation_cache() -> None:
    belief = Belief(
        map_context="home",
        nav_goal=(10, 20),
        nav_path=[(1, 2), (10, 20)],
        nav_cursor=1,
    )

    update_belief(belief, _state(map_context="main"))

    assert belief.map_context == "main"
    assert belief.nav_goal is None
    assert belief.nav_path is None
    assert belief.nav_cursor == 0
