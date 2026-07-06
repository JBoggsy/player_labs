"""Diagnostic SpriteV1 scene dump for calibrating Heartleaf perception.

This module is intentionally label-and-position only. It rides the SDK
``SpriteWorld`` exactly as Cady's future perception layer will, but does not
decode pixels or infer game semantics beyond Heartleaf's documented object-id
ranges.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TextIO

from players.player_sdk import (
    Button,
    SpriteContext,
    SpriteObject,
    SpriteWorld,
    env_ws_url,
    run_sprite_bridge,
)

CLOCK_GLYPH_START = 7000
CLOCK_GLYPH_END = 7100


def read_clock_string(world: SpriteWorld) -> str | None:
    """Read Heartleaf's clock by joining per-glyph ``clock <char>`` labels.

    Clock glyph objects can arrive in any dictionary insertion order, so they
    are ordered by x coordinate and then object id for deterministic tie
    handling. Objects with missing sprite definitions or non-clock labels are
    ignored. ``None`` means no clock glyphs were readable in this world.
    """

    glyphs: list[tuple[int, int, str]] = []
    for obj in world.objects.values():
        if not CLOCK_GLYPH_START <= obj.object_id < CLOCK_GLYPH_END:
            continue
        sprite = world.sprite_for(obj)
        if sprite is None or not sprite.label.startswith("clock "):
            continue
        char = sprite.label[len("clock ") :]
        if char:
            glyphs.append((obj.x, obj.object_id, char))

    if not glyphs:
        return None
    return "".join(char for _, _, char in sorted(glyphs))


@dataclass(frozen=True)
class ObjectGroup:
    """Display grouping for one Heartleaf object-id range."""

    sort_key: int
    title: str


def _object_group(object_id: int) -> ObjectGroup:
    if object_id == 1:
        return ObjectGroup(0, "1 world-map/camera")
    if 1000 <= object_id < 2000:
        return ObjectGroup(10, "1000s gnomes")
    if 2000 <= object_id < 3000:
        return ObjectGroup(20, "2000s name tags")
    if 3000 <= object_id < 4000:
        return ObjectGroup(30, "3000s chat bubbles")
    if 4000 <= object_id < 5000:
        return ObjectGroup(40, "4000s gardens")
    if 5000 <= object_id < 6000:
        return ObjectGroup(50, "5000s inventory items")
    if 6000 <= object_id < 7000:
        return ObjectGroup(60, "6000s inventory/ui counts")
    if CLOCK_GLYPH_START <= object_id < CLOCK_GLYPH_END:
        return ObjectGroup(70, "7000s clock glyphs")
    if 7100 <= object_id < 7200:
        return ObjectGroup(71, "7100s score panels")
    return ObjectGroup(99, "unknown")


def _sprite_label(world: SpriteWorld, obj: SpriteObject) -> str:
    sprite = world.sprite_for(obj)
    if sprite is None:
        return "<missing sprite>"
    return sprite.label or "<empty label>"


class CaptureSceneProbe:
    """A ``decide(world, ctx)`` probe that dumps the first changed frames."""

    def __init__(self, max_frames: int = 40, out: TextIO | None = None) -> None:
        self.max_frames = max(0, max_frames)
        self.out = sys.stdout if out is None else out
        self._dumped_frames = 0

    def decide(self, world: SpriteWorld, ctx: SpriteContext) -> Button:
        """Dump one frame while under the frame limit, then hold neutral input."""

        if self._dumped_frames < self.max_frames:
            self._dump_world(world, ctx)
            self._dumped_frames += 1
        return Button(0)

    def _dump_world(self, world: SpriteWorld, ctx: SpriteContext) -> None:
        clock = read_clock_string(world)
        print(
            f"frame={ctx.frame} objects={len(world.objects)} sprites={len(world.sprites)} "
            f"clock={clock or '<none>'}",
            file=self.out,
        )

        grouped: dict[ObjectGroup, list[SpriteObject]] = defaultdict(list)
        for obj in world.objects.values():
            grouped[_object_group(obj.object_id)].append(obj)

        for group in sorted(grouped, key=lambda item: item.sort_key):
            print(f"[{group.title}]", file=self.out)
            for obj in sorted(grouped[group], key=lambda item: item.object_id):
                label = _sprite_label(world, obj)
                print(
                    f"  object_id={obj.object_id} label={label!r} "
                    f"pos=({obj.x}, {obj.y}, {obj.z}) layer={obj.layer} sprite_id={obj.sprite_id}",
                    file=self.out,
                )


_DEFAULT_PROBE = CaptureSceneProbe()


def decide(world: SpriteWorld, ctx: SpriteContext) -> Button:
    """Default bridge callback used by ``run_sprite_bridge``."""

    return _DEFAULT_PROBE.decide(world, ctx)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the capture probe against ``COWORLD_PLAYER_WS_URL``."""

    parser = argparse.ArgumentParser(description="Dump Heartleaf SpriteV1 scene labels.")
    parser.add_argument(
        "--frames",
        type=int,
        default=40,
        help="number of changed frames to dump before staying quiet",
    )
    args = parser.parse_args(argv)

    probe = CaptureSceneProbe(max_frames=args.frames)
    asyncio.run(run_sprite_bridge(env_ws_url(), probe.decide))


if __name__ == "__main__":
    main()
