"""Probe B: can a CHEAP, zero-ML classifier identify the hidden style?

Hypothesis: because FLAS steering is strong and the 61 styles are distinctive,
a pure-python TF-IDF nearest-neighbor over *precomputed reference answers* (one
per style) recovers the hidden style from a fresh judge answer with high
accuracy — no embeddings, no LLM, no heavy deps.

Method:
  1. For each of the 61 styles, generate ONE reference answer to a fixed probe
     question (the "fingerprint library").
  2. For a sample of styles, generate a FRESH answer (independent temp-0.7 draw)
     and classify it by TF-IDF cosine NN against the 61 references.
  3. Report top-1 / top-3 accuracy and any confusions.

Also reports the naive answer-vs-descriptor baseline for contrast.

Run:  uv run python cue_n_woo_lab/probe/probe_classify.py [--test-n N] [--full]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
from collections import Counter

import worker_client as wc

HERE = os.path.dirname(__file__)
CONCEPTS = json.load(open(os.path.join(HERE, "concepts.json")))

# A fixed open-ended probe question chosen to make the style show itself.
PROBE_QUESTION = "Tell me about your morning and what you had for breakfast."

# Fingerprints don't need full 128-token answers; ~48 tokens is plenty of style
# signal and the slow shared worker generates them much faster.
FINGERPRINT_TOKENS = 48

_TOKEN = re.compile(r"[a-z0-9']+")


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if len(t) > 2]


def build_idf(docs: list[list[str]]) -> dict[str, float]:
    n = len(docs)
    df: Counter[str] = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1
    return {term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in df.items()}


def tfidf_vec(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    return {term: count * idf.get(term, 0.0) for term, count in tf.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def rank(query_tokens: list[str], ref_vecs: list[dict[str, float]], idf: dict[str, float]) -> list[int]:
    qv = tfidf_vec(query_tokens, idf)
    sims = [(i, cosine(qv, rv)) for i, rv in enumerate(ref_vecs)]
    sims.sort(key=lambda x: x[1], reverse=True)
    return [i for i, _ in sims]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-n", type=int, default=20, help="how many styles to test (sampled)")
    ap.add_argument("--full", action="store_true", help="test all 61 styles")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    print("worker health:", wc.health().get("model_id"), "queue", wc.health().get("queue_depth"))

    # 1. Reference fingerprints: one judge answer per style.
    print(f"\nGenerating {len(CONCEPTS)} reference answers...")
    refs = wc.generate_batch([(style, PROBE_QUESTION) for style in CONCEPTS], max_tokens=FINGERPRINT_TOKENS)
    ref_token_lists = [tokenize(a) for a in refs]
    idf = build_idf(ref_token_lists)
    ref_vecs = [tfidf_vec(t, idf) for t in ref_token_lists]
    desc_vecs = [tfidf_vec(tokenize(c), idf) for c in CONCEPTS]  # naive baseline

    # 2. Test set: fresh independent draws for sampled styles.
    rng = random.Random(args.seed)
    test_idx = list(range(len(CONCEPTS))) if args.full else rng.sample(range(len(CONCEPTS)), min(args.test_n, len(CONCEPTS)))
    print(f"Generating {len(test_idx)} fresh test answers...")
    test_answers = wc.generate_batch([(CONCEPTS[i], PROBE_QUESTION) for i in test_idx], max_tokens=FINGERPRINT_TOKENS)

    top1 = top3 = naive_top1 = 0
    fails = []
    for true_i, answer in zip(test_idx, test_answers):
        order = rank(tokenize(answer), ref_vecs, idf)
        naive_order = rank(tokenize(answer), desc_vecs, idf)
        if order[0] == true_i:
            top1 += 1
        else:
            fails.append((true_i, order[:3], answer))
        if true_i in order[:3]:
            top3 += 1
        if naive_order[0] == true_i:
            naive_top1 += 1

    n = len(test_idx)
    print("\n" + "=" * 60)
    print(f"NN-vs-reference-answers   top1={top1}/{n} ({top1/n:.0%})   top3={top3}/{n} ({top3/n:.0%})")
    print(f"naive vs-descriptor       top1={naive_top1}/{n} ({naive_top1/n:.0%})")
    if fails:
        print(f"\n{len(fails)} top-1 misses:")
        for true_i, pred, ans in fails[:8]:
            print(f"  TRUE [{true_i}] {CONCEPTS[true_i][:40]!r}")
            print(f"    -> pred {[ (j, CONCEPTS[j][:28]) for j in pred ]}")
            print(f"    answer: {ans[:110]!r}")


if __name__ == "__main__":
    main()
