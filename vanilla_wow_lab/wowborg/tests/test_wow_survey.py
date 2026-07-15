"""Unit tests for tools/wow_survey.py over a synthesized episode directory."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# wow_survey imports cwreplay by path itself; load survey via the same mechanism.
wow_survey = _load("wow_survey_test_mod", TOOLS_DIR / "wow_survey.py")

# Reuse the replay fixture builder from the decoder tests.
from test_cwreplay_tool import build_replay  # noqa: E402


def make_episode_dir(tmp_path: Path, *, with_replay: bool = True) -> Path:
    episode_dir = tmp_path / "20260715T0000_ereq_test"
    episode_dir.mkdir(parents=True)
    (episode_dir / "episode.json").write_text(
        json.dumps(
            {
                "episode_id": "ereq_test",
                "job_id": "job_1",
                "status": "completed",
                "variant_name": "Orc Fresh Start",
                "scores": [{"policy_version_id": "x", "score": 0.0}],
                "participants": [
                    {"position": 0, "policy_name": "wowborg", "version": 2}
                ],
            }
        ),
        encoding="utf-8",
    )
    if with_replay:
        fixture = build_replay(tmp_path)
        (episode_dir / "replay.json").write_bytes(fixture.read_bytes())
    return episode_dir


def test_survey_episode_metrics(tmp_path: Path) -> None:
    episode_dir = make_episode_dir(tmp_path)
    row = wow_survey.survey_episode(episode_dir)
    assert row is not None
    assert row["status"] == "completed"
    assert row["participants"] == [{"slot": 0, "policy": "wowborg:v2"}]
    member = row["members"][0]
    assert member["name"] == "Freshwar"
    assert member["login_verified"] is True
    assert member["movement_packets"] == 2
    assert member["travelled_yd"] == 5.0  # 3-4-5 triangle between the two positions
    assert member["says"] == ["wowborg leg 1: reached_target"]
    assert row["flags"] == []  # moved, logged in, completed → clean


def test_survey_flags_no_replay(tmp_path: Path) -> None:
    episode_dir = make_episode_dir(tmp_path, with_replay=False)
    row = wow_survey.survey_episode(episode_dir)
    assert "no replay downloaded" in row["flags"]


def test_render_html_is_self_contained(tmp_path: Path) -> None:
    episode_dir = make_episode_dir(tmp_path)
    row = wow_survey.survey_episode(episode_dir)
    html_text = wow_survey.render_html([row], "test survey", {})
    assert html_text.startswith("<!DOCTYPE html>")
    assert "Freshwar" in html_text
    assert "wowborg leg 1: reached_target" in html_text
    assert "Nothing flagged" in html_text


def test_main_writes_report_and_sidecar(tmp_path: Path) -> None:
    make_episode_dir(tmp_path)
    out = tmp_path / "report.html"
    assert wow_survey.main([str(tmp_path), "--out", str(out), "--title", "t"]) == 0
    assert out.exists()
    sidecar = json.loads(out.with_suffix(".survey.json").read_text(encoding="utf-8"))
    assert len(sidecar) == 1
