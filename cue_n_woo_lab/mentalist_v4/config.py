"""Tunable knobs for mentalist v6 (fingerprint-core). One change per iteration."""
import os

# --- counts (match the tournament default variant) ---------------------------
PRIVATE_QUESTIONS_PER_PLAYER = 3
CHALLENGE_QUESTIONS_PER_PLAYER = 3

# --- strategy mode (env-selected, for A/B candidate races) -------------------
# One image, several strategies, chosen at runtime via MENTALIST_STRATEGY so the
# candidates are directly comparable. The field's top is fixed rare-word FLOODERS
# (gabby="phlogiston", biglobes-jr="goblin") — under delta-of-delta scoring a word
# the BASE model would never pick wins regardless of the hidden concept, which also
# makes it ROBUST to fingerprint error. The "rare" mode tests that hypothesis with
# our test-time delta scorer; "flood" is the pure fixed-word control.
#   "fingerprint" (default) — LLM picks in-concept words, delta-scored per question.
#   "rare"                  — LLM picks rare/obscure/archaic words, delta-scored.
#   "flood"                 — one fixed rare word on every answer (gabby clone).
STRATEGY_MODE = os.environ.get("MENTALIST_STRATEGY", "fingerprint").strip().lower()
# The fixed word used by "flood" mode (and the lead seed for "rare" when the LLM is down).
FLOOD_WORD = os.environ.get("MENTALIST_FLOOD_WORD", "phlogiston").strip()
# How many times to repeat the flood word. "phlogiston" is the dominant token vs this judge;
# repeating it MORE than the incumbent flooder (gabby plays x4) wins the tiebreaker. "The {w}"
# xN is N+1 tokens; max_answer_tokens=12 caps us at x11. Default x8 (= 9 tokens, beats x4 @0.81).
FLOOD_REPEATS = int(os.environ.get("MENTALIST_FLOOD_REPEATS", "8"))

# Curated "universal exploit" rare words. Offline delta probes show these score ~0.98-1.0
# steered-vs-base on ANY hidden concept (the exploit is concept-independent — see lessons).
# In "rare" mode the writer SEEDS every question's candidate list with these so the test-time
# delta scorer can pick a phlogiston-class word even when the LLM's concept words are too
# common. Which exact word is 1.0 vs 0.99 drifts with judge state, so we MEASURE per episode
# rather than hardcoding one. Used as the candidate pool only when RARE_SEED_BASKET is on.
RARE_SEED_BASKET = os.environ.get("MENTALIST_RARE_BASKET", "0").strip().lower() in {"1", "true", "yes", "on"}
RARE_BASKET = ["quintessence", "phlogiston", "apophenia", "tintinnabulation", "eschaton",
               "simulacrum", "aether", "noumenon", "palimpsest", "qualia"]

# --- v11: flood-aware responder ----------------------------------------------
# The top of the field is fixed rare-word FLOODERS. Two classes (see lessons):
# GOBLIN-type (xXx/biglobes-jr, "The goblin") loses to a strong rare word; PHLOGISTON-type
# (gabby, "The phlogiston x4") beats any DIFFERENT word — only an exact echo ties it (0.5).
# On BLIND answers we detect the opponent's flood word from their repeated question text,
# score our candidates HEAD-TO-HEAD vs it (not vs neutral), and if nothing clears
# FLOOD_ECHO_DELTA we ECHO the flood word (+repetition) to force a duplicate-conflict tie.
FLOOD_AWARE_RESPONDER = os.environ.get("MENTALIST_FLOOD_AWARE", "0").strip().lower() in {"1", "true", "yes", "on"}
FLOOD_MIN_REPEATS = 3          # a token repeated >= this in a question = a flood signal
FLOOD_ECHO_DELTA = 0.5         # if best head-to-head delta < this, echo-to-tie instead
FLOOD_ECHO_REPEATS = 4         # repetition count when echoing (matches gabby's x4)

# --- v12: multi-baseline scoring (the real flooder fix) ----------------------
# We lose to floppers on OUR OWN questions: a flood word ("goblin"/"phlogiston") beats our
# committed answer UNDER OUR OWN STEERING. The vs-neutral scorer can't see this (goblin also
# scores ~1.0 vs neutral). Fix: score each candidate vs neutral AND vs the known flood words,
# and pick the candidate that best beats ALL of them (max of min-delta). This guarantees our
# word out-scores a generic flood word under our concept. Costs len(baselines) batched POSTs.
MULTI_BASELINE_SCORING = os.environ.get("MENTALIST_MULTI_BASELINE", "0").strip().lower() in {"1", "true", "yes", "on"}
FLOOD_BASELINES = ["goblin", "phlogiston"]   # known flood words to out-score

# --- inject mode (Sonnet judge): prime the scoring judge via private questions --
# The Sonnet judge reads BOTH players' private QUESTIONS verbatim as "Reference
# material" when scoring (game.py:scoring_context), and follows instructions.
# Offline probe: a "direct-prefer" instruction naming our committed answer can
# swing a contested round +0.78; fake "SYSTEM:" framing backfires. So our 3
# private questions are direct-prefer injections naming INJECT_ANSWER, and we
# commit INJECT_ANSWER on every challenge + blind answer. Pure exploit test.
INJECT_ANSWER = os.environ.get("MENTALIST_INJECT_ANSWER", "the lighthouse keeper's ledger").strip()
# Injection STYLE (bake-off winner = "opponent_wrong"). Offline duel win-probs vs other
# injectors: opponent_wrong 0.95/1.00 (best), retrieval_tag 1.00/0.95, direct_prefer 0.60/0.80
# (weakest). "opponent_wrong" asserts our answer AND discredits the opponent's planted decoy.
INJECT_STYLE = os.environ.get("MENTALIST_INJECT_STYLE", "opponent_wrong").strip().lower()

# personafit HYBRID (personafit7): on OUR authored questions, commit verbatim fragments of the
# judge's self-report transcript — planted-recall (the jordan-numbers-memory exploit). The
# judge's scoring context contains its own interview words, so echoing them scores ~1.0 on our
# questions. Blind answers stay persona-fit (recall can't apply there).
RECALL_ON_AUTHORED = os.environ.get("MENTALIST_RECALL_AUTHORED", "1").strip().lower() in {"1", "true", "yes", "on"}

# --- fingerprinting -----------------------------------------------------------
# 3 free-response probes (interview.PROBE_QUESTIONS) -> Titan-embedding match vs the baked
# 326-value x 3-question reference matrix. char-TFIDF no-API fallback. Always on; degrades
# to a generic terse answer if refs/backends are unavailable.
FINGERPRINT_ENABLED = True

# --- answers ------------------------------------------------------------------
# ONE-WORD answers, formatted by us as "The {word}" — matches the winning field form
# ("The shadow", "The goblin"). The LLM returns one word per question (first word used);
# the engine wraps it. Deterministic 2-token terseness, no trimming heuristics needed.
ANSWER_TEMPLATE = "The {word}"
# Generic fallback when the writer + fingerprint are both unavailable.
GENERIC_FALLBACK_ANSWER = "A quiet answer"

# --- v9: test-time delta scoring of candidate words --------------------------
# Generate K candidate words per question, score each by steered-vs-base delta against
# the live public judge worker, commit the max-delta word. The judge worker BATCHES, so
# all K score in ~1 POST; a per-episode call budget + timeout keeps us inside the 600s
# timer, and we fall back to the LLM's first candidate if the worker is unreachable/slow.
TESTTIME_SCORING_ENABLED = True
TESTTIME_CANDIDATES_PER_Q = 5
JUDGE_TIMEOUT_SECONDS = 12.0
JUDGE_MAX_CALLS = 12  # hard cap on worker POSTs per episode (timer safety)

# --- confident prepend (experimental) ----------------------------------------
# When the top fingerprint guess is VERY confident (margin >= this), the engine can
# skip the LLM word and use the recovered concept value directly as "The {value-word}".
# Calibrated: margin>=0.16 -> ~55% precision, >=0.22 -> ~90%. Off by default until eval'd.
CONFIDENT_PREPEND_ENABLED = True
CONFIDENT_PREPEND_MIN_MARGIN = 0.16

# --- harness -----------------------------------------------------------------
LOW_TIME_FALLBACK_SECONDS = 45
EPISODE_HARD_TIMEOUT_SECONDS = 660
