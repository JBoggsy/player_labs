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
    # Razor Hill / the road north (fresh region — never raced before)
    "razor-hill":       (Point(1, 315.0, -4743.0, 10.5), "razor-hill", "reachable"),
    # Orgrimmar (urban; verify-and-correct coordinates from first traces)
    "orgrimmar-gate":   (Point(1, 1295.0, -4377.0, 26.1), "orgrimmar", "reachable"),
    "org-valley-of-strength": (Point(1, 1629.0, -4373.0, 31.3), "orgrimmar", "reachable"),
    "cleft-of-shadow":  (Point(1, 1811.0, -4420.0, -18.5), "orgrimmar", "reachable"),
    # Ragefire Chasm (dungeon; cross-map via the portal edge)
    "rfc-entrance":     (Point(389, 0.8, -8.2, -15.5), "rfc", "reachable"),
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


def log(message: str) -> None:
    print(f"WOWBORG-POLICY {message}", flush=True)


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
        reached = sum(1 for r in self.results if r["outcome"] == "arrived")
        honest = sum(
            1 for r in self.results
            if r["expected"] == "unreachable" and r["outcome"] == "failed_unreachable"
        )
        expected_reachable = sum(1 for r in self.results if r["expected"] == "reachable")
        expected_unreachable = sum(1 for r in self.results if r["expected"] == "unreachable")
        return {
            "course": self.course,
            "stations_attempted": len(self.results),
            "reached": reached,
            "reachability": round(reached / expected_reachable, 3) if expected_reachable else None,
            "honesty": round(honest / expected_unreachable, 3) if expected_unreachable else None,
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
        for name in self.course:
            if name in done_names:
                continue
            remaining = until - time.monotonic()
            if remaining <= 30.0:
                log("out of session time; stopping course")
                break
            point, region, expected = self.stations[name]
            station_deadline = time.monotonic() + max(
                60.0, remaining * STATION_DEADLINE_FRACTION
            )
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
                "deaths": 0,
                "combat_pauses": 0,
                "replans": 0,
            }
            self.results.append(row)
            trace("nav_station", **row)
            log(f"station {name}: {outcome} in {seconds:.0f}s ({len(result.legs)} legs)")

        summary = self.summary()
        trace("race_end", **summary)
        log(f"world race done: {json.dumps(summary)}")
