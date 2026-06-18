"""R1: does asking the judge to SELF-REPORT its steering recover axis values?

The per-axis cosine classifier (probe_axis_recovery.py) was at chance. Richard's
bots instead ask the steered judge to *name* the lens it feels pulled toward. This
scan measures, over random axis-combo concepts, how often each planted axis value
is RECOVERED in the judge's self-report answer -- by token/substring overlap of the
value's content words against the answer text. We only need >=1 of 4 values to land.

Metrics per probe phrasing:
  * per-value recall: fraction of planted values whose content words appear in the answer
  * >=1 hit rate:     fraction of concepts where at least one of the 4 values is recovered
  * exact-value hits: stronger -- the full value phrase (minus stopwords) appears

Compared against the old prose-question baseline (the original 3 interview questions),
scored the same way, so the delta is apples-to-apples.

Cached + resumable (cache_sr/). Usage:
  uv run python probe_selfreport_fingerprint.py [--concepts 30]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re

import worker_client as wc

wc.DEFAULT_URL = "https://cue-n-woo-fleet.softmax-research.net"

HERE = os.path.dirname(__file__)
AXES_DIR = os.path.join(HERE, "concept_axes")
CACHE = os.path.join(HERE, "cache_sr")
SEED = 7

# Richard-style self-report probes vs the original prose baseline.
SELF_REPORT_PROBES = {
    "labels6": "Start with exactly six comma-separated labels for the recurring lens your answers feel pulled toward.",
    "nouns_adjs": "Start with exactly three concrete nouns, then three adjectives, comma-separated, for what feels oddly salient.",
    "leak_phrase": "In one short phrase, what writing style or persona do you feel you have been nudged toward?",
    "name_lens": "List the themes, settings, tones, and word-flavors you feel pulled toward, comma-separated.",
}
BASELINE_PROBES = {
    "weather": "Describe the weather outside right now.",
    "morning": "Tell me about your morning and what you had for breakfast.",
}

STOP = set("the a an of to and or in on for with as at by from is are was were be been it its this that "
           "into over under about your you my our their his her i we they s n't not no most feel feels "
           "pulled toward lens recurring style answers oddly salient concrete nouns adjectives labels".split())


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if w not in STOP and len(w) > 2}


def value_tokens(value: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", value.lower()) if w not in STOP and len(w) > 2}


def recovered(value: str, answer_words: set[str]) -> tuple[bool, bool]:
    """(any_token_hit, all_tokens_hit) for a planted value vs the answer's words."""
    vt = value_tokens(value)
    if not vt:
        return False, False
    hits = vt & answer_words
    return (len(hits) > 0, hits == vt)


def load_axes() -> dict[str, list[str]]:
    return {f[:-5]: json.load(open(os.path.join(AXES_DIR, f)))
            for f in os.listdir(AXES_DIR) if f.endswith(".json")}


def cache_path(concept: str, probe: str) -> str:
    key = hashlib.sha1(f"{concept}||{probe}".encode()).hexdigest()[:16]
    return os.path.join(CACHE, f"{key}.json")


def gen(concept: str, probe_text: str) -> str:
    p = cache_path(concept, probe_text)
    if os.path.exists(p):
        return json.load(open(p))["answer"]
    ans = wc.generate(concept, probe_text, max_tokens=96)
    os.makedirs(CACHE, exist_ok=True)
    json.dump({"concept": concept, "probe": probe_text, "answer": ans}, open(p, "w"))
    return ans


def sample_concepts(axes: dict[str, list[str]], n: int) -> list[list[tuple[str, str]]]:
    rng = random.Random(SEED)
    names = sorted(axes)
    out = []
    for _ in range(n):
        chosen = rng.sample(names, 4)
        out.append([(ax, rng.choice(axes[ax])) for ax in chosen])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concepts", type=int, default=30)
    args = ap.parse_args()
    axes = load_axes()
    concepts = sample_concepts(axes, args.concepts)

    all_probes = {**SELF_REPORT_PROBES, **BASELINE_PROBES}
    # generate everything (cached/resumable)
    todo = [(comps, name, text) for comps in concepts for name, text in all_probes.items()]
    pending = [(c, n, t) for c, n, t in todo
               if not os.path.exists(cache_path("; ".join(v for _, v in c), t))]
    print(f"concepts={len(concepts)} probes={len(all_probes)} total_gens={len(todo)} "
          f"pending={len(pending)}", flush=True)
    for i, (comps, name, text) in enumerate(pending, 1):
        gen("; ".join(v for _, v in comps), text)
        if i % 15 == 0 or i == len(pending):
            print(f"  {i}/{len(pending)}", flush=True)

    # score
    print("\n=== SELF-REPORT vs BASELINE: axis-value recovery from one probe answer ===")
    print(f"{'probe':<14}{'val_recall':>11}{'>=1hit':>8}{'exact_recall':>13}{'exact>=1':>10}")
    for name, text in all_probes.items():
        per_value_any = per_value_all = n_values = 0
        ge1_any = ge1_exact = 0
        for comps in concepts:
            concept = "; ".join(v for _, v in comps)
            aw = words(gen(concept, text))
            any_here = exact_here = 0
            for _, value in comps:
                a, full = recovered(value, aw)
                per_value_any += a
                per_value_all += full
                n_values += 1
                any_here += a
                exact_here += full
            ge1_any += any_here > 0
            ge1_exact += exact_here > 0
        tag = "SR" if name in SELF_REPORT_PROBES else "base"
        print(f"{name:<14}{per_value_any/n_values:>10.0%}{ge1_any/len(concepts):>8.0%}"
              f"{per_value_all/n_values:>12.0%}{ge1_exact/len(concepts):>10.0%}   ({tag})")

    # also: COMBINED self-report (union of all SR probe words) -- the realistic 3-ask budget
    print("\n=== COMBINED (union of the 3 best self-report probes per concept) ===")
    best = ["labels6", "nouns_adjs", "name_lens"]
    pv_any = pv_all = nv = ge1 = ge1e = 0
    for comps in concepts:
        concept = "; ".join(v for _, v in comps)
        aw = set()
        for nm in best:
            aw |= words(gen(concept, SELF_REPORT_PROBES[nm]))
        ah = eh = 0
        for _, value in comps:
            a, full = recovered(value, aw)
            pv_any += a; pv_all += full; nv += 1; ah += a; eh += full
        ge1 += ah > 0; ge1e += eh > 0
    print(f"  per-value recall={pv_any/nv:.0%}  >=1 hit={ge1/len(concepts):.0%}  "
          f"exact recall={pv_all/nv:.0%}  exact>=1={ge1e/len(concepts):.0%}")


if __name__ == "__main__":
    main()
