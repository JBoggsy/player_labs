#!/usr/bin/env python3
"""Run the matched-compute 750k-unique training arm without opening the test set."""

from __future__ import annotations

import argparse
from pathlib import Path

from corpus_store import write_balanced_indices
from run_expert_training import evaluate, record_status, run, train_command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-budget", type=int, default=750_000)
    args = parser.parse_args()

    status = args.output / "status.json"
    arrow = args.workspace / "arrow"
    prepared = args.workspace / "prepared"
    indices = args.workspace / "indices"
    train_indices = indices / f"train-diverse-{args.train_budget}.npy"
    validation_indices = indices / "validation.npy"
    full = args.output / "full"

    if not train_indices.exists():
        record_status(
            status,
            "building_balanced_indices",
            train_budget=args.train_budget,
            epochs=1,
            experiment="matched_compute_unique_rows",
        )
        write_balanced_indices(arrow / "train", train_indices, args.train_budget, seed=1)

    if not (full / "training_run.json").exists():
        record_status(
            status,
            "training_full",
            train_budget=args.train_budget,
            epochs=1,
            experiment="matched_compute_unique_rows",
        )
        run(
            train_command(
                arrow / "train",
                prepared / "train.maps.jsonl",
                train_indices,
                arrow / "validation",
                prepared / "validation.maps.jsonl",
                validation_indices,
                full,
                epochs=1,
                checkpoint_every_updates=1_000,
            )
        )

    validation_evaluation = full / "validation_evaluation.json"
    if not validation_evaluation.exists():
        record_status(status, "evaluating_validation")
        evaluate(
            full / "best",
            arrow / "validation",
            prepared / "validation.maps.jsonl",
            validation_indices,
            validation_evaluation,
        )
    record_status(status, "complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
