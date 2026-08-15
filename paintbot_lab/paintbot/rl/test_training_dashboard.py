import json
from pathlib import Path

from training_dashboard import (
    PROGRESS_RATE_POINTS,
    build_snapshot,
    estimate_eta,
    full_training_log,
    observed_progress_points,
    parse_training_log,
)


def test_parse_training_log_extracts_progress_validation_and_errors() -> None:
    parsed = parse_training_log(
        "epoch=1 step=100 loss=0.4\n"
        "epoch=1 validation_loss=0.3\n"
        "epoch=2 step=50 loss=0.2\n"
        "RuntimeError: failed safely\n"
    )

    assert parsed["latest"] == {"epoch": 2, "step": 50, "loss": 0.2}
    assert parsed["validations"] == [{"epoch": 1, "loss": 0.3}]
    assert parsed["errors"] == ["RuntimeError: failed safely"]


def test_full_training_log_excludes_canary_metrics() -> None:
    text = (
        "+ python train_sft.py --output runs/x/training-v1/canary\n"
        "epoch=1 validation_loss=1.2\n"
        "+ python train_sft.py --output runs/x/training-v1/full\n"
        "epoch=1 validation_loss=0.3\n"
    )

    parsed = parse_training_log(full_training_log(text))

    assert parsed["validations"] == [{"epoch": 1, "loss": 0.3}]


def test_snapshot_reports_microbatch_progress_and_evaluation(tmp_path: Path) -> None:
    workspace = tmp_path / "runs/expert-corpus-v1"
    training = workspace / "training-v1"
    output = training / "full"
    output.mkdir(parents=True)
    (training / "status.json").write_text(
        json.dumps({"stage": "training_full", "train_budget": 100, "epochs": 3})
    )
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "expert-training-v1.log").write_text(
        "epoch=1 validation_loss=0.4\nepoch=2 step=25 loss=0.2\n"
    )
    evaluation = {
        "groups": {
            "all": {
                "samples": 10,
                "constrained_exact_action_accuracy": 0.3,
                "autoregressive_exact_action_accuracy": 0.25,
            }
        }
    }
    (output / "test_evaluation.json").write_text(json.dumps(evaluation))

    def command_output(command: list[str]) -> str:
        if command[0] == "pgrep":
            return "1 python train_sft.py --batch-size 2"
        if command[0] == "nvidia-smi":
            return "RTX 4090, 12000, 24000, 99, 70"
        return ""

    snapshot = build_snapshot(workspace, command_output)

    assert snapshot["healthy"] is True
    assert snapshot["progress"]["steps_per_epoch"] == 50
    assert snapshot["progress"]["completed_microbatches"] == 75
    assert snapshot["progress"]["fraction"] == 0.5
    assert snapshot["validation_history"] == [{"epoch": 1, "loss": 0.4}]
    assert snapshot["gpu"]["utilization_percent"] == 99
    assert snapshot["evaluations"]["test_evaluation.json"][
        "constrained_exact_action_accuracy"
    ] == 0.3
    assert snapshot["evaluations"]["test_evaluation.json"][
        "autoregressive_exact_action_accuracy"
    ] == 0.25


def test_snapshot_marks_missing_trainer_unhealthy(tmp_path: Path) -> None:
    workspace = tmp_path / "runs/expert-corpus-v1"
    training = workspace / "training-v1"
    training.mkdir(parents=True)
    (training / "status.json").write_text(
        json.dumps({"stage": "training_full", "train_budget": 100, "epochs": 3})
    )

    snapshot = build_snapshot(workspace, lambda command: "")

    assert snapshot["healthy"] is False


def test_observed_progress_produces_eta_before_checkpoint() -> None:
    PROGRESS_RATE_POINTS.clear()
    observed_progress_points("run", 100.0, 100)
    points = observed_progress_points("run", 110.0, 120)

    assert estimate_eta(points, 80) == {"seconds": 40.0, "rate_per_second": 2.0}
