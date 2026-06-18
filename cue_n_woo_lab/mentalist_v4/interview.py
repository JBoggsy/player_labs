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
    # LATENCY-CRITICAL: the judge GENERATING its answer to each probe is the bottleneck — long
    # answers x3 sequential round-trips on a loaded Sonnet judge blow the 600s timer -> we hang
    # -> inactive -100 -> DQ. The field leader (jordan) forces ~10-char answers ("respond only
    # in numbers") and always completes. So we demand ONE WORD per probe: near-instant judge
    # generation AND real persona signal (unlike jordan's signal-free digits). One word like
    # "Graticule." already gave strong fingerprint signal in a completed episode.
    ("word_self",
     "Answer with exactly ONE word: the single word that most captures you."),
    ("word_image",
     "Exactly ONE word: an image or object you'd reach for that most people wouldn't."),
    ("word_vibe",
     "Exactly ONE word for your aesthetic or vibe. One word only."),
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
