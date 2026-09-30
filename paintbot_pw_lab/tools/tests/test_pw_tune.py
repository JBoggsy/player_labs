"""Contracts of pw_tune.py that do not need the engine: the @tune convention (parse and render
leave every other byte alone), the value grid, and the SPSA step's direction and bounds."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pw_tune  # noqa: E402

SOURCE = """if started = 0 then
  kWetCost = 6 ' @tune 2 12 1
  kMargin = -1 ' @TUNE -3 3
  kOther = 5 ' not tuned
end if
"""


def test_parse_knobs_reads_name_range_and_default_step():
    knobs = pw_tune.parse_knobs(SOURCE)
    assert [(k.name, k.line, k.value, k.low, k.high, k.step) for k in knobs] == [
        ("kWetCost", 1, 6, 2, 12, 1), ("kMargin", 2, -1, -3, 3, 1)]


@pytest.mark.parametrize("line", [
    "x = 1.5 ' @tune 0 3",        # not an integer
    "x = 9 ' @tune 0 3",          # start value outside the range
    "x = 1 ' @tune 3 0",          # empty range
    "x = 1 ' @tune 0",            # missing HIGH
    "x = 1 ' @tune 0 4 2",        # start value off the step grid
    "print x ' @tune 0 4",        # not an assignment
])
def test_parse_knobs_rejects_malformed_marks(line):
    with pytest.raises(ValueError):
        pw_tune.parse_knobs(line)


def test_parse_knobs_rejects_duplicates_and_empty():
    with pytest.raises(ValueError):
        pw_tune.parse_knobs("a = 1 ' @tune 0 3\nA = 2 ' @tune 0 3\n")
    with pytest.raises(ValueError):
        pw_tune.parse_knobs("a = 1\n")


def test_render_changes_only_knob_values():
    knobs = pw_tune.parse_knobs(SOURCE)
    out = pw_tune.render(SOURCE, knobs, {"kWetCost": 11, "kMargin": 3})
    assert out == SOURCE.replace("kWetCost = 6 '", "kWetCost = 11 '").replace("kMargin = -1 '", "kMargin = 3 '")
    assert pw_tune.render(SOURCE, knobs, {"kWetCost": 6, "kMargin": -1}) == SOURCE
    crlf = SOURCE.replace("\n", "\r\n")
    assert pw_tune.render(crlf, pw_tune.parse_knobs(crlf), {"kWetCost": 7, "kMargin": 0}).count("\r\n") == crlf.count("\r\n")


def test_knob_grid_rounds_and_clamps():
    knob = pw_tune.Knob("k", 0, 10, 0, 100, 25)
    assert [knob.to_value(u) for u in (-1, 0, 0.1, 0.13, 0.5, 0.99, 2)] == [0, 0, 0, 25, 50, 100, 100]
    assert knob.to_unit(50) == 0.5


def test_perturbation_is_reproducible_per_iteration():
    first = pw_tune.perturbation(3, 4, rng_seed=0)
    assert np.array_equal(first, pw_tune.perturbation(3, 4, rng_seed=0))
    assert set(np.abs(first)) == {1.0}


def test_spsa_moves_toward_the_better_side_within_bounds():
    knobs = [pw_tune.Knob("a", 0, 5, 0, 10, 1), pw_tune.Knob("b", 1, 5, 0, 10, 1)]
    u = np.array([0.5, 0.5])
    delta = np.array([1.0, -1.0])
    plus, minus, c_vec = pw_tune.spsa_points(u, delta, 0.01, knobs)
    assert np.allclose(c_vec, 0.1)  # widened to one grid step (1 / range 10)
    assert pw_tune.values_at(knobs, plus) != pw_tune.values_at(knobs, minus)
    after, gradient = pw_tune.spsa_update(u, delta, c_vec, y_plus=0.6, y_minus=0.4, a_k=1.0, max_move=0.2)
    # plus side scored higher: a goes up, b (perturbed -1 on the plus side) goes down; move capped.
    assert after[0] == pytest.approx(0.7) and after[1] == pytest.approx(0.3)
    assert gradient[0] > 0 > gradient[1]


def test_render_set_with_a_non_integer_value_is_a_usage_error(tmp_path, capsys):
    candidate = tmp_path / "cand.bas"
    candidate.write_text(SOURCE)
    code = pw_tune.main(["render", str(candidate), "--set", "kWetCost=abc", "--out", str(tmp_path / "out.bas")])
    assert code == 2
    assert not (tmp_path / "out.bas").exists()
