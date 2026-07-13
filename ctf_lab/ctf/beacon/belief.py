"""Belief update — fold a per-frame CtfState into the long-lived Belief.

The only genuinely stateful part is the aim estimate: the aim-dot sprite gives an
absolute read (~2 brad resolution) but isn't always visible, so between reads we
dead-reckon by the rotation we commanded last frame. Everything else in CTF (flags,
enemies) is effectively per-frame because pedestals never fog and enemies vanish when
out of the cone/bubble.
"""

from __future__ import annotations

from ctf.beacon.config import AIM_BRADS_TURN, AIM_TURN_RATE, SPAWN_AIM
from ctf.beacon.types import ActionState, Belief, CtfState


def update_belief(belief: Belief, percept: CtfState, action_state: ActionState) -> None:
    """Mutate ``belief`` in place from this frame's percept."""
    was_alive = belief.alive
    belief.alive = percept.self_xy is not None
    if percept.self_xy is not None:
        belief.self_xy = percept.self_xy

    # Aim estimate: prefer the observed aim-dot read; else dead-reckon by the rotation
    # we commanded last frame. On (re)spawn, reseed to the spawn aim.
    if belief.team is not None and (not was_alive and belief.alive):
        belief.aim_brads = SPAWN_AIM[belief.team]
        belief.sweep_offset = 0
        belief.sweep_dir = 1
    if percept.observed_aim is not None:
        belief.aim_brads = percept.observed_aim
    else:
        belief.aim_brads = (belief.aim_brads + action_state.last_rot * AIM_TURN_RATE) % AIM_BRADS_TURN

    belief.fire_ready = percept.fire_ready
    belief.enemies = percept.enemies
    belief.teammates = percept.teammates
    belief.i_carry_enemy_flag = percept.i_carry_enemy_flag
    belief.enemy_flag_on_pedestal = percept.enemy_flag_on_pedestal
    belief.enemy_flag_pos = percept.enemy_flag_pos
    belief.own_flag_stolen = percept.own_flag_stolen
    belief.own_flag_thief_pos = percept.own_flag_thief_pos


__all__ = ["update_belief"]
