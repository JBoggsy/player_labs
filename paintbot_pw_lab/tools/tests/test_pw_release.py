"""pw_release (tools/release.env) and deployed_ref's offline logic: pins, exit codes, --write."""
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import deployed_ref  # noqa: E402
import pw_release  # noqa: E402

ENV_TEXT = """# comment kept
PW_RELEASE_TAG=coworld-v0.3.78
PW_RELEASE_SHA=570174a2
PW_DOCS_SHA=570174a2
"""


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    path = tmp_path / "release.env"
    path.write_text(ENV_TEXT)
    monkeypatch.setattr(pw_release, "RELEASE_ENV", path)
    monkeypatch.setattr(pw_release, "TOOLS", tmp_path)
    return path


def test_repo_release_env_is_complete():
    env = pw_release.read_env()
    assert env["PW_RELEASE_TAG"].startswith("coworld-v")
    assert len(env["PW_RELEASE_SHA"]) >= 7 and len(env["PW_DOCS_SHA"]) >= 7


def test_write_env_keeps_comments_and_docs_sha(env_file):
    pw_release.write_env("coworld-v0.3.79", "d0728ab13dccdc316a1c48b42154daa9c5230249")
    text = env_file.read_text()
    assert "# comment kept" in text
    assert pw_release.read_env() == {"PW_RELEASE_TAG": "coworld-v0.3.79", "PW_RELEASE_SHA": "d0728ab1",
                                     "PW_DOCS_SHA": "570174a2"}


def test_require_built_names_the_build_command(env_file):
    with pytest.raises(pw_release.NotBuilt, match=r"run paintbot_pw_lab/tools/build_tools.sh$"):
        pw_release.require_built("pw_trace")
    with pytest.raises(pw_release.NotBuilt, match=r"build_native.sh coworld-v0.3.70$"):
        pw_release.require_built("libpw.dylib", "coworld-v0.3.70")
    with pytest.raises(ValueError, match="valid: paintbot-headless"):
        pw_release.require_built("nope")
    (env_file.parent / "bin" / "coworld-v0.3.78").mkdir(parents=True)
    (env_file.parent / "bin" / "coworld-v0.3.78" / "pw_trace").write_text("")
    assert pw_release.require_built("pw_trace").name == "pw_trace"


def test_cli_json_and_exit_codes(env_file, capsys):
    assert pw_release.main(["--json", "--require", "pw_trace"]) == 3
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and out["tool"] == "pw_release" and out["release_tag"] == "coworld-v0.3.78"
    assert out["failures"][0]["code"] == "not_built"
    assert out["next"] == ["paintbot_pw_lab/tools/build_tools.sh"]
    assert pw_release.main(["--json"]) == 0
    with pytest.raises(SystemExit) as err:
        pw_release.main(["--require", "bogus"])
    assert err.value.code == 2


def test_parse_numstat_and_tools_current():
    rows = deployed_ref.parse_numstat("4\t4\texamples/paintbot/bots.nim\n-\t-\tbin.dat\n")
    assert rows == [{"path": "examples/paintbot/bots.nim", "added": 4, "deleted": 4},
                    {"path": "bin.dat", "added": None, "deleted": None}]
    env = {"PW_RELEASE_TAG": "coworld-v0.3.79", "PW_RELEASE_SHA": "d0728ab1", "PW_DOCS_SHA": "570174a2"}
    assert deployed_ref.tools_current("coworld-v0.3.79", "d0728ab13dcc", env)
    assert not deployed_ref.tools_current("coworld-v0.3.80", "ffff", env)
    assert not deployed_ref.tools_current("coworld-v0.3.79", None, env)


def _fake_league(monkeypatch, tag, sha, diff=()):
    monkeypatch.setattr(deployed_ref, "release_tags", lambda: {})
    monkeypatch.setattr(deployed_ref, "resolve_leagues", lambda tags: [
        {"label": "paintbot-pw (teams)", "league_id": "l", "tracked": True, "coworld_id": "c",
         "coworld": "paintbot-pw", "version": tag.removeprefix("coworld-v"), "tag": tag, "sha": sha}])
    monkeypatch.setattr(deployed_ref, "rule_diffstat", lambda clone, a, b: list(diff))


def test_deployed_ref_current_behind_and_write(env_file, monkeypatch, capsys):
    _fake_league(monkeypatch, "coworld-v0.3.78", "570174a2aaaa")
    assert deployed_ref.main(["--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and out["result"]["docs_rule_files_changed"] == 0

    _fake_league(monkeypatch, "coworld-v0.3.79", "d0728ab1bbbb",
                 [{"path": "examples/paintbot/sim.nim", "added": 2, "deleted": 2}])
    assert deployed_ref.main(["--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert not out["ok"] and out["outputs"] == [] and out["result"]["docs_rule_files_changed"] == 1
    assert out["next"][0].endswith("deployed_ref.py --write")

    assert deployed_ref.main(["--json", "--write"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["outputs"] == [str(env_file)] and out["result"]["written"]
    assert pw_release.read_env()["PW_RELEASE_TAG"] == "coworld-v0.3.79"
    assert deployed_ref.main(["--json"]) == 0      # now current
    capsys.readouterr()


def test_deployed_ref_environment_missing_exits_3(env_file, monkeypatch, capsys):
    def no_login():
        raise deployed_ref.EnvironmentMissing("no softmax login token: run `uv run softmax login`")
    monkeypatch.setattr(deployed_ref, "release_tags", no_login)
    assert deployed_ref.main(["--json"]) == 3
    out = json.loads(capsys.readouterr().out)
    assert out["failures"][0]["code"] == "environment_missing" and "softmax login" in out["failures"][0]["message"]


def test_deployed_ref_rate_limit_is_exit_1_not_a_login_problem(env_file, monkeypatch, capsys):
    monkeypatch.setattr(deployed_ref, "release_tags", lambda: {})

    def throttled(tags):
        raise deployed_ref.classify_http_error(429, "https://softmax.com/api/observatory/v2/leagues/x")
    monkeypatch.setattr(deployed_ref, "resolve_leagues", throttled)
    assert deployed_ref.main(["--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["failures"][0]["code"] == "rate_limited"
    assert "login" not in json.dumps(out) and out["next"] == [deployed_ref.RETRY]


def test_deployed_ref_http_classification_and_fix_in_next(env_file, monkeypatch, capsys):
    assert isinstance(deployed_ref.classify_http_error(401, "u"), deployed_ref.EnvironmentMissing)
    assert deployed_ref.classify_http_error(403, "u").fix == deployed_ref.LOGIN
    assert deployed_ref.classify_http_error(502, "u").code == "api_unavailable"
    monkeypatch.setattr(deployed_ref, "release_tags", lambda: {})

    def unauthorized(tags):
        raise deployed_ref.classify_http_error(401, "u")
    monkeypatch.setattr(deployed_ref, "resolve_leagues", unauthorized)
    assert deployed_ref.main(["--json"]) == 3
    out = json.loads(capsys.readouterr().out)
    assert out["failures"][0]["code"] == "environment_missing" and out["next"] == [deployed_ref.LOGIN]


def test_cache_root_honours_pw_cache_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("PW_CACHE_DIR", raising=False)
    assert pw_release.cache_root() == pw_release.TOOLS / ".cache"
    monkeypatch.setenv("PW_CACHE_DIR", str(tmp_path / "c"))
    assert pw_release.cache_root() == tmp_path / "c"
    assert pw_release.release_tree("coworld-v0.3.70") == tmp_path / "c" / "coworld-v0.3.70"
    import pw_mapdata
    assert pw_mapdata.map_cache("coworld-v0.3.70") == tmp_path / "c" / "maps" / "coworld-v0.3.70"
    assert pw_mapdata.map_cache(None) == tmp_path / "c" / "maps" / pw_mapdata.DEFAULT_TAG
