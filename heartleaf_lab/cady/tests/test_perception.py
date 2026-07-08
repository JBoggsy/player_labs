"""Tests for Cady's label-only Heartleaf perception."""

from __future__ import annotations

from cady.perception import FOOT_OFFSET, parse_clock_minutes, perceive
from cady.types import Observation
from players.player_sdk import SpriteDef, SpriteObject, SpriteWorld

FX, FY = FOOT_OFFSET


def _sprite(sprite_id: int, label: str) -> SpriteDef:
    return SpriteDef(sprite_id=sprite_id, width=1, height=1, label=label, data=b"")


def _object(object_id: int, x: int, y: int, sprite_id: int) -> SpriteObject:
    return SpriteObject(object_id=object_id, x=x, y=y, z=0, layer=0, sprite_id=sprite_id)


def _perception_world() -> SpriteWorld:
    world = SpriteWorld()
    labels = {
        1: "heartleaf bottom 0",  # bottom layer -> main map context
        100: "gnome 0 south",
        101: "gnome 1 north",
        400: "garden marker",
        500: "inventory apple",
        501: "inventory pear",
        700: "clock 3", 701: "clock :", 702: "clock 0",
        703: "clock 0", 704: "clock p", 705: "clock m",
    }
    world.sprites = {sid: _sprite(sid, label) for sid, label in labels.items()}
    world.objects = {
        1: _object(1, 0, 0, 1),
        1000: _object(1000, 10, 20, 100),   # foot (26, 46)
        1001: _object(1001, 150, 90, 101),  # foot (166, 116) — nearest the viewport centre
        4000: _object(4000, 30, 40, 400),
        5000: _object(5000, 3, 4, 500),
        5001: _object(5001, 7, 8, 501),
        7004: _object(7004, 44, 20, 704), 7001: _object(7001, 11, 20, 701),
        7005: _object(7005, 55, 20, 705), 7000: _object(7000, 0, 20, 700),
        7003: _object(7003, 33, 20, 703), 7002: _object(7002, 22, 20, 702),
    }
    return world


def test_perceive_self_is_the_own_gnome_foot_nearest_viewport_centre() -> None:
    state = perceive(Observation(world=_perception_world(), frame=1))

    assert state.ready
    assert state.map_context == "main"  # from the bottom-layer sprite label
    # gnome 1001 (foot (166,116)) is nearest the 320x200 viewport centre (160,100).
    assert state.self_xy == (150 + FX, 90 + FY)
    assert state.own_house_index == 1
    assert state.time_minutes == 420
    assert state.inventory_count == 2

    assert len(state.gardens) == 1
    assert state.gardens[0].pos == (30, 40)  # marker pos + camera (0 here); no foot offset

    by_index = {g.index: g for g in state.gnomes}
    assert by_index[0].facing == "south" and by_index[0].pos == (10 + FX, 20 + FY)
    assert by_index[1].facing == "north" and by_index[1].pos == (150 + FX, 90 + FY)


def test_perceive_without_a_gnome_degrades_cleanly() -> None:
    world = _perception_world()
    del world.objects[1000]
    del world.objects[1001]

    state = perceive(Observation(world=world, frame=1))

    assert not state.ready
    assert state.self_xy is None
    assert state.gnomes == ()


def test_perceive_detects_home_context_from_bottom_object() -> None:
    world = _perception_world()
    world.sprites[1] = _sprite(1, "heartleaf home bottom 3")

    state = perceive(Observation(world=world, frame=1))

    assert state.map_context == "home"


def test_parse_clock_minutes() -> None:
    assert parse_clock_minutes("8:00am") == 0
    assert parse_clock_minutes("12:00pm") == 240
    assert parse_clock_minutes("6:00pm") == 600
    assert parse_clock_minutes("12:00am") == -480
    assert parse_clock_minutes("junk") is None


def test_perceive_applies_camera_offset_on_a_scrolling_map() -> None:
    """On the main map the bottom object scrolls; self = screen foot + camera."""
    world = _perception_world()
    world.objects[1] = _object(1, -300, -600, 1)  # camera = (300, 600)

    state = perceive(Observation(world=world, frame=1))

    # gnome 1001 screen foot (166,116) + camera (300,600) = (466,716)
    assert state.self_xy == (150 + FX + 300, 90 + FY + 600)
    assert state.gnomes[0].pos[0] >= 300  # everything shifted into map space


def _invite_world() -> SpriteWorld:
    """Cady (gnome 6, near viewport center) + villager 'Anton' (slot 1) inviting."""
    world = SpriteWorld()
    world.sprites = {
        1: _sprite(1, "heartleaf bottom 0"),
        106: _sprite(106, "gnome 6 south"),
        201: _sprite(201, "name Anton"),
        301: _sprite(301, "chat Dinner at my house at 6, tell everyone!"),
    }
    world.objects = {
        1: _object(1, 0, 0, 1),
        1006: _object(1006, 150, 90, 106),  # nearest viewport center -> self
        2001: _object(2001, 50, 50, 201),   # NameObjectBase + 1
        3001: _object(3001, 50, 40, 301),   # ChatObjectBase + 1
    }
    return world


def test_perceive_hears_invite_and_resolves_speaker_house() -> None:
    from cady.types import HeardInvite

    state = perceive(Observation(world=_invite_world(), frame=1))
    assert state.heard_invites == (HeardInvite(house_index=1, speaker="Anton"),)  # Anton -> house 1


def test_perceive_ignores_non_invite_chat() -> None:
    world = _invite_world()
    world.sprites[301] = _sprite(301, "chat Have you seen the creek today?")
    state = perceive(Observation(world=world, frame=1))
    assert state.heard_invites == ()


def test_perceive_ignores_our_own_invite() -> None:
    # A chat from the slot whose name maps to OUR house is not a party to attend.
    world = _invite_world()
    world.sprites[201] = _sprite(201, "name Vova")  # Vova == house 6 == Cady's own
    state = perceive(Observation(world=world, frame=1))
    assert state.heard_invites == ()  # own-house invite dropped
