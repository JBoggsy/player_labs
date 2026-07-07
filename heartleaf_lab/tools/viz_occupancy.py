#!/usr/bin/env python3
"""Render the baked occupancy heatmap as one image per game-hour, over the map.

Overlays each hour's other-player occupancy (from `cady/mapdata/occupancy.npz`,
built by `build_occupancy_heatmap.py`) on the real Heartleaf map art, so you can
see where villagers actually cluster through the day — and sanity-check what
Cady's invite patrol is steering toward.

Background: the real game map PNG (export it once with the game-repo tool
`tools/export_map_png.nim` → e.g. `heartleaf_map.png`). If it's missing, falls
back to the baked walkability grid so the script still works.

Usage:
    uv run python heartleaf_lab/tools/viz_occupancy.py \
        --map heartleaf_map.png --out-dir /tmp/occ
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cady import occupancy  # noqa: E402
from cady.mapdata import WALK_GRID  # noqa: E402

_WALKABLE_RGB = (238, 236, 230)
_WALL_RGB = (60, 66, 74)


def _base_image(map_png: Path | None, grid_w: int, grid_h: int) -> Image.Image:
    """Real map art if available, else the walkability grid as paper/ink."""
    if map_png is not None and map_png.exists():
        img = Image.open(map_png).convert("RGB")
        if img.size != (grid_w, grid_h):
            img = img.resize((grid_w, grid_h), Image.NEAREST)
        return img
    grid = np.asarray(WALK_GRID, dtype=bool)
    rgb = np.where(grid[..., None], _WALKABLE_RGB, _WALL_RGB).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


def _heat_overlay(grid: np.ndarray, cell: int, size: tuple[int, int]) -> Image.Image:
    """A translucent red heat layer for one hour's cell counts (upscaled)."""
    norm = grid.astype(np.float64)
    peak = norm.max()
    if peak > 0:
        # sqrt for perceptual spread so mid-density cells stay visible.
        norm = np.sqrt(norm / peak)
    alpha = (norm * 200).astype(np.uint8)  # 0..200 alpha
    h, w = grid.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., 0] = 255           # red
    rgba[..., 1] = (80 * (1 - norm)).astype(np.uint8)  # toward orange at peaks
    rgba[..., 3] = alpha
    layer = Image.fromarray(rgba, mode="RGBA")
    return layer.resize((w * cell, h * cell), Image.NEAREST).crop((0, 0, size[0], size[1]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=None,
                        help="real Heartleaf map PNG (from export_map_png.nim)")
    parser.add_argument("--out-dir", type=Path, default=Path("occupancy_viz"))
    parser.add_argument("--scale", type=int, default=1, help="integer upscale")
    args = parser.parse_args()

    heatmap = occupancy._load()
    if heatmap is None:
        sys.exit("no baked heatmap (run build_occupancy_heatmap.py first)")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    base = _base_image(args.map, heatmap.grid_w, heatmap.grid_h)

    for i, hour in enumerate(heatmap.hours):
        grid = heatmap.counts[i]
        overlay = _heat_overlay(grid, heatmap.cell_size, base.size)
        frame = base.convert("RGBA")
        frame.alpha_composite(overlay)
        frame = frame.convert("RGB")
        if args.scale > 1:
            frame = frame.resize((frame.width * args.scale, frame.height * args.scale), Image.NEAREST)
        label = f"{(hour - 1) % 12 + 1}{'am' if hour < 12 else 'pm'}"  # 8->8am, 15->3pm
        out = args.out_dir / f"occ_{i:02d}_{int(hour):02d}h_{label}.png"
        frame.save(out)
        print(f"wrote {out}  (hour {int(hour)} = {label}, {int(grid.sum()):,} samples)", file=sys.stderr)


if __name__ == "__main__":
    main()
