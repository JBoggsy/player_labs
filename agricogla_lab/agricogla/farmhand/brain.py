"""farmhand decision logic — DELEGATES to the proven v1 player logic.

After repeated reimplementation-parity bugs, farmhand now runs v1's EXACT decision
functions (vendored verbatim in v1_logic.py) instead of a hand-port. The only
new code is the adapter (choices_adapter.py) that synthesizes the legal-move
`choices`/`options` layer v1 expects from the raw cogweb view — because
cogweb.player.v1 does not provide it (the old protocol did). So: farmhand == v1,
guaranteed, plus the SDK transport/tracing and the PARAMS beam-search surface
(v1_logic reads the same AGRICOGLA_PARAMS via its own _load_params).

On a rejected reply (our synthesized legality disagreed with the host) we drop to
an always-legal no-arg placement rather than re-guess.
"""

from __future__ import annotations

from agricogla.farmhand import v1_logic
from agricogla.farmhand.choices_adapter import synth_obs

SAFE_NOARG = (
    "day_laborer", "fishing", "forest", "clay_pit", "reed_bank", "grain_seeds",
    "grove", "copse", "hollow", "resource_market", "traveling_players",
    "r_sheep", "r_boar", "r_cattle", "r_vegetable", "quarry_stall",
    "r_west_quarry", "r_east_quarry",
)


class Brain:
    def __init__(self, params: dict | None = None) -> None:
        # v1_logic carries its own PARAMS (loaded from AGRICOGLA_PARAMS at import);
        # params arg kept for API compatibility with the bridge/tests.
        self.params = params

    def decide(self, view: dict, seat: int, rejected: bool) -> dict:
        me = view["players"][seat]
        if view.get("phase") == "feeding":
            try:
                return v1_logic.decide_feeding(synth_obs(view, seat))
            except Exception:
                return {"conversions": []}  # safest legal feed (host falls back)
        if rejected:
            return self._fallback(view)
        try:
            return v1_logic.pick_best_action(synth_obs(view, seat))
        except Exception:
            return self._fallback(view)

    def _fallback(self, view: dict) -> dict:
        free = {s["id"] for s in view.get("actionSpaces", []) if s.get("occupiedBy") is None}
        for sid in SAFE_NOARG:
            if sid in free:
                return {"action": sid}
        return {"action": next(iter(free))} if free else {"action": "day_laborer"}
