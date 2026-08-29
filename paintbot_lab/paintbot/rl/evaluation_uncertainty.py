"""Fixed replay-cluster uncertainty contract for exact-action accuracy."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from scipy.stats import bootstrap


CLUSTER_BOOTSTRAP_CONFIDENCE = 0.95
CLUSTER_BOOTSTRAP_RESAMPLES = 9_999
CLUSTER_BOOTSTRAP_SEED = 20_260_814
CLUSTER_BOOTSTRAP_METHOD = "BCa"


def _ratio(correct: np.ndarray, samples: np.ndarray, *, axis: int = -1):
    return correct.sum(axis=axis) / samples.sum(axis=axis)


def replay_cluster_bootstrap(
    outcomes: Mapping[str, tuple[int, int]],
    *,
    n_resamples: int = CLUSTER_BOOTSTRAP_RESAMPLES,
) -> dict:
    """Estimate a row-weighted accuracy interval by resampling whole replays."""
    if not outcomes:
        raise ValueError("cluster bootstrap requires at least one replay")
    ordered = [outcomes[key] for key in sorted(outcomes)]
    correct = np.asarray([item[0] for item in ordered], dtype=np.float64)
    samples = np.asarray([item[1] for item in ordered], dtype=np.float64)
    if np.any(samples <= 0) or np.any(correct < 0) or np.any(correct > samples):
        raise ValueError("replay outcomes must satisfy 0 <= correct <= samples")
    point = float(correct.sum() / samples.sum())
    common = {
        "cluster_unit": "replay_id",
        "clusters": len(outcomes),
        "samples": int(samples.sum()),
        "correct": int(correct.sum()),
        "point_estimate": point,
        "confidence_level": CLUSTER_BOOTSTRAP_CONFIDENCE,
        "method": CLUSTER_BOOTSTRAP_METHOD,
        "resamples": n_resamples,
        "seed": CLUSTER_BOOTSTRAP_SEED,
    }
    if len(outcomes) < 2:
        return {
            **common,
            "available": False,
            "lower": None,
            "upper": None,
            "standard_error": None,
        }
    result = bootstrap(
        (correct, samples),
        _ratio,
        paired=True,
        vectorized=True,
        n_resamples=n_resamples,
        batch=256,
        confidence_level=CLUSTER_BOOTSTRAP_CONFIDENCE,
        alternative="two-sided",
        method=CLUSTER_BOOTSTRAP_METHOD,
        rng=np.random.default_rng(CLUSTER_BOOTSTRAP_SEED),
    )
    return {
        **common,
        "available": True,
        "lower": float(result.confidence_interval.low),
        "upper": float(result.confidence_interval.high),
        "standard_error": float(result.standard_error),
    }
