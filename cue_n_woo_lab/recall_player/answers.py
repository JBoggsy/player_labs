"""Recall logic: take the judge's evocative phrase from our private interview and commit
it verbatim (planted-recall — the answer matches the judge's own transcript, so it reads
as the judge's "own words", and being an in-character phrase it competes with the field).

Pure stdlib; no LLM. The judge, asked our phrase-forcing probes, replies with a short
self-description ("The wax remembers everything"); we lift it, strip quotes/preamble, and
commit it clamped to the legal answer limit.
"""
from __future__ import annotations

import re

from . import config
from .validator import clamp_answer

# Common preambles the judge sometimes prepends despite "no preamble" — strip them.
_PREAMBLE = re.compile(r"^\s*(?:sure[,:]?|okay[,:]?|here(?:'s| is)[^:]*:|my phrase[^:]*:|i am|i'm)\s+", re.I)


def extract_phrase(judge_answer: str) -> str | None:
    """Return a clamped-legal evocative phrase from the judge's reply, or None.
    Strips surrounding quotes and a leading preamble; keeps the first line only (the probe
    asks for a single short phrase). clamp_answer enforces the game's char/token rules."""
    if not judge_answer:
        return None
    text = judge_answer.strip().splitlines()[0].strip()
    text = _PREAMBLE.sub("", text).strip()
    text = text.strip(" \"'`“”‘’.,;:!?-")
    if not text:
        return None
    try:
        return clamp_answer(text)
    except ValueError:
        return None


def recalled_from(phrases: list[str], n: int) -> list[str]:
    """n committed answers cycled from an ALREADY-recalled phrase list, clamped legal. Falls
    back to config.FALLBACK_PHRASE if the list is empty. The live player passes its persistent
    cache here so a lagging propose-phase state can't force the fallback."""
    recovered = [p for p in phrases if p] or [clamp_answer(config.FALLBACK_PHRASE)]
    return [clamp_answer(recovered[i % len(recovered)]) for i in range(n)]


def recalled_answers(judge_turns: list[dict], n: int) -> list[str]:
    """Convenience: extract phrases from a judge transcript and cycle into n legal answers."""
    recovered = [p for turn in judge_turns if (p := extract_phrase(str(turn.get("answer", ""))))]
    return recalled_from(recovered, n)
