"""Search mode — imposter pre-kill positioning (the lead window before kill-ready).

STATUS (2026-06-24): PLACEHOLDER. The previous occupancy-hotspot + commit-to-most-
isolated-victim implementation was retired (cold-stored at ``modes/_deprecated/
search.py``, DO NOT USE) pending the new seeking approach: **stay with the group to
keep many victims reachable, and commit to shadowing an individual only once it
clearly peels off into isolation**, then hold position so Hunt can strike
(design.md → "Imposter seeking/positioning — NEW APPROACH"). Until that lands, this
stub keeps the mode registry valid and is a no-op (idle). Replace with the new
logic — do NOT revive the deprecated occupancy-seeking version.
"""

from __future__ import annotations

from crewrift.crewborg.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode, ModeParams


class SearchMode(Mode[Belief, ActionState, Intent]):
    name = "search"
    params_type = EmptyModeParams

    def __init__(self, params: ModeParams | None = None) -> None:
        super().__init__(params)

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del belief, action_state
        # TODO(new-seeking): group-follow -> detect clean peel-off -> shadow straggler.
        return Intent(kind="idle", reason="search: placeholder (new seeking approach pending)")
