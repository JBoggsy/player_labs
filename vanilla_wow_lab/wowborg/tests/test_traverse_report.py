"""Focused integration test for the Traverse episode report."""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

from test_cwreplay_tool import build_replay

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
SPEC = importlib.util.spec_from_file_location(
    "traverse_report_test_module", TOOLS_DIR / "traverse_report.py"
)
assert SPEC is not None and SPEC.loader is not None
traverse_report = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = traverse_report
SPEC.loader.exec_module(traverse_report)


def test_reports_score_trace_and_living_replay_metrics(tmp_path: Path) -> None:
    episode_dir = tmp_path / "episode"
    artifacts = episode_dir / "artifacts"
    artifacts.mkdir(parents=True)
    (episode_dir / "episode.json").write_text(
        json.dumps(
            {
                "id": "ereq_test",
                "episode_id": "episode_test",
                "job_id": "job_test",
                "participants": [
                    {"position": 0, "policy_name": "wowborg", "version": 63}
                ],
                "participant_scores": [{"position": 0, "score": 1000.0}],
                "game_config": {
                    "kalimdor_traversal": {
                        "start_world_x": -9187.0,
                        "goal_world_x": 6687.333052,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (episode_dir / "replay.json").write_bytes(build_replay(tmp_path).read_bytes())
    events = [
        {"ts": 1784000000.0, "kind": "observation", "is_dead": False, "is_ghost": False},
        {"ts": 1784000001.0, "kind": "observation", "is_dead": True, "is_ghost": False},
        {"ts": 1784000002.0, "kind": "observation", "is_dead": False, "is_ghost": True},
        {"ts": 1784000005.0, "kind": "observation", "is_dead": False, "is_ghost": False},
        {"ts": 1784000005.0, "kind": "traverse_travel_form", "activation": 1, "success": True},
        {
            "ts": 1784000006.0,
            "kind": "strategy_end",
            "strategy": "traverse",
            "frontiers_attempted": 4,
            "frontiers_arrived": 3,
            "route_failures": 1,
        },
    ]
    with zipfile.ZipFile(artifacts / "policy_artifact_0.zip", "w") as bundle:
        bundle.writestr("trace.jsonl", "".join(json.dumps(event) + "\n" for event in events))

    report = traverse_report.report_episode(episode_dir)

    assert report["trace_available"] is True
    assert report["score"]["northing_yards"] == 1000.0
    assert report["score"]["authoritative_world_x"] == -8187.0
    assert report["lifecycle"] == {
        "deaths": 1,
        "ghost_seconds": 3.0,
        "dead_or_ghost_seconds": 4.0,
    }
    assert report["frontiers"] == {"attempted": 4, "arrived": 3, "failures": 1}
    assert report["travel_form"]["activation_trace"][0]["success"] is True
    assert report["replay"]["trajectory_yards"] == 5.0
    speed = report["replay"]["living_forward_speed_yards_per_second"]
    assert speed["samples"] == 1
    assert speed["median"] == 25.0


def test_marks_trace_only_metrics_unavailable_when_artifact_is_missing(
    tmp_path: Path,
) -> None:
    episode_dir = tmp_path / "episode"
    episode_dir.mkdir()
    (episode_dir / "episode.json").write_text(
        json.dumps(
            {
                "participants": [{"policy_name": "wowborg", "version": 63}],
                "participant_scores": [{"score": 1000.0}],
                "game_config": {
                    "kalimdor_traversal": {
                        "start_world_x": -9187.0,
                        "goal_world_x": 6687.333052,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (episode_dir / "replay.json").write_bytes(build_replay(tmp_path).read_bytes())

    report = traverse_report.report_episode(episode_dir)

    assert report["trace_available"] is False
    assert report["lifecycle"] == {
        "deaths": None,
        "ghost_seconds": None,
        "dead_or_ghost_seconds": None,
    }
    assert report["frontiers"] == {
        "attempted": None,
        "arrived": None,
        "failures": None,
    }
