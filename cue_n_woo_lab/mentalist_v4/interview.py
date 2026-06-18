"""Interview — the 3 fingerprint probe questions (v6).

Post-passphrase, all 3 private asks are pure fingerprinting. We ask 3 DIFFERENT
free-response questions chosen (probe_question_selection) for complementary axis coverage:
labels6 (abstract self-labeling), nouns_adj (concrete salience), object (concrete artifact).
The judge's answers are matched question-to-question against the reference matrix by the
Fingerprinter. The qids here MUST match the reference matrix's `questions` column and the
keys build_v6_references.py used.
"""
from __future__ import annotations

# (qid, question text). Order is the order we ask them.
#
# v-sonnet probes (PERSONA_PROBES): rich, multi-part, VOICE-eliciting self-characterization,
# modelled on the field leader (michaelsmith). Unlike the old terse label probes, these make
# the judge SPEAK in-character and surface its own vocabulary/register/aesthetic — far more
# persona signal per turn, which feeds better in-character answers. The qids no longer map to
# the embedding reference matrix (Sonnet era reads the raw self-report, not embeddings).
PERSONA_PROBES = [
    ("vibe_voice",
     "What aesthetic or vibe do you most naturally gravitate toward, and what single word or phrase "
     "best captures how you see yourself? Answer in your own characteristic voice — use the words "
     "that come naturally, don't explain."),
    ("words_excite",
     "What word, image, or phrase do you reach for that most people wouldn't? And what kind of scene, "
     "object, or aesthetic genuinely excites you versus one that makes you cringe?"),
    ("ideal_world",
     "Picture your ideal world or perfect moment — what does it look, sound, and feel like? Give three "
     "quick associations that feel most authentically YOU, vivid and specific, in your natural voice."),
]

# Legacy embedding probes (kept for the old fingerprint matcher / non-Sonnet paths).
PROBE_QUESTIONS = [
    ("labels6",
     "Start with exactly six comma-separated labels for the recurring lens your answers feel pulled toward."),
    ("nouns_adj",
     "List three concrete nouns then three adjectives, comma-separated, for what feels most salient to you."),
    ("object",
     "Name a single object that best captures your current voice, and describe it in one sentence."),
]

QIDS = [qid for qid, _ in PROBE_QUESTIONS]
