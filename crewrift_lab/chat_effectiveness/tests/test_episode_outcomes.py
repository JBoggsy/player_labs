import json
import sys
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from episode_outcomes import build_outcomes_table, parse_episode_outcome  # noqa: E402

EPISODE_JSON = {
    "id": "ep_opaque_internal_id",
    "episode_id": "also_opaque",
    "participants": [
        {"position": 0, "policy_name": "crewborg", "version": 89, "player_name": "James"},
        {"position": 1, "policy_name": "notsus", "version": 168, "player_name": "Andre"},
    ],
}

RESULTS_JSON = {
    "names": ["James", "Andre"],
    "scores": [108, 20],
    "win": [True, False],
    "tasks": [8, 0],
    "kills": [0, 2],
    "imposter": [0, 1],
    "crew": [1, 0],
}


LEAGUE_EPISODE_JSON = {
    "id": "ep_opaque",
    "policy_results": [
        {"position": 0, "policy": {"name": "crewborg", "version": 89}},
        {"position": 1, "policy": {"name": "notsus", "version": 168}},
    ],
}


def _write_episode_dir(root: Path, name: str, episode_json: dict = EPISODE_JSON) -> Path:
    d = root / name
    d.mkdir()
    (d / "episode.json").write_text(json.dumps(episode_json))
    (d / "results.json").write_text(json.dumps(RESULTS_JSON))
    return d


def test_parse_episode_outcome_uses_dir_name_as_episode_key(tmp_path):
    d = _write_episode_dir(tmp_path, "20260702T000000_ereq_abc123-01")

    rows = parse_episode_outcome(d)

    assert len(rows) == 2
    assert rows[0]["episode"] == "20260702T000000_ereq_abc123-01"
    assert rows[0]["slot"] == 0
    assert rows[0]["policy_name"] == "crewborg"
    assert rows[0]["policy_version"] == 89
    assert rows[0]["role"] == "crew"
    assert rows[0]["win"] is True
    assert rows[0]["score"] == 108
    assert rows[1]["role"] == "imposter"
    assert rows[1]["win"] is False


def test_parse_episode_outcome_falls_back_to_policy_results_for_league_shape(tmp_path):
    d = _write_episode_dir(tmp_path, "league_ep", episode_json=LEAGUE_EPISODE_JSON)

    rows = parse_episode_outcome(d)

    assert len(rows) == 2
    assert rows[0]["policy_name"] == "crewborg"
    assert rows[0]["policy_version"] == 89
    assert rows[1]["policy_name"] == "notsus"
    assert rows[1]["policy_version"] == 168


def test_build_outcomes_table_across_multiple_episode_dirs(tmp_path):
    _write_episode_dir(tmp_path, "ep_one")
    _write_episode_dir(tmp_path, "ep_two")
    (tmp_path / "not_an_episode").mkdir()  # no episode.json/results.json — must be skipped

    df = build_outcomes_table(tmp_path)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 4
    assert set(df["episode"]) == {"ep_one", "ep_two"}
    assert list(df.columns) == [
        "episode", "slot", "policy_name", "policy_version", "role", "win", "score",
    ]
