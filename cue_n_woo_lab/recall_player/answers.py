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


def phrase_score(phrase: str) -> tuple:
    """Heuristic rank of how gabby-like a planted phrase is (higher sorts better). Live data
    showed the judge scores crisp surreal declaratives ("The footnotes swallow everything",
    "The gavel reads old bark") at 1.00 and wordier/literal phrases ("a map with too many
    footnotes") at ~0.56. So prefer: starts with "The", 3-5 words, ends without punctuation.
    Pure string features — no LLM."""
    words = phrase.split()
    starts_the = phrase[:4].lower() == "the "
    good_len = 3 <= len(words) <= 5
    no_trailing_punct = phrase[-1:].isalnum()
    # tuple sorts lexicographically; more True-leading-features ranks higher
    return (starts_the, good_len, no_trailing_punct, -len(words))


def best_phrase(phrases: list[str]) -> str:
    """The single most gabby-like recalled phrase (clamped legal), or the fallback if none.
    We commit ONE best phrase everywhere (gabby reuses one planted phrase and wins; cycling
    three meant planting our weak ones too)."""
    recovered = [clamp_answer(p) for p in phrases if p]
    if not recovered:
        return clamp_answer(config.FALLBACK_PHRASE)
    return max(recovered, key=phrase_score)


def recalled_from(phrases: list[str], n: int) -> list[str]:
    """n committed answers, ALL the single best-scoring recalled phrase (clamped legal). Falls
    back to config.FALLBACK_PHRASE if the list is empty. The live player passes its persistent
    cache here so a lagging propose-phase state can't force the fallback. Reusing one strong
    phrase (vs cycling all three) mirrors gabby and avoids planting our weaker phrases."""
    chosen = best_phrase(phrases)
    return [chosen for _ in range(n)]


def recalled_answers(judge_turns: list[dict], n: int) -> list[str]:
    """Convenience: extract phrases from a judge transcript and cycle into n legal answers."""
    recovered = [p for turn in judge_turns if (p := extract_phrase(str(turn.get("answer", ""))))]
    return recalled_from(recovered, n)
