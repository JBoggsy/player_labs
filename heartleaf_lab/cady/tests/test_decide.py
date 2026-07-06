"""End-to-end tests for Cady's SpriteWorld decide adapter."""

from __future__ import annotations

from cady.decide import build_decide
from cady.mapdata import GARDEN_APPROACHES, GARDEN_CIRCUIT
from players.player_sdk import SpriteContext, SpriteDef, SpriteObject, SpriteWorld


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


def _gather_world() -> SpriteWorld:
    world = SpriteWorld()
    start_x, start_y = GARDEN_APPROACHES[GARDEN_CIRCUIT[-1]]
    labels = {
        1: "world map",
        400: "garden marker",
        700: "clock 1",
        701: "clock 0",
        702: "clock :",
        703: "clock 0",
        704: "clock 0",
        705: "clock a",
        706: "clock m",
    }
    world.sprites = {sprite_id: _sprite(sprite_id, label) for sprite_id, label in labels.items()}
    world.objects = {
        1: _object(1, -start_x, -start_y, 1),
        4000: _object(4000, 50, 0, 400),
        7000: _object(7000, 0, 20, 700),
        7001: _object(7001, 10, 20, 701),
        7002: _object(7002, 20, 20, 702),
        7003: _object(7003, 30, 20, 703),
        7004: _object(7004, 40, 20, 704),
        7005: _object(7005, 50, 20, 705),
        7006: _object(7006, 60, 20, 706),
    }
    return world


def test_decide_moves_toward_visible_garden_at_gather_time() -> None:
    decide = build_decide()

    mask = decide(_gather_world(), SpriteContext(frame=1))

    assert isinstance(mask, int)
    assert mask != 0


def test_decide_holds_still_when_world_not_ready() -> None:
    decide = build_decide()

    mask = decide(SpriteWorld(), SpriteContext(frame=1))

    assert mask == 0
