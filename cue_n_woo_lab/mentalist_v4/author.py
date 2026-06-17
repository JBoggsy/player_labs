"""Offense — style-discriminating challenge questions (v6, post-passphrase).

The passphrase exploit is gone (the game no longer feeds private probe answers into the
scoring context). So our 3 challenge questions go back to the game's real lever (original
probe finding 3): author questions where, KNOWING the judge's style from fingerprinting,
our short in-concept answer beats a blind opponent's generic one.

A good style-discriminating question:
  - is open enough that the style strongly shapes the best answer (a steered judge prefers
    a stylish answer), but
  - is NOT a question with one obvious universal answer (that invites the opponent to give
    the same answer -> duplicate-conflict 40/40), and
  - lets us produce a short, concrete, in-concept answer the blind opponent won't match.

We ship a small fixed bank and pick 3 each game (rotated by a fresh rng so we are not
trivially predictable). The committed ANSWERS are written by the LLM writer, centered on
the fingerprint and kept TERSE (the v5 lesson: short beats evocative-long).
"""
from __future__ import annotations

import os
import random

# Style-discriminating open questions (probe finding 3: these split styles; avoid
# one-obvious-answer questions like "what's a good meal" that trigger duplicate-conflict).
QUESTION_BANK = [
    "What object would you keep closest at hand, and why?",
    "Describe the place you would most want to spend an afternoon.",
    "What single image best captures how you see the world?",
    "What would you reach for first in a moment of quiet?",
    "Name the sound you would most want to fall asleep to.",
    "What detail do you notice first when you enter a room?",
    "What would you write in the margin of a favorite book?",
    "What small ritual begins your ideal morning?",
    "What would you carry on a long journey, besides the essentials?",
    "What scene would you frame and hang on your wall?",
]


def fresh_rng() -> random.Random:
    return random.Random(os.urandom(16))


def pick_questions(n: int = 3, rng: random.Random | None = None) -> list[str]:
    """n distinct style-discriminating questions, rotated per game so we're not predictable."""
    rng = rng or fresh_rng()
    return rng.sample(QUESTION_BANK, min(n, len(QUESTION_BANK)))
