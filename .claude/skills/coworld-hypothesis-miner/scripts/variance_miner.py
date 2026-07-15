"""Variance miner engine: turn a corpus of scored episodes into RANKED, testable hypotheses.

Adapted from Metta-AI/optimizer-skills `harness/tools/variance_miner.py` (the
executable form of a hand-done strategy reconstruction). Its central, hard-won
insight: the behaviors that *separate a policy's wins from its losses* are NOT
the behaviors the policy does in every game (its invariant engine), but the
high-variance moves. Analyzing (or training on) the invariant competence learns
nothing about the policy's own score variance. This miner finds the load-bearing,
variance-explaining behaviors automatically and emits them as candidate
hypotheses for the experiment/A/B loop.

Pipeline (game-agnostic core, game-specific feature adapter — the coworld-ab pattern):

  episodes (rows) --featurize--> per-episode feature vectors (the lab's adapter)
                  --associate--> per-feature (high/low delta, correlation, score swing)
                  --rank-------> hypotheses sorted by load-bearing score swing.

The core never hardcodes a game. A `FeatureAdapter` maps one raw episode row to a
flat `dict[str, float]` of behavioral features plus the seat's `score`. Each lab
ships one adapter module (see the SKILL.md for the contract).
"""

from __future__ import annotations

import math
import statistics as stats
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# Feature adapter protocol
# --------------------------------------------------------------------------- #
@dataclass
class Episode:
    """One scored datapoint: a flat feature vector + the outcome we optimize."""

    episode_id: str
    score: float
    features: dict[str, float]
    # Optional free-form context carried through to hypotheses (e.g. round timings
    # that read nicely in prose). Never used in the math.
    notes: dict[str, str] = field(default_factory=dict)


# A FeatureAdapter is just: raw_row -> Episode | None  (None drops the row).
FeatureAdapter = Callable[[dict], "Episode | None"]


@dataclass
class FeatureMeta:
    """Human-facing description of a feature, so hypotheses read mechanistically.

    - kind="timing"  : value is "tick/round achieved" (lower is earlier). A NEGATIVE
                       score-correlation means "earlier is better".
    - kind="presence": value is 0/1 (did the behavior happen at all this game).
    - kind="count"   : value is a magnitude (#kills, #tasks, points in a category).
    The `change_hint` is a templated, game-specific suggestion for the policy edit.
    """

    name: str
    kind: str  # "timing" | "presence" | "count"
    blurb: str
    change_hint: str
    # If set, a unit move in this feature is worth ~this many points (used only
    # for display when the data-derived swing is too noisy to trust on its own).
    prior_vp_per_unit: float | None = None


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #
def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = stats.mean(xs), stats.mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / (sx * sy)


def _quantile(sorted_vals: Sequence[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = q * (len(sorted_vals) - 1)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return sorted_vals[lo]
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


# --------------------------------------------------------------------------- #
# Association: per-feature, how load-bearing is it for SCORE VARIANCE?
# --------------------------------------------------------------------------- #
@dataclass
class FeatureAssociation:
    name: str
    kind: str
    n: int
    coverage: float  # fraction of episodes where the behavior occurred (presence/timing)
    corr: float | None  # Pearson r with score
    high_mean: float  # feature mean in the top-score bucket
    low_mean: float  # feature mean in the bottom-score bucket
    high_score: float
    low_score: float
    spread: float  # |high_mean - low_mean| in feature units
    score_gap: float  # high_score - low_score (points between the buckets)
    # The headline number: estimated points this behavior is worth, attributing
    # the bucket score gap to features by |corr|-weighted contribution. How much
    # of the high/low SCORE gap this feature could plausibly explain.
    vp_swing: float
    discriminative: bool  # spread is large AND correlated (load-bearing)
    invariant: bool  # feature barely moves across buckets => can't explain variance


def associate(
    episodes: Sequence[Episode],
    metas: dict[str, FeatureMeta],
    *,
    bucket_q: float = 0.25,
) -> list[FeatureAssociation]:
    """For every feature, measure association with score AND whether it explains
    *variance* (a behavior present in every game, win or lose, is invariant and
    uninformative even if correlated)."""
    if len(episodes) < 4:
        raise ValueError(f"need >=4 episodes to mine variance, got {len(episodes)}")

    scores = [e.score for e in episodes]
    ssorted = sorted(scores)
    hi_cut = _quantile(ssorted, 1 - bucket_q)
    lo_cut = _quantile(ssorted, bucket_q)
    high = [e for e in episodes if e.score >= hi_cut]
    low = [e for e in episodes if e.score <= lo_cut]
    high_score = stats.mean([e.score for e in high])
    low_score = stats.mean([e.score for e in low])
    score_gap = high_score - low_score

    feat_names = sorted({k for e in episodes for k in e.features})
    out: list[FeatureAssociation] = []
    for name in feat_names:
        meta = metas.get(name)
        kind = meta.kind if meta else "count"
        present = [e for e in episodes if name in e.features]
        xs = [e.features[name] for e in present]
        ys = [e.score for e in present]
        coverage = len(present) / len(episodes)
        corr = _pearson(xs, ys)

        def fmean(group: Sequence[Episode]) -> float:
            vals = [e.features[name] for e in group if name in e.features]
            return stats.mean(vals) if vals else 0.0

        hi_m, lo_m = fmean(high), fmean(low)
        spread = abs(hi_m - lo_m)
        feat_range = (max(xs) - min(xs)) if xs else 0.0

        # Discriminative = the behavior genuinely differs between winning and
        # losing games (large normalized spread) AND tracks score (|r| meaningful).
        norm_spread = spread / feat_range if feat_range > 0 else 0.0
        discriminative = norm_spread >= 0.25 and (corr is not None and abs(corr) >= 0.3)
        invariant = norm_spread < 0.10

        # Score swing: share of the bucket score gap attributable to this feature.
        # We attribute by |corr| and by how much of the feature's own spread the
        # high/low gap captures. This intentionally rewards features that BOTH
        # correlate AND vary across buckets — exactly the load-bearing ones.
        if corr is None or score_gap <= 0:
            vp_swing = 0.0
        else:
            vp_swing = abs(corr) * norm_spread * score_gap

        out.append(
            FeatureAssociation(
                name=name,
                kind=kind,
                n=len(present),
                coverage=round(coverage, 3),
                corr=None if corr is None else round(corr, 3),
                high_mean=round(hi_m, 3),
                low_mean=round(lo_m, 3),
                high_score=round(high_score, 2),
                low_score=round(low_score, 2),
                spread=round(spread, 3),
                score_gap=round(score_gap, 2),
                vp_swing=round(vp_swing, 3),
                discriminative=discriminative,
                invariant=invariant,
            )
        )
    out.sort(key=lambda a: a.vp_swing, reverse=True)
    return out


# --------------------------------------------------------------------------- #
# Hypothesis emission — candidates for the coworld-experiment / coworld-ab loop
# --------------------------------------------------------------------------- #
def _direction(meta: FeatureMeta, a: FeatureAssociation) -> str:
    """Human phrasing for which way to push the feature."""
    if a.corr is None:
        return "unclear"
    better_high = a.corr > 0
    if meta.kind == "timing":
        # timing: higher value = later; positive corr w/ score => later is better
        return "achieve it EARLIER" if not better_high else "achieve it LATER"
    if meta.kind == "presence":
        return "DO it" if better_high else "AVOID it"
    return "do MORE of it" if better_high else "do LESS of it"


def emit_hypothesis(meta: FeatureMeta, a: FeatureAssociation, rank: int) -> str:
    direction = _direction(meta, a)
    corr_txt = "n/a" if a.corr is None else f"{a.corr:+.2f}"
    return f"""### H{rank}: {meta.name} — {meta.blurb}  (≈+{a.vp_swing:.1f} pts)

```
Observation:  In winning games the {meta.name} feature averages {a.high_mean} vs {a.low_mean}
              in losing games (spread {a.spread} in feature units; coverage {a.coverage:.0%}
              of {a.n} episodes). It correlates with final score at r={corr_txt}. The top
              score bucket means {a.high_score} pts, the bottom {a.low_score} pts
              (a {a.score_gap:.1f}-pt gap this behavior helps explain).
Causal guess: {meta.blurb} The data says the policy should {direction}.
Evidence:     {a.n} real episodes; high/low buckets at the {{25th, 75th}} score percentiles;
              this feature ranks #{rank} by load-bearing score swing among all mined behaviors.
Missing data: per-decision attribution of WHY losing games skip this behavior — confirm
              in the traces/replays before committing the change.
Change:       {meta.change_hint}
Expected:     moving {meta.name} from the losing-game level ({a.low_mean}) toward the
              winning-game level ({a.high_mean}) should recover up to ~{a.vp_swing:.1f} pts.
Next step:    harden via coworld-experiment (falsify the mechanism against existing data),
              then measure any fix with a matched fresh coworld-ab.
Overfit risk: {("LOW — strongly discriminative" if a.discriminative else "MEDIUM — correlation present but spread is modest; verify it is not opponent-specific")}.
```
"""


@dataclass
class MineResult:
    n_episodes: int
    score_mean: float
    score_p25: float
    score_p75: float
    associations: list[FeatureAssociation]
    metas: dict[str, FeatureMeta]

    def ranked_hypotheses(self, top: int = 5, min_vp: float = 0.3) -> list[str]:
        out: list[str] = []
        rank = 0
        for a in self.associations:
            if a.invariant or a.vp_swing < min_vp:
                continue
            meta = self.metas.get(a.name)
            if meta is None:
                continue
            rank += 1
            out.append(emit_hypothesis(meta, a, rank))
            if rank >= top:
                break
        return out

    def invariant_behaviors(self) -> list[str]:
        """Behaviors present in wins AND losses: they explain how the policy beats
        OTHERS but not its own variance. Reported so no hypothesis is wasted on
        them — and as evidence of what is table-stakes vs. what wins."""
        return [a.name for a in self.associations if a.invariant and a.coverage >= 0.8]


def mine(rows: Iterable[dict], adapter: FeatureAdapter, metas: dict[str, FeatureMeta]) -> MineResult:
    episodes = [ep for ep in (adapter(r) for r in rows) if ep is not None]
    if len(episodes) < 4:
        raise ValueError(f"adapter produced {len(episodes)} usable episodes; need >=4")
    assocs = associate(episodes, metas)
    scores = sorted(e.score for e in episodes)
    return MineResult(
        n_episodes=len(episodes),
        score_mean=round(stats.mean(scores), 2),
        score_p25=round(_quantile(scores, 0.25), 2),
        score_p75=round(_quantile(scores, 0.75), 2),
        associations=assocs,
        metas=metas,
    )


def render_report(res: MineResult, *, top: int = 5) -> str:
    lines: list[str] = []
    lines.append("# Hypothesis Miner — Ranked Candidates\n")
    lines.append(
        f"**Corpus:** {res.n_episodes} episodes · score mean {res.score_mean} "
        f"(p25 {res.score_p25} / p75 {res.score_p75})\n"
    )
    inv = res.invariant_behaviors()
    if inv:
        lines.append(
            "## Invariant behaviors (NOT hypotheses)\n\n"
            "These happen in winning AND losing games, so they cannot explain this "
            "policy's score variance. Do not spend a hypothesis here:\n\n- "
            + "\n- ".join(inv)
            + "\n"
        )
    lines.append("## Load-bearing behaviors (ranked by points they could recover)\n")
    hyps = res.ranked_hypotheses(top=top)
    if not hyps:
        lines.append(
            "_No feature cleared the variance + correlation bar. Either the corpus "
            "is too small, or the score spread is pure noise (no actionable signal)._\n"
        )
    else:
        lines.extend(hyps)
    lines.append("\n## Full feature table\n")
    lines.append("| feature | kind | cover | r | high | low | spread | swing | flag |")
    lines.append("|---|---|--:|--:|--:|--:|--:|--:|:--|")
    for a in res.associations:
        flag = "DISCRIM" if a.discriminative else ("inv" if a.invariant else "")
        r = "n/a" if a.corr is None else f"{a.corr:+.2f}"
        lines.append(
            f"| {a.name} | {a.kind} | {a.coverage:.0%} | {r} | {a.high_mean} | "
            f"{a.low_mean} | {a.spread} | {a.vp_swing:.2f} | {flag} |"
        )
    return "\n".join(lines) + "\n"
