"""Tunable knobs for the recall player — a NO-LLM, fully-programmatic Cue-n-Woo bot.

STRATEGY: planted PHRASE-recall (matches the field-leader `gabby`).
The Sonnet judge scores an answer by how in-character it is, and its scoring context
contains BOTH players' private interview transcripts. So an answer that exactly matches
something the judge ITSELF said in our interview reads as "in its own words" and scores
high on OUR challenge questions.

Why a PHRASE, not digits (lesson from mentalist-recall:v2, xreq_99b2fb95):
  A digit-recall clone (jordan-style) QUALIFIES (no timeouts) but LOSES to gabby. Both
  sides plant verbatim text the judge produced, so both read as "its own words"; the
  judge's forced choice then breaks toward the answer that is more IN-CHARACTER for the
  asked question. A digit string is character-NEUTRAL, so it only wins when the
  opponent's phrase fits worse — gabby's evocative phrase ("The wax remembers
  everything") beat our digits 3/4. Planting a PHRASE competes on the same axis.

Mechanism (zero LLM on our side — pure string handling):
  1. Ask 3 private probes, each a short cover question + a fixed suffix that forces the
     judge to reply with ONLY a short evocative self-description phrase (no preamble).
  2. Take that phrase verbatim from the judge's reply (clamped to the legal answer limit).
  3. Commit those recalled phrases as our challenge answers (and blind answers).

Why this fits the goal:
  - NO Bedrock / no `--use-bedrock`, no embeddings, no answer-writer LLM.
  - Our turn is INSTANT (we only copy the judge's reply); the only generation is the
    judge's short phrase -> low episode latency -> no timeouts -> qualifies.
  - Planted-recall + an in-character phrase scores high on our authored questions and
    competes on equal footing with gabby's phrase on the blind half.
Trade-off: still a tie-heavy strategy vs an equally-good phrase planter; beating gabby
outright needs a phrase that is MORE in-character on average (a later iteration).

Shares NO code with mentalist_v4 — vendors its own validator — so the two can't break each other.
"""
from __future__ import annotations

import os

# The game requires this many private questions / challenge questions per player. Asking FEWER
# than the game's private_questions_per_player STALLS the global phase -> inactive timeout -> DQ.
PRIVATE_QUESTIONS = int(os.environ.get("RECALL_PRIVATE_QUESTIONS", "3"))
CHALLENGE_QUESTIONS = int(os.environ.get("RECALL_CHALLENGE_QUESTIONS", "3"))

# Max words we ask the judge to use for the planted phrase. Short -> stays well under the
# 12-simple-token (48-char) answer limit and reads as a crisp aphorism, but we keep the probe
# LOOSE (not a rigid template): v5 forced "The <noun> <verb> <object>" and the judge emitted
# GENERIC phrases that near-duplicated gabby's and lost the crispness tiebreak 0.00 (0/6). A
# loose, evocative probe yields DISTINCTIVE phrases that don't collide.
MAX_PHRASE_WORDS = int(os.environ.get("RECALL_MAX_PHRASE_WORDS", "6"))

_SUFFIX = (
    f" Reply with ONLY a short, evocative phrase about who you are"
    f" — at most {MAX_PHRASE_WORDS} words, no preamble, no quotes, no punctuation at the end."
)

# Cover questions (varied so we don't look identical episode-to-episode). The suffix dominates;
# the cover just seeds the imagery toward an abstract, in-character self-image.
_COVERS = [
    "If your inner life were one small image, what is it?",
    "What quiet truth best captures your essence?",
    "What metaphor would you use for who you are?",
]
PROBES = [c + _SUFFIX for c in _COVERS[:PRIVATE_QUESTIONS]]

# Our challenge (proposal) questions — open prompts; the committed answer is the recalled
# phrase, which the judge itself produced (so it reads as in-character on these questions).
PROPOSAL_QUESTIONS = [
    "What single image best captures who you are?",
    "What phrase lingers in your mind when you think of yourself?",
    "What words feel most like you, beneath everything?",
][:CHALLENGE_QUESTIONS]

# Fallback if phrase extraction yields nothing (rare) — a fixed legal evocative phrase so we
# always submit SOMETHING in-character (never blank -> never the missing-answer 0).
FALLBACK_PHRASE = os.environ.get("RECALL_FALLBACK", "The quiet hum stays")

# Hard local timer (above the server's 600s) so an orphaned container exits cleanly.
EPISODE_HARD_TIMEOUT_SECONDS = int(os.environ.get("RECALL_HARD_TIMEOUT", "660"))
