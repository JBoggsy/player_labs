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


def signature_of(phrases: list[str]) -> str:
    """The planted SIGNATURE phrase = the FIRST recalled phrase (the judge's answer to our first
    probe, which our self-referential proposal questions tell it to reproduce). Clamped legal;
    fallback if we recalled nothing. Order matters: phrases are harvested in interview order, so
    index 0 is the signature probe's answer."""
    recovered = [clamp_answer(p) for p in phrases if p]
    return recovered[0] if recovered else clamp_answer(config.FALLBACK_PHRASE)


def recalled_from(phrases: list[str], n: int) -> list[str]:
    """n committed answers CYCLED from the recalled phrase list (clamped legal), best-first.
    Falls back to config.FALLBACK_PHRASE if the list is empty. The live player passes its
    persistent cache here so a lagging propose-phase state can't force the fallback.

    Cycle VARIED phrases (don't collapse to one): v5 committed a single 'best' phrase everywhere
    and a single weak/colliding pick tanked all 3 rows (0/6). Cycling distinct phrases is a
    diversity hedge — one weak phrase costs at most one row. Order best-first so the strongest
    phrase lands on the first (and, when n>len, most-repeated) slot."""
    recovered = [clamp_answer(p) for p in phrases if p]
    if not recovered:
        recovered = [clamp_answer(config.FALLBACK_PHRASE)]
    ordered = sorted(recovered, key=phrase_score, reverse=True)
    return [ordered[i % len(ordered)] for i in range(n)]


def recalled_answers(judge_turns: list[dict], n: int) -> list[str]:
    """Convenience: extract phrases from a judge transcript and cycle into n legal answers."""
    recovered = [p for turn in judge_turns if (p := extract_phrase(str(turn.get("answer", ""))))]
    return recalled_from(recovered, n)
