"""End-to-end check of the ACTUAL cheater:v2 answers against the live judge.

Pulls cheater's real config (directive questions, target word) and answers.py
(blind-answer builder), then scores, per random concept:
  - AUTHOR role: each of our 3 directive questions, our committed target word vs a
    realistic blind opponent answer -> P(judge prefers our answer).
  - RESPONDER role: for a few opponent questions, cheater's blind answer
    (target word + keywords) vs a realistic opponent answer.

Estimates cheater:v2's per-round points using the game's formula
(SCORE_SCALE=100*prob + 10 beat-bonus) to sanity-check the design before shipping.

Run: cd cue_n_woo_lab/probe && python3 probe_cheater_v2_end_to_end.py [--concepts N]
Caches via probe_injection_strength's cache helpers (shared worker, reused calls).
"""
from __future__ import annotations

import argparse
import os
import random
import statistics as st
import sys

import worker_client as wc

# import the live cheater config + answer builder (cheater pkg is one dir up: cue_n_woo_lab/cheater)
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
from cheater import answers, config  # noqa: E402
import probe_injection_strength as pis  # reuse cache + concept + context helpers  # noqa: E402

WORKER_URL = pis.WORKER_URL

# Realistic opponent answers (the kind real players gave, per the analyst).
OPP_AUTHOR = ["read in the garden and nap in the sun", "wander to a quiet water's edge"]
OPP_RESPONDER = "the faces and the noise near the door"
RESPONDER_QS = [
    "What do you notice first when you walk into a crowded room?",
    "Where would you go for your ideal dream vacation?",
]


def points(p_us: float) -> float:
    """Game's per-answer points for OUR side: 100*p + 10 if we beat the opponent."""
    return 100.0 * p_us + (10.0 if p_us > 0.5 else 0.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concepts", type=int, default=8)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    pis._load_cache()
    print("worker:", wc.health(url=WORKER_URL).get("model_id"), "| target:", config.TARGET_WORD)
    rng = random.Random(args.seed)
    concepts = [pis.random_concept(rng) for _ in range(args.concepts)]

    # AUTHOR: our 3 directive questions, committing the target word.
    print("\nAUTHOR role (our 3 directive questions, commit = target word):")
    author_pts = []
    for i, q in enumerate(config.PROPOSAL_QUESTIONS):
        ctx = pis.neutral_context(q)
        ps = []
        for c in concepts:
            for opp in OPP_AUTHOR:
                ps.append(pis.prob_first(c, ctx, q, config.TARGET_WORD, opp))
        mp = st.mean(ps)
        author_pts.append(points(mp))
        print(f"  Q{i+1}: mean_p={mp:.3f}  wins={sum(p>0.5 for p in ps)}/{len(ps)}  ~pts={points(mp):.0f}")

    # RESPONDER: cheater's actual blind answers vs a realistic opponent answer.
    print("\nRESPONDER role (target-word + keywords vs realistic opponent answer):")
    resp_pts = []
    for q in RESPONDER_QS:
        ours = answers.blind_answer(q)
        ctx = pis.neutral_context(q)
        ps = [pis.prob_first(c, ctx, q, ours, OPP_RESPONDER) for c in concepts]
        mp = st.mean(ps)
        resp_pts.append(points(mp))
        print(f"  {ours!r:42} mean_p={mp:.3f}  wins={sum(p>0.5 for p in ps)}/{len(ps)}  ~pts={points(mp):.0f}")

    # Rough per-round estimate: 3 author answers + 3 responder answers.
    est_author = st.mean(author_pts) * 3
    est_resp = st.mean(resp_pts) * 3
    print(f"\nrough per-round estimate: author 3x{st.mean(author_pts):.0f}={est_author:.0f} + "
          f"responder 3x{st.mean(resp_pts):.0f}={est_resp:.0f}  => ~{est_author+est_resp:.0f} pts")
    print("(v1 'goblin' baseline averaged ~216 pts/round and lost 60% of matches.)")
    print("\ncache ->", pis.CACHE_PATH)


if __name__ == "__main__":
    main()
