#!/usr/bin/env python3
"""Render sampled GotA hero paths or occupancy heatmaps from expanded JSONL (Pillow).

Generate samples with replay_stats.py --snapshot-every 240 first. Coordinates use
BASIC tiles: x increases right, y increases down. This is a tile grid, not terrain.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

COLORS = ('#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
          '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4')


def render(source: Path, output: Path, *, mode: str = 'paths',
           slots: set[int] | None = None, scale: int = 6) -> None:
    paths = defaultdict(list)
    heat = Counter()
    meta = summary = last_state = None
    samples = 0
    with source.open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['type'] == 'meta':
                meta = row
            elif row['type'] == 'summary':
                summary = row
            elif row.get('kind') in ('hero_death', 'hero_respawn'):
                paths[row['slot']].append(None)
            elif row.get('kind') == 'objective_state':
                last_state = row
                samples += 1
                for hero in row['heroes']:
                    slot = hero['slot']
                    if slots is not None and slot not in slots:
                        continue
                    if not hero['alive']:
                        paths[slot].append(None)
                        continue
                    point = (hero['pos']['x'], hero['pos']['y'])
                    paths[slot].append(point)
                    heat[point] += 1
    if not meta or not summary or not summary.get('verified'):
        raise ValueError('input lacks a hash-verified summary')
    if not samples:
        raise ValueError('no objective_state samples; expand with --snapshot-every 240')
    if not heat:
        raise ValueError('no living hero samples for the selected seats')
    grid = meta['grid_tiles']
    margin = 48
    size = grid * scale
    image = Image.new('RGB', (size + 2*margin, size + 160), '#111827')
    draw = ImageDraw.Draw(image)
    draw.text((margin, 10), f'GotA {mode} | {samples} snapshots | {summary["ticks"]} ticks', fill='white')
    def pixel(point):
        return (margin + point[0]*scale + scale//2, margin + point[1]*scale + scale//2)
    if mode == 'heatmap':
        peak = max(heat.values())
        for (x, y), count in heat.items():
            if not 0 <= x < grid or not 0 <= y < grid:
                continue
            strength = (count / peak) ** 0.5
            color = (int(255*strength), int(180*strength), 35)
            left, top = margin+x*scale, margin+y*scale
            draw.rectangle((left, top, left+scale-1, top+scale-1), fill=color)
        draw.text((margin, margin+size+18), f'Peak: {peak} hero samples/tile; brightness uses square-root scaling', fill='white')
    for tile in range(0, grid+1, 10):
        at = margin + tile*scale
        draw.line((at, margin, at, margin+size), fill='#374151')
        draw.line((margin, at, margin+size, at), fill='#374151')
        draw.text((at, margin-16), str(tile), fill='#9ca3af')
        draw.text((10, at), str(tile), fill='#9ca3af')
    if mode == 'paths':
        for slot, points in paths.items():
            if slots is not None and slot not in slots:
                continue
            previous = None
            for point in points:
                if point is None:
                    previous = None
                    continue
                here = pixel(point)
                if previous is not None:
                    draw.line((*previous, *here), fill=COLORS[slot % len(COLORS)], width=2)
                previous = here
            if previous:
                draw.text(previous, str(slot), fill='white')
        for slot in sorted(paths):
            if slots is None or slot in slots:
                draw.text((margin+(slot % 5)*size//5, margin+size+18+(slot//5)*18),
                          f'Seat {slot}', fill=COLORS[slot % len(COLORS)])
    for building in last_state['buildings']:
        color = '#f87171' if building['team'] == 'RedTeam' else '#60a5fa'
        if building['hp'] <= 0:
            color = '#6b7280'
        draw.text(pixel((building['pos']['x'], building['pos']['y'])),
                  'T' if building['building_kind'] == 'tower' else 'B', fill=color)
    for fort in last_state['forts']:
        draw.text(pixel((fort['pos']['x'], fort['pos']['y'])), 'F', fill='white')
    draw.text((margin, margin+size+65), 'x -> right; y -> down | T tower, B barracks, F fort | samples, not exact trajectories', fill='#9ca3af')
    image.save(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('expanded', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--mode', choices=('paths', 'heatmap'), default='paths')
    parser.add_argument('--slot', type=int, action='append', help='restrict to seat(s); repeatable')
    parser.add_argument('--scale', type=int, default=6, help='pixels per tile')
    args = parser.parse_args()
    if not 1 <= args.scale <= 32:
        parser.error('--scale must be between 1 and 32')
    if args.slot and any(not 0 <= slot < 10 for slot in args.slot):
        parser.error('--slot must be between 0 and 9')
    render(args.expanded, args.output, mode=args.mode,
           slots=set(args.slot) if args.slot else None, scale=args.scale)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f'viz_replay: {error}', file=sys.stderr)
        raise SystemExit(1)
