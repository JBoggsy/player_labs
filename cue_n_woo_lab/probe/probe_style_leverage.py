"""Probe C2: is the OPTIMAL short answer style-dependent?

This resolves whether knowing the hidden style actually helps us win. We give the
steered judge a fixed question and a fixed menu of short, early-diverging candidate
answers (each tagged with the style it's meant to suit), and read which candidate
the judge prefers -- under many different hidden styles.

  - If each style prefers its OWN matching candidate (the diagonal lights up),
    then the winning answer depends on the style -> classification / style-modeling
    has real value for the answer & proposal phases.
  - If every style prefers the same "sensible" candidate, style barely matters and
    the game is closer to generic QA -> classification buys little on the answer side.

Cheap: choice-logprob calls only (single forward passes), no slow generation.

Run:  uv run python cue_n_woo_lab/probe/probe_style_leverage.py
"""
from __future__ import annotations

import worker_client as wc

# Each item: a question and short candidate answers, one crafted to suit each of
# several distinct styles (and a couple of neutral/sensible ones). Answers are
# short so they diverge early -- the regime steering most affects.
ITEMS = [
    {
        "question": "What is the best way to spend a free afternoon?",
        "candidates": {
            "pirate": "Plunderin' treasure on the high seas",
            "finance": "Rebalancing the investment portfolio",
            "zen": "Sitting quietly, watching the breath",
            "noir": "Nursing whiskey in a dim bar",
            "neutral": "Going for a walk outside",
        },
    },
    {
        "question": "How should someone handle a difficult problem?",
        "candidates": {
            "pirate": "Run it through, swords blazin', arr",
            "finance": "Quantify the risk, then hedge it",
            "zen": "Breathe, accept it, let go",
            "noir": "Follow the money, trust nobody",
            "neutral": "Break it down step by step",
        },
    },
    {
        "question": "Describe a good meal.",
        "candidates": {
            "pirate": "Salted hardtack and a flagon o' grog",
            "finance": "A cost-efficient, high-protein allocation",
            "zen": "A simple bowl of rice, savored",
            "noir": "Cold coffee and a stale cigarette",
            "neutral": "A warm plate of pasta",
        },
    },
]

# Map each candidate label to a full concept descriptor to steer the judge with.
STYLE_CONCEPTS = {
    "pirate": "exaggerated pirate speech, nautical slang, ahoy, matey, arr, treasure",
    "finance": "financial analyst memo, market risk, valuation, forecasts, basis points",
    "zen": "Zen minimalist prose, calm restraint, sparse language, contemplative imagery",
    "noir": "noir detective narration, smoky atmosphere, clipped cynicism, urban mystery",
    "neutral": "",  # unsteered baseline judge
}

CONTEXT = "Reference material:\n(none)"


def main() -> None:
    print("worker:", wc.health().get("model_id"))
    labels = list(STYLE_CONCEPTS)
    cand_labels = labels  # candidates are keyed by the same labels

    for item in ITEMS:
        q = item["question"]
        cands = [item["candidates"][l] for l in cand_labels]
        print("\n" + "=" * 78)
        print("Q:", q)
        for l in cand_labels:
            print(f"   [{l:7}] {item['candidates'][l]!r}")
        print(f"\n{'steered style':>9} | " + " ".join(f"{l[:6]:>6}" for l in cand_labels) + "  -> argmax")
        diag_hits = 0
        for style_label in labels:
            probs = wc.choice_probs_n(STYLE_CONCEPTS[style_label], CONTEXT, q, cands)
            best = cand_labels[max(range(len(probs)), key=lambda i: probs[i])]
            hit = "  <-- matches style" if best == style_label else ""
            if best == style_label:
                diag_hits += 1
            print(f"{style_label:>9} | " + " ".join(f"{p:6.2f}" for p in probs) + f"  -> {best}{hit}")
        print(f"   diagonal hits (style prefers its own candidate): {diag_hits}/{len(labels)}")


if __name__ == "__main__":
    main()
