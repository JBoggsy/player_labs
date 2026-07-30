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
    "spray can": "arc",
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

    The player wire is 1x map pixels since the 0.7.8 renderer restore (the 0.6-0.7.7
    "HD" era carried 3x coordinates; RULES.md's "Observation render scale" section
    describes the spectator/replay stream, not the player stream). RENDER_SCALE (=1)
    is kept at this seam so a future wire-scale change is a one-constant fix.
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


#: The identity badge (0.7.69 nameplates) sits on the soldier body's bottom-right
#: corner — its centre is ~SoldierBodyPx/2 = 17px diagonal from the body centre.
#: A badge within this radius of a player sprite belongs to that player.
_BADGE_RADIUS = 30.0
_IDENTITY_NAMES = ("alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta")
_IDENTITY_INDEX = {n: i for i, n in enumerate(_IDENTITY_NAMES)}


def _identity_badges(world: SpriteWorld, color: Team) -> list[tuple[int, tuple[int, int]]]:
    """Visible identity badges of ``color``: (identity index, badge centre)."""
    out: list[tuple[int, tuple[int, int]]] = []
    prefix = f"identity {color} "
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is None or not sprite.label.startswith(prefix):
            continue
        idx = _IDENTITY_INDEX.get(sprite.label[len(prefix):])
        if idx is not None:
            out.append((idx, _center(world, obj)))
    return out


def _players_of_color(world: SpriteWorld, color: Team) -> tuple[Enemy, ...]:
    """Visible players of ``color``, with nameplate identity where a badge resolves.

    Badges are emitted per visible player (fog-gated with the player, like the hp
    bar), so a greedy nearest-badge association within _BADGE_RADIUS is reliable —
    ambiguity only in a tight scrum, where a wrong same-team identity is harmless
    for cohesion purposes."""
    players: list[tuple[tuple[int, int], str]] = []
    for facing in ("right", "left"):
        for obj in _objects_with_label(world, f"player {color} {facing}"):
            players.append((_center(world, obj), facing))
    badges = _identity_badges(world, color)
    out: list[Enemy] = []
    for pos, facing in players:
        best_idx: int | None = None
        best_d = _BADGE_RADIUS
        for idx, bpos in badges:
            d = math.hypot(bpos[0] - pos[0], bpos[1] - pos[1])
            if d < best_d:
                best_d = d
                best_idx = idx
        out.append(Enemy(pos=pos, facing=facing, identity=best_idx))
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


def _heard_shouts(world: SpriteWorld) -> tuple[tuple[str, str, str, tuple[int, int]], ...]:
    """Shout bubbles in this frame (v18 chat): (team, sender address, text, pos).

    Bubble label format (global.nim addShouts): ``<team> shout <address>: <text>``
    where <address> may itself contain spaces — split on the LAST ': ' instead."""
    out: list[tuple[str, str, str, tuple[int, int]]] = []
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is None:
            continue
        label = sprite.label
        if " shout " not in label:
            continue
        team, rest = label.split(" shout ", 1)
        if team not in ("red", "blue") or ": " not in rest:
            continue
        address, text = rest.rsplit(": ", 1)
        out.append((team, address, text, _center(world, obj)))
    return tuple(out)


def _team_scores(world: SpriteWorld) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """Both teams' (kills, deaths) from the top-center scoreboard, or (None, None).

    The player stream draws ``team score RED <k>/<d>`` / ``team score BLUE <k>/<d>``
    every Playing frame (global.nim addTeamScoreboard) — aggregate, both teams,
    fog-independent. Deaths are the wipe clock: team lives remaining =
    3*8 - deaths while every slot stays connected."""
    red: tuple[int, int] | None = None
    blue: tuple[int, int] | None = None
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is None or not sprite.label.startswith("team score "):
            continue
        # "team score RED 12/9" -> ("RED", "12/9")
        parts = sprite.label[len("team score "):].split(" ")
        if len(parts) != 2 or "/" not in parts[1]:
            continue
        try:
            kills, deaths = (int(v) for v in parts[1].split("/", 1))
        except ValueError:
            continue
        if parts[0] == "RED":
            red = (kills, deaths)
        elif parts[0] == "BLUE":
            blue = (kills, deaths)
    return red, blue


def _nearest_marker_assignments(
    actors: list[tuple[int, int]],
    markers: list[tuple[int, int]],
) -> dict[int, int]:
    """Globally assign nearby overhead markers to actors, one-to-one.

    A tight scrum can put more than one body inside ``_OVERHEAD_RADIUS``. Sorting
    all feasible actor/marker pairs by distance prevents one marker from being
    claimed twice or our own marker from being independently selected as an
    enemy's.
    """
    pairs: list[tuple[float, int, int]] = []
    for actor_i, actor_pos in enumerate(actors):
        for marker_i, marker_pos in enumerate(markers):
            d = _dist(actor_pos, marker_pos)
            if d <= _OVERHEAD_RADIUS:
                pairs.append((d, actor_i, marker_i))
    assigned_actors: set[int] = set()
    assigned_markers: set[int] = set()
    out: dict[int, int] = {}
    for _distance, actor_i, marker_i in sorted(pairs):
        if actor_i in assigned_actors or marker_i in assigned_markers:
            continue
        assigned_actors.add(actor_i)
        assigned_markers.add(marker_i)
        out[actor_i] = marker_i
    return out


def _attach_overhead_state(
    world: SpriteWorld,
    self_xy: tuple[int, int],
    enemies: tuple[Enemy, ...],
    teammates: tuple[Enemy, ...],
) -> tuple[int | None, bool, bool, bool, tuple[Enemy, ...], tuple[Enemy, ...]]:
    """Attach ordinal HP bars and carried markers to every visible player.

    ``labels.nim`` defines ``hp <lit>/<total>`` as lit BAR SEGMENTS over
    ``hp + shieldHp``. The numerator is retained as an ordinal 1..3 value; it is
    never interpreted as hit points. Markers are scanned once. Self ownership is
    resolved first with the exact legacy proximity rules so flags-off item behavior
    is unchanged; remaining markers are then assigned one-to-one across enemies and
    teammates.
    """
    hp_values: list[int] = []
    hp_positions: list[tuple[int, int]] = []
    carried_positions: dict[str, list[tuple[int, int]]] = {
        "grenade carried": [],
        "shield carried": [],
        "plasma arc carried": [],
        "spray can carried": [],
    }
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is None:
            continue
        label = sprite.label
        if label.startswith("hp "):
            try:
                lit = int(label.split(" ", 1)[1].split("/", 1)[0])
            except (IndexError, ValueError):
                continue
            hp_values.append(lit)
            hp_positions.append(_center(world, obj))
        elif label in carried_positions:
            carried_positions[label].append(_center(world, obj))

    self_hp: int | None = None
    self_hp_marker: int | None = None
    self_hp_distance = _OVERHEAD_RADIUS
    for marker_i, marker_pos in enumerate(hp_positions):
        distance = _dist(self_xy, marker_pos)
        if distance < self_hp_distance:
            self_hp_distance = distance
            self_hp = hp_values[marker_i]
            self_hp_marker = marker_i

    actors = [*(enemy.pos for enemy in enemies), *(mate.pos for mate in teammates)]
    remaining_hp = [
        (marker_i, marker_pos)
        for marker_i, marker_pos in enumerate(hp_positions)
        if marker_i != self_hp_marker
    ]
    hp_by_actor = {
        actor_i: hp_values[remaining_hp[marker_i][0]]
        for actor_i, marker_i in _nearest_marker_assignments(
            actors,
            [pos for _original_i, pos in remaining_hp],
        ).items()
    }

    self_carried: dict[str, bool] = {}
    carried_by_actor: dict[str, set[int]] = {}
    for label, positions in carried_positions.items():
        self_markers = {
            marker_i
            for marker_i, marker_pos in enumerate(positions)
            if _dist(self_xy, marker_pos) <= _OVERHEAD_RADIUS
        }
        self_carried[label] = bool(self_markers)
        remaining = [
            marker_pos
            for marker_i, marker_pos in enumerate(positions)
            if marker_i not in self_markers
        ]
        carried_by_actor[label] = set(
            _nearest_marker_assignments(actors, remaining)
        )

    enemy_start = 0
    teammate_start = len(enemies)
    attached_enemies = tuple(
        Enemy(
            pos=enemy.pos,
            facing=enemy.facing,
            identity=enemy.identity,
            hp_segments=hp_by_actor.get(enemy_start + i),
            shielded=enemy_start + i in carried_by_actor["shield carried"],
        )
        for i, enemy in enumerate(enemies)
    )
    attached_teammates = tuple(
        Enemy(
            pos=mate.pos,
            facing=mate.facing,
            identity=mate.identity,
            hp_segments=hp_by_actor.get(teammate_start + i),
            shielded=teammate_start + i in carried_by_actor["shield carried"],
        )
        for i, mate in enumerate(teammates)
    )
    return (
        self_hp,
        self_carried["grenade carried"],
        self_carried["shield carried"],
        (
            self_carried["plasma arc carried"]
            or self_carried["spray can carried"]
        ),
        attached_enemies,
        attached_teammates,
    )


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
    heard_shouts = _heard_shouts(world)
    if self_xy is not None:
        (
            hp_pips,
            have_grenade,
            have_shield,
            have_arc,
            enemies,
            teammates,
        ) = _attach_overhead_state(world, self_xy, enemies, teammates)
        # Current CTF exposes an explicit own-weapon HUD label. It is the
        # authoritative seam; the overhead carrier marker is retained for old
        # replays and for attaching visible state to other actors.
        have_arc = have_arc or bool(_objects_with_label(world, "weapon spray"))
    else:
        hp_pips, have_grenade, have_shield, have_arc = None, False, False, False
    red_score, blue_score = _team_scores(world)
    own_team_score = red_score if team == "red" else blue_score
    enemy_team_score = blue_score if team == "red" else red_score

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
        heard_shouts=heard_shouts,
        hp_pips=hp_pips,
        i_have_grenade=have_grenade,
        i_have_shield=have_shield,
        i_have_arc=have_arc,
        own_team_score=own_team_score,
        enemy_team_score=enemy_team_score,
    )


__all__ = ["perceive"]
