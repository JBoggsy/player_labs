"""Identity, pairing, failure and request-body contracts of the A/B adapter (compare.py)."""
import sys
from collections import Counter
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import compare as cmp  # noqa: E402
import pw_ab_requests as req  # noqa: E402
import pw_episodes as pe  # noqa: E402

SAMPLE = TOOLS.parent / "episode_data" / "20260928T214433_ereq_5092af64-d3"
BINARY = TOOLS / "bin" / pe.DEFAULT_TAG / "pw_trace"
RICHARD = "b5bf25a9-a5ed-453f-b66d-cc4d03169e6b"   # seats 0,2,.. (red) in SAMPLE
DAVEEY = "84c2fd66-9d3e-4a69-9463-6363fffed584"    # seats 1,3,.. (blue), won 542-0


def row(arm, episode, side=0, seed=1, opp="opp", final_hash=None, config_seed=None, **values):
    r = cmp.empty_row(episode, arm, f"local:{arm}", side, [opp], opp, config_seed, seed, final_hash, 47, None)
    r.update(values)
    return r


def failed_episode(error_type, index):
    participants = [{"position": i, "policy_version_id": RICHARD if i % 2 == 0 else DAVEEY,
                     "policy_name": "r" if i % 2 == 0 else "d", "version": 1} for i in range(16)]
    return {"id": "ereq_f", "status": "failed", "error_type": error_type, "failed_policy_index": index,
            "participants": participants, "game_config": {"seed": 5}, "coworld_version": "0.3.78"}


def test_failure_attribution_follows_metta_forfeit_rules():
    assert cmp.failure_state(None) == ("ok", None)
    assert cmp.failure_state({"status": "completed"}) == ("ok", None)
    assert cmp.failure_state({"status": "running"}) == ("unfinished", None)
    assert cmp.failure_state(failed_episode("policy_error", 3)) == ("failed", 3)
    assert cmp.failure_state(failed_episode("pod_deleted", 3)) == ("failed", None)  # infrastructure
    exclusions = Counter()
    rows = cmp.failure_rows(failed_episode("policy_error", 3), {"baseline": RICHARD, "candidate": DAVEEY}, exclusions)
    by_arm = {r["arm"]: r for r in rows}
    assert by_arm["candidate"]["elo_outcome"] == 0.0 and by_arm["candidate"]["forfeit"] == "ours"   # seat 3 = blue
    assert by_arm["baseline"]["elo_outcome"] == 1.0 and by_arm["baseline"]["win_rate"] == 1.0
    assert by_arm["baseline"]["kills_per_seat"] is None and by_arm["baseline"]["ops_fail"] == 1.0
    assert exclusions == Counter(ops_fail_forfeit_scored=1)  # once per episode, not per arm
    exclusions = Counter()
    rows = cmp.failure_rows(failed_episode("pod_deleted", None), {"baseline": RICHARD, "candidate": DAVEEY}, exclusions)
    assert all(r["elo_outcome"] is None for r in rows) and exclusions == Counter(ops_fail_unattributed=1)


def test_pairing_by_opponent_side_seed_and_leftovers_counted():
    rows = [row("baseline", "b1", seed=1), row("candidate", "c1", seed=1),
            row("baseline", "b2", seed=1, side=1), row("candidate", "c2", seed=2, side=1),
            row("baseline", "b3", seed=3), row("baseline", "b4", seed=3), row("candidate", "c3", seed=3),
            row("baseline", "b5", seed=4, config_seed=9), row("candidate", "c5", seed=5, config_seed=9)]
    exclusions = Counter()
    pairs, info = cmp.pair_rows(rows, exclusions)
    assert {(b["episode_id"], c["episode_id"]) for b, c in pairs} == {("b1", "c1"), ("b3", "c3"), ("b5", "c5")}
    assert exclusions["unpaired_baseline"] == 2 and exclusions["unpaired_candidate"] == 1
    assert info == {"pairs_with_different_engine_seeds": 1}  # paired on config seed 9, engine seeds differ


def test_duplicate_games_and_rules_pooling_refused():
    rows = [row("baseline", "a", final_hash=7), row("baseline", "b", final_hash=7), row("baseline", "c", final_hash=8),
            row("candidate", "d", final_hash=7)]
    exclusions = Counter()
    kept = cmp.drop_duplicate_games(rows, exclusions)
    assert [r["episode_id"] for r in kept] == ["a", "c", "d"] and exclusions["duplicate_game"] == 1
    mixed = [row("baseline", "a"), {**row("candidate", "b"), "rules": 44}]
    with pytest.raises(SystemExit, match="rules"):
        cmp.check_single_ruleset(mixed)


def test_policy_resolution_is_exact():
    known = {"pv-1": "alpha:v1", "pv-2": "alpha:v2", "local:a.bas": "a.bas"}
    assert cmp.resolve_policy("alpha:v2", known) == "pv-2"
    assert cmp.resolve_policy("pv-1", known) == "pv-1"
    with pytest.raises(SystemExit):
        cmp.resolve_policy("alpha", known)
    with pytest.raises(SystemExit, match="several"):
        cmp.resolve_policy("x:v1", {"k1": "x:v1", "k2": "x:v1"})


def test_designs_use_their_tests_and_refuse_wrong_shapes():
    h2h = []
    for i in range(4):
        won = i % 2 == 0
        h2h += [row("baseline", f"e{i}", side=1, elo_outcome=0.3 if won else 0.6, win_rate=float(not won)),
                row("candidate", f"e{i}", elo_outcome=0.7 if won else 0.4, win_rate=float(won))]
    result = cmp.analyse(h2h, "h2h", Counter(), metrics=[m for m in cmp.METRICS if m[0] in ("elo_outcome", "win_rate")])
    tests = {(d.metric, d.group): d.test for d in result["deltas"]}
    assert tests[("elo_outcome", "all")] == "one_sample" and tests[("win_rate", "all")] == "decisive_binomial"
    with pytest.raises(SystemExit, match="h2h"):
        cmp.analyse(h2h, "paired", Counter())
    with pytest.raises(SystemExit, match="h2h"):
        cmp.analyse(h2h, "field", Counter())


@pytest.mark.skipif(not BINARY.is_file() or not SAMPLE.is_dir(), reason="needs the sample and pw_trace")
def test_hosted_sample_rows_are_complementary_and_per_seat():
    ep = pe.load_episode(SAMPLE)
    rows = {r["arm"]: r for r in cmp.episode_rows(ep, {"baseline": RICHARD, "candidate": DAVEEY}, Counter())}
    assert rows["candidate"]["elo_outcome"] == pytest.approx(0.771)
    assert rows["baseline"]["elo_outcome"] + rows["candidate"]["elo_outcome"] == pytest.approx(1.0)
    assert (rows["baseline"]["side"], rows["candidate"]["side"]) == ("red", "blue")
    assert rows["candidate"]["opponent"] == "richard-paintbot-pw:v1"
    assert rows["candidate"]["kills_per_seat"] == pytest.approx(30 / 8)
    assert rows["candidate"]["config_seed"] == 2026 and rows["candidate"]["engine_seed"] == 1327528889


def test_request_bodies_pin_sixteen_seats_by_parity():
    requests = req.compose("paired", "base:v1", "cand:v2", ["opp:v3"], [4, 5], {"league_id": "l"}, run_id="t")
    assert len(requests) == 2 * 2 * 2  # arms x sides x seeds
    for r in requests:
        body = r["body"]
        side = cmp.SIDES.index(r["side"])
        ours = [e["slot"] for e in body["roster"] if e["player"]["policy_ref"] == r["policy"]]
        assert ours == [s for s in range(16) if s % 2 == side]
        assert body["game_config_overrides"] == {"seed": r["seed"]} and body["num_episodes"] == 1
        assert set(body) <= req.TOP_LEVEL_FIELDS
    assert len({r["body"]["idempotency_key"] for r in requests}) == len(requests)
    single = req.compose("field", "base:v1", "base:v1", ["opp:v2"], None, {"league_id": "l"}, episodes=10, run_id="t")
    assert [(r["arm"], r["side"]) for r in single] == [("baseline", "red"), ("baseline", "blue")]
    with pytest.raises(ValueError, match="self-play"):
        req.compose("h2h", "base:v1", "cand:v2", [], None, {"league_id": "l"}, episodes=20, run_id="t")
    with pytest.raises(ValueError, match="seeds"):
        req.compose("paired", "a", "b", ["c"], None, {"league_id": "l"}, run_id="t")
    with pytest.raises(ValueError):
        req.validate({**requests[0]["body"], "roster": requests[0]["body"]["roster"][:15]})
