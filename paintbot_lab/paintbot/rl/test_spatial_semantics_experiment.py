from run_spatial_semantics_experiment import passes_screen


def metrics(*, exact: int, changed_exact: int, movement: float) -> dict:
    return {
        "groups": {
            "all": {
                "samples": 10_000,
                "changed_action_samples": 5_000,
                "autoregressive_exact": exact,
                "autoregressive_changed_exact": changed_exact,
                "autoregressive_exact_action_accuracy": exact / 10_000,
                "autoregressive_changed_exact_action_accuracy": changed_exact / 5_000,
                "autoregressive_slot_accuracy": {"movement": movement},
            }
        }
    }


def test_spatial_screen_requires_exact_movement_and_held_signal() -> None:
    assert passes_screen(metrics(exact=5_850, changed_exact=1_200, movement=0.72))
    assert not passes_screen(metrics(exact=5_750, changed_exact=1_200, movement=0.72))
    assert not passes_screen(metrics(exact=5_850, changed_exact=1_200, movement=0.70))
    assert not passes_screen(metrics(exact=5_850, changed_exact=1_300, movement=0.72))
