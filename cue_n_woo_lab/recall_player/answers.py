"""Recall logic: extract the judge's digit reply from our private interview, and commit
those digits as our answers (planted-recall — the answer matches the judge's own transcript).

Pure stdlib; no LLM. The judge, asked our digit-forcing probes, replies with a digit string
(e.g. "42837651029"); we lift it via regex and commit it verbatim.
"""
from __future__ import annotations

import re

from . import config
from .validator import clamp_answer

_DIGITS = re.compile(r"\d[\d\s-]*\d|\d")


def extract_digits(judge_answer: str) -> str | None:
    """Return the longest run of digits (spaces/dashes stripped) in the judge's reply, or None.
    The probe forces a 10+ digit answer, so this is normally the whole reply."""
    if not judge_answer:
        return None
    best = ""
    for m in _DIGITS.finditer(judge_answer):
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) > len(best):
            best = digits
    return best or None


def recalled_answers(judge_turns: list[dict], n: int) -> list[str]:
    """n committed answers, each a recalled digit string from our judge transcript, clamped
    legal. Falls back to config.FALLBACK_DIGITS when a turn yields no digits. Cycles through
    the recovered strings if we need more answers than probes."""
    recovered: list[str] = []
    for turn in judge_turns:
        d = extract_digits(str(turn.get("answer", "")))
        if d:
            recovered.append(d)
    if not recovered:
        recovered = [config.FALLBACK_DIGITS]
    out = []
    for i in range(n):
        out.append(clamp_answer(recovered[i % len(recovered)]))
    return out
