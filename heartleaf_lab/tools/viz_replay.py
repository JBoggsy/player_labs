#!/usr/bin/env python3
"""Draw player travel lines and event markers from an expanded Heartleaf replay.

Consumes the JSONL produced by ``tools/expand_replay`` (see
``build_expand_replay.sh``) and renders, over the baked walkability map, each
player's path on the main map with event markers — a navigation/behaviour
debugging image.

    # build the expander once, expand a replay, then draw it:
    heartleaf_lab/tools/build_expand_replay.sh
    heartleaf_lab/tools/bin/expand_replay replay.json > out.jsonl
    uv run python heartleaf_lab/tools/viz_replay.py out.jsonl --out paths.png

    # or pipe straight through:
    heartleaf_lab/tools/bin/expand_replay replay.json \
        | uv run python heartleaf_lab/tools/viz_replay.py - --player Cady

By default every main-map player is drawn faintly and all are labelled; pass
``--player NAME`` to spotlight one (its path bright, the rest dimmed).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# Make the sibling ``cady`` package importable for the baked map data.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cady.mapdata import GARDEN_RECTS, HOUSE_RECTS, WALK_GRID  # noqa: E402

# A distinct, high-contrast colour per player slot (0..8).
_PLAYER_COLORS = [
    (231, 76, 60), (46, 204, 113), (52, 152, 219), (241, 196, 15),
    (155, 89, 182), (26, 188, 156), (230, 126, 34), (236, 64, 122),
    (149, 165, 166),
]
# Background: walkable vs wall (light paper / ink).
_WALKABLE_RGB = (238, 236, 230)
_WALL_RGB = (60, 66, 74)
_GARDEN_OUTLINE = (39, 174, 96)
_HOUSE_OUTLINE = (41, 128, 185)

# Event marker styling: (radius, fill). Drawn on the acting player's colour when
# it reads better, else a fixed colour.
_EVENT_STYLE = {
    "harvest": ("dot", 3),
    "enter_house": ("up", 4),
    "exit_house": ("down", 4),
    "chat": ("dot", 2),
    "score": ("star", 5),
    "dinner": ("star", 6),
}


def _color_for(slot: int) -> tuple[int, int, int]:
    return _PLAYER_COLORS[slot % len(_PLAYER_COLORS)]


def _dim(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Blend a colour toward the walkable background by ``factor`` (0..1)."""
    return tuple(
        int(c + (bg - c) * factor) for c, bg in zip(color, _WALKABLE_RGB)
    )


def _split_segments(ticks: list[int], points: list[tuple[int, int]]):
    """Split a path into contiguous segments, breaking where the player left
    the main map (a large gap in sampled ticks — e.g. a house visit) so we
    don't draw a misleading straight line across the resulting jump."""
    if len(ticks) < 2:
        return [points]
    deltas = sorted(ticks[i + 1] - ticks[i] for i in range(len(ticks) - 1))
    stride = deltas[len(deltas) // 2] or 1  # median sampling stride
    threshold = max(stride * 4, stride + 1)
    segments: list[list[tuple[int, int]]] = [[]]
    for i, point in enumerate(points):
        if i > 0 and ticks[i] - ticks[i - 1] > threshold:
            segments.append([])
        segments[-1].append(point)
    return segments


def _read_rows(source: str):
    stream = sys.stdin if source == "-" else open(source, encoding="utf-8")
    with stream:
        for line in stream:
            line = line.strip()
            if line:
                yield json.loads(line)


def _base_image() -> Image.Image:
    """Walkability map as a paper/ink background image (H x W)."""
    grid = np.asarray(WALK_GRID, dtype=bool)
    rgb = np.where(grid[..., None], _WALKABLE_RGB, _WALL_RGB).astype(np.uint8)
    image = Image.fromarray(rgb, mode="RGB")
    draw = ImageDraw.Draw(image)
    for x, y, w, h in GARDEN_RECTS:
        draw.rectangle([x, y, x + w - 1, y + h - 1], outline=_GARDEN_OUTLINE)
    for x, y, w, h in HOUSE_RECTS:
        draw.rectangle([x, y, x + w - 1, y + h - 1], outline=_HOUSE_OUTLINE)
    return image


def _marker(draw: ImageDraw.ImageDraw, shape: str, x: int, y: int,
            radius: int, color: tuple[int, int, int]) -> None:
    if shape == "dot":
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)
    elif shape == "up":
        draw.polygon([(x, y - radius), (x - radius, y + radius),
                      (x + radius, y + radius)], fill=color)
    elif shape == "down":
        draw.polygon([(x, y + radius), (x - radius, y - radius),
                      (x + radius, y - radius)], fill=color)
    elif shape == "star":
        draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                     fill=color, outline=(0, 0, 0))


def render(rows, spotlight: str | None, spotlight_user: str | None,
           draw_events: bool) -> Image.Image:
    """Render travel lines + events for all main-map players."""
    names: dict[int, str] = {}
    users: dict[int, str] = {}
    # Per slot: parallel lists of sampled ticks and (x, y) on the main map.
    ticks: dict[int, list[int]] = {}
    paths: dict[int, list[tuple[int, int]]] = {}
    events: list[dict] = []

    for row in rows:
        kind = row.get("type")
        if kind == "tick":
            tick = row["tick"]
            for player in row["players"]:
                if player["map"] != 0:  # main map only
                    continue
                slot = player["slot"]
                names[slot] = player["name"]
                users[slot] = player.get("user", "")
                ticks.setdefault(slot, []).append(tick)
                paths.setdefault(slot, []).append((player["x"], player["y"]))
        elif kind == "event":
            events.append(row)

    image = _base_image()
    draw = ImageDraw.Draw(image)

    def is_spotlit(slot: int) -> bool:
        if spotlight_user is not None:
            return users.get(slot, "") == spotlight_user
        return spotlight is None or names.get(slot, "") == spotlight

    # Travel lines: dim the non-spotlit players so the subject stands out.
    for slot, points in sorted(paths.items()):
        if len(points) < 2:
            continue
        base = _color_for(slot)
        spot = is_spotlit(slot)
        color = base if spot else _dim(base, 0.72)
        for segment in _split_segments(ticks[slot], points):
            if len(segment) >= 2:
                draw.line(segment, fill=color, width=2 if spot else 1,
                          joint="curve")
        sx, sy = points[0]
        ex, ey = points[-1]
        draw.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], outline=(0, 0, 0),
                     fill=color)  # start
        draw.rectangle([ex - 3, ey - 3, ex + 3, ey + 3], outline=(0, 0, 0),
                       fill=color)  # end

    if draw_events:
        for event in events:
            style = _EVENT_STYLE.get(event["kind"])
            if style is None:
                continue
            slot = event.get("slot", -1)
            if not is_spotlit(slot):
                continue
            # Place the marker at the sampled position nearest the event's tick.
            pts = paths.get(slot)
            slot_ticks = ticks.get(slot)
            if not pts or not slot_ticks:
                continue
            index = int(np.searchsorted(slot_ticks, event["tick"]))
            index = min(index, len(pts) - 1)
            x, y = pts[index]
            shape, radius = style
            _marker(draw, shape, x, y, radius, _color_for(slot))

    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", help="expanded replay JSONL ('-' for stdin)")
    parser.add_argument("--out", default="replay_paths.png", help="output PNG")
    parser.add_argument("--player", default=None,
                        help="spotlight this player NAME (display name; dim the rest)")
    parser.add_argument("--user", default=None,
                        help="spotlight by USERNAME instead of display name "
                             "(e.g. --user Cady; display names vary per episode)")
    parser.add_argument("--no-events", action="store_true",
                        help="draw only travel lines, no event markers")
    parser.add_argument("--scale", type=int, default=1,
                        help="integer upscale factor for the output image")
    args = parser.parse_args()

    image = render(_read_rows(args.jsonl), args.player, args.user, not args.no_events)
    if args.scale > 1:
        image = image.resize(
            (image.width * args.scale, image.height * args.scale),
            Image.NEAREST,
        )
    image.save(args.out)
    print(f"wrote {args.out} ({image.width}x{image.height})", file=sys.stderr)


if __name__ == "__main__":
    main()
