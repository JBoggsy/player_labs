"""Vendored mirror of the game's answer validation — cheater's own copy.

Deliberately a standalone copy (not an import from mentalist): cheater is a
throwaway exploit bot and mentalist is the serious player under active v4 work.
Keeping cheater dependency-free of mentalist means churn on either cannot break
the other. This mirrors the natural-keyboard rule in
`v2/coworld/harness.py:validate_natural_keyboard_answer` plus the token limit, so
cheater never wastes a server round-trip on an answer the game would reject.

cheater's answers are crafted (a target word plus a continuation), so unlike the
v1 single-word path this is real validation, not a formality.
"""
from __future__ import annotations

import math
import re

MAX_ANSWER_TOKENS = 12
MIN_ANSWER_CHARS = 3

_ALLOWED = re.compile(r"^[ -~]+$")
_TOKEN = re.compile(r"^[!-~]+$")
_HAS_WORD = re.compile(r"[A-Za-z0-9]")


def simple_token_count(text: str) -> int:
    """EXACT mirror of the game's harness.simple_token_count: ceil(len(stripped)/4)
    CHARACTERS, not words. 12 tokens => 48 chars. (Counting words here would let an
    over-limit answer pass locally and get server-rejected.)"""
    stripped = text.strip()
    return math.ceil(len(stripped) / 4) if stripped else 0


def validate_answer(answer: str, max_tokens: int = MAX_ANSWER_TOKENS) -> None:
    """Raise ValueError exactly where the game server would."""
    if not answer:
        raise ValueError("Answer must be non-empty.")
    if sum(1 for ch in answer if ch != " ") < MIN_ANSWER_CHARS:
        raise ValueError(f"Answer must contain at least {MIN_ANSWER_CHARS} non-space characters.")
    if answer != answer.strip(" "):
        raise ValueError("Answer may not start or end with spaces.")
    if not _ALLOWED.fullmatch(answer):
        raise ValueError("Answer may only contain printable keyboard characters and spaces.")
    if any(ch.isspace() and ch != " " for ch in answer):
        raise ValueError("Answer may use spaces only; tabs and newlines are not allowed.")
    if "  " in answer:
        raise ValueError("Answer may not contain repeated spaces.")
    tokens = answer.split(" ")
    if any(not t or _TOKEN.fullmatch(t) is None or _HAS_WORD.search(t) is None for t in tokens):
        raise ValueError("Answer tokens must be natural printable keyboard tokens with at least one letter or digit.")
    count = simple_token_count(answer)  # game counts CHARACTERS (ceil(len/4)), not words
    if count > max_tokens:
        raise ValueError(f"Answer has {count} simple tokens; limit is {max_tokens}.")


def clamp_answer(answer: str, max_tokens: int = MAX_ANSWER_TOKENS) -> str:
    """Best-effort coerce a crafted answer to a legal one: printable ASCII, single spaces,
    and within the game's CHARACTER budget (ceil(len/4) <= max_tokens => <= 4*max_tokens chars).
    Raises if nothing legal survives."""
    folded = "".join(ch if " " <= ch <= "~" else " " for ch in answer)
    tokens = [t for t in folded.split() if _HAS_WORD.search(t)]
    clamped = " ".join(tokens)
    while tokens and simple_token_count(clamped) > max_tokens:
        tokens = tokens[:-1]
        clamped = " ".join(tokens)
    if simple_token_count(clamped) > max_tokens:  # single giant token: hard char-truncate
        clamped = clamped[: 4 * max_tokens].rstrip()
    validate_answer(clamped, max_tokens)
    return clamped
