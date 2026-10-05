"""score_outcome: the ladder's result-score margin at an explicit scale (compare.py)."""
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import compare as cmp  # noqa: E402
import pw_episodes as pe  # noqa: E402

SAMPLE = TOOLS.parent / "episode_data" / "20260928T214433_ereq_5092af64-d3"
BINARY = TOOLS / "bin" / pe.DEFAULT_TAG / "pw_trace"
RICHARD = "b5bf25a9-a5ed-453f-b66d-cc4d03169e6b"   # red in SAMPLE, lost 0-542
DAVEEY = "84c2fd66-9d3e-4a69-9463-6363fffed584"    # blue in SAMPLE, won 542-0


def row(arm, episode, side=0, seed=1, **values):
    r = cmp.empty_row(episode, arm, f"local:{arm}", side, ["opp"], "opp", None, seed, None, 49, None)
    r.update(values)
    return r


def test_formula_matches_openskill_and_clips():
    # metta dcdfc19a openskill.py: clamp(0.5 + (means[0] - means[1]) / (2 * margin_scale), 0, 1)
    assert cmp.score_outcome(542, 0, 600) == pytest.approx(0.5 + 542 / 1200)
    assert cmp.score_outcome(0, 542, 600) == pytest.approx(0.5 - 542 / 1200)
    assert cmp.score_outcome(542, 0, 1000) == pytest.approx(0.771)       # the historical scale
    assert cmp.score_outcome(0, 0, 600) == 0.5                           # a 0-glory win is a draw
    assert cmp.score_outcome(1300, 0, 600) == 1.0 and cmp.score_outcome(0, 1300, 600) == 0.0
    assert cmp.score_outcome(600, 0, 600) == 1.0                         # exactly at the clip edge


def test_scale_validation_is_a_usage_error():
    assert cmp.margin_scale_arg("600") == 600.0
    for bad in ("0", "-5", "nan", "inf", "six"):
        with pytest.raises(SystemExit, match="margin-scale"):
            cmp.margin_scale_arg(bad)


def test_forfeit_scores_zero_one_and_infrastructure_stays_unknown():
    participants = [{"position": i, "policy_version_id": RICHARD if i % 2 == 0 else DAVEEY,
                     "policy_name": "r" if i % 2 == 0 else "d", "version": 1} for i in range(16)]
    failed = {"id": "f", "status": "failed", "error_type": "policy_error", "failed_policy_index": 4,
              "participants": participants, "game_config": {"seed": 5}, "coworld_version": "0.3.115"}
    rows = {r["arm"]: r for r in cmp.failure_rows(failed, {"baseline": RICHARD, "candidate": DAVEEY}, Counter())}
    assert rows["baseline"]["score_outcome"] == 0.0 and rows["candidate"]["score_outcome"] == 1.0  # seat 4 = red
    infra = {**failed, "error_type": "pod_deleted"}
    assert all(r["score_outcome"] is None
               for r in cmp.failure_rows(infra, {"baseline": RICHARD, "candidate": DAVEEY}, Counter()))


def test_team_scores_use_exact_result_scores():
    seats = pd.DataFrame({"team": [0, 1] * 8, "score": [0.0, 542.0] * 8})

    class Ep(dict):
        pass

    ep = Ep(seats=seats)
    assert cmp.team_scores(ep) == {0: 0.0, 1: 542.0}


def test_sprt_and_h2h_follow_the_requested_outcome():
    rows = []
    for i in range(6):
        rows += [row("baseline", f"b{i}", seed=i, elo_outcome=0.5, score_outcome=0.5),
                 row("candidate", f"c{i}", seed=i, elo_outcome=0.5, score_outcome=0.9)]
    elo = cmp.primary_sprt(rows, "paired", Counter(), h0=0, h1=0.05, alpha=0.05, beta=0.05)
    score = cmp.primary_sprt(rows, "paired", Counter(), h0=0, h1=0.05, alpha=0.05, beta=0.05, target="score_outcome")
    assert elo.estimate == pytest.approx(0.0) and score.estimate == pytest.approx(0.4)
    # a non-outcome --target leaves the SPRT on the primary metric
    assert cmp.sprt_target("kills_per_seat") == "elo_outcome" and cmp.sprt_target("score_outcome") == "score_outcome"
    h2h = [row("baseline", f"e{i}", side=1, score_outcome=0.4) for i in range(3)]
    h2h += [row("candidate", f"e{i}", score_outcome=0.6) for i in range(3)]
    result = cmp.analyse(h2h, "h2h", Counter(), metrics=[m for m in cmp.METRICS if m[0] == "score_outcome"])
    assert {d.test for d in result["deltas"] if d.group == "all"} == {"one_sample"}


def test_cli_defaults_keep_history_and_propagate_scale():
    parser = cmp.build_parser()
    base = ["ROOT", "--design", "paired", "--baseline", "a", "--candidate", "b"]
    args = parser.parse_args(["compare", *base])
    assert (args.target, args.margin_scale) == ("elo_outcome", 1000.0)
    args = parser.parse_args(["compare", *base, "--target", "score_outcome", "--margin-scale", "600"])
    assert (args.target, args.margin_scale) == ("score_outcome", 600.0)
    args = parser.parse_args(["sprt", *base, "--target", "score_outcome", "--margin-scale", "600"])
    assert (args.target, args.margin_scale) == ("score_outcome", 600.0)
    with pytest.raises(SystemExit):
        parser.parse_args(["sprt", *base, "--target", "kills_per_seat"])
    with pytest.raises(SystemExit):
        parser.parse_args(["compare", *base, "--margin-scale", "0"])
    meta = cmp.outcome_metadata(600.0)
    assert meta["margin_scale"] == 600.0 and "2 * 600" in meta["score_outcome"]


def test_bad_scale_exits_two_with_envelope(capsys):
    code = cmp.main(["compare", "ROOT", "--design", "paired", "--baseline", "a", "--candidate", "b",
                     "--margin-scale", "-1", "--json"])
    assert code == 2
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is False and "margin-scale" in json.dumps(envelope)


@pytest.mark.skipif(not BINARY.is_file() or not SAMPLE.is_dir(), reason="needs the sample and pw_trace")
def test_hosted_sample_scale_propagates_and_elo_is_unchanged():
    ep = pe.load_episode(SAMPLE)
    keys = {"baseline": RICHARD, "candidate": DAVEEY}
    at600 = {r["arm"]: r for r in cmp.episode_rows(ep, keys, Counter(), 600.0)}
    default = {r["arm"]: r for r in cmp.episode_rows(ep, keys, Counter())}
    assert at600["candidate"]["score_outcome"] == pytest.approx(0.5 + 542 / 1200)
    assert at600["baseline"]["score_outcome"] + at600["candidate"]["score_outcome"] == pytest.approx(1.0)
    assert at600["candidate"]["elo_outcome"] == pytest.approx(0.771)      # historical metric untouched
    assert default["candidate"]["score_outcome"] == pytest.approx(default["candidate"]["elo_outcome"])
