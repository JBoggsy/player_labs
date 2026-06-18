"""Select the 3 best fingerprint probe questions (mentalist v6 — post-passphrase pivot).

The game dev will stop adding private probe answers to the scoring context, killing the
passphrase exploit. So all 3 private asks are now free for FINGERPRINTING, and we want 3
DIFFERENT free-response questions whose axis coverage is COMPLEMENTARY (union covers the
most axes), not 3 that all surface the same axes.

Method (Titan-embedding recovery, the winner from compare_matchers):
  * CANDIDATES: several free-response questions, each a different angle.
  * REFERENCES: a per-axis value sample (REFS_PER_AXIS each of 15 axes); for each candidate
    question, the judge steered by that value ALONE answers the question -> embed.
  * TEST: random 4-axis combos; for each candidate question, judge under the full combo
    answers -> embed.
  * RECOVERY: per (question, combo, true value): rank the value among all reference values
    by Titan cosine. Aggregate per-question recall@k AND per-question x per-axis recall.
  * SELECTION: report each question's per-axis coverage, then the best 3-question TRIPLE by
    union axis coverage (an axis is "covered" by the triple if ANY of its 3 questions
    recovers that axis's value in top-k often enough).

Cached + resumable (cache_qsel/ for gens, embed_cache/ shared with compare_matchers).
Usage: uv run --with boto3 --with numpy python probe_question_selection.py [--report]
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import random

import numpy as np

import worker_client as wc

wc.DEFAULT_URL = "https://cue-n-woo-fleet.softmax-research.net"

HERE = os.path.dirname(__file__)
AXES_DIR = os.path.join(HERE, "concept_axes")
CACHE = os.path.join(HERE, "cache_qsel")
EMBED_CACHE = os.path.join(HERE, "embed_cache")
TITAN = "amazon.titan-embed-text-v2:0"
SEED = 4242
REFS_PER_AXIS = 4     # sampled values per axis for the reference library
N_COMBOS = 30         # test 4-axis combos
TOPK = 10

# Candidate free-response probe questions — diverse angles to cover different axis families.
CANDIDATES = {
    "labels6":   "Start with exactly six comma-separated labels for the recurring lens your answers feel pulled toward.",
    "nouns_adj": "List three concrete nouns then three adjectives, comma-separated, for what feels most salient to you.",
    "scene":     "In two sentences, describe the setting, era, and atmosphere you feel most drawn to evoke.",
    "advice":    "What piece of advice about life would you most naturally give, and why?",
    "object":    "Name a single object that best captures your current voice, and describe it in one sentence.",
    "story":     "Write the first two sentences of a short story in your most natural voice.",
}


def load_axes() -> dict[str, list[str]]:
    return {f[:-5]: json.load(open(os.path.join(AXES_DIR, f)))
            for f in os.listdir(AXES_DIR) if f.endswith(".json")}


def cache_path(concept: str, qid: str) -> str:
    key = hashlib.sha1(f"{concept}||{qid}".encode()).hexdigest()[:16]
    return os.path.join(CACHE, f"{key}.json")


def gen(concept: str, qid: str) -> str:
    p = cache_path(concept, qid)
    if os.path.exists(p):
        return json.load(open(p))["answer"]
    ans = wc.generate(concept, CANDIDATES[qid], max_tokens=110)
    os.makedirs(CACHE, exist_ok=True)
    json.dump({"concept": concept, "qid": qid, "answer": ans}, open(p, "w"))
    return ans


def is_cached(concept: str, qid: str) -> bool:
    return os.path.exists(cache_path(concept, qid))


def titan_client():
    import boto3
    return boto3.Session(profile_name="softmax", region_name="us-east-1").client("bedrock-runtime")


def embed(text: str, client) -> np.ndarray:
    key = hashlib.sha1(("QSEL::" + text).encode()).hexdigest()[:20]
    path = os.path.join(EMBED_CACHE, f"{key}.json")
    if os.path.exists(path):
        v = np.asarray(json.load(open(path)), dtype=np.float32)
    else:
        body = json.dumps({"inputText": text or " "})
        r = client.invoke_model(modelId=TITAN, body=body)
        v = np.asarray(json.loads(r["body"].read())["embedding"], dtype=np.float32)
        os.makedirs(EMBED_CACHE, exist_ok=True)
        json.dump(v.tolist(), open(path, "w"))
    return v / (np.linalg.norm(v) + 1e-9)


def sample_refs(axes):
    rng = random.Random(SEED)
    return [(ax, v) for ax in sorted(axes) for v in rng.sample(axes[ax], min(REFS_PER_AXIS, len(axes[ax])))]


def sample_combos(axes, refs):
    """Combos drawn from the SAMPLED reference values (so the true value is recoverable)."""
    rng = random.Random(SEED + 1)
    by_axis = {}
    for ax, v in refs:
        by_axis.setdefault(ax, []).append(v)
    names = sorted(by_axis)
    out = []
    for _ in range(N_COMBOS):
        chosen = rng.sample(names, 4)
        out.append([(ax, rng.choice(by_axis[ax])) for ax in chosen])
    return out


def generate_all(axes):
    refs = sample_refs(axes)
    combos = sample_combos(axes, refs)
    work = []
    for qid in CANDIDATES:
        work += [(v, qid) for _, v in refs]
        work += [("; ".join(v for _, v in c), qid) for c in combos]
    todo = [(c, q) for c, q in work if not is_cached(c, q)]
    print(f"refs={len(refs)} combos={len(combos)} candidates={len(CANDIDATES)} "
          f"total={len(work)} todo={len(todo)}", flush=True)
    for i, (c, q) in enumerate(todo, 1):
        gen(c, q)
        if i % 20 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)}", flush=True)
    return refs, combos


def report(axes):
    refs = sample_refs(axes)
    combos = sample_combos(axes, refs)
    client = titan_client()

    # per-question: embed all refs + combos; compute per-axis recall@TOPK
    per_q_axis = {q: {} for q in CANDIDATES}   # qid -> axis -> [hits, n]
    per_q_overall = {}
    for qid in CANDIDATES:
        ref_vecs = np.vstack([embed(gen(v, qid), client) for _, v in refs])
        ref_axis = [ax for ax, _ in refs]
        ref_val = [v for _, v in refs]
        hits = n = 0
        axis_stat = {}
        for combo in combos:
            concept = "; ".join(v for _, v in combo)
            tv = embed(gen(concept, qid), client)
            sims = ref_vecs @ tv
            order = np.argsort(-sims)
            ranked = [ref_val[i] for i in order]
            for ax, value in combo:
                r = ranked.index(value)
                hit = r < TOPK
                hits += hit
                n += 1
                s = axis_stat.setdefault(ax, [0, 0])
                s[0] += hit
                s[1] += 1
        per_q_overall[qid] = hits / n
        per_q_axis[qid] = {ax: (s[0] / s[1]) for ax, s in axis_stat.items()}

    print("\n=== PER-QUESTION overall recall@%d ===" % TOPK)
    for qid in sorted(per_q_overall, key=lambda k: -per_q_overall[k]):
        print(f"  {qid:<12} {per_q_overall[qid]:.0%}")

    all_axes = sorted(axes)
    print("\n=== PER-QUESTION x PER-AXIS recall@%d (which axes each question surfaces) ===" % TOPK)
    print(f"  {'axis':<14}" + "".join(f"{q[:9]:>10}" for q in CANDIDATES))
    for ax in all_axes:
        print(f"  {ax:<14}" + "".join(f"{per_q_axis[q].get(ax, 0):>9.0%} " for q in CANDIDATES))

    # best TRIPLE by union axis coverage: an axis is covered if max over the 3 questions >= COVER
    COVER = 0.34
    def coverage(triple):
        c = 0
        for ax in all_axes:
            if max(per_q_axis[q].get(ax, 0) for q in triple) >= COVER:
                c += 1
        return c
    triples = list(itertools.combinations(CANDIDATES, 3))
    triples.sort(key=coverage, reverse=True)
    print(f"\n=== BEST 3-QUESTION TRIPLES by union axis coverage (axis covered if any q recall@{TOPK} >= {COVER:.0%}) ===")
    for t in triples[:5]:
        covered = [ax for ax in all_axes if max(per_q_axis[q].get(ax, 0) for q in t) >= COVER]
        print(f"  {t}: {coverage(t)}/{len(all_axes)} axes  -> {', '.join(covered)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    axes = load_axes()
    if not args.report:
        generate_all(axes)
    report(axes)


if __name__ == "__main__":
    main()
