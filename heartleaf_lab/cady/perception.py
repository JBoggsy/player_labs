"""Label-only Heartleaf perception from the SDK ``SpriteWorld``."""

from __future__ import annotations

import re

from players.player_sdk import SpriteObject, SpriteWorld

from cady.config import PLAYER_NAMES
from cady.tools.capture_scene import read_clock_string
from cady.types import Garden, Gnome, HeardInvite, HeartleafState, MapContext, Observation

BOTTOM_OBJECT_ID = 1  # the map's bottom layer; its sprite label names the active map
GNOME_OBJECT_BASE = 1000
GNOME_OBJECT_LIMIT = 2000
NAME_OBJECT_BASE = 2000  # "name <PlayerName>" per visible player (NameObjectBase + slot)
NAME_OBJECT_LIMIT = 3000
CHAT_OBJECT_BASE = 3000  # "chat <text>" per speaking visible player (ChatObjectBase + slot)
CHAT_OBJECT_LIMIT = 4000
GARDEN_OBJECT_BASE = 4000
GARDEN_OBJECT_LIMIT = 5000
INVENTORY_OBJECT_BASE = 5000
INVENTORY_OBJECT_LIMIT = 6000
NAME_LABEL_PREFIX = "name "
CHAT_LABEL_PREFIX = "chat "
# Host-invite phrasings (mirror heartleaf isHostInviteMessage). Invites say "my
# house", so the TEXT doesn't name the house — the SPEAKER's name does.
_HOST_INVITE_PHRASES = ("at my house", "party at my", "come to my", "meet at my", "dinner at my", "my place")
_NAME_TO_HOUSE = {name.lower(): i for i, name in enumerate(PLAYER_NAMES)}
MAIN_WALKABILITY_LABEL = "heartleaf main walkability"
HOME_WALKABILITY_LABEL = "heartleaf home walkability"
MAIN_BOTTOM_PREFIX = "heartleaf bottom"
HOME_BOTTOM_PREFIX = "heartleaf home bottom"

# Object x/y are the gnome sprite top-left in the CURRENT map's pixel frame (which
# equals our baked-grid frame — no camera offset). The gnome STANDS at its foot:
# foot = (x + PlayerBoxOffsetX + PlayerBoxWidth//2, y + PlayerBoxOffsetY + PlayerBoxHeight//2)
# = (x + 16, y + 26) (heartleaf common.nim). Self position is the own gnome's foot.
FOOT_OFFSET = (16, 26)
# The controlled gnome is the one nearest the 320x200 viewport centre (the camera
# follows it) — mirrors the game's own villager `findSelfIndexByCamera`.
VIEWPORT_CENTER = (160, 100)

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
    map_context = _map_context(world)
    # Object x/y are viewport/screen coords; the map scrolls, so the true map
    # position is screen + camera, where camera = -(bottom layer object's placement)
    # (the bottom is pinned to the map origin). The home map fits the viewport so
    # its bottom sits at (0,0) -> camera 0; the larger main map scrolls -> camera != 0.
    cam = _camera(world)

    clock = read_clock_string(world)
    gardens: list[Garden] = []
    gnomes: list[Gnome] = []
    inventory_count = 0
    own: tuple[int, tuple[int, int], str] | None = None  # (index, map_foot, facing)
    own_dist = None
    names_by_slot: dict[int, str] = {}   # NameObjectBase+slot -> speaker name
    chats_by_slot: dict[int, str] = {}   # ChatObjectBase+slot -> chat text

    for obj in world.objects.values():
        label = _sprite_label(world, obj)
        if label is None:
            continue

        if NAME_OBJECT_BASE <= obj.object_id < NAME_OBJECT_LIMIT:
            if label.startswith(NAME_LABEL_PREFIX):
                names_by_slot[obj.object_id - NAME_OBJECT_BASE] = label[len(NAME_LABEL_PREFIX):]
            continue
        if CHAT_OBJECT_BASE <= obj.object_id < CHAT_OBJECT_LIMIT:
            if label.startswith(CHAT_LABEL_PREFIX):
                chats_by_slot[obj.object_id - CHAT_OBJECT_BASE] = label[len(CHAT_LABEL_PREFIX):]
            continue

        if GNOME_OBJECT_BASE <= obj.object_id < GNOME_OBJECT_LIMIT:
            parsed = _parse_gnome_label(label)
            if parsed is None:
                continue
            index, facing = parsed
            # self-selection uses the SCREEN foot (self is nearest the viewport
            # centre); the reported position is the MAP foot (screen + camera).
            screen_foot = (obj.x + FOOT_OFFSET[0], obj.y + FOOT_OFFSET[1])
            map_foot = (screen_foot[0] + cam[0], screen_foot[1] + cam[1])
            gnomes.append(Gnome(index=index, pos=map_foot, facing=facing))
            dist = (screen_foot[0] - VIEWPORT_CENTER[0]) ** 2 + (screen_foot[1] - VIEWPORT_CENTER[1]) ** 2
            if own_dist is None or dist < own_dist:
                own_dist = dist
                own = (index, map_foot, facing)
        elif GARDEN_OBJECT_BASE <= obj.object_id < GARDEN_OBJECT_LIMIT and label == "garden marker":
            gardens.append(Garden(object_id=obj.object_id, pos=(obj.x + cam[0], obj.y + cam[1]), has_food=True))
        elif INVENTORY_OBJECT_BASE <= obj.object_id < INVENTORY_OBJECT_LIMIT:
            inventory_count += 1  # best-effort (calibrate later)

    if own is None:
        # No gnome visible -> we can't locate ourselves this frame.
        return HeartleafState(
            ready=False, self_xy=None, map_context=map_context, time_minutes=None,
            gardens=(), gnomes=(), own_house_index=None, houses=(), inventory_count=0,
        )

    return HeartleafState(
        ready=True,
        self_xy=own[1],
        map_context=map_context,
        time_minutes=parse_clock_minutes(clock) if clock is not None else None,
        gardens=tuple(gardens),
        gnomes=tuple(gnomes),
        own_house_index=own[0],  # the controlled gnome's label index
        houses=(),
        inventory_count=inventory_count,
        heard_invites=_heard_invites(names_by_slot, chats_by_slot, own[0]),
    )


def _heard_invites(
    names_by_slot: dict[int, str],
    chats_by_slot: dict[int, str],
    own_house_index: int,
) -> tuple[HeardInvite, ...]:
    """Pair name+chat objects by slot; a host-invite chat from another player
    resolves to that speaker's house (invites say 'my house', so the speaker
    identifies the party, not the text)."""
    invites: list[HeardInvite] = []
    for slot, text in chats_by_slot.items():
        speaker = names_by_slot.get(slot)
        if speaker is None or not _is_host_invite(text):
            continue
        house = _NAME_TO_HOUSE.get(speaker.strip().lower())
        if house is None or house == own_house_index:
            continue
        invites.append(HeardInvite(house_index=house, speaker=speaker))
    return tuple(invites)


def _is_host_invite(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _HOST_INVITE_PHRASES)


def _camera(world: SpriteWorld) -> tuple[int, int]:
    """Camera offset (map = screen + camera) from the bottom layer object (id 1),
    which is pinned to the map origin. (0, 0) when the bottom isn't placed yet."""
    bottom = world.objects.get(BOTTOM_OBJECT_ID)
    if bottom is None:
        return (0, 0)
    return (-bottom.x, -bottom.y)


def _map_context(world: SpriteWorld) -> MapContext:
    """Active map from the bottom layer object (id 1) sprite label — reliable even
    when both maps' walkability sprite *definitions* linger. Falls back to the
    walkability labels present."""
    bottom = world.objects.get(BOTTOM_OBJECT_ID)
    if bottom is not None:
        sprite = world.sprite_for(bottom)
        if sprite is not None:
            if sprite.label.startswith(HOME_BOTTOM_PREFIX):
                return "home"
            if sprite.label.startswith(MAIN_BOTTOM_PREFIX):
                return "main"
    labels = {sprite.label for sprite in world.sprites.values()}
    if HOME_WALKABILITY_LABEL in labels:
        return "home"
    if MAIN_WALKABILITY_LABEL in labels:
        return "main"
    return "unknown"


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


__all__ = ["HOME_WALKABILITY_LABEL", "MAIN_WALKABILITY_LABEL", "parse_clock_minutes", "perceive"]
