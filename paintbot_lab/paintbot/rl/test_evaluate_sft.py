import json
import sys
from types import SimpleNamespace

import numpy as np
import torch

import evaluate_sft
from actions import ACTION_TOKENS, UP, canonical_action_tokens
from dataset import SFTSample
from observation_text import EntitySnapshot, ObservationSnapshot


def test_evaluator_separates_autoregressive_from_teacher_forced_exact(
    tmp_path, monkeypatch
) -> None:
    token_ids = {token: index for index, token in enumerate(ACTION_TOKENS)}
    target_tokens = canonical_action_tokens(UP)
    target_ids = [token_ids[token] for token in target_tokens]

    class Tokenizer:
        def convert_tokens_to_ids(self, token):
            return token_ids[token]

    observation = ObservationSnapshot(
        game_version="40",
        frame=1,
        map_width=8,
        map_height=8,
        entities=(EntitySnapshot(1, "self red right", 0, 0, 0, 0, 1, 1),),
        tick=1,
    ).to_dict()
    sample = SFTSample(
        "replay", "40", 0, 1, 1, "map", observation, 0, UP
    )

    class Dataset:
        maps = {"map": SimpleNamespace(mask=lambda: np.ones((8, 8)))}
        arrow = SimpleNamespace(_fingerprint="dataset-fingerprint")

        def __init__(self, *args):
            pass

        def __iter__(self):
            yield sample

        def __len__(self):
            return 1

    class Collator:
        def __init__(self, *args, **kwargs):
            self.maps = args[1]

        def __call__(self, samples):
            return {
                "input_ids": torch.tensor([[99, *target_ids]]),
                "labels": torch.tensor([[-100, *target_ids]]),
                "attention_mask": torch.ones((1, 6), dtype=torch.long),
                "maps": [torch.zeros((8, 8))],
                "positions": [(0.0, 0.0)],
            }

        def _prompt_ids(self, sample, target_length):
            return [99]

    class Model:
        action_encoding = "absolute"
        map_encoder = SimpleNamespace(
            config=SimpleNamespace(token_count=1),
            encode_static=lambda mask: object(),
        )

        def __call__(self, **batch):
            # Zero logits choose the first legal token in every teacher-forced
            # slot, making movement idle instead of the target UP.
            return SimpleNamespace(
                logits=torch.zeros((1, 7, len(ACTION_TOKENS) + 1)),
                loss=torch.tensor(0.5),
            )

        def greedy_action(self, *args):
            return target_tokens

    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    (checkpoint / "weights").write_text("fake")
    output = tmp_path / "evaluation.json"
    monkeypatch.setattr(evaluate_sft, "PolicyDataset", Dataset)
    monkeypatch.setattr(evaluate_sft, "PolicyCollator", Collator)
    monkeypatch.setattr(
        evaluate_sft, "load_policy", lambda *args, **kwargs: (Tokenizer(), Model())
    )
    monkeypatch.setattr(evaluate_sft, "evaluation_device", lambda: torch.device("cpu"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_sft.py",
            "--checkpoint",
            str(checkpoint),
            "--samples",
            str(tmp_path / "samples"),
            "--maps",
            str(tmp_path / "maps"),
            "--out",
            str(output),
        ],
    )

    assert evaluate_sft.main() == 0
    metrics = json.loads(output.read_text())["groups"]["all"]
    evaluation = json.loads(output.read_text())
    assert evaluation["sample_dataset_fingerprint"] == "dataset-fingerprint"
    assert len(evaluation["selected_samples_sha256"]) == 64
    assert evaluation["maps_count"] == 1
    assert len(evaluation["maps_fingerprint"]) == 64
    uncertainty = evaluation["autoregressive_exact_action_cluster_bootstrap"]
    assert uncertainty["available"] is False
    assert uncertainty["point_estimate"] == 1.0
    assert uncertainty["clusters"] == 1
    assert metrics["constrained_exact_action_accuracy"] == 0.0
    assert metrics["autoregressive_exact_action_accuracy"] == 1.0
    assert metrics["autoregressive_changed_exact_action_accuracy"] == 1.0
