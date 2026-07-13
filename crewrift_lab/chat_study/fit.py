#!/usr/bin/env python
"""Stage 3 — compute the persuasion label and fit readable models.

Two questions, two models, each split by speaker role (crew vs imposter):

  A. SUSPICION DRAWN — after this message, do votes shift onto THE SPEAKER?
       label = (votes against speaker after the msg) > (before), within the meeting.
       (columns from stage 1: lbl_votes_against_speaker_before/after)

  B. PERSUASION — after this message, do votes shift onto the player the speaker ACCUSED?
       Computed here from votes.parquet: for a chat that named ``accused_color`` (stage 2),
       label = (votes against that color after the msg) > (before), within the meeting.
       Only defined for messages that accused someone.

Features = symbolic (f_*) + LLM-semantic (s_*). Model = L2 logistic regression with
standardized features so coefficients are comparable; we report the coefficients (the
whole point — what draws suspicion / what persuades), with group-CV AUC as a sanity check
that the signal is real, not the goal.

Output: ``models/report.md`` + ``models/coeffs.json``. Idempotent.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

# CONTROLS: timing/position mechanically bound how many votes can still move after a
# message (a late message has few votes left to shift), which otherwise swamps the content
# signal. We keep them IN the model as explicit controls so the content coefficients are
# read "holding timing fixed", but we report them separately from the actionable features.
CONTROLS = ["f_latency_ticks", "f_speak_order", "f_votes_remaining"]
SYMBOLIC = [
    "f_first_speaker", "f_word_count",
    "f_is_question", "f_names_color", "f_self_reference", "f_says_vote", "f_says_sus",
]
SEMANTIC = [
    "s_accuses", "s_provides_evidence", "s_defends_self",
    "s_asks_question", "s_vouches", "s_bandwagons",
]


def persuasion_label(chats: pd.DataFrame, votes: pd.DataFrame) -> pd.Series:
    """For each chat that accused a color, did votes against that color rise after the msg?"""
    by_color: dict[tuple, list[int]] = defaultdict(list)
    for r in votes.itertuples():
        if r.target_color is not None:
            by_color[(r.episode_id, r.meeting_idx, r.target_color)].append(int(r.ts))
    for k in by_color:
        by_color[k].sort()

    out = []
    for r in chats.itertuples():
        tgt = r.accused_color
        if not tgt:
            out.append(np.nan)
            continue
        seq = by_color.get((r.episode_id, r.meeting_idx, tgt))
        if not seq:
            out.append(0)  # named a target, but that color drew no votes at all
            continue
        cut = bisect.bisect_right(seq, r.ts)
        before, after = cut, len(seq) - cut
        out.append(1 if after > before else 0)
    return pd.Series(out, index=chats.index)


def fit_one(df: pd.DataFrame, features: list[str], controls: list[str], label: str, groups: pd.Series) -> dict:
    """Fit a standardized L2 logit over features+controls; return coefficients (tagged
    control vs actionable) + group-CV AUC. Controls absorb timing so the content
    coefficients read 'holding when-in-the-meeting fixed'."""
    all_feats = features + controls
    d = df.dropna(subset=[label]).copy()
    X = d[all_feats].astype(float).values
    y = d[label].astype(int).values
    g = groups.loc[d.index].values
    if len(d) < 50 or y.min() == y.max():
        return {"n": int(len(d)), "positive_rate": float(y.mean()) if len(d) else 0.0, "skipped": "degenerate"}

    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    model = LogisticRegression(penalty="l2", C=1.0, max_iter=2000).fit(Xs, y)

    aucs = []
    n_splits = min(5, len(np.unique(g)))
    if n_splits >= 2:
        for tr, te in GroupKFold(n_splits=n_splits).split(Xs, y, g):
            if len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2:
                continue
            m = LogisticRegression(penalty="l2", C=1.0, max_iter=2000).fit(Xs[tr], y[tr])
            aucs.append(roc_auc_score(y[te], m.predict_proba(Xs[te])[:, 1]))

    ctrl = set(controls)
    coeffs = sorted(
        ({"feature": f, "coef": float(c), "control": f in ctrl} for f, c in zip(all_feats, model.coef_[0])),
        key=lambda x: -abs(x["coef"]),
    )
    return {
        "n": int(len(d)),
        "positive_rate": round(float(y.mean()), 3),
        "cv_auc": round(float(np.mean(aucs)), 3) if aucs else None,
        "coeffs": coeffs,
    }


def render(results: dict, out_dir: Path) -> None:
    lines = ["# Chat-persuasion study — what draws suspicion vs. persuades", ""]
    lines.append("Standardized L2-logit coefficients (per 1 SD; + = raises the outcome). "
                 "`cv_auc` is a meeting-grouped sanity check, not the goal.\n")
    for qkey, qtitle in [("suspicion", "A. SUSPICION DRAWN onto the speaker"),
                         ("persuasion", "B. PERSUASION — votes moved onto the accused target")]:
        lines.append(f"## {qtitle}\n")
        for role in ["crew", "imposter"]:
            r = results.get(qkey, {}).get(role)
            if not r:
                continue
            if r.get("skipped"):
                lines.append(f"### {role} — SKIPPED ({r['skipped']}, n={r['n']})\n")
                continue
            lines.append(f"### {role}  (n={r['n']}, base rate={r['positive_rate']}, cv_auc={r['cv_auc']})\n")
            lines.append("| feature | coef | |")
            lines.append("| --- | ---: | --- |")
            for c in r["coeffs"]:
                tag = "_(timing control)_" if c.get("control") else ""
                lines.append(f"| {c['feature']} | {c['coef']:+.3f} | {tag} |")
            lines.append("")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.md").write_text("\n".join(lines))
    (out_dir / "coeffs.json").write_text(json.dumps(results, indent=2))
    print("\n".join(lines))
    print(f"\nwrote {out_dir/'report.md'} + coeffs.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path(__file__).parent / "dataset")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "models")
    args = ap.parse_args()

    chats = pd.read_parquet(args.dataset / "chats_labeled.parquet")
    votes = pd.read_parquet(args.dataset / "votes.parquet")

    chats["suspicion"] = (
        chats["lbl_votes_against_speaker_after"] > chats["lbl_votes_against_speaker_before"]
    ).astype(int)
    chats["persuasion"] = persuasion_label(chats, votes)
    chats["meeting_key"] = chats["episode_id"] + ":" + chats["meeting_idx"].astype(str)

    # f_votes_remaining: how many votes were cast in this meeting AFTER the message — the
    # timing control that bounds how much either label can still move.
    vote_ts_by_meeting: dict[tuple, list[int]] = defaultdict(list)
    for r in votes.itertuples():
        vote_ts_by_meeting[(r.episode_id, r.meeting_idx)].append(int(r.ts))
    for k in vote_ts_by_meeting:
        vote_ts_by_meeting[k].sort()

    def votes_remaining(r) -> int:
        seq = vote_ts_by_meeting.get((r.episode_id, r.meeting_idx), [])
        return len(seq) - bisect.bisect_right(seq, r.ts)

    chats["f_votes_remaining"] = [votes_remaining(r) for r in chats.itertuples()]

    features = SYMBOLIC + SEMANTIC
    results: dict = {"suspicion": {}, "persuasion": {}}
    for role in ["crew", "imposter"]:
        sub = chats[chats["role"] == role]
        results["suspicion"][role] = fit_one(sub, features, CONTROLS, "suspicion", sub["meeting_key"])
        results["persuasion"][role] = fit_one(sub, features, CONTROLS, "persuasion", sub["meeting_key"])
    render(results, args.out)


if __name__ == "__main__":
    main()
