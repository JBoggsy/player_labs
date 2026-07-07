"""Resolve Cady intents into SpriteV1 controller masks."""

from __future__ import annotations

from players.player_sdk import Button

from cady.types import ActionState, Belief, Command, Intent

ARRIVE_RADIUS = 4
STOP_FACTOR = 1.3
GATHER_RANGE = 12  # CALIBRATION: interaction radius; TODO(calibrate)
GATHER_RANGE_SQ = GATHER_RANGE * GATHER_RANGE


def resolve_action(intent: Intent, belief: Belief, state: ActionState) -> Command:
    """Execute one symbolic intent into this tick's held-button mask."""

    self_xy = belief.self_xy
    if self_xy is None:
        state.a_held = False
        return Command(held_mask=0)

    velocity = _velocity(state, self_xy)
    mask = _resolve_mask(intent, belief, state, self_xy, velocity)

    state.last_self_xy = self_xy
    state.a_held = bool(mask & int(Button.A))
    return Command(held_mask=int(mask))


def _resolve_mask(
    intent: Intent,
    belief: Belief,
    state: ActionState,
    self_xy: tuple[int, int],
    velocity: tuple[int, int],
) -> int:
    if intent.kind in ("idle", "hold"):
        return 0

    if intent.kind == "navigate_to":
        if intent.point is None:
            return 0
        return _movement_mask(self_xy, intent.point, velocity)

    if intent.kind == "gather_at":
        if intent.point is None:
            return _edge_press_a(state)
        # gather.py only issues gather_at once we're within the game's harvest
        # radius of the garden, so press A every frame to collect. Also keep
        # nudging toward the approach point: it settles a small perception
        # offset that could otherwise leave the foot just out of true range.
        return _movement_mask(self_xy, intent.point, velocity) | _edge_press_a(state)

    if intent.kind == "enter_house":
        if intent.house_index is None:
            return 0
        entrance = belief.house_entrances.get(intent.house_index)
        if entrance is None:
            # CALIBRATION: v1 hosting uses navigate_to(home_anchor)+hold. Direct
            # house entry becomes active once house entrances are calibrated.
            return 0
        return _interact_or_navigate(entrance, self_xy, velocity, state)

    return 0


def _axis_input(delta: int, velocity: int) -> int:
    """Return -1/0/+1 d-pad input for one axis."""

    if abs(delta) <= ARRIVE_RADIUS:
        return 0
    if velocity != 0 and (velocity > 0) == (delta > 0) and abs(delta) <= STOP_FACTOR * abs(velocity):
        return 0
    return 1 if delta > 0 else -1


def _movement_mask(self_xy: tuple[int, int], target_xy: tuple[int, int], velocity: tuple[int, int]) -> int:
    """Held d-pad mask to drive from ``self_xy`` toward ``target_xy``."""

    ix = _axis_input(target_xy[0] - self_xy[0], velocity[0])
    iy = _axis_input(target_xy[1] - self_xy[1], velocity[1])
    mask = 0
    if ix < 0:
        mask |= int(Button.LEFT)
    elif ix > 0:
        mask |= int(Button.RIGHT)
    if iy < 0:
        mask |= int(Button.UP)
    elif iy > 0:
        mask |= int(Button.DOWN)
    return mask


def _interact_or_navigate(
    target_xy: tuple[int, int],
    self_xy: tuple[int, int],
    velocity: tuple[int, int],
    state: ActionState,
) -> int:
    if _dist2(self_xy, target_xy) <= GATHER_RANGE_SQ:
        return _edge_press_a(state)
    return _movement_mask(self_xy, target_xy, velocity)


def _edge_press_a(state: ActionState) -> int:
    """Emit a fresh A press, releasing for one tick if A was already held."""

    return 0 if state.a_held else int(Button.A)


def _velocity(state: ActionState, self_xy: tuple[int, int]) -> tuple[int, int]:
    if state.last_self_xy is None:
        return (0, 0)
    return (self_xy[0] - state.last_self_xy[0], self_xy[1] - state.last_self_xy[1])


def _dist2(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


__all__ = [
    "ARRIVE_RADIUS",
    "GATHER_RANGE",
    "STOP_FACTOR",
    "resolve_action",
]
