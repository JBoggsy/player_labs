"""Fingerprinting effectiveness report — v6 (full 3-question dataset, shipped method).

Measures the ACTUAL shipped v6 fingerprinter: match a 4-axis combo's 3 probe answers
(labels6 + nouns_adj + object) against the full 978-row reference matrix (326 values x 3
questions), question-to-question, exactly as mentalist_v4/fingerprint.py does at runtime.

Test set: the 30 4-axis combos from the question-selection probe (cache_qsel/), each with
all 3 probe answers cached. References: the shipped matrix the player ships.

Stats: recall@k vs chance (binomial p), mean rank vs null (permutation p), MRR, per-axis
recall@10 with Wilson CI, per-value influence, axis-vs-value variance, within-axis
discrimination, rank distribution, a worked example. Writes HTML (lab broadsheet) + JSON.

Usage: uv run --with boto3 --with numpy --with scikit-learn python fingerprint_report_v6.py -o out.html
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import random
import sys
from collections import defaultdict

import numpy as np

import probe_question_selection as Q

# import the SHIPPED fingerprinter so the report measures exactly what the player does
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
from mentalist_v4.fingerprint import Fingerprinter  # noqa: E402

CHOSEN = ["labels6", "nouns_adj", "object"]


def _all_cached_combos(axes):
    """Every cached 4-axis combo that has all 3 chosen questions, parsed back to (axis,value).

    Combos come from multiple generation runs (qsel + the extra-combo run); we recover the
    axis of each value by membership so the report uses ALL available 3-question test data.
    """
    import glob
    val_to_axis = {v: ax for ax in axes for v in axes[ax]}
    have = defaultdict(set)
    for f in glob.glob(os.path.join(Q.CACHE, "*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        have[d["concept"]].add(d["qid"])
    combos = []
    for concept, qs in have.items():
        if concept.count(";") != 3 or not set(CHOSEN) <= qs:
            continue
        vals = [p.strip() for p in concept.split(";")]
        if all(v in val_to_axis for v in vals):
            combos.append([(val_to_axis[v], v) for v in vals])
    return combos


def compute():
    axes = Q.load_axes()
    combos = _all_cached_combos(axes)

    fp = Fingerprinter()  # loads the shipped 978-row matrix; uses Titan (cached embeds)
    if not fp.ready:
        sys.exit("reference matrix not found — run build_v6_references.py first")
    N_values = len(set(fp._values))

    obs = []
    combo_best = []   # per combo: the BEST (lowest) rank achieved across its 4 planted values
    examples = []
    for combo in combos:
        concept = "; ".join(v for _, v in combo)
        answers = {q: Q.gen(concept, q) for q in CHOSEN}
        result = fp.identify(answers)
        ranked = _full_ranking(fp, answers)
        ranking = [g.value for g in ranked]
        ranked_axis = {g.value: g.axis for g in ranked}
        planted = [v for _, v in combo]
        combo_ranks = []
        for ax, value in combo:
            if value in ranking:
                r = ranking.index(value)
                same = [v for v in ranking if ranked_axis[v] == ax]
                obs.append({"axis": ax, "value": value, "rank": r,
                            "rank_axis_only": same.index(value)})
                combo_ranks.append(r)
        if combo_ranks:
            combo_best.append(min(combo_ranks))   # best of the 4 — our real success metric
        if len(examples) < 8:
            examples.append({"concept": concept, "answers": answers,
                             "top": [(g.value, g.axis) for g in result.guesses[:6]],
                             "planted": planted})
    return {"N": N_values, "obs": obs, "axes": axes, "n_combos": len(combos),
            "combo_best": combo_best, "examples": examples}


def _full_ranking(fp: Fingerprinter, answers: dict):
    """Reproduce the fingerprinter's per-value aggregate, return ALL values ranked desc."""
    value_scores = defaultdict(list)
    value_axis = {}
    for qid, ans in answers.items():
        sims, _ = fp._score_one(qid, ans)
        if sims is None:
            continue
        rows = fp._rows_for_question(qid)
        for ridx, sim in zip(rows, sims):
            value_scores[fp._values[ridx]].append(float(sim))
            value_axis[fp._values[ridx]] = fp._axes[ridx]
    agg = {v: sum(s) / len(s) for v, s in value_scores.items()}
    from mentalist_v4.fingerprint import AxisGuess
    ranked = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
    return [AxisGuess(axis=value_axis[v], value=v, score=s, margin=0.0) for v, s in ranked]


# ---- stats (shared with the v1 report) ----
def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def binom_sf(k, n, p):
    from math import comb
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def analyze(data):
    N, obs, axes = data["N"], data["obs"], data["axes"]
    n = len(obs)
    ranks = np.array([o["rank"] for o in obs])
    overall = {}
    for k in (1, 5, 10, 25, 50):
        hits = int((ranks < k).sum())
        chance = k / N
        overall[k] = {"recall": hits / n, "chance": chance, "ci": wilson(hits, n),
                      "p": binom_sf(hits, n, chance), "lift": (hits / n) / chance if chance else 0}
    mrr = float(np.mean(1.0 / (ranks + 1)))
    mean_rank, median_rank = float(ranks.mean()), float(np.median(ranks))
    rng = random.Random(0)
    null = np.array([np.mean([rng.randrange(N) for _ in range(n)]) for _ in range(2000)])
    perm_p = float((null <= mean_rank).mean())

    by_axis = defaultdict(list)
    for o in obs:
        by_axis[o["axis"]].append(o["rank"])
    axis_stats = []
    for ax, rs in by_axis.items():
        rs = np.array(rs)
        hits = int((rs < 10).sum())
        axis_stats.append({"axis": ax, "n": len(rs), "recall10": hits / len(rs),
                           "ci": wilson(hits, len(rs)), "mean_rank": float(rs.mean()),
                           "n_values": len(axes[ax])})
    axis_stats.sort(key=lambda a: a["recall10"], reverse=True)

    by_val = defaultdict(list)
    for o in obs:
        by_val[(o["axis"], o["value"])].append(o["rank"])
    val_stats = [{"axis": ax, "value": v, "n": len(rs), "mean_rank": float(np.mean(rs))}
                 for (ax, v), rs in by_val.items()]
    val_stats.sort(key=lambda x: x["mean_rank"])

    grand = ranks.mean()
    ss_tot = float(((ranks - grand) ** 2).sum())
    ss_axis = sum(len(rs) * (np.mean(rs) - grand) ** 2 for rs in by_axis.values())
    eta2 = ss_axis / ss_tot if ss_tot else 0.0
    own_top1 = float((np.array([o["rank_axis_only"] for o in obs]) == 0).mean())

    # THE SUCCESS METRIC: P(recover >=1 of the 4 axes) at each threshold, per combo.
    cb = np.array(data.get("combo_best", []))
    n_combos_scored = len(cb)
    any_hit = {}
    for k in (1, 5, 10, 25):
        hits = int((cb < k).sum()) if n_combos_scored else 0
        # chance that >=1 of 4 independent picks lands in top-k: 1-(1-k/N)^4
        chance = 1 - (1 - k / N) ** 4
        any_hit[k] = {"rate": hits / n_combos_scored if n_combos_scored else 0,
                      "hits": hits, "n": n_combos_scored,
                      "ci": wilson(hits, n_combos_scored), "chance": chance,
                      "p": binom_sf(hits, n_combos_scored, chance) if n_combos_scored else 1.0}

    return {"N": N, "n_obs": n, "n_combos": data["n_combos"], "overall": overall, "mrr": mrr,
            "mean_rank": mean_rank, "median_rank": median_rank, "perm_p": perm_p,
            "axis_stats": axis_stats, "val_stats": val_stats, "eta2_axis": eta2,
            "own_axis_top1": own_top1,
            "rank_hist": np.histogram(ranks, bins=[0, 1, 5, 10, 25, 50, 100, N])[0].tolist(),
            "any_hit": any_hit, "n_combos_scored": n_combos_scored,
            "examples": data.get("examples", [])}


# ---- reuse the renderer from the v1 report ----
import fingerprint_report as R  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="/tmp/fingerprint_report_v6.html")
    args = ap.parse_args()
    data = compute()
    a = analyze(data)
    # adapt example shape to the v1 renderer (self_report from the 3 answers)
    for e in a["examples"]:
        e["self_report"] = " | ".join(f"{q}: {t}" for q, t in e["answers"].items())[:300]
        e["top6"] = e["top"]
        e["recovered"] = [v for v, _ in e["top"] if v in e["planted"]]
    open(args.out, "w").write(R.render_html(a))
    json.dump({k: v for k, v in a.items() if k != "examples"},
              open(args.out.replace(".html", ".json"), "w"), indent=2, default=float)
    print(f"wrote {args.out}")
    print(f"[v6 3-question] recall@10={a['overall'][10]['recall']:.0%} "
          f"(lift {a['overall'][10]['lift']:.0f}x, p={a['overall'][10]['p']:.2g}) | "
          f"mean rank {a['mean_rank']:.0f}/{a['N']} | own-axis top1 {a['own_axis_top1']:.0%}")
    print("most:", ", ".join(f"{s['axis']} {s['recall10']:.0%}" for s in a["axis_stats"][:4]))
    print("least:", ", ".join(f"{s['axis']} {s['recall10']:.0%}" for s in a["axis_stats"][-4:]))


if __name__ == "__main__":
    main()
