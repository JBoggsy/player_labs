"""Nav test policy: race through a randomized subset of landmark waypoints, timed.

THE CATALOG. Named, tiered landmarks in Durotar (map 1), all taken from the game
repo's AUTHORED leveling profile (`player/bots/leveling/profiles/durotar_troll_shaman.nim`)
— every point is a route node or hunt-area anchor King Richard's own bot provably
navigates to, so reachability is grounded, not guessed. Tiers by distance from the
orc/troll fresh-start spawn (-618.5, -4251.7):

- near  (< 150 yd): inside the Valley of Trials bowl
- mid   (150-450 yd): valley rim / Sarkoth's mesa / the exit gate corridor
- far   (> 450 yd): out the valley gate — Razor Hill road, Sen'jin Village coast

COURSE SELECTION. Each session builds its course by sampling a random subset (default
5 waypoints: ~2 near / ~2 mid / ~1 far) in random order, so races vary while staying
comparable through per-leg splits keyed to named waypoints. ``WOWBORG_RACE_SEED`` makes
a course reproducible (A/B: same seed both arms). ``WOWBORG_WAYPOINTS`` /
``WOWBORG_WAYPOINTS_FILE`` (JSON ``[[x,y,z], ...]``) still override with a fixed course.

RACE SEMANTICS. Visit waypoints strictly in order; a leg completes when the observed
position is within ``arrival_tolerance`` of the waypoint. One `move` settlement advances
only one route CHUNK (~30-50 yd on the live controller — first race batch evidence), so
legs are PROGRESS-based, not attempt-capped: keep re-issuing the move while distance to
the target shrinks; a DNF requires ``MAX_NO_PROGRESS`` consecutive settlements without
progress OR blowing the distance-scaled time budget. After two consecutive
no-progress settlements the policy interleaves the planner's recommended action (its
unstick logic) before retrying — the first batch showed a bot wedged repeating "no safe
adjacent edge" 174 times with no recovery. Laps repeat (fresh shuffle each lap) until
the deadline. Every leg emits a ``race_leg`` trace event (waypoint name, wall-clock
split, straight-line yards, move count); the summary reports completion rate and
yards/second — the race metrics.
"""

from __future__ import annotations

import json
import math
import os
import random
import time

# name -> (x, y, z, tier). Sources: durotar_troll_shaman.nim (authored route nodes,
# trainer/vendor spawns, hunt-area anchors); spawn cross-checked against our own
# hosted traces. All map 1 (Kalimdor/Durotar).
WAYPOINT_CATALOG: dict[str, tuple[float, float, float, str]] = {
    # --- near: the Valley of Trials bowl (< 150 yd from spawn) ---
    "spawn-plaza":        (-618.5, -4251.7, 38.7, "near"),   # fresh-start spawn
    "valley-trainers":    (-623.9, -4203.9, 38.4, "near"),   # class-trainer row (Shikrik spawn)
    "boar-yard":          (-715.0, -4240.0, 40.0, "near"),   # Mottled Boar hunt anchor
    "sleeping-peons":     (-628.5, -4340.7, 41.8, "near"),   # Lazy Peons field (south)
    "scorpid-field-edge": (-600.1, -4186.2, 41.3, "near"),   # staging node toward the east field
    # --- mid: rim, mesa, gate corridor (150-450 yd) ---
    "east-scorpid-field": (-405.0, -4118.0, 51.0, "mid"),    # Hana'zua's scorpid flats
    "sarkoth-mesa":       (-547.3, -4103.9, 70.1, "mid"),    # Sarkoth's den atop the mesa (elevation!)
    "gate-corridor":      (-359.7, -4309.8, 49.9, "mid"),    # authored route node at the valley exit
    "northwest-ridge":    (-753.6, -4143.2, 38.8, "mid"),    # NW hunt pocket past the boar yard
    # --- far: out the gate (> 450 yd; real Detour road work) ---
    "razor-hill-road":    (-825.6, -4920.8, 19.7, "far"),    # Razor Hill approach (authored node)
    "senjin-village":     (-797.5, -4921.2, 23.0, "far"),    # Sen'jin Village center
}

DEFAULT_SUBSET_BY_TIER = {"near": 2, "mid": 2, "far": 1}

WAYPOINTS_ENV = "WOWBORG_WAYPOINTS"
WAYPOINTS_FILE_ENV = "WOWBORG_WAYPOINTS_FILE"
RACE_SEED_ENV = "WOWBORG_RACE_SEED"

ARRIVAL_TOLERANCE_YARDS = 8.0
# A leg fails only when it stops making progress, not after N chunk-moves:
MAX_NO_PROGRESS = 4            # consecutive settlements with < PROGRESS_EPSILON gain
PROGRESS_EPSILON_YARDS = 3.0
UNSTICK_AFTER_NO_PROGRESS = 2  # interleave the planner's recommendation this early
LEG_BUDGET_BASE_SECONDS = 30.0     # + distance-scaled component
LEG_BUDGET_SECONDS_PER_YARD = 0.5  # ~2 yd/s observed pace → 0.5 s/yd doubles as slack
FRAME_TIMEOUT_SECONDS = 60.0
SETTLE_TIMEOUT_SECONDS = 30.0

BREADCRUMBS_ENV = "WOWBORG_BREADCRUMBS"
DEFAULT_BREADCRUMBS = "minimal"


def log(message: str) -> None:
    print(f"WOWBORG-POLICY {message}", flush=True)


def sample_course(rng: random.Random) -> list[tuple[str, list[float]]]:
    """Random subset of the catalog (tier-balanced), in random order."""
    course: list[tuple[str, list[float]]] = []
    for tier, count in DEFAULT_SUBSET_BY_TIER.items():
        names = [n for n, (_, _, _, t) in WAYPOINT_CATALOG.items() if t == tier]
        for name in rng.sample(names, min(count, len(names))):
            x, y, z, _ = WAYPOINT_CATALOG[name]
            course.append((name, [x, y, z]))
    rng.shuffle(course)
    return course


def load_course(rng: random.Random | None = None) -> list[tuple[str, list[float]]]:
    """Fixed course from env when supplied; else a random catalog subset."""
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
                return [
                    (f"wp{i}", [float(v) for v in p]) for i, p in enumerate(course)
                ]
            log("ignoring malformed waypoint course (need >=2 [x,y,z] points)")
        except json.JSONDecodeError as exc:
            log(f"ignoring unparseable waypoint course: {exc}")
    seed = os.environ.get(RACE_SEED_ENV)
    if rng is None:
        rng = random.Random(int(seed)) if seed and seed.lstrip("-").isdigit() else random.Random()
    return sample_course(rng)


def distance_2d(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


class WaypointRacePolicy:
    def __init__(
        self,
        course: list[tuple[str, list[float]]] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        seed = os.environ.get(RACE_SEED_ENV)
        self._rng = rng or (
            random.Random(int(seed)) if seed and seed.lstrip("-").isdigit() else random.Random()
        )
        self.course = course if course is not None else load_course(self._rng)
        self.legs_completed = 0
        self.legs_skipped = 0
        self.laps_completed = 0
        self.total_race_seconds = 0.0
        self.splits: list[dict] = []  # per completed leg: name, seconds, yards, attempts

    def summary(self) -> dict:
        yards = sum(s["yards"] for s in self.splits)
        seconds = sum(s["seconds"] for s in self.splits)
        attempted = self.legs_completed + self.legs_skipped
        return {
            "course": [name for name, _ in self.course],
            "legs_completed": self.legs_completed,
            "legs_skipped": self.legs_skipped,
            "completion_rate": round(self.legs_completed / attempted, 3) if attempted else None,
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
        trace("race_start", course=[{"name": n, "point": p} for n, p in self.course])
        log(f"course: {[n for n, _ in self.course]}, racing until deadline")

        index = 0
        moves = 0
        no_progress_streak = 0
        best_distance: float | None = None
        leg_started_at: float | None = None
        leg_origin: list[float] | None = None
        leg_budget: float | None = None

        def advance(completed_leg: bool, loc, name: str, target: list[float]) -> None:
            nonlocal index, moves, no_progress_streak, best_distance, leg_started_at, leg_origin, leg_budget
            index += 1
            if index >= len(self.course):
                index = 0
                self.laps_completed += 1
                trace("race_lap", lap=self.laps_completed)
                if completed_leg:
                    say(f"wowborg lap {self.laps_completed} complete")
                log(f"LAP {self.laps_completed} complete — reshuffling course")
                self._rng.shuffle(self.course)
            moves = 0
            no_progress_streak = 0
            best_distance = None
            leg_started_at = time.monotonic()
            leg_origin = [loc.x, loc.y]
            next_name, next_target = self.course[index]
            leg_budget = LEG_BUDGET_BASE_SECONDS + LEG_BUDGET_SECONDS_PER_YARD * distance_2d(
                loc.x, loc.y, next_target[0], next_target[1]
            )

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
                    bridge.wait_for_settlement(frame.frame_id, timeout_s=SETTLE_TIMEOUT_SECONDS)
                continue

            name, target = self.course[index]
            loc = obs.location
            to_target = distance_2d(loc.x, loc.y, target[0], target[1])

            # Arrived?
            if to_target <= ARRIVAL_TOLERANCE_YARDS:
                # A leg only COUNTS if we actually raced it (≥1 move);
                # standing at a waypoint advances silently — no phantom split.
                if leg_started_at is not None and moves > 0 and leg_origin is not None:
                    seconds = time.monotonic() - leg_started_at
                    yards = distance_2d(leg_origin[0], leg_origin[1], target[0], target[1])
                    self.splits.append(
                        {
                            "leg": self.legs_completed + 1,
                            "name": name,
                            "to": target,
                            "seconds": round(seconds, 1),
                            "yards": round(yards, 1),
                            "attempts": moves,
                        }
                    )
                    self.legs_completed += 1
                    trace(
                        "race_leg",
                        leg=self.legs_completed,
                        name=name,
                        waypoint=target,
                        seconds=round(seconds, 1),
                        yards=round(yards, 1),
                        attempts=moves,
                    )
                    log(
                        f"leg {self.legs_completed}: reached {name} in {seconds:.1f}s "
                        f"({yards:.0f} yd straight-line, {moves} moves)"
                    )
                advance(True, loc, name, target)
                continue

            # Leg failure: only on sustained no-progress or a blown time budget.
            over_budget = (
                leg_started_at is not None
                and leg_budget is not None
                and time.monotonic() - leg_started_at > leg_budget
            )
            if no_progress_streak >= MAX_NO_PROGRESS or over_budget:
                reason = "budget" if over_budget else "no_progress"
                self.legs_skipped += 1
                trace(
                    "race_leg_skipped",
                    name=name,
                    waypoint=target,
                    attempts=moves,
                    reason=reason,
                    remaining_yd=round(to_target, 1),
                )
                log(f"{name}: SKIPPED ({reason}) after {moves} moves, {to_target:.0f} yd short (DNF)")
                advance(False, loc, name, target)
                continue

            if leg_started_at is None:
                leg_started_at = time.monotonic()
                leg_origin = [loc.x, loc.y]
                leg_budget = LEG_BUDGET_BASE_SECONDS + LEG_BUDGET_SECONDS_PER_YARD * to_target

            # Progress bookkeeping: did the last settlement move us closer?
            if best_distance is None or to_target < best_distance - PROGRESS_EPSILON_YARDS:
                best_distance = to_target
                no_progress_streak = 0
            else:
                no_progress_streak += 1

            # Wedged? Let the planner's own recommendation run once (its unstick logic)
            # before re-issuing our move — the observed failure mode is a bot repeating
            # "no safe adjacent edge" forever from the same spot.
            if no_progress_streak >= UNSTICK_AFTER_NO_PROGRESS and frame.recommended_action is not None:
                log(f"{name}: {no_progress_streak} stalled settlements — taking recommended (unstick)")
                request_id = bridge.select_recommended(frame)
                if request_id is not None:
                    bridge.wait_for_settlement(frame.frame_id, timeout_s=SETTLE_TIMEOUT_SECONDS)
                    continue

            moves += 1
            request_id = bridge.select_move_to(frame, target[0], target[1], target[2], loc.map_id)
            if request_id is None:
                log(f"{name}: move refused by mask (move {moves}); taking recommended")
                request_id = bridge.select_recommended(frame)
                if request_id is None:
                    continue
            remaining = until - time.monotonic()
            if remaining <= 0:
                break
            outcome = bridge.wait_for_settlement(
                frame.frame_id, timeout_s=min(SETTLE_TIMEOUT_SECONDS, remaining)
            )
            if outcome is None:
                log(f"{name}: settlement TIMEOUT (move {moves})")
            elif not outcome.success:
                log(f"{name}: settled unsuccessfully ({outcome.detail!r}, move {moves})")

        summary = self.summary()
        trace("race_end", **summary)
        log(f"race done: {json.dumps(summary)}")
        say(
            f"wowborg race done: {self.laps_completed} laps, "
            f"{self.legs_completed} legs"
        )
