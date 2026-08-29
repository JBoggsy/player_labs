import json

import numpy as np

from corpus_store import (
    balanced_indices,
    convert_corpus,
    load_arrow_dataset,
    write_balanced_indices,
)
from dataset import SFTSample, write_jsonl
from episode_map import EpisodeMap
from merge_prepared_shards import merge_shards
from pipeline import prepare_large_arrow_corpus
from pipeline_manifest import PipelineManifest, PreparationConfig, TrainingConfig
from training import EpochSampler, PolicyDataset


def test_arrow_conversion_preserves_samples_and_expert_metadata(tmp_path) -> None:
    manifest = {
        "episodes": [
            {
                "episode_id": "episode",
                "coworld_name": "paintbot",
                "expert_policies": [
                    {
                        "policy_name": "expert",
                        "version": 7,
                        "player_id": "player",
                    }
                ],
            }
        ]
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    shard = tmp_path / "shards/shard-000/prepared"
    shard.mkdir(parents=True)
    (shard / "provenance.json").write_text(
        json.dumps(
            {
                "trajectories": [
                    {"episode_id": "episode", "seat": 2, "policy": "expert:7"}
                ]
            }
        )
    )
    prepared = tmp_path / "prepared"
    sample = SFTSample("episode", "41", 2, 10, 10, "map", {}, 0, 1)
    write_jsonl(prepared / "train.samples.jsonl", [sample])
    write_jsonl(prepared / "train.maps.jsonl", [])

    assert convert_corpus(manifest_path, tmp_path) == {"train": 1}

    dataset = PolicyDataset(tmp_path / "arrow/train", prepared / "train.maps.jsonl")
    # Map validation is lazy for Arrow; this test only exercises the sample/metadata contract.
    assert dataset[0] == sample
    row = dataset.arrow[0]
    assert row["changed_action"] is True
    assert row["expert_player_id"] == "player"
    assert row["world"] == "paintbot"


def test_balanced_indices_split_transition_budget_across_strata() -> None:
    import datasets

    dataset = datasets.Dataset.from_dict(
        {
            "sample_json": ["{}"] * 80,
            "changed_action": [False] * 60 + [True] * 20,
            "game_version": ["16"] * 30 + ["40"] * 30 + ["16"] * 10 + ["40"] * 10,
            "expert_player_id": ["a"] * 15 + ["b"] * 15 + ["a"] * 15 + ["b"] * 15 + ["a"] * 10 + ["b"] * 10,
            "world": ["ctf"] * 40 + ["paintbot"] * 40,
        }
    )

    indices, summary = balanced_indices(dataset, budget=20, seed=1)

    assert len(np.unique(indices)) == 20
    assert summary["changed"] == 10
    assert summary["held"] == 10


def test_merge_converts_shards_incrementally_without_global_sample_copy(tmp_path) -> None:
    episode_map = EpisodeMap.from_mask(np.ones((2, 2), dtype=bool))
    for shard_number in range(2):
        shard_name = f"shard-{shard_number:03d}"
        episode_id = f"episode-{shard_number}"
        prepared = tmp_path / "shards" / shard_name / "prepared"
        prepared.mkdir(parents=True)
        sample = SFTSample(
            episode_id, "41", shard_number, 10, 10, episode_map.map_hash, {}, 0, shard_number
        )
        write_jsonl(prepared / "train.samples.jsonl", [sample])
        for split in ("validation", "test"):
            write_jsonl(prepared / f"{split}.samples.jsonl", [])
        for split in ("train", "validation", "test"):
            write_jsonl(prepared / f"{split}.maps.jsonl", [episode_map])
        (prepared / "provenance.json").write_text(
            json.dumps(
                {
                    "split_counts": {"train": 1, "validation": 0, "test": 0},
                    "trajectories": [
                        {
                            "episode_id": episode_id,
                            "seat": shard_number,
                            "policy": "expert:7",
                        }
                    ],
                    "failures": [],
                }
            )
        )
        manifests = tmp_path / "manifests"
        manifests.mkdir(exist_ok=True)
        (manifests / f"{shard_name}.json").write_text(
            json.dumps(
                {
                    "episodes": [
                        {
                            "episode_id": episode_id,
                            "coworld_name": "paintbot",
                            "expert_policies": [
                                {
                                    "policy_name": "expert",
                                    "version": 7,
                                    "player_id": f"player-{shard_number}",
                                }
                            ],
                        }
                    ]
                }
            )
        )

    first = merge_shards(tmp_path / "shards", tmp_path / "prepared")
    second = merge_shards(tmp_path / "shards", tmp_path / "prepared")
    dataset = load_arrow_dataset(tmp_path / "arrow/train")
    index_summary = write_balanced_indices(
        tmp_path / "arrow/train", tmp_path / "indices/train.npy", 2, 1
    )
    policy_dataset = PolicyDataset(
        tmp_path / "arrow/train",
        tmp_path / "prepared/train.maps.jsonl",
        tmp_path / "indices/train.npy",
    )

    assert first["split_counts"]["train"] == 2
    assert second["split_counts"]["train"] == 2
    assert len(dataset) == 2
    assert index_summary["selected"] == 2
    assert len(policy_dataset) == 2
    assert not list((tmp_path / "shards").glob("shard-*/prepared/*.samples.jsonl"))
    assert (tmp_path / "prepared/train.maps.jsonl").samefile(
        tmp_path / "prepared/maps.jsonl"
    )


def test_epoch_sampler_is_repeatable_and_changes_between_epochs() -> None:
    sampler = EpochSampler(list(range(20)), seed=5)
    first = list(sampler)
    sampler.set_epoch(1)
    second = list(sampler)
    sampler.set_epoch(0)

    assert list(sampler) == first
    assert second != first


def test_large_prepare_converts_bounded_parts_before_pruning_json(tmp_path) -> None:
    shard = tmp_path / "shards/shard-000"
    episode_map = EpisodeMap.from_mask(np.ones((2, 2), dtype=bool))
    empty_trajectory = shard / "trajectories/trajectory-empty"
    write_jsonl(empty_trajectory / "samples.jsonl", [])
    write_jsonl(empty_trajectory / "map.jsonl", [episode_map])
    records = [
        {
            "episode_id": "episode-empty",
            "game_version": "1",
            "source_commit": "commit",
            "split": "train",
            "seat": 0,
            "policy": "expert:7",
            "expert_player_id": "player",
            "world": "paintbot",
            "reward": 1,
            "observations": 1,
            "samples": 0,
            "raw_entities": 0,
            "retained_entities": 0,
            "wire_source": "wire",
            "map_hash": episode_map.map_hash,
            "trajectory": empty_trajectory.name,
        }
    ]
    for number in range(2):
        trajectory = shard / "trajectories" / f"trajectory-{number}"
        sample = SFTSample(
            f"episode-{number}", "41", number, 10, 10, episode_map.map_hash, {}, 0, number
        )
        write_jsonl(trajectory / "samples.jsonl", [sample])
        write_jsonl(trajectory / "map.jsonl", [episode_map])
        records.append(
            {
                "episode_id": sample.replay_id,
                "game_version": "41",
                "source_commit": "commit",
                "split": "train",
                "seat": number,
                "policy": "expert:7",
                "expert_player_id": "player",
                "world": "paintbot",
                "reward": 1,
                "observations": 1,
                "samples": 1,
                "raw_entities": 0,
                "retained_entities": 0,
                "wire_source": "wire",
                "map_hash": episode_map.map_hash,
                "trajectory": trajectory.name,
            }
        )
    manifest = PipelineManifest(
        source_repository="repo",
        episodes=(),
        preparation=PreparationConfig(
            balance_versions=False,
            prune_trajectory_artifacts_after_prepare=True,
        ),
        training=TrainingConfig(),
    )

    summary = prepare_large_arrow_corpus(
        manifest,
        shard,
        records,
        [],
        {episode_map.map_hash: episode_map},
        trajectories_per_part=1,
    )
    merged = merge_shards(tmp_path / "shards", tmp_path / "prepared")
    dataset = load_arrow_dataset(tmp_path / "arrow/train")

    assert summary["split_counts"]["train"] == 2
    assert merged["split_counts"]["train"] == 2
    assert len(dataset) == 2
    assert not list(shard.glob("trajectories/*/*.jsonl"))
