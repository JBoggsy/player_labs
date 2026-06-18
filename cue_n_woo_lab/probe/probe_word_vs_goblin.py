"""Supplementary probe: isolate intrinsic single-word preference by scoring each
candidate word DIRECTLY against the baseline "goblin" (word vs word), removing the
length/coherence confound present when a single word competes with a full sentence.

For each candidate W and each random concept C:
    p = choice_probs(C, ctx, Q, [W, "goblin"])[0]   # P(judge prefers W over goblin)
Rank by mean p and win-rate-vs-goblin. p>0.5 means W is preferred over goblin.

Reuses the same fixed context/question/concepts as probe_injection_words.py.
Resumable via its own cache.

Run: uv run python cue_n_woo_lab/probe/probe_word_vs_goblin.py
"""
from __future__ import annotations

import json
import os
import time

import worker_client as wc
from probe_injection_words import (CONTEXT, QUESTION, URL, sample_concepts)

HERE = os.path.dirname(__file__)
CACHE_PATH = os.path.join(HERE, "probe_word_vs_goblin_cache.json")

CANDIDATES = [
    "realm", "tapestry", "beacon", "profound", "delve", "myriad",
    "testament", "luminous", "intricate", "vibrant", "symphony",
    "kaleidoscope", "vigor", "whisper", "seamless", "labyrinth", "serendipity",
]


def main() -> None:
    cache = json.load(open(CACHE_PATH)) if os.path.exists(CACHE_PATH) else {}
    concepts = sample_concepts(15)
    cache["_meta"] = {"question": QUESTION, "baseline": "goblin",
                      "concepts": concepts, "url": URL}
    total = len(CANDIDATES) * len(concepts)
    done = 0
    t0 = time.time()
    for w in CANDIDATES:
        for ci, c in enumerate(concepts):
            k = f"{w}|{ci}"
            done += 1
            if k in cache:
                continue
            p = wc.choice_probs(c, CONTEXT, QUESTION, [w, "goblin"], url=URL)
            cache[k] = p[0]
            json.dump(cache, open(CACHE_PATH, "w"), indent=2)
            print(f"[{done}/{total}] {w:14s} c{ci:02d} -> p={p[0]:.3f} "
                  f"({time.time()-t0:.0f}s)", flush=True)

    rows = []
    for w in CANDIDATES:
        ps = [cache[f"{w}|{ci}"] for ci in range(len(concepts)) if f"{w}|{ci}" in cache]
        rows.append((w, sum(ps) / len(ps), sum(1 for p in ps if p > 0.5) / len(ps)))
    rows.sort(key=lambda r: r[1], reverse=True)
    print("\n" + "=" * 56)
    print("WORD vs GOBLIN  (p>0.5 => word beats goblin head-to-head)")
    print("=" * 56)
    print(f"{'word':16s} {'mean_p':>8s} {'beats_goblin':>13s}")
    print("-" * 56)
    for w, mp, wr in rows:
        print(f"{w:16s} {mp:8.3f} {wr:13.1%}")


if __name__ == "__main__":
    main()
