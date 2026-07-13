#!/usr/bin/env python3
"""Game-agnostic A/B statistics engine — the shared core of the `coworld-ab` skill.

This module knows NOTHING about any specific game's metrics. It provides the significance
tests, the improved/regressed/noise verdict logic, the metric-delta builder, and the neutral
Markdown/JSON renderers. Each game lab writes a thin `compare.py` **adapter** that:

  - extracts per-appearance records from *its* results.json/episode.json schema,
  - declares its METRICS list and a grouping dimension (e.g. crewrift: role in {crew, imposter};
    a role-less game: a single {"all": [...]} group),
  - imports this module and calls `build_deltas(...)` + `render_markdown(...)` + `emit_json(...)`.

The adapter → engine contract:

  metrics:      list of (key, higher_is_better: bool, kind: "rate"|"mean", applies_to_group|None)
  metric_value: (recs, key) -> (value: float, n: int) | None       # game-specific aggregation
  value_fn:     (recs, key) -> list[float]                          # per-appearance values (mean kind)
  *_groups:     {group_name: [rec, ...]}                            # the lab's grouping dimension
  all_groups:   ordered list of group names to report when a metric applies to every group

Neutral JSON contract (what compare_report.py consumes):
  {baseline, candidate, target,
   deltas:[{metric, group, base, cand, n_base, n_cand, p, effect, verdict}]}
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass


# --- significance (normal-approx; no scipy) -----------------------------------------

def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def two_sided_p(z: float) -> float:
    return 2 * (1 - _phi(abs(z)))


def rate_sig(p_a: float, n_a: int, p_b: float, n_b: int) -> tuple[float, float]:
    """Two-proportion z-test. Returns (z, p)."""
    if n_a == 0 or n_b == 0:
        return 0.0, 1.0
    pool = (p_a * n_a + p_b * n_b) / (n_a + n_b)
    se = math.sqrt(pool * (1 - pool) * (1 / n_a + 1 / n_b))
    if se == 0:
        return 0.0, 1.0
    z = (p_b - p_a) / se
    return z, two_sided_p(z)


def mean_sig(vals_a: list[float], vals_b: list[float]) -> tuple[float, float, float]:
    """Welch-ish z on the mean difference + Cohen's d. Returns (z, p, d)."""
    if len(vals_a) < 2 or len(vals_b) < 2:
        return 0.0, 1.0, 0.0
    ma, mb = statistics.mean(vals_a), statistics.mean(vals_b)
    va, vb = statistics.variance(vals_a), statistics.variance(vals_b)
    se = math.sqrt(va / len(vals_a) + vb / len(vals_b))
    z = (mb - ma) / se if se else 0.0
    pooled_sd = math.sqrt((va + vb) / 2)
    d = (mb - ma) / pooled_sd if pooled_sd else 0.0
    return z, two_sided_p(z), d


SIG_P = 0.05
SMALL_N = 30


@dataclass
class Delta:
    metric: str
    group: str
    higher_is_better: bool
    base: float | None
    cand: float | None
    n_base: int
    n_cand: int
    kind: str
    p: float = 1.0
    effect: float = 0.0          # Cohen's d for means; z for rates
    verdict: str = "n/a"         # improved | regressed | noise | n/a

    def compute(self, base_vals: list[float], cand_vals: list[float], sig_p: float = SIG_P) -> None:
        """Fill p / effect / verdict. base_vals/cand_vals are per-appearance values (mean kind only)."""
        if self.base is None or self.cand is None:
            return
        delta = self.cand - self.base
        if self.kind == "rate":
            z, p = rate_sig(self.base, self.n_base, self.cand, self.n_cand)
            self.p, self.effect = p, z
        else:
            z, p, d = mean_sig(base_vals, cand_vals)
            self.p, self.effect = p, d
        sig = self.p < sig_p and min(self.n_base, self.n_cand) >= 2
        if not sig or delta == 0:
            self.verdict = "noise"
        else:
            better = (delta > 0) == self.higher_is_better
            self.verdict = "improved" if better else "regressed"


def build_deltas(base_groups, cand_groups, metrics, metric_value, value_fn, all_groups,
                 sig_p: float = SIG_P) -> list[Delta]:
    """Compute a Delta per (metric, applicable group).

    metric_value(recs, key) -> (value, n) | None ; value_fn(recs, key) -> list[float].
    A metric with `applies_to_group` set is reported only for that group; otherwise for
    every group in `all_groups` (order preserved).
    """
    out: list[Delta] = []
    for key, hib, kind, only_group in metrics:
        groups = [only_group] if only_group else list(all_groups)
        for group in groups:
            br, cr = base_groups.get(group, []), cand_groups.get(group, [])
            bv = metric_value(br, key)
            cv = metric_value(cr, key)
            d = Delta(metric=key, group=group, higher_is_better=hib,
                      base=bv[0] if bv else None, cand=cv[0] if cv else None,
                      n_base=bv[1] if bv else 0, n_cand=cv[1] if cv else 0, kind=kind)
            d.compute(value_fn(br, key), value_fn(cr, key), sig_p=sig_p)
            out.append(d)
    return out


# --- rendering ----------------------------------------------------------------------

VERDICT_MARK = {"improved": "▲ improved", "regressed": "▼ REGRESSED",
                "noise": "· noise", "n/a": "—"}


def fmt(v: float | None, kind: str) -> str:
    if v is None:
        return "—"
    return f"{v*100:.0f}%" if kind == "rate" else f"{v:.2f}"


def emit_json(base_spec: str, cand_spec: str, target: str | None, deltas: list[Delta]) -> dict:
    """The neutral JSON contract consumed by compare_report.py."""
    return {
        "baseline": base_spec, "candidate": cand_spec, "target": target,
        "deltas": [{"metric": d.metric, "group": d.group, "base": d.base, "cand": d.cand,
                    "n_base": d.n_base, "n_cand": d.n_cand, "p": d.p,
                    "effect": d.effect, "verdict": d.verdict} for d in deltas],
    }


def render_markdown(base_spec: str, cand_spec: str, base_groups, cand_groups,
                    deltas: list[Delta], target: str | None, all_groups, metrics) -> str:
    """The plain-text A/B summary. Group-agnostic; `all_groups` orders the count line."""
    L = []
    L.append(f"# A/B: `{cand_spec}` (candidate) vs `{base_spec}` (baseline)")
    L.append("")
    base_n = "  ".join(f"{g} {len(base_groups.get(g, []))}" for g in all_groups)
    cand_n = "  ".join(f"{g} {len(cand_groups.get(g, []))}" for g in all_groups)
    L.append(f"Baseline n: {base_n}  |  Candidate n: {cand_n}")
    small = min(sum(len(base_groups.get(g, [])) for g in all_groups),
                sum(len(cand_groups.get(g, [])) for g in all_groups))
    if small < SMALL_N:
        L.append("")
        L.append(f"> ⚠ Small sample (min side {small}) — deltas are directional, not "
                 f"conclusive. Run larger matched requests for a firm call.")
    L.append("")

    if target:
        L.append(f"## Target axis: `{target}`")
        hits = [d for d in deltas if d.metric == target]
        if not hits:
            L.append(f"_Unknown metric `{target}`. Known: {', '.join(m[0] for m in metrics)}._")
        for d in hits:
            if d.base is None and d.cand is None:
                continue
            L.append(f"- **{d.group}**: {fmt(d.base, d.kind)} → {fmt(d.cand, d.kind)}  "
                     f"(**{VERDICT_MARK[d.verdict]}**, p={d.p:.3f}, "
                     f"{'d' if d.kind=='mean' else 'z'}={d.effect:+.2f})")
        L.append("")

    L.append("## All metrics (baseline → candidate, Δ, verdict)")
    L.append("")
    L.append("| metric | group | baseline | candidate | verdict (p) |")
    L.append("| --- | --- | ---: | ---: | --- |")
    for d in deltas:
        if d.base is None and d.cand is None:
            continue
        L.append(f"| {d.metric} | {d.group} | {fmt(d.base, d.kind)} | {fmt(d.cand, d.kind)} "
                 f"| {VERDICT_MARK[d.verdict]} (p={d.p:.2f}) |")
    L.append("")

    regr = [d for d in deltas if d.verdict == "regressed"]
    if regr:
        L.append("## ⚠ Regressions (significant adverse moves — watch these)")
        for d in regr:
            L.append(f"- **{d.metric} / {d.group}**: {fmt(d.base, d.kind)} → {fmt(d.cand, d.kind)} (p={d.p:.2f})")
        L.append("")

    L.append("## Next: the qualitative half")
    L.append("")
    L.append("Numbers say *whether* it moved; they don't say *why*. Now read the two")
    L.append("batches' replays + logs side by side, steered by your context (target")
    L.append("dimension / specific opponent / specific fault) — see SKILL.md §Qualitative.")
    return "\n".join(L)
