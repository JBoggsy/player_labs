"""Can we BIN axis values into a small identifiable set? (mentalist v4 pivot, 2026-06-15)

probe_axis_recovery.py established that recovering the EXACT axis value from 3
judge answers is at chance (top-1 ~7-13% vs 5% chance, mean norm-rank ~0.42).
This asks the course-correction question: many axis values are probably very
similar (register={terse,clinical,technical} vs {poetic,theatrical,devotional}).
If values that PRODUCE similar judge text are binned together, can we at least
identify the BIN -- a small candidate set -- even when we can't pick the exact
value? Bin-level identification, if it works, is enough to bias the writer.

All three analyses run on the EXISTING cache (no new worker calls):

  A. TF-IDF fairness recheck -- redo exact-value recovery with TF-IDF cosine
     (the recovery probe used raw token counts; the production classifier uses
     TF-IDF). Rules out "we just measured a bad featurizer."
  B. Binning test -- cluster each axis's value-fingerprints into K bins, then
     measure BIN-level recovery from blended test draws vs the by-chance rate.
     The honest metric: does bin-recovery beat value-recovery enough to matter?
  C. Coherence -- print example bins so a human can judge if they're sensible.

Run:  uv run python probe_axis_binning.py [--k 4]
"""
from __future__ import annotations

import argparse

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import probe_axis_recovery as P


def answers_text(concept_text: str) -> str:
    """The judge's 3 cached answers for a concept, concatenated."""
    return "\n".join(P.cached_generate(concept_text, q) for q in range(len(P.QUESTIONS)))


def build_corpus(axes: dict[str, list[str]]):
    """TF-IDF over all single-axis reference docs (one per value, all axes)."""
    ref_values, ref_axis, ref_docs = [], [], []
    for ax in P.TESTED_AXES:
        for v in axes[ax]:
            ref_values.append(v)
            ref_axis.append(ax)
            ref_docs.append(answers_text(v))
    # char n-grams capture style; word also helps. Use word + char blend via two
    # vectorizers would complicate cosine; word(1,2) is a fair, strong default.
    vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    ref_mat = vec.fit_transform(ref_docs)
    return vec, ref_values, ref_axis, ref_mat


def all_cached(concept_text: str) -> bool:
    return all(P.is_cached(concept_text, q) for q in range(len(P.QUESTIONS)))


def analysis_a_value_recovery(axes, vec, ref_values, ref_axis, ref_mat, draws):
    """Exact-value recovery with TF-IDF cosine (fairness recheck)."""
    print("\n=== A. EXACT-VALUE recovery, TF-IDF cosine (fairness recheck) ===")
    idx_by_axis = {ax: [i for i, a in enumerate(ref_axis) if a == ax] for ax in P.TESTED_AXES}
    t1 = t3 = n = 0
    chance1 = 0.0
    for d in draws:
        if not all_cached(d["concept_text"]):
            continue
        ax = d["tested_axis"]
        cols = idx_by_axis[ax]
        test = vec.transform([answers_text(d["concept_text"])])
        sims = cosine_similarity(test, ref_mat[cols])[0]
        order = np.argsort(-sims)
        ranked_vals = [ref_values[cols[j]] for j in order]
        r = ranked_vals.index(d["true_value"])
        n += 1
        t1 += r == 0
        t3 += r < 3
        chance1 += 1.0 / len(cols)
    print(f"  n={n}  top1={t1/n:.0%} (chance {chance1/n:.0%})  top3={t3/n:.0%}")
    return t1 / n


def analysis_b_binning(axes, vec, ref_values, ref_axis, ref_mat, draws, k):
    """Bin each axis's values by fingerprint; measure bin-level recovery."""
    print(f"\n=== B. BIN-level recovery (K={k} bins per axis) ===")
    print(f"  {'axis':<12} {'#v':>3} {'binrec':>7} {'chance':>7} {'lift':>6}")
    idx_by_axis = {ax: [i for i, a in enumerate(ref_axis) if a == ax] for ax in P.TESTED_AXES}
    bins_by_axis = {}
    agg_hit = agg_n = 0
    agg_chance = 0.0
    for ax in P.TESTED_AXES:
        cols = idx_by_axis[ax]
        m = len(cols)
        kk = min(k, m)
        sub = ref_mat[cols].toarray()
        labels = AgglomerativeClustering(n_clusters=kk, metric="cosine", linkage="average").fit_predict(sub)
        value_bin = {ref_values[cols[j]]: int(labels[j]) for j in range(m)}
        # bin centroids in TF-IDF space
        centroids = np.vstack([sub[labels == b].mean(axis=0) for b in range(kk)])
        bins_by_axis[ax] = (value_bin, labels, cols)
        # chance: weighted by bin sizes (prob a random draw's bin == predicted-by-prior bin)
        sizes = np.array([(labels == b).sum() for b in range(kk)], dtype=float)
        chance = float((sizes / m) ** 2 @ np.ones(kk))  # sum (size/m)^2
        # bin recovery on test draws
        hit = n = 0
        for d in draws:
            if d["tested_axis"] != ax or not all_cached(d["concept_text"]):
                continue
            test = vec.transform([answers_text(d["concept_text"])]).toarray()
            pred_bin = int(np.argmax(cosine_similarity(test, centroids)[0]))
            true_bin = value_bin[d["true_value"]]
            hit += pred_bin == true_bin
            n += 1
        agg_hit += hit
        agg_n += n
        agg_chance += chance * n
        rec = hit / n if n else 0.0
        lift = rec - chance
        print(f"  {ax:<12} {m:>3} {rec:>6.0%} {chance:>6.0%} {lift:>+6.0%}")
    print(f"  {'AGGREGATE':<12} {'':>3} {agg_hit/agg_n:>6.0%} {agg_chance/agg_n:>6.0%} "
          f"{agg_hit/agg_n - agg_chance/agg_n:>+6.0%}   (n={agg_n})")
    return bins_by_axis


def analysis_c_coherence(axes, bins_by_axis, show_axes):
    """Print example bins so a human can judge semantic coherence."""
    print("\n=== C. Example bins (are similar concepts grouped sensibly?) ===")
    for ax in show_axes:
        value_bin, labels, cols = bins_by_axis[ax]
        kk = max(value_bin.values()) + 1
        print(f"\n  [{ax}]  {len(value_bin)} values -> {kk} bins:")
        for b in range(kk):
            members = [v for v, bb in value_bin.items() if bb == b]
            print(f"    bin {b}: " + ", ".join(members))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=4, help="bins per axis")
    args = ap.parse_args()
    axes = P.load_axes()
    draws = P.build_test_draws(axes)
    vec, ref_values, ref_axis, ref_mat = build_corpus(axes)

    analysis_a_value_recovery(axes, vec, ref_values, ref_axis, ref_mat, draws)
    bins = analysis_b_binning(axes, vec, ref_values, ref_axis, ref_mat, draws, args.k)
    analysis_c_coherence(axes, bins, show_axes=["register", "object", "domain"])


if __name__ == "__main__":
    main()
