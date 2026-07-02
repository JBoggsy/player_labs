"""Accuse mode: call a meeting on a player who is tailing us (design §7.1).

When we detect we're being actively shadowed by someone the meeting would actually
convict (``active_tail_suspect`` — an ongoing ``tailing_self`` interval *and* that
player is ``top_suspect``, the one Attend Meeting would vote out), we stop what we're
doing and go **call a meeting** rather than run away: emit ``call_meeting`` (the action
layer walks to the emergency button and presses it), and once the meeting opens, Attend
Meeting accuses and votes that same top suspect. The call bar IS the conviction bar, so
we never burn the one-shot button on a tail the meeting would only silently skip
(``strategy.suspicion.active_tail_suspect``).

This replaces the old keep-away Flee behaviour: a believed imposter shadowing us is
better answered by dragging them into a public vote than by fleeing. The emergency
button is a **one-shot** resource (``buttonCalls = 1``), so the *selector*
(``strategy.rule_based``) — not this mode — decides when to spend it and won't
re-enter Accuse once the call is used.
"""

from __future__ import annotations

from crewrift.crewborg.strategy.suspicion import active_tail_suspect
from crewrift.crewborg.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode


class AccuseMode(Mode[Belief, ActionState, Intent]):
    name = "accuse"
    params_type = EmptyModeParams

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        # Best-effort record of whom we mean to accuse (the meeting re-derives the
        # vote from suspicion); None if the tail just lapsed while we commit to the run.
        target = active_tail_suspect(belief)
        return Intent(kind="call_meeting", target_color=target, reason="calling a meeting to accuse a tail")
