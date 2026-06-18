"""Build the FULL v6 reference matrix: all 326 axis-values x 3 chosen probe questions.

The shipped v6 fingerprinter compares the judge's answers to the 3 probe questions
(labels6, nouns_adj, object) against single-axis reference fingerprints for EVERY value
of EVERY axis. This generates those references (single-axis steering, one answer per
(value, question)), embeds each with Titan, and writes the matrix the player ships.

Reuses cache_qsel/ (the question-selection probe already cached the 4/axis sample for
these same 3 questions) and embed_cache/. ~326 values x 3 questions = 978 gens, minus
whatever's cached.

Output: mentalist_v4/data/axis_reference_embeddings.npz with arrays
  vectors [N,1024] (L2-normed Titan), axes [N], values [N], questions [N], texts [N]
where N = 326 values x 3 questions = 978 rows. The fingerprinter pools the 3 per value.

Usage: uv run --with boto3 --with numpy python build_v6_references.py [--gen-only]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

import numpy as np

import worker_client as wc

wc.DEFAULT_URL = "https://cue-n-woo-fleet.softmax-research.net"

HERE = os.path.dirname(__file__)
AXES_DIR = os.path.join(HERE, "concept_axes")
CACHE = os.path.join(HERE, "cache_qsel")   # shared with the question-selection probe
EMBED_CACHE = os.path.join(HERE, "embed_cache")
TITAN = "amazon.titan-embed-text-v2:0"
OUT = os.path.normpath(os.path.join(HERE, "..", "mentalist_v4", "data", "axis_reference_embeddings.npz"))

# The chosen 3 (must match probe_question_selection.CANDIDATES ids + the player's interview).
QUESTIONS = {
    "labels6":   "Start with exactly six comma-separated labels for the recurring lens your answers feel pulled toward.",
    "nouns_adj": "List three concrete nouns then three adjectives, comma-separated, for what feels most salient to you.",
    "object":    "Name a single object that best captures your current voice, and describe it in one sentence.",
}


def load_axes() -> dict[str, list[str]]:
    return {f[:-5]: json.load(open(os.path.join(AXES_DIR, f)))
            for f in os.listdir(AXES_DIR) if f.endswith(".json")}


def cache_path(concept: str, qid: str) -> str:
    # identical keying to probe_question_selection.gen so cached samples are reused
    key = hashlib.sha1(f"{concept}||{qid}".encode()).hexdigest()[:16]
    return os.path.join(CACHE, f"{key}.json")


def gen(concept: str, qid: str) -> str:
    p = cache_path(concept, qid)
    if os.path.exists(p):
        return json.load(open(p))["answer"]
    ans = wc.generate(concept, QUESTIONS[qid], max_tokens=110)
    os.makedirs(CACHE, exist_ok=True)
    json.dump({"concept": concept, "qid": qid, "answer": ans}, open(p, "w"))
    return ans


def is_cached(concept: str, qid: str) -> bool:
    return os.path.exists(cache_path(concept, qid))


def rows(axes):
    return [(ax, v, qid) for ax in sorted(axes) for v in axes[ax] for qid in QUESTIONS]


def generate_all(axes):
    todo = [(v, qid) for ax, v, qid in rows(axes) if not is_cached(v, qid)]
    print(f"values={sum(len(v) for v in axes.values())} questions={len(QUESTIONS)} "
          f"total={len(rows(axes))} todo={len(todo)}", flush=True)
    for i, (v, qid) in enumerate(todo, 1):
        gen(v, qid)
        if i % 20 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)}", flush=True)


def titan_client():
    import boto3
    return boto3.Session(profile_name="softmax", region_name="us-east-1").client("bedrock-runtime")


def embed(text: str, client) -> np.ndarray:
    key = hashlib.sha1(("QSEL::" + text).encode()).hexdigest()[:20]  # same key as qsel embeds
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


def build_matrix(axes):
    client = titan_client()
    vecs, axn, vals, qs, texts = [], [], [], [], []
    allrows = rows(axes)
    for i, (ax, v, qid) in enumerate(allrows, 1):
        text = gen(v, qid)
        vecs.append(embed(text, client))
        axn.append(ax); vals.append(v); qs.append(qid); texts.append(text)
        if i % 100 == 0 or i == len(allrows):
            print(f"  embedded {i}/{len(allrows)}", flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    np.savez_compressed(OUT, vectors=np.vstack(vecs).astype(np.float32),
                        axes=np.array(axn), values=np.array(vals),
                        questions=np.array(qs), texts=np.array(texts))
    print(f"wrote {OUT}  ({len(allrows)} rows = {len(allrows)//len(QUESTIONS)} values x {len(QUESTIONS)} questions)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-only", action="store_true", help="generate self-reports, skip embedding/matrix")
    args = ap.parse_args()
    axes = load_axes()
    generate_all(axes)
    if not args.gen_only:
        build_matrix(axes)


if __name__ == "__main__":
    main()
