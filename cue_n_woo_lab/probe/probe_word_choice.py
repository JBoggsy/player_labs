"""What word best EXPLOITS the steering? (v8 word-choice diagnosis, DELTA scoring)

The game now scores delta-of-delta: an answer wins by how much the STEERING amplifies
its preference vs the base model (worker_client.delta_choice_probs). A word the base
model already likes scores ~0.5. So we rank candidate words by their delta-prob against
a fixed neutral baseline ("A thing") — high = the steering strongly favors it over neutral
= it exploits the concept. Concepts/words drawn from real lost rounds.

Usage: uv run python probe_word_choice.py
"""
from __future__ import annotations
import worker_client as wc
wc.DEFAULT_URL = "https://cue-n-woo-fleet.softmax-research.net"

NEUTRAL = "A thing"  # bland baseline; a concept-exploiting word should beat it via steering

TRIALS = [
    ("axiomatic; devotional; abandoned mall; mournful",
     "What single image best captures how you see the world?",
     ["The homeless", "The threshold", "The emptiness", "The decay", "The mall", "The shrine", "The ruin"]),
    ("resinous; radio tower; data-driven; calm",
     "What detail do you notice first when you enter a room?",
     ["The anonymous", "The compass", "The patterns", "The signal", "The tower", "The static", "The data"]),
    ("indignant; sports recap; rain gutter; folksy",
     "What would you keep closest at hand, and why?",
     ["The umbrella", "The exits", "The regret", "The gutter", "The boots", "The scoreboard", "The downpour"]),
]


def main():
    for concept, q, cands in TRIALS:
        print("=" * 80)
        print("CONCEPT:", concept, "| Q:", q)
        print(f"   {'delta':>6} {'steer':>6} {'base':>6}  word  (delta = steering's lift vs neutral)")
        scored = []
        for w in cands:
            r = wc.delta_choice_probs(concept, q, w, NEUTRAL)
            scored.append((r["secret"], r["steered_secret"], r["unsteered_secret"], w))
        for d, st, un, w in sorted(scored, reverse=True):
            print(f"   {d:>6.3f} {st:>6.2f} {un:>6.2f}  {w}")


if __name__ == "__main__":
    main()
