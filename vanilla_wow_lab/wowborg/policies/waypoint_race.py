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

# name -> (x, y, z, tier, via). Sources: durotar_troll_shaman.nim (authored route
# nodes, trainer/vendor spawns, hunt-area anchors); spawn cross-checked against our own
# hosted traces. All map 1 (Kalimdor/Durotar).
#
# `via` = staging waypoints (catalog names, visited loosely en route) for targets the
# executor cannot route to DIRECTLY — mirrors the authored profile's approachRoutes.
# v6 race evidence: sarkoth-mesa / east-scorpid-field / northwest-ridge DNF'd with
# "no goal-relative progress" at consistent distances (the valley wall / disconnected
# mesa); the profile itself routes them through these staging nodes.
WAYPOINT_CATALOG: dict[str, tuple[float, float, float, str, tuple[str, ...]]] = {
    # --- near: the Valley of Trials bowl (< 150 yd from spawn) ---
    "spawn-plaza":        (-618.5, -4251.7, 38.7, "near", ()),   # fresh-start spawn
    "valley-trainers":    (-623.9, -4203.9, 38.4, "near", ()),   # class-trainer row
    "boar-yard":          (-715.0, -4240.0, 40.0, "near", ()),   # Mottled Boar anchor
    "sleeping-peons":     (-628.5, -4340.7, 41.8, "near", ()),   # Lazy Peons field
    "scorpid-field-edge": (-600.1, -4186.2, 41.3, "near", ()),   # authored staging node
    # --- staging-only nodes (authored approachRoute points; never sampled) ---
    "field-shelf-1":      (-560.3, -4235.5, 43.9, "stage", ()),  # steep-choke bypass
    "field-shelf-2":      (-514.3, -4284.2, 40.7, "stage", ()),
    "field-shelf-3":      (-482.2, -4216.1, 50.1, "stage", ()),
    "field-shelf-4":      (-457.3, -4156.4, 47.6, "stage", ()),
    # South descent to Sen'jin — sampled from wowborg's OWN successful v6 trajectory
    # (362s, gate never involved). v14 lesson: the first sampled point (-614,-4391)
    # sat in the wall pocket where two bots stalled; use the v6 path's FARTHER-south
    # samples, which are past the choke, and let Detour handle the top of the descent.
    "south-descent-1":    (-645.0, -4489.0, 28.0, "stage", ()),
    "south-descent-2":    (-632.0, -4665.0, 25.0, "stage", ()),
    "south-descent-3":    (-736.0, -4823.0, 22.0, "stage", ()),
    # --- mid: rim / gate corridor (150-450 yd) ---
    "gate-corridor":      (-359.7, -4309.8, 49.9, "mid", ()),    # authored valley-exit node
    "field-shelf-far":    (-457.3, -4156.4, 47.6, "mid",
                           ("scorpid-field-edge", "field-shelf-1", "field-shelf-2",
                            "field-shelf-3")),  # deepest reliably-reached shelf point
    # --- far: Sen'jin Village (> 450 yd; real Detour road work) ---
    # Staged along wowborg's own PROVEN v6 trajectory: straight south from the valley
    # at x≈-620, descending to the coast road (362s door-to-door). NOT via the eastern
    # gate — v12/v13 traces show the executor jams at the gate ramp (-360,-4310) when
    # given Sen'jin from there (Detour path crosses Tiragarde-side terrain it refuses
    # to chunk); the authored (-100,-4980) bend is likewise the Razor-Hill-origin
    # route, wrong for a valley origin.
    "senjin-gadrin":      (-825.6, -4920.8, 19.7, "far",
                           ("south-descent-1", "south-descent-2", "south-descent-3")),
    "senjin-village":     (-797.5, -4921.2, 23.0, "far",
                           ("south-descent-1", "south-descent-2", "south-descent-3")),
    # --- hard: unreliable at this executor's pace — 4 hosted batches of evidence
    # (northwest-ridge 0/8 completions; the east-field family ~2/12 even with the full
    # authored shelf chain). Sampled ONLY by stress courses (count 0 by default); kept
    # because they're the benchmark for future navigation improvements. ---
    "east-scorpid-field": (-405.0, -4118.0, 51.0, "hard",
                           ("scorpid-field-edge", "field-shelf-1", "field-shelf-2",
                            "field-shelf-3", "field-shelf-4")),
    "hanazua-rock":       (-397.8, -4109.0, 50.3, "hard",
                           ("scorpid-field-edge", "field-shelf-1", "field-shelf-2",
                            "field-shelf-3", "field-shelf-4")),
    "sarkoth-mesa":       (-547.3, -4103.9, 70.1, "hard",
                           ("scorpid-field-edge", "field-shelf-1", "field-shelf-2",
                            "field-shelf-3", "field-shelf-4", "hanazua-rock")),
    "northwest-ridge":    (-753.6, -4143.2, 38.8, "hard", ("boar-yard",)),
}

# Course composition for a ~970s episode at the executor's observed ~2 yd/s ceiling:
# near legs 30-150s, mid 130-180s, a far leg 450-650s (v16 measurements). 2 near +
# 1 mid + 1 far ≈ 700-900s typical — completable with the far leg anywhere in the
# random order. "hard" defaults to 0 (stress-only); override via WOWBORG_COURSE_TIERS
# (JSON, e.g. {"near":1,"mid":1,"hard":2}).
DEFAULT_SUBSET_BY_TIER = {"near": 2, "mid": 1, "far": 1}
COURSE_TIERS_ENV = "WOWBORG_COURSE_TIERS"

WAYPOINTS_ENV = "WOWBORG_WAYPOINTS"
WAYPOINTS_FILE_ENV = "WOWBORG_WAYPOINTS_FILE"
RACE_SEED_ENV = "WOWBORG_RACE_SEED"

ARRIVAL_TOLERANCE_YARDS = 8.0
# Staging nodes are corridor GUIDES, not targets: clear them from much farther out.
# v14 evidence: bots stalled 20-30 yd from a descent node pressed against the valley
# wall — close enough to be through the corridor, too far for target-grade clearing.
STAGE_CLEAR_YARDS = 35.0
# A leg fails only when the character genuinely STOPS: a settlement counts as stalled
# only when it neither improved goal distance NOR physically moved us (v7 evidence:
# roads bend, so goal distance can stagnate for several chunks while the executor is
# legitimately walking — displacement disambiguates "detouring" from "wedged").
MAX_NO_PROGRESS = 6
PROGRESS_EPSILON_YARDS = 3.0
DISPLACEMENT_EPSILON_YARDS = 5.0
UNSTICK_AFTER_NO_PROGRESS = 3  # interleave the planner's recommendation this early
LEG_BUDGET_BASE_SECONDS = 60.0     # + distance-scaled component
# v15 evidence: far legs walk the descent steadily at ~1.3-1.5 yd/s over an actual
# path ~1.2x the staged straight-line, then die to budget 400 yd short. 1.0 s/yd
# funds the observed pace with slack; a still-progressing leg deserves its time.
LEG_BUDGET_SECONDS_PER_YARD = 1.0
FRAME_TIMEOUT_SECONDS = 60.0
SETTLE_TIMEOUT_SECONDS = 30.0

BREADCRUMBS_ENV = "WOWBORG_BREADCRUMBS"
DEFAULT_BREADCRUMBS = "minimal"


def log(message: str) -> None:
    print(f"WOWBORG-POLICY {message}", flush=True)


def waypoint_point(name: str) -> list[float]:
    x, y, z, _, _ = WAYPOINT_CATALOG[name]
    return [x, y, z]


def waypoint_via(name: str) -> tuple[str, ...]:
    return WAYPOINT_CATALOG[name][4] if name in WAYPOINT_CATALOG else ()


def course_tiers() -> dict[str, int]:
    raw = os.environ.get(COURSE_TIERS_ENV)
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and all(
                isinstance(v, int) and v >= 0 for v in parsed.values()
            ):
                return parsed
            log("ignoring malformed WOWBORG_COURSE_TIERS (need {tier: count})")
        except json.JSONDecodeError as exc:
            log(f"ignoring unparseable WOWBORG_COURSE_TIERS: {exc}")
    return dict(DEFAULT_SUBSET_BY_TIER)


def sample_course(rng: random.Random) -> list[tuple[str, list[float]]]:
    """Random subset of the catalog (tier-balanced), in random order.

    Stage-tier nodes are routing infrastructure, never race targets; hard-tier nodes
    are sampled only when WOWBORG_COURSE_TIERS asks for them.
    """
    course: list[tuple[str, list[float]]] = []
    for tier, count in course_tiers().items():
        names = [n for n, entry in WAYPOINT_CATALOG.items() if entry[3] == tier]
        for name in rng.sample(names, min(count, len(names))):
            course.append((name, waypoint_point(name)))
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
        last_position: tuple[float, float] | None = None
        leg_started_at: float | None = None
        leg_origin: list[float] | None = None
        leg_budget: float | None = None
        # Staging queue for the current leg: via nodes not yet passed. The race clock
        # covers the whole leg (via + final) — staging is a routing aid, not a split.
        stage_queue: list[tuple[str, list[float]]] = []
        # Hysteresis: nodes stay "passed" until we drift far from them. v12 evidence:
        # without this, Detour's first chunk toward the next goal can step slightly
        # away from a just-passed node, the positional recompute re-arms it, and the
        # bot flip-flops at the node forever (90-move oscillation at the gate).
        passed_stages: dict[str, list[float]] = {}
        STAGE_REARM_YARDS = 100.0

        def build_stages(name: str, current_x: float, current_y: float) -> list[tuple[str, list[float]]]:
            """Ordered staging nodes for this target, starting from where we are.

            Drop the PREFIX of the chain that is already behind us (nearest-suffix),
            and drop any node in passed_stages (hysteresis) — a passed node re-arms
            only if we've drifted STAGE_REARM_YARDS from it (a genuine relocation,
            e.g. a planner recovery, not Detour chunk jitter).
            """
            for passed_name, point in list(passed_stages.items()):
                if distance_2d(current_x, current_y, point[0], point[1]) > STAGE_REARM_YARDS:
                    del passed_stages[passed_name]
            chain = [
                (v, waypoint_point(v))
                for v in waypoint_via(name)
                if v not in passed_stages
            ]
            if not chain:
                return []
            nearest = min(
                range(len(chain)),
                key=lambda i: distance_2d(current_x, current_y, chain[i][1][0], chain[i][1][1]),
            )
            nearest_d = distance_2d(
                current_x, current_y, chain[nearest][1][0], chain[nearest][1][1]
            )
            start = nearest + 1 if nearest_d <= STAGE_CLEAR_YARDS else nearest
            for passed_name, point in chain[:start]:
                passed_stages[passed_name] = point
            return chain[start:]

        def advance(completed_leg: bool, loc, name: str, target: list[float]) -> None:
            nonlocal index, moves, no_progress_streak, best_distance, last_position, leg_started_at, leg_origin, leg_budget, stage_queue
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
            last_position = None
            passed_stages.clear()  # hysteresis is per-leg
            leg_started_at = time.monotonic()
            leg_origin = [loc.x, loc.y]
            next_name, next_target = self.course[index]
            stage_queue = build_stages(next_name, loc.x, loc.y)
            # Budget covers the staged path, not the straight line.
            path_yd = 0.0
            px, py = loc.x, loc.y
            for _, sp in [*stage_queue, (next_name, next_target)]:
                path_yd += distance_2d(px, py, sp[0], sp[1])
                px, py = sp[0], sp[1]
            leg_budget = LEG_BUDGET_BASE_SECONDS + LEG_BUDGET_SECONDS_PER_YARD * path_yd

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

            # Staging is POSITIONAL, recomputed every frame: steer at the first chain
            # node ahead of us. (v8 evidence: a pop-once queue broke when a planner
            # recovery relocated the bot back inside the valley — the popped gate
            # node never re-entered and the bot tried to cross the wall directly.)
            new_stages = build_stages(name, loc.x, loc.y)
            if [s[0] for s in new_stages] != [s[0] for s in stage_queue]:
                stage_queue = new_stages
                no_progress_streak = 0
                best_distance = None
                if stage_queue:
                    log(f"{name}: staging via {[s[0] for s in stage_queue]}")
            steer_name, steer_point = (
                stage_queue[0] if stage_queue else (name, target)
            )
            to_target = distance_2d(loc.x, loc.y, target[0], target[1])
            to_steer = distance_2d(loc.x, loc.y, steer_point[0], steer_point[1])

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

            # Leg failure: only on sustained no-progress or a blown time budget —
            # but a leg that is STILL MOVING gets to keep its budget (v15: far legs
            # died to the clock while walking steadily; a budget exists to cut
            # wedged legs loose, not to cap honest travel time).
            over_budget = (
                leg_started_at is not None
                and leg_budget is not None
                and time.monotonic() - leg_started_at > leg_budget
                and no_progress_streak > 0  # moving legs never budget out
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
                stage_queue = build_stages(name, loc.x, loc.y)
                steer_name, steer_point = stage_queue[0] if stage_queue else (name, target)
                to_steer = distance_2d(loc.x, loc.y, steer_point[0], steer_point[1])
                leg_budget = LEG_BUDGET_BASE_SECONDS + LEG_BUDGET_SECONDS_PER_YARD * to_target

            # Progress bookkeeping: a settlement is stalled only if it neither improved
            # distance to the CURRENT steering point NOR physically displaced us
            # (roads bend — walking a detour is progress even when goal distance isn't
            # shrinking; a wedged bot does neither).
            displaced = (
                last_position is not None
                and distance_2d(loc.x, loc.y, last_position[0], last_position[1])
                > DISPLACEMENT_EPSILON_YARDS
            )
            if best_distance is None or to_steer < best_distance - PROGRESS_EPSILON_YARDS:
                best_distance = to_steer
                no_progress_streak = 0
            elif displaced:
                no_progress_streak = 0
            else:
                no_progress_streak += 1
            last_position = (loc.x, loc.y)

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
            request_id = bridge.select_move_to(
                frame, steer_point[0], steer_point[1], steer_point[2], loc.map_id
            )
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
