#!/usr/bin/env python3
"""Render the per-game-hour movement flow field as arrows over the map.

Draws, for each game-hour, one arrow per cell pointing in the mean direction
players moved through that cell (from `cady/mapdata/flow_field.npz`, built by
`build_flow_field.py`), over the real Heartleaf map. Arrow length/opacity scale
with how consistent+busy the flow is — so you can see the daily drift (gardens →
central paths → houses) aggregated across many games.

Usage:
    uv run python heartleaf_lab/tools/viz_flow_field.py --map heartleaf_map.png --out-dir /tmp/flow
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cady.mapdata import WALK_GRID  # noqa: E402

_WALKABLE_RGB = (238, 236, 230)
_WALL_RGB = (60, 66, 74)
FLOW_PATH = Path(__file__).resolve().parent.parent / "cady" / "mapdata" / "flow_field.npz"


def _base(map_png: Path | None, w: int, h: int) -> Image.Image:
    if map_png is not None and map_png.exists():
        img = Image.open(map_png).convert("RGB")
        return img if img.size == (w, h) else img.resize((w, h), Image.NEAREST)
    grid = np.asarray(WALK_GRID, dtype=bool)
    rgb = np.where(grid[..., None], _WALKABLE_RGB, _WALL_RGB).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


def _arrow(draw: ImageDraw.ImageDraw, x0, y0, dx, dy, color) -> None:
    x1, y1 = x0 + dx, y0 + dy
    draw.line([(x0, y0), (x1, y1)], fill=color, width=2)
    # arrowhead
    ang = math.atan2(dy, dx)
    for da in (math.radians(150), math.radians(-150)):
        hx = x1 + 4 * math.cos(ang + da)
        hy = y1 + 4 * math.sin(ang + da)
        draw.line([(x1, y1), (hx, hy)], fill=color, width=2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("flow_viz"))
    parser.add_argument("--min-count", type=int, default=30,
                        help="skip cells with fewer than this many steps (noise floor)")
    args = parser.parse_args()

    if not FLOW_PATH.exists():
        sys.exit("no flow field (run build_flow_field.py first)")
    with np.load(FLOW_PATH) as d:
        hours = d["hours"]
        sum_dx, sum_dy, count = d["sum_dx"], d["sum_dy"], d["count"]
        cell = int(d["cell_size"])
        gw, gh = int(d["grid_w"]), int(d["grid_h"])

    args.out_dir.mkdir(parents=True, exist_ok=True)
    base = _base(args.map, gw, gh)
    # Scale arrows so the busiest consistent cell spans ~1.4 cells.
    mean_mag = np.hypot(
        np.divide(sum_dx, np.maximum(count, 1)),
        np.divide(sum_dy, np.maximum(count, 1)),
    )
    peak = max(1e-6, float(mean_mag.max()))
    arrow_scale = (cell * 1.4) / peak

    for i, hour in enumerate(hours):
        frame = base.copy()
        draw = ImageDraw.Draw(frame, "RGBA")
        cnt = count[i]
        for cy in range(cnt.shape[0]):
            for cx in range(cnt.shape[1]):
                c = cnt[cy, cx]
                if c < args.min_count:
                    continue
                mx = sum_dx[i, cy, cx] / c
                my = sum_dy[i, cy, cx] / c
                mag = math.hypot(mx, my)
                if mag < 0.3:  # essentially stationary cell — skip the clutter
                    continue
                px = cx * cell + cell // 2
                py = cy * cell + cell // 2
                # opacity by busyness (log), color by direction consistency.
                alpha = int(min(255, 60 + 40 * math.log1p(c)))
                _arrow(draw, px, py, mx * arrow_scale, my * arrow_scale, (200, 30, 30, alpha))
        label = f"{(int(hour) - 1) % 12 + 1}{'am' if hour < 12 else 'pm'}"
        out = args.out_dir / f"flow_{i:02d}_{int(hour):02d}h_{label}.png"
        frame.save(out)
        print(f"wrote {out} ({label})", file=sys.stderr)


if __name__ == "__main__":
    main()
