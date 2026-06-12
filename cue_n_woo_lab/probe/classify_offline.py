"""Offline classifier bake-off over the cached generations (no worker calls).

Compares featurizers and question counts for the nearest-neighbor style
classifier, to find the cheapest setup that classifies the hidden style well.
Style lives in case, punctuation, and morphology, so char n-grams should beat
word TF-IDF; the player gets 3 questions, so concatenating them should help too.

Run (after build_cache.py):  uv run python cue_n_woo_lab/probe/classify_offline.py
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter

HERE = os.path.dirname(__file__)
CONCEPTS = json.load(open(os.path.join(HERE, "concepts.json")))
CACHE = json.load(open(os.path.join(HERE, "cache", "generations.json")))


# ---- featurizers: text -> token list ----

def feat_word_lower(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9']+", text.lower()) if len(t) > 2]


def feat_word_raw(text: str) -> list[str]:
    # keep case + short function words + standalone punctuation as tokens
    return re.findall(r"[A-Za-z0-9']+|[^\sA-Za-z0-9]", text)


def feat_char_ngram(text: str, lo: int = 3, hi: int = 5) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    grams = []
    for n in range(lo, hi + 1):
        grams += [text[i:i + n] for i in range(len(text) - n + 1)]
    return grams


def feat_combined(text: str) -> list[str]:
    return feat_char_ngram(text) + ["W:" + w for w in feat_word_raw(text)]


FEATURIZERS = {
    "word_lower": feat_word_lower,
    "word_raw": feat_word_raw,
    "char_3_5": feat_char_ngram,
    "combined": feat_combined,
}


# ---- tf-idf nearest neighbor ----

def build_idf(docs: list[list[str]]) -> dict[str, float]:
    n = len(docs)
    df: Counter[str] = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1
    return {term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in df.items()}


def vec(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    return {t: c * idf.get(t, 0.0) for t, c in tf.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def evaluate(featurize, n_questions: int) -> tuple[float, float]:
    refs = CACHE["refs"]
    tests = CACHE["tests"]
    idxs = sorted(int(k) for k in refs)

    def fingerprint(answers: list[str]) -> list[str]:
        text = "\n".join(answers[:n_questions])
        return featurize(text)

    ref_tokens = {i: fingerprint(refs[str(i)]) for i in idxs}
    idf = build_idf(list(ref_tokens.values()))
    ref_vecs = {i: vec(ref_tokens[i], idf) for i in idxs}

    top1 = top3 = 0
    for true_i in idxs:
        qv = vec(fingerprint(tests[str(true_i)]), idf)
        ranked = sorted(idxs, key=lambda j: cosine(qv, ref_vecs[j]), reverse=True)
        if ranked[0] == true_i:
            top1 += 1
        if true_i in ranked[:3]:
            top3 += 1
    n = len(idxs)
    return top1 / n, top3 / n


def main() -> None:
    print(f"cache: {len(CACHE['refs'])} styles, {len(CACHE['questions'])} questions each\n")
    print(f"{'featurizer':<12} {'#Q':>3} {'top1':>6} {'top3':>6}")
    print("-" * 32)
    for name, fn in FEATURIZERS.items():
        for nq in range(1, len(CACHE["questions"]) + 1):
            t1, t3 = evaluate(fn, nq)
            print(f"{name:<12} {nq:>3} {t1:>6.0%} {t3:>6.0%}")


if __name__ == "__main__":
    main()
