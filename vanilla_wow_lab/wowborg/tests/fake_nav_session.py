"""A frame-driven fake Gym session with a scripted world for nav-layer tests.

Simulates: chunked movement (the executor's ~14yd settlements), walls (regions that
block movement), combat zones, death zones, portals (map transitions), and a scripted
route planner — so L0/L1/L2 logic is tested against the failure modes the audit named
without a live server.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from wowborg.types import ActionOutcome, PlannedRoute, Position


@dataclass
class FakeLocation:
    map_id: int = 1
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    orientation: float = 0.0


@dataclass
class FakeFrame:
    frame_id: int
    location: FakeLocation = field(default_factory=FakeLocation)
    is_dead: bool = False
    is_ghost: bool = False
    in_combat: bool = False
    health: int = 60
    max_health: int = 60
    active_area_trigger_ids: list[int] = field(default_factory=list)
    known_spells: list[int] = field(default_factory=list)


class NavWorldSession:
    """Scripted world: movement advances CHUNK_YARDS toward the destination per
    settlement, unless blocked by a wall segment. Configurable hazards."""

    CHUNK_YARDS = 14.0

    def __init__(
        self,
        *,
        start: tuple[int, float, float, float] = (1, 0.0, 0.0, 0.0),
        walls: list[tuple[float, float, float]] | None = None,  # (x, y, radius) blocks
        combat_at: tuple[float, float, float] | None = None,     # entering radius → combat N frames
        combat_frames: int = 3,
        death_at: tuple[float, float, float] | None = None,      # entering radius → die once
        graveyard: tuple[int, float, float, float] | None = None,
        portals: dict[int, tuple[int, float, float, float]] | None = None,  # trigger_id → dest
        portal_pads: dict[int, tuple[float, float, float]] | None = None,   # trigger_id → pad pos
        route_status: str = "ok",
        route_detour: float = 1.15,  # planned distance multiplier vs straight line
        planner_available: bool = True,
        probe_broken: bool = False,  # self-probe (here→here) also fails: broken planner
    ) -> None:
        self.map_id, self.x, self.y, self.z = start
        self.walls = walls or []
        self.health = 60  # tests set <30 to model a losing fight (yield threshold)
        self.combat_at = combat_at
        self.combat_frames_left = 0
        self.combat_frames = combat_frames
        self.death_at = death_at
        self.died_once = False
        self.dead_frames_left = 0
        self.graveyard = graveyard or start
        self.portals = portals or {}
        # Trigger bindings are SPATIAL (codex audit #6: the fake used to offer
        # every portal everywhere, so a wrong pad coordinate could never fail
        # a test). Default pads sit at the trigger's destination-facing spot.
        self.portal_pads = portal_pads or {}
        self.portal_pad_radius = 10.0
        self.route_status = route_status
        self.route_detour = route_detour
        self.planner_available = planner_available
        self.probe_broken = probe_broken
        self._frame = 0
        self._tracer = None
        self.plan_calls = 0
        self.move_selections = 0
        self.wait_selections = 0

    # ---- frames -------------------------------------------------------------

    def wait_for_frame(self, *, timeout_s: float = 60.0) -> FakeFrame:
        self._frame += 1
        return FakeFrame(
            frame_id=self._frame,
            location=FakeLocation(self.map_id, self.x, self.y, self.z),
            is_dead=self.dead_frames_left > 0,
            is_ghost=False,
            in_combat=self.combat_frames_left > 0,
            health=self.health,
            max_health=60,
            active_area_trigger_ids=[
                tid for tid in self.portals if self._near_portal(tid)
            ],
        )

    def observe(self):
        return FakeFrame(
            frame_id=self._frame,
            location=FakeLocation(self.map_id, self.x, self.y, self.z),
            health=self.health,
            max_health=60,
            in_combat=self.combat_frames_left > 0,
            is_dead=self.dead_frames_left > 0,
            is_ghost=False,
        )

    # ---- actions -------------------------------------------------------------

    def select_move_to(self, frame, x, y, z, map_id) -> str:
        self.move_selections += 1
        self._advance_toward(x, y, z)
        return f"frame-{frame.frame_id}"

    def select_wait(self, frame) -> str:
        self.wait_selections += 1
        # Recommended action resolves hazards: combat ticks down, death→revive at
        # graveyard, otherwise a small shuffle (unstick).
        if self.dead_frames_left > 0:
            self.dead_frames_left -= 1
            if self.dead_frames_left == 0:
                self.map_id, self.x, self.y, self.z = self.graveyard
        elif self.combat_frames_left > 0:
            self.combat_frames_left -= 1
        else:
            self.x += 1.0
        return f"frame-{frame.frame_id}"

    def select_area_trigger(self, frame, trigger_id) -> str | None:
        selected = trigger_id
        if selected is None and frame.active_area_trigger_ids:
            selected = frame.active_area_trigger_ids[0]
        if selected in frame.active_area_trigger_ids and selected in self.portals:
            self.map_id, self.x, self.y, self.z = self.portals[selected]
            return f"frame-{frame.frame_id}"
        return None

    def wait_for_settlement(self, frame_id, *, timeout_s=90.0) -> ActionOutcome:
        return ActionOutcome(
            request_id=f"frame-{frame_id}", kind="move", success=True,
            settlement_kind=None, displacement_yards=None, end_position=None,
            detail="fake settlement", frame_id=frame_id, settled_tick=self._frame,
        )

    # ---- planning --------------------------------------------------------------

    def plan_route(self, source, target, map_id, *, arrival_radius=3.0,
                   tile_load_mode="auto") -> PlannedRoute:
        self.plan_calls += 1
        if not self.planner_available:
            return PlannedRoute("unavailable", map_id, [], 0.0, False, None, False, "off")
        if (not self.probe_broken
                and math.dist((source.x, source.y, source.z),
                              (target.x, target.y, target.z)) < 1.0):
            # Self-probe (L1's planner-health check): a working planner always
            # routes a point to itself, regardless of the scripted route status.
            return PlannedRoute("ok", map_id, [Position(target.x, target.y, target.z, 0.0)],
                                0.0, False, 0.0, False, "")
        if self.route_status != "ok":
            return PlannedRoute(self.route_status, map_id, [], 0.0,
                                self.route_status == "partial", None, False, "scripted")
        # Straight-line waypoint chain every CHUNK*2 yards, detour-inflated distance.
        sx, sy, sz = source.x, source.y, source.z
        tx, ty, tz = target.x, target.y, target.z
        dist = math.dist((sx, sy, sz), (tx, ty, tz))
        n = max(2, int(dist / (self.CHUNK_YARDS * 2)))
        waypoints = [
            Position(sx + (tx - sx) * i / n, sy + (ty - sy) * i / n,
                     sz + (tz - sz) * i / n, 0.0)
            for i in range(1, n + 1)
        ]
        return PlannedRoute("ok", map_id, waypoints, dist * self.route_detour,
                            False, 0.5, False, "")

    # ---- world physics -----------------------------------------------------------

    def _advance_toward(self, x: float, y: float, z: float) -> None:
        if self.dead_frames_left > 0:
            return
        in_combat = self.combat_frames_left > 0
        if in_combat:
            # Fleeing works: moving while in combat runs out of the mob's leash
            # (combat ticks down); movement continues at reduced pace — the live
            # executor keeps walking between interrupts.
            self.combat_frames_left -= 1
        dx, dy, dz = x - self.x, y - self.y, z - self.z
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist < 0.01:
            return
        step = min(self.CHUNK_YARDS * (0.5 if in_combat else 1.0), dist)
        nx = self.x + dx / dist * step
        ny = self.y + dy / dist * step
        nz = self.z + dz / dist * step
        for wx, wy, radius in self.walls:
            if math.hypot(nx - wx, ny - wy) <= radius:
                return  # blocked: no movement this settlement
        self.x, self.y, self.z = nx, ny, nz
        if self.combat_at is not None:
            cx, cy, radius = self.combat_at
            if math.hypot(self.x - cx, self.y - cy) <= radius:
                self.combat_frames_left = self.combat_frames
                self.combat_at = None  # one ambush
        if self.death_at is not None and not self.died_once:
            dx2, dy2, radius = self.death_at
            if math.hypot(self.x - dx2, self.y - dy2) <= radius:
                self.died_once = True
                self.dead_frames_left = 3

    def _near_portal(self, trigger_id: int) -> bool:
        pad = self.portal_pads.get(trigger_id)
        if pad is None:
            return True  # no declared pad: binding offered anywhere (legacy tests)
        return math.dist((self.x, self.y, self.z), pad) <= self.portal_pad_radius
