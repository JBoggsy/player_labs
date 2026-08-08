import json

import numpy as np

from corpus_store import balanced_indices, convert_corpus
from dataset import SFTSample, write_jsonl
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


def test_epoch_sampler_is_repeatable_and_changes_between_epochs() -> None:
    sampler = EpochSampler(list(range(20)), seed=5)
    first = list(sampler)
    sampler.set_epoch(1)
    second = list(sampler)
    sampler.set_epoch(0)

    assert list(sampler) == first
    assert second != first
