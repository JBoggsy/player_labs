"""The declared world model — topology knowledge that cannot be derived from frames.

This is DATA, deliberately mirroring the authored rotation tables' philosophy: general
code, curated data. Grow it by adding entries, never by changing navigation logic.
Every coordinate is source-backed (game repo dungeon defs, authored profiles, or our
own hosted traces) and carries full map identity.

Graph shape: PLACES (named points with map_id) connected by EDGES (how to travel).
Edge kinds:
- ``walk``   — an L1 route on one map (cost = route distance, planned live).
- ``portal`` — an instance entrance: stand at ``from`` and fire ``area_trigger`` with
  ``trigger_id``; you appear at ``to`` on another map.
(Zeppelin/boat/hearth edges are future kinds; the executor support is unverified.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Point:
    map_id: int
    x: float
    y: float
    z: float

    def horizontal_distance(self, other: "Point") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def distance(self, other: "Point") -> float:
        return math.sqrt(
            (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2
        )


@dataclass(frozen=True)
class Place:
    name: str
    point: Point


@dataclass(frozen=True)
class Edge:
    kind: str  # "walk" | "portal"
    a: str  # place name
    b: str  # place name
    bidirectional: bool = True
    trigger_id: int | None = None  # portal edges: the areatrigger to fire at `a`
    cost_hint: float = 0.0  # rough yards for graph search; walk edges re-cost live


# ---------------------------------------------------------------------------------
# The seed graph: Durotar ↔ Orgrimmar ↔ Ragefire Chasm.
# Sources: authored leveling profile (durotar_troll_shaman.nim), the game repo's
# dungeon registry (dungeon.py: areatrigger 2230 → map 389 at 0.797/-8.234/-15.529),
# our own hosted traces (v6 trajectories), and VMaNGOS-era public coordinates for
# Orgrimmar anchors (marked; verify from traces when first walked).
# ---------------------------------------------------------------------------------

PLACES: dict[str, Place] = {
    # Durotar (map 1)
    "valley-spawn": Place("valley-spawn", Point(1, -618.5, -4251.7, 38.7)),
    "valley-gate": Place("valley-gate", Point(1, -359.7, -4309.8, 49.9)),
    "senjin-village": Place("senjin-village", Point(1, -797.5, -4921.2, 23.0)),
    "razor-hill": Place("razor-hill", Point(1, 315.0, -4743.0, 10.5)),  # VMaNGOS-era; verify
    # Orgrimmar (map 1 — the city is on the continent map)
    "orgrimmar-gate": Place("orgrimmar-gate", Point(1, 1295.0, -4377.0, 26.1)),  # front gate; verify
    "org-valley-of-strength": Place("org-valley-of-strength", Point(1, 1629.0, -4373.0, 31.3)),  # verify
    "cleft-of-shadow": Place("cleft-of-shadow", Point(1, 1811.0, -4420.0, -18.5)),  # verify
    # The RFC portal pad inside the Cleft (areatrigger 2230's world side).
    "rfc-portal": Place("rfc-portal", Point(1, 1815.0, -4418.0, -18.5)),  # verify from trace
    # Ragefire Chasm (map 389) — entrance + stations from the dungeon definition.
    "rfc-entrance": Place("rfc-entrance", Point(389, 0.8, -8.2, -15.5)),
    "rfc-entry-cavern": Place("rfc-entry-cavern", Point(389, -142.3, -6.2, -53.2)),
}

EDGES: list[Edge] = [
    Edge("walk", "valley-spawn", "valley-gate", cost_hint=280),
    Edge("walk", "valley-spawn", "senjin-village", cost_hint=740),
    Edge("walk", "valley-gate", "razor-hill", cost_hint=800),
    Edge("walk", "razor-hill", "orgrimmar-gate", cost_hint=1100),
    Edge("walk", "orgrimmar-gate", "org-valley-of-strength", cost_hint=350),
    Edge("walk", "org-valley-of-strength", "cleft-of-shadow", cost_hint=300),
    Edge("walk", "cleft-of-shadow", "rfc-portal", cost_hint=30),
    Edge("portal", "rfc-portal", "rfc-entrance", bidirectional=False,
         trigger_id=2230, cost_hint=1),
    Edge("walk", "rfc-entrance", "rfc-entry-cavern", cost_hint=160),
]


@dataclass
class WorldModel:
    places: dict[str, Place] = field(default_factory=lambda: dict(PLACES))
    edges: list[Edge] = field(default_factory=lambda: list(EDGES))

    def place(self, name: str) -> Place:
        return self.places[name]

    def neighbors(self, name: str) -> list[tuple[Edge, str]]:
        result = []
        for edge in self.edges:
            if edge.a == name:
                result.append((edge, edge.b))
            elif edge.bidirectional and edge.b == name:
                result.append((edge, edge.a))
        return result

    def nearest_place(self, point: Point, *, same_map: bool = True) -> Place | None:
        candidates = [
            p for p in self.places.values()
            if not same_map or p.point.map_id == point.map_id
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda p: p.point.horizontal_distance(point))

    def plan(self, start: str, goal: str) -> list[Edge] | None:
        """Dijkstra over cost hints; walk edges get re-costed live by the journey layer."""
        import heapq

        queue: list[tuple[float, str, list[Edge]]] = [(0.0, start, [])]
        seen: set[str] = set()
        while queue:
            cost, node, path = heapq.heappop(queue)
            if node == goal:
                return path
            if node in seen:
                continue
            seen.add(node)
            for edge, neighbor in self.neighbors(node):
                if neighbor not in seen:
                    heapq.heappush(
                        queue, (cost + max(edge.cost_hint, 1.0), neighbor, path + [edge])
                    )
        return None
