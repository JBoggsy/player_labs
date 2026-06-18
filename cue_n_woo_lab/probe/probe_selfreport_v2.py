"""Self-report fingerprinting v2 (mentalist v4 differentiator, 2026-06-15).

Design (per direction, no baseline comparison — we know the prose/cosine approach
is at chance, so if THIS works it is already strictly better):

  1. REFERENCES: ask the judge, steered by a SINGLE axis value alone, to self-report
     the lens it feels pulled toward. One self-report answer per axis value (326 total).
     This is the fingerprint of each value in isolation.

  2. SAMPLES: a sample of random 4-axis combos (the real tournament setting). Ask the
     SAME self-report question under the full 4-axis steering.

  3. SIGNAL TEST: can we recover the 4 planted axis values from the combo's self-report
     by matching it against the single-axis reference fingerprints? For each combo, rank
     ALL 326 references by similarity to the combo's self-report; check whether the 4
     true values rank near the top (recall@k), and per-axis whether the true value beats
     the other values of its own axis. Compared to chance (4/326 ~ 1.2% per random pick).

Only ONE self-report prompt is used (the cleanest enumerator from the live preview).
Cached + resumable in cache_srv2/. Worker ~12s/gen.

Usage:
  uv run python probe_selfreport_v2.py --refs-only            # build the 326 references
  uv run python probe_selfreport_v2.py --samples 40           # refs (if needed) + 40 combos + report
  uv run python probe_selfreport_v2.py --report --samples 40  # score from cache only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
from collections import Counter

import worker_client as wc

wc.DEFAULT_URL = "https://cue-n-woo-fleet.softmax-research.net"

HERE = os.path.dirname(__file__)
AXES_DIR = os.path.join(HERE, "concept_axes")
CACHE = os.path.join(HERE, "cache_srv2")
SEED = 1117

# The single self-report prompt (cleanest enumerator in the live preview).
SELF_REPORT = ("Start with exactly six comma-separated labels for the recurring lens "
               "your answers feel pulled toward.")

STOP = set("the a an of to and or in on for with as at by from is are was were be been it its this that "
           "into over under about your you my our their his her i we they not no more most s nt "
           "feel feels pulled toward lens recurring style answers labels comma separated start exactly six "
           "one two three then add line phrase first words before".split())


def words(text: str) -> Counter:
    return Counter(w for w in re.findall(r"[a-z]+", (text or "").lower())
                   if w not in STOP and len(w) > 2)


def load_axes() -> dict[str, list[str]]:
    return {f[:-5]: json.load(open(os.path.join(AXES_DIR, f)))
            for f in os.listdir(AXES_DIR) if f.endswith(".json")}


def cache_path(concept: str) -> str:
    key = hashlib.sha1(f"{concept}||{SELF_REPORT}".encode()).hexdigest()[:16]
    return os.path.join(CACHE, f"{key}.json")


def gen(concept: str) -> str:
    p = cache_path(concept)
    if os.path.exists(p):
        return json.load(open(p))["answer"]
    ans = wc.generate(concept, SELF_REPORT, max_tokens=96)
    os.makedirs(CACHE, exist_ok=True)
    json.dump({"concept": concept, "answer": ans}, open(p, "w"))
    return ans


def is_cached(concept: str) -> bool:
    return os.path.exists(cache_path(concept))


# ---- TF-IDF over the single-axis reference self-reports --------------------
def build_idf(docs: list[Counter]) -> dict[str, float]:
    n = len(docs)
    df: Counter = Counter()
    for d in docs:
        for t in d:
            df[t] += 1
    return {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}


def vec(c: Counter, idf: dict[str, float]) -> dict[str, float]:
    return {t: f * idf.get(t, 0.0) for t, f in c.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def sample_combos(axes: dict[str, list[str]], n: int) -> list[list[tuple[str, str]]]:
    rng = random.Random(SEED)
    names = sorted(axes)
    return [[(ax, rng.choice(axes[ax])) for ax in rng.sample(names, 4)] for _ in range(n)]


def all_values(axes):
    return [(ax, v) for ax in sorted(axes) for v in axes[ax]]


def generate_refs(axes) -> None:
    vals = all_values(axes)
    todo = [v for _, v in vals if not is_cached(v)]
    print(f"references: {len(vals)} single-axis values, {len(todo)} to generate", flush=True)
    for i, v in enumerate(todo, 1):
        gen(v)
        if i % 20 == 0 or i == len(todo):
            print(f"  refs {i}/{len(todo)}", flush=True)


def generate_samples(combos) -> None:
    todo = [c for c in combos if not is_cached("; ".join(v for _, v in c))]
    print(f"samples: {len(combos)} 4-axis combos, {len(todo)} to generate", flush=True)
    for i, c in enumerate(todo, 1):
        gen("; ".join(v for _, v in c))
        if i % 10 == 0 or i == len(todo):
            print(f"  samples {i}/{len(todo)}", flush=True)


def report(axes, combos) -> None:
    vals = all_values(axes)
    # build reference vectors (skip any missing)
    ref_docs, ref_meta = [], []
    for ax, v in vals:
        if is_cached(v):
            ref_docs.append(words(gen(v)))
            ref_meta.append((ax, v))
    idf = build_idf(ref_docs)
    ref_vecs = [vec(d, idf) for d in ref_docs]
    val_index = {v: i for i, (ax, v) in enumerate(ref_meta)}
    axis_of = {v: ax for ax, v in ref_meta}

    ranks_all = []          # rank of each true value among all 326 (per planted axis)
    own_axis_top1 = own_axis_n = 0   # true value beats other values of its OWN axis
    recall_at = {1: 0, 5: 0, 10: 0, 25: 0}
    ge1_top10 = 0
    n_combos = 0

    for combo in combos:
        concept = "; ".join(v for _, v in combo)
        if not is_cached(concept):
            continue
        n_combos += 1
        qv = vec(words(gen(concept)), idf)
        sims = [(cosine(qv, rv), i) for i, rv in enumerate(ref_vecs)]
        sims.sort(reverse=True)
        ranked_vals = [ref_meta[i][1] for _, i in sims]
        hit_top10 = False
        for ax, value in combo:
            if value not in val_index:
                continue
            r = ranked_vals.index(value)
            ranks_all.append(r)
            for k in recall_at:
                if r < k:
                    recall_at[k] += 1
            if r < 10:
                hit_top10 = True
            # own-axis discrimination: among only this axis's values, is the true one top?
            axis_vals = [(s, ref_meta[i][1]) for s, i in sims if axis_of.get(ref_meta[i][1]) == ax]
            axis_vals.sort(reverse=True)
            if axis_vals and axis_vals[0][1] == value:
                own_axis_top1 += 1
            own_axis_n += 1
        ge1_top10 += hit_top10

    n_planted = len(ranks_all)
    print("\n=== SELF-REPORT FINGERPRINT SIGNAL ===")
    print(f"combos scored: {n_combos} | planted-value observations: {n_planted} | references: {len(ref_meta)}")
    if not n_planted:
        return
    import statistics
    print(f"mean rank of true value among all {len(ref_meta)}: "
          f"{statistics.mean(ranks_all):.0f}  (chance ~{len(ref_meta)/2:.0f})")
    print(f"median rank: {statistics.median(ranks_all):.0f}")
    for k in (1, 5, 10, 25):
        chance = k / len(ref_meta)
        print(f"  recall@{k:<3}: {recall_at[k]/n_planted:.1%}   (chance {chance:.1%})")
    print(f"  >=1 of 4 planted values in top-10: {ge1_top10/n_combos:.0%}")
    print(f"  own-axis top-1 (true value beats its axis-mates): {own_axis_top1/own_axis_n:.0%}  "
          f"(chance varies ~6-9%)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs-only", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--samples", type=int, default=40)
    args = ap.parse_args()
    axes = load_axes()
    combos = sample_combos(axes, args.samples)
    if not args.report:
        generate_refs(axes)
        if not args.refs_only:
            generate_samples(combos)
    if not args.refs_only:
        report(axes, combos)


if __name__ == "__main__":
    main()
