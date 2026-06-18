"""Compare fingerprint matchers on the SAME cached self-reports (no new judge calls).

probe_selfreport_v2 measured word-TF-IDF cosine: recall@10=17%, >=1-in-top10=55%.
That is a LEXICAL lower bound -- "frontier town" self-reports as "rural/small towns"
while a frontier combo says "field research/bioregionalism" (semantically close,
lexically divergent). This harness re-scores the identical cached data with:

  * word_tfidf  -- the v2 baseline (word 1-2 grams, TF-IDF cosine)
  * char_tfidf  -- char 3-5 gram TF-IDF (catches morphology: frontier/frontiers)
  * titan_embed -- AWS Bedrock Titan v2 text embeddings, cosine (SEMANTIC)

Titan embeddings are cached to embed_cache/ (one cheap API call per distinct text,
not per pair). Reuses probe_selfreport_v2's concept sampling + cache so the
reference/sample sets are byte-identical to the measured run.

Usage: uv run --with boto3 python compare_matchers.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import probe_selfreport_v2 as P

HERE = os.path.dirname(__file__)
EMBED_CACHE = os.path.join(HERE, "embed_cache")
TITAN_MODEL = "amazon.titan-embed-text-v2:0"
SAMPLES = 40


# ---------- Titan embeddings (cached per text) ----------
def _titan_client():
    import boto3
    return boto3.Session(profile_name="softmax", region_name="us-east-1").client("bedrock-runtime")


def titan_embed(text: str, client) -> list[float]:
    key = hashlib.sha1(text.encode()).hexdigest()[:20]
    path = os.path.join(EMBED_CACHE, f"{key}.json")
    if os.path.exists(path):
        return json.load(open(path))
    body = json.dumps({"inputText": text or " "})
    r = client.invoke_model(modelId=TITAN_MODEL, body=body)
    vec = json.loads(r["body"].read())["embedding"]
    os.makedirs(EMBED_CACHE, exist_ok=True)
    json.dump(vec, open(path, "w"))
    return vec


# ---------- shared data ----------
def load_data():
    axes = P.load_axes()
    refs = [(ax, v) for ax in sorted(axes) for v in axes[ax] if P.is_cached(v)]
    combos = []
    for combo in P.sample_combos(axes, SAMPLES):
        concept = "; ".join(v for _, v in combo)
        if P.is_cached(concept):
            combos.append((combo, concept))
    ref_texts = [P.gen(v) for _, v in refs]            # cached self-reports (refs)
    return refs, ref_texts, combos


def recall_report(name, rank_lists, n_refs):
    """rank_lists: list of (rank_of_true_value) for each planted observation."""
    n = len(rank_lists)
    out = {}
    for k in (1, 5, 10, 25):
        out[k] = sum(1 for r in rank_lists if r < k) / n
    return out


def score_matcher(name, sim_fn, refs, combos):
    """sim_fn(combo_concept) -> list of sims aligned to refs. Returns rank stats."""
    ranks = []
    ge1_top10 = 0
    for combo, concept in combos:
        sims = sim_fn(concept)
        order = np.argsort(-np.asarray(sims))
        ranked_vals = [refs[i][1] for i in order]
        hit10 = False
        for _, value in combo:
            if value in ranked_vals:
                r = ranked_vals.index(value)
                ranks.append(r)
                if r < 10:
                    hit10 = True
        ge1_top10 += hit10
    rc = recall_report(name, ranks, len(refs))
    mean_rank = sum(ranks) / len(ranks)
    print(f"\n{name}:")
    print(f"  recall@1={rc[1]:.1%}  @5={rc[5]:.1%}  @10={rc[10]:.1%}  @25={rc[25]:.1%}")
    print(f"  mean rank={mean_rank:.0f}/{len(refs)}  | >=1 of 4 in top-10: {ge1_top10/len(combos):.0%}")
    return rc, ge1_top10 / len(combos)


def main():
    refs, ref_texts, combos = load_data()
    print(f"refs={len(refs)}  combos={len(combos)}  (chance recall@10 ~ {10/len(refs):.1%})")

    # --- word TF-IDF (baseline) ---
    wv = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True)
    wmat = wv.fit_transform(ref_texts)
    def word_sim(concept):
        return cosine_similarity(wv.transform([P.gen(concept)]), wmat)[0]
    score_matcher("word_tfidf (v2 baseline)", word_sim, refs, combos)

    # --- char TF-IDF ---
    cv = TfidfVectorizer(lowercase=True, analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    cmat = cv.fit_transform(ref_texts)
    def char_sim(concept):
        return cosine_similarity(cv.transform([P.gen(concept)]), cmat)[0]
    score_matcher("char_tfidf (3-5 gram)", char_sim, refs, combos)

    # --- Titan embeddings (semantic) ---
    client = _titan_client()
    print(f"\nembedding {len(ref_texts)} refs + {len(combos)} combos via Titan (cached)...", flush=True)
    ref_emb = np.array([titan_embed(t, client) for t in ref_texts])
    ref_emb /= np.linalg.norm(ref_emb, axis=1, keepdims=True) + 1e-9
    combo_emb = {}
    for combo, concept in combos:
        e = np.array(titan_embed(P.gen(concept), client))
        combo_emb[concept] = e / (np.linalg.norm(e) + 1e-9)
    def titan_sim(concept):
        return ref_emb @ combo_emb[concept]
    score_matcher("titan_embed (SEMANTIC)", titan_sim, refs, combos)


if __name__ == "__main__":
    main()
