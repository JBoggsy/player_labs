#!/usr/bin/env python3
"""Route lab — validate nav planning against the REAL world navmesh, locally.

Runs inside the pinned GAME image (which carries /vmangos-data/mmaps — the full
1,783-tile world navmesh — and /usr/local/bin/vmangos-navmesh-helper), driving the
actual L1/L2 code with real Detour plans and an idealized executor that walks the
returned corridors. This validates every PLANNING decision — reachability verdicts,
partial/projection handling, road routing, budgets, world-model coordinates — in
seconds instead of a ~1-hour hosted batch. What it cannot validate: the live
environment's locomotion and transport behavior (hosted evaluation still owns those).

Usage (from the repo root, via tools/route_lab.sh):
    route_lab.py stations              # every catalog station from the spawn
    route_lab.py course                # all configured stations, sequentially
    route_lab.py station NAME         # one station
    route_lab.py route X Y Z [MAP]    # ad-hoc target
"""

from __future__ import annotations

import math
import sys
import time

sys.path.insert(0, "/opt/wowborg")

from wowborg.nav.journey import JourneyPlanner, JourneyStatus
from wowborg.nav.world_model import Point
from wowborg.types import PlannedRoute, Position

SPAWN = Point(1, -618.518, -4251.67, 38.718)
# Idealized executor: walks a real Detour corridor at stock run speed.
RUN_SPEED_YDS_PER_S = 7.0

# Area triggers, from the game repo's fast-travel registry (bots/decision/
# fast_travel.py; evidence: VMaNGOS areatrigger_teleport + AreaTrigger.dbc).
# trigger_id → (pad map, pad x, y, z, activation radius, dest map, x, y, z)
AREA_TRIGGERS = {
    2230: (1, 1818.4, -4427.26, -20.56, 10.0, 389, 0.798, -8.234, -15.529),
}


class NavmeshWorldSession:
    """The real planner + an idealized executor.

    plan_route → the actual navmesh helper (real world geometry).
    Movement → advances along the last corridor toward the L0 destination;
    every frame settles instantly (no wall-clock waits, no combat).
    """

    def __init__(self, start: Point) -> None:
        self.here = start
        self.plan_calls = 0
        self.moves = 0
        self.sim_seconds = 0.0
        self._frame = 0

    # ---- planning (REAL) ---------------------------------------------------------

    def plan_route(self, source, target, map_id, *, arrival_radius=3.0,
                   tile_load_mode="auto") -> PlannedRoute:
        from environment.contract.agent import WorldPoint as NavPoint
        from player.sdk.navmesh.client import route_navmesh

        self.plan_calls += 1
        route = route_navmesh(
            NavPoint(map_id=map_id, x=source.x, y=source.y, z=source.z),
            NavPoint(map_id=map_id, x=target.x, y=target.y, z=target.z),
            arrival_radius=arrival_radius,
            tile_load_mode=tile_load_mode,
        )
        waypoints = [Position(w.x, w.y, w.z, 0.0) for w in (route.waypoints or [])]
        partial = bool(route.partial_path_end) or route.path_type == "partial"
        return PlannedRoute(
            status=route.status, map_id=route.map_id, waypoints=waypoints,
            route_distance=float(route.route_distance or 0.0), partial=partial,
            projected_target_distance=route.projected_target_distance,
            jump_required=bool(getattr(route, "jump_required", False)),
            message=route.message or "",
        )

    # ---- idealized executor ------------------------------------------------------

    def wait_for_frame(self, *, timeout_s: float = 60.0):
        self._frame += 1

        class Loc:
            pass

        class Frame:
            pass

        loc = Loc()
        loc.map_id, loc.x, loc.y, loc.z = (
            self.here.map_id, self.here.x, self.here.y, self.here.z)
        frame = Frame()
        frame.frame_id = self._frame
        frame.location = loc
        frame.is_dead = frame.is_ghost = frame.in_combat = False
        frame.health, frame.max_health = 100, 100
        frame.known_spells = []
        # Spatial trigger bindings — offered only when standing on a pad,
        # exactly like the live controller.
        near = [
            tid for tid, (pm, px, py, pz, radius, *_rest) in AREA_TRIGGERS.items()
            if self.here.map_id == pm
            and math.dist((self.here.x, self.here.y, self.here.z),
                          (px, py, pz)) <= radius
        ]
        frame.active_area_trigger_ids = near
        return frame

    def observe(self):
        return self.wait_for_frame()

    def select_move_to(self, frame, x, y, z, map_id) -> str:
        """Walk a REAL corridor toward (x,y,z), like the live executor's
        server-side Detour (≤8 waypoints ≈ one settlement chunk)."""
        self.moves += 1
        plan = self.plan_route(
            Position(self.here.x, self.here.y, self.here.z, 0.0),
            Position(x, y, z, 0.0), map_id)
        if not plan.waypoints:
            return f"frame-{frame.frame_id}"  # settles without movement (blocked)
        chunk = plan.waypoints[: 8]
        walked = 0.0
        prev = (self.here.x, self.here.y, self.here.z)
        for w in chunk:
            walked += math.dist(prev, (w.x, w.y, w.z))
            prev = (w.x, w.y, w.z)
        end = chunk[-1]
        self.here = Point(map_id, end.x, end.y, end.z)
        self.sim_seconds += walked / RUN_SPEED_YDS_PER_S
        return f"frame-{frame.frame_id}"

    def select_area_trigger(self, frame, trigger_id) -> str | None:
        selected = trigger_id
        if selected is None and frame.active_area_trigger_ids:
            selected = frame.active_area_trigger_ids[0]
        if selected in frame.active_area_trigger_ids:
            if selected in AREA_TRIGGERS:
                spec = AREA_TRIGGERS[selected]
                _pm, _px, _py, _pz, _rad, dm, dx, dy, dz = spec
                self.here = Point(dm, dx, dy, dz)
                self.sim_seconds += 3.0  # loading screen
                return f"frame-{frame.frame_id}"
        return None

    def select_wait(self, frame) -> str | None:
        return None

    def select_stuck(self, frame) -> str | None:
        return None

    def wait_for_settlement(self, frame_id, *, timeout_s=90.0):
        from wowborg.types import ActionOutcome

        return ActionOutcome(
            request_id=f"frame-{frame_id}", kind="move", success=True,
            settlement_kind=None, displacement_yards=None, end_position=None,
            detail="route-lab settlement", frame_id=frame_id, settled_tick=self._frame,
        )


class InstantDeadline:
    """monotonic-based deadline that tracks SIMULATED seconds, not wall clock."""


def run_station(name: str, target: Point, expected: str) -> dict:
    bridge = NavmeshWorldSession(SPAWN)
    journey = JourneyPlanner()
    started = time.monotonic()
    # Wall deadline generous — helper plan calls cost ~1-2s each and long
    # journeys make ~100 of them; sim time is the metric, not wall time.
    result = journey.journey_to(bridge, target, deadline=time.monotonic() + 600.0)
    wall = time.monotonic() - started
    outcome = ("arrived" if result.status == JourneyStatus.ARRIVED
               else f"failed_{result.reason}")
    # An expected-unreachable station is handled honestly by ANY fast typed
    # refusal: off-mesh targets → unreachable; unrepresented maps (other
    # continent, no transport edges) → unknown_region. Both are correct
    # "I cannot go there" verdicts; grinding or false arrival is the failure.
    ok = (outcome == "arrived") if expected == "reachable" else (
        outcome in ("failed_unreachable", "failed_unknown_region",
                    "failed_no_world_path"))
    return {
        "name": name, "expected": expected, "outcome": outcome, "ok": ok,
        "sim_seconds": round(bridge.sim_seconds, 1),
        "plans": bridge.plan_calls, "moves": bridge.moves,
        "wall_seconds": round(wall, 1),
        "end": (f"{bridge.here.map_id}:{bridge.here.x:.0f},{bridge.here.y:.0f},"
                f"{bridge.here.z:.0f}"),
        "legs": [f"{l['kind']}:{l['status']}" for l in result.legs],
    }


def run_course(stations: dict) -> list[dict]:
    """Run configured stations in insertion order as one continuous race."""

    session = NavmeshWorldSession(SPAWN)
    journey = JourneyPlanner()
    rows = []
    prior_sim_seconds = 0.0
    prior_plans = 0
    prior_moves = 0
    for name, (target, _region, expected) in stations.items():
        started = time.monotonic()
        result = journey.journey_to(
            session, target, deadline=time.monotonic() + 600.0
        )
        outcome = (
            "arrived"
            if result.status == JourneyStatus.ARRIVED
            else f"failed_{result.reason}"
        )
        ok = (outcome == "arrived") if expected == "reachable" else (
            outcome in (
                "failed_unreachable",
                "failed_unknown_region",
                "failed_no_world_path",
            )
        )
        rows.append(
            {
                "name": name,
                "expected": expected,
                "outcome": outcome,
                "ok": ok,
                "sim_seconds": round(session.sim_seconds - prior_sim_seconds, 1),
                "plans": session.plan_calls - prior_plans,
                "moves": session.moves - prior_moves,
                "wall_seconds": round(time.monotonic() - started, 1),
                "end": (
                    f"{session.here.map_id}:{session.here.x:.0f},"
                    f"{session.here.y:.0f},{session.here.z:.0f}"
                ),
                "legs": [f"{leg['kind']}:{leg['status']}" for leg in result.legs],
            }
        )
        prior_sim_seconds = session.sim_seconds
        prior_plans = session.plan_calls
        prior_moves = session.moves
    return rows


def main() -> int:
    # load_stations() honors WOWBORG_STATIONS (pass -e to docker) — the same
    # data seam as hosted, so held-out courses run here unchanged.
    from wowborg.policies.world_race import load_stations

    STATIONS = load_stations()

    args = sys.argv[1:]
    if args and args[0] == "course":
        rows = run_course(STATIONS)
    elif args and args[0] == "route":
        x, y, z = float(args[1]), float(args[2]), float(args[3])
        map_id = int(args[4]) if len(args) > 4 else 1
        rows = [run_station("adhoc", Point(map_id, x, y, z), "reachable")]
    elif args and args[0] == "station":
        point, region, expected = STATIONS[args[1]]
        rows = [run_station(args[1], point, expected)]
    else:
        rows = [run_station(n, p, e) for n, (p, r, e) in STATIONS.items()]

    print(f"\n{'station':<26} {'expected':<12} {'outcome':<24} {'ok':<4} "
          f"{'sim_s':>7} {'plans':>6} {'end'}")
    failures = 0
    for r in rows:
        if not r["ok"]:
            failures += 1
        print(f"{r['name']:<26} {r['expected']:<12} {r['outcome']:<24} "
              f"{'✓' if r['ok'] else '✗':<4} {r['sim_seconds']:>7} "
              f"{r['plans']:>6} {r['end']}")
        if not r["ok"]:
            print(f"    legs: {r['legs']}")
    print(f"\n{len(rows) - failures}/{len(rows)} stations behave as declared")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
