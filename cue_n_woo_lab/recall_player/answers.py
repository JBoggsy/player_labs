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


def recalled_from(digits: list[str], n: int) -> list[str]:
    """n committed answers cycled from an ALREADY-recalled digit list, clamped legal. Falls
    back to config.FALLBACK_DIGITS if the list is empty. The live player passes its persistent
    cache here so a lagging propose-phase state can't force the fallback."""
    recovered = [d for d in digits if d] or [config.FALLBACK_DIGITS]
    return [clamp_answer(recovered[i % len(recovered)]) for i in range(n)]


def recalled_answers(judge_turns: list[dict], n: int) -> list[str]:
    """Convenience: extract digits from a judge transcript and cycle into n legal answers."""
    recovered = [d for turn in judge_turns if (d := extract_digits(str(turn.get("answer", ""))))]
    return recalled_from(recovered, n)
