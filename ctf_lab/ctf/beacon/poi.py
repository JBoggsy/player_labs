"""The canonical points/areas-of-interest map — the shared field language.

Loads ``mapdata/points_of_interest.json`` (human-curated in tools/poi_editor.html;
the same file the plan editor, plan renderer, and battle plans reference by name)
and exposes it to strategy code. This is the single source of truth for named
field locations: humans discuss plans in these names, plans store them, and
beacon resolves them here — when the map is re-curated, everything moves together.

Mirroring: the map is authored red-side (mirror line x = 617). ``resolve(loc,
team)`` flips x for blue, so strategy code can use red-frame names for both
teams. Name-based conveniences (``point("red_rally_top", team)``) additionally
swap red_/blue_ prefixes for blue, so "my rally" reads naturally either side.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ctf.beacon.types import Team

POI_PATH = Path(__file__).resolve().parent / "mapdata" / "points_of_interest.json"
MAP_W = 1235


@dataclass(frozen=True)
class Area:
    name: str
    cx: int
    cy: int
    w: int
    h: int
    angle: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.cx, self.cy)

    def contains(self, x: int, y: int) -> bool:
        """Point-in-rotated-rect (angle degrees CCW, matching the editor)."""
        import math

        c = math.cos(-math.radians(self.angle))
        s = math.sin(-math.radians(self.angle))
        dx, dy = x - self.cx, y - self.cy
        lx, ly = dx * c - dy * s, dx * s + dy * c
        return abs(lx) <= self.w / 2 and abs(ly) <= self.h / 2


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, tuple[int, int]], dict[str, Area]]:
    doc = json.loads(POI_PATH.read_text())
    points = {p["name"]: (p["x"], p["y"]) for p in doc.get("points", [])}
    areas = {
        a["name"]: Area(a["name"], a["cx"], a["cy"], a["w"], a["h"], a.get("angle", 0))
        for a in doc.get("areas", [])
    }
    return points, areas


def _swap_side(name: str) -> str:
    if "red_" in name:
        return name.replace("red_", "blue_")
    if "blue_" in name:
        return name.replace("blue_", "red_")
    return name


def _mirror(xy: tuple[int, int]) -> tuple[int, int]:
    return (MAP_W - 1 - xy[0], xy[1])


def point(name: str, team: Team = "red") -> tuple[int, int]:
    """A named point (or an area's center) in ``team``'s frame.

    Red-frame names; for blue the red_/blue_ prefix swaps AND x mirrors, so
    ``point("red_rally_top", "blue")`` = blue's own top rally. Raises KeyError
    on an unknown name (a plan/strategy referencing a renamed POI should fail
    loudly, not drift silently).
    """
    points, areas = _load()
    lookup = name if team == "red" else _swap_side(name)
    if lookup in points:
        return points[lookup]
    if lookup in areas:
        return areas[lookup].center
    # The swapped twin may not exist (side-neutral or unpaired name): mirror
    # the red-frame geometry instead.
    if name in points:
        return points[name] if team == "red" else _mirror(points[name])
    if name in areas:
        return areas[name].center if team == "red" else _mirror(areas[name].center)
    raise KeyError(f"unknown POI: {name!r}")


def area(name: str, team: Team = "red") -> Area:
    """A named area in ``team``'s frame (prefix-swapped for blue; KeyError if
    the twin doesn't exist — mirrored-geometry fallback only applies to centers)."""
    _points, areas = _load()
    lookup = name if team == "red" else _swap_side(name)
    if lookup in areas:
        return areas[lookup]
    raise KeyError(f"unknown POI area: {name!r}")


def resolve(loc, team: Team = "red") -> tuple[int, int] | None:
    """A plan location -> map point in ``team``'s frame.

    ``loc`` is a POI name (str) or a raw ``{"x":…, "y":…}`` dict (battle-plan
    schema). Raw coords are authored red-frame and mirror for blue. None if
    a name is unknown (plans may reference not-yet-created POIs; the caller
    decides whether that's fatal).
    """
    if isinstance(loc, dict):
        xy = (int(loc["x"]), int(loc["y"]))
        return xy if team == "red" else _mirror(xy)
    if isinstance(loc, str):
        try:
            return point(loc, team)
        except KeyError:
            return None
    return None


__all__ = ["Area", "area", "point", "resolve", "POI_PATH"]
