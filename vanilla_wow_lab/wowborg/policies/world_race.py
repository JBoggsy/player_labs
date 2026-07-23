"""The World Race — the nav-v2 benchmark policy.

Draws a seedable random multi-region course of STATIONS and visits each via
``JourneyPlanner.journey_to`` (which handles cross-map/gates/dungeons). Stations are
pure DATA: adding one requires no code or constant change — that's the generality bar
(the /goal): new stations should one-shot.

Station schema: name → (Point, region, expected) where expected ∈
  reachable    — journey should ARRIVE
  unreachable  — journey should FAIL fast with reason=unreachable (honesty score)
Course draw: N stations spanning ≥ MIN_REGIONS distinct regions; adversarial
(unreachable) stations included at their catalog rate. Per-station trace: nav_station
{name, expected, outcome, seconds, planned_distance, walked_seconds, combat_pauses,
deaths, replans} — nav_report.py scores reachability/honesty/efficiency/robustness.
"""

from __future__ import annotations

import json
import os
import random
import time

from wowborg.nav.journey import JourneyPlanner, JourneyStatus
from wowborg.nav.route import NavState
from wowborg.nav.world_model import Point

# ---------------------------------------------------------------------------------
# STATION CATALOG — data only. Sources: authored profiles, dungeon defs, own traces.
# Region tags drive draw diversity; they are labels, not logic.
# ---------------------------------------------------------------------------------
STATIONS: dict[str, tuple[Point, str, str]] = {
    # Durotar outdoor (proven region — regression guard vs the v19/v20 results)
    "valley-trainers":  (Point(1, -623.9, -4203.9, 38.4), "durotar", "reachable"),
    "boar-yard":        (Point(1, -715.0, -4240.0, 40.0), "durotar", "reachable"),
    "valley-gate":      (Point(1, -359.7, -4309.8, 49.9), "durotar", "reachable"),
    "senjin-village":   (Point(1, -797.5, -4921.2, 23.0), "durotar", "reachable"),
    "sarkoth-mesa":     (Point(1, -547.3, -4103.9, 70.1), "durotar-hard", "reachable"),
    # Razor Hill / the road north (coordinates: game repo graph_data.py anchors)
    "razor-hill":       (Point(1, 315.0, -4743.0, 9.0), "razor-hill", "reachable"),
    # Orgrimmar (urban; coordinates: game repo graph_data.py anchors — the old
    # guessed set had the gate 90yd off and the Cleft z wrong by 56yd)
    "orgrimmar-gate":   (Point(1, 1385.0, -4374.0, 27.0), "orgrimmar", "reachable"),
    "org-valley-of-strength": (Point(1, 1629.36, -4373.39, 31.3), "orgrimmar", "reachable"),
    "cleft-of-shadow":  (Point(1, 1750.667, -4382.667, 37.863), "orgrimmar", "reachable"),
    # Ragefire Chasm (dungeon; cross-map via the portal edge — fast_travel.py)
    "rfc-entrance":     (Point(389, 0.798, -8.234, -15.529), "rfc", "reachable"),
    "rfc-entry-cavern": (Point(389, -142.3, -6.2, -53.2), "rfc", "reachable"),
    # Adversarial: honesty probes — correct behavior is FAST, CLEAN failure.
    "midair-over-sea":  (Point(1, -1200.0, -5800.0, 150.0), "adversarial", "unreachable"),
    "under-the-world":  (Point(1, -618.5, -4251.7, -200.0), "adversarial", "unreachable"),
}

DEFAULT_STATION_COUNT = 4
MIN_REGIONS = 3
ADVERSARIAL_COUNT = 1

RACE_SEED_ENV = "WOWBORG_RACE_SEED"
STATIONS_ENV = "WOWBORG_STATIONS"           # JSON [[name, map_id, x, y, z, expected], ...]
STATION_COUNT_ENV = "WOWBORG_STATION_COUNT"
STATION_DEADLINE_FRACTION = 0.55            # max fraction of remaining time per station
# Best-case moving pace through the nim_control seam, measured across v25-v33
# hosted batches (the executor advances ≤8 corridor waypoints ≈ 17yd per ~7.6s
# settle cycle ≈ 2.2 yd/s; overhead only lowers it). Seam fact, not zone
# calibration — used only to skip stations that provably can't fit their share.
OPTIMISTIC_PACE_YDS_PER_S = 2.5


def log(message: str) -> None:
    print(f"WOWBORG-POLICY {message}", flush=True)


def _travel_estimate_yards(world, here: Point | None, target: Point) -> float | None:
    """Straight-line travel estimate; cross-map targets route over the world graph
    (walk-edge cost hints + the final same-map stretch). None when unknown."""
    if here is None:
        return None
    if target.map_id == here.map_id:
        return here.horizontal_distance(target)
    start = world.nearest_place(here, same_map=True)
    candidates = [p for p in world.places.values() if p.point.map_id == target.map_id]
    if start is None or not candidates:
        return None
    goal = min(candidates, key=lambda p: p.point.horizontal_distance(target))
    path = world.plan(start.name, goal.name)
    if path is None:
        return None
    yards = here.horizontal_distance(start.point)
    yards += sum(e.cost_hint for e in path)
    yards += goal.point.horizontal_distance(target)
    return yards


def load_stations() -> dict[str, tuple[Point, str, str]]:
    raw = os.environ.get(STATIONS_ENV)
    if not raw:
        return dict(STATIONS)
    try:
        rows = json.loads(raw)
        stations = {}
        for row in rows:
            name, map_id, x, y, z, expected = row
            stations[str(name)] = (Point(int(map_id), float(x), float(y), float(z)),
                                   "custom", str(expected))
        if stations:
            return stations
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        log(f"ignoring malformed WOWBORG_STATIONS: {exc}")
    return dict(STATIONS)


def draw_course(
    rng: random.Random,
    stations: dict[str, tuple[Point, str, str]],
    count: int,
) -> list[str]:
    """Random multi-region draw: fill from distinct regions first, then anywhere;
    include adversarial stations at the configured rate."""
    adversarial = [n for n, (_, r, e) in stations.items() if e == "unreachable"]
    reachable = [n for n, (_, r, e) in stations.items() if e != "unreachable"]
    by_region: dict[str, list[str]] = {}
    for name in reachable:
        by_region.setdefault(stations[name][1], []).append(name)

    course: list[str] = []
    regions = list(by_region)
    rng.shuffle(regions)
    for region in regions[: max(MIN_REGIONS, 1)]:
        course.append(rng.choice(by_region[region]))
    remaining = [n for n in reachable if n not in course]
    rng.shuffle(remaining)
    while len(course) < max(count - ADVERSARIAL_COUNT, len(course)) and remaining:
        course.append(remaining.pop())
    for _ in range(ADVERSARIAL_COUNT):
        if adversarial:
            course.append(rng.choice(adversarial))
    rng.shuffle(course)
    return course


class WorldRacePolicy:
    def __init__(
        self,
        course: list[str] | None = None,
        rng: random.Random | None = None,
        stations: dict[str, tuple[Point, str, str]] | None = None,
    ) -> None:
        seed = os.environ.get(RACE_SEED_ENV)
        self._rng = rng or (
            random.Random(int(seed)) if seed and seed.lstrip("-").isdigit()
            else random.Random()
        )
        self.stations = stations if stations is not None else load_stations()
        count = int(os.environ.get(STATION_COUNT_ENV, DEFAULT_STATION_COUNT) or DEFAULT_STATION_COUNT)
        self.course = course if course is not None else draw_course(
            self._rng, self.stations, count
        )
        self.results: list[dict] = []

    def summary(self) -> dict:
        # Reachability counts ONLY expected-reachable rows in both numerator and
        # denominator (codex audit #15: adversarial arrivals inflated it >100%),
        # and skips are NOT censored out — they fail reachability and surface
        # separately as coverage (audit #1: the old skip exclusion made the
        # benchmark structurally unable to test the long-range cases the
        # generality claim is about).
        reachable_rows = [r for r in self.results if r["expected"] == "reachable"]
        reached = sum(1 for r in reachable_rows if r["outcome"] == "arrived")
        skipped = sum(
            1 for r in reachable_rows
            if r["outcome"] == "skipped_insufficient_time"
        )
        honest = sum(
            1 for r in self.results
            if r["expected"] == "unreachable" and r["outcome"] == "failed_unreachable"
        )
        surprise_arrivals = sum(
            1 for r in self.results
            if r["expected"] == "unreachable" and r["outcome"] == "arrived"
        )
        expected_unreachable = sum(1 for r in self.results if r["expected"] == "unreachable")
        return {
            "course": self.course,
            "stations_attempted": len(self.results),
            "reached": reached,
            "reachability": (
                round(reached / len(reachable_rows), 3) if reachable_rows else None
            ),
            "coverage": (
                round((len(reachable_rows) - skipped) / len(reachable_rows), 3)
                if reachable_rows else None
            ),
            "skipped": skipped,
            "honesty": round(honest / expected_unreachable, 3) if expected_unreachable else None,
            "surprise_arrivals": surprise_arrivals,
            "deaths": sum(r["deaths"] for r in self.results),
            "combat_pauses": sum(r["combat_pauses"] for r in self.results),
            "replans": sum(r["replans"] for r in self.results),
        }

    def run(self, bridge, *, until: float) -> None:
        tracer = getattr(bridge, "_tracer", None)

        def trace(kind: str, **payload) -> None:
            if tracer is not None:
                tracer.emit(kind, **payload)

        journey = JourneyPlanner(tracer=tracer)
        # Restart-idempotent: the shim re-invokes run() after crashes; visited
        # stations stay visited and race_start is emitted once.
        if not hasattr(self, "_started"):
            self._started = True
            trace("race_start", course=self.course)
        log(f"world race course: {self.course}")

        # Wait until the character is genuinely in-world before racing (login can
        # take minutes on hosted infra; frames exist but carry map 0 / origin).
        while time.monotonic() < until:
            here = journey.router._observe_position(bridge)
            if here is not None:
                log(f"in world at map {here.map_id} ({here.x:.0f},{here.y:.0f},{here.z:.0f})")
                break
            time.sleep(2.0)
        else:
            log("never entered world before deadline; aborting race")
            trace("race_end", **self.summary())
            return

        done_names = {r["name"] for r in self.results}
        while True:
            pending = [n for n in self.course if n not in done_names]
            if not pending:
                break
            remaining = until - time.monotonic()
            if remaining <= 30.0:
                log("out of session time; stopping course")
                break
            # Nearest-first visiting order (v31: random order criss-crossed the
            # map — Orgrimmar out, back past the start to Razor Hill — and later
            # stations starved). Straight-line is a fine ordering heuristic;
            # journeys still follow real routes.
            here = journey.router._observe_position(bridge)
            if here is not None:
                pending.sort(
                    key=lambda n: (
                        self.stations[n][0].map_id != here.map_id,  # same map first
                        self.stations[n][0].horizontal_distance(here)
                        if self.stations[n][0].map_id == here.map_id else 0.0,
                    )
                )
            name = pending[0]
            done_names.add(name)
            point, region, expected = self.stations[name]
            # The last pending station gets the whole remaining session; otherwise
            # the fair-share fraction protects the rest of the course.
            share = (remaining - 30.0 if len(pending) == 1
                     else remaining * STATION_DEADLINE_FRACTION)
            # Physically-honest skip: if even at full moving pace (no combat, no
            # replans) the station can't be reached inside its fair share of the
            # session, don't burn the course walking toward it — record
            # skipped_insufficient_time and move on. v33 evidence: Orgrimmar
            # stations ~2000yd out need ~15-25min through the seam; walking at
            # them ate 340-530s per episode and starved everything after.
            # Cross-map stations estimate over the world graph (v34: RFC journeys
            # route through Orgrimmar — ~2500yd the same-map check never saw).
            travel_yards = _travel_estimate_yards(journey.world, here, point)
            if expected == "reachable" and travel_yards is not None:
                optimistic_seconds = travel_yards / OPTIMISTIC_PACE_YDS_PER_S
                if optimistic_seconds > share:
                    row = {
                        "name": name, "region": region, "expected": expected,
                        "outcome": "skipped_insufficient_time",
                        "seconds": 0.0, "legs": 0,
                        "deaths": 0, "combat_pauses": 0, "replans": 0,
                    }
                    self.results.append(row)
                    trace("nav_station", **row)
                    log(f"station {name}: skipped (needs ≥{optimistic_seconds:.0f}s "
                        f"of travel, share is {share:.0f}s)")
                    continue
            station_deadline = time.monotonic() + max(60.0, share)
            started = time.monotonic()
            log(f"station {name} ({region}, expect {expected}): "
                f"map {point.map_id} ({point.x:.0f},{point.y:.0f},{point.z:.0f})")
            result = journey.journey_to(bridge, point, deadline=min(station_deadline, until))
            seconds = time.monotonic() - started

            if result.status == JourneyStatus.ARRIVED:
                outcome = "arrived"
            elif result.reason == "unreachable":
                outcome = "failed_unreachable"
            else:
                outcome = f"failed_{result.reason}"

            # Roll up nav metrics from the journey legs (route legs carry them).
            row = {
                "name": name,
                "region": region,
                "expected": expected,
                "outcome": outcome,
                "seconds": round(seconds, 1),
                "legs": len(result.legs),
                "deaths": sum(leg.get("deaths", 0) for leg in result.legs),
                "combat_pauses": sum(leg.get("combat_pauses", 0) for leg in result.legs),
                "replans": sum(leg.get("replans", 0) for leg in result.legs),
                "walked_seconds": round(
                    sum(leg.get("walked_seconds", 0.0) for leg in result.legs), 1
                ),
                "planned_distance": round(
                    sum(leg.get("planned_distance", 0.0) for leg in result.legs), 1
                ),
            }
            self.results.append(row)
            trace("nav_station", **row)
            log(f"station {name}: {outcome} in {seconds:.0f}s ({len(result.legs)} legs)")

        summary = self.summary()
        trace("race_end", **summary)
        log(f"world race done: {json.dumps(summary)}")
