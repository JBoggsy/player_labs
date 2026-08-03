"""Seat-based role assignment, generalized to variable rosters.

The beacon lesson holds: games are decided by wipe/elimination at least as often
as by capture, so a defensive contingent that holds cover on our own turf wins
lives. Seats 0..N-1 defend; the rest attack. Paintbot rosters vary (8 seats per
team on 2-team boards and 4ffa8; 4 on 4ffa), so the defender count scales with
the actual seat count instead of assuming 8.

Hold points are DERIVED from the episode map (worldmap.choke_point on the
home->center axis, spread perpendicular to it, snapped to cover) — beacon's
hand-authored CHOKE_X/HOLD_Y band does not survive procgen.
"""

from __future__ import annotations

import math

from paintbot.stencil.config import DEFENDER_COUNT
from paintbot.stencil.types import Role, Team
from paintbot.stencil.worldmap import WorldMap


def defender_count(seats: int) -> int:
    """Scale the 3-of-8 defender split to the actual per-team seat count."""
    return max(1, round(DEFENDER_COUNT * seats / 8))


def role_for_seat(seat: int, seats: int) -> Role:
    return "defender" if seat < defender_count(seats) else "attacker"


def hold_point_for_seat(wm: WorldMap, team: Team, seat: int, seats: int) -> tuple[int, int]:
    """A distinct hold cell for defender ``seat``, snapped to COVER.

    Defenders spread along the axis PERPENDICULAR to home->center at the choke
    anchor, then snap to the nearest cover cell so they peek-fire from behind an
    obstacle instead of standing in the open.
    """
    n = max(1, defender_count(seats))
    base = wm.choke_point(team)
    hx, hy = wm.home_center(team)
    cx, cy = wm.center
    ax, ay = cx - hx, cy - hy
    norm = math.hypot(ax, ay) or 1.0
    # unit perpendicular to the home->center axis
    px, py = -ay / norm, ax / norm
    #: Spread band scales with the map (about a quarter of the smaller dimension).
    band = min(wm.width, wm.height) // 4
    if n == 1:
        offset = 0.0
    else:
        offset = -band + 2 * band * seat / (n - 1)
    point = (
        min(max(int(base[0] + px * offset), 12), wm.width - 13),
        min(max(int(base[1] + py * offset), 12), wm.height - 13),
    )
    cover = wm.nearest_cover(*point, max_cells=10)
    return cover if cover is not None else point


__all__ = ["defender_count", "hold_point_for_seat", "role_for_seat"]
