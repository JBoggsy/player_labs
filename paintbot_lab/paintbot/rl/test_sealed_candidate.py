import hashlib

import pytest

from evaluate_sft import sha256_tree
from evaluate_sealed_candidate import (
    GATE_SAMPLES,
    VALIDATION_INDEX_SHA256,
    require_frozen_index,
    validate_validation_gate,
)


def validation(
    accuracy: float,
    *,
    samples: int = GATE_SAMPLES,
    index_hash: str = VALIDATION_INDEX_SHA256,
    checkpoint_hash: str = "checkpoint",
) -> dict:
    return {
        "sample_indices_sha256": index_hash,
        "checkpoint_sha256": checkpoint_hash,
        "max_text_tokens": 4096,
        "action_encoding": "absolute",
        "include_spatial_semantics": False,
        "groups": {
            "all": {
                "samples": samples,
                "constrained_exact_action_accuracy": accuracy,
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
    with pytest.raises(ValueError, match="this checkpoint"):
        validate_validation_gate(
            validation(0.8, checkpoint_hash="other"), **kwargs
        )


def test_frozen_index_check_hashes_exact_bytes(tmp_path) -> None:
    path = tmp_path / "index.npy"
    path.write_bytes(b"frozen-index")
    digest = hashlib.sha256(b"frozen-index").hexdigest()

    require_frozen_index(path, digest, "test")
    with pytest.raises(ValueError, match="hash mismatch"):
        require_frozen_index(path, "0" * 64, "test")


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
