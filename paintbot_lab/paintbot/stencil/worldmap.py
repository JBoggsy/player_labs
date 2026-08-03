"""The episode-scoped world model, built ONLINE from the observation stream.

Paintbot maps are procedurally generated per episode (mapPath "gen": five size
classes, 2-team sides layouts or 4-team corners/plus layouts) and the generation
seed is never on the wire — so unlike beacon's offline-baked ``nav.npz``, every
map fact must come from what the init snapshot actually states:

  * the ``walkability map`` sprite — RGBA, alpha>0 = walkable, 1x map pixels
    (snappy raw-block compressed; decoded here with cramjam + numpy);
  * the ``game teams <n> map <w>x<h>`` marker — team count + exact map size;
  * the per-team ``endzone <color> <shape> <x0>,<y0> <x1>,<y1>`` markers;
  * heart pedestal positions, folded in from ``<color> flag planted`` sightings
    (pedestal hearts never fog, so these resolve on the first alive frame).

One ``WorldMap`` instance is built per episode and owned by the Belief — there
are deliberately NO module-level caches (beacon's ``lru_cache`` loaders were a
latent cross-episode bug under procgen; see the recon report). Everything the
policy knows about terrain flows through this object:

  * ``walkable`` — footprint-eroded 8px nav grid (a body fits in the cell);
  * ``wall`` — per-pixel wall mask for line-of-sight rays;
  * ``cover`` — walkable cells hugging a wall (peek-fire cover);
  * flow fields + route-distance fields to arbitrary goals, computed lazily via
    Dijkstra and cached per goal cell *on this instance*;
  * derived tactical anchors — per-color home/capture points, choke and rally
    lines on the home->center axis (fractions in config.py), spawn aim — which
    replace beacon's hand-authored POIs, CHOKE_X, BASE_FRONT_X, and battle plans.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import numpy as np

from paintbot.stencil.config import (
    CHOKE_FRACTION,
    AIM_BRADS_TURN,
    LIVES_PER_PLAYER,
    NAV_CELL,
    RALLY_FRACTION,
)

#: Neighbour table shared by flow fields, A*, and route distances (index -> dx,dy).
NEIGHBORS: tuple[tuple[int, int], ...] = (
    (-1, 0), (1, 0), (0, -1), (0, 1),
    (-1, -1), (-1, 1), (1, -1), (1, 1),
)

#: Player half-footprint in px (sim.nim PlayerHalf) — the erosion radius.
PLAYER_HALF = 6

_SQRT2 = math.sqrt(2)


@dataclass(frozen=True)
class Endzone:
    """One team's home capture region, verbatim from its endzone marker.

    ``shape`` is one of column/square/disc/corner/arm; the box is the inclusive
    bounding box in map pixels. ``contains`` implements the RULES.md membership
    rules (disc = inscribed circle; corner = the diagonal half toward the anchor;
    everything else = the full box — close enough for navigation anchors).
    """

    color: str
    shape: str
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def center(self) -> tuple[int, int]:
        return ((self.x0 + self.x1) // 2, (self.y0 + self.y1) // 2)

    def contains(self, point: tuple[int, int]) -> bool:
        x, y = point
        if not (self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1):
            return False
        if self.shape == "disc":
            cx, cy = self.center
            r = min(self.x1 - self.x0, self.y1 - self.y0) / 2
            return math.hypot(x - cx, y - cy) <= r
        return True


class WorldMap:
    """Terrain + derived tactical geometry for ONE episode's map."""

    def __init__(
        self,
        walkable_mask: np.ndarray,  # bool [H, W], True = walkable pixel
        teams: int,
        endzones: dict[str, Endzone],
    ) -> None:
        self.height, self.width = walkable_mask.shape
        self.teams = teams
        self.endzones = endzones
        self.center = (self.width // 2, self.height // 2)
        #: Per-pixel wall mask (True = wall) for line-of-sight rays.
        self.wall: np.ndarray = ~walkable_mask
        self.grid_w = max(1, self.width // NAV_CELL)
        self.grid_h = max(1, self.height // NAV_CELL)
        #: Footprint-eroded nav grid: a cell is walkable when a player body
        #: centred on the cell centre fits (no wall pixel within PLAYER_HALF).
        self.walkable: np.ndarray = self._erode(walkable_mask)
        #: Walkable cells adjacent (8-neighbourhood) to a non-walkable cell.
        self.cover: np.ndarray = self._cover_cells(self.walkable)
        #: Heart pedestal positions by color, folded in from planted-heart
        #: sightings (perception). Falls back to the endzone centre until seen.
        self.pedestals: dict[str, tuple[int, int]] = {}
        #: Lazy per-goal-cell caches, episode-scoped by construction.
        self._flow_fields: dict[tuple[int, int], np.ndarray] = {}
        self._route_fields: dict[tuple[int, int], np.ndarray] = {}

    # --- construction helpers ---------------------------------------------------

    def _erode(self, walkable_mask: np.ndarray) -> np.ndarray:
        """Nav grid from the pixel mask, eroded by the player footprint.

        Uses a summed-area table over the wall mask so each cell's footprint
        window test is O(1): a cell is walkable iff the (2*PLAYER_HALF+1)^2
        window around its centre contains zero wall pixels and lies on-map.
        """
        wall = self.wall.astype(np.int32)
        sat = np.zeros((self.height + 1, self.width + 1), dtype=np.int64)
        np.cumsum(np.cumsum(wall, axis=0), axis=1, out=sat[1:, 1:])

        grid = np.zeros((self.grid_h, self.grid_w), dtype=bool)
        half = PLAYER_HALF
        cys = np.arange(self.grid_h) * NAV_CELL + NAV_CELL // 2
        cxs = np.arange(self.grid_w) * NAV_CELL + NAV_CELL // 2
        y0 = cys - half
        y1 = cys + half
        x0 = cxs - half
        x1 = cxs + half
        on_map_y = (y0 >= 0) & (y1 < self.height)
        on_map_x = (x0 >= 0) & (x1 < self.width)
        y0c = np.clip(y0, 0, self.height - 1)
        y1c = np.clip(y1, 0, self.height - 1)
        x0c = np.clip(x0, 0, self.width - 1)
        x1c = np.clip(x1, 0, self.width - 1)
        # windowed wall counts via the SAT, vectorized over the full grid
        a = sat[np.ix_(y1c + 1, x1c + 1)]
        b = sat[np.ix_(y0c, x1c + 1)]
        c = sat[np.ix_(y1c + 1, x0c)]
        d = sat[np.ix_(y0c, x0c)]
        walls_in_window = a - b - c + d
        grid = (walls_in_window == 0) & on_map_y[:, None] & on_map_x[None, :]
        return grid

    @staticmethod
    def _cover_cells(walkable: np.ndarray) -> np.ndarray:
        """Walkable cells with at least one non-walkable 8-neighbour."""
        padded = np.pad(walkable, 1, constant_values=False)
        blocked_near = np.zeros_like(walkable)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                blocked_near |= ~padded[
                    1 + dy : 1 + dy + walkable.shape[0],
                    1 + dx : 1 + dx + walkable.shape[1],
                ]
        return walkable & blocked_near

    # --- cell math ---------------------------------------------------------------

    def cell_of(self, x: int, y: int) -> tuple[int, int]:
        return (
            min(max(x // NAV_CELL, 0), self.grid_w - 1),
            min(max(y // NAV_CELL, 0), self.grid_h - 1),
        )

    @staticmethod
    def cell_center(gx: int, gy: int) -> tuple[int, int]:
        return (gx * NAV_CELL + NAV_CELL // 2, gy * NAV_CELL + NAV_CELL // 2)

    def nearest_walkable(self, gx: int, gy: int) -> tuple[int, int]:
        if self.walkable[gy, gx]:
            return gx, gy
        for ring in range(1, max(self.grid_w, self.grid_h)):
            for dy in range(-ring, ring + 1):
                for dx in range(-ring, ring + 1):
                    nx, ny = gx + dx, gy + dy
                    if (
                        0 <= nx < self.grid_w
                        and 0 <= ny < self.grid_h
                        and self.walkable[ny, nx]
                    ):
                        return nx, ny
        return gx, gy

    # --- line of sight -----------------------------------------------------------

    def ray_clear(self, a: tuple[int, int], b: tuple[int, int], step: float = 2.0) -> bool:
        """True when the segment a->b crosses no wall pixel (sampled every ~step px)."""
        ax, ay = a
        bx, by = b
        length = math.hypot(bx - ax, by - ay)
        n = max(int(length / step), 1)
        t = np.linspace(0.0, 1.0, n + 1)
        xs = np.clip(np.round(ax + (bx - ax) * t).astype(np.intp), 0, self.width - 1)
        ys = np.clip(np.round(ay + (by - ay) * t).astype(np.intp), 0, self.height - 1)
        return not self.wall[ys, xs].any()

    def walkable_segment(self, start: tuple[int, int], end: tuple[int, int]) -> bool:
        """Whether a short straight movement keeps the full player footprint clear."""
        distance = math.hypot(end[0] - start[0], end[1] - start[1])
        samples = max(1, math.ceil(distance / 2))
        for index in range(samples + 1):
            t = index / samples
            x = round(start[0] + (end[0] - start[0]) * t)
            y = round(start[1] + (end[1] - start[1]) * t)
            x0, x1 = x - PLAYER_HALF, x + PLAYER_HALF
            y0, y1 = y - PLAYER_HALF, y + PLAYER_HALF
            if (
                x0 < 0
                or y0 < 0
                or x1 >= self.width
                or y1 >= self.height
                or self.wall[y0 : y1 + 1, x0 : x1 + 1].any()
            ):
                return False
        return True

    # --- flow fields + route distances (lazy Dijkstra per goal cell) --------------

    def _dijkstra(self, goal_cell: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
        """Distance field + next-hop field from every cell toward ``goal_cell``.

        Next-hop encoding matches beacon's baked fields: 0 = at goal/unreachable,
        else 1 + index into NEIGHBORS. One full Dijkstra costs O(cells log cells)
        — up to ~100k cells on a giant board, well under a second; computed once
        per goal per episode and cached on this instance.
        """
        gx, gy = self.nearest_walkable(*goal_cell)
        grid = self.walkable
        dist = np.full(grid.shape, np.inf, dtype=np.float64)
        hop = np.zeros(grid.shape, dtype=np.uint8)
        dist[gy, gx] = 0.0
        queue: list[tuple[float, int, int]] = [(0.0, gx, gy)]
        while queue:
            d, x, y = heapq.heappop(queue)
            if d > float(dist[y, x]):
                continue
            for i, (dx, dy) in enumerate(NEIGHBORS):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.grid_w and 0 <= ny < self.grid_h):
                    continue
                if not grid[ny, nx]:
                    continue
                if dx != 0 and dy != 0 and not (grid[y, nx] and grid[ny, x]):
                    continue  # no diagonal squeeze through a wall corner
                nd = d + (_SQRT2 if dx and dy else 1.0)
                if nd < float(dist[ny, nx]):
                    dist[ny, nx] = nd
                    # step from (nx,ny) BACK toward (x,y): the reverse neighbour
                    hop[ny, nx] = 1 + NEIGHBORS.index((-dx, -dy))
                    heapq.heappush(queue, (nd, nx, ny))
        return dist, hop

    def _fields_for(self, goal: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
        goal_cell = self.cell_of(*goal)
        if goal_cell not in self._flow_fields:
            dist, hop = self._dijkstra(goal_cell)
            self._route_fields[goal_cell] = dist
            self._flow_fields[goal_cell] = hop
        return self._route_fields[goal_cell], self._flow_fields[goal_cell]

    def flow_waypoint(self, goal: tuple[int, int], self_xy: tuple[int, int]) -> tuple[int, int]:
        """Next-hop waypoint toward ``goal`` from the cached flow field."""
        _dist, hop = self._fields_for(goal)
        gx, gy = self.nearest_walkable(*self.cell_of(*self_xy))
        code = int(hop[gy, gx])
        if code == 0:  # at goal (or unreachable) — steer straight at the target
            return self_xy
        dx, dy = NEIGHBORS[code - 1]
        return self.cell_center(gx + dx, gy + dy)

    def route_distance(self, start: tuple[int, int], goal: tuple[int, int]) -> float:
        """Shortest static-map walking distance in pixels between two map points."""
        dist, _hop = self._fields_for(goal)
        sx, sy = self.nearest_walkable(*self.cell_of(*start))
        return float(dist[sy, sx]) * NAV_CELL

    # --- cover -------------------------------------------------------------------

    def nearest_cover(self, px: int, py: int, max_cells: int = 6) -> tuple[int, int] | None:
        """Map-space centre of the nearest cover cell to (px, py), or None."""
        gx, gy = self.cell_of(px, py)
        if self.cover[gy, gx]:
            return self.cell_center(gx, gy)
        for ring in range(1, max_cells + 1):
            best = None
            best_d = 1e18
            for dy in range(-ring, ring + 1):
                for dx in range(-ring, ring + 1):
                    nx, ny = gx + dx, gy + dy
                    if (
                        0 <= nx < self.grid_w
                        and 0 <= ny < self.grid_h
                        and self.cover[ny, nx]
                    ):
                        d = dx * dx + dy * dy
                        if d < best_d:
                            best_d = d
                            best = self.cell_center(nx, ny)
            if best is not None:
                return best
        return None

    # --- derived tactical anchors (replace beacon's authored POIs/plans) -----------

    def home_center(self, color: str) -> tuple[int, int]:
        zone = self.endzones.get(color)
        return zone.center if zone is not None else self.center

    def pedestal(self, color: str) -> tuple[int, int]:
        """Where ``color``'s heart rests when planted (seen > endzone centre)."""
        return self.pedestals.get(color, self.home_center(color))

    def capture_point(self, color: str) -> tuple[int, int]:
        """The carry-home delivery target: a walkable point inside our endzone."""
        zone = self.endzones.get(color)
        if zone is None:
            return self.center
        cx, cy = zone.center
        gx, gy = self.nearest_walkable(*self.cell_of(cx, cy))
        return self.cell_center(gx, gy)

    def _axis_point(self, color: str, fraction: float) -> tuple[int, int]:
        """A point ``fraction`` of the way from home centre toward map centre."""
        hx, hy = self.home_center(color)
        cx, cy = self.center
        return (
            int(hx + (cx - hx) * fraction),
            int(hy + (cy - hy) * fraction),
        )

    def choke_point(self, color: str) -> tuple[int, int]:
        """The defender hold anchor on the home->center axis, snapped to cover."""
        base = self._axis_point(color, CHOKE_FRACTION)
        cover = self.nearest_cover(*base, max_cells=10)
        return cover if cover is not None else base

    def rally_point(self, color: str) -> tuple[int, int]:
        """The attacker staging anchor on the home->center axis."""
        return self._axis_point(color, RALLY_FRACTION)

    def past_rally(self, color: str, point: tuple[int, int]) -> bool:
        """Whether ``point`` is committed beyond our rally line (toward center)."""
        hx, hy = self.home_center(color)
        cx, cy = self.center
        ax, ay = cx - hx, cy - hy
        norm2 = ax * ax + ay * ay
        if norm2 == 0:
            return False
        t = ((point[0] - hx) * ax + (point[1] - hy) * ay) / norm2
        return t > RALLY_FRACTION

    def home_step(self, color: str, pos: tuple[int, int], step: int) -> tuple[int, int]:
        """``pos`` stepped ``step`` px along the axis toward our home centre."""
        hx, hy = self.home_center(color)
        dx, dy = hx - pos[0], hy - pos[1]
        d = math.hypot(dx, dy)
        if d < 1:
            return pos
        return (
            min(max(int(pos[0] + dx / d * step), 12), self.width - 13),
            min(max(int(pos[1] + dy / d * step), 12), self.height - 13),
        )

    def inside_base(self, color: str, point: tuple[int, int], margin: int = 80) -> bool:
        """Whether ``point`` is in/near ``color``'s home region (endzone + margin)."""
        zone = self.endzones.get(color)
        if zone is None:
            return False
        return (
            zone.x0 - margin <= point[0] <= zone.x1 + margin
            and zone.y0 - margin <= point[1] <= zone.y1 + margin
        )

    def spawn_aim(self, color: str) -> int:
        """Spawn-facing estimate: brads from home centre toward map centre."""
        hx, hy = self.home_center(color)
        cx, cy = self.center
        if hx == cx and hy == cy:
            return 0
        ang = math.atan2(-(cy - hy), cx - hx)
        return round(ang / (2 * math.pi) * AIM_BRADS_TURN) % AIM_BRADS_TURN

    @property
    def grenade_max_range(self) -> int:
        """sim.nim GrenadeMaxRange = MapWidth div 5 (also the shout radius)."""
        return self.width // 5

    def seats_per_team(self) -> int:
        """Best-effort roster inference: the wire never states the muster.

        2-team boards always seat 8 per team (ctf default / paintbot 2v2). The
        4-team 16-seat variant (4ffa) seats 4; the 32-seat 4ffa8 seats 8 and is
        always on a giant (>=2000px) generated board.
        """
        if self.teams == 2:
            return 8
        return 8 if self.width >= 2000 else 4

    def team_total_lives(self) -> int:
        return self.seats_per_team() * LIVES_PER_PLAYER

    def signature(self) -> tuple[int, int, int]:
        """Cheap identity for map-change detection across games in one process."""
        return (self.width, self.height, self.teams)


__all__ = ["Endzone", "NEIGHBORS", "PLAYER_HALF", "WorldMap"]
