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
