"""Focused tests for the stateful replay batch profiler."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
SPEC = importlib.util.spec_from_file_location(
    "wow_batch_profiler_test_module", TOOLS_DIR / "wow_batch_profiler.py"
)
assert SPEC is not None and SPEC.loader is not None
profiler = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = profiler
SPEC.loader.exec_module(profiler)


def incident(t: float, x: float, *, stationary: float, outcome: str) -> dict:
    return {
        "requested_elapsed_seconds": t,
        "preceding_stationary_seconds": stationary,
        "origin": {"map_id": 1, "x": x, "y": 2.0, "z": 3.0, "orientation": 0.0},
        "outcome": outcome,
        "failure_elapsed_seconds": t + 0.5 if outcome == "cast_failed" else None,
        "relocation_elapsed_seconds": t + 2.0 if outcome == "relocated" else None,
    }


def test_cluster_unstuck_incidents_collapses_retry_bursts() -> None:
    clusters = profiler.cluster_unstuck_incidents(
        [
            incident(10.0, 1.0, stationary=5.0, outcome="cast_failed"),
            incident(14.0, 1.5, stationary=9.0, outcome="relocated"),
            incident(100.0, 40.0, stationary=6.0, outcome="cast_failed"),
        ]
    )

    assert len(clusters) == 2
    assert clusters[0]["duration_seconds"] == 11.0
    assert clusters[0]["invocations"] == 2
    assert clusters[0]["outcomes"] == {"cast_failed": 1, "relocated": 1}


def test_interval_union_seconds_does_not_double_count_overlap() -> None:
    assert profiler.interval_union_seconds([(0.0, 10.0), (5.0, 12.0), (20.0, 25.0)]) == 17.0


def test_discover_replays_accepts_episode_and_batch_directories(tmp_path: Path) -> None:
    first = tmp_path / "one"
    second = tmp_path / "nested" / "two"
    first.mkdir()
    second.mkdir(parents=True)
    (first / "replay.json").write_bytes(b"CWREPLAY")
    (second / "replay.cwreplay").write_bytes(b"CWREPLAY")

    assert profiler.discover_replays([first]) == [(first / "replay.json").resolve()]
    assert profiler.discover_replays([tmp_path]) == [
        (second / "replay.cwreplay").resolve(),
        (first / "replay.json").resolve(),
    ]


def test_unique_replays_deduplicates_exact_content(tmp_path: Path) -> None:
    first = tmp_path / "first.replay"
    duplicate = tmp_path / "duplicate.replay"
    different = tmp_path / "different.replay"
    first.write_bytes(b"same")
    duplicate.write_bytes(b"same")
    different.write_bytes(b"different")

    unique, duplicates = profiler.unique_replays([first, duplicate, different])

    assert unique == [first, different]
    assert duplicates == [{"replay": str(duplicate), "same_as": str(first)}]


def test_replay_metadata_reads_request_episode(tmp_path: Path) -> None:
    request = tmp_path / "xreq_123" / "episode"
    request.mkdir(parents=True)
    replay = request / "replay.json"
    replay.write_bytes(b"replay")
    (request / "episode.json").write_text(
        '{"episode_id":"episode-1","created_at":"now",'
        '"participants":[{"policy_name":"wowborg","version":69}],'
        '"participant_scores":[{"score":42.5}]}',
        encoding="utf-8",
    )

    assert profiler.replay_metadata(replay) == {
        "episode_id": "episode-1",
        "experience_request_id": "xreq_123",
        "created_at": "now",
        "policy_version": 69,
        "score": 42.5,
    }


def test_aggregate_preserves_life_stuck_combat_and_spell_totals() -> None:
    row = {
        "replay": "/tmp/replay.json",
        "life": {
            "end": "ghost",
            "seconds": {"alive": 10.0, "dead": 1.0, "ghost": 9.0, "unknown": 0.0},
            "deaths": [{"elapsed_seconds": 10.0}],
        },
        "movement": {
            "stuck_episode_count": 2,
            "stuck_episodes": [{"duration_seconds": 8.0}],
            "stuck_union_seconds": 8.0,
            "unstuck_invocations": 5,
            "longest_stationary_seconds": 8.0,
        },
        "combat": {
            "damage_in": 100,
            "damage_out": 25,
            "attack_packets": 3,
            "damage_sources": [
                {"guid": "7", "entry": 42, "name": "Mob", "damage": 100, "event_count": 4}
            ],
        },
        "spells": {"requests": {"783": 1}, "effects": {"783": 1}},
        "recovery": {
            "release_spirit": 1,
            "reclaim_corpse": 1,
            "spirit_healer": 0,
            "spirit_healer_confirmed": 0,
            "resurrect_responses": 0,
        },
    }

    summary = profiler.aggregate([row, row])

    assert summary["replays"] == 1
    assert summary["members"] == 2
    assert summary["ended_ghost"] == 2
    assert summary["deaths"] == 2
    assert summary["ghost_fraction"] == 0.45
    assert summary["stuck_episodes"] == 4
    assert summary["stuck_retry_window_seconds"] == 16.0
    assert summary["stuck_union_seconds"] == 16.0
    assert summary["damage_in"] == 200
    assert summary["damage_sources"][0]["damage"] == 200
    assert summary["spell_requests"] == {"783": 2}
    assert summary["recovery"]["release_spirit"] == 2
