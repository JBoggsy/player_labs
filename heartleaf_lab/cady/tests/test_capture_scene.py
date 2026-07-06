"""Tests for the Heartleaf scene-capture probe."""

from __future__ import annotations

import pytest

from cady.tools.capture_scene import CaptureSceneProbe, read_clock_string
from players.player_sdk import Button, SpriteContext, SpriteDef, SpriteObject, SpriteWorld


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


def _world() -> SpriteWorld:
    world = SpriteWorld()
    labels = {
        1: "world map",
        100: "gnome 0 south",
        101: "gnome 1 north",
        400: "garden marker",
        700: "clock 3",
        701: "clock :",
        702: "clock 0",
        703: "clock 0",
        704: "clock p",
        705: "clock m",
    }
    world.sprites = {sprite_id: _sprite(sprite_id, label) for sprite_id, label in labels.items()}
    world.objects = {
        1: _object(1, 100, 200, 1, layer=0),
        1000: _object(1000, 90, 210, 100, layer=2),
        1001: _object(1001, 110, 210, 101, layer=2),
        4000: _object(4000, 130, 240, 400, layer=1),
        # Insert glyph objects out of x-order; read_clock_string must sort by x.
        7004: _object(7004, 44, 20, 704),
        7001: _object(7001, 11, 20, 701),
        7005: _object(7005, 55, 20, 705),
        7000: _object(7000, 0, 20, 700),
        7003: _object(7003, 33, 20, 703),
        7002: _object(7002, 22, 20, 702),
    }
    return world


def test_read_clock_string_sorts_clock_glyphs_by_x() -> None:
    assert read_clock_string(_world()) == "3:00pm"


def test_capture_probe_dumps_scene_vocabulary(capsys: pytest.CaptureFixture[str]) -> None:
    probe = CaptureSceneProbe(max_frames=1)

    result = probe.decide(_world(), SpriteContext(frame=1))
    assert result == Button(0)

    output = capsys.readouterr().out
    assert "clock=3:00pm" in output
    assert "garden marker" in output
    assert "gnome 0 south" in output
    assert "gnome 1 north" in output

    probe.decide(_world(), SpriteContext(frame=2))
    assert capsys.readouterr().out == ""
