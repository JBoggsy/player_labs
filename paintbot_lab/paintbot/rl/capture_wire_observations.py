#!/usr/bin/env python3
"""Extract versioned observation snapshots from a recorded Sprite-v1 stream."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from players.player_sdk import SpriteWorld

from episode_map import EpisodeMap, episode_map_from_world
from observation_text import EntitySnapshot, ObservationSnapshot


GAME_LABEL_PREFIX = "game teams "
WALKABILITY_LABEL = "walkability map"


def map_dimensions(world: SpriteWorld) -> tuple[int, int] | None:
    for sprite in world.sprites.values():
        if sprite.label.startswith(GAME_LABEL_PREFIX):
            parts = sprite.label.split()
            if len(parts) == 5 and parts[3] == "map" and "x" in parts[4]:
                width, height = parts[4].split("x", 1)
                return int(width), int(height)
    for sprite in world.sprites.values():
        if sprite.label == WALKABILITY_LABEL:
            return sprite.width, sprite.height
    return None


def snapshot_world(
    world: SpriteWorld,
    *,
    game_version: str,
    source: str,
    tick: int | None = None,
) -> ObservationSnapshot:
    dimensions = map_dimensions(world)
    if dimensions is None:
        raise ValueError("frame has no game-parameter or walkability-map dimensions")

    entities = []
    for object_id, obj in world.objects.items():
        sprite = world.sprite_for(obj)
        if sprite is None or not sprite.label:
            continue
        entities.append(
            EntitySnapshot(
                object_id=object_id,
                label=sprite.label,
                x=obj.x,
                y=obj.y,
                z=obj.z,
                layer=obj.layer,
                width=sprite.width,
                height=sprite.height,
            )
        )
    return ObservationSnapshot(
        game_version=game_version,
        frame=world.frame,
        map_width=dimensions[0],
        map_height=dimensions[1],
        entities=tuple(entities),
        source=source,
        tick=tick,
    )


def extract(
    path: Path,
    *,
    game_version: str,
    stride: int,
    map_out: Path | None = None,
    selected_ticks: set[int] | None = None,
) -> list[ObservationSnapshot]:
    world = SpriteWorld()
    snapshots = []
    episode_map: EpisodeMap | None = None
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event.get("direction") != "in" or event.get("type") != "binary":
            continue
        if not world.apply_frame(base64.b64decode(event["data"])):
            continue
        if episode_map is None:
            episode_map = episode_map_from_world(world)
        event_tick = int(event["tick"]) if event.get("tick") is not None else None
        if selected_ticks is not None:
            if event_tick not in selected_ticks:
                continue
        elif world.frame != 1 and world.frame % stride != 0:
            continue
        try:
            snapshots.append(
                snapshot_world(
                    world,
                    game_version=game_version,
                    source=str(path),
                    tick=event_tick,
                )
            )
        except ValueError:
            # Early init packets may precede the map metadata.
            continue
    if map_out is not None:
        if episode_map is None:
            raise ValueError("wire stream did not contain walkability sprite pixels")
        map_out.parent.mkdir(parents=True, exist_ok=True)
        map_out.write_text(json.dumps(episode_map.to_dict()) + "\n")
    return snapshots


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wire", type=Path)
    parser.add_argument("--game-version", required=True)
    parser.add_argument("--stride", type=int, default=24)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--map-out",
        type=Path,
        help="write the episode-level packed walkability map as JSONL",
    )
    args = parser.parse_args()
    if args.stride <= 0:
        parser.error("--stride must be positive")

    snapshots = extract(
        args.wire,
        game_version=args.game_version,
        stride=args.stride,
        map_out=args.map_out,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(item.to_dict()) + "\n" for item in snapshots))
    print(f"wrote {len(snapshots)} observations to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
