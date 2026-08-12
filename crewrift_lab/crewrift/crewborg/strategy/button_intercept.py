"""Front-of-ship positioning prior for imposter Search (button-runner interception, Tier 1).

Design: ``docs/designs/button-runner-interception.md``. Phase-0 corpus study (§2,
1,875 league games): crew run the emergency button to **reset every imposter's kill
cooldown** in ~92% of games (~2×/game), on a ~900-tick rhythm — past our 500-tick
cooldown, so the runner is killable. The runners travel **alone** and funnel through
the corridor just **east of the bridge button**, converging on it from their task
rooms. Intercepting a runner before it presses denies the cooldown reset *and* the
meeting (and banks a kill), so during our pre-kill Search window we want to be
loitering on that convergence corridor rather than at generic occupancy hot spots.

This module supplies that positioning prior. It is **map-agnostic**: the convergence
points are derived from the precomputed anchor→button route polylines already built
in the tracking substrate (``agent_tracking.build_occupancy_substrate``), sampled in
a distance band off the button — far enough that a kill there drops the body outside
the high-traffic button room, close enough to reach an inbound runner mid-approach.

Tier 1 is a **bias only**: Search still follows any visible/trackable victim first
(bird in hand; ``SearchMode._target``), and these points are merely prepended to the
occupancy seek list when ``CREWBORG_FRONT_BIAS`` is set, so they steer the *idle*
search walk toward the corridor without overriding a real target. Gated behind the
env flag for a clean A/B (mirrors ``CREWBORG_BE_DUMB``).
"""

from __future__ import annotations

import math
import os

from crewrift.crewborg.types import Belief

Point = tuple[int, int]

# Distance band (world px) off the button to loiter in. Phase-0: runners sit a median
# ~241px out 250t before pressing and converge through cells ~150–240px east of the
# button; we aim for the band centre, off the button room but reachable mid-approach.
FRONT_BAND_MIN = 140
FRONT_BAND_MAX = 300
FRONT_BAND_CENTER = 210

# Points within this distance are treated as the same convergence cluster (≈ one grid
# cell); the cluster a route passes through is the chokepoint we want to camp.
CLUSTER_RADIUS = 32

# Keep only the top few convergence clusters so the corridor bias never fills the whole
# seek list — Search must still rotate out to occupancy when no runner appears.
MAX_APPROACH_POINTS = 2


def front_bias_enabled() -> bool:
    """Whether the front-of-ship positioning prior is active (``CREWBORG_FRONT_BIAS``)."""

    return os.environ.get("CREWBORG_FRONT_BIAS", "").strip().lower() in {"1", "true", "yes", "on"}


def button_approach_points(belief: Belief) -> list[Point]:
    """Convergence points on the runners' approach corridor, hottest cluster first.

    Empty until the tracking substrate exists (its anchor→button polylines are the
    source of the approaches) or if the button is unreachable.
    """

    substrate = belief.agent_tracking.substrate
    if substrate is None:
        return []
    button = _button_anchor(belief, substrate)
    if button is None:
        return []

    # One band point per route that ends at the button: where that route crosses the
    # band, nearest the band centre. Routes from different rooms share the corridor, so
    # these points cluster on the chokepoint.
    band_points: list[Point] = []
    for (_start, end), polyline in substrate.polylines.items():
        if end != "button":
            continue
        point = _band_point(_sample_polyline(polyline), button)
        if point is not None:
            band_points.append(point)
    if not band_points:
        return []

    clusters = _cluster(band_points)
    # Rank by convergence (cluster size) first, then nearest the button (closest to the
    # bridge mouth = catches runners from the most directions before they press).
    clusters.sort(key=lambda c: (-c[1], _dist2(c[0], button)))
    return [_reachable_point(belief, centroid) for centroid, _count in clusters[:MAX_APPROACH_POINTS]]


def _button_anchor(belief: Belief, substrate) -> Point | None:
    for anchor in substrate.anchors:
        if anchor.name == "button":
            return anchor.point
    if belief.nav is not None and belief.nav.button_anchor is not None:
        return belief.nav.button_anchor
    if belief.map is not None:
        return belief.map.button.center.x, belief.map.button.center.y
    return None


def _band_point(points: list[Point], button: Point) -> Point | None:
    """The point inside the band whose distance to ``button`` is nearest the band
    centre, or ``None`` if none of ``points`` fall in the band. Operates on a sampled
    point sequence (see ``_sample_polyline``) so straight routes with no intermediate
    vertex inside the band are still covered."""

    best: Point | None = None
    best_err = float("inf")
    for p in points:
        d = math.dist(p, button)
        if FRONT_BAND_MIN <= d <= FRONT_BAND_MAX:
            err = abs(d - FRONT_BAND_CENTER)
            if err < best_err:
                best_err, best = err, p
    return best


def _sample_polyline(polyline, step: int = 16) -> list[Point]:
    """Points along the route at ``step``-px arc-length intervals (endpoints included)."""

    total = polyline.total_length
    if total <= 0:
        return list(polyline.points)
    n = int(total // step)
    return [polyline.point_at(i * step) for i in range(n + 1)] + [polyline.point_at(total)]


def _cluster(points: list[Point]) -> list[tuple[Point, int]]:
    """Greedy single-pass clustering by proximity; returns (representative, size)."""

    clusters: list[tuple[Point, list[Point]]] = []
    for p in points:
        for rep, members in clusters:
            if _dist2(p, rep) <= CLUSTER_RADIUS**2:
                members.append(p)
                break
        else:
            clusters.append((p, [p]))
    return [(_centroid(members), len(members)) for _rep, members in clusters]


def _centroid(members: list[Point]) -> Point:
    mean = (sum(p[0] for p in members) / len(members), sum(p[1] for p in members) / len(members))
    return min(members, key=lambda p: _dist2(p, (round(mean[0]), round(mean[1]))))


def _dist2(a: Point, b: Point) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _reachable_point(belief: Belief, point: Point) -> Point:
    """Snap ``point`` to the nearest reachable nav node (a walkable goal)."""

    if belief.nav is None:
        return point
    cell = belief.nav.nearest_reachable_node(*point)
    if cell is None:
        return point
    return belief.nav.node_point[cell]
