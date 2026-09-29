"""Contracts of pw_episodes: tape sniffing, seat/team/policy joins, results cross-checks.

The integration tests trace a sample league replay and skip when the pw_trace build or
the (gitignored) sample episode is absent.
"""
import gzip
import json
import shutil
import struct
import sys
import zlib
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import pw_episodes as pe  # noqa: E402

SAMPLE = TOOLS.parent / "episode_data" / "20260928T214433_ereq_5092af64-d3"
BINARY = TOOLS / "bin" / pe.DEFAULT_TAG / "pw_trace"
needs_sample = pytest.mark.skipif(not (SAMPLE.is_dir() and BINARY.is_file()),
                                  reason="sample episode or pw_trace build missing")


def fake_tape(rules=47, game=b"paintbot_pw"):
    return pe.MAGIC + struct.pack("<HHH", 1, rules, len(game)) + game + b"payload"


def test_tape_sniffing_accepts_raw_gzip_and_zlib():
    raw = fake_tape()
    for data in (raw, gzip.compress(raw), zlib.compress(raw)):
        assert pe.raw_tape(data) == raw
    assert pe.tape_header(raw) == {"file_format": 1, "game_version": 47, "game": "paintbot_pw",
                                   "rules": 47, "ffa": False}
    assert pe.tape_header(fake_tape(1047))["ffa"] is True
    with pytest.raises(pe.EpisodeError):
        pe.raw_tape(b"{\"not\": \"a tape\"}")


def meta(seats=4):
    return {"seats": seats, "names": [f"P{i}" for i in range(seats)]}


def episode(seats=4, slots=True, order=None):
    participants = [{"position": i, "policy_version_id": f"pv{i % 2}", "policy_name": f"pol{i % 2}",
                     "player_name": f"P{i}", "version": 3} for i in range(seats)]
    if order:
        participants = [participants[i] for i in order]
    e = {"participants": participants}
    if slots:
        e["game_config"] = {"slots": [{"team": "red" if i % 2 == 0 else "blue"} for i in range(seats)]}
    return e


def test_seats_join_by_position_not_array_order():
    rows, notes = pe.seat_identity(None, meta(), episode(order=[3, 1, 0, 2]), None)
    assert [r["seat"] for r in rows] == [0, 1, 2, 3]
    assert [r["policy_version_id"] for r in rows] == ["pv0", "pv1", "pv0", "pv1"]
    assert [r["team"] for r in rows] == [0, 1, 0, 1]
    assert all(r["team_source"] == "game_config" for r in rows) and notes == []
    assert [r["policy_key"] for r in rows] == ["pv0", "pv1", "pv0", "pv1"]
    assert all(r["name_matches_tape"] for r in rows)


def test_team_disagreeing_with_engine_parity_fails_the_episode():
    e = episode()
    e["game_config"]["slots"][2]["team"] = "blue"
    with pytest.raises(pe.EpisodeError) as error:
        pe.seat_identity(None, meta(), e, None)
    assert error.value.code == "identity"


def test_missing_slots_falls_back_to_parity_with_a_note():
    rows, notes = pe.seat_identity(None, meta(), episode(slots=False), None)
    assert [r["team"] for r in rows] == [0, 1, 0, 1]
    assert {r["team_source"] for r in rows} == {"engine_parity"}
    assert notes and notes[0].startswith("team_from_parity")


def test_participant_positions_must_cover_every_seat():
    e = episode()
    e["participants"].pop(1)
    with pytest.raises(pe.EpisodeError):
        pe.seat_identity(None, meta(), e, None)


def test_local_meta_identity_and_anonymous_fallback():
    local = {"seats": [{"position": i, "policy_name": "a.bas" if i % 2 == 0 else "b.bas", "team": i % 2}
                       for i in range(4)]}
    rows, _ = pe.seat_identity(None, meta(), None, local)
    assert [r["policy_key"] for r in rows] == ["local:a.bas", "local:b.bas", "local:a.bas", "local:b.bas"]
    rows, notes = pe.seat_identity(None, meta(), None, None)
    assert rows[1]["policy_key"] == "local:P1" and notes[0].startswith("anonymous_local")


def summary(glory=(0, 542), ticks=1649, winner=1):
    return {"glory": list(glory), "ticks": ticks, "winner": winner}


def test_results_cross_check():
    m = {"seats": 4, "seed": 7}
    good = {"scores": [0, 542, 0, 542], "ticks": 1649, "seed": 7, "outcome": "1"}
    assert pe.check_results(m, summary(), good, None) == "results.json"
    for bad in ({**good, "ticks": 1650}, {**good, "seed": 8}, {**good, "scores": [0, 541, 0, 542]},
                {**good, "outcome": "0"}):
        with pytest.raises(pe.EpisodeError) as error:
            pe.check_results(m, summary(), bad, None)
        assert error.value.code == "results_mismatch"
    scores = {"participant_scores": [{"position": i, "score": [0, 542][i % 2]} for i in range(4)]}
    assert pe.check_results(m, summary(), None, scores) == "participant_scores"
    assert pe.check_results(m, summary(), None, None) == "none"


@needs_sample
def test_sample_episode_tables_and_cache(tmp_path):
    directory = tmp_path / "episode"
    directory.mkdir()
    for name in ("episode.json", "results.json", "replay.json"):
        shutil.copy(SAMPLE / name, directory / name)
    ep = pe.load_episode(directory)
    assert not ep.cache_hit and ep.summary["verified"]
    assert set(ep.tables) == set(pe.TABLES)
    results = json.loads((directory / "results.json").read_text())
    row = ep["episodes"].iloc[0]
    assert row.ticks == results["ticks"] and row.engine_seed == results["seed"]
    assert len(ep["seats"]) == 16 and ep["seats"].seat.tolist() == list(range(16))
    # Every gun hit in shots has exactly one gun damage row, and kills match the engine's counters.
    shots, damage, kills = ep["shots"], ep["damage"], ep["kills"]
    assert shots.hit.sum() == (damage.weapon == "gun").sum()
    assert shots[shots.hit].hit_distance.notna().all()
    enemy_kills = kills[kills.seat.notna() & ~kills.friendly & ~kills["self"]]
    assert len(enemy_kills) == ep["seats"].ss_kills.sum()
    # One row per (episode, seat) in states at every sample.
    states = ep["states"]
    assert (states.groupby("t").size() == 16).all()
    assert pe.load_episode(directory).cache_hit
    # Changing an input invalidates the cache; a wrong results.json fails the episode.
    results["scores"][1] += 1
    (directory / "results.json").write_text(json.dumps(results))
    with pytest.raises(pe.EpisodeError) as error:
        pe.load_episode(directory)
    assert error.value.code == "results_mismatch"


@needs_sample
def test_batch_lists_failures_instead_of_dropping(tmp_path):
    good = tmp_path / "good"
    good.mkdir()
    for name in ("episode.json", "results.json", "replay.json"):
        shutil.copy(SAMPLE / name, good / name)
    missing = tmp_path / "missing"
    missing.mkdir()
    shutil.copy(SAMPLE / "episode.json", missing / "episode.json")
    corrupt = tmp_path / "corrupt"
    corrupt.mkdir()
    for name in ("episode.json", "results.json"):
        shutil.copy(SAMPLE / name, corrupt / name)
    tape = bytearray((SAMPLE / "replay.json").read_bytes())
    tape[-5000] ^= 0xFF
    (corrupt / "replay.json").write_bytes(bytes(tape))
    # The same episode id twice would be a duplicate, so give the copies distinct ids.
    for i, d in enumerate((missing, corrupt)):
        e = json.loads((d / "episode.json").read_text())
        e["id"] = f"ereq_copy{i}"
        (d / "episode.json").write_text(json.dumps(e))
    batch = pe.load_batch(tmp_path)
    assert len(batch.episodes) == 1
    assert dict(batch.exclusions) == {"no_replay": 1, "trace_failed": 1}
    con = pe.open_duckdb(batch)
    assert con.execute("select count(*) from seats").fetchone() == (16,)
    assert pe.main([str(tmp_path)]) == 1


def test_cache_variants_are_separate_directories(tmp_path):
    binary = pe.pw_release.bin_dir(pe.DEFAULT_TAG) / "pw_trace"
    assert pe.cache_variant(None, binary, pe.TraceOptions()) == ""
    assert pe.cache_variant(pe.DEFAULT_TAG, binary, pe.TraceOptions()) == ""
    other = pe.pw_release.bin_dir("coworld-v0.3.70") / "pw_trace"
    assert pe.cache_variant("coworld-v0.3.70", other, pe.TraceOptions()) == "coworld-v0.3.70"
    fine = pe.TraceOptions(window=(960, 1560))
    assert pe.cache_variant("coworld-v0.3.70", other, fine) == "coworld-v0.3.70+se6-ve0-w960_1560"
    assert pe.cache_variant(None, binary, pe.TraceOptions(vis_every=24)) == "se6-ve24"
    custom = tmp_path / "pw_trace"
    custom.write_bytes(b"x")
    assert pe.cache_variant(None, custom, pe.TraceOptions()).startswith("bin-")

    hosted = pe.Source("hosted", tmp_path / "ep" / "replay.gz", None, None, None, tmp_path / "ep" / "pw_cache",
                       tmp_path / "ep")
    assert pe.variant_cache(hosted, "") == tmp_path / "ep" / "pw_cache"
    assert pe.variant_cache(hosted, "se6-ve24") == tmp_path / "ep" / "pw_cache@se6-ve24"
    local = pe.local_source(tmp_path / "m.replay")
    assert pe.variant_cache(local, "se6-ve24") == tmp_path / "m@se6-ve24.pw_cache"   # matches *.pw_cache/ ignore
    assert pe.in_cache(tmp_path / "ep" / "pw_cache@x" / "a.replay") and pe.in_cache(tmp_path / "m@x.pw_cache" / "t")
    assert not pe.in_cache(tmp_path / "ep" / "replay.gz")


@needs_sample
def test_a_finer_trace_does_not_replace_the_default_cache(tmp_path):
    directory = tmp_path / "episode"
    directory.mkdir()
    for name in ("episode.json", "results.json", "replay.json"):
        shutil.copy(SAMPLE / name, directory / name)
    assert not pe.load_episode(directory).cache_hit
    fine = pe.load_episode(directory, options=pe.TraceOptions(window=(100, 160)))
    assert not fine.cache_hit and fine.source.cache.name == "pw_cache@se6-ve0-w100_160"
    assert pe.load_episode(directory).cache_hit                       # the default is still there
    assert pe.load_episode(directory, options=pe.TraceOptions(window=(100, 160))).cache_hit
    assert len(pe.discover([tmp_path])) == 1                          # variant dirs are not episodes
