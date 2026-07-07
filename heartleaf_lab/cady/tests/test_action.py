"""Tests for Cady action resolution."""

from __future__ import annotations

from cady.action import ARRIVE_RADIUS, resolve_action
from cady.config import A_PRESS_PERIOD
from cady.types import ActionState, Belief, Intent
from players.player_sdk import Button


def _has(mask: int, button: Button) -> bool:
    return bool(mask & int(button))


def test_gather_at_presses_a_on_a_cadence_not_every_frame() -> None:
    # Press-and-verify: A on the first frame, then released for A_PRESS_PERIOD
    # frames (observe the result) before the next press — never a per-frame spam.
    state = ActionState()
    intent = Intent(kind="gather_at", point=(100, 10))

    def press(self_xy: tuple[int, int]) -> bool:
        return _has(resolve_action(intent, Belief(self_xy=self_xy), state).held_mask, Button.A)

    assert press((10, 10))  # frame 0: fresh press
    for i in range(A_PRESS_PERIOD):
        assert not press((11 + i, 10)), f"frame {i + 1} should release/observe, not press"
    assert press((15, 10))  # next press only after the observe window


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
    # At the point (within ARRIVE_RADIUS, so no movement) the mask is a pure A
    # edge: press this frame, then release next frame to observe the result.
    belief = Belief(self_xy=(10, 10))
    state = ActionState()
    intent = Intent(kind="gather_at", point=(12, 12))

    assert resolve_action(intent, belief, state).held_mask == int(Button.A)
    assert resolve_action(intent, belief, state).held_mask == 0


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
