"""Tunable policy parameters — the beam-search search space for farmhand.

Defaults reproduce the strategic intent of the prior heuristic. A variant
overrides a subset via the ``AGRICOGLA_PARAMS`` env var (inline JSON), which the
build bakes from a candidate file. Unknown keys are ignored; malformed JSON falls
back to defaults so the policy never crashes on a bad override.

These params are the optimization surface: the beam loop perturbs them, builds a
variant image per candidate, and evaluates via hosted experience requests.
"""

from __future__ import annotations

import json
import os

DEFAULT_PARAMS: dict[str, float] = {
    # Family growth — central compounding lever, gated on a real food engine (§1.1/§1.2)
    "grow_safe": 80.0,
    "grow_base": 40.0,
    "grow_urgency_penalty": 8.0,
    "urgent_grow_safe": 65.0,
    "urgent_grow_risky": 30.0,
    # Rooms (enable growth)
    "room_housebound": 55.0,
    "room_ahead": 35.0,
    # Food / cooking (never-starve, §1.2)
    "cooker_critical": 50.0,
    "cooker_urgency": 5.0,
    "renovate_cooker": 45.0,
    "day_laborer_base": 3.0,
    "day_laborer_urgency": 8.0,
    "fishing_urgency": 2.0,
    # Resources
    "wood_need_growth": 5.0,
    "wood_need_base": 2.0,
    # Fields & sowing (sow-before-bake, breadth; §1.3/§1.4)
    "field_first": 28.0,
    "field_gap": 20.0,
    "sow_per_field": 6.0,
    # Category breadth (the 0->1 ~+2 swing; §1.4)
    "animal_category_bonus": 8.0,
    "animal_breed_bonus": 10.0,
    "veg_gap": 22.0,
    # Cards (relevant at 4p; §1.5/§1.6)
    "occupation_early": 18.0,
    "occupation_late": 10.0,
    # Renovation / stone engine (looser 4p economy)
    "redevelop_late": 22.0,
    # Late-game fill
    "late_fill_round": 10.0,
    "late_fill_cap": 8.0,
}


def load_params() -> dict[str, float]:
    """Defaults overlaid with any AGRICOGLA_PARAMS override (env or params.json)."""
    params = dict(DEFAULT_PARAMS)
    raw = os.environ.get("AGRICOGLA_PARAMS")
    if not raw:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "params.json")
        if os.path.exists(path):
            try:
                with open(path) as handle:
                    raw = handle.read()
            except OSError:
                raw = None
    if raw:
        try:
            overrides = json.loads(raw)
            if isinstance(overrides, dict):
                params.update(
                    {k: v for k, v in overrides.items() if k in DEFAULT_PARAMS}
                )
        except (ValueError, TypeError):
            pass
    return params
