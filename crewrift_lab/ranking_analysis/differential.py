#!/usr/bin/env python3
"""Differential analysis: which behavioral features most distinguish crewborg
from the TOP-3 policies, separately for crew and imposter. Reports effect size
(Cohen's d) + Mann-Whitney U p-value, ranked by |effect|. NO causal claims."""
from __future__ import annotations
import json
import numpy as np
import os
from pathlib import Path
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("RANK_DATA", HERE / "data"))
F = os.environ.get("RANK_FEATURES", str(DATA / "features.json"))
OUT = os.environ.get("RANK_DIFFERENTIAL_OUT", str(DATA / "differential.json"))
df = pd.read_json(F)

# top-3 by clean-game role win rate (from the ranking)
TOP = {
    "crew": ["crewborg-mv", "scott-crewborg-hs1", "forgeling-focusfire"],
    "imposter": ["crewrift-prime-crewborg-aaln-hunter-relhalpha", "jordan-crewborg-aaln", "sasmith-crewborg-hs1"],
}
FEATURES = {
    "crew": ["win", "tasks", "tasks_while_dead", "chats", "chatted", "votes_player",
             "voted", "votes_skip", "meetings_called", "rooms_visited", "got_killed",
             "ghost_move_latency", "got_trailed", "isolations"],
    "imposter": ["win", "kills", "chats", "chatted", "suss_chats", "votes_player", "voted",
                 "first_kill_tick", "witnesses_per_kill", "follows", "chases",
                 "rooms_visited", "got_killed", "isolations", "meetings_called"],
}

def cohend(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2: return float("nan")
    sp = np.sqrt(((na-1)*a.var(ddof=1) + (nb-1)*b.var(ddof=1)) / (na+nb-2))
    return (a.mean() - b.mean())/sp if sp > 0 else 0.0

results = {}
for role in ("crew", "imposter"):
    sub = df[df.role == role]
    me = sub[sub.policy_name == "crewborg"]
    top = sub[sub.policy_name.isin(TOP[role])]
    rows = []
    for feat in FEATURES[role]:
        a = me[feat].dropna().values
        b = top[feat].dropna().values
        if len(a) < 5 or len(b) < 5:
            continue
        d = cohend(a, b)
        try:
            u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        except ValueError:
            p = float("nan")
        rows.append({
            "feature": feat, "crewborg_mean": float(np.mean(a)), "top3_mean": float(np.mean(b)),
            "crewborg_n": int(len(a)), "top3_n": int(len(b)),
            "cohen_d": float(d), "p": float(p),
            "direction": "crewborg HIGHER" if np.mean(a) > np.mean(b) else "crewborg LOWER",
        })
    rows.sort(key=lambda r: -abs(r["cohen_d"]))
    results[role] = rows

json.dump(results, open(OUT, "w"), indent=2)

for role in ("crew", "imposter"):
    print(f"\n{'='*78}\n{role.upper()}: crewborg vs top-3 ({', '.join(TOP[role])})\n{'='*78}")
    print(f"{'feature':22s} {'crewborg':>10} {'top3':>10} {'Δ%':>7} {'d':>6} {'p':>9}  flag")
    for r in results[role]:
        cb, t3 = r["crewborg_mean"], r["top3_mean"]
        dpct = (cb-t3)/t3*100 if t3 else float('nan')
        sig = "***" if r["p"] < 0.001 else "**" if r["p"] < 0.01 else "*" if r["p"] < 0.05 else ""
        big = " <<<" if abs(r["cohen_d"]) >= 0.3 else ""
        print(f"{r['feature']:22s} {cb:10.3f} {t3:10.3f} {dpct:+6.0f}% {r['cohen_d']:+6.2f} {r['p']:9.2e}  {sig}{big}")
