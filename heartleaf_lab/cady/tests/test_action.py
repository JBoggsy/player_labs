"""Tests for Cady action resolution."""

from __future__ import annotations

from cady.action import ARRIVE_RADIUS, resolve_action
from cady.types import ActionState, Belief, Intent
from players.player_sdk import Button


def _has(mask: int, button: Button) -> bool:
    return bool(mask & int(button))


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


def test_gather_at_out_of_range_navigates_without_a() -> None:
    command = resolve_action(
        Intent(kind="gather_at", point=(100, 10)),
        Belief(self_xy=(10, 10)),
        ActionState(),
    )

    assert command.held_mask != 0
    assert not _has(command.held_mask, Button.A)
    assert _has(command.held_mask, Button.RIGHT)


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
