#!/usr/bin/env python3
"""Open the frozen test once for a checkpoint that already clears validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluate_sft import sha256_file, sha256_tree
from run_expert_training import evaluate


VALIDATION_INDEX_SHA256 = "78e46be391cf13c6c488b6b0ed2ccd0fe1da36eb73d13fb6db5a42c0f8d50644"
TEST_INDEX_SHA256 = "244dad9d331ab92c2a852c1f7ca1ae31d5892c48e11acf08cb31c6f65577dbdb"
GATE_SAMPLES = 10_000
TARGET_ACCURACY = 0.70


def validate_validation_gate(
    evaluation: dict,
    *,
    checkpoint_sha256: str,
    action_encoding: str,
    spatial_semantics: bool,
) -> float:
    if evaluation.get("sample_indices_sha256") != VALIDATION_INDEX_SHA256:
        raise ValueError("validation evaluation is not tied to the frozen index")
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
    return float(accuracy)


def require_frozen_index(path: Path, expected: str, name: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"{name} index hash mismatch: {actual}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--validation-evaluation", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    decision_path = args.out.with_suffix(".sealed-decision.json")
    if args.out.exists() or decision_path.exists():
        parser.error(f"refusing to overwrite an existing sealed result: {args.out}")
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
        test_index = args.workspace / "indices" / "test.npy"
        require_frozen_index(
            validation_index, VALIDATION_INDEX_SHA256, "validation"
        )
        require_frozen_index(test_index, TEST_INDEX_SHA256, "test")
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))

    evaluate(
        args.checkpoint,
        args.workspace / "arrow" / "test",
        args.workspace / "prepared" / "test.maps.jsonl",
        test_index,
        args.out,
        spatial_semantics=spatial_semantics,
        action_encoding=action_encoding,
    )
    result = json.loads(args.out.read_text())
    if result.get("sample_indices_sha256") != TEST_INDEX_SHA256:
        raise RuntimeError("evaluator did not attest the frozen test index")
    if result.get("checkpoint_sha256") != checkpoint_sha256:
        raise RuntimeError("evaluator did not attest the selected checkpoint")
    metrics = result["groups"]["all"]
    if metrics["samples"] != GATE_SAMPLES:
        raise RuntimeError("sealed evaluation did not contain exactly 10,000 rows")
    test_accuracy = float(metrics["autoregressive_exact_action_accuracy"])
    decision = {
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": checkpoint_sha256,
        "validation_index_sha256": VALIDATION_INDEX_SHA256,
        "test_index_sha256": TEST_INDEX_SHA256,
        "validation_exact_action_accuracy": validation_accuracy,
        "test_exact_action_accuracy": test_accuracy,
        "target_accuracy": TARGET_ACCURACY,
        "passed": test_accuracy > TARGET_ACCURACY,
    }
    decision_path.write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps(decision, indent=2))
    return 0 if decision["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
