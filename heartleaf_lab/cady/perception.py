"""Label-only Heartleaf perception from the SDK ``SpriteWorld``."""

from __future__ import annotations

import re

from players.player_sdk import SpriteObject, SpriteWorld

from cady.tools.capture_scene import read_clock_string
from cady.types import Garden, Gnome, HeartleafState, Observation

MAP_OBJECT_ID = 1
GNOME_OBJECT_BASE = 1000
GNOME_OBJECT_LIMIT = 2000
GARDEN_OBJECT_BASE = 4000
GARDEN_OBJECT_LIMIT = 5000
INVENTORY_OBJECT_BASE = 5000
INVENTORY_OBJECT_LIMIT = 6000

# CALIBRATION: exact self offset from camera center is unknown until the capture
# probe sees a live stream. v1 navigation uses relative vectors and records
# home_anchor from self_xy with the same offset, so this constant cancels out for
# target-vs-self and self-vs-home calculations.
SELF_OFFSET = (0, 0)  # TODO(calibrate)

_CLOCK_RE = re.compile(r"^(\d{1,2}):(\d{2})(am|pm)$", re.IGNORECASE)


def parse_clock_minutes(text: str) -> int | None:
    """Parse ``H:MMam``/``H:MMpm`` into minutes since Heartleaf's 8:00 AM start."""

    match = _CLOCK_RE.fullmatch(text.strip())
    if match is None:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    suffix = match.group(3).lower()
    if not 1 <= hour <= 12 or not 0 <= minute <= 59:
        return None

    if suffix == "am":
        hour_24 = 0 if hour == 12 else hour
    else:
        hour_24 = 12 if hour == 12 else hour + 12

    return hour_24 * 60 + minute - 8 * 60


def perceive(obs: Observation) -> HeartleafState:
    """Resolve one raw sprite frame into Cady's Heartleaf percept."""

    world = obs.world
    camera = _camera(world)
    if camera is None:
        return HeartleafState(
            ready=False,
            self_xy=None,
            time_minutes=None,
            gardens=(),
            gnomes=(),
            own_house_index=None,
            houses=(),
            inventory_count=0,
        )

    clock = read_clock_string(world)
    gardens: list[Garden] = []
    gnomes: list[Gnome] = []
    inventory_count = 0

    for obj in world.objects.values():
        label = _sprite_label(world, obj)
        if label is None:
            continue

        if GNOME_OBJECT_BASE <= obj.object_id < GNOME_OBJECT_LIMIT:
            parsed = _parse_gnome_label(label)
            if parsed is None:
                continue
            index, facing = parsed
            gnomes.append(Gnome(index=index, pos=_world_xy(obj, camera), facing=facing))
        elif GARDEN_OBJECT_BASE <= obj.object_id < GARDEN_OBJECT_LIMIT and label == "garden marker":
            gardens.append(Garden(object_id=obj.object_id, pos=_world_xy(obj, camera), has_food=True))
        elif INVENTORY_OBJECT_BASE <= obj.object_id < INVENTORY_OBJECT_LIMIT:
            inventory_count += 1  # best-effort (calibrate later)

    self_xy = (camera[0] + SELF_OFFSET[0], camera[1] + SELF_OFFSET[1])
    return HeartleafState(
        ready=True,
        self_xy=self_xy,
        time_minutes=parse_clock_minutes(clock) if clock is not None else None,
        gardens=tuple(gardens),
        gnomes=tuple(gnomes),
        own_house_index=None,  # CALIBRATION: seat/house identity is deferred.
        houses=(),  # CALIBRATION: v1 hosts via Belief.home_anchor, not house geometry.
        inventory_count=inventory_count,
    )


def _camera(world: SpriteWorld) -> tuple[int, int] | None:
    obj = world.objects.get(MAP_OBJECT_ID)
    if obj is None:
        return None
    return (-obj.x, -obj.y)


def _world_xy(obj: SpriteObject, camera: tuple[int, int]) -> tuple[int, int]:
    return (obj.x + camera[0], obj.y + camera[1])


def _sprite_label(world: SpriteWorld, obj: SpriteObject) -> str | None:
    sprite = world.sprite_for(obj)
    return None if sprite is None else sprite.label


def _parse_gnome_label(label: str) -> tuple[int, str] | None:
    parts = label.split()
    if len(parts) != 3 or parts[0] != "gnome":
        return None
    try:
        index = int(parts[1])
    except ValueError:
        return None
    return index, parts[2]


__all__ = ["SELF_OFFSET", "parse_clock_minutes", "perceive"]
