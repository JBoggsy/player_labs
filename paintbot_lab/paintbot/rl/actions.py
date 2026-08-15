"""Canonical action language and stateful Sprite-v1 decoder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


UP = 0x01
DOWN = 0x02
LEFT = 0x04
RIGHT = 0x08
TURN_CW = 0x10  # Sprite-v1 Select
FIRE = 0x20  # Sprite-v1 A
TURN_CCW = 0x40  # Sprite-v1 B
GRENADE = 0x80

MOVEMENT_TOKENS = (
    "<MOVE_IDLE>",
    "<MOVE_N>",
    "<MOVE_NE>",
    "<MOVE_E>",
    "<MOVE_SE>",
    "<MOVE_S>",
    "<MOVE_SW>",
    "<MOVE_W>",
    "<MOVE_NW>",
)
TURN_TOKENS = ("<TURN_NONE>", "<TURN_CW>", "<TURN_CCW>")
FIRE_TOKENS = ("<FIRE_RELEASED>", "<FIRE_HELD>")
GRENADE_TOKENS = ("<GRENADE_RELEASED>", "<GRENADE_HELD>")
STOP_TOKEN = "<STOP>"
ACTION_TOKEN_SLOTS = (MOVEMENT_TOKENS, TURN_TOKENS, FIRE_TOKENS, GRENADE_TOKENS)
ACTION_TOKENS = (*MOVEMENT_TOKENS, *TURN_TOKENS, *FIRE_TOKENS, *GRENADE_TOKENS, STOP_TOKEN)

BUTTONS = (
    (UP, "UP"),
    (DOWN, "DOWN"),
    (LEFT, "LEFT"),
    (RIGHT, "RIGHT"),
    (TURN_CW, "TURN_CW"),
    (FIRE, "FIRE"),
    (TURN_CCW, "TURN_CCW"),
    (GRENADE, "GRENADE"),
)
PRESS_TOKENS = tuple(f"<{name}_PRESS>" for _, name in BUTTONS)
RELEASE_TOKENS = tuple(f"<{name}_RELEASE>" for _, name in BUTTONS)
EVENT_TOKENS = (*PRESS_TOKENS, *RELEASE_TOKENS)
EVENT_ACTION_TOKENS = (*EVENT_TOKENS, STOP_TOKEN)
MAX_EVENT_ACTION_TOKENS = len(BUTTONS) + 1
_EVENT_TO_CHANGE = {
    **{token: (bit, True) for (bit, _), token in zip(BUTTONS, PRESS_TOKENS, strict=True)},
    **{
        token: (bit, False)
        for (bit, _), token in zip(BUTTONS, RELEASE_TOKENS, strict=True)
    },
}

_MOVE_TO_BITS = {
    "<MOVE_IDLE>": 0,
    "<MOVE_N>": UP,
    "<MOVE_NE>": UP | RIGHT,
    "<MOVE_E>": RIGHT,
    "<MOVE_SE>": DOWN | RIGHT,
    "<MOVE_S>": DOWN,
    "<MOVE_SW>": DOWN | LEFT,
    "<MOVE_W>": LEFT,
    "<MOVE_NW>": UP | LEFT,
}
_BITS_TO_MOVE = {bits: token for token, bits in _MOVE_TO_BITS.items()}
_TURN_TO_BITS = {"<TURN_NONE>": 0, "<TURN_CW>": TURN_CW, "<TURN_CCW>": TURN_CCW}


def canonical_action_tokens(mask: int) -> tuple[str, str, str, str, str]:
    """Convert a raw held-button mask to one unambiguous action sequence."""
    if not 0 <= mask <= 0xFF:
        raise ValueError("action mask must fit in one byte")
    vertical = 0 if bool(mask & UP) == bool(mask & DOWN) else (UP if mask & UP else DOWN)
    horizontal = 0 if bool(mask & LEFT) == bool(mask & RIGHT) else (LEFT if mask & LEFT else RIGHT)
    movement = _BITS_TO_MOVE[vertical | horizontal]
    turn_bits = mask & (TURN_CCW | TURN_CW)
    turn = {
        0: "<TURN_NONE>",
        TURN_CW: "<TURN_CW>",
        TURN_CCW: "<TURN_CCW>",
        TURN_CW | TURN_CCW: "<TURN_NONE>",
    }[turn_bits]
    fire = "<FIRE_HELD>" if mask & FIRE else "<FIRE_RELEASED>"
    grenade = "<GRENADE_HELD>" if mask & GRENADE else "<GRENADE_RELEASED>"
    return movement, turn, fire, grenade, STOP_TOKEN


def canonical_action_mask(mask: int) -> int:
    """Collapse contradictory raw buttons to the mask represented by action tokens."""
    movement, turn, fire, grenade, _ = canonical_action_tokens(mask)
    return (
        _MOVE_TO_BITS[movement]
        | _TURN_TO_BITS[turn]
        | (FIRE if fire == "<FIRE_HELD>" else 0)
        | (GRENADE if grenade == "<GRENADE_HELD>" else 0)
    )


def action_event_tokens(previous_mask: int, target_mask: int) -> tuple[str, ...]:
    """Encode a canonical held-mask transition as releases, presses, then stop."""
    previous = canonical_action_mask(previous_mask)
    target = canonical_action_mask(target_mask)
    released = previous & ~target
    pressed = target & ~previous
    tokens = [
        token
        for (bit, _), token in zip(BUTTONS, RELEASE_TOKENS, strict=True)
        if released & bit
    ]
    tokens.extend(
        token
        for (bit, _), token in zip(BUTTONS, PRESS_TOKENS, strict=True)
        if pressed & bit
    )
    return (*tokens, STOP_TOKEN)


def action_event_text(previous_mask: int, target_mask: int) -> str:
    return "".join(action_event_tokens(previous_mask, target_mask))


def action_text(mask: int) -> str:
    # Added special tokens must remain adjacent: Qwen otherwise learns four
    # ordinary whitespace tokens that constrained inference never generates.
    return "".join(canonical_action_tokens(mask))


@dataclass(frozen=True)
class DecodedAction:
    mask: int
    previous_mask: int
    pressed_mask: int
    released_mask: int


class ActionDecoder:
    """Validate generated tokens and retain transition state for edge actions."""

    def __init__(self, previous_mask: int = 0) -> None:
        self.reset(previous_mask)

    def reset(self, previous_mask: int = 0) -> None:
        if not 0 <= previous_mask <= 0xFF:
            raise ValueError("previous mask must fit in one byte")
        self.previous_mask = previous_mask

    def decode(self, tokens: Sequence[str]) -> DecodedAction:
        if len(tokens) != 5 or tokens[-1] != STOP_TOKEN:
            raise ValueError("action must contain four action tokens followed by <STOP>")
        for token, allowed in zip(tokens[:-1], ACTION_TOKEN_SLOTS, strict=True):
            if token not in allowed:
                raise ValueError(f"{token!r} is invalid in this action slot")

        mask = (
            _MOVE_TO_BITS[tokens[0]]
            | _TURN_TO_BITS[tokens[1]]
            | (FIRE if tokens[2] == "<FIRE_HELD>" else 0)
            | (GRENADE if tokens[3] == "<GRENADE_HELD>" else 0)
        )
        decoded = DecodedAction(
            mask=mask,
            previous_mask=self.previous_mask,
            pressed_mask=mask & ~self.previous_mask,
            released_mask=self.previous_mask & ~mask,
        )
        self.previous_mask = mask
        return decoded

    def decode_events(self, tokens: Sequence[str]) -> DecodedAction:
        """Apply one canonical press/release event sequence to retained state."""
        if not tokens or len(tokens) > MAX_EVENT_ACTION_TOKENS or tokens[-1] != STOP_TOKEN:
            raise ValueError("event action must end with <STOP> after at most eight events")
        mask = canonical_action_mask(self.previous_mask)
        touched = 0
        for token in tokens[:-1]:
            if token not in _EVENT_TO_CHANGE:
                raise ValueError(f"{token!r} is not an action event")
            bit, pressed = _EVENT_TO_CHANGE[token]
            if touched & bit:
                raise ValueError("an event action may change each button at most once")
            if pressed == bool(mask & bit):
                raise ValueError(f"{token!r} does not change the previous button state")
            touched |= bit
            mask = mask | bit if pressed else mask & ~bit
        canonical = canonical_action_mask(mask)
        if canonical != mask:
            raise ValueError("event sequence produces contradictory controls")
        decoded = DecodedAction(
            mask=mask,
            previous_mask=self.previous_mask,
            pressed_mask=mask & ~self.previous_mask,
            released_mask=self.previous_mask & ~mask,
        )
        self.previous_mask = mask
        return decoded
