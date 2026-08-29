#!/usr/bin/env python3
"""Open the frozen test once for a checkpoint that already clears validation."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Callable
from pathlib import Path

from corpus_store import load_arrow_dataset
from evaluation_uncertainty import (
    CLUSTER_BOOTSTRAP_CONFIDENCE,
    CLUSTER_BOOTSTRAP_METHOD,
    CLUSTER_BOOTSTRAP_RESAMPLES,
    CLUSTER_BOOTSTRAP_SEED,
)
from evaluate_sft import sha256_file, sha256_tree
from run_expert_training import evaluate


VALIDATION_INDEX_SHA256 = "78e46be391cf13c6c488b6b0ed2ccd0fe1da36eb73d13fb6db5a42c0f8d50644"
TEST_INDEX_SHA256 = "8db6fb0c7fc8c53f514443ca7a7cba923f2a29b13356cc86fcf99d38b96c5b2e"
VALIDATION_DATASET_FINGERPRINT = "599c88fdfbf0ba82"
TEST_DATASET_FINGERPRINT = "03693a38c974e27a"
VALIDATION_SELECTED_SAMPLES_SHA256 = "8b02bd5212d0ba47346d81af812be24ddf46d9e9ff9f19d3071754217ddcb35a"
TEST_SELECTED_SAMPLES_SHA256 = "6b86e5f4452546a256b40595ce1d91445a9ce1cf9196652060ff275acc656dc9"
TEST_INDEX_NAME = "test-confirmation.npy"
GATE_SAMPLES = 10_000
TARGET_ACCURACY = 0.70


def load_or_evaluate_result(path: Path, evaluate_result: Callable[[], None]) -> dict:
    """Resume validation of an already-written result after a process interruption."""
    if not path.exists():
        evaluate_result()
    return json.loads(path.read_text())


def validate_cluster_bootstrap(evaluation: dict, accuracy: float) -> dict:
    uncertainty = evaluation.get("autoregressive_exact_action_cluster_bootstrap")
    if not isinstance(uncertainty, dict) or uncertainty.get("available") is not True:
        raise ValueError("evaluation lacks replay-cluster uncertainty")
    expected = {
        "cluster_unit": "replay_id",
        "samples": GATE_SAMPLES,
        "confidence_level": CLUSTER_BOOTSTRAP_CONFIDENCE,
        "method": CLUSTER_BOOTSTRAP_METHOD,
        "resamples": CLUSTER_BOOTSTRAP_RESAMPLES,
        "seed": CLUSTER_BOOTSTRAP_SEED,
    }
    if any(uncertainty.get(key) != value for key, value in expected.items()):
        raise ValueError("replay-cluster uncertainty contract mismatch")
    clusters = uncertainty.get("clusters")
    correct = uncertainty.get("correct")
    if not isinstance(clusters, int) or not 2 <= clusters <= GATE_SAMPLES:
        raise ValueError("replay-cluster count is invalid")
    if not isinstance(correct, int) or correct != round(accuracy * GATE_SAMPLES):
        raise ValueError("replay-cluster correct count does not match accuracy")
    point = uncertainty.get("point_estimate")
    lower = uncertainty.get("lower")
    upper = uncertainty.get("upper")
    if not all(isinstance(value, (int, float)) for value in (point, lower, upper)):
        raise ValueError("replay-cluster interval is invalid")
    if not all(math.isfinite(value) for value in (point, lower, upper)):
        raise ValueError("replay-cluster interval is non-finite")
    if not math.isclose(point, accuracy, rel_tol=0, abs_tol=1e-12):
        raise ValueError("replay-cluster point estimate does not match accuracy")
    if not 0 <= lower <= point <= upper <= 1:
        raise ValueError("replay-cluster interval bounds are invalid")
    return uncertainty


def validate_validation_gate(
    evaluation: dict,
    *,
    checkpoint_sha256: str,
    action_encoding: str,
    spatial_semantics: bool,
) -> float:
    if evaluation.get("sample_indices_sha256") != VALIDATION_INDEX_SHA256:
        raise ValueError("validation evaluation is not tied to the frozen index")
    if evaluation.get("sample_dataset_fingerprint") != VALIDATION_DATASET_FINGERPRINT:
        raise ValueError("validation evaluation is not tied to the frozen dataset")
    if (
        evaluation.get("selected_samples_sha256")
        != VALIDATION_SELECTED_SAMPLES_SHA256
    ):
        raise ValueError("validation evaluation is not tied to the frozen sample rows")
    maps_fingerprint = evaluation.get("maps_fingerprint")
    if not isinstance(maps_fingerprint, str) or len(maps_fingerprint) != 64:
        raise ValueError("validation evaluation does not attest the map set")
    if (
        not isinstance(evaluation.get("maps_count"), int)
        or evaluation["maps_count"] <= 0
    ):
        raise ValueError("validation evaluation does not attest a non-empty map set")
    if evaluation.get("checkpoint_sha256") != checkpoint_sha256:
        raise ValueError("validation evaluation is not tied to this checkpoint")
    if evaluation.get("max_text_tokens") != 4096:
        raise ValueError("validation evaluation must use 4096 text tokens")
    if evaluation.get("action_encoding", "absolute") != action_encoding:
        raise ValueError("validation action encoding does not match the checkpoint")
    if bool(evaluation.get("include_spatial_semantics", False)) != spatial_semantics:
        raise ValueError("validation spatial representation does not match the checkpoint")
    metrics = evaluation.get("groups", {}).get("all", {})
    if metrics.get("samples") != GATE_SAMPLES:
        raise ValueError(f"validation gate must contain exactly {GATE_SAMPLES} rows")
    accuracy = metrics.get("autoregressive_exact_action_accuracy")
    if not isinstance(accuracy, (int, float)) or accuracy <= TARGET_ACCURACY:
        raise ValueError(
            "validation autoregressive exact action must exceed "
            f"{TARGET_ACCURACY:.0%}; got {accuracy!r}"
        )
    validate_cluster_bootstrap(evaluation, float(accuracy))
    return float(accuracy)


def require_frozen_index(path: Path, expected: str, name: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"{name} index hash mismatch: {actual}")


def require_frozen_dataset(path: Path, expected: str, name: str) -> None:
    actual = str(load_arrow_dataset(path)._fingerprint)
    if actual != expected:
        raise ValueError(f"{name} dataset fingerprint mismatch: {actual}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--validation-evaluation", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    decision_path = args.out.with_suffix(".sealed-decision.json")
    if decision_path.exists():
        parser.error(f"sealed decision already exists: {decision_path}")
    policy_config = json.loads((args.checkpoint / "policy_config.json").read_text())
    action_encoding = policy_config.get("action_encoding", "absolute")
    checkpoint_sha256 = sha256_tree(args.checkpoint)
    training_run_path = args.checkpoint.parent / "training_run.json"
    training_run = (
        json.loads(training_run_path.read_text()) if training_run_path.exists() else {}
    )
    spatial_semantics = bool(training_run.get("include_spatial_semantics", False))
    validation = json.loads(args.validation_evaluation.read_text())
    try:
        validation_accuracy = validate_validation_gate(
            validation,
            checkpoint_sha256=checkpoint_sha256,
            action_encoding=action_encoding,
            spatial_semantics=spatial_semantics,
        )
        validation_index = args.workspace / "indices" / "validation.npy"
        test_index = args.workspace / "indices" / TEST_INDEX_NAME
        require_frozen_index(
            validation_index, VALIDATION_INDEX_SHA256, "validation"
        )
        require_frozen_index(test_index, TEST_INDEX_SHA256, "test")
        require_frozen_dataset(
            args.workspace / "arrow" / "validation",
            VALIDATION_DATASET_FINGERPRINT,
            "validation",
        )
        require_frozen_dataset(
            args.workspace / "arrow" / "test", TEST_DATASET_FINGERPRINT, "test"
        )
        validation_maps = args.workspace / "prepared" / "validation.maps.jsonl"
        test_maps = args.workspace / "prepared" / "test.maps.jsonl"
        if not validation_maps.samefile(test_maps):
            raise ValueError("validation and test do not use the same frozen map table")
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))

    result = load_or_evaluate_result(
        args.out,
        lambda: evaluate(
            args.checkpoint,
            args.workspace / "arrow" / "test",
            args.workspace / "prepared" / "test.maps.jsonl",
            test_index,
            args.out,
            spatial_semantics=spatial_semantics,
            action_encoding=action_encoding,
        ),
    )
    if result.get("sample_indices_sha256") != TEST_INDEX_SHA256:
        raise RuntimeError("evaluator did not attest the frozen test index")
    if result.get("sample_dataset_fingerprint") != TEST_DATASET_FINGERPRINT:
        raise RuntimeError("evaluator did not attest the frozen test dataset")
    if result.get("selected_samples_sha256") != TEST_SELECTED_SAMPLES_SHA256:
        raise RuntimeError("evaluator did not attest the frozen test sample rows")
    if result.get("checkpoint_sha256") != checkpoint_sha256:
        raise RuntimeError("evaluator did not attest the selected checkpoint")
    if result.get("maps_fingerprint") != validation["maps_fingerprint"]:
        raise RuntimeError("test and validation map-set attestations differ")
    if result.get("maps_count") != validation["maps_count"]:
        raise RuntimeError("test and validation map counts differ")
    metrics = result["groups"]["all"]
    if metrics["samples"] != GATE_SAMPLES:
        raise RuntimeError("sealed evaluation did not contain exactly 10,000 rows")
    test_accuracy = float(metrics["autoregressive_exact_action_accuracy"])
    uncertainty = validate_cluster_bootstrap(result, test_accuracy)
    decision = {
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": checkpoint_sha256,
        "validation_index_sha256": VALIDATION_INDEX_SHA256,
        "test_index_sha256": TEST_INDEX_SHA256,
        "validation_dataset_fingerprint": VALIDATION_DATASET_FINGERPRINT,
        "test_dataset_fingerprint": TEST_DATASET_FINGERPRINT,
        "validation_selected_samples_sha256": VALIDATION_SELECTED_SAMPLES_SHA256,
        "test_selected_samples_sha256": TEST_SELECTED_SAMPLES_SHA256,
        "maps_fingerprint": validation["maps_fingerprint"],
        "maps_count": validation["maps_count"],
        "validation_exact_action_accuracy": validation_accuracy,
        "test_exact_action_accuracy": test_accuracy,
        "test_cluster_bootstrap_95_percent_interval": [
            uncertainty["lower"],
            uncertainty["upper"],
        ],
        "test_cluster_bootstrap_lower_exceeds_target": (
            uncertainty["lower"] > TARGET_ACCURACY
        ),
        "target_accuracy": TARGET_ACCURACY,
        "passed": test_accuracy > TARGET_ACCURACY,
    }
    decision_path.write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps(decision, indent=2))
    return 0 if decision["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
