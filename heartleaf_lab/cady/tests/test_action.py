"""Tests for Cady action resolution."""

from __future__ import annotations

from cady.action import ARRIVE_RADIUS, resolve_action
from cady.frame import to_world
from cady.mapdata import HOUSE_RECTS
from cady.types import ActionState, Belief, Intent
from players.player_sdk import Button


def _has(mask: int, button: Button) -> bool:
    return bool(mask & int(button))


def test_gather_at_does_not_press_a_while_on_a_house_footprint() -> None:
    # A press on a house rect ENTERS the house (overloaded A), so gather_at must
    # not press A there — it should only move (toward the approach point).
    hx, hy, hw, hh = HOUSE_RECTS[0]
    on_house_world = to_world((hx + hw // 2, hy + hh // 2))

    command = resolve_action(
        Intent(kind="gather_at", point=(on_house_world[0] + 100, on_house_world[1])),
        Belief(self_xy=on_house_world),
        ActionState(),
    )

    assert not _has(command.held_mask, Button.A)
    assert _has(command.held_mask, Button.RIGHT)  # still steps toward the garden


def test_navigate_to_moves_right_and_down() -> None:
    command = resolve_action(
        Intent(kind="navigate_to", point=(100, 100)),
        Belief(self_xy=(10, 10)),
        ActionState(),
    )

    assert _has(command.held_mask, Button.RIGHT)
    assert _has(command.held_mask, Button.DOWN)
    assert not _has(command.held_mask, Button.LEFT)
    assert not _has(command.held_mask, Button.UP)


def test_navigate_to_releases_inside_arrive_radius() -> None:
    command = resolve_action(
        Intent(kind="navigate_to", point=(10 + ARRIVE_RADIUS, 10 - ARRIVE_RADIUS)),
        Belief(self_xy=(10, 10)),
        ActionState(),
    )

    assert command.held_mask == 0


def test_gather_at_edge_triggers_a_press() -> None:
    belief = Belief(self_xy=(10, 10))
    state = ActionState()
    intent = Intent(kind="gather_at", point=(12, 12))

    assert resolve_action(intent, belief, state).held_mask == int(Button.A)
    assert state.a_held
    assert resolve_action(intent, belief, state).held_mask == 0
    assert not state.a_held
    assert resolve_action(intent, belief, state).held_mask == int(Button.A)
    assert state.a_held


def test_gather_at_moves_toward_point_and_pulses_a() -> None:
    # gather.py only issues gather_at once in harvest range, so gather_at both
    # closes any residual gap (RIGHT) and presses A to collect.
    state = ActionState()

    first = resolve_action(
        Intent(kind="gather_at", point=(100, 10)),
        Belief(self_xy=(10, 10)),
        state,
    )
    assert _has(first.held_mask, Button.RIGHT)
    assert _has(first.held_mask, Button.A)  # fresh press this frame

    # A was held last frame -> release it for one tick (edge press) but keep moving.
    second = resolve_action(
        Intent(kind="gather_at", point=(100, 10)),
        Belief(self_xy=(11, 10)),
        state,
    )
    assert _has(second.held_mask, Button.RIGHT)
    assert not _has(second.held_mask, Button.A)


def test_hold_and_idle_release_buttons() -> None:
    belief = Belief(self_xy=(10, 10))

    assert resolve_action(Intent(kind="hold"), belief, ActionState()).held_mask == 0
    assert resolve_action(Intent(kind="idle"), belief, ActionState()).held_mask == 0


def test_missing_self_holds_still() -> None:
    command = resolve_action(
        Intent(kind="navigate_to", point=(100, 100)),
        Belief(self_xy=None),
        ActionState(),
    )

    assert command.held_mask == 0


def test_predictive_stop_releases_axis_when_coasting_to_target() -> None:
    command = resolve_action(
        Intent(kind="navigate_to", point=(20, 0)),
        Belief(self_xy=(10, 0)),
        ActionState(last_self_xy=(0, 0)),
    )

    assert command.held_mask == 0


def test_enter_house_without_calibrated_entrance_is_no_op() -> None:
    command = resolve_action(
        Intent(kind="enter_house", house_index=0),
        Belief(self_xy=(10, 10)),
        ActionState(),
    )

    assert command.held_mask == 0
