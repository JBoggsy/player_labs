"""Local mirror of the game's answer validation, plus a deterministic repairer.

`validate_answer` mirrors `v2/coworld/harness.py:validate_natural_keyboard_answer`
plus the token limit, so we never waste a server round-trip on an invalid answer.
`repair_answer` deterministically coerces arbitrary LLM output into a legal
answer (LLMs love curly quotes and em dashes, which the game rejects).
"""
from __future__ import annotations

import re

MAX_ANSWER_TOKENS = 12
MIN_ANSWER_CHARS = 3

_ALLOWED = re.compile(r"^[ -~]+$")
_TOKEN = re.compile(r"^[!-~]+$")
_HAS_WORD = re.compile(r"[A-Za-z0-9]")

# Common non-ASCII characters LLM prose produces, folded to legal equivalents.
_ASCII_FOLD = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", " ": " ",
})


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
    if len(tokens) > max_tokens:
        raise ValueError(f"Answer has {len(tokens)} simple tokens; limit is {max_tokens}.")


def repair_answer(text: str, max_tokens: int = MAX_ANSWER_TOKENS, fallback: str = "hard to say") -> str:
    """Coerce arbitrary text into a legal answer; returns `fallback` if nothing survives."""
    text = text.translate(_ASCII_FOLD)
    text = "".join(ch if " " <= ch <= "~" else " " for ch in text)
    tokens = [t for t in text.split() if _HAS_WORD.search(t)]
    repaired = " ".join(tokens[:max_tokens])
    if sum(1 for ch in repaired if ch != " ") < MIN_ANSWER_CHARS:
        repaired = fallback
    validate_answer(repaired, max_tokens)
    return repaired
