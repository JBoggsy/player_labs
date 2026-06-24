"""Pretend mode — imposter default blending stance.

STATUS (2026-06-24): PLACEHOLDER. The previous occupancy-density implementation was
retired (cold-stored at ``modes/_deprecated/pretend.py``, DO NOT USE) pending the
new seeking approach: **follow the group to preserve optionality, and commit to
shadowing an individual only once it clearly peels off the group into isolation**
(design.md → "Imposter seeking/positioning — NEW APPROACH"). Until that lands, this
stub keeps the mode registry valid and is a no-op (idle); it does not yet implement
group-following. Replace this with the new logic — do NOT revive the deprecated FSM.
"""

from __future__ import annotations

from crewrift.crewborg.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode, ModeParams


class PretendMode(Mode[Belief, ActionState, Intent]):
    name = "pretend"
    params_type = EmptyModeParams

    def __init__(self, params: ModeParams | None = None) -> None:
        super().__init__(params)

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del belief, action_state
        # TODO(new-seeking): follow the crew group; hold optionality until a peel-off.
        return Intent(kind="idle", reason="pretend: placeholder (new seeking approach pending)")
