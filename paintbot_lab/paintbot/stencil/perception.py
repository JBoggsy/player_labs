"""Sprite-label perception: raw SpriteWorld -> PaintState.

Mostly label lookups over the retained scene, as the Nim baseline does it — plus
the three things Paintbot's procgen maps force us to READ off the wire that
beacon compiled in:

  * the ``game teams <count> map <width>x<height>`` marker (episode parameters);
  * the per-team ``endzone <color> <shape> <x0>,<y0> <x1>,<y1>`` markers;
  * the ``walkability map`` sprite's PIXELS (snappy raw-block compressed RGBA;
    alpha>0 = walkable) — decoded once per sprite definition and cached by id.

Team color is initially guessed from the connection slot (slot mod teams) and
locked from the first ``self <color>`` sighting (belief handles the lock).
"""

from __future__ import annotations

import math

import numpy as np

try:
    import cramjam
except ImportError:  # pragma: no cover - cramjam ships in the image
    cramjam = None

from paintbot.stencil.config import AIM_BRADS_TURN, RENDER_SCALE, TEAM_COLORS
from paintbot.stencil.types import Enemy, HeartState, PaintState, Team
from players.player_sdk import SpriteObject, SpriteWorld

#: Carried heart within this distance (px) of us => we're carrying it (the
#: carried banner is CENTERED on its carrier).
_CARRY_DIST = 24.0
#: The white-outlined self soldier sprite pool: 5100 + skin*16 + rot.
_SELF_SPRITE_BASE = 5100
_SOLDIER_ROTATIONS = 16
#: Overhead UI (hp bar, carried-item markers) association radius.
_OVERHEAD_RADIUS = 34.0
#: Pickup sprite labels on the map layer, exact-match.
_ITEM_LABELS = {
    "grenade": "grenade",
    "med kit": "medkit",
    "shield": "shield",
    "plasma arc": "arc",
    "spray can": "arc",
}
#: Sound-ring labels (hearing): audible map-wide, jittered ±20px, team-anonymous.
_SOUND_LABELS = {
    "shot impact": "shot",
    "grenade sound": "grenade",
}
#: Endzone marker shape vocabulary (labels.nim LabelEndzoneShapes). The
#: spectator stream also emits "endzone <color> power <n>" glow overlays;
#: matching the shape token filters those out.
_ENDZONE_SHAPES = ("column", "square", "disc", "corner", "arm")

#: Identity badges (nameplates).
_BADGE_RADIUS = 30.0
_IDENTITY_NAMES = ("alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta")
_IDENTITY_INDEX = {n: i for i, n in enumerate(_IDENTITY_NAMES)}

#: Decoded walkability masks keyed by (sprite_id, width, height) — a pure decode
#: cache, safe across episodes because a different map defines a different sprite.
_walkability_cache: dict[tuple[int, int, int], np.ndarray] = {}


def _center(world: SpriteWorld, obj: SpriteObject) -> tuple[int, int]:
    """Map-space centre of an object (player wire is 1x map pixels)."""
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


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


# --- Episode parameters (procgen: read, never assume) --------------------------------


def parse_game_params(world: SpriteWorld) -> tuple[int, tuple[int, int]] | None:
    """The ``game teams <count> map <width>x<height>`` marker, if present."""
    for sprite in world.sprites.values():
        label = sprite.label
        if not label.startswith("game teams "):
            continue
        parts = label[len("game teams "):].split(" ")
        # ["<count>", "map", "<width>x<height>"]
        if len(parts) != 3 or parts[1] != "map" or "x" not in parts[2]:
            continue
        try:
            teams = max(2, min(int(parts[0]), 4))
            w, h = (int(v) for v in parts[2].split("x", 1))
        except ValueError:
            continue
        return teams, (w, h)
    return None


def parse_endzones(world: SpriteWorld) -> dict[Team, tuple[str, tuple[int, int, int, int]]]:
    """Per-team endzone markers: color -> (shape, inclusive corner box)."""
    out: dict[Team, tuple[str, tuple[int, int, int, int]]] = {}
    for sprite in world.sprites.values():
        label = sprite.label
        if not label.startswith("endzone "):
            continue
        parts = label[len("endzone "):].split(" ")
        # [<color>, <shape>, "<x0>,<y0>", "<x1>,<y1>"]
        if len(parts) != 4 or parts[0] not in TEAM_COLORS:
            continue
        if parts[1] not in _ENDZONE_SHAPES:
            continue  # e.g. the spectator "power" glow overlay
        try:
            x0, y0 = (int(v) for v in parts[2].split(",", 1))
            x1, y1 = (int(v) for v in parts[3].split(",", 1))
        except ValueError:
            continue
        out[parts[0]] = (parts[1], (x0, y0, x1, y1))
    return out


def decode_walkability(world: SpriteWorld) -> np.ndarray | None:
    """The ``walkability map`` sprite decoded to a bool [H, W] mask, or None.

    RGBA, alpha>0 = walkable, always unscaled 1x map pixels. The compressed
    payload is snappy RAW block format (no stream framing) — cramjam's
    ``decompress_raw`` matches the server's supersnappy output.
    """
    for sprite in world.sprites.values():
        if sprite.label != "walkability map":
            continue
        key = (sprite.sprite_id, sprite.width, sprite.height)
        cached = _walkability_cache.get(key)
        if cached is not None:
            return cached
        if cramjam is None or sprite.width <= 0 or sprite.height <= 0:
            return None
        try:
            raw = bytes(cramjam.snappy.decompress_raw(sprite.data))
        except Exception:
            return None
        if len(raw) != sprite.width * sprite.height * 4:
            return None
        alpha = np.frombuffer(raw, dtype=np.uint8).reshape(
            sprite.height, sprite.width, 4
        )[:, :, 3]
        mask = alpha > 0
        _walkability_cache.clear()  # keep exactly one map resident
        _walkability_cache[key] = mask
        return mask
    return None


# --- Players -------------------------------------------------------------------------


def _find_self(world: SpriteWorld, colors: tuple[Team, ...]):
    """Our self marker across the active colors: (centre, color, facing, aim).

    The self sprite's rotation id (5100 + skin*16 + rot, 16 steps of 16 brads)
    is the only absolute aim readback — coarse but drift-free."""
    for color in colors:
        for facing in ("right", "left"):
            objs = _objects_with_label(world, f"self {color} {facing}")
            if objs:
                obj = objs[0]
                offset = obj.sprite_id - _SELF_SPRITE_BASE
                rot = offset % _SOLDIER_ROTATIONS
                aim = (
                    rot * (AIM_BRADS_TURN // _SOLDIER_ROTATIONS)
                    if offset >= 0
                    else None
                )
                return _center(world, obj), color, facing, aim
    return None, None, None, None


def _identity_badges(world: SpriteWorld, color: Team) -> list[tuple[int, tuple[int, int]]]:
    out: list[tuple[int, tuple[int, int]]] = []
    prefix = f"identity {color} "
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is None or not sprite.label.startswith(prefix):
            continue
        # The badge tail is "<name>[ shield][ nade] <weapon>" — first token is the name.
        name = sprite.label[len(prefix):].split(" ", 1)[0]
        idx = _IDENTITY_INDEX.get(name)
        if idx is not None:
            out.append((idx, _center(world, obj)))
    return out


def _players_of_color(world: SpriteWorld, color: Team) -> tuple[Enemy, ...]:
    """Visible players of ``color``, with nameplate identity where a badge resolves."""
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
        out.append(Enemy(pos=pos, facing=facing, color=color, identity=best_idx))
    return tuple(out)


# --- Items / sounds / shouts / scores ------------------------------------------------


def _visible_items(world: SpriteWorld) -> tuple[tuple[str, tuple[int, int]], ...]:
    out: list[tuple[str, tuple[int, int]]] = []
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is not None and sprite.label in _ITEM_LABELS:
            out.append((_ITEM_LABELS[sprite.label], _center(world, obj)))
    return tuple(out)


def _heard_impacts(world: SpriteWorld) -> tuple[tuple[str, tuple[int, int]], ...]:
    out: list[tuple[str, tuple[int, int]]] = []
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is not None and sprite.label in _SOUND_LABELS:
            out.append((_SOUND_LABELS[sprite.label], _center(world, obj)))
    return tuple(out)


def _heard_shouts(
    world: SpriteWorld,
) -> tuple[tuple[str, str, str, tuple[int, int]], ...]:
    """Shout bubbles: (team color, sender name, text, pos). The sender is the
    per-team slot letter (anonymized upstream), split on the LAST ': '."""
    out: list[tuple[str, str, str, tuple[int, int]]] = []
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is None:
            continue
        label = sprite.label
        if " shout " not in label:
            continue
        team, rest = label.split(" shout ", 1)
        if team not in TEAM_COLORS or ": " not in rest:
            continue
        address, text = rest.rsplit(": ", 1)
        out.append((team, address, text, _center(world, obj)))
    return tuple(out)


def _team_scores(world: SpriteWorld) -> dict[Team, tuple[int, int]]:
    """All teams' (kills, deaths) from the top-center scoreboard chips.

    Labels read ``team score RED <k>/<d>`` per active team, fog-independent."""
    out: dict[Team, tuple[int, int]] = {}
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is None or not sprite.label.startswith("team score "):
            continue
        parts = sprite.label[len("team score "):].split(" ")
        if len(parts) != 2 or "/" not in parts[1]:
            continue
        color = parts[0].lower()
        if color not in TEAM_COLORS:
            continue
        try:
            kills, deaths = (int(v) for v in parts[1].split("/", 1))
        except ValueError:
            continue
        out[color] = (kills, deaths)
    return out


# --- Overhead markers ----------------------------------------------------------------


def _nearest_marker_assignments(
    actors: list[tuple[int, int]],
    markers: list[tuple[int, int]],
) -> dict[int, int]:
    """Globally assign nearby overhead markers to actors, one-to-one."""
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
):
    """Attach ordinal HP bars and carried markers to every visible player."""
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
        carried_by_actor[label] = set(_nearest_marker_assignments(actors, remaining))

    enemy_start = 0
    teammate_start = len(enemies)
    attached_enemies = tuple(
        Enemy(
            pos=enemy.pos,
            facing=enemy.facing,
            color=enemy.color,
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
            color=mate.color,
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
        (self_carried["plasma arc carried"] or self_carried["spray can carried"]),
        attached_enemies,
        attached_teammates,
    )


# --- The percept ---------------------------------------------------------------------


def perceive(obs, team: Team, colors: tuple[Team, ...]) -> PaintState:
    """Read one frame's PaintState for our ``team`` among active ``colors``."""
    world = obs.world
    enemy_colors = tuple(c for c in colors if c != team)

    self_xy, self_color, self_facing, observed_aim = _find_self(world, colors)
    if self_color is not None and self_color != team:
        # Slot-dealt guess was wrong; report players relative to the REAL color.
        team = self_color
        enemy_colors = tuple(c for c in colors if c != team)
    ready = self_xy is not None
    fire_ready = len(_objects_with_label(world, "fire icon")) > 0
    enemies: tuple[Enemy, ...] = ()
    for color in enemy_colors:
        enemies = enemies + _players_of_color(world, color)
    teammates = _players_of_color(world, team)

    # Heart bookkeeping per color. A planted heart rests on its pedestal (never
    # fogged); a carried heart is exactly as visible as its carrier. For each
    # color: planted -> stealable/safe; carried-visible -> a live fix; NEITHER
    # sprite -> stolen by a fogged carrier (or retired after elimination —
    # belief.py resolves which via the team scoreboard).
    hearts: dict[Team, HeartState] = {}
    for color in colors:
        planted = _objects_with_label(world, f"{color} flag planted")
        carried = _objects_with_label(world, f"{color} flag")
        pos = _center(world, planted[0]) if planted else None
        carried_pos = _center(world, carried[0]) if carried else None
        hearts[color] = HeartState(
            planted=bool(planted),
            pos=pos if planted else carried_pos,
            carried_pos=carried_pos,
        )

    i_carry: Team | None = None
    if self_xy is not None:
        for color in enemy_colors:
            state = hearts[color]
            if state.carried_pos is not None and _dist(state.carried_pos, self_xy) <= _CARRY_DIST:
                i_carry = color
                break

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
        have_arc = have_arc or bool(_objects_with_label(world, "weapon spray"))
    else:
        hp_pips, have_grenade, have_shield, have_arc = None, False, False, False

    params = parse_game_params(world)
    return PaintState(
        ready=ready,
        self_xy=self_xy,
        self_color=self_color,
        self_facing=self_facing,
        observed_aim=observed_aim,
        fire_ready=fire_ready,
        enemies=enemies,
        teammates=teammates,
        hearts=hearts,
        i_carry_heart_of=i_carry,
        game_teams=params[0] if params else None,
        map_size=params[1] if params else None,
        endzones=parse_endzones(world),
        walkability=decode_walkability(world),
        visible_items=visible_items,
        heard_impacts=heard_impacts,
        heard_shouts=heard_shouts,
        hp_pips=hp_pips,
        i_have_grenade=have_grenade,
        i_have_shield=have_shield,
        i_have_arc=have_arc,
        team_scores=_team_scores(world),
    )


__all__ = [
    "decode_walkability",
    "parse_endzones",
    "parse_game_params",
    "perceive",
]
