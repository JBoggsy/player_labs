import json

import pytest

from dataset import SFTSample
from pipeline import balanced_by_version_and_trajectory, resolve_povs
from pipeline_manifest import EpisodeSpec, load_manifest


def sample(version: str, replay: str, tick: int) -> SFTSample:
    return SFTSample(replay, version, 0, tick, tick, "map", {}, 0, 0)


def test_manifest_rejects_replay_leakage_between_splits(tmp_path) -> None:
    manifest = {
        "schema_version": 1,
        "source_repository": "repo",
        "episodes": [
            {
                "episode_id": "same",
                "game_version": "16",
                "source_commit": "a",
                "split": "train",
            },
            {
                "episode_id": "same",
                "game_version": "40",
                "source_commit": "b",
                "split": "validation",
            },
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))

    with pytest.raises(ValueError, match="replay-disjoint"):
        load_manifest(path)


def test_balancing_round_robins_trajectories() -> None:
    values = [sample("16", "long", tick) for tick in range(10)] + [
        sample("16", "short", tick) for tick in range(2)
    ]

    selected = balanced_by_version_and_trajectory(values, cap=4, seed=1)

    assert sum(item.replay_id == "long" for item in selected) == 2
    assert sum(item.replay_id == "short" for item in selected) == 2


def test_balancing_uses_same_count_for_each_version() -> None:
    values = [sample("16", "old", tick) for tick in range(5)] + [
        sample("40", "new", tick) for tick in range(2)
    ]

    selected = balanced_by_version_and_trajectory(values, cap=None, seed=1)

    assert sum(item.game_version == "16" for item in selected) == 2
    assert sum(item.game_version == "40" for item in selected) == 2


def test_best_reward_pov_and_minimum_are_validated(tmp_path) -> None:
    metadata = {
        "policy_results": [
            {
                "policy": {"name": "strong", "version": 7},
                "agents": [{"agent_id": 3, "reward": 2}],
            },
            {
                "policy": {"name": "weak", "version": 1},
                "agents": [{"agent_id": 0, "reward": -1}],
            },
        ]
    }
    path = tmp_path / "episode.json"
    path.write_text(json.dumps(metadata))
    spec = EpisodeSpec("episode", "40", "commit", "train", "best_reward", 1)

    assert resolve_povs(spec, path) == [(3, 2.0, "strong:7")]
