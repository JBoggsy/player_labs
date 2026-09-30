"""pw_terrain: the shared terrain cache's keying, build-once protocol, pruning and LRU cap."""
import json
import os
import re
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import pw_release  # noqa: E402
import pw_terrain  # noqa: E402

PIN = "coworld-v9.9.9"


@pytest.fixture
def cache(tmp_path, monkeypatch):
    """A scratch cache root with the pin at PIN; returns <root>/terrain/."""
    monkeypatch.setenv("PW_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv(pw_terrain.ENV_SWITCH, raising=False)
    monkeypatch.delenv(pw_terrain.ENV_MAX_GB, raising=False)
    monkeypatch.setattr(pw_release, "current_tag", lambda: PIN)
    return tmp_path / "terrain"


def put(path: Path, size: int, age: float = 0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)
    stamp = time.time() - age
    os.utime(path, (stamp, stamp))
    return path


def test_file_name_packs_the_flags_in_engine_order():
    assert pw_terrain.file_name(48) == "island-f2047.pwterrain"   # every current tape and local match
    assert pw_terrain.file_name(35) == pw_terrain.file_name(44) == pw_terrain.file_name(48)
    assert pw_terrain.file_name(10) == "island-f0.pwterrain"
    assert pw_terrain.file_name(29) == "island-f127.pwterrain"    # through riverTerrain


def test_flag_rules_match_the_release_sim_nim():
    sim = pw_release.release_tree() / "examples" / "paintbot" / "sim.nim"
    if not sim.is_file():
        pytest.skip(f"no release worktree at {sim.parent} (run build_tools.sh)")
    body = sim.read_text().split("proc configureRules*", 1)[1].split("refreshTerrainTable()", 1)[0]
    found = [int(v) for v in re.findall(r"^\s*\w+ = visionRulesVersion >= (\d+)$", body, re.M)]
    assert tuple(found) == pw_terrain.FLAG_RULES


def test_load_or_build_builds_once_then_loads(cache):
    path = cache / PIN / "island-f2047.pwterrain"
    built, loaded = [], []

    def build(p):
        put(p.with_name(p.name + ".tmp-new"), 8).rename(p)
        built.append(p)

    put(path.with_name(path.name + ".tmp-dead"), 8)   # a killed builder's leftover
    assert pw_terrain.load_or_build(path, lambda p: loaded.append(p) or True, build) == "built"
    assert not path.with_name(path.name + ".tmp-dead").exists()
    os.utime(path, (1, 1))
    assert pw_terrain.load_or_build(path, lambda p: loaded.append(p) or True, build) == "loaded"
    assert len(built) == 1 and loaded == [path]
    assert path.stat().st_mtime > 1   # recency refreshed for the LRU cap


def test_a_rejected_file_is_never_overwritten(cache, capsys):
    path = put(cache / PIN / "island-f2047.pwterrain", 8)
    result = pw_terrain.load_or_build(path, lambda p: False, lambda p: pytest.fail("rebuilt"))
    assert result == "rejected" and path.read_bytes() == b"\0" * 8
    assert "terrain-cache clear" in capsys.readouterr().err


def test_parallel_processes_build_exactly_one_file(cache, tmp_path):
    """Eight processes race for a missing file: one builds, the rest wait on the lock and load."""
    path = cache / PIN / "island-f2047.pwterrain"
    log = tmp_path / "builds.log"
    script = textwrap.dedent(f"""
        import sys, time
        sys.path.insert(0, {str(TOOLS)!r})
        from pathlib import Path
        import pw_terrain
        path, log = Path({str(path)!r}), Path({str(log)!r})
        def build(p):
            with log.open("a") as f: f.write("built\\n")
            tmp = p.with_name(p.name + ".tmp-x" + str(__import__("os").getpid()))
            tmp.write_bytes(b"t" * 1000); time.sleep(0.5); tmp.rename(p)
        print(pw_terrain.load_or_build(path, lambda p: p.stat().st_size == 1000, build))
    """)
    procs = [subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True) for _ in range(8)]
    results = sorted(p.communicate(timeout=60)[0].strip() for p in procs)
    assert results == ["built"] + ["loaded"] * 7
    assert log.read_text().count("built") == 1
    assert sorted(p.name for p in path.parent.iterdir()) == [path.name, path.name + ".lock"]


def test_prune_drops_other_tags_but_keeps_the_pin_and_the_tag_in_use(cache):
    put(cache / PIN / "island-f2047.pwterrain", 10)
    put(cache / "coworld-v0.3.80" / "island-f2047.pwterrain", 10)
    put(cache / "coworld-v1.0.0" / "island-f2047.pwterrain", 10)
    removed = pw_terrain.prune({"coworld-v1.0.0"}, cap=10**9)
    assert removed == [str(cache / "coworld-v0.3.80")]
    assert sorted(p.name for p in cache.iterdir()) == ["coworld-v1.0.0", PIN]


def test_prune_keeps_a_directory_whose_file_is_being_built(cache):
    old = put(cache / "coworld-v0.3.80" / "island-f2047.pwterrain.tmp-live", 10)
    with pw_terrain.locked(old.with_name("island-f2047.pwterrain")):
        pw_terrain.prune(cap=10**9)
        assert old.exists()
    pw_terrain.prune(cap=10**9)
    assert not old.parent.exists()


def test_orphaned_temporary_files_go_unless_their_build_is_live(cache):
    target = cache / PIN / "island-f2047.pwterrain"
    tmp = put(target.with_name(target.name + ".tmp-abc"), 10)
    with pw_terrain.locked(target):
        assert pw_terrain.prune(cap=10**9) == [] and tmp.exists()
    assert pw_terrain.prune(cap=10**9) == [str(tmp)]


def test_cap_evicts_least_recently_used_first(cache):
    oldest = put(cache / PIN / "island-f0.pwterrain", 400, age=300)
    middle = put(cache / PIN / "island-f127.pwterrain", 400, age=200)
    newest = put(cache / PIN / "island-f2047.pwterrain", 400, age=100)
    assert pw_terrain.prune(cap=900) == [str(oldest)]
    assert middle.exists() and newest.exists()
    os.utime(middle)   # a run used it: now the newest
    assert pw_terrain.prune(cap=500) == [str(newest)]
    assert pw_terrain.prune(cap=0) == [str(middle)]


def test_cap_comes_from_the_environment(cache, monkeypatch):
    assert pw_terrain.cap_bytes() == 2_000_000_000
    monkeypatch.setenv(pw_terrain.ENV_MAX_GB, "0.5")
    assert pw_terrain.cap_bytes() == 500_000_000
    monkeypatch.setenv(pw_terrain.ENV_MAX_GB, "lots")
    with pytest.raises(SystemExit):
        pw_terrain.cap_bytes()


def test_disabled_or_untagged_runs_are_uncached_and_touch_nothing(cache, monkeypatch):
    stale = put(cache / "coworld-v0.3.80" / "island-f2047.pwterrain", 10)
    assert pw_terrain.prepare(None) is None
    monkeypatch.setenv(pw_terrain.ENV_SWITCH, "0")
    with pw_terrain.session(PIN) as directory:
        assert directory is None
        assert pw_terrain.ENV_DIR not in pw_terrain.env(directory)
    assert stale.exists()


def test_session_points_the_nim_tools_at_the_tag_directory(cache, monkeypatch):
    monkeypatch.setenv(pw_terrain.ENV_DIR, "/somewhere/else")
    with pw_terrain.session(PIN) as directory:
        assert directory == cache / PIN
        assert pw_terrain.env(directory)[pw_terrain.ENV_DIR] == str(cache / PIN)
    assert pw_terrain.env(None).get(pw_terrain.ENV_DIR) is None


def test_session_prunes_a_file_built_during_the_run_against_the_cap(cache, monkeypatch):
    monkeypatch.setenv(pw_terrain.ENV_MAX_GB, "0.000001")   # 1000 bytes
    with pw_terrain.session(PIN) as directory:
        put(directory / "island-f2047.pwterrain", 800)
        put(directory / "island-f0.pwterrain", 800, age=60)
    assert [p.name for p in directory.glob("*.pwterrain")] == ["island-f2047.pwterrain"]


def test_cli_status_and_clear(cache, capsys):
    put(cache / PIN / "island-f2047.pwterrain", 100)
    assert pw_terrain.main(["status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["ok"] and status["result"]["total_bytes"] == 100
    assert status["result"]["files"][0]["file"] == "island-f2047.pwterrain"
    assert pw_terrain.main(["clear", "--json"]) == 0
    cleared = json.loads(capsys.readouterr().out)
    assert cleared["result"]["total_bytes"] == 0 and len(cleared["result"]["removed"]) == 1
    assert pw_terrain.main(["bogus", "--json"]) == 2
