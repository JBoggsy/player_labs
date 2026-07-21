"""Offline nav bake for the CTF arena.

The CTF arena is **static and seed-independent** — its geometry is a compile-time
constant in the game's ``src/ctf/sim.nim`` (``arenaCtfMap`` / ``isArenaWall``), with
no RNG. So the whole navigation graph can be solved once, offline, and shipped in the
player image. This tool ports the wall function faithfully, erodes it by the player
footprint, and precomputes:

  * ``walkable``  — an 8px-cell boolean grid (True = a body fits here)
  * ``flow_steal`` / ``flow_home`` — for each team, a next-hop flow field (Dijkstra
    from the goal outward) that turns "go to the enemy pedestal / my capture zone"
    into an O(1) grid lookup at run time.

Everything here mirrors named constants in ``sim.nim`` at the pinned ``CTF_REF`` (see
``ctf_lab/tools/build_expand_replay.sh``); if the deployed arena ever changes, re-run
this. The runtime (``beacon.nav``) only ever *reads* the baked artifact.

Run:  python -m ctf.beacon.tools.bake_map          # writes beacon/mapdata/nav.npz
      python -m ctf.beacon.tools.bake_map --ascii  # also print an ASCII sanity map
"""

from __future__ import annotations

import argparse
import heapq
import math
from pathlib import Path

import numpy as np

# --- Arena constants (verbatim from src/ctf/sim.nim @ CTF_REF 5450c64; geometry
# verified byte-identical to the original 761c098 port on 2026-07-14) --------------
MAP_W = 1235
MAP_H = 659
CENTER_X = MAP_W // 2  # 617
CENTER_Y = MAP_H // 2  # 329

ARENA_BORDER = 10
ARENA_FLAG_RING = 70
ARENA_CAPTURE_CLEAR = 210
ARENA_SPAWN_CLEAR_W = 70
ARENA_SPAWN_CLEAR_H = 130
PLAYER_HALF = 6  # solid player footprint half-extent, px (sim.nim PlayerHalf)

NAV_CELL = 8
GRID_W = (MAP_W + NAV_CELL - 1) // NAV_CELL  # 155
GRID_H = (MAP_H + NAV_CELL - 1) // NAV_CELL  # 83

# Static pedestals (flagHome in sim.nim: teamHomeX = center ± center*7/10).
PEDESTAL = {"red": (186, 329), "blue": (1049, 329)}
# A point deep in each team's capture zone to aim the "home" flow field at.
HOME_DEEP = {"red": (150, 329), "blue": (MAP_W - 1 - 150, 329)}

# Obstacle shapes on the LEFT half; the arena mirrors each across x = center.
# (kind, params) — verbatim from ArenaLeftObstacles.
_RECTS = [  # (x, y, w, h)
    (268, 10, 18, 62), (268, 108, 18, 60), (268, 204, 18, 60), (268, 300, 18, 59),
    (268, 395, 18, 60), (268, 491, 18, 60), (268, 587, 18, 62),
    (556, 24, 18, 66), (556, 569, 18, 66),
]
_DIAMONDS = [  # (cx, cy, radius)
    (349, 90, 28), (349, 186, 28), (349, 282, 28), (349, 376, 28), (349, 472, 28),
    (349, 568, 28),
    (565, 156, 30), (565, 252, 30), (565, 406, 30), (565, 502, 30),
]
_DISCS = [  # (cx, cy, radius)
    (421, 66, 28), (421, 162, 28), (421, 258, 28), (421, 400, 28), (421, 496, 28),
    (421, 592, 28),
]
_DIAGONALS = [  # (x0, y0, x1, y1, thickness)
    (479, 86, 507, 114, 12), (507, 114, 479, 142, 12), (507, 182, 479, 210, 12),
    (479, 210, 507, 238, 12), (479, 276, 506, 303, 12), (506, 303, 479, 330, 12),
    (479, 329, 506, 356, 12), (506, 356, 479, 383, 12), (507, 421, 479, 449, 12),
    (479, 449, 507, 477, 12), (479, 517, 507, 545, 12), (507, 545, 479, 573, 12),
]


def _mirror_rect(x, y, w, h):
    return (MAP_W - x - w, y, w, h)


def _in_rect(x, y, r):
    rx, ry, rw, rh = r
    return rx <= x < rx + rw and ry <= y < ry + rh


def _in_disc(x, y, cx, cy, radius):
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius


def _in_diamond(x, y, cx, cy, radius):
    return abs(x - cx) + abs(y - cy) <= radius


def _in_diagonal(x, y, x0, y0, x1, y1, thickness):
    # Integer point-to-segment distance test, matching sim.nim's inShape.
    half = thickness // 2 + 1
    if x < min(x0, x1) - half or x > max(x0, x1) + half:
        return False
    if y < min(y0, y1) - half or y > max(y0, y1) + half:
        return False
    vx, vy = x1 - x0, y1 - y0
    wx, wy = x - x0, y - y0
    len2 = vx * vx + vy * vy
    t = max(0, min(wx * vx + wy * vy, len2))
    dx = wx * len2 - t * vx
    dy = wy * len2 - t * vy
    return dx * dx + dy * dy <= thickness * thickness * len2 * len2 // 4


def _all_obstacles():
    """Left-half shapes plus their x-mirror, as callables over (x, y)."""
    shapes = []
    for r in _RECTS:
        shapes.append((_in_rect, (r,)))
        shapes.append((_in_rect, (_mirror_rect(*r),)))
    for cx, cy, rad in _DIAMONDS:
        shapes.append((_in_diamond, (cx, cy, rad)))
        shapes.append((_in_diamond, (MAP_W - 1 - cx, cy, rad)))
    for cx, cy, rad in _DISCS:
        shapes.append((_in_disc, (cx, cy, rad)))
        shapes.append((_in_disc, (MAP_W - 1 - cx, cy, rad)))
    for x0, y0, x1, y1, th in _DIAGONALS:
        shapes.append((_in_diagonal, (x0, y0, x1, y1, th)))
        shapes.append((_in_diagonal, (MAP_W - 1 - x0, y0, MAP_W - 1 - x1, y1, th)))
    return shapes


def _protected_floor(x, y):
    """Regions kept walkable regardless of obstacles (isProtectedFloor)."""
    if x < ARENA_CAPTURE_CLEAR or x >= MAP_W - ARENA_CAPTURE_CLEAR:
        return True
    if (x - CENTER_X) ** 2 + (y - CENTER_Y) ** 2 <= ARENA_FLAG_RING ** 2:
        return True
    for home_x in (186, 1049):
        if abs(x - home_x) <= ARENA_SPAWN_CLEAR_W and abs(y - CENTER_Y) <= ARENA_SPAWN_CLEAR_H:
            return True
    return False


def build_wall_mask() -> np.ndarray:
    """Per-pixel wall mask (True = wall), matching sim.nim isArenaWall exactly."""
    wall = np.zeros((MAP_H, MAP_W), dtype=bool)
    shapes = _all_obstacles()
    for y in range(MAP_H):
        for x in range(MAP_W):
            if x < ARENA_BORDER or y < ARENA_BORDER or x >= MAP_W - ARENA_BORDER or y >= MAP_H - ARENA_BORDER:
                wall[y, x] = True
                continue
            if _protected_floor(x, y):
                continue
            for fn, params in shapes:
                if fn(x, y, *params):
                    wall[y, x] = True
                    break
    return wall


def build_walkable_grid(wall_px: np.ndarray) -> np.ndarray:
    """Erode by the player footprint and downsample to the 8px nav grid.

    A grid cell is walkable iff a full PlayerHalf-box centred at the cell's centre
    pixel is entirely wall-free — the same clearance test the sim uses for movement.
    """
    walk_px = ~wall_px
    grid = np.zeros((GRID_H, GRID_W), dtype=bool)
    for gy in range(GRID_H):
        for gx in range(GRID_W):
            cx = min(gx * NAV_CELL + NAV_CELL // 2, MAP_W - 1)
            cy = min(gy * NAV_CELL + NAV_CELL // 2, MAP_H - 1)
            x0, x1 = cx - PLAYER_HALF, cx + PLAYER_HALF
            y0, y1 = cy - PLAYER_HALF, cy + PLAYER_HALF
            if x0 < 0 or y0 < 0 or x1 >= MAP_W or y1 >= MAP_H:
                continue
            if walk_px[y0 : y1 + 1, x0 : x1 + 1].all():
                grid[gy, gx] = True
    return grid


# 8-connected neighbours; diagonal cost sqrt(2), straight cost 1.
_NEIGHBORS = [
    (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
    (-1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)),
    (1, -1, math.sqrt(2)), (1, 1, math.sqrt(2)),
]


def _cell_of(px: int, py: int) -> tuple[int, int]:
    return (min(px // NAV_CELL, GRID_W - 1), min(py // NAV_CELL, GRID_H - 1))


def _nearest_walkable(grid: np.ndarray, gx: int, gy: int) -> tuple[int, int]:
    if grid[gy, gx]:
        return gx, gy
    for ring in range(1, max(GRID_W, GRID_H)):
        for dy in range(-ring, ring + 1):
            for dx in range(-ring, ring + 1):
                nx, ny = gx + dx, gy + dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H and grid[ny, nx]:
                    return nx, ny
    raise RuntimeError("no walkable cell found")


def build_flow_field(grid: np.ndarray, goal_px: tuple[int, int]) -> np.ndarray:
    """Dijkstra outward from ``goal_px``; store the next-hop direction per cell.

    Encoding (uint8): 0 = unreachable/goal, else 1 + neighbour-index into
    _NEIGHBORS — the runtime steps to that neighbour to move one hop toward the goal.
    """
    gx, gy = _nearest_walkable(grid, *_cell_of(*goal_px))
    INF = float("inf")
    dist = np.full((GRID_H, GRID_W), INF)
    nexthop = np.zeros((GRID_H, GRID_W), dtype=np.uint8)
    dist[gy, gx] = 0.0
    pq = [(0.0, gx, gy)]
    while pq:
        d, x, y = heapq.heappop(pq)
        if d > dist[y, x]:
            continue
        for i, (dx, dy, cost) in enumerate(_NEIGHBORS):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H) or not grid[ny, nx]:
                continue
            # Disallow diagonal squeezes through wall corners.
            if dx != 0 and dy != 0 and not (grid[y, nx] and grid[ny, x]):
                continue
            nd = d + cost
            if nd < dist[ny, nx]:
                dist[ny, nx] = nd
                # From (nx,ny), the hop back toward the goal is the reverse of (dx,dy).
                back = _NEIGHBORS.index((-dx, -dy, cost))
                nexthop[ny, nx] = back + 1
                heapq.heappush(pq, (nd, nx, ny))
    return nexthop


def build_cover_grid(grid: np.ndarray) -> np.ndarray:
    """Cover cells: walkable cells orthogonally adjacent to a non-walkable cell.

    A player on a cover cell has a wall on at least one side to peek-fire from and
    duck behind — the baseline's edge. Used to snap hold/staging points off the open.
    """
    cover = np.zeros_like(grid)
    for gy in range(GRID_H):
        for gx in range(GRID_W):
            if not grid[gy, gx]:
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = gx + dx, gy + dy
                if not (0 <= nx < GRID_W and 0 <= ny < GRID_H) or not grid[ny, nx]:
                    cover[gy, gx] = True
                    break
    return cover


def bake() -> dict[str, np.ndarray]:
    wall_px = build_wall_mask()
    grid = build_walkable_grid(wall_px)
    # The raw per-pixel mask ships too: line-of-sight rays (peek/duck micro) must
    # test true walls, not the footprint-eroded grid (sight has no 6px body).
    fields = {"wall": wall_px, "walkable": grid, "cover": build_cover_grid(grid)}
    for team in ("red", "blue"):
        enemy = "blue" if team == "red" else "red"
        fields[f"flow_steal_{team}"] = build_flow_field(grid, PEDESTAL[enemy])
        fields[f"flow_home_{team}"] = build_flow_field(grid, HOME_DEEP[team])
    return fields


def _ascii(grid: np.ndarray) -> str:
    step_y = max(1, GRID_H // 40)
    step_x = max(1, GRID_W // 100)
    lines = []
    for gy in range(0, GRID_H, step_y):
        lines.append("".join("." if grid[gy, gx] else "#" for gx in range(0, GRID_W, step_x)))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Bake the CTF nav grid + flow fields.")
    ap.add_argument("--ascii", action="store_true", help="print an ASCII sanity map")
    ap.add_argument("--out", default=None, help="output .npz (default: beacon/mapdata/nav.npz)")
    args = ap.parse_args()

    fields = bake()
    grid = fields["walkable"]
    walk_frac = grid.mean()
    cover_n = int(fields["cover"].sum())
    print(f"grid {GRID_W}x{GRID_H} cells @ {NAV_CELL}px  walkable={walk_frac:.1%}  cover_cells={cover_n}")
    for team in ("red", "blue"):
        for kind in ("steal", "home"):
            f = fields[f"flow_{kind}_{team}"]
            reached = ((f > 0).sum() + 1)  # +1 for the goal cell itself
            print(f"  flow_{kind}_{team}: {reached}/{int(grid.sum())} walkable cells routed")

    out = Path(args.out) if args.out else Path(__file__).resolve().parents[1] / "mapdata" / "nav.npz"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **fields)
    print(f"wrote {out} ({out.stat().st_size} bytes)")

    if args.ascii:
        print(_ascii(grid))


if __name__ == "__main__":
    main()
