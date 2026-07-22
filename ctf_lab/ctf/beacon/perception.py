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

from ctf.beacon.config import AIM_BRADS_TURN, RENDER_SCALE
from ctf.beacon.types import CtfState, Enemy, Team
from players.player_sdk import SpriteObject, SpriteWorld

#: Carried enemy flag within this distance (px) of us => we're carrying it. Since
#: 0.7.8 the carried banner is CENTERED on its carrier (global.nim: flag.x = the
#: carrier's centre), so our own carry reads at ~0px; 24 leaves margin while staying
#: well under the distance to a teammate carrier.
_CARRY_DIST = 24.0
#: The white-outlined self soldier sprite pool: 5100 + rot, one per 16-brad aim step
#: (global.nim SpritePlayerSelfSpriteBase / sim.nim SoldierRotations). The aim-dot
#: indicator was retired in the renderer restore; the self sprite's rotation id is
#: now the only absolute aim readback (coarse: ±8 brads).
_SELF_SPRITE_BASE = 5100
_SOLDIER_ROTATIONS = 16
#: Only resync the dead-reckoned aim estimate when it disagrees with the quantized
#: sprite read by more than the quantization step (else the coarse read adds noise).
_AIM_RESYNC_SLACK = 12
#: Overhead UI (hp bar, carried-item markers) sits stacked just above the 34px
#: soldier body (global.nim overheadAnchorY - OverheadYOffset), ~20-30px from the
#: body centre. A marker within this radius of a player belongs to that player.
_OVERHEAD_RADIUS = 34.0
#: Pickup sprite labels on the map layer, exact-match (the carried/air/sound
#: variants use longer labels, so exact match selects only ground pickups).
_ITEM_LABELS = {
    "grenade": "grenade",
    "med kit": "medkit",
    "shield": "shield",
    "plasma arc": "arc",
}
#: Sound-ring labels (v16 hearing): audible map-wide through walls and fog,
#: jittered ±20px per event, team-anonymous. "shot impact" = a bullet LANDED
#: near here (~0.5s ring); "grenade sound" = an unseen grenade blast.
_SOUND_LABELS = {
    "shot impact": "shot",
    "grenade sound": "grenade",
}


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


def _find_self(world: SpriteWorld, color: Team):
    """Our self marker: (centre, facing, observed_aim_brads|None).

    The aim-dot indicator was retired in the 0.7.8 renderer restore; the aim
    readback is now the self sprite's rotation id (5100 + rot, 16 steps of 16
    brads) — coarse but absolute, used only to correct dead-reckoning drift."""
    for facing in ("right", "left"):
        objs = _objects_with_label(world, f"self {color} {facing}")
        if objs:
            obj = objs[0]
            rot = obj.sprite_id - _SELF_SPRITE_BASE
            aim = (
                rot * (AIM_BRADS_TURN // _SOLDIER_ROTATIONS)
                if 0 <= rot < _SOLDIER_ROTATIONS
                else None
            )
            return _center(world, obj), facing, aim
    return None, None, None


def _players_of_color(world: SpriteWorld, color: Team) -> tuple[Enemy, ...]:
    """Visible players of ``color`` (the Enemy dataclass is just pos+facing)."""
    out: list[Enemy] = []
    for facing in ("right", "left"):
        for obj in _objects_with_label(world, f"player {color} {facing}"):
            out.append(Enemy(pos=_center(world, obj), facing=facing))
    return tuple(out)


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _visible_items(world: SpriteWorld) -> tuple[tuple[str, tuple[int, int]], ...]:
    """Ground pickups in view this frame, as (kind, map-px centre) pairs."""
    out: list[tuple[str, tuple[int, int]]] = []
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is not None and sprite.label in _ITEM_LABELS:
            out.append((_ITEM_LABELS[sprite.label], _center(world, obj)))
    return tuple(out)


def _heard_impacts(world: SpriteWorld) -> tuple[tuple[str, tuple[int, int]], ...]:
    """Sound rings in this frame, as (kind, map-px centre) pairs (v16 hearing)."""
    out: list[tuple[str, tuple[int, int]]] = []
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is not None and sprite.label in _SOUND_LABELS:
            out.append((_SOUND_LABELS[sprite.label], _center(world, obj)))
    return tuple(out)


def _overhead_state(world: SpriteWorld, self_xy: tuple[int, int]) -> tuple[int | None, bool, bool, bool]:
    """Our own hp pips + carried-item markers, read from the overhead UI stack.

    Every living player we can see carries the same overhead sprites (a wounded
    enemy's hp is readable intel), so ownership is by proximity: the marker whose
    centre is nearest us — within the overhead stack radius — is ours.
    """
    hp: int | None = None
    hp_d = _OVERHEAD_RADIUS
    have = {"grenade carried": False, "shield carried": False, "plasma arc carried": False}
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is None:
            continue
        label = sprite.label
        if label.startswith("hp "):
            d = _dist(_center(world, obj), self_xy)
            if d < hp_d:
                hp_d = d
                try:
                    hp = int(label.split(" ")[1].split("/")[0])
                except (IndexError, ValueError):
                    hp = None
        elif label in have:
            if _dist(_center(world, obj), self_xy) <= _OVERHEAD_RADIUS:
                have[label] = True
    return hp, have["grenade carried"], have["shield carried"], have["plasma arc carried"]


def perceive(obs, team: Team) -> CtfState:
    """Read one frame's CtfState for our fixed ``team``."""
    world = obs.world
    enemy_color: Team = "blue" if team == "red" else "red"

    self_xy, self_facing, observed_aim = _find_self(world, team)
    ready = self_xy is not None
    fire_ready = len(_objects_with_label(world, "fire icon")) > 0
    enemies = _players_of_color(world, enemy_color)
    # Same-colour "player" sprites are teammates (our own avatar uses "self", so it
    # never matches here). Used only for the friendly-fire gate — friendly fire is ON.
    teammates = _players_of_color(world, team)

    # Flag bookkeeping. Since the 0.7.8 renderer restore the flag ships as two
    # distinct sprites (global.nim flagLabel): "<color> flag planted" resting on its
    # pedestal, or "<color> flag" CENTERED on its carrier while carried. A pedestal
    # flag is never fogged — even from a dead viewer — and a carried flag is exactly
    # as visible as its carrier. So for the ENEMY flag: planted = stealable; a
    # carried sprite near us = WE carry it; carried elsewhere = a teammate has it.
    # For OUR flag: planted = safe; carried-visible = a live thief fix; NEITHER
    # sprite in frame = stolen by a fogged thief.
    enemy_planted = _objects_with_label(world, f"{enemy_color} flag planted")
    enemy_carried = _objects_with_label(world, f"{enemy_color} flag")
    own_planted = _objects_with_label(world, f"{team} flag planted")
    own_carried = _objects_with_label(world, f"{team} flag")

    i_carry = False
    enemy_flag_on_pedestal = len(enemy_planted) > 0
    enemy_flag_pos: tuple[int, int] | None = None
    if enemy_planted:
        enemy_flag_pos = _center(world, enemy_planted[0])
    elif enemy_carried:
        enemy_flag_pos = _center(world, enemy_carried[0])
        if self_xy is not None and _dist(enemy_flag_pos, self_xy) <= _CARRY_DIST:
            i_carry = True

    own_flag_stolen = len(own_planted) == 0
    own_flag_thief_pos: tuple[int, int] | None = None
    if own_flag_stolen and own_carried:
        own_flag_thief_pos = _center(world, own_carried[0])

    visible_items = _visible_items(world)
    heard_impacts = _heard_impacts(world)
    if self_xy is not None:
        hp_pips, have_grenade, have_shield, have_arc = _overhead_state(world, self_xy)
    else:
        hp_pips, have_grenade, have_shield, have_arc = None, False, False, False

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
        visible_items=visible_items,
        heard_impacts=heard_impacts,
        hp_pips=hp_pips,
        i_have_grenade=have_grenade,
        i_have_shield=have_shield,
        i_have_arc=have_arc,
    )


__all__ = ["perceive"]
