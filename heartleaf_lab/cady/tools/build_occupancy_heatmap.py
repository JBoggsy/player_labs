#!/usr/bin/env python3
"""Build a per-game-hour occupancy heatmap of OTHER players from replays.

Cady's guest problem: during the invite window she only knows about on-screen
gnomes, and when her screen is empty she walks to the map center blindly. This
tool learns, from many past games, *where players actually are at each hour of
the day*, so she can head to the empirically-crowded spots instead of guessing.

Method: expand every replay (via the `expand_replay` binary), and for every
per-tick position of every player OTHER than the subject, accumulate a count
into a coarse grid cell, bucketed by **game-hour** (8 AM … 9 PM). Positions are
main-map foot pixels (the same frame as the baked walk grid), so a cell maps
directly to a world point Cady can navigate to.

Output: `cady/mapdata/occupancy.npz` — `hours` (list of hour labels) and a
`counts` array of shape (n_hours, cells_y, cells_x), plus the cell size and grid
dims, consumed by `cady/occupancy.py`.

Usage:
    heartleaf_lab/tools/build_expand_replay.sh          # build the expander once
    uv run python heartleaf_lab/tools/build_occupancy_heatmap.py \
        /path/to/artifacts_root ...                     # dirs containing */replay.json

Game-hour from a tick (league day = 2400 gameplay + 240 score ticks = 2640):
    day_tick   = tick % 2640                 # position within the current day
    if day_tick >= 2400: score screen        # skip (everyone teleported home)
    game_min   = 480 + 5*floor(day_tick*168/2400)   # heartleaf currentDayMinutes
    hour       = game_min // 60              # 8 .. 21
See docs/heartleaf-gameplay.md "Exact timing".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

LAB_DIR = Path(__file__).resolve().parent.parent.parent  # heartleaf_lab/
EXPANDER = LAB_DIR / "tools" / "bin" / "expand_replay"
OUT_PATH = Path(__file__).resolve().parent.parent / "mapdata" / "occupancy.npz"

# Coarse cells: 16px blocks smooth the occupancy and are plenty to steer a patrol.
CELL_SIZE = 16
GRID_W, GRID_H = 748, 941  # main-map pixel dims (matches the baked walk grid)

# League day timing (see module docstring + docs/heartleaf-gameplay.md).
GAMEPLAY_TICKS_PER_DAY = 2400
SCORE_SCREEN_TICKS = 240
FULL_DAY_TICKS = GAMEPLAY_TICKS_PER_DAY + SCORE_SCREEN_TICKS
DAY_START_MIN = 480  # 8 AM
DAY_STEP_COUNT = 168
DAY_TOTAL_MIN = 840
HOURS = list(range(8, 22))  # 8 AM .. 9 PM (inclusive labels)


def game_hour_for_tick(tick: int) -> int | None:
    """Game-hour (8..21) for a replay tick, or None during the score screen."""
    day_tick = tick % FULL_DAY_TICKS
    if day_tick >= GAMEPLAY_TICKS_PER_DAY:
        return None  # end-of-day score screen: everyone teleported home, skip
    step = min(DAY_STEP_COUNT, day_tick * DAY_STEP_COUNT // GAMEPLAY_TICKS_PER_DAY)
    game_min = DAY_START_MIN + step * (DAY_TOTAL_MIN // DAY_STEP_COUNT)
    return game_min // 60


def _expand(replay: Path):
    """Yield decoded JSONL rows from expanding one replay."""
    proc = subprocess.run(
        [str(EXPANDER), str(replay)],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def build(roots: list[Path], subject_user: str) -> None:
    cells_x = (GRID_W + CELL_SIZE - 1) // CELL_SIZE
    cells_y = (GRID_H + CELL_SIZE - 1) // CELL_SIZE
    hour_index = {h: i for i, h in enumerate(HOURS)}
    counts = np.zeros((len(HOURS), cells_y, cells_x), dtype=np.int64)

    replays = sorted(r for root in roots for r in root.glob("*/replay.json"))
    if not replays:
        sys.exit(f"no replays found under {', '.join(str(r) for r in roots)}")
    print(f"expanding {len(replays)} replays…", file=sys.stderr)

    samples = 0
    for n, replay in enumerate(replays, 1):
        try:
            for row in _expand(replay):
                if row.get("type") != "tick":
                    continue
                hour = game_hour_for_tick(row["tick"])
                if hour is None or hour not in hour_index:
                    continue
                hi = hour_index[hour]
                for p in row["players"]:
                    # Only OTHER players, only on the main map (invite happens there).
                    if p.get("user") == subject_user or p["map"] != 0:
                        continue
                    cx = min(cells_x - 1, max(0, p["x"] // CELL_SIZE))
                    cy = min(cells_y - 1, max(0, p["y"] // CELL_SIZE))
                    counts[hi, cy, cx] += 1
                    samples += 1
        except subprocess.CalledProcessError as exc:
            print(f"  skip {replay} (expander failed: {exc})", file=sys.stderr)
            continue
        if n % 20 == 0:
            print(f"  {n}/{len(replays)} replays, {samples:,} samples", file=sys.stderr)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT_PATH,
        hours=np.array(HOURS, dtype=np.int32),
        counts=counts,
        cell_size=np.int32(CELL_SIZE),
        grid_w=np.int32(GRID_W),
        grid_h=np.int32(GRID_H),
    )
    print(
        f"wrote {OUT_PATH} — {len(HOURS)} hours × {cells_y}×{cells_x} cells, "
        f"{samples:,} samples from {len(replays)} replays",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", help="dirs containing */replay.json")
    parser.add_argument(
        "--subject-user",
        default="Cady",
        help="username to EXCLUDE (our own player; default Cady)",
    )
    args = parser.parse_args()
    if not EXPANDER.exists():
        sys.exit(f"expander not built: {EXPANDER} (run tools/build_expand_replay.sh)")
    build([Path(r) for r in args.roots], args.subject_user)


if __name__ == "__main__":
    main()
