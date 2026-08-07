"""Contract tests for wowborg's thin wrapper around the upstream `/player` API."""

from __future__ import annotations

from environment.contract.policy import (
    ActionState,
    Action,
    EnvironmentContext,
    Observation,
    WorldPoint,
)

from wowborg.environment import GymSession, hosted_endpoints


def _frame(frame_id: int, *, x: float = 1.0, action_state=None) -> Observation:
    return Observation.model_construct(
        episode_id="00000000-0000-0000-0000-000000000001",
        frame_id=frame_id,
        environment=EnvironmentContext.model_construct(terminal=False),
        tick=frame_id,
        location=WorldPoint(map_id=1, x=x, y=2.0, z=3.0),
        health=100,
        max_health=100,
        in_combat=False,
        is_dead=False,
        is_ghost=False,
        known_spells=[],
        active_area_trigger_ids=[],
        action_state=action_state,
    )


class FakeEnv:
    def __init__(self) -> None:
        self.actions = []
        self.closed = False

    def step(self, action):
        self.actions.append(action)
        return (
            _frame(2, x=10.0),
            0.0,
            False,
            False,
            {"action_status": "accepted", "action_detail": ""},
        )

    def close(self) -> None:
        self.closed = True


def test_hosted_endpoints_leave_environment_auth_to_pinned_client() -> None:
    env_url, navigation_url, slot, token = hosted_endpoints(
        "wss://game.example/player?slot=7&token=secret"
    )
    assert env_url == "wss://game.example/player?slot=7&token=secret"
    assert navigation_url == (
        "https://game.example/player/navigation?slot=7&token=secret"
    )
    assert slot == 7
    assert token == "secret"


def test_hosted_endpoints_require_slot_and_token() -> None:
    try:
        hosted_endpoints("ws://game.example/player")
    except ValueError as exc:
        assert "slot and token" in str(exc)
    else:
        raise AssertionError("missing hosted authentication was accepted")


def test_move_uses_upstream_action_and_advances_to_next_frame() -> None:
    env = FakeEnv()
    session = GymSession(env, _frame(1), {})

    request_id = session.select_move_to(session.frame, 10.0, 20.0, 30.0, 1)

    assert request_id == "frame-1"
    assert session.frame.frame_id == 2
    assert len(env.actions) == 1
    action = env.actions[0]
    assert isinstance(action, Action)
    assert action.kind == "move_to"
    assert action.destination == WorldPoint(map_id=1, x=10.0, y=20.0, z=30.0)
    outcome = session.wait_for_settlement(1)
    assert outcome.success is True
    assert outcome.settlement_kind is None


def test_matching_action_state_marks_the_action_settled() -> None:
    class SettledEnv(FakeEnv):
        def step(self, action):
            self.actions.append(action)
            state = ActionState(
                action_id=1,
                submitted_frame_id=1,
                action=action,
                status="succeeded",
                completion_frame_id=2,
                detail="advanced one observation horizon",
            )
            return (
                _frame(2, x=10.0, action_state=state),
                0.0,
                False,
                False,
                {"action_status": "accepted", "action_detail": ""},
            )

    session = GymSession(SettledEnv(), _frame(1), {})
    session.select_move_to(session.frame, 10.0, 20.0, 30.0, 1)

    outcome = session.wait_for_settlement(1)
    assert outcome.success is True
    assert outcome.settlement_kind == "succeeded"


def test_stale_frame_does_not_submit_an_action() -> None:
    env = FakeEnv()
    session = GymSession(env, _frame(2), {})

    assert session.select_wait(_frame(1)) is None
    assert env.actions == []
