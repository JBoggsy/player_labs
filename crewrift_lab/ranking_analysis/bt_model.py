#!/usr/bin/env python3
"""Team Bradley-Terry rating for Crewrift, with bootstrap rank CIs.

Crewrift is a team game: each game is ONE binary outcome (crew win vs imposter
win), all 6 crew share it and both imposters share the opposite. So we model the
GAME outcome as a function of *who was on each team*, and let the fit attribute
that shared outcome to individual policies — controlling for teammates/opponents,
which a raw win rate cannot.

Model (generalized Bradley-Terry / additive team strength on the logit scale,
the same form TrueSkill uses for team games):

    logit P(crew wins game g) = b0
        + sum_{p in crew(g)}     a_p        # a_p = crew skill  (higher = better crewmate)
        - sum_{p in imposter(g)} s_p        # s_p = imposter skill (higher = better imposter)

Each policy gets TWO independent ratings (crew skill a_p, imposter skill s_p): a
policy contributes a_p only in games it's crew, s_p only in games it's imposter.
The imposter term enters negative because a stronger imposter makes crew LESS
likely to win. Fit by L2-regularized logistic regression (the ridge resolves the
always-6-crew / always-2-imposter level degeneracy; only skill *differences* are
identified, which is exactly what a ranking needs).

Uncertainty: bootstrap over GAMES (the independent unit — not seats). Resample
games with replacement, refit, and record each policy's skill and its RANK. The
rank distribution is the direct answer to "where do we rank, confidently."

Usage: bt_model.py [episode_root ...]   (default: /tmp/v96_rank_wh_episodes)
"""
from __future__ import annotations
import glob
import json
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression

from _data import clean_games, DATA

C_RIDGE = 10.0        # weak L2 (data dominates at ~1500 games); bootstrap carries uncertainty
N_BOOT = 1000
MIN_GAMES = 20        # don't rank a policy with too few appearances
RNG = np.random.default_rng(20260706)


def load_games(roots: list[str]):
    """Return (games, policies). Each game: (crew_idx tuple, imp_idx tuple, crew_won)."""
    raw = []  # (crew_names, imp_names, crew_won)
    for root in roots:
        for epdir in glob.glob(f"{root}/*/"):
            try:
                res = json.load(open(epdir + "results.json"))
                epi = json.load(open(epdir + "episode.json"))
            except Exception:
                continue
            parts = epi.get("participants", [])
            n = len(parts)
            if n == 0 or "imposter" not in res or len(res["imposter"]) != n:
                continue
            ct = res.get("connect_timeout", [0] * n)
            dt = res.get("disconnect_timeout", [0] * n)
            sc = res.get("scores", [0] * n)
            # GAME-level ops filter: a broken seat breaks the whole team composition.
            if any(ct[i] or dt[i] or (sc[i] is not None and sc[i] <= -100) for i in range(n)):
                continue
            crew, imp = [], []
            for i, p in enumerate(parts):
                name = p.get("policy_name")
                if name is None:
                    break
                (imp if res["imposter"][i] else crew).append(name)
            else:
                # crew all share one outcome; take any crew seat's win
                crew_seats = [i for i in range(n) if not res["imposter"][i]]
                if not crew_seats:
                    continue
                wins = {bool(res["win"][i]) for i in crew_seats}
                if len(wins) != 1:        # inconsistent crew outcome: skip (shouldn't happen)
                    continue
                raw.append((crew, imp, wins.pop()))
    policies = sorted({p for c, i, _ in raw for p in (*c, *i)})
    pidx = {p: k for k, p in enumerate(policies)}
    games = [(tuple(pidx[p] for p in c), tuple(pidx[p] for p in i), int(w)) for c, i, w in raw]
    return games, policies, pidx


def design(games, n_pol):
    """X columns: [crew_0..crew_{P-1}, imp_0..imp_{P-1}]; imp columns are -1."""
    X = np.zeros((len(games), 2 * n_pol))
    y = np.zeros(len(games))
    for g, (crew, imp, w) in enumerate(games):
        for p in crew:
            X[g, p] += 1.0
        for p in imp:
            X[g, n_pol + p] += -1.0
        y[g] = w
    return X, y


def fit(X, y):
    m = LogisticRegression(C=C_RIDGE, fit_intercept=True, max_iter=2000, solver="lbfgs")
    m.fit(X, y)
    coef = m.coef_[0]
    n_pol = X.shape[1] // 2
    a = coef[:n_pol]              # crew skill
    s = coef[n_pol:]             # imposter skill (already oriented: higher = better imposter)
    # center within role so levels are comparable (differences are what's identified)
    return a - a.mean(), s - s.mean()


def summarize(name, boots, policies, focus="crewborg"):
    P = len(policies)
    skills = np.array([b[0] for b in boots]) if name == "crew" else np.array([b[1] for b in boots])
    # skills: (n_boot, P). rank 1 = highest skill.
    order = (-skills).argsort(axis=1)
    ranks = np.empty_like(order)
    for b in range(skills.shape[0]):
        ranks[b, order[b]] = np.arange(1, P + 1)
    pt = skills.mean(axis=0)
    consensus = (-pt).argsort()
    print(f"=== {name.upper()} skill ranking (team Bradley-Terry, {skills.shape[0]} bootstraps) ===")
    print(f"{'rank':>4}  {'policy':46s} {'skill':>7} {'90% CI':>16} {'rank 5-95%':>12}")
    for r, k in enumerate(consensus, 1):
        lo, hi = np.percentile(skills[:, k], [5, 95])
        rlo, rhi = np.percentile(ranks[:, k], [5, 95])
        star = "  <== crewborg" if policies[k] == focus else ""
        print(f"{r:>4}  {policies[k]:46s} {pt[k]:+7.2f} [{lo:+5.2f},{hi:+5.2f}]"
              f"   {int(rlo):>2}-{int(rhi):<2}{star}")
    if focus in policies:
        k = policies.index(focus)
        med = int(np.median(ranks[:, k]))
        rlo, rhi = np.percentile(ranks[:, k], [5, 95])
        print(f"  -> {focus} {name} rank: median {med} of {P}  (90% interval {int(rlo)}-{int(rhi)})")
    print()


def main():
    # Portable path: reconstruct clean games from the committed episode_players
    # parquet (see _data.clean_games). Pass episode dirs as argv to use the legacy
    # raw-episode loader instead.
    if len(sys.argv) > 1:
        games, policies, _pidx = load_games(sys.argv[1:])
    else:
        games, policies = clean_games()
    P = len(policies)
    if not games:
        print("no usable games yet")
        return
    counts = np.zeros(P)
    for c, i, _ in games:
        for p in (*c, *i):
            counts[p] += 1
    keep = {policies[k] for k in range(P) if counts[k] >= MIN_GAMES}
    print(f"# {len(games)} intact games, {P} policies "
          f"({sum(y for *_, y in games)} crew wins = {np.mean([g[2] for g in games]):.1%})\n")

    X, y = design(games, P)
    boots = []
    idx = np.arange(len(games))
    for b in range(N_BOOT):
        take = RNG.choice(idx, size=len(idx), replace=True) if b else idx  # b=0: point estimate
        boots.append(fit(X[take], y[take]))
    # filter low-N policies out of the display
    disp = [p for p in policies if p in keep]
    dpi = [policies.index(p) for p in disp]
    boots_d = [(a[dpi], s[dpi]) for a, s in boots]
    import json as _json
    export = {}
    for role in ("crew", "imposter"):
        summarize(role, boots_d, disp)
        skills = np.array([b[0] for b in boots_d]) if role == "crew" else np.array([b[1] for b in boots_d])
        P = len(disp)
        order = (-skills).argsort(axis=1)
        ranks = np.empty_like(order)
        for b in range(skills.shape[0]):
            ranks[b, order[b]] = np.arange(1, P + 1)
        pt = skills.mean(axis=0)
        export[role] = {
            disp[k]: {
                "skill": float(pt[k]),
                "skill_lo": float(np.percentile(skills[:, k], 5)),
                "skill_hi": float(np.percentile(skills[:, k], 95)),
                "rank_med": float(np.median(ranks[:, k])),
                "rank_lo": float(np.percentile(ranks[:, k], 5)),
                "rank_hi": float(np.percentile(ranks[:, k], 95)),
            } for k in range(P)
        }
    _json.dump(export, open(DATA / "bt_ranks.json", "w"), indent=2)


if __name__ == "__main__":
    main()
