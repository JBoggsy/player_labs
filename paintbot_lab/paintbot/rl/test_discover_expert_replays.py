import json

from discover_expert_replays import discover_query


class EmptyClient:
    def __init__(self) -> None:
        self.payloads = []

    def request_json(self, method, path, **kwargs):
        self.payloads.append(kwargs["json"])
        return {"entries": [], "total_count": 0}


def test_legacy_cursor_resumes_in_bounded_time_window(tmp_path) -> None:
    queries = tmp_path / "queries"
    queries.mkdir()
    state = queries / "expert-ctf.state.json"
    state.write_text(
        json.dumps(
            {
                "complete": False,
                "rows": 12,
                "before_created_at": "2026-07-10T00:00:00Z",
            }
        )
    )
    client = EmptyClient()

    written = discover_query(
        client,
        tmp_path,
        {"label": "Expert", "player_id": "player"},
        "ctf",
        None,
        "2026-07-09T00:00:00Z",
        24,
    )

    assert written == 12
    clauses = client.payloads[0]["where"]["clauses"]
    assert {"op": "gte", "field": "created_at", "value": "2026-07-09T00:00:00Z"} in clauses
    assert {"op": "lt", "field": "created_at", "value": "2026-07-10T00:00:00Z"} in clauses
    assert json.loads(state.read_text())["complete"] is True
