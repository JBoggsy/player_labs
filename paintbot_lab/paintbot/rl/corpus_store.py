#!/usr/bin/env python3
"""Convert merged JSONL samples into a disk-backed, balanced Arrow corpus."""

from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


SPLITS = ("train", "validation", "test")
METADATA_COLUMNS = ("changed_action", "game_version", "expert_player_id", "world")


def _datasets():
    try:
        import datasets
    except ImportError as error:
        raise RuntimeError("install the rl dependency group to use Arrow corpora") from error
    return datasets


def trajectory_metadata(manifest_path: Path, shards_root: Path) -> dict[tuple[str, int], dict]:
    manifest = json.loads(manifest_path.read_text())
    episodes = {item["episode_id"]: item for item in manifest["episodes"]}
    result: dict[tuple[str, int], dict] = {}
    for provenance_path in sorted(shards_root.glob("shard-*/prepared/provenance.json")):
        result.update(trajectory_metadata_from_provenance(episodes, provenance_path))
    return result


def trajectory_metadata_from_provenance(
    episodes: dict[str, dict], provenance_path: Path
) -> dict[tuple[str, int], dict]:
    result = {}
    provenance = json.loads(provenance_path.read_text())
    for trajectory in provenance.get("trajectories", ()):
        episode_id = trajectory["episode_id"]
        episode = episodes[episode_id]
        player_ids = {
            f'{policy["policy_name"]}:{policy["version"]}': policy["player_id"]
            for policy in episode.get("expert_policies", ())
        }
        policy = trajectory["policy"]
        try:
            player_id = player_ids[policy]
        except KeyError as error:
            raise ValueError(
                f"trajectory {episode_id} seat {trajectory['seat']} has unmapped policy {policy}"
            ) from error
        result[(episode_id, int(trajectory["seat"]))] = {
            "expert_player_id": player_id,
            "world": episode["coworld_name"],
        }
    return result


def sample_rows(samples_path: Path, metadata: dict[tuple[str, int], dict]):
    with samples_path.open() as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            sample = json.loads(line)
            key = (str(sample["replay_id"]), int(sample["pov"]))
            try:
                trajectory = metadata[key]
            except KeyError as error:
                raise ValueError(
                    f"{samples_path}:{line_number} has no trajectory metadata for {key}"
                ) from error
            yield {
                "sample_json": line.rstrip("\n"),
                "changed_action": int(sample["previous_mask"]) != int(sample["target_mask"]),
                "game_version": str(sample["game_version"]),
                **trajectory,
            }


def convert_split(samples_path: Path, output: Path, metadata: dict[tuple[str, int], dict]) -> int:
    datasets = _datasets()
    if (output / "dataset_info.json").exists():
        return len(datasets.load_from_disk(str(output)))
    features = datasets.Features(
        {
            "sample_json": datasets.Value("string"),
            "changed_action": datasets.Value("bool"),
            "game_version": datasets.Value("string"),
            "expert_player_id": datasets.Value("string"),
            "world": datasets.Value("string"),
        }
    )
    cache = output.parent / f".{output.name}-build-cache"
    dataset = datasets.Dataset.from_generator(
        sample_rows,
        gen_kwargs={"samples_path": samples_path, "metadata": metadata},
        features=features,
        cache_dir=str(cache),
        keep_in_memory=False,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}-incomplete")
    if temporary.exists():
        shutil.rmtree(temporary)
    dataset.save_to_disk(str(temporary), max_shard_size="2GB")
    temporary.rename(output)
    if cache.exists():
        shutil.rmtree(cache)
    return len(dataset)


def convert_corpus(manifest: Path, workspace: Path) -> dict[str, int]:
    prepared = workspace / "prepared"
    arrow_provenance = workspace / "arrow" / "provenance.json"
    if arrow_provenance.exists():
        return {
            split: int(count)
            for split, count in json.loads(arrow_provenance.read_text())["split_counts"].items()
        }
    metadata = trajectory_metadata(manifest, workspace / "shards")
    counts = {}
    for split in SPLITS:
        samples = prepared / f"{split}.samples.jsonl"
        if samples.exists():
            counts[split] = convert_split(samples, workspace / "arrow" / split, metadata)
    (workspace / "arrow" / "provenance.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_manifest": str(manifest),
                "source_prepared": str(prepared),
                "split_counts": counts,
                "metadata_columns": list(METADATA_COLUMNS),
            },
            indent=2,
        )
        + "\n"
    )
    return counts


def load_arrow_dataset(path: Path):
    datasets = _datasets()
    if (path / "dataset_info.json").exists():
        return datasets.load_from_disk(str(path))
    manifest_path = path / "shards.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"no Arrow dataset or shard manifest at {path}")
    manifest = json.loads(manifest_path.read_text())
    shards = [load_arrow_dataset((path / shard).resolve()) for shard in manifest["shards"]]
    if not shards:
        raise ValueError(f"Arrow shard manifest is empty: {manifest_path}")
    return datasets.concatenate_datasets(shards)


def _balanced_quotas(capacities: dict[tuple[str, ...], int], budget: int) -> dict[tuple[str, ...], int]:
    if budget <= 0:
        raise ValueError("sample budget must be positive")
    remaining = min(budget, sum(capacities.values()))
    quotas = {key: 0 for key in capacities}
    active = set(capacities)
    while remaining and active:
        share = max(1, remaining // len(active))
        progressed = 0
        for key in sorted(active):
            addition = min(share, capacities[key] - quotas[key], remaining)
            quotas[key] += addition
            remaining -= addition
            progressed += addition
            if remaining == 0:
                break
        active = {key for key in active if quotas[key] < capacities[key]}
        if not progressed:
            break
    return {key: value for key, value in quotas.items() if value}


def _stratum(batch: dict, index: int) -> tuple[str, ...]:
    return (
        str(batch["changed_action"][index]),
        str(batch["game_version"][index]),
        str(batch["expert_player_id"][index]),
        str(batch["world"][index]),
    )


def metadata_batches(dataset, batch_size: int = 100_000):
    yield from dataset.select_columns(list(METADATA_COLUMNS)).iter(batch_size=batch_size)


def balanced_indices(dataset, budget: int, seed: int) -> tuple[np.ndarray, dict]:
    capacities: Counter[tuple[str, ...]] = Counter()
    for batch in metadata_batches(dataset):
        for index in range(len(batch["changed_action"])):
            capacities[_stratum(batch, index)] += 1

    changed_budget = min((budget + 1) // 2, sum(v for k, v in capacities.items() if k[0] == "True"))
    held_budget = min(budget - changed_budget, sum(v for k, v in capacities.items() if k[0] == "False"))
    if changed_budget + held_budget < budget:
        if changed_budget < (budget + 1) // 2:
            held_budget = min(budget - changed_budget, sum(v for k, v in capacities.items() if k[0] == "False"))
        else:
            changed_budget = min(budget - held_budget, sum(v for k, v in capacities.items() if k[0] == "True"))
    quotas = {}
    for changed, class_budget in (("True", changed_budget), ("False", held_budget)):
        class_capacities = {key: value for key, value in capacities.items() if key[0] == changed}
        quotas.update(_balanced_quotas(class_capacities, class_budget))

    rng = random.Random(seed)
    seen: Counter[tuple[str, ...]] = Counter()
    reservoirs: dict[tuple[str, ...], list[int]] = defaultdict(list)
    offset = 0
    for batch in metadata_batches(dataset):
        for index in range(len(batch["changed_action"])):
            key = _stratum(batch, index)
            quota = quotas.get(key, 0)
            if quota:
                seen[key] += 1
                values = reservoirs[key]
                if len(values) < quota:
                    values.append(offset + index)
                else:
                    replacement = rng.randrange(seen[key])
                    if replacement < quota:
                        values[replacement] = offset + index
        offset += len(batch["changed_action"])

    indices = np.fromiter(
        (index for key in sorted(reservoirs) for index in reservoirs[key]), dtype=np.int64
    )
    rng.shuffle(indices)
    summary = {
        "requested_budget": budget,
        "selected": int(len(indices)),
        "seed": seed,
        "changed": int(sum(quotas.get(key, 0) for key in quotas if key[0] == "True")),
        "held": int(sum(quotas.get(key, 0) for key in quotas if key[0] == "False")),
        "strata": len(quotas),
        "available": len(dataset),
    }
    return indices, summary


def write_balanced_indices(dataset_path: Path, output: Path, budget: int, seed: int) -> dict:
    dataset = load_arrow_dataset(dataset_path)
    indices, summary = balanced_indices(dataset, budget, seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.save(output, indices)
    output.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    convert = subparsers.add_parser("convert")
    convert.add_argument("--manifest", type=Path, required=True)
    convert.add_argument("--workspace", type=Path, required=True)
    index = subparsers.add_parser("index")
    index.add_argument("--dataset", type=Path, required=True)
    index.add_argument("--output", type=Path, required=True)
    index.add_argument("--budget", type=int, required=True)
    index.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    if args.command == "convert":
        print(json.dumps(convert_corpus(args.manifest, args.workspace), indent=2))
    else:
        print(json.dumps(write_balanced_indices(args.dataset, args.output, args.budget, args.seed), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
