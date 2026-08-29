#!/usr/bin/env python3
"""Freeze a balanced confirmation index disjoint from a previously opened index."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from corpus_store import METADATA_COLUMNS, _balanced_quotas, load_arrow_dataset
from dataset import SFTSample


CONFIRMATION_SEED = "paintbot-exact-action-confirmation-v1-2026-08-14"
IDENTITY = re.compile(
    r'^\{"replay_id":\s*"([^"]+)",\s*"game_version":\s*"[^"]+",\s*"pov":\s*(\d+),'
)


@dataclass(frozen=True)
class Candidate:
    index: int
    replay_id: str
    pov: int
    changed: bool
    stratum: tuple[str, ...]

    @property
    def trajectory(self) -> tuple[str, int]:
        return self.replay_id, self.pov


def sample_identity(sample_json: str) -> tuple[str, int]:
    """Read the leading identity fields without parsing the large observation payload."""
    match = IDENTITY.match(sample_json)
    if match is None:
        raise ValueError("sample JSON does not use the canonical replay/version/POV prefix")
    return match.group(1), int(match.group(2))


def priority(seed: str, purpose: str, *values: object) -> bytes:
    payload = "\0".join((seed, purpose, *(str(value) for value in values)))
    return hashlib.sha256(payload.encode()).digest()


def confirmation_class_budgets(
    candidates: list[Candidate], budget: int
) -> dict[bool, int]:
    if budget <= 0:
        raise ValueError("sample budget must be positive")
    changed_capacity = len({item.trajectory for item in candidates if item.changed})
    held_capacity = len({item.trajectory for item in candidates if not item.changed})
    changed_budget = min((budget + 1) // 2, changed_capacity)
    held_budget = min(budget - changed_budget, held_capacity)
    if changed_budget + held_budget < budget:
        if changed_budget < (budget + 1) // 2:
            held_budget = min(budget - changed_budget, held_capacity)
        else:
            changed_budget = min(budget - held_budget, changed_capacity)
    if changed_budget + held_budget < budget:
        raise ValueError(
            f"only {changed_budget + held_budget} eligible trajectories for budget {budget}"
        )
    return {True: changed_budget, False: held_budget}


def freeze_confirmation_indices(
    dataset,
    contaminated_indices: np.ndarray,
    *,
    budget: int,
    seed: str = CONFIRMATION_SEED,
) -> tuple[np.ndarray, dict]:
    contaminated_rows = dataset.select([int(index) for index in contaminated_indices])[
        "sample_json"
    ]
    contaminated_replays = {sample_identity(row)[0] for row in contaminated_rows}

    # Keep one deterministic changed and held row candidate per episode-seat trajectory.
    per_trajectory_class: dict[tuple[str, int, bool], tuple[bytes, Candidate]] = {}
    offset = 0
    columns = ("sample_json", *METADATA_COLUMNS)
    for batch in dataset.select_columns(list(columns)).iter(batch_size=100_000):
        for local_index, sample_json in enumerate(batch["sample_json"]):
            replay_id, pov = sample_identity(sample_json)
            if replay_id in contaminated_replays:
                continue
            changed = bool(batch["changed_action"][local_index])
            stratum = (
                str(changed),
                str(batch["game_version"][local_index]),
                str(batch["expert_player_id"][local_index]),
                str(batch["world"][local_index]),
            )
            index = offset + local_index
            candidate = Candidate(index, replay_id, pov, changed, stratum)
            key = replay_id, pov, changed
            rank = priority(seed, "row", replay_id, pov, changed, index)
            incumbent = per_trajectory_class.get(key)
            if incumbent is None or rank < incumbent[0]:
                per_trajectory_class[key] = rank, candidate
        offset += len(batch["sample_json"])

    candidates = [candidate for _, candidate in per_trajectory_class.values()]
    class_budgets = confirmation_class_budgets(candidates, budget)
    class_capacities = Counter(candidate.changed for candidate in candidates)
    class_order = sorted(
        (False, True), key=lambda changed: (class_capacities[changed], changed)
    )
    selected: list[Candidate] = []
    used_trajectories: set[tuple[str, int]] = set()
    for changed in class_order:
        eligible = [
            candidate
            for candidate in candidates
            if candidate.changed == changed
            and candidate.trajectory not in used_trajectories
        ]
        capacities = Counter(candidate.stratum for candidate in eligible)
        quotas = _balanced_quotas(capacities, class_budgets[changed])
        if sum(quotas.values()) != class_budgets[changed]:
            raise ValueError(
                f"only {sum(quotas.values())} disjoint {changed=} trajectories for "
                f"budget {class_budgets[changed]}"
            )
        by_stratum: dict[tuple[str, ...], list[Candidate]] = defaultdict(list)
        for candidate in eligible:
            by_stratum[candidate.stratum].append(candidate)
        for stratum, quota in sorted(quotas.items()):
            ranked = sorted(
                by_stratum[stratum],
                key=lambda item: priority(seed, "trajectory", *item.trajectory),
            )
            chosen = ranked[:quota]
            selected.extend(chosen)
            used_trajectories.update(candidate.trajectory for candidate in chosen)
    selected.sort(key=lambda item: priority(seed, "shuffle", item.index))

    indices = np.asarray([candidate.index for candidate in selected], dtype=np.int64)
    trajectories = {candidate.trajectory for candidate in selected}
    selected_replays = {candidate.replay_id for candidate in selected}
    if len(indices) != budget or len(trajectories) != budget:
        raise RuntimeError("confirmation selection must contain one row per trajectory")
    if selected_replays & contaminated_replays:
        raise RuntimeError("confirmation selection overlaps a contaminated replay")
    summary = {
        "schema_version": 1,
        "seed": seed,
        "requested_budget": budget,
        "selected": len(indices),
        "selected_trajectories": len(trajectories),
        "selected_replays": len(selected_replays),
        "contaminated_rows": len(contaminated_indices),
        "contaminated_replays": len(contaminated_replays),
        "eligible_trajectories": len(
            {candidate.trajectory for candidate in candidates}
        ),
        "changed": sum(candidate.changed for candidate in selected),
        "held": sum(not candidate.changed for candidate in selected),
        "strata": len({candidate.stratum for candidate in selected}),
        "available": len(dataset),
    }
    return indices, summary


def selected_samples_sha256(dataset, indices: np.ndarray) -> str:
    digest = hashlib.sha256()
    for row in dataset.select([int(index) for index in indices])["sample_json"]:
        sample = SFTSample.from_dict(json.loads(row))
        payload = json.dumps(
            asdict(sample), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        digest.update(len(payload).to_bytes(8, "little"))
        digest.update(payload)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--contaminated-index", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=10_000)
    args = parser.parse_args()
    summary_path = args.out.with_suffix(".json")
    if args.out.exists() or summary_path.exists():
        parser.error(f"refusing to overwrite a frozen confirmation index: {args.out}")

    dataset = load_arrow_dataset(args.dataset)
    contaminated_indices = np.load(args.contaminated_index)
    indices, summary = freeze_confirmation_indices(
        dataset, contaminated_indices, budget=args.budget
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.out, indices)
    summary.update(
        {
            "dataset_fingerprint": str(dataset._fingerprint),
            "contaminated_index": str(args.contaminated_index),
            "contaminated_index_sha256": sha256_file(args.contaminated_index),
            "index_sha256": sha256_file(args.out),
            "selected_samples_sha256": selected_samples_sha256(dataset, indices),
        }
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
