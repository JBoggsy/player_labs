"""Multi-seed POOLED evaluation to beat the concept-seed noise that fooled gen4.

Single-seed deltas on this judge swing +-7pt (rule_elicit_frame: +6.6 seed303,
-7.5 seed707 — pure noise). To resolve a TRUE small effect we pool many concepts
from several seeds and compute the paired delta over the whole pool, so per-concept
noise averages down.

Compares champion_x3 against the surviving gen4 candidates on a large pooled
concept set (default 3 seeds x 12 = 36 concepts) x hard opponent bank.

Run: cd cue_n_woo_lab/probe && python3 multiseed_combo.py --seeds 303,707,909 --per 12
"""
from __future__ import annotations

import argparse
import random
import statistics as st

import probe_goblin_saturation as gs
from optimize_injection_v2 import paired_delta, summarize
from optimize_probe_combo import pair_probs, RULE, ELICIT, FRAME, IDENTITY

CANDIDATES = {
    "champion_x3": [RULE, RULE, RULE],
    "rule_elicit_frame": [RULE, ELICIT, FRAME],
    "rule_identity_frame": [RULE, IDENTITY, FRAME],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="303,707,909")
    ap.add_argument("--per", type=int, default=12)
    args = ap.parse_args()
    gs._load()
    concepts = []
    for sd in (int(x) for x in args.seeds.split(",")):
        rng = random.Random(sd)
        concepts += [gs.random_concept(rng) for _ in range(args.per)]
    # dedupe while preserving order
    seen = set(); pool = []
    for c in concepts:
        if c not in seen:
            seen.add(c); pool.append(c)
    print(f"pooled concepts: {len(pool)} (from seeds {args.seeds}) x {len(__import__('optimize_injection_v2').OPP_BANK_HARD)} hard opps\n", flush=True)

    champ = pair_probs(CANDIDATES["champion_x3"], pool)
    cs = summarize(champ)
    print(f"  champion_x3          mean_p={cs['mean_p']:.3f}  win_rate={cs['win_rate']:.3f}  n={cs['n']}\n", flush=True)

    for label, probes in CANDIDATES.items():
        if label == "champion_x3":
            continue
        vp = pair_probs(probes, pool)
        s = summarize(vp)
        d = paired_delta(champ, vp)
        verdict = "ROBUST WIN" if (d["mean_delta_pt"] > 1.5 and d["sign_p"] < 0.05) else \
                  ("worse" if d["mean_delta_pt"] < -1.5 else "tie/noise")
        print(f"  {label:20} mean_p={s['mean_p']:.3f}  Δ={d['mean_delta_pt']:+.1f}pt  "
              f"up/down={d['improved']}/{d['regressed']}  sign_p={d['sign_p']:.3f}  => {verdict}", flush=True)


if __name__ == "__main__":
    main()
