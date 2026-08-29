#!/usr/bin/env python3
"""Calibrate one previous-action change bias on a replay-disjoint validation split."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def replay_split(replay_ids: np.ndarray) -> np.ndarray:
    """Assign every replay wholly to calibration (true) or confirmation (false)."""
    return np.asarray(
        [hashlib.sha256(str(value).encode()).digest()[0] < 128 for value in replay_ids]
    )


def predict(data, bias: float) -> np.ndarray:
    logits = data["logits"].copy()
    previous = data["previous"]
    token_ids = data["token_ids"]
    valid_counts = data["valid_counts"]
    for slot in range(4):
        candidates = token_ids[slot, : valid_counts[slot]]
        logits[:, slot, : valid_counts[slot]] += bias * (
            candidates[None, :] != previous[:, slot, None]
        )
    choices = logits.argmax(axis=2)
    return token_ids[np.arange(token_ids.shape[0])[None, :], choices]


def metrics(predicted: np.ndarray, data, selected: np.ndarray) -> dict:
    labels = data["labels"][selected]
    previous = data["previous"][selected]
    predicted = predicted[selected]
    target_changes = previous[:, :4] != labels[:, :4]
    predicted_changes = previous[:, :4] != predicted[:, :4]
    changed = target_changes.any(axis=1)
    exact = (predicted == labels).all(axis=1)
    held = ~changed
    mean_or_none = lambda values: float(values.mean()) if len(values) else None
    return {
        "samples": int(selected.sum()),
        "changed_samples": int(changed.sum()),
        "exact_action_accuracy": mean_or_none(exact),
        "changed_exact_action_accuracy": mean_or_none(exact[changed]),
        "held_exact_action_accuracy": mean_or_none(exact[held]),
        "change_precision": float(
            (target_changes & predicted_changes).sum() / predicted_changes.sum()
        )
        if predicted_changes.any()
        else None,
        "change_recall": float(
            (target_changes & predicted_changes).sum() / target_changes.sum()
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logits", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--minimum-bias", type=float, default=0.0)
    parser.add_argument("--maximum-bias", type=float, default=4.0)
    parser.add_argument("--bias-step", type=float, default=0.1)
    args = parser.parse_args()

    data = np.load(args.logits)
    calibration = replay_split(data["replay_ids"])
    confirmation = ~calibration
    biases = np.arange(
        args.minimum_bias,
        args.maximum_bias + args.bias_step / 2,
        args.bias_step,
    )
    sweep = []
    for bias in biases:
        predicted = predict(data, float(bias))
        sweep.append({"bias": float(bias), **metrics(predicted, data, calibration)})
    selected = max(sweep, key=lambda row: (row["exact_action_accuracy"], -abs(row["bias"])))
    selected_bias = selected["bias"]
    baseline = predict(data, 0.0)
    candidate = predict(data, selected_bias)
    result = {
        "method": "single global logit bonus for action tokens differing from previous state",
        "selection_metric": "calibration exact_action_accuracy",
        "split": "sha256(replay_id) first byte < 128; no replay crosses halves",
        "selected_bias": selected_bias,
        "calibration": {
            "baseline": metrics(baseline, data, calibration),
            "candidate": metrics(candidate, data, calibration),
        },
        "confirmation": {
            "baseline": metrics(baseline, data, confirmation),
            "candidate": metrics(candidate, data, confirmation),
        },
        "sweep": sweep,
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
