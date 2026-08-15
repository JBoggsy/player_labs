#!/usr/bin/env python3
"""Wait for expert preprocessing, run a GPU canary, then train unattended."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from corpus_store import convert_corpus, write_balanced_indices


RL_ROOT = Path(__file__).resolve().parent


def record_status(path: Path, stage: str, **details) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"stage": stage, "updated_at_unix": time.time(), **details}, indent=2)
        + "\n"
    )
    print(f"stage={stage} {details}", flush=True)


def run(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, check=True)


def ensure_indices(dataset: Path, output: Path, budget: int, seed: int) -> None:
    if output.exists() and output.with_suffix(".json").exists():
        summary = json.loads(output.with_suffix(".json").read_text())
        if summary.get("requested_budget") == budget and summary.get("seed") == seed:
            return
    write_balanced_indices(dataset, output, budget, seed)


def latest_resume(output: Path) -> Path | None:
    candidates = []
    for state in (output / "trainer_state").glob("*/training_state.json"):
        value = json.loads(state.read_text())
        candidates.append(
            (
                int(value.get("global_updates", 0)),
                int(value.get("completed_epochs", 0)),
                state.parent,
            )
        )
    return max(candidates)[2] if candidates else None


def train_command(
    samples: Path,
    maps: Path,
    indices: Path,
    validation_samples: Path,
    validation_maps: Path,
    validation_indices: Path,
    output: Path,
    *,
    epochs: int,
    checkpoint_every_updates: int,
    schedule_epochs: int | None = None,
    spatial_semantics: bool = False,
) -> list[str]:
    command = [
        sys.executable,
        "-u",
        str(RL_ROOT / "train_sft.py"),
        "--samples",
        str(samples),
        "--maps",
        str(maps),
        "--sample-indices",
        str(indices),
        "--validation-samples",
        str(validation_samples),
        "--validation-maps",
        str(validation_maps),
        "--validation-indices",
        str(validation_indices),
        "--output",
        str(output),
        "--epochs",
        str(epochs),
        "--batch-size",
        "2",
        "--gradient-accumulation",
        "8",
        "--learning-rate",
        "0.0002",
        "--max-text-tokens",
        "4096",
        "--max-history-tokens",
        "832",
        "--mixed-precision",
        "bf16",
        "--action-change-weight",
        "1",
        "--log-every",
        "100",
        "--checkpoint-every-updates",
        str(checkpoint_every_updates),
    ]
    if schedule_epochs is not None:
        command.extend(("--schedule-epochs", str(schedule_epochs)))
    if spatial_semantics:
        command.append("--spatial-semantics")
    resume = latest_resume(output)
    if resume is not None:
        command.extend(("--resume-from", str(resume)))
    return command


def evaluate(
    checkpoint: Path,
    samples: Path,
    maps: Path,
    indices: Path,
    output: Path,
    *,
    spatial_semantics: bool = False,
) -> None:
    command = [
            sys.executable,
            "-u",
            str(RL_ROOT / "evaluate_sft.py"),
            "--checkpoint",
            str(checkpoint),
            "--samples",
            str(samples),
            "--maps",
            str(maps),
            "--sample-indices",
            str(indices),
            "--max-text-tokens",
            "4096",
            "--out",
            str(output),
        ]
    if spatial_semantics:
        command.append("--spatial-semantics")
    run(command)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-budget", type=int, default=250_000)
    parser.add_argument("--validation-budget", type=int, default=10_000)
    parser.add_argument("--test-budget", type=int, default=10_000)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args()
    status = args.output / "status.json"

    prepared = args.workspace / "prepared"
    while not (prepared / "provenance.json").exists():
        record_status(status, "waiting_for_preprocessing")
        time.sleep(args.poll_seconds)

    record_status(status, "converting_arrow")
    counts = convert_corpus(args.manifest, args.workspace)
    arrow = args.workspace / "arrow"
    indices = args.workspace / "indices"
    record_status(status, "building_balanced_indices", split_counts=counts)
    ensure_indices(arrow / "train", indices / "canary-train.npy", 1_024, 10_001)
    ensure_indices(arrow / "validation", indices / "canary-validation.npy", 256, 10_001)
    ensure_indices(arrow / "train", indices / "train.npy", args.train_budget, 1)
    ensure_indices(
        arrow / "validation", indices / "validation.npy", args.validation_budget, 2
    )
    ensure_indices(arrow / "test", indices / "test.npy", args.test_budget, 3)

    canary = args.output / "canary"
    if not (canary / "training_run.json").exists():
        record_status(status, "training_canary")
        run(
            train_command(
                arrow / "train",
                prepared / "train.maps.jsonl",
                indices / "canary-train.npy",
                arrow / "validation",
                prepared / "validation.maps.jsonl",
                indices / "canary-validation.npy",
                canary,
                epochs=1,
                checkpoint_every_updates=0,
            )
        )
    if not (canary / "validation_evaluation.json").exists():
        record_status(status, "evaluating_canary")
        evaluate(
            canary / "best",
            arrow / "validation",
            prepared / "validation.maps.jsonl",
            indices / "canary-validation.npy",
            canary / "validation_evaluation.json",
        )

    full = args.output / "full"
    if not (full / "training_run.json").exists():
        record_status(status, "training_full", train_budget=args.train_budget, epochs=args.epochs)
        run(
            train_command(
                arrow / "train",
                prepared / "train.maps.jsonl",
                indices / "train.npy",
                arrow / "validation",
                prepared / "validation.maps.jsonl",
                indices / "validation.npy",
                full,
                epochs=args.epochs,
                checkpoint_every_updates=1_000,
            )
        )
    if not (full / "test_evaluation.json").exists():
        record_status(status, "evaluating_full")
        evaluate(
            full / "best",
            arrow / "test",
            prepared / "test.maps.jsonl",
            indices / "test.npy",
            full / "test_evaluation.json",
        )
    record_status(status, "complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
