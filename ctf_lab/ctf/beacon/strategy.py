"""The priority ladder — choose ONE navigation objective per tick (v2, role-aware).

Combat and aim are NOT a rung here; they ride as an overlay in action.py (sweep the
threat axis, snap-and-fire on any visible enemy). The ladder only decides *where to
move*. See design §5, and TENTATIVE_LESSONS (games are decided by wipe → defense wins).

Returns an Intent plus the flow-field kind to use ("steal" / "home" / None for A*).
"""

from __future__ import annotations

from ctf.beacon.config import HOLD_ARRIVE_PX, PEDESTAL
from ctf.beacon.types import Belief, Intent


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def decide_objective(belief: Belief) -> tuple[Intent, str | None]:
    """Pick the single movement objective. Returns (intent, flow_kind)."""
    team = belief.team
    assert team is not None
    enemy = "blue" if team == "red" else "red"

    # Rung 1 (everyone): carrying the enemy flag -> run it home. A carried flag is a
    # win one delivery away, and dying returns it instantly. Overrides role.
    if belief.i_carry_enemy_flag:
        return Intent(kind="navigate_to", point=None, reason="carry_home"), "home"

    # Rung 2 (everyone): our flag is stolen and we can SEE the thief -> intercept.
    # Killing the carrier returns the flag instantly; this is the anti-capture play,
    # and it matters most for defenders sitting on the escape lanes.
    if belief.own_flag_stolen and belief.own_flag_thief_pos is not None:
        return Intent(kind="navigate_to", point=belief.own_flag_thief_pos, reason="intercept_thief"), None

    # Rung 3: role split.
    if belief.role == "defender" and belief.hold_point is not None:
        # Hold cover on our turf: the enemy dies attacking us (we respawn close),
        # and our flag stops being undefended. Once at the hold point, stop
        # advancing (A* returns ~self) and let the combat overlay work the lane.
        if belief.self_xy is not None and _dist(belief.self_xy, belief.hold_point) <= HOLD_ARRIVE_PX:
            return Intent(kind="hold", reason="hold_line"), None
        return Intent(kind="navigate_to", point=belief.hold_point, reason="to_hold"), None

    # Attackers (and defenders with no hold point): push the enemy flag.
    return Intent(kind="navigate_to", point=PEDESTAL[enemy], reason="steal"), "steal"


__all__ = ["decide_objective"]
