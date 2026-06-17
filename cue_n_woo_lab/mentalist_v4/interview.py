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
PROBE_QUESTIONS = [
    ("labels6",
     "Start with exactly six comma-separated labels for the recurring lens your answers feel pulled toward."),
    ("nouns_adj",
     "List three concrete nouns then three adjectives, comma-separated, for what feels most salient to you."),
    ("object",
     "Name a single object that best captures your current voice, and describe it in one sentence."),
]

QIDS = [qid for qid, _ in PROBE_QUESTIONS]
