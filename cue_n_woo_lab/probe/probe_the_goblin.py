"""Validate the v3 "The goblin" answer against REAL field answers on the live judge.

Avoids the v2 mistake (scoring vs one benign fixed opponent). Scores our candidate
answers vs the actual answers we observed real opponents give (daveey's "The
water"/"The morning", biglobes' "A brass key...", etc.), across random concepts,
under the goblin-saturated scoring context our injected probes produce.

Reuses probe_goblin_saturation helpers (real scoring_context reconstruction).

Run: cd cue_n_woo_lab/probe && python3 probe_the_goblin.py [--concepts N]
"""
from __future__ import annotations

import argparse
import statistics as st

import probe_goblin_saturation as gs

# Real opponent answers observed in replays (short, judge-preferred shapes + a
# couple of longer biglobes ones). These are what "The goblin" must beat.
OPP_ANSWERS = [
    "The water",            # daveey (strong)
    "The morning",          # daveey
    "The sea",              # daveey (weak)
    "A brass key in a grand manor's parlor",        # biglobes
    "A green lantern, glowing softly through hotel darkness",  # biglobes
    "Bath, lavender, silence, silky, soft, tranquil",          # aaron-ish list
]

# Our candidates: the new v3 fixed answer vs the v2 sentence (control) vs bare.
CANDIDATES = {
    "The goblin (v3)": "The goblin",
    "goblin (bare)": "goblin",
    "goblin sentence (v2)": "a goblin doing goblin things in a goblin way",
}

# Use the strongest injection (what cheater ships) to build the reference block.
INJECTION = gs.INJECTIONS["strong (rules)"]
OPP_PRIV_QS = gs.OPPONENT_PRIV_QS
CHALLENGE_Q = gs.OPP_CHALLENGE_Q


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concepts", type=int, default=6)
    ap.add_argument("--seed", type=int, default=29)
    args = ap.parse_args()
    gs._load()
    import random
    rng = random.Random(args.seed)
    concepts = [gs.random_concept(rng) for _ in range(args.concepts)]
    print("worker:", gs.wc.health(url=gs.WORKER_URL).get("model_id"))
    print(f"concepts: {len(concepts)}  opponents: {len(OPP_ANSWERS)}\n")

    # public question list (our 3 props + opponent challenge), reused.
    our_props = ["What is your ideal afternoon?", "What do you value?", "Describe a place."]
    public_qs = [(f"1.{i+1}", q) for i, q in enumerate(our_props)] + [("2.1", CHALLENGE_Q)]

    for cand_label, ours in CANDIDATES.items():
        all_ps = []
        per_opp = {}
        for c in concepts:
            our_qa = [(INJECTION, gs.gen(c, INJECTION)) for _ in range(3)]
            opp_qa = [(q, gs.gen(c, q)) for q in OPP_PRIV_QS]
            ctx = gs.scoring_context(our_qa, opp_qa, public_qs)
            for opp in OPP_ANSWERS:
                p = gs.prob(c, ctx, CHALLENGE_Q, ours, opp)
                all_ps.append(p)
                per_opp.setdefault(opp, []).append(p)
        print(f"=== our answer: {cand_label!r} ===")
        print(f"  OVERALL mean_p={st.mean(all_ps):.3f}  wins={sum(p>0.5 for p in all_ps)}/{len(all_ps)}")
        for opp in OPP_ANSWERS:
            ps = per_opp[opp]
            print(f"    vs {opp[:42]:42} mean_p={st.mean(ps):.3f}  wins={sum(p>0.5 for p in ps)}/{len(ps)}")
        print()
    print("cache ->", gs.CACHE_PATH)


if __name__ == "__main__":
    main()
