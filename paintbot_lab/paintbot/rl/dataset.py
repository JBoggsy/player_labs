"""On-disk contract and causal alignment for cross-era SFT examples."""

from __future__ import annotations

import bisect
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from actions import action_text
from episode_map import EpisodeMap
from observation_text import (
    ObservationSnapshot,
    bot_semantic_observation,
    self_center,
    serialize_observation,
    serialize_temporal_history,
)


@dataclass(frozen=True)
class ActionChange:
    tick: int
    mask: int


@dataclass(frozen=True)
class SFTSample:
    replay_id: str
    game_version: str
    pov: int
    observation_tick: int
    action_tick: int
    map_hash: str
    observation: dict
    previous_mask: int
    target_mask: int
    history: tuple[dict, ...] = ()

    @classmethod
    def from_dict(cls, value: dict) -> SFTSample:
        return cls(
            replay_id=str(value["replay_id"]),
            game_version=str(value["game_version"]),
            pov=int(value["pov"]),
            observation_tick=int(value["observation_tick"]),
            action_tick=int(value["action_tick"]),
            map_hash=str(value["map_hash"]),
            observation=dict(value["observation"]),
            previous_mask=int(value["previous_mask"]),
            target_mask=int(value["target_mask"]),
            history=tuple(value.get("history", ())),
        )

    def prompt(self) -> str:
        snapshot = ObservationSnapshot.from_dict(self.observation)
        current = (
            serialize_observation(snapshot)
            + "\nprevious_action "
            + action_text(self.previous_mask)
            + "\naction"
        )
        if not self.history:
            return current
        return serialize_temporal_history(self.history) + "\n" + current

    def prompt_parts(self) -> tuple[str, str, str]:
        """Return history, current observation, and must-retain action suffix."""
        snapshot = ObservationSnapshot.from_dict(self.observation)
        history = serialize_temporal_history(self.history) if self.history else ""
        suffix = "previous_action " + action_text(self.previous_mask) + "\naction"
        return history, serialize_observation(snapshot), suffix

    def target(self) -> str:
        return action_text(self.target_mask)

    def position(self) -> tuple[float, float]:
        return self_center(ObservationSnapshot.from_dict(self.observation))


class ActionTimeline:
    """Piecewise-constant held input reconstructed from replay change records."""

    def __init__(self, changes: Iterable[ActionChange]) -> None:
        ordered = sorted(changes, key=lambda item: item.tick)
        self.ticks = [item.tick for item in ordered]
        self.masks = [item.mask for item in ordered]
        if any(not 0 <= mask <= 0xFF for mask in self.masks):
            raise ValueError("action masks must fit in one byte")

    def mask_at(self, tick: int) -> int:
        index = bisect.bisect_right(self.ticks, tick) - 1
        return 0 if index < 0 else self.masks[index]


def build_samples(
    snapshots: Iterable[ObservationSnapshot],
    timeline: ActionTimeline,
    *,
    replay_id: str,
    pov: int,
    map_hash: str,
    action_delay_ticks: int = 0,
    filter_bot_semantics: bool = True,
) -> list[SFTSample]:
    """Align each observation to the held input consumed from that state."""
    if action_delay_ticks < 0:
        raise ValueError("action delay must be non-negative")
    samples = []
    for snapshot in snapshots:
        if snapshot.tick is None:
            raise ValueError("snapshot is missing replay tick metadata")
        try:
            self_center(snapshot)
        except ValueError:
            # Replay initialization can render map/global markers before this POV joins.
            continue
        action_tick = snapshot.tick + action_delay_ticks
        policy_snapshot = (
            bot_semantic_observation(snapshot) if filter_bot_semantics else snapshot
        )
        samples.append(
            SFTSample(
                replay_id=replay_id,
                game_version=snapshot.game_version,
                pov=pov,
                observation_tick=snapshot.tick,
                action_tick=action_tick,
                map_hash=map_hash,
                # Persist the policy view, not renderer-only sprites. This keeps
                # prepared corpora compact and makes the on-disk contract match
                # what prompt serialization actually consumes.
                observation=policy_snapshot.to_dict(),
                previous_mask=timeline.mask_at(action_tick - 1),
                target_mask=timeline.mask_at(action_tick),
            )
        )
    return samples


def read_actions(path: Path) -> list[ActionChange]:
    return [ActionChange(tick=int(row["tick"]), mask=int(row["mask"])) for row in _jsonl(path)]


def read_samples(path: Path) -> list[SFTSample]:
    return [SFTSample.from_dict(row) for row in _jsonl(path)]


def read_maps(path: Path) -> dict[str, EpisodeMap]:
    maps = [EpisodeMap.from_dict(row) for row in _jsonl(path)]
    return {item.map_hash: item for item in maps}


def write_jsonl(path: Path, values: Iterable[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as output:
        for value in values:
            if hasattr(value, "to_dict"):
                value = value.to_dict()
            elif hasattr(value, "__dataclass_fields__"):
                value = asdict(value)
            output.write(json.dumps(value) + "\n")


def _jsonl(path: Path) -> Iterable[dict]:
    with path.open() as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            yield value
