import json
import sys
from pathlib import Path

import run_expert_training


def test_unattended_run_evaluates_validation_without_opening_test(
    tmp_path: Path, monkeypatch
) -> None:
    workspace = tmp_path / "corpus"
    output = workspace / "training-v1"
    prepared = workspace / "prepared"
    prepared.mkdir(parents=True)
    (prepared / "provenance.json").write_text("{}\n")
    for run in (output / "canary", output / "full"):
        run.mkdir(parents=True)
        (run / "training_run.json").write_text("{}\n")
    (output / "canary" / "validation_evaluation.json").write_text("{}\n")

    monkeypatch.setattr(
        run_expert_training,
        "convert_corpus",
        lambda manifest, corpus: {"train": 1, "validation": 1, "test": 1},
    )
    monkeypatch.setattr(run_expert_training, "ensure_indices", lambda *args: None)
    evaluations = []
    monkeypatch.setattr(
        run_expert_training,
        "evaluate",
        lambda checkpoint, samples, maps, indices, result: evaluations.append(
            (checkpoint, samples, maps, indices, result)
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_expert_training.py",
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--workspace",
            str(workspace),
            "--output",
            str(output),
        ],
    )

    assert run_expert_training.main() == 0
    assert evaluations == [
        (
            output / "full" / "best",
            workspace / "arrow" / "validation",
            prepared / "validation.maps.jsonl",
            workspace / "indices" / "validation.npy",
            output / "full" / "validation_evaluation.json",
        )
    ]
    assert json.loads((output / "status.json").read_text())["stage"] == "complete"


def test_train_command_can_combine_event_and_spatial_representations(
    tmp_path: Path,
) -> None:
    command = run_expert_training.train_command(
        tmp_path / "train",
        tmp_path / "maps",
        tmp_path / "indices.npy",
        tmp_path / "validation",
        tmp_path / "validation-maps",
        tmp_path / "validation-indices.npy",
        tmp_path / "output",
        epochs=1,
        checkpoint_every_updates=1_000,
        spatial_semantics=True,
        action_encoding="events",
    )

    assert "--spatial-semantics" in command
    assert command[command.index("--action-encoding") + 1] == "events"
