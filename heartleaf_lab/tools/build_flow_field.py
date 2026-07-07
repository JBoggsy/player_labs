#!/usr/bin/env python3
"""Build a per-game-hour movement flow field of OTHER players from replays.

Where the occupancy heatmap answers *where* players are, this answers *how they
move* — the standard technique for aggregating many trajectories into readable
motion: bin space into coarse cells and accumulate, per cell, the **mean
displacement vector** of every player step passing through it (a binned
mean-flow / vector field). Rendered as arrows, it shows the typical direction of
travel per region and per game-hour — e.g. the drift from gardens toward houses
as dinner nears.

(This is the discretized, aggregated form of the attraction/repulsion-field idea:
each cell's arrow is the average pull players feel there at that time of day.)

Method: for each replay, sample positions every `--stride` ticks; for each
consecutive pair of a player's main-map positions, add the displacement
(dx, dy) into the cell of the start point, bucketed by game-hour. Output stores
summed dx, dy, and a count per cell so the renderer can compute mean vectors and
magnitudes.

Output: `cady/mapdata/flow_field.npz` (hours, sum_dx, sum_dy, count, cell_size,
grid dims). Consumed by `tools/viz_flow_field.py`.

Usage:
    heartleaf_lab/tools/build_expand_replay.sh
    uv run python heartleaf_lab/tools/build_flow_field.py <artifacts_root>... [--stride 6]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

LAB_DIR = Path(__file__).resolve().parent.parent  # heartleaf_lab/
EXPANDER = LAB_DIR / "tools" / "bin" / "expand_replay"
OUT_PATH = LAB_DIR / "cady" / "mapdata" / "flow_field.npz"

CELL_SIZE = 24  # a bit coarser than occupancy — arrows read better sparser
GRID_W, GRID_H = 748, 941
GAMEPLAY_TICKS_PER_DAY = 2400
SCORE_SCREEN_TICKS = 240
FULL_DAY_TICKS = GAMEPLAY_TICKS_PER_DAY + SCORE_SCREEN_TICKS
DAY_START_MIN, DAY_STEP_COUNT, DAY_TOTAL_MIN = 480, 168, 840
HOURS = list(range(8, 22))
# Ignore huge jumps (day-reset teleport home, or a player entering/leaving a
# house) — those aren't walking movement and would corrupt the flow field.
MAX_STEP_PX = 60


def game_hour_for_tick(tick: int) -> int | None:
    day_tick = tick % FULL_DAY_TICKS
    if day_tick >= GAMEPLAY_TICKS_PER_DAY:
        return None
    step = min(DAY_STEP_COUNT, day_tick * DAY_STEP_COUNT // GAMEPLAY_TICKS_PER_DAY)
    return (DAY_START_MIN + step * (DAY_TOTAL_MIN // DAY_STEP_COUNT)) // 60


def _expand(replay: Path, stride: int):
    proc = subprocess.run(
        [str(EXPANDER), "--snapshot-every", str(stride), str(replay)],
        capture_output=True, text=True, check=True,
    )
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def build(roots: list[Path], subject_user: str, stride: int) -> None:
    cells_x = (GRID_W + CELL_SIZE - 1) // CELL_SIZE
    cells_y = (GRID_H + CELL_SIZE - 1) // CELL_SIZE
    hour_index = {h: i for i, h in enumerate(HOURS)}
    shape = (len(HOURS), cells_y, cells_x)
    sum_dx = np.zeros(shape, dtype=np.float64)
    sum_dy = np.zeros(shape, dtype=np.float64)
    count = np.zeros(shape, dtype=np.int64)

    replays = sorted(r for root in roots for r in root.glob("*/replay.json"))
    if not replays:
        sys.exit(f"no replays under {', '.join(map(str, roots))}")
    print(f"expanding {len(replays)} replays (stride {stride})…", file=sys.stderr)

    steps = 0
    for n, replay in enumerate(replays, 1):
        # prev[slot] = (tick, x, y) of that player's last main-map sample.
        prev: dict[int, tuple[int, int, int]] = {}
        try:
            for row in _expand(replay, stride):
                if row.get("type") != "tick":
                    continue
                tick = row["tick"]
                hour = game_hour_for_tick(tick)
                for p in row["players"]:
                    slot = p["slot"]
                    if p.get("user") == subject_user or p["map"] != 0:
                        prev.pop(slot, None)  # left the main map — break the chain
                        continue
                    x, y = p["x"], p["y"]
                    last = prev.get(slot)
                    prev[slot] = (tick, x, y)
                    if last is None or hour is None or hour not in hour_index:
                        continue
                    dx, dy = x - last[1], y - last[2]
                    if dx * dx + dy * dy > MAX_STEP_PX * MAX_STEP_PX:
                        continue  # teleport / house transition — not walking
                    hi = hour_index[hour]
                    cx = min(cells_x - 1, max(0, last[1] // CELL_SIZE))
                    cy = min(cells_y - 1, max(0, last[2] // CELL_SIZE))
                    sum_dx[hi, cy, cx] += dx
                    sum_dy[hi, cy, cx] += dy
                    count[hi, cy, cx] += 1
                    steps += 1
        except subprocess.CalledProcessError as exc:
            print(f"  skip {replay} ({exc})", file=sys.stderr)
            continue
        if n % 20 == 0:
            print(f"  {n}/{len(replays)} replays, {steps:,} steps", file=sys.stderr)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT_PATH, hours=np.array(HOURS, dtype=np.int32),
        sum_dx=sum_dx, sum_dy=sum_dy, count=count,
        cell_size=np.int32(CELL_SIZE), grid_w=np.int32(GRID_W), grid_h=np.int32(GRID_H),
    )
    print(f"wrote {OUT_PATH} — {len(HOURS)}h × {cells_y}×{cells_x}, {steps:,} steps",
          file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+")
    parser.add_argument("--subject-user", default="Cady")
    parser.add_argument("--stride", type=int, default=6,
                        help="ticks between samples (default 6 = 4Hz; enough to see walking)")
    args = parser.parse_args()
    if not EXPANDER.exists():
        sys.exit(f"expander not built: {EXPANDER}")
    build([Path(r) for r in args.roots], args.subject_user, args.stride)


if __name__ == "__main__":
    main()
