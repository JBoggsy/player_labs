import json
import sys
from types import SimpleNamespace

import torch

import evaluate_sft
from actions import ACTION_TOKENS, UP, canonical_action_tokens


def test_evaluator_separates_autoregressive_from_teacher_forced_exact(
    tmp_path, monkeypatch
) -> None:
    token_ids = {token: index for index, token in enumerate(ACTION_TOKENS)}
    target_tokens = canonical_action_tokens(UP)
    target_ids = [token_ids[token] for token in target_tokens]

    class Tokenizer:
        def convert_tokens_to_ids(self, token):
            return token_ids[token]

    sample = SimpleNamespace(
        game_version="40",
        map_hash="map",
        previous_mask=0,
        target_mask=UP,
        replay_id="replay",
        position=lambda: (0.0, 0.0),
    )

    class Dataset:
        maps = {"map": object()}

        def __init__(self, *args):
            pass

        def __iter__(self):
            yield sample

    class Collator:
        def __init__(self, *args, **kwargs):
            pass

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
    assert metrics["constrained_exact_action_accuracy"] == 0.0
    assert metrics["autoregressive_exact_action_accuracy"] == 1.0
    assert metrics["autoregressive_changed_exact_action_accuracy"] == 1.0
