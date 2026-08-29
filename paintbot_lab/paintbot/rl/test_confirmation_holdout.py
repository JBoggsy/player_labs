import json

import numpy as np

from freeze_confirmation_holdout import (
    freeze_confirmation_indices,
    sample_identity,
)


def row(replay: str, pov: int, changed: bool, version: str = "40") -> dict:
    return {
        "sample_json": json.dumps(
            {
                "replay_id": replay,
                "game_version": version,
                "pov": pov,
                "observation_tick": int(changed),
            }
        ),
        "changed_action": changed,
        "game_version": version,
        "expert_player_id": "expert",
        "world": "ctf",
    }


class Rows:
    def __init__(self, values: list[dict]):
        self.values = values

    def __len__(self) -> int:
        return len(self.values)

    def select(self, indices: list[int]):
        return Rows([self.values[index] for index in indices])

    def select_columns(self, columns: list[str]):
        return Rows([{key: value[key] for key in columns} for value in self.values])

    def __getitem__(self, key: str):
        return [row[key] for row in self.values]

    def iter(self, batch_size: int):
        for start in range(0, len(self.values), batch_size):
            values = self.values[start : start + batch_size]
            yield {key: [row[key] for row in values] for key in values[0]}


def test_confirmation_is_balanced_and_replay_disjoint() -> None:
    values = [row("opened", 0, False), row("opened", 0, True)]
    for replay in ("a", "b", "c", "d", "e", "f", "g", "h"):
        values.extend((row(replay, 0, False), row(replay, 0, True)))

    indices, summary = freeze_confirmation_indices(
        Rows(values), np.asarray([0], dtype=np.int64), budget=6, seed="test"
    )
    selected = [sample_identity(values[index]["sample_json"]) for index in indices]

    assert len(selected) == len(set(selected)) == 6
    assert all(replay != "opened" for replay, _ in selected)
    assert summary["changed"] == summary["held"] == 3
    assert summary["selected_trajectories"] == 6


def test_confirmation_selection_is_deterministic() -> None:
    values = [row("opened", 0, False)]
    for index in range(12):
        values.extend((row(f"r{index}", 0, False), row(f"r{index}", 0, True)))
    dataset = Rows(values)

    first, _ = freeze_confirmation_indices(
        dataset, np.asarray([0], dtype=np.int64), budget=8, seed="fixed"
    )
    second, _ = freeze_confirmation_indices(
        dataset, np.asarray([0], dtype=np.int64), budget=8, seed="fixed"
    )

    np.testing.assert_array_equal(first, second)
