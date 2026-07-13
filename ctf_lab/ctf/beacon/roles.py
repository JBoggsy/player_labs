"""Seat-based role assignment (v2).

CTF games are decided by wipe, not capture (TENTATIVE_LESSONS), so survival on our
own turf wins. Seats 0..DEFENDER_COUNT-1 defend (hold cover between our flag and our
edge, spread across a y-band); the rest attack (push the enemy flag). Role is fixed by
seat for the whole episode, so the split is deterministic and needs no coordination —
which matters because there is no team radio.
"""

from __future__ import annotations

from ctf.beacon import mapdata
from ctf.beacon.config import CHOKE_X, DEFENDER_COUNT, HOLD_Y_MAX, HOLD_Y_MIN
from ctf.beacon.types import Role, Team


def role_for_seat(seat: int) -> Role:
    return "defender" if seat < DEFENDER_COUNT else "attacker"


def hold_point_for_seat(team: Team, seat: int) -> tuple[int, int]:
    """A distinct hold cell for defender ``seat`` on our own turf, snapped to COVER.

    Defenders spread across a y-band on the choke x-line, then snap to the nearest
    cover cell (a walkable cell hugging a wall) so they peek-fire from behind an
    obstacle instead of standing in the open — the baseline's edge (v3).
    """
    n = max(1, DEFENDER_COUNT)
    if n == 1:
        y = (HOLD_Y_MIN + HOLD_Y_MAX) // 2
    else:
        y = HOLD_Y_MIN + (HOLD_Y_MAX - HOLD_Y_MIN) * seat // (n - 1)
    base = (CHOKE_X[team], y)
    cover = mapdata.nearest_cover(*base)
    return cover if cover is not None else base


__all__ = ["hold_point_for_seat", "role_for_seat"]
