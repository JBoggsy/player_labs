"""The dashboard poller must stop once nothing it watches can change."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import xp_dashboard  # noqa: E402


class DoneClient:
    """Every request is terminal; each completed episode has valid results."""

    def __init__(self) -> None:
        self.list_calls = 0

    def get_json(self, path: str, **params: object) -> object:
        self.list_calls += 1
        return [
            {"id": "ereq_a", "status": "completed",
             "participants": [{"position": 0, "player_name": "p", "policy_name": "x", "version": 1}]},
            {"id": "ereq_b", "status": "failed", "participants": []},
        ]

    def get_text_or_none(self, path: str) -> str:
        return '{"win": [1], "scores": [5]}'


def test_poller_stops_when_all_requests_finished() -> None:
    client = DoneClient()
    poller = xp_dashboard.Poller(client, ["xreq_done"])
    poller.run_until_finished()  # returns instead of polling forever
    assert poller.finished_at is not None
    assert client.list_calls == 1
