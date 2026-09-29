#!/usr/bin/env python3
"""Paired, head-to-head and sequential A/B statistics for the `coworld-ab` skill.

Game-agnostic companion to `ab_stats.py` (which covers independent samples). Use it when the
design, not the data, makes observations dependent:

  paired        both arms play the same opponent on the same (seed, side) schedule. One pair
                = (baseline episode, candidate episode) with the same key. Means: paired
                t-test on the per-pair differences, with a Wilcoxon signed-rank check that
                must agree before a directional verdict. Binary outcomes: exact McNemar on
                the discordant pairs (concordant pairs carry no information and drop out;
                a draw counts as a non-win).
  head-to-head  candidate and baseline in the same episode. The primary continuous outcome
                (e.g. an Elo outcome score in [0, 1]) gets a one-sample t-test against 0.5;
                a win gets an exact binomial test on decisive games (draws dropped). Other
                metrics are paired within the episode (candidate seats vs baseline seats).
  sequential    a normal-approximation SPRT on a mean difference (the form fishtest's GSPRT
                uses for Elo): accept_h0 / accept_h1 / continue, with the LLR and bounds.

Guardrails inherited from ab_stats (same constants, same code): SIG_P, the SMALL_N floor
(no directional verdict, and no sequential decision, below 30 pairs/observations),
Benjamini-Yekutieli correction across every reported test (`ab_stats.apply_correction`),
missing values excluded and counted per metric (n shows how many pairs entered each test).
Exclusion counting and the ops-failure metric belong to the lab adapter, exactly as for
ab_stats: report `ops_fail_rate` as a metric (it pairs like any binary outcome) and pass the
adapter's exclusion counters into the JSON.

The adapter -> engine contract mirrors ab_stats:

  metrics:      list of (key, higher_is_better, kind in {"rate", "mean"}, applies_to_group|None)
  value_of:     (row, key) -> float | None     one arm's value in one episode
  pair_groups:  {group: [(baseline_row, candidate_row), ...]}
  tests:        optional {key: "one_sample" | "decisive_binomial"} overrides (head-to-head)

Rendering reuses ab_stats.render_markdown / emit_json; `emit_json` here adds each delta's
`test` and `detail` (Wilcoxon p, discordant counts, mean difference).
"""

from __future__ import annotations

import math
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ab_stats  # noqa: E402
from ab_stats import SIG_P, SMALL_N, Delta  # noqa: E402

PAIRED_ANALYSIS = ("Paired design: paired t-test on per-pair differences (Wilcoxon signed-rank must agree) for means; "
                   "exact McNemar on discordant pairs for rates (draw = non-win). BY correction across reported "
                   "metrics; minimum 30 pairs. Inconclusive is not equivalence.")
H2H_ANALYSIS = ("Head-to-head design: one-sample t-test of the candidate's outcome score against 0.5; exact binomial "
                "on decisive games for wins (draws dropped); other metrics paired within the episode. BY correction "
                "across reported metrics; minimum 30 episodes. Inconclusive is not equivalence.")


# --------------------------------------------------------------------------- tests

def paired_mean_sig(base_vals: list[float], cand_vals: list[float]) -> tuple[float, float, float, float]:
    """Paired t-test on (cand - base); return (t, p, dz, wilcoxon_p).

    dz is the mean difference over the SD of the differences. With no variance in the
    differences there is no test: p = 1 (the observed difference is still reported)."""
    if len(base_vals) != len(cand_vals):
        raise ValueError("paired values must have equal length")
    diffs = [c - b for b, c in zip(base_vals, cand_vals)]
    if len(diffs) < 2 or statistics.pstdev(diffs) == 0:
        return 0.0, 1.0, 0.0, 1.0
    result = stats.ttest_rel(cand_vals, base_vals)
    dz = statistics.mean(diffs) / statistics.stdev(diffs)
    return float(result.statistic), float(result.pvalue), dz, wilcoxon_p(diffs)


def wilcoxon_p(diffs: list[float]) -> float:
    """Two-sided Wilcoxon signed-rank p on the differences (zero differences dropped)."""
    nonzero = [d for d in diffs if d != 0]
    if not nonzero:
        return 1.0
    return float(stats.wilcoxon(nonzero).pvalue)


def decisive_binomial(wins: int, losses: int) -> tuple[float, float]:
    """Exact two-sided binomial test of wins vs losses at 1/2 (ties/draws already removed).

    Returns (effect, p) with effect = wins / (wins + losses) - 0.5."""
    decisive = wins + losses
    if decisive == 0:
        return 0.0, 1.0
    return wins / decisive - 0.5, float(stats.binomtest(wins, decisive, 0.5).pvalue)


def mcnemar_sig(base_bin: list[float], cand_bin: list[float]) -> tuple[float, float, int, int]:
    """Exact McNemar test on paired binary outcomes; return (effect, p, b, c).

    b = pairs where only the baseline had the outcome, c = pairs where only the candidate
    did. Concordant pairs drop out; the test is the exact binomial of c against b + c.
    effect = (c - b) / n_pairs, which equals the difference in proportions."""
    if len(base_bin) != len(cand_bin):
        raise ValueError("paired values must have equal length")
    for value in (*base_bin, *cand_bin):
        if value not in (0, 1):
            raise ValueError("McNemar needs binary 0/1 outcomes per episode")
    b = sum(1 for x, y in zip(base_bin, cand_bin) if x == 1 and y == 0)
    c = sum(1 for x, y in zip(base_bin, cand_bin) if x == 0 and y == 1)
    _, p = decisive_binomial(c, b)
    return ((c - b) / len(base_bin) if base_bin else 0.0), p, b, c


def one_sample_sig(values: list[float], null: float = 0.5) -> tuple[float, float, float]:
    """One-sample t-test of the mean against `null`; return (t, p, d) with d = (mean - null) / sd."""
    if len(values) < 2 or statistics.pstdev(values) == 0:
        return 0.0, 1.0, 0.0
    result = stats.ttest_1samp(values, null)
    return float(result.statistic), float(result.pvalue), (statistics.mean(values) - null) / statistics.stdev(values)


# --------------------------------------------------------------------------- deltas

@dataclass
class PairedDelta(Delta):
    """An ab_stats.Delta whose n_base == n_cand == the number of pairs that entered the test."""
    test: str = ""
    detail: dict = field(default_factory=dict)

    def compute_pairs(self, base_vals: list[float], cand_vals: list[float], test: str,
                      sig_p: float = SIG_P) -> None:
        """Fill p / effect / verdict for one of: paired_t, mcnemar, one_sample, decisive_binomial."""
        self.test = test
        if not base_vals:
            return
        if test == "paired_t":
            _, p, dz, w_p = paired_mean_sig(base_vals, cand_vals)
            self.p, self.effect = p, dz
            self.detail = {"mean_diff": statistics.mean(c - b for b, c in zip(base_vals, cand_vals)),
                           "wilcoxon_p": w_p}
            agrees = w_p < sig_p
        elif test == "mcnemar":
            effect, p, b, c = mcnemar_sig(base_vals, cand_vals)
            self.p, self.effect = p, effect
            self.detail = {"only_baseline": b, "only_candidate": c, "concordant": len(base_vals) - b - c}
            agrees = True
        elif test == "one_sample":
            _, p, d = one_sample_sig(cand_vals, 0.5)
            self.p, self.effect = p, d
            self.detail = {"null": 0.5, "mean_minus_null": statistics.mean(cand_vals) - 0.5}
            agrees = True
        elif test == "decisive_binomial":
            # Within one episode "only the candidate won" is a candidate win, "only the
            # baseline won" a candidate loss, and a draw (neither won) drops out.
            effect, p, losses, wins = mcnemar_sig(base_vals, cand_vals)
            self.p, self.effect = p, wins / (wins + losses) - 0.5 if wins + losses else 0.0
            self.detail = {"candidate_wins": wins, "candidate_losses": losses,
                           "draws": len(base_vals) - wins - losses}
            agrees = True
        else:
            raise ValueError(f"unknown paired test {test!r}")
        self.raw_p = self.p
        delta = self.cand - self.base
        significant = self.p < sig_p and agrees and self.n_base >= SMALL_N
        if not significant or delta == 0:
            self.verdict = "inconclusive"
        else:
            self.verdict = "improved" if (delta > 0) == self.higher_is_better else "regressed"


def build_paired_deltas(pair_groups: dict, metrics, value_of, all_groups, *, tests: dict | None = None,
                        sig_p: float = SIG_P) -> list[PairedDelta]:
    """A PairedDelta per (metric, applicable group), then BY across all of them.

    A pair enters a metric's test only when both arms' values are known; `n_base`/`n_cand`
    report that count. The default test is paired_t for "mean" and mcnemar for "rate";
    `tests` overrides it per metric key (head-to-head: "one_sample", "decisive_binomial")."""
    tests = tests or {}
    out: list[PairedDelta] = []
    for key, hib, kind, only_group in metrics:
        for group in ([only_group] if only_group else list(all_groups)):
            known = [(value_of(b, key), value_of(c, key)) for b, c in pair_groups.get(group, [])]
            known = [(x, y) for x, y in known if x is not None and y is not None]
            base_vals, cand_vals = [x for x, _ in known], [y for _, y in known]
            d = PairedDelta(metric=key, group=group, higher_is_better=hib,
                            base=statistics.mean(base_vals) if known else None,
                            cand=statistics.mean(cand_vals) if known else None,
                            n_base=len(known), n_cand=len(known), kind=kind)
            d.compute_pairs(base_vals, cand_vals, tests.get(key, "paired_t" if kind == "mean" else "mcnemar"),
                            sig_p=sig_p)
            out.append(d)
    ab_stats.apply_correction(out, sig_p)
    return out


def emit_json(base_spec: str, cand_spec: str, target: str | None, deltas: list[PairedDelta],
              analysis: str = PAIRED_ANALYSIS) -> dict:
    """ab_stats' neutral JSON contract plus each delta's `test` and `detail`."""
    report = ab_stats.emit_json(base_spec, cand_spec, target, deltas, analysis=analysis)
    for row, d in zip(report["deltas"], deltas):
        row.update(test=d.test, detail=d.detail)
    return report


def render_detail(deltas: list[PairedDelta]) -> str:
    """A Markdown table of which test each metric used and its supporting counts."""
    lines = ["## Paired detail", "", "| metric | group | test | n pairs | raw p | detail |", "| --- | --- | --- | ---: | ---: | --- |"]
    for d in deltas:
        if d.base is None:
            continue
        detail = ", ".join(f"{k}={v:.3g}" if isinstance(v, float) else f"{k}={v}" for k, v in d.detail.items())
        lines.append(f"| {d.metric} | {d.group} | {d.test} | {d.n_base} | {d.raw_p:.3f} | {detail} |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- sequential

@dataclass
class SprtResult:
    decision: str            # accept_h0 | accept_h1 | continue
    llr: float
    lower: float             # log(beta / (1 - alpha)): at or below -> accept H0
    upper: float             # log((1 - beta) / alpha): at or above -> accept H1
    n: int
    estimate: float | None
    stderr: float | None
    h0: float
    h1: float
    alpha: float
    beta: float
    note: str = ""

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def sprt_bounds(alpha: float, beta: float) -> tuple[float, float]:
    if not (0 < alpha < 1 and 0 < beta < 1):
        raise ValueError("alpha and beta must be in (0, 1)")
    return math.log(beta / (1 - alpha)), math.log((1 - beta) / alpha)


def sprt(estimate: float, variance: float, n: int, *, h0: float, h1: float,
         alpha: float = 0.05, beta: float = 0.05, min_n: int = SMALL_N) -> SprtResult:
    """Normal-approximation SPRT for a mean (difference) with estimated variance.

    LLR = ((est - h0)^2 - (est - h1)^2) / (2 * variance), where `variance` is the variance of
    the estimate (s^2 / n for a mean). This is the approximation fishtest's GSPRT uses.
    Below `min_n` (default SMALL_N) the answer is always `continue`: early variance estimates
    are too noisy to stop on."""
    if h1 == h0:
        raise ValueError("h0 and h1 must differ")
    lower, upper = sprt_bounds(alpha, beta)
    base = dict(lower=lower, upper=upper, n=n, h0=h0, h1=h1, alpha=alpha, beta=beta)
    if n < 2 or not variance > 0:
        return SprtResult("continue", 0.0, estimate=estimate if n else None, stderr=None,
                          note="not enough variation to estimate a variance", **base)
    llr = ((estimate - h0) ** 2 - (estimate - h1) ** 2) / (2 * variance)
    stderr = math.sqrt(variance)
    if n < min_n:
        return SprtResult("continue", llr, estimate=estimate, stderr=stderr,
                          note=f"below the {min_n}-observation floor: no stopping decision yet", **base)
    decision = "accept_h1" if llr >= upper else "accept_h0" if llr <= lower else "continue"
    return SprtResult(decision, llr, estimate=estimate, stderr=stderr, **base)


def sprt_mean(values: list[float], *, h0: float, h1: float, alpha: float = 0.05, beta: float = 0.05,
              min_n: int = SMALL_N) -> SprtResult:
    """SPRT on the mean of one sample: per-pair differences (paired design), or the
    candidate's outcome minus 0.5 (head-to-head)."""
    n = len(values)
    estimate = statistics.mean(values) if n else 0.0
    variance = statistics.variance(values) / n if n >= 2 else 0.0
    return sprt(estimate, variance, n, h0=h0, h1=h1, alpha=alpha, beta=beta, min_n=min_n)


def sprt_two_sample(base_vals: list[float], cand_vals: list[float], *, h0: float, h1: float,
                    alpha: float = 0.05, beta: float = 0.05, min_n: int = SMALL_N) -> SprtResult:
    """SPRT on mean(cand) - mean(base) for independent arms (Welch variance). The floor
    applies to the smaller arm."""
    n = min(len(base_vals), len(cand_vals))
    if n < 2:
        estimate = (statistics.mean(cand_vals) - statistics.mean(base_vals)) if n else 0.0
        return sprt(estimate, 0.0, n, h0=h0, h1=h1, alpha=alpha, beta=beta, min_n=min_n)
    estimate = statistics.mean(cand_vals) - statistics.mean(base_vals)
    variance = statistics.variance(base_vals) / len(base_vals) + statistics.variance(cand_vals) / len(cand_vals)
    return sprt(estimate, variance, n, h0=h0, h1=h1, alpha=alpha, beta=beta, min_n=min_n)
