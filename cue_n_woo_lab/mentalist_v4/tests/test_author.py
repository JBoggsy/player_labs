"""Tests for v6 author: style-discriminating challenge questions."""
from __future__ import annotations

import random

from mentalist_v4 import author


def test_pick_questions_distinct():
    qs = author.pick_questions(3, random.Random(0))
    assert len(qs) == 3 == len(set(qs))
    assert all(q in author.QUESTION_BANK for q in qs)


def test_pick_questions_rotates():
    a = author.pick_questions(3, random.Random(1))
    b = author.pick_questions(3, random.Random(2))
    assert a != b  # different seeds -> different selections (not trivially predictable)


def test_bank_avoids_obvious_universal_answers():
    # questions should be open/style-shaping, not one-obvious-answer (dup-conflict trap).
    # heuristic: none are yes/no or "what is your favorite meal"-style universal-answer Qs.
    for q in author.QUESTION_BANK:
        assert q.endswith("?") or q.startswith("Describe") or q.startswith("Name")
        assert "favorite meal" not in q.lower() and "favorite food" not in q.lower()
