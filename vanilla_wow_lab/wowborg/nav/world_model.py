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
# AUTHORITATIVE sources (codex audit #6 flagged the old guessed coordinates —
# several were 50-60yd off; the Cleft z was wrong by 56 yards):
# - game repo bots/decision/graph_data.py (the executor's own decision-graph
#   anchors: valley_of_trials, razor_hill, orgrimmar_gate,
#   orgrimmar_valley_of_strength, cleft_of_shadow — exact _jp() coordinates)
# - game repo bots/decision/fast_travel.py FastTravelLink
#   dungeon_portal:ragefire_chasm:2230 (walk_source = the walkable pad,
#   destination = map 389 arrival; evidence: vmangos areatrigger_teleport +
#   AreaTrigger.dbc + VMAP/MMAP portal floor)
# - our own hosted traces (v6 trajectories) for valley-gate / senjin.
# ---------------------------------------------------------------------------------

PLACES: dict[str, Place] = {
    # Durotar (map 1)
    "valley-spawn": Place("valley-spawn", Point(1, -618.518, -4251.67, 38.718)),
    "valley-gate": Place("valley-gate", Point(1, -359.7, -4309.8, 49.9)),
    "senjin-village": Place("senjin-village", Point(1, -797.5, -4921.2, 23.0)),
    # The south road out of the Valley of Trials (graph_data.py chain; its own
    # note: "leave the starter valley through the southern road pass instead of
    # cutting straight at Razor Hill" — the direct east line dead-ends at the
    # canyon wall, which is where v25-v40 razor-hill attempts all died).
    "valley-south-pass": Place("valley-south-pass", Point(1, -582.795, -4550.96, 42.725)),
    "south-road-west": Place("south-road-west", Point(1, -610.798, -4599.89, 41.444)),
    "canyon-west": Place("canyon-west", Point(1, -498.031, -4687.444, 38.529)),
    "canyon-mid": Place("canyon-mid", Point(1, -298.267, -4687.733, 43.585)),
    "canyon-lower-west": Place("canyon-lower-west", Point(1, -225.0, -4684.0, 39.0)),
    "canyon-lower-east": Place("canyon-lower-east", Point(1, -190.0, -4660.0, 38.0)),
    "canyon-east": Place("canyon-east", Point(1, -104.735, -4650.149, 35.219)),
    "razormane-road": Place("razormane-road", Point(1, 18.233, -4617.23, 44.73)),
    "razor-hill-south": Place("razor-hill-south", Point(1, 267.9, -4625.4, 17.1)),
    "razor-hill": Place("razor-hill", Point(1, 315.0, -4743.0, 9.0)),
    "northern-durotar": Place("northern-durotar", Point(1, 1031.733, -4597.333, 23.819)),
    # Orgrimmar (map 1 — the city is on the continent map)
    "orgrimmar-gate": Place("orgrimmar-gate", Point(1, 1385.0, -4374.0, 27.0)),
    "org-valley-of-strength": Place(
        "org-valley-of-strength", Point(1, 1629.36, -4373.39, 31.3)),
    "org-drag": Place("org-drag", Point(1, 1643.253, -4380.884, 26.498)),
    "cleft-of-shadow": Place("cleft-of-shadow", Point(1, 1750.667, -4382.667, 37.863)),
    # The RFC portal pad (fast_travel.py walk_source: the walkable floor point).
    "rfc-portal": Place("rfc-portal", Point(1, 1818.4, -4427.26, -20.56)),
    # Ragefire Chasm (map 389) — fast_travel.py destination + spine data.
    "rfc-entrance": Place("rfc-entrance", Point(389, 0.798, -8.234, -15.529)),
    "rfc-entry-cavern": Place("rfc-entry-cavern", Point(389, -142.3, -6.2, -53.2)),
}

EDGES: list[Edge] = [
    Edge("walk", "valley-spawn", "valley-gate", cost_hint=280),
    Edge("walk", "valley-spawn", "senjin-village", cost_hint=740),
    # The authoritative south road to Razor Hill (graph_data.py edge chain).
    Edge("walk", "valley-spawn", "valley-south-pass", cost_hint=300),
    Edge("walk", "valley-south-pass", "south-road-west", cost_hint=60),
    Edge("walk", "south-road-west", "canyon-west", cost_hint=145),
    Edge("walk", "canyon-west", "canyon-mid", cost_hint=200),
    Edge("walk", "canyon-mid", "canyon-lower-west", cost_hint=75),
    Edge("walk", "canyon-lower-west", "canyon-lower-east", cost_hint=45),
    Edge("walk", "canyon-lower-east", "canyon-east", cost_hint=85),
    Edge("walk", "canyon-east", "razormane-road", cost_hint=125),
    Edge("walk", "razormane-road", "razor-hill-south", cost_hint=250),
    Edge("walk", "razor-hill-south", "razor-hill", cost_hint=130),
    Edge("walk", "razor-hill-south", "northern-durotar", cost_hint=770),
    Edge("walk", "northern-durotar", "orgrimmar-gate", cost_hint=420),
    Edge("walk", "orgrimmar-gate", "org-valley-of-strength", cost_hint=250),
    Edge("walk", "org-valley-of-strength", "org-drag", cost_hint=20),
    Edge("walk", "org-drag", "cleft-of-shadow", cost_hint=110),
    Edge("walk", "cleft-of-shadow", "rfc-portal", cost_hint=90),
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
