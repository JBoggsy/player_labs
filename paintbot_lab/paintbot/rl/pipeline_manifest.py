"""Validated manifest contract for replay-to-checkpoint training runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


Split = Literal["train", "validation", "test"]


@dataclass(frozen=True)
class EpisodeSpec:
    episode_id: str
    game_version: str
    source_commit: str
    split: Split
    povs: tuple[int, ...] | Literal["best_reward", "expert_policies"]
    minimum_reward: float | None = None
    expert_policy_version_ids: tuple[str, ...] = ()
    max_povs_per_policy: int | None = None


@dataclass(frozen=True)
class PreparationConfig:
    stride: int = 24
    action_delay_ticks: int = 0
    max_samples_per_version: int | None = None
    balance_versions: bool = True
    history_ticks: int = 0
    continue_on_error: bool = False
    retain_intermediates: bool = True
    prune_trajectory_artifacts_after_prepare: bool = False
    seed: int = 1


@dataclass(frozen=True)
class TrainingConfig:
    tuning: str = "lora"
    epochs: int = 3
    batch_size: int = 2
    gradient_accumulation: int = 8
    learning_rate: float | None = None
    weight_decay: float = 0.01
    warmup_ratio: float = 0.03
    max_text_tokens: int = 4096
    max_history_tokens: int = 832
    mixed_precision: str = "bf16"
    seed: int = 1
    action_change_weight: float | str = 1.0


@dataclass(frozen=True)
class PipelineManifest:
    source_repository: str
    episodes: tuple[EpisodeSpec, ...]
    preparation: PreparationConfig
    training: TrainingConfig
    schema_version: int = 1


def load_manifest(path: Path) -> PipelineManifest:
    value = json.loads(path.read_text())
    if value.get("schema_version") != 1:
        raise ValueError("manifest schema_version must be 1")
    episodes = tuple(_episode(item) for item in value.get("episodes", ()))
    if not episodes:
        raise ValueError("manifest must contain at least one episode")
    ids = [episode.episode_id for episode in episodes]
    if len(ids) != len(set(ids)):
        raise ValueError("an episode may appear only once; data splits must be replay-disjoint")
    versions = {episode.game_version for episode in episodes}
    if len(versions) < 2:
        raise ValueError("cross-era training requires at least two GameVersions")
    training_versions = {
        episode.game_version for episode in episodes if episode.split == "train"
    }
    if len(training_versions) < 2:
        raise ValueError("the training split must contain at least two GameVersions")

    preparation = PreparationConfig(**value.get("preparation", {}))
    if preparation.stride <= 0:
        raise ValueError("preparation.stride must be positive")
    if preparation.action_delay_ticks < 0:
        raise ValueError("preparation.action_delay_ticks must be non-negative")
    if (
        preparation.max_samples_per_version is not None
        and preparation.max_samples_per_version <= 0
    ):
        raise ValueError("preparation.max_samples_per_version must be positive")
    if preparation.history_ticks not in {0, 4}:
        raise ValueError("preparation.history_ticks must currently be 0 or 4")
    if not preparation.balance_versions and preparation.max_samples_per_version is not None:
        raise ValueError("max_samples_per_version requires balance_versions")

    training = TrainingConfig(**value.get("training", {}))
    if training.tuning not in {"lora", "full"}:
        raise ValueError("training.tuning must be lora or full")
    if training.mixed_precision not in {"no", "fp16", "bf16"}:
        raise ValueError("training.mixed_precision must be no, fp16, or bf16")
    if not 0 <= training.warmup_ratio < 1:
        raise ValueError("training.warmup_ratio must be in [0, 1)")
    if training.action_change_weight != "balanced":
        try:
            action_change_weight = float(training.action_change_weight)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "training.action_change_weight must be positive or 'balanced'"
            ) from error
        if action_change_weight <= 0:
            raise ValueError(
                "training.action_change_weight must be positive or 'balanced'"
            )

    return PipelineManifest(
        schema_version=1,
        source_repository=str(value["source_repository"]),
        episodes=episodes,
        preparation=preparation,
        training=training,
    )


def _episode(value: dict[str, Any]) -> EpisodeSpec:
    split = str(value["split"])
    if split not in {"train", "validation", "test"}:
        raise ValueError(f"invalid split {split!r}")
    raw_povs = value.get("povs", "best_reward")
    if raw_povs in {"best_reward", "expert_policies"}:
        povs: tuple[int, ...] | Literal["best_reward", "expert_policies"] = raw_povs
    elif isinstance(raw_povs, list) and raw_povs:
        povs = tuple(int(item) for item in raw_povs)
        if len(povs) != len(set(povs)) or any(item < 0 for item in povs):
            raise ValueError("episode povs must be unique non-negative seat indices")
    else:
        raise ValueError(
            "episode povs must be 'best_reward', 'expert_policies', or a non-empty list"
        )
    expert_policy_version_ids = tuple(
        str(item) for item in value.get("expert_policy_version_ids", ())
    )
    if raw_povs == "expert_policies" and not expert_policy_version_ids:
        raise ValueError("expert_policies POV selection requires policy version ids")
    max_povs_per_policy = value.get("max_povs_per_policy")
    if max_povs_per_policy is not None and int(max_povs_per_policy) <= 0:
        raise ValueError("max_povs_per_policy must be positive")
    return EpisodeSpec(
        episode_id=str(value["episode_id"]),
        game_version=str(value["game_version"]),
        source_commit=str(value["source_commit"]),
        split=split,  # type: ignore[arg-type]
        povs=povs,
        minimum_reward=(
            float(value["minimum_reward"])
            if value.get("minimum_reward") is not None
            else None
        ),
        expert_policy_version_ids=expert_policy_version_ids,
        max_povs_per_policy=(
            int(max_povs_per_policy) if max_povs_per_policy is not None else None
        ),
    )
