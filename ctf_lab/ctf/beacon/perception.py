"""Sprite-label perception: raw SpriteWorld -> CtfState.

All perception is label lookups over the retained scene, exactly as the Nim baseline
does it (baseline.nim findSelf/observedAim/actorsFor + the flag bookkeeping). No pixel
decode is needed at run time — the nav grid is baked offline (see mapdata.py).

Team is fixed for the whole episode and passed in (derived from the connection slot
in main.py: even slot = red, odd = blue). Our team's sprites are labeled with our
team colour ("red"/"blue"); the enemy is the opposite colour.
"""

from __future__ import annotations

import math

from ctf.beacon.config import AIM_BRADS_TURN, PEDESTAL, RENDER_SCALE
from ctf.beacon.types import CtfState, Enemy, Team
from players.player_sdk import SpriteObject, SpriteWorld

#: A visible aim-dot farther than this (px) from us is a teammate's, not ours.
_AIM_DOT_RADIUS = 40.0
#: Enemy heart within this distance (px) of us => we're carrying it.
#: A carried heart rides ~10px ABOVE its carrier (global.nim CarriedFlagLift=10), so
#: the heart's observed centre sits ~10px from our self-sprite centre even when WE
#: hold it. The old 6px threshold was below that, so carry was NEVER detected and the
#: carrier sat on the pedestal in "steal" mode instead of running home. 24px clears
#: the lift with margin while staying well under the distance to a teammate carrier.
_CARRY_DIST = 24.0
#: Own heart within this distance (px) of its pedestal => safely home.
_HOME_SAFE_DIST = 8.0


def _center(world: SpriteWorld, obj: SpriteObject) -> tuple[int, int]:
    """Map-space centre of an object (camera sits at origin in CTF).

    Since game 0.6.0 the zoomable map layer is wire-scaled: object coordinates and
    sprite sizes arrive at RENDER_SCALE (3x) map resolution, with every entity sprite
    centered on its scaled map point — so the wire centre divided by the scale is the
    exact map-pixel centre (RULES.md, "Observation render scale").
    """
    sprite = world.sprite_for(obj)
    w = sprite.width if sprite else 0
    h = sprite.height if sprite else 0
    return (round((obj.x + w / 2) / RENDER_SCALE), round((obj.y + h / 2) / RENDER_SCALE))


def _objects_with_label(world: SpriteWorld, label: str) -> list[SpriteObject]:
    out = []
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is not None and sprite.label == label:
            out.append(obj)
    return out


def _brads_of(dx: float, dy: float) -> int:
    """Aim brads for a direction vector. 0 = east, CCW positive, y points down
    (so screen-up is +brads) — matches sim.nim aimVector (angle uses -sin y)."""
    ang = math.atan2(-dy, dx)  # radians, CCW positive
    brads = round(ang / (2 * math.pi) * AIM_BRADS_TURN)
    return brads % AIM_BRADS_TURN


def _find_self(world: SpriteWorld, color: Team):
    for facing in ("right", "left"):
        objs = _objects_with_label(world, f"self {color} {facing}")
        if objs:
            return _center(world, objs[0]), facing
    return None, None


def _observed_aim(world: SpriteWorld, color: Team, self_xy: tuple[int, int]) -> int | None:
    """Our aim read back from our own aim-dot sprites: the farthest same-colour dot
    within the indicator radius points along our aim. None if none is close enough."""
    best_d = 0.0
    best_aim: int | None = None
    sx, sy = self_xy
    for obj in _objects_with_label(world, f"aim dot {color}"):
        px, py = _center(world, obj)
        d = math.hypot(px - sx, py - sy)
        if d <= _AIM_DOT_RADIUS and d > best_d:
            best_d = d
            best_aim = _brads_of(px - sx, py - sy)
    return best_aim


def _players_of_color(world: SpriteWorld, color: Team) -> tuple[Enemy, ...]:
    """Visible players of ``color`` (the Enemy dataclass is just pos+facing)."""
    out: list[Enemy] = []
    for facing in ("right", "left"):
        for obj in _objects_with_label(world, f"player {color} {facing}"):
            out.append(Enemy(pos=_center(world, obj), facing=facing))
    return tuple(out)


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def perceive(obs, team: Team) -> CtfState:
    """Read one frame's CtfState for our fixed ``team``."""
    world = obs.world
    enemy_color: Team = "blue" if team == "red" else "red"

    self_xy, self_facing = _find_self(world, team)
    ready = self_xy is not None
    observed_aim = _observed_aim(world, team, self_xy) if self_xy is not None else None
    fire_ready = len(_objects_with_label(world, "fire icon")) > 0
    enemies = _players_of_color(world, enemy_color)
    # Same-colour "player" sprites are teammates (our own avatar uses "self", so it
    # never matches here). Used only for the friendly-fire gate — friendly fire is ON.
    teammates = _players_of_color(world, team)

    # Heart bookkeeping (the capture objects; labeled "<color> heart" since 0.7.0).
    # A pedestal heart is never fogged — even from a dead viewer — and a carried
    # heart is exactly as visible as its carrier (sim.nim flagVisibleTo). So for the
    # ENEMY heart: on its pedestal = stealable, on us = carrying, elsewhere-visible =
    # a teammate carries it. For OUR heart: on its pedestal = safe, absent = a fogged
    # thief has it, visible-off-pedestal = a live thief fix.
    steal_target = PEDESTAL[enemy_color]
    own_home = PEDESTAL[team]
    enemy_flags = _objects_with_label(world, f"{enemy_color} heart")
    own_flags = _objects_with_label(world, f"{team} heart")

    i_carry = False
    enemy_flag_on_pedestal = False
    enemy_flag_pos: tuple[int, int] | None = None
    if enemy_flags:
        enemy_flag_pos = _center(world, enemy_flags[0])
        # On its pedestal => stealable (never carried). OFF the pedestal AND near us =>
        # WE carry it (it rides ~10px above us via CarriedFlagLift). The pedestal test
        # must come first: standing on the pedestal with the flag still on it is within
        # _CARRY_DIST too, but is NOT carrying — the off-pedestal guard disambiguates.
        if _dist(enemy_flag_pos, steal_target) <= 4.0:
            enemy_flag_on_pedestal = True
        elif self_xy is not None and _dist(enemy_flag_pos, self_xy) <= _CARRY_DIST:
            i_carry = True

    own_flag_stolen = len(own_flags) == 0
    own_flag_thief_pos: tuple[int, int] | None = None
    if own_flags:
        fp = _center(world, own_flags[0])
        if _dist(fp, own_home) > _HOME_SAFE_DIST:
            own_flag_stolen = True
            own_flag_thief_pos = fp

    return CtfState(
        ready=ready,
        self_xy=self_xy,
        self_facing=self_facing,
        observed_aim=observed_aim,
        fire_ready=fire_ready,
        enemies=enemies,
        teammates=teammates,
        i_carry_enemy_flag=i_carry,
        enemy_flag_on_pedestal=enemy_flag_on_pedestal,
        enemy_flag_pos=enemy_flag_pos,
        own_flag_stolen=own_flag_stolen,
        own_flag_thief_pos=own_flag_thief_pos,
    )


__all__ = ["perceive"]
