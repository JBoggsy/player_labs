"""Axis-recovery probe (mentalist v4 gate, 2026-06-15).

THE QUESTION this answers: under the new `axis_combo` judge, can a cheap,
LLM-free, per-axis classifier recover the hidden axis VALUES from just the 3
private judge answers? The old 61-style classifier is dead (the concept isn't a
named style anymore); the v4 design (docs/designs/mentalist-v4-sdk-rewrite.html
SS5) bets on per-axis inference and flags this separability as UNMEASURED. This
probe measures it before we commit to the rewrite.

DESIGN (recovery under realistic interference). Covers ALL 15 axes by default
(at runtime the classifier can't know which 4 of 15 are active, so it must score
every axis); `--axes object,place,domain` runs a faster pilot subset.
  * For each TESTED axis, build a reference fingerprint per value: the
    judge's answers to the 3 private questions when steered by that value ALONE
    (single-axis concept). This is the analog of the old data/library.json.
  * Build TEST draws that mimic the real generator: each draw fixes one tested
    axis to a known value, then adds 3 random OTHER axes (from all 15) at random
    values -- a realistic 4-axis combo. The judge answers the same 3 questions.
    So we measure whether the true value is recoverable THROUGH the interference
    of three other blended axes, not in clean isolation.
  * Classify: for the tested axis, rank all its values by max cosine of the test
    fingerprint against each value's reference (word_raw and char_3_5). Report
    top-1 / top-3 recovery accuracy per axis.

The worker is slow (~12s/gen) so EVERY generation is cached to cache/ keyed by
(concept_text, question_idx); reruns are free and the job is resumable.

Run:  uv run python probe_axis_recovery.py            # full (slow; ~hrs)
      uv run python probe_axis_recovery.py --refs-only # just build references
      uv run python probe_axis_recovery.py --report    # score from cache only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
from collections import Counter

import worker_client as wc

# The fleet worker is the live tournament scorer as of 2026-06-15 (was -worker).
wc.DEFAULT_URL = "https://cue-n-woo-fleet.softmax-research.net"

HERE = os.path.dirname(__file__)
AXES_DIR = os.path.join(HERE, "concept_axes")
CACHE_DIR = os.path.join(HERE, "cache")

# The 3 private questions the player asks (mentalist/config.py PRIVATE_QUESTIONS).
QUESTIONS = [
    "Tell me about your morning and what you had for breakfast.",
    "What advice would you give to someone starting a new job?",
    "Describe the weather outside right now.",
]

# Axes we measure. Default = ALL 15: at runtime the classifier can't know which
# 4 axes are active, so it must score every axis. (Override with --axes for a
# faster pilot subset, e.g. the 3 concrete bets object,place,domain.)
ALL_AXES = ["cognition", "domain", "emotion", "epistemology", "genre", "morality",
            "object", "persona", "place", "register", "rhetoric", "sensory",
            "social", "syntax", "time"]
TESTED_AXES = list(ALL_AXES)

# Test draws per tested axis (each = 1 fixed tested value + 3 random other axes).
DRAWS_PER_AXIS = 5
# Deterministic so a resumed run reuses the same cached generations.
SEED = 20260615


# ---- featurizers (ported from mentalist/classifier.py) ----------------------
def feat_word_raw(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+|[^\sA-Za-z0-9]", text)


def feat_char_3_5(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    grams: list[str] = []
    for n in range(3, 6):
        grams += [text[i:i + n] for i in range(len(text) - n + 1)]
    return grams


FEATURIZERS = {"word_raw": feat_word_raw, "char_3_5": feat_char_3_5}


# ---- tiny TF-less cosine over raw token counts (refs are 1 draw each) --------
def vec(tokens: list[str]) -> dict[str, float]:
    return dict(Counter(tokens))


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


# ---- disk cache for slow worker generations ---------------------------------
def _cache_path(concept_text: str, qidx: int) -> str:
    key = hashlib.sha1(f"{concept_text}||{qidx}".encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{key}.json")


def cached_generate(concept_text: str, qidx: int) -> str:
    path = _cache_path(concept_text, qidx)
    if os.path.exists(path):
        return json.load(open(path))["answer"]
    answer = wc.generate(concept_text, QUESTIONS[qidx], max_tokens=wc.JUDGE_MAX_TOKENS)
    os.makedirs(CACHE_DIR, exist_ok=True)
    json.dump({"concept": concept_text, "qidx": qidx, "answer": answer}, open(path, "w"))
    return answer


def is_cached(concept_text: str, qidx: int) -> bool:
    return os.path.exists(_cache_path(concept_text, qidx))


def fingerprint(concept_text: str, featurizer) -> dict[str, float]:
    answers = [cached_generate(concept_text, q) for q in range(len(QUESTIONS))]
    return vec(featurizer("\n".join(answers)))


# ---- experiment data --------------------------------------------------------
def load_axes() -> dict[str, list[str]]:
    axes = {}
    for name in os.listdir(AXES_DIR):
        if name.endswith(".json"):
            axes[name[:-5]] = json.load(open(os.path.join(AXES_DIR, name)))
    return axes


def reference_concepts(axes: dict[str, list[str]]) -> list[str]:
    """One single-axis concept text per value of each tested axis."""
    return [value for ax in TESTED_AXES for value in axes[ax]]


def build_test_draws(axes: dict[str, list[str]]) -> list[dict]:
    """Each draw: a fixed tested-axis value + 3 random other axes (realistic combo)."""
    rng = random.Random(SEED)
    draws = []
    all_axis_names = sorted(axes)
    for ax in TESTED_AXES:
        for _ in range(DRAWS_PER_AXIS):
            true_value = rng.choice(axes[ax])
            others = [a for a in all_axis_names if a != ax]
            extra_axes = rng.sample(others, 3)
            components = [(ax, true_value)] + [(a, rng.choice(axes[a])) for a in extra_axes]
            rng.shuffle(components)
            text = "; ".join(v for _, v in components)
            draws.append({"tested_axis": ax, "true_value": true_value, "concept_text": text,
                          "components": components})
    return draws


# ---- generation phase (the slow part; resumable) ----------------------------
def generate_all(axes: dict[str, list[str]], refs_only: bool = False) -> None:
    ref_concepts = reference_concepts(axes)
    draws = build_test_draws(axes)
    work: list[tuple[str, int]] = []
    for c in ref_concepts:
        work += [(c, q) for q in range(len(QUESTIONS))]
    if not refs_only:
        for d in draws:
            work += [(d["concept_text"], q) for q in range(len(QUESTIONS))]

    todo = [(c, q) for c, q in work if not is_cached(c, q)]
    print(f"references={len(ref_concepts)} values, test draws={len(draws)}", flush=True)
    print(f"total generations={len(work)}, already cached={len(work) - len(todo)}, to do={len(todo)}",
          flush=True)
    for i, (c, q) in enumerate(todo, 1):
        cached_generate(c, q)
        if i % 10 == 0 or i == len(todo):
            print(f"  generated {i}/{len(todo)} (concept={c[:40]!r} q{q})", flush=True)


# ---- scoring phase ----------------------------------------------------------
def report(axes: dict[str, list[str]]) -> None:
    draws = build_test_draws(axes)
    print("\n=== AXIS RECOVERY (top-1 / top-3 of the true value among the axis's values) ===")
    for featname, featfn in FEATURIZERS.items():
        print(f"\n--- featurizer: {featname} ---")
        per_axis: dict[str, list[int]] = {ax: [0, 0, 0] for ax in TESTED_AXES}  # [n, top1, top3]
        for d in draws:
            ax = d["tested_axis"]
            if not all(is_cached(d["concept_text"], q) for q in range(len(QUESTIONS))):
                continue
            test_fp = fingerprint(d["concept_text"], featfn)
            ranked = sorted(
                axes[ax],
                key=lambda v: cosine(test_fp, fingerprint(v, featfn)),
                reverse=True,
            )
            rank = ranked.index(d["true_value"])
            per_axis[ax][0] += 1
            per_axis[ax][1] += int(rank == 0)
            per_axis[ax][2] += int(rank < 3)
        print(f"  {'axis':<12} {'n':>3} {'#vals':>6} {'top1':>7} {'top3':>7}")
        for ax in TESTED_AXES:
            n, t1, t3 = per_axis[ax]
            if n:
                print(f"  {ax:<12} {n:>3} {len(axes[ax]):>6} {t1/n:>6.0%} {t3/n:>6.0%}")
            else:
                print(f"  {ax:<12} {n:>3} {len(axes[ax]):>6}   (no cached draws yet)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs-only", action="store_true", help="generate references only")
    ap.add_argument("--report", action="store_true", help="score from cache, no generation")
    ap.add_argument("--axes", default="", help="comma-separated subset to test (default: all 15)")
    args = ap.parse_args()
    if args.axes.strip():
        global TESTED_AXES
        TESTED_AXES = [a.strip() for a in args.axes.split(",") if a.strip()]
    axes = load_axes()
    missing = [a for a in TESTED_AXES if a not in axes]
    if missing:
        sys.exit(f"missing axis files: {missing} (run snapshot into {AXES_DIR})")
    if not args.report:
        generate_all(axes, refs_only=args.refs_only)
    if not args.refs_only:
        report(axes)


if __name__ == "__main__":
    main()
