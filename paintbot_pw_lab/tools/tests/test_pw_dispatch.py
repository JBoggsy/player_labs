"""pw.py: the dispatcher's catalog is complete and consistent, docs/tools/README.md is generated
from it and in sync, every Python tool honours --json/--help, and selectors are checked."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

TOOLS = Path(__file__).resolve().parents[1]
LAB = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import pw  # noqa: E402
import pw_cli  # noqa: E402
import pw_viz as pv  # noqa: E402

README = LAB / "docs" / "tools" / "README.md"
REGENERATE = "uv run python paintbot_pw_lab/tools/pw.py tools --markdown > paintbot_pw_lab/docs/tools/README.md"
PY_TOOLS = [e for e in pw.CATALOG if e["target"][0] == "py"]


def test_readme_is_generated_from_the_catalog():
    assert README.read_text() == pw.markdown(), f"docs/tools/README.md is stale: run {REGENERATE}"


def test_catalog_targets_docs_and_skills_exist():
    for entry in pw.CATALOG:
        kind, what = entry["target"]
        if kind in ("py", "sh"):
            assert (TOOLS / what).is_file(), entry["name"]
        assert (LAB / "docs" / "tools" / entry["doc"].split("#")[0]).is_file(), entry["name"]
        if entry["skill"]:
            assert (LAB / ".claude" / "skills" / entry["skill"] / "SKILL.md").is_file(), entry["name"]
        for key in ("purpose", "when_to_use", "inputs", "outputs", "exit_codes"):
            assert entry[key], (entry["name"], key)
    assert len(pw.BY_NAME) == len(pw.CATALOG)


def test_every_python_tool_is_in_the_catalog():
    listed = {e["target"][1] for e in PY_TOOLS}
    libraries = {"pw.py", "pw_cli.py", "pw_public.py", "features.py"}   # not CLIs of their own
    assert {p.name for p in TOOLS.glob("*.py")} - libraries - listed == set()


def test_tools_json_catalog_shape(capsys):
    assert pw.main(["tools", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] and {t["name"] for t in data["result"]["tools"]} == set(pw.BY_NAME)
    row = next(t for t in data["result"]["tools"] if t["name"] == "metrics")
    assert set(row) >= {"name", "command", "purpose", "when_to_use", "inputs", "outputs", "exit_codes", "doc", "skill"}
    assert row["command"] == "uv run python paintbot_pw_lab/tools/pw.py metrics"


def test_unknown_subcommand_is_a_usage_error_with_the_valid_list(capsys):
    assert pw.main(["nosuch", "--json"]) == 2
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False and "metrics" in data["result"]["valid"]


@pytest.mark.parametrize("entry", PY_TOOLS, ids=[e["name"] for e in PY_TOOLS])
def test_every_python_tool_documents_json_and_examples_in_help(entry):
    done = subprocess.run([sys.executable, str(TOOLS / entry["target"][1]), "--help"],
                          capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    assert "--json" in done.stdout or "subcommand" in done.stdout.lower() or "{" in done.stdout
    assert "example" in done.stdout.lower(), f"{entry['name']} --help has no examples"


class FakeEpisode:
    def __init__(self, episode_id, ticks, policies=("alpha", "beta")):
        self.episode_id = episode_id
        self.tables = {
            "episodes": pd.DataFrame({"ticks": [ticks]}),
            "seats": pd.DataFrame({"seat": range(4), "team": [0, 1, 0, 1],
                                   "policy_key": [f"pv-{policies[s % 2]}" for s in range(4)],
                                   "policy_name": [policies[s % 2] for s in range(4)]}),
        }

    def __getitem__(self, name):
        return self.tables[name]


def test_viz_window_past_every_match_end_is_a_usage_error_listing_lengths():
    episodes = [FakeEpisode("e1", 1649)]
    with pytest.raises(pw_cli.UsageError) as error:
        pv.check_window(episodes, pv.parse_time("1:10"), pv.parse_time("1:40"))
    assert error.value.valid == ["e1: ticks 0-1649 (0:00-1:08.7)"]
    with pytest.raises(pw_cli.UsageError, match="must be after"):
        pv.check_window(episodes, 900, 800)


def test_viz_window_is_clamped_and_reported_per_episode():
    window = pv.check_window([FakeEpisode("short", 1000), FakeEpisode("long", 3000)], 1200, 5000)
    assert window["starts_after_end"] == ["short"] and window["clamped_to_end"] == ["long"]
    assert window["match_end_ticks"] == {"short": 1000, "long": 3000}


def test_viz_unknown_seat_or_policy_is_a_usage_error():
    episodes = [FakeEpisode("e1", 1000)]
    pv.check_seats(episodes, [1, 2], None, ["alpha"])
    with pytest.raises(pw_cli.UsageError) as error:
        pv.check_seats(episodes, [9], None, None)
    assert error.value.valid == ["0", "1", "2", "3"]
    with pytest.raises(pw_cli.UsageError, match="not in these episodes"):
        pv.check_seats(episodes, None, None, ["gamma"])
    with pytest.raises(pw_cli.UsageError, match="no seat matches"):
        pv.check_seats(episodes, [1], 0, None)            # seat 1 is on team 1


def test_the_skill_viz_examples_use_a_window_inside_the_sample_match():
    """The replay skill's movement example must not start past the 1:08.7 sample match."""
    skill = (LAB / ".claude" / "skills" / "paintbot-pw-replay" / "SKILL.md").read_text()
    starts = [pv.parse_time(t) for t in re.findall(r"movement \S+ --from (\S+)", skill)]
    assert starts and all(t < 1649 for t in starts)
