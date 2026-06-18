"""Confirm the gen4 candidate (rule_elicit_frame: 3 DISTINCT probes) on a 2ND seed.

Single-seed probe deltas of a few points have proven to be noise on this judge
(see fantasy-question reversal). The gen4 candidate showed +6.6pt at seed 303 with
sign_p=0.060 (borderline). Before building/Gate-2, re-test champion_x3 vs
rule_elicit_frame on a fresh, larger concept seed with the paired delta + sign test.

Run: cd cue_n_woo_lab/probe && python3 confirm_probe_combo.py --concepts 16 --seed 707
"""
from __future__ import annotations

import argparse
import random
import statistics as st

import probe_goblin_saturation as gs
from optimize_injection_v2 import paired_delta, summarize
from optimize_probe_combo import pair_probs, RULE, ELICIT, FRAME

CHAMPION_PROBES = [RULE, RULE, RULE]
CANDIDATE_PROBES = [RULE, ELICIT, FRAME]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concepts", type=int, default=16)
    ap.add_argument("--seed", type=int, default=707)
    args = ap.parse_args()
    gs._load()
    rng = random.Random(args.seed)
    concepts = [gs.random_concept(rng) for _ in range(args.concepts)]
    print(f"CONFIRM seed={args.seed} | {len(concepts)} concepts x hard opponents\n", flush=True)

    champ = pair_probs(CHAMPION_PROBES, concepts)
    cand = pair_probs(CANDIDATE_PROBES, concepts)
    cs, vs = summarize(champ), summarize(cand)
    d = paired_delta(champ, cand)
    print(f"  champion_x3       mean_p={cs['mean_p']:.3f}  win_rate={cs['win_rate']:.3f}")
    print(f"  rule_elicit_frame mean_p={vs['mean_p']:.3f}  win_rate={vs['win_rate']:.3f}")
    print(f"  paired Δ={d['mean_delta_pt']:+.1f}pt  up/down={d['improved']}/{d['regressed']}  sign_p={d['sign_p']:.3f}")
    verdict = "CONFIRMED multi-pt win" if (d["mean_delta_pt"] > 1.5 and d["sign_p"] < 0.05) else "NOT confirmed"
    print(f"  => {verdict}")


if __name__ == "__main__":
    main()
