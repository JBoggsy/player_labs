"""Render the chat-effectiveness study into a static HTML report.

Follows crewrift-survey's plain f-string HTML pattern
(crewrift_lab/.claude/skills/crewrift-survey/scripts/survey.py:render_html)
— no templating engine, no external template files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _table(df: pd.DataFrame) -> str:
    return df.to_html(index=False, float_format=lambda x: f"{x:.3f}", border=0, classes="tbl")


def render_html(
    meta: dict,
    detector_validation: dict,
    crew_accuracy: pd.DataFrame,
    effectiveness: pd.DataFrame,
    winrate: pd.DataFrame,
) -> str:
    if detector_validation.get("n_matched"):
        validation_note = (
            f"Regex-vs-LLM agreement on {detector_validation['n_matched']} sampled chat lines: "
            f"stance agreement {detector_validation['stance_agreement']:.2f}, "
            f"target agreement {detector_validation['target_agreement']}. "
            "Treat the tables below with this precision in mind — they are not ground truth "
            "on the detector's own accuracy."
        )
    else:
        validation_note = "Detector validation not yet run — regex accusation-target detection is unverified."

    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><title>Chat accuracy &amp; effectiveness — {meta.get('field_snapshot_date', '')}</title>
<style>
body {{ font-family: -apple-system, sans-serif; margin: 2rem; color: #1a1a2e; }}
h1, h2 {{ border-bottom: 1px solid #ddd; padding-bottom: .3rem; }}
table.tbl {{ border-collapse: collapse; margin: 1rem 0; }}
table.tbl th, table.tbl td {{ padding: .4rem .8rem; border: 1px solid #ddd; text-align: right; }}
table.tbl th:first-child, table.tbl td:first-child {{ text-align: left; }}
.note {{ background: #fff8e1; padding: .8rem 1rem; border-left: 4px solid #f9a825; margin: 1rem 0; }}
.caveat {{ color: #555; font-style: italic; }}
</style></head><body>
<h1>Chat accuracy &amp; effectiveness — Crewrift Prime</h1>
<p class="caveat">Field snapshot: {meta.get('field_snapshot_date', '')} &middot; rounds {meta.get('round_ids', '')} &middot;
episodes {meta.get('n_episodes', '')} &middot; entrants {meta.get('entrants', '')}</p>
<p class="caveat">Observational, not causal: no randomized intervention on who accuses whom.</p>
<div class="note">{validation_note}</div>

<h2>1. Crew accusation accuracy (vs. ground-truth imposter)</h2>
{_table(crew_accuracy)}

<h2>2. Same-meeting effectiveness (crew + imposter)</h2>
{_table(effectiveness)}

<h2>3. Win-rate association (seat-normalized)</h2>
{_table(winrate)}
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the chat-effectiveness HTML report.")
    parser.add_argument("--meta", type=Path, required=True, help="JSON: field_snapshot_date, round_ids, n_episodes, entrants.")
    parser.add_argument("--validation", type=Path, required=True, help="JSON from validate_detector.py.")
    parser.add_argument("--metrics-dir", type=Path, required=True, help="Dir with crew_accuracy/effectiveness/winrate_association parquet.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    meta = json.loads(args.meta.read_text())
    validation = json.loads(args.validation.read_text())
    crew_accuracy = pd.read_parquet(args.metrics_dir / "crew_accuracy.parquet")
    effectiveness = pd.read_parquet(args.metrics_dir / "effectiveness.parquet")
    winrate = pd.read_parquet(args.metrics_dir / "winrate_association.parquet")

    html = render_html(meta, validation, crew_accuracy, effectiveness, winrate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html)
    print(f"Wrote report -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
