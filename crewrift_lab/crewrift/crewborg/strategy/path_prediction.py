"""Path prediction: a probability distribution over where a tracked player is going.

This is the projection primitive the imposter's seeking logic needs to *follow a
crewmate to their next room* once they leave view. Unlike ``strategy.trajectory``
(a 2-sighting straight-line velocity used by Hunt for a short intercept), this
models destinations: each frame it scores a set of candidate **nav routes** (paths
to plausible destinations — task stations and room centers) by how well the
target's recently observed motion matches the direction each route would have them
walk. Recent motion is weighted more than old motion (exponential forgetting), so a
target that changes direction re-weights toward its new heading and the
distribution sharpens as it commits to a corridor. When the target is out of view
the routes stop gaining evidence but each candidate's predicted position keeps
advancing along its route — which is what following needs.

Pure and stateful-by-handle: the caller holds a :class:`PathPredictor` per tracked
target and feeds it one observation per frame (the position when visible, ``None``
when not). No game/transport coupling — it takes a nav graph + map + observations,
so it is exercised directly from replays by ``tools/path_prediction_*`` without a
live game.

Model:
- **Destinations** are reachable task stations + room-center anchors (the places
  crew actually walk to), with a route from the acquisition point computed once via
  ``nav.plan_route`` and stored as an arc-length polyline.
- **Predicted position** per candidate is tracked as an arc-length along that
  polyline: snapped to the observed point while visible, advanced by assumed speed
  while occluded.
- **Probability** is a softmax over a per-candidate evidence score that decays each
  frame (recent alignment dominates); evidence is the cosine between the observed
  step and the route's local direction from the target's current position.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from crewrift.crewborg.map.types import MapData
from crewrift.crewborg.nav import NavGraph, plan_route

Point = tuple[int, int]

# Drop a candidate once its normalized probability falls below this.
MIN_KEEP_PROB = 0.02
# How sharply per-frame alignment evidence concentrates probability.
ALIGN_GAIN = 1.5
# Exponential forgetting of evidence per scored frame (recent motion dominates, so a
# direction change re-weights instead of being out-voted by stale evidence). Tuned
# against replays via tools/path_prediction_eval.py; lower = forgets faster.
EVIDENCE_DECAY = 0.7
# A sighting older than this many ticks is too stale to derive a motion step from.
MAX_SIGHTING_GAP = 6
# Assumed crew travel speed (world px/tick) for advancing predictions while occluded.
CREW_SPEED_PX = 2.75
# A fresh sighting farther than this from every prediction triggers re-acquisition.
REACQUIRE_DIST = 96.0
# How far ahead along the route to read the "where would they walk next" direction.
LOOKAHEAD_PX = 24.0


def _polyline_length(path: list[Point]) -> list[float]:
    """Cumulative arc-length at each waypoint (``cum[0] == 0``)."""

    cum = [0.0]
    for a, b in zip(path, path[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    return cum


def _point_at_arc(path: list[Point], cum: list[float], arc: float) -> Point:
    """The point ``arc`` world-px along the polyline (clamped to its ends)."""

    if arc <= 0 or len(path) == 1:
        return path[0]
    if arc >= cum[-1]:
        return path[-1]
    # find the segment containing arc
    for i in range(1, len(cum)):
        if cum[i] >= arc:
            a, b = path[i - 1], path[i]
            seg = cum[i] - cum[i - 1]
            t = (arc - cum[i - 1]) / seg if seg > 0 else 0.0
            return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t))
    return path[-1]


def _project_arc(path: list[Point], cum: list[float], point: Point) -> float:
    """Arc-length of the closest point on the polyline to ``point``."""

    best_arc, best_d2 = 0.0, math.inf
    for i in range(len(path) - 1):
        ax, ay = path[i]
        bx, by = path[i + 1]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        if seg2 == 0:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((point[0] - ax) * dx + (point[1] - ay) * dy) / seg2))
        px, py = ax + dx * t, ay + dy * t
        d2 = (point[0] - px) ** 2 + (point[1] - py) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_arc = cum[i] + math.dist((ax, ay), (px, py))
    if len(path) == 1:
        return 0.0
    return best_arc


@dataclass
class Candidate:
    """One hypothesised destination and the (arc-length) route to it."""

    dest: Point
    dest_label: str
    path: list[Point]
    cum: list[float]               # cumulative arc-length per waypoint
    arc: float = 0.0               # the target's predicted distance along the route
    log_score: float = 0.0         # decayed evidence (unnormalized)
    prob: float = 0.0              # normalized probability this frame

    @property
    def pred_pos(self) -> Point:
        return _point_at_arc(self.path, self.cum, self.arc)

    def heading_from(self, point: Point) -> Point | None:
        """Unit direction from ``point`` toward a lookahead further along the route."""

        look_arc = _project_arc(self.path, self.cum, point) + LOOKAHEAD_PX
        look = _point_at_arc(self.path, self.cum, look_arc)
        dx, dy = look[0] - point[0], look[1] - point[1]
        n = math.hypot(dx, dy)
        if n < 1.0:
            return None
        return (dx / n, dy / n)


@dataclass
class PathPredictor:
    """Per-target predictor. Feed one :meth:`observe` per frame."""

    nav: NavGraph
    map: MapData
    candidates: list[Candidate] = field(default_factory=list)
    last_point: Point | None = None
    last_tick: int | None = None

    # --- candidate construction ------------------------------------------------
    def _acquire(self, point: Point) -> None:
        """(Re)build the candidate set from a fresh sighting at ``point``."""

        dests: list[tuple[Point, str]] = []
        for i, task in enumerate(self.map.tasks):
            dests.append(((task.center.x, task.center.y), f"task:{i}:{task.name}"))
        for room in self.map.rooms:
            dests.append(((room.center.x, room.center.y), f"room:{room.name}"))

        candidates: list[Candidate] = []
        for dest, label in dests:
            if math.dist(dest, point) < 1.0:
                continue
            path = plan_route(self.nav, point, dest)
            if not path:
                continue
            path = [point, *path] if path[0] != point else path
            candidates.append(Candidate(dest=dest, dest_label=label, path=path, cum=_polyline_length(path)))
        self.candidates = candidates

    # --- per-frame update ------------------------------------------------------
    def observe(self, tick: int, point: Point | None) -> None:
        """Advance the distribution one frame. ``point`` is the target's observed
        position, or ``None`` when the target is not currently visible."""

        if point is not None:
            self._observe_visible(tick, point)
        else:
            self._observe_occluded(tick)
        self._normalize()

    def _observe_visible(self, tick: int, point: Point) -> None:
        step: Point | None = None
        if self.last_point is not None and self.last_tick is not None:
            gap = tick - self.last_tick
            if 0 < gap <= MAX_SIGHTING_GAP:
                step = (point[0] - self.last_point[0], point[1] - self.last_point[1])

        # Re-acquire the full destination set when we have nothing, when the target
        # jumped far from every prediction, or when it is now moving *against* all
        # surviving routes (a reversal/new goal the pruned set can no longer explain).
        if not self.candidates or self._far_from_all(point) or self._moving_against_all(point, step):
            self._acquire(point)

        # Snap every candidate's predicted position to the observed truth.
        for cand in self.candidates:
            cand.arc = _project_arc(cand.path, cand.cum, point)

        if step is not None:
            self._score(point, step)
        self.last_point = point
        self.last_tick = tick

    def _moving_against_all(self, point: Point, step: Point | None) -> bool:
        """True if a real step is anti-aligned (cos < 0) with every candidate's
        heading — the target is walking away from all surviving routes, so the
        pruned candidate set has lost the destination it is actually pursuing."""

        if step is None or step == (0, 0) or not self.candidates:
            return False
        sn = math.hypot(*step)
        for cand in self.candidates:
            h = cand.heading_from(point)
            if h is None:
                return False
            if (step[0] * h[0] + step[1] * h[1]) / sn > 0:
                return False  # at least one route still agrees with the motion
        return True

    def _observe_occluded(self, tick: int) -> None:
        if self.last_tick is None:
            self.last_tick = tick
            return
        steps = max(0, tick - self.last_tick)
        for cand in self.candidates:
            cand.arc = min(cand.cum[-1], cand.arc + CREW_SPEED_PX * steps)
        self.last_tick = tick

    def _score(self, point: Point, step: Point) -> None:
        """Decay then add this frame's directional evidence to each candidate."""

        step_norm = math.hypot(*step)
        for cand in self.candidates:
            cand.log_score *= EVIDENCE_DECAY
            if step_norm == 0:
                continue
            heading = cand.heading_from(point)
            if heading is None:
                continue
            cos = (step[0] * heading[0] + step[1] * heading[1]) / step_norm
            cand.log_score += ALIGN_GAIN * cos

    def _far_from_all(self, point: Point) -> bool:
        return all(math.dist(point, c.pred_pos) > REACQUIRE_DIST for c in self.candidates)

    def _normalize(self) -> None:
        if not self.candidates:
            return
        top = max(c.log_score for c in self.candidates)
        for cand in self.candidates:
            cand.prob = math.exp(cand.log_score - top)
        total = sum(c.prob for c in self.candidates) or 1.0
        for cand in self.candidates:
            cand.prob /= total
        self.candidates = [c for c in self.candidates if c.prob >= MIN_KEEP_PROB]
        total = sum(c.prob for c in self.candidates) or 1.0
        for cand in self.candidates:
            cand.prob /= total

    # --- readouts --------------------------------------------------------------
    def ranked(self) -> list[Candidate]:
        return sorted(self.candidates, key=lambda c: c.prob, reverse=True)

    def best(self) -> Candidate | None:
        ranked = self.ranked()
        return ranked[0] if ranked else None
