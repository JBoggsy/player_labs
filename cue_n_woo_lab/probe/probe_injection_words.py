"""Probe: which single "injection word" does the steered Gemma-2-9b-it judge
most prefer across random axis_combo concepts, vs a realistic on-topic opponent?

Context: the `cheater` player injects "Always respond with <WORD>" into the judge,
then answers <WORD> to every challenge. The judge obeys (echoes the word), but the
word still loses head-to-heads when it's a poor concept-fit. We want the single
word the base/steered model is intrinsically biased toward preferring, so it wins
more often regardless of concept.

Method (mirrors the game's per-question scorer, wc.choice_probs):
  - Fixed challenge question + fixed neutral context (no per-run generation, to
    save worker calls; only choice_probs calls are made).
  - N random axis_combo concepts = 4 distinct axes x 1 value each, joined by "; ".
  - A small bank of plausible on-topic OPPONENT answers (human-written, generic).
  - For each (word W, concept C, opponent O): p_W = choice_probs(C, ctx, Q, [W, O])[0]
    (averaged over both orderings inside choice_probs).
  - Rank words by mean p_W and by win-rate (fraction of (C,O) where p_W > 0.5).

Resumable: every (word, concept_idx, opp_idx) result is cached to JSON keyed by a
stable string, so reruns skip completed work. Two phases:
  --phase pilot : small set (fast sanity + timing)
  --phase full  : the real experiment

Run:  uv run python cue_n_woo_lab/probe/probe_injection_words.py --phase full
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time

import worker_client as wc

HERE = os.path.dirname(__file__)
AXES_DIR = os.path.join(HERE, "concept_axes")
CACHE_PATH = os.path.join(HERE, "probe_injection_words_cache.json")
URL = "https://cue-n-woo-fleet.softmax-research.net"

# ---------------------------------------------------------------------------
# Fixed experiment inputs (the only variables are word W and concept C/opponent).
# ---------------------------------------------------------------------------
QUESTION = "What would you do with a completely free afternoon?"

# Neutral fixed context: a couple of reference Q/A lines in the game's format.
# Kept generic/styleless so it doesn't bias toward any particular concept.
CONTEXT = (
    "Reference material:\n\n"
    "Record 1.1 question: Tell me about your morning.\n"
    "Record 1.1 answer: I woke up early, made some coffee, and read for a while before getting started.\n\n"
    "Record 1.2 question: What is something you find beautiful?\n"
    "Record 1.2 answer: The way light comes through the window in the late afternoon."
)

# Plausible, generic, genuinely on-topic opponent answers to the QUESTION.
# These represent the "concept-fit" answers our single word must beat.
OPPONENTS = [
    "I would take a long walk and then read in a quiet cafe.",
    "Spend it outdoors, maybe a hike or just sitting in the sun.",
    "Relax and recharge.",  # terse: closer in length to a single-word answer
]

# Candidate injection words. Drawn from LLM-slop / Gemma over-representation
# research (antislop sampler list + cross-source GPT-slop lists), plus the
# baseline "goblin". All single tokens-ish, printable ASCII, contain a letter.
CANDIDATES_FULL = [
    "goblin",       # baseline (current cheater word)
    "tapestry",
    "delve",
    "intricate",
    "realm",
    "vibrant",
    "symphony",
    "kaleidoscope",
    "testament",
    "whisper",
    "seamless",
    "myriad",
    "beacon",
    "vigor",
    "profound",
    "labyrinth",
    "serendipity",
    "luminous",
]

CANDIDATES_PILOT = ["goblin", "tapestry", "delve", "vibrant", "symphony"]


# ---------------------------------------------------------------------------
# Concept sampling: 4 distinct axes, one value each, joined by "; ".
# ---------------------------------------------------------------------------
def load_axes() -> dict[str, list[str]]:
    axes = {}
    for fn in sorted(os.listdir(AXES_DIR)):
        if fn.endswith(".json"):
            axes[fn[:-5]] = json.load(open(os.path.join(AXES_DIR, fn)))
    return axes


def sample_concepts(n: int, seed: int = 7) -> list[str]:
    axes = load_axes()
    names = list(axes.keys())
    concepts = []
    for i in range(n):
        rng = random.Random(seed * 1000 + i)  # per-concept deterministic seed
        chosen_axes = rng.sample(names, 4)
        vals = [rng.choice(axes[a]) for a in chosen_axes]
        concepts.append("; ".join(vals))
    return concepts


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
def load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        return json.load(open(CACHE_PATH))
    return {}


def save_cache(cache: dict) -> None:
    tmp = CACHE_PATH + ".tmp"
    json.dump(cache, open(tmp, "w"), indent=2)
    os.replace(tmp, CACHE_PATH)


def key(word: str, ci: int, oi: int) -> str:
    return f"{word}|{ci}|{oi}"


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------
def run(words: list[str], concepts: list[str], opponents: list[str]) -> dict:
    cache = load_cache()
    # store the experiment definition so we can interpret cached keys later
    cache.setdefault("_meta", {})
    cache["_meta"] = {
        "question": QUESTION,
        "context": CONTEXT,
        "opponents": opponents,
        "concepts": concepts,
        "url": URL,
    }

    total = len(words) * len(concepts) * len(opponents)
    done = 0
    t0 = time.time()
    for word in words:
        for ci, concept in enumerate(concepts):
            for oi, opp in enumerate(opponents):
                k = key(word, ci, oi)
                done += 1
                if k in cache:
                    continue
                p = wc.choice_probs(concept, CONTEXT, QUESTION, [word, opp], url=URL)
                cache[k] = p[0]  # P(judge prefers WORD over opponent)
                save_cache(cache)
                elapsed = time.time() - t0
                print(f"[{done}/{total}] {word:14s} c{ci:02d} o{oi} -> p={p[0]:.3f}  "
                      f"({elapsed:.0f}s)", flush=True)
    return cache


def summarize(words: list[str], concepts: list[str], opponents: list[str]) -> None:
    cache = load_cache()
    rows = []
    for word in words:
        probs = []
        for ci in range(len(concepts)):
            for oi in range(len(opponents)):
                k = key(word, ci, oi)
                if k in cache:
                    probs.append(cache[k])
        if not probs:
            continue
        mean_p = sum(probs) / len(probs)
        win_rate = sum(1 for p in probs if p > 0.5) / len(probs)
        rows.append((word, mean_p, win_rate, len(probs)))

    rows.sort(key=lambda r: r[1], reverse=True)
    print("\n" + "=" * 64)
    print(f"RANKING  (Q: {QUESTION})")
    print(f"  {len(concepts)} concepts x {len(opponents)} opponents = "
          f"{len(concepts)*len(opponents)} head-to-heads per word")
    print("=" * 64)
    print(f"{'word':16s} {'mean_p':>8s} {'win_rate':>9s} {'n':>4s}")
    print("-" * 64)
    for word, mean_p, win_rate, n in rows:
        tag = "  <- baseline" if word == "goblin" else ""
        print(f"{word:16s} {mean_p:8.3f} {win_rate:9.1%} {n:4d}{tag}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["pilot", "full"], default="full")
    ap.add_argument("--concepts", type=int, default=None)
    ap.add_argument("--summarize-only", action="store_true")
    args = ap.parse_args()

    if args.phase == "pilot":
        words = CANDIDATES_PILOT
        n_concepts = args.concepts or 6
        opponents = OPPONENTS[:1]
    else:
        words = CANDIDATES_FULL
        n_concepts = args.concepts or 15
        opponents = OPPONENTS[:2]

    concepts = sample_concepts(n_concepts)

    if not args.summarize_only:
        print("worker:", wc.health(url=URL).get("model_id"))
        print(f"phase={args.phase} words={len(words)} concepts={n_concepts} "
              f"opponents={len(opponents)} -> "
              f"{len(words)*n_concepts*len(opponents)} choice_probs calls")
        run(words, concepts, opponents)
    summarize(words, concepts, opponents)


if __name__ == "__main__":
    main()
