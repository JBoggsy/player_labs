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
    libraries = {"pw.py", "pw_cli.py", "pw_public.py", "features.py", "strategy_build.py", "strategy_format.py", "strategy_basic.py", "strategy_gates.py"}   # not CLIs of their own
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


CHARTER_TEMPLATE = """# Working context

## Loop charter

Not set. The loop skill runs only when James fills this in.

- objective: (e.g. raise the mean Elo outcome)
- policy_file: (e.g. paintbot_pw_lab/policy/dist/<name>.bas)
- policy_name / player: (upload name)
- baseline: (accepted version `name:vN`)
- opponents: (explicit `policy_ref`s)
- allowed_changes: (classes of change)
- credit_budget: (credits per iteration)
- max_iterations:

## Identity and presence
- objective: not part of the charter
"""


def test_loop_readiness_reads_the_charter(tmp_path):
    path = tmp_path / "WORKING_CONTEXT.md"
    path.write_text(CHARTER_TEMPLATE)
    loop = pw.loop_readiness(path)
    assert not loop["ready"] and loop["missing"][0] == "not_set_marker"
    assert set(loop["missing"][1:]) == set(pw.CHARTER_FIELDS) and loop["charter_path"] == str(path)

    filled = (CHARTER_TEMPLATE.replace("Not set. The loop skill runs only when James fills this in.\n", "")
              .replace("(e.g. raise the mean Elo outcome)", "beat the top 3")
              .replace("(e.g. paintbot_pw_lab/policy/dist/<name>.bas)", "`paintbot_pw_lab/reference/base.bas`")
              .replace("(upload name)", "james-pw / James Boggs").replace("(accepted version `name:vN`)", "james-pw:v3")
              .replace("(explicit `policy_ref`s)", "coach:v8").replace("(classes of change)", "constants")
              .replace("(credits per iteration)", "20").replace("- max_iterations:", "- max_iterations: 5"))
    path.write_text(filled)
    loop = pw.loop_readiness(path)
    assert loop["ready"] and loop["missing"] == [] and loop["fields"]["baseline"] == "james-pw:v3"

    path.write_text(filled.replace("paintbot_pw_lab/reference/base.bas", "paintbot_pw_lab/policy/nope.bas"))
    assert pw.loop_readiness(path)["missing"] == ["policy_file_exists"]
    assert pw.loop_readiness(tmp_path / "absent.md")["missing"] == ["charter_file"]


class Proc:
    def __init__(self, returncode, envelope):
        self.returncode, self.stdout, self.stderr = returncode, json.dumps(envelope), ""


def test_league_check_rate_limit_is_not_an_environment_problem(monkeypatch):
    envelope = {"failures": [{"id": "observatory_api", "code": "rate_limited", "message": "HTTP 429"}],
                "next": ["wait a minute, then rerun ..."], "result": None}
    monkeypatch.setattr(pw.subprocess, "run", lambda *a, **k: Proc(1, envelope))
    result = pw.league_check()
    assert not result["ok"] and result["severity"] == "rate_limited" and "login" not in result["fix"]
    envelope = {"failures": [{"id": "environment", "code": "environment_missing", "message": "no token"}],
                "next": ["uv run softmax login"], "result": None}
    monkeypatch.setattr(pw.subprocess, "run", lambda *a, **k: Proc(3, envelope))
    assert pw.league_check()["severity"] == "missing" and pw.league_check()["fix"] == "uv run softmax login"


def test_doctor_rate_limit_exit_1_and_unready_loop_keeps_exit_code(monkeypatch, capsys):
    ok = [pw.check("uv", True, "uv")]
    unready = {"ready": False, "missing": ["objective"], "charter_path": "paintbot_pw_lab/WORKING_CONTEXT.md",
               "fields": {}, "skill": "paintbot_pw_lab/.claude/skills/paintbot-pw-loop/SKILL.md"}
    monkeypatch.setattr(pw, "loop_readiness", lambda: unready)
    monkeypatch.setattr(pw, "active_player", lambda: {"active_player_id": None, "session": "none",
                                                       "detail": "main user", "confirm": "uv run coworld player list"})
    monkeypatch.setattr(pw, "doctor_checks", lambda offline: ok)
    assert pw.main(["doctor", "--json"]) == 0                     # loop not ready: exit unchanged
    out = json.loads(capsys.readouterr().out)
    assert out["result"]["loop"]["ready"] is False and any("paintbot-pw-loop" in n for n in out["next"])
    assert out["result"]["player"]["confirm"] == "uv run coworld player list"

    throttled = ok + [pw.check("league_build", False, "HTTP 429", "wait", severity="rate_limited")]
    monkeypatch.setattr(pw, "doctor_checks", lambda offline: throttled)
    assert pw.main(["doctor", "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["failures"] == [{"id": "league_build", "code": "rate_limited", "message": "HTTP 429"}]
    assert out["next"][:2] == pw.RETRY_LATER and not any("softmax login" in n for n in out["next"])


def test_leaders_is_forwarded_to_scout_with_its_subcommand(monkeypatch):
    calls = []
    monkeypatch.setattr(pw.subprocess, "call", lambda argv, **kw: calls.append(argv) or 0)
    assert pw.main(["leaders", "--top", "3", "--json"]) == 0
    assert calls[0][1].endswith("pw_scout.py") and calls[0][2:] == ["leaders", "--top", "3", "--json"]
