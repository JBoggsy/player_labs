import hashlib
import json
from pathlib import Path

import pytest

from evaluate_sft import sha256_tree
from evaluate_sealed_candidate import (
    GATE_SAMPLES,
    TEST_INDEX_NAME,
    TEST_INDEX_SHA256,
    TEST_SELECTED_SAMPLES_SHA256,
    VALIDATION_DATASET_FINGERPRINT,
    VALIDATION_INDEX_SHA256,
    VALIDATION_SELECTED_SAMPLES_SHA256,
    require_frozen_dataset,
    require_frozen_index,
    validate_validation_gate,
)
from evaluation_uncertainty import (
    CLUSTER_BOOTSTRAP_CONFIDENCE,
    CLUSTER_BOOTSTRAP_METHOD,
    CLUSTER_BOOTSTRAP_RESAMPLES,
    CLUSTER_BOOTSTRAP_SEED,
)


def test_confirmation_manifest_matches_sealed_gate() -> None:
    manifest = json.loads(
        (Path(__file__).parent / "configs" / "confirmation-holdout-v1.json").read_text()
    )

    assert Path(manifest["confirmation_index"]).name == TEST_INDEX_NAME
    assert manifest["confirmation_index_sha256"] == TEST_INDEX_SHA256
    assert manifest["selected_samples_sha256"] == TEST_SELECTED_SAMPLES_SHA256
    assert manifest["selected"] == GATE_SAMPLES
    assert manifest["independent_verification"]["old_new_replay_overlap"] == 0
    assert manifest["evaluation_uncertainty"] == {
        "cluster_unit": "replay_id",
        "confidence_level": CLUSTER_BOOTSTRAP_CONFIDENCE,
        "method": CLUSTER_BOOTSTRAP_METHOD,
        "resamples": CLUSTER_BOOTSTRAP_RESAMPLES,
        "seed": CLUSTER_BOOTSTRAP_SEED,
    }


def validation(
    accuracy: float,
    *,
    samples: int = GATE_SAMPLES,
    index_hash: str = VALIDATION_INDEX_SHA256,
    checkpoint_hash: str = "checkpoint",
) -> dict:
    correct = round(accuracy * samples) if isinstance(accuracy, (int, float)) else 0
    return {
        "sample_indices_sha256": index_hash,
        "sample_dataset_fingerprint": VALIDATION_DATASET_FINGERPRINT,
        "selected_samples_sha256": VALIDATION_SELECTED_SAMPLES_SHA256,
        "maps_fingerprint": "a" * 64,
        "maps_count": 123,
        "checkpoint_sha256": checkpoint_hash,
        "max_text_tokens": 4096,
        "action_encoding": "absolute",
        "include_spatial_semantics": False,
        "autoregressive_exact_action_cluster_bootstrap": {
            "cluster_unit": "replay_id",
            "clusters": samples // 2,
            "samples": samples,
            "correct": correct,
            "point_estimate": accuracy,
            "confidence_level": 0.95,
            "method": "BCa",
            "resamples": 9999,
            "seed": 20260814,
            "available": True,
            "lower": max(0.0, accuracy - 0.01),
            "upper": min(1.0, accuracy + 0.01),
            "standard_error": 0.005,
        },
        "groups": {
            "all": {
                "samples": samples,
                "autoregressive_exact_action_accuracy": accuracy,
            }
        },
    }


def test_sealed_gate_requires_frozen_index_size_and_strictly_over_70() -> None:
    kwargs = {
        "checkpoint_sha256": "checkpoint",
        "action_encoding": "absolute",
        "spatial_semantics": False,
    }
    assert validate_validation_gate(validation(0.7001), **kwargs) == 0.7001
    with pytest.raises(ValueError, match="must exceed"):
        validate_validation_gate(validation(0.70), **kwargs)
    with pytest.raises(ValueError, match="exactly 10000"):
        validate_validation_gate(validation(0.8, samples=9_999), **kwargs)
    with pytest.raises(ValueError, match="frozen index"):
        validate_validation_gate(validation(0.8, index_hash="wrong"), **kwargs)
    substituted_dataset = validation(0.8)
    substituted_dataset["sample_dataset_fingerprint"] = "wrong"
    with pytest.raises(ValueError, match="frozen dataset"):
        validate_validation_gate(substituted_dataset, **kwargs)
    substituted_rows = validation(0.8)
    substituted_rows["selected_samples_sha256"] = "wrong"
    with pytest.raises(ValueError, match="frozen sample rows"):
        validate_validation_gate(substituted_rows, **kwargs)
    with pytest.raises(ValueError, match="this checkpoint"):
        validate_validation_gate(
            validation(0.8, checkpoint_hash="other"), **kwargs
        )


def test_sealed_gate_rejects_teacher_forced_proxy() -> None:
    evaluation = validation(0.8)
    metrics = evaluation["groups"]["all"]
    metrics.pop("autoregressive_exact_action_accuracy")
    metrics["constrained_exact_action_accuracy"] = 0.99

    with pytest.raises(ValueError, match="must exceed"):
        validate_validation_gate(
            evaluation,
            checkpoint_sha256="checkpoint",
            action_encoding="absolute",
            spatial_semantics=False,
        )


def test_sealed_gate_requires_fixed_replay_cluster_uncertainty() -> None:
    evaluation = validation(0.8)
    evaluation["autoregressive_exact_action_cluster_bootstrap"]["seed"] = 7

    with pytest.raises(ValueError, match="uncertainty contract"):
        validate_validation_gate(
            evaluation,
            checkpoint_sha256="checkpoint",
            action_encoding="absolute",
            spatial_semantics=False,
        )


def test_frozen_index_check_hashes_exact_bytes(tmp_path) -> None:
    path = tmp_path / "index.npy"
    path.write_bytes(b"frozen-index")
    digest = hashlib.sha256(b"frozen-index").hexdigest()

    require_frozen_index(path, digest, "test")
    with pytest.raises(ValueError, match="hash mismatch"):
        require_frozen_index(path, "0" * 64, "test")


def test_frozen_dataset_check_uses_arrow_fingerprint(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "evaluate_sealed_candidate.load_arrow_dataset",
        lambda path: type("Dataset", (), {"_fingerprint": "frozen"})(),
    )

    require_frozen_dataset(tmp_path, "frozen", "validation")
    with pytest.raises(ValueError, match="dataset fingerprint mismatch"):
        require_frozen_dataset(tmp_path, "other", "validation")


def test_checkpoint_tree_hash_binds_names_and_contents(tmp_path) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    (checkpoint / "policy_config.json").write_text("config")
    adapter = checkpoint / "adapter"
    adapter.mkdir()
    (adapter / "weights").write_bytes(b"weights")

    first = sha256_tree(checkpoint)
    (adapter / "weights").write_bytes(b"changed")
    assert sha256_tree(checkpoint) != first
