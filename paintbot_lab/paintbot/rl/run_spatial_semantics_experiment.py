#!/usr/bin/env python3
"""Screen egocentric spatial labels on validation, then promote only on signal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_expert_training import evaluate, record_status, run, train_command


MIN_AUTOREGRESSIVE_EXACT = 0.5802
MIN_AUTOREGRESSIVE_HELD_EXACT = 0.9124
MIN_AUTOREGRESSIVE_MOVEMENT = 0.7130


def passes_screen(metrics: dict) -> bool:
    all_metrics = metrics["groups"]["all"]
    held_samples = all_metrics["samples"] - all_metrics["changed_action_samples"]
    held_exact = (
        all_metrics["autoregressive_exact"]
        - all_metrics["autoregressive_changed_exact"]
    ) / held_samples
    return (
        all_metrics["autoregressive_exact_action_accuracy"]
        >= MIN_AUTOREGRESSIVE_EXACT
        and all_metrics["autoregressive_slot_accuracy"]["movement"]
        > MIN_AUTOREGRESSIVE_MOVEMENT
        and held_exact >= MIN_AUTOREGRESSIVE_HELD_EXACT
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    status = args.output / "status.json"
    arrow = args.workspace / "arrow"
    prepared = args.workspace / "prepared"
    indices = args.workspace / "indices"
    full = args.output / "full"
    validation = full / "validation_epoch_1.json"

    training_run = full / "training_run.json"
    completed_epochs = 0
    if training_run.exists():
        completed_epochs = int(json.loads(training_run.read_text())["epochs"])
    if completed_epochs < 1:
        record_status(status, "training_epoch_1", experiment="spatial_semantics_screen")
        run(
            train_command(
                arrow / "train",
                prepared / "train.maps.jsonl",
                indices / "train.npy",
                arrow / "validation",
                prepared / "validation.maps.jsonl",
                indices / "validation.npy",
                full,
                epochs=1,
                schedule_epochs=3,
                checkpoint_every_updates=1_000,
                spatial_semantics=True,
            )
        )
    if not validation.exists():
        record_status(status, "evaluating_epoch_1")
        evaluate(
            full / "best",
            arrow / "validation",
            prepared / "validation.maps.jsonl",
            indices / "validation.npy",
            validation,
            spatial_semantics=True,
        )

    metrics = json.loads(validation.read_text())
    if not passes_screen(metrics):
        record_status(status, "screen_rejected", promotion=False)
        return 0

    if completed_epochs < 3:
        record_status(status, "training_epochs_2_and_3", promotion=True)
        run(
            train_command(
                arrow / "train",
                prepared / "train.maps.jsonl",
                indices / "train.npy",
                arrow / "validation",
                prepared / "validation.maps.jsonl",
                indices / "validation.npy",
                full,
                epochs=3,
                schedule_epochs=3,
                checkpoint_every_updates=1_000,
                spatial_semantics=True,
            )
        )
    final_validation = full / "validation_evaluation.json"
    if not final_validation.exists():
        record_status(status, "evaluating_final_validation")
        evaluate(
            full / "best",
            arrow / "validation",
            prepared / "validation.maps.jsonl",
            indices / "validation.npy",
            final_validation,
            spatial_semantics=True,
        )
    record_status(status, "complete", promotion=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
