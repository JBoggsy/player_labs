"""Tests for Cady's label-only Heartleaf perception."""

from __future__ import annotations

from cady.perception import SELF_OFFSET, parse_clock_minutes, perceive
from cady.types import Observation
from players.player_sdk import SpriteDef, SpriteObject, SpriteWorld


def _sprite(sprite_id: int, label: str) -> SpriteDef:
    return SpriteDef(sprite_id=sprite_id, width=1, height=1, label=label, data=b"")


def _object(object_id: int, x: int, y: int, sprite_id: int, *, layer: int = 0) -> SpriteObject:
    return SpriteObject(
        object_id=object_id,
        x=x,
        y=y,
        z=0,
        layer=layer,
        sprite_id=sprite_id,
    )


def _perception_world() -> SpriteWorld:
    world = SpriteWorld()
    labels = {
        1: "world map",
        100: "gnome 0 south",
        101: "gnome 1 north",
        400: "garden marker",
        500: "inventory apple",
        501: "inventory pear",
        700: "clock 3",
        701: "clock :",
        702: "clock 0",
        703: "clock 0",
        704: "clock p",
        705: "clock m",
    }
    world.sprites = {sprite_id: _sprite(sprite_id, label) for sprite_id, label in labels.items()}
    world.objects = {
        1: _object(1, -100, -50, 1),
        1000: _object(1000, 10, 20, 100),
        1001: _object(1001, 40, 25, 101),
        4000: _object(4000, 30, 40, 400),
        5000: _object(5000, 3, 4, 500),
        5001: _object(5001, 7, 8, 501),
        7004: _object(7004, 44, 20, 704),
        7001: _object(7001, 11, 20, 701),
        7005: _object(7005, 55, 20, 705),
        7000: _object(7000, 0, 20, 700),
        7003: _object(7003, 33, 20, 703),
        7002: _object(7002, 22, 20, 702),
    }
    return world


def test_perceive_resolves_world_coordinates_labels_and_clock() -> None:
    state = perceive(Observation(world=_perception_world(), frame=1))

    assert state.ready
    assert state.self_xy == (100 + SELF_OFFSET[0], 50 + SELF_OFFSET[1])
    assert state.time_minutes == 420
    assert state.inventory_count == 2

    assert len(state.gardens) == 1
    assert state.gardens[0].object_id == 4000
    assert state.gardens[0].pos == (130, 90)
    assert state.gardens[0].has_food

    by_index = {gnome.index: gnome for gnome in state.gnomes}
    assert by_index[0].facing == "south"
    assert by_index[0].pos == (110, 70)
    assert by_index[1].facing == "north"
    assert by_index[1].pos == (140, 75)


def test_perceive_without_world_map_degrades_cleanly() -> None:
    world = _perception_world()
    del world.objects[1]

    state = perceive(Observation(world=world, frame=1))

    assert not state.ready
    assert state.self_xy is None
    assert state.time_minutes is None
    assert state.gardens == ()
    assert state.gnomes == ()


def test_parse_clock_minutes() -> None:
    assert parse_clock_minutes("8:00am") == 0
    assert parse_clock_minutes("12:00pm") == 240
    assert parse_clock_minutes("6:00pm") == 600
    assert parse_clock_minutes("12:00am") == -480
    assert parse_clock_minutes("junk") is None
