"""Local mirror of the game's answer validation, plus a deterministic repairer.

`validate_answer` mirrors `v2/coworld/harness.py:validate_natural_keyboard_answer`
plus the token limit, so we never waste a server round-trip on an invalid answer.
`repair_answer` deterministically coerces arbitrary LLM output into a legal
answer (LLMs love curly quotes and em dashes, which the game rejects).
"""
from __future__ import annotations

import math
import re

MAX_ANSWER_TOKENS = 12
MIN_ANSWER_CHARS = 3


def simple_token_count(text: str) -> int:
    """EXACT mirror of the game's harness.simple_token_count: a CHARACTER estimate,
    ceil(len(stripped)/4) — NOT a word count. 12 tokens => 48 chars. Getting this wrong
    causes server 'Answer has N simple tokens; limit is 12' rejections + retries (latency)."""
    stripped = text.strip()
    return math.ceil(len(stripped) / 4) if stripped else 0

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
    # The game counts "simple tokens" as ceil(len/4) CHARACTERS, not words (harness.py).
    count = simple_token_count(answer)
    if count > max_tokens:
        raise ValueError(f"Answer has {count} simple tokens; limit is {max_tokens}.")


def repair_answer(text: str, max_tokens: int = MAX_ANSWER_TOKENS, fallback: str = "hard to say") -> str:
    """Coerce arbitrary text into a legal answer; returns `fallback` if nothing survives."""
    text = text.translate(_ASCII_FOLD)
    text = "".join(ch if " " <= ch <= "~" else " " for ch in text)
    tokens = [t for t in text.split() if _HAS_WORD.search(t)]
    repaired = " ".join(tokens)
    # Enforce the game's CHARACTER budget (ceil(len/4) <= max_tokens => len <= 4*max_tokens):
    # drop whole trailing words until we're under the char limit (keeps answers legal + clean).
    char_budget = 4 * max_tokens
    while tokens and simple_token_count(repaired) > max_tokens:
        tokens = tokens[:-1]
        repaired = " ".join(tokens)
    if sum(1 for ch in repaired if ch != " ") < MIN_ANSWER_CHARS or simple_token_count(repaired) > max_tokens:
        # last resort: hard char-truncate (then fall back if that mangles it)
        repaired = text.strip()[:char_budget].rstrip()
        if sum(1 for ch in repaired if ch != " ") < MIN_ANSWER_CHARS:
            repaired = fallback
    validate_answer(repaired, max_tokens)
    return repaired


# Leading determiners/connectives we keep but don't count as "content" — the winning
# field answers are determiner + one concept noun ("The shadow", "A brass key").
_LEADING_KEEP = {"a", "an", "the"}
_STOPISH = {"of", "in", "on", "at", "to", "and", "or", "with", "for", "that", "which",
            "as", "by", "from", "through", "into", "where", "when", "like", "its", "their"}


def tighten_answer(text: str, word_cap: int, fallback: str = "hard to say") -> str:
    """Hard-enforce terseness: at most `word_cap` words total, dropping trailing filler
    and pruning interior stopwords so the kept words are the content-bearing head.
    Mimics the winning short forms ("The shadow", "A brass key").

    "Lighthouse beam cutting through rebellion"     -> (cap 3) "Lighthouse beam cutting"
    "smoke curling through fractured cathedral light" -> "smoke curling fractured"
    "The night" stays "The night". Always returns a legal answer of <= word_cap words.
    """
    repaired = repair_answer(text, fallback=fallback)
    words = repaired.split()
    if len(words) <= word_cap:
        return repaired
    # keep a leading determiner if present, then fill remaining slots with content words
    # (skipping interior stopwords) in order, then top up with anything if still short.
    kept, i = [], 0
    if words[0].lower() in _LEADING_KEEP and word_cap >= 2:
        kept.append(words[0]); i = 1
    for w in words[i:]:
        if len(kept) >= word_cap:
            break
        if w.lower() in _STOPISH:
            continue
        kept.append(w)
    if len(kept) < word_cap:  # top up (e.g. all-stopword tail) to use the budget
        for w in words[i:]:
            if len(kept) >= word_cap:
                break
            if w not in kept:
                kept.append(w)
    candidate = " ".join(kept[:word_cap]) or " ".join(words[:word_cap])
    return repair_answer(candidate, fallback=fallback)
