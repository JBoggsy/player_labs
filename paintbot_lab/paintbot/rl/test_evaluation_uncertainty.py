import pytest

from evaluation_uncertainty import replay_cluster_bootstrap


def test_replay_cluster_bootstrap_is_deterministic_and_row_weighted() -> None:
    outcomes = {
        "a": (3, 3),
        "b": (0, 1),
        "c": (1, 2),
        "d": (0, 2),
        "e": (1, 1),
    }

    first = replay_cluster_bootstrap(outcomes, n_resamples=999)
    second = replay_cluster_bootstrap(outcomes, n_resamples=999)

    assert first == second
    assert first["point_estimate"] == pytest.approx(5 / 9)
    assert first["samples"] == 9
    assert first["correct"] == 5
    assert first["clusters"] == 5
    assert first["available"] is True
    assert first["lower"] < first["point_estimate"] < first["upper"]


def test_replay_cluster_bootstrap_marks_single_cluster_unavailable() -> None:
    result = replay_cluster_bootstrap({"only": (1, 1)}, n_resamples=99)

    assert result["available"] is False
    assert result["point_estimate"] == 1.0
    assert result["lower"] is None


@pytest.mark.parametrize(
    "outcomes",
    [
        {},
        {"a": (2, 1), "b": (0, 1)},
        {"a": (0, 0), "b": (0, 1)},
    ],
)
def test_replay_cluster_bootstrap_rejects_invalid_clusters(outcomes) -> None:
    with pytest.raises(ValueError):
        replay_cluster_bootstrap(outcomes, n_resamples=99)
