import sys
from pathlib import Path

import numpy as np
import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from build_report import render_html  # noqa: E402

META = {"field_snapshot_date": "2026-07-02", "round_ids": "391-394", "n_episodes": 240, "entrants": "11"}
VALIDATION = {"n_matched": 150, "n_sampled": 200, "stance_agreement": 0.82, "target_agreement": 0.77}
CREW_ACCURACY = pd.DataFrame([{"speaker_policy": "crewborg", "n": 40, "accuracy": 0.55}])
EFFECTIVENESS = pd.DataFrame(
    [{"speaker_policy": "crewborg", "speaker_role": "crew", "n": 40, "p_target_voted": 0.6, "p_target_ejected": 0.4, "mean_baseline_rate": 0.2}]
)
WINRATE = pd.DataFrame(
    [{"policy_name": "crewborg", "role": "crew", "seat_games": 100, "seat_win_rate": 0.24, "accusations_made": 40, "accuracy": 0.55}]
)


def test_render_html_includes_all_sections_and_caveats():
    html = render_html(META, VALIDATION, CREW_ACCURACY, EFFECTIVENESS, WINRATE)

    assert "Crew accusation accuracy" in html
    assert "Same-meeting effectiveness" in html
    assert "Win-rate association" in html
    assert "Observational, not causal" in html
    assert "crewborg" in html
    assert "2026-07-02" in html


def test_render_html_flags_missing_validation():
    html = render_html(META, {"n_matched": 0, "stance_agreement": None, "target_agreement": None}, CREW_ACCURACY, EFFECTIVENESS, WINRATE)

    assert "not yet run" in html or "unverified" in html


def test_render_html_formats_none_target_agreement():
    """When target_agreement is None (no accusations in sample), format as 'n/a' not 'None'."""
    validation = {"n_matched": 50, "stance_agreement": 0.9, "target_agreement": None}
    html = render_html(META, validation, CREW_ACCURACY, EFFECTIVENESS, WINRATE)

    assert "None" not in html, "Literal 'None' should not appear in HTML output"
    assert "n/a" in html, "Should format None target_agreement as 'n/a'"
    assert "target agreement n/a" in html, "Should read as 'target agreement n/a'"


def test_render_html_formats_nan_metric_cell_as_na():
    """A zero-accusation policy leaves `accuracy` as NaN in winrate_association;
    it must render as 'N/A' in the HTML table, not the literal 'nan'.
    """
    winrate_with_nan = pd.DataFrame(
        [
            {"policy_name": "crewborg", "role": "crew", "seat_games": 100, "seat_win_rate": 0.24, "accusations_made": 40, "accuracy": 0.55},
            {"policy_name": "notsus", "role": "imposter", "seat_games": 50, "seat_win_rate": 0.6, "accusations_made": 0, "accuracy": np.nan},
        ]
    )

    html = render_html(META, VALIDATION, CREW_ACCURACY, EFFECTIVENESS, winrate_with_nan)

    assert ">nan<" not in html, "Literal 'nan' should not appear as a table cell in HTML output"
    assert "N/A" in html, "Should render NaN accuracy cell as 'N/A'"
