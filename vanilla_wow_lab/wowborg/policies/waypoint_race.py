"""Nav test policy: race through pre-selected waypoints in order, timing every leg.

The course is a JSON list of [x, y, z] world points (map-local), supplied via
``WOWBORG_WAYPOINTS`` (inline JSON) or ``WOWBORG_WAYPOINTS_FILE``; the default course
is a Valley of Trials loop chosen from landmarks near the orc fresh-start spawn.

Race semantics: visit waypoints strictly in order; a leg completes when its move
settles successfully AND the observed position is within ``arrival_tolerance`` of the
waypoint (settlement alone can under-deliver, e.g. no_progress). A failed/blocked leg
is retried up to ``MAX_LEG_ATTEMPTS`` times before being skipped (counted DNF). Laps
repeat until the deadline; every leg emits a ``race_leg`` trace event with wall-clock
split, straight-line distance, and attempts, so the report tier can compute
yards/second per leg and per lap from the trace alone (replay cross-check via
trajectory stays available).
"""

from __future__ import annotations

import json
import math
import os
import time

# Valley of Trials landmarks (map 1, Durotar). Chosen off the VMaNGOS spawn
# (-618.5, -4251.7, 38.7): a ~4-point loop with legs 40-90 yd — long enough that
# Detour routing matters, short enough for several laps inside a 970 s episode.
DEFAULT_COURSE: list[list[float]] = [
    [-618.5, -4251.7, 38.7],   # spawn / Den entrance plaza
    [-560.0, -4212.0, 41.0],   # NE path toward the Den exit gate
    [-543.0, -4288.0, 39.5],   # E boar fields
    [-641.0, -4310.0, 38.0],   # S canyon pocket
]
WAYPOINTS_ENV = "WOWBORG_WAYPOINTS"
WAYPOINTS_FILE_ENV = "WOWBORG_WAYPOINTS_FILE"

ARRIVAL_TOLERANCE_YARDS = 8.0
MAX_LEG_ATTEMPTS = 3
FRAME_TIMEOUT_SECONDS = 60.0
LEG_TIMEOUT_SECONDS = 120.0

BREADCRUMBS_ENV = "WOWBORG_BREADCRUMBS"
DEFAULT_BREADCRUMBS = "minimal"


def log(message: str) -> None:
    print(f"WOWBORG-POLICY {message}", flush=True)


def load_course() -> list[list[float]]:
    raw = os.environ.get(WAYPOINTS_ENV)
    if not raw:
        path = os.environ.get(WAYPOINTS_FILE_ENV)
        if path and os.path.isfile(path):
            raw = open(path, encoding="utf-8").read()
    if raw:
        try:
            course = json.loads(raw)
            if (
                isinstance(course, list)
                and len(course) >= 2
                and all(isinstance(p, list) and len(p) == 3 for p in course)
            ):
                return [[float(v) for v in p] for p in course]
            log(f"ignoring malformed waypoint course (need >=2 [x,y,z] points)")
        except json.JSONDecodeError as exc:
            log(f"ignoring unparseable waypoint course: {exc}")
    return [list(p) for p in DEFAULT_COURSE]


def distance_2d(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


class WaypointRacePolicy:
    def __init__(self, course: list[list[float]] | None = None) -> None:
        self.course = course if course is not None else load_course()
        self.legs_completed = 0
        self.legs_skipped = 0
        self.laps_completed = 0
        self.total_race_seconds = 0.0
        self.splits: list[dict] = []  # per completed leg: seconds, yards, attempts

    def summary(self) -> dict:
        yards = sum(s["yards"] for s in self.splits)
        seconds = sum(s["seconds"] for s in self.splits)
        return {
            "course_points": len(self.course),
            "legs_completed": self.legs_completed,
            "legs_skipped": self.legs_skipped,
            "laps_completed": self.laps_completed,
            "total_yards": round(yards, 1),
            "total_seconds": round(seconds, 1),
            "yards_per_second": round(yards / seconds, 2) if seconds > 0 else None,
        }

    def run(self, bridge, *, until: float) -> None:
        mode = os.environ.get(BREADCRUMBS_ENV, DEFAULT_BREADCRUMBS)
        bridge_say = getattr(bridge, "say", lambda _text: None)
        say = bridge_say if mode != "off" else (lambda _text: None)
        tracer = getattr(bridge, "_tracer", None)

        def trace(kind: str, **payload) -> None:
            if tracer is not None:
                tracer.emit(kind, **payload)

        say("wowborg waypoint_race starting")
        trace("race_start", course=self.course)
        log(f"course: {len(self.course)} waypoints, racing until deadline")

        index = 0
        attempts = 0
        leg_started_at: float | None = None
        while time.monotonic() < until:
            remaining = until - time.monotonic()
            frame = bridge.wait_for_frame(timeout_s=min(FRAME_TIMEOUT_SECONDS, remaining))
            if frame is None:
                log("no decision frame offered before timeout; retrying")
                continue

            obs = frame.observation
            if obs.is_dead or obs.is_ghost:
                log("character dead/ghost — accepting recommended recovery action")
                request_id = bridge.select_recommended(frame)
                if request_id is not None:
                    bridge.wait_for_settlement(frame.frame_id, timeout_s=LEG_TIMEOUT_SECONDS)
                continue

            target = self.course[index]
            loc = obs.location
            started = distance_2d(loc.x, loc.y, target[0], target[1])

            # Already at the waypoint? (arrival check happens here so a partial leg
            # that settled short still completes once a later frame shows us close)
            if started <= ARRIVAL_TOLERANCE_YARDS:
                # A leg only COUNTS if we actually raced it (≥1 move attempt);
                # standing at a waypoint (spawn, or after a lap of skips) advances
                # the course silently — no phantom split.
                if leg_started_at is not None and attempts > 0:
                    seconds = time.monotonic() - leg_started_at
                    origin = self.splits[-1]["to"] if self.splits else self.course[-1]
                    yards = distance_2d(origin[0], origin[1], target[0], target[1])
                    self.splits.append(
                        {
                            "leg": self.legs_completed + 1,
                            "to": target,
                            "seconds": round(seconds, 1),
                            "yards": round(yards, 1),
                            "attempts": attempts,
                        }
                    )
                    self.legs_completed += 1
                    trace(
                        "race_leg",
                        leg=self.legs_completed,
                        waypoint=target,
                        seconds=round(seconds, 1),
                        yards=round(yards, 1),
                        attempts=attempts,
                    )
                    log(
                        f"leg {self.legs_completed}: reached wp{index} in {seconds:.1f}s "
                        f"({attempts} attempts)"
                    )
                index = (index + 1) % len(self.course)
                if index == 0:
                    self.laps_completed += 1
                    trace("race_lap", lap=self.laps_completed)
                    say(f"wowborg lap {self.laps_completed} complete")
                    log(f"LAP {self.laps_completed} complete")
                attempts = 0
                leg_started_at = time.monotonic()
                continue

            if attempts >= MAX_LEG_ATTEMPTS:
                self.legs_skipped += 1
                trace("race_leg_skipped", waypoint=target, attempts=attempts)
                log(f"wp{index}: SKIPPED after {attempts} attempts (DNF)")
                index = (index + 1) % len(self.course)
                attempts = 0
                leg_started_at = time.monotonic()
                continue

            if leg_started_at is None:
                leg_started_at = time.monotonic()
            attempts += 1
            request_id = bridge.select_move_to(frame, target[0], target[1], target[2], loc.map_id)
            if request_id is None:
                log(f"wp{index}: move refused by mask (attempt {attempts}); taking recommended")
                request_id = bridge.select_recommended(frame)
                if request_id is None:
                    continue
            remaining = until - time.monotonic()
            if remaining <= 0:
                break
            outcome = bridge.wait_for_settlement(
                frame.frame_id, timeout_s=min(LEG_TIMEOUT_SECONDS, remaining)
            )
            if outcome is None:
                log(f"wp{index}: settlement TIMEOUT (attempt {attempts})")
            elif not outcome.success:
                log(f"wp{index}: settled unsuccessfully ({outcome.detail!r}, attempt {attempts})")

        summary = self.summary()
        trace("race_end", **summary)
        log(f"race done: {json.dumps(summary)}")
        say(
            f"wowborg race done: {self.laps_completed} laps, "
            f"{self.legs_completed} legs"
        )
