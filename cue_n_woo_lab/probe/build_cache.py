"""Build a local cache of judge generations so classifier experiments can iterate
OFFLINE (the shared worker is slow, ~1 gen/10s; we hit it once, then reuse).

Saves cache/generations.json:
  {
    "questions": [...],
    "refs":  {style_index: [answer_per_question, ...]},   # the fingerprint library
    "tests": {style_index: [answer_per_question, ...]}     # independent fresh draws
  }

refs and tests are SEPARATE temp-0.7 draws, so evaluating tests against refs is an
honest held-out check (never the same draw).

Run:  uv run python cue_n_woo_lab/probe/build_cache.py [--tokens 64]
"""
from __future__ import annotations

import argparse
import json
import os

import worker_client as wc

HERE = os.path.dirname(__file__)
CONCEPTS = json.load(open(os.path.join(HERE, "concepts.json")))
CACHE_PATH = os.path.join(HERE, "cache", "generations.json")

# Three diverse probe questions to elicit different facets of a style.
QUESTIONS = [
    "Tell me about your morning and what you had for breakfast.",
    "What advice would you give to someone starting a new job?",
    "Describe the weather outside right now.",
]


def gen_all(tokens: int) -> dict[int, list[str]]:
    pairs = [(style, q) for style in CONCEPTS for q in QUESTIONS]
    answers = wc.generate_batch(pairs, max_tokens=tokens)
    out: dict[int, list[str]] = {}
    k = 0
    for si in range(len(CONCEPTS)):
        out[si] = answers[k:k + len(QUESTIONS)]
        k += len(QUESTIONS)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", type=int, default=64)
    args = ap.parse_args()
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    print("worker:", wc.health().get("model_id"))
    print(f"Building reference library ({len(CONCEPTS)} styles x {len(QUESTIONS)} questions)...")
    refs = gen_all(args.tokens)
    print(f"Building test set ({len(CONCEPTS)} styles x {len(QUESTIONS)} questions)...")
    tests = gen_all(args.tokens)
    json.dump({"questions": QUESTIONS, "refs": refs, "tests": tests}, open(CACHE_PATH, "w"), indent=1)
    print("wrote", CACHE_PATH)


if __name__ == "__main__":
    main()
