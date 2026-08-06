"""Kalimdor Traverse strategy: keep selecting reachable northbound frontiers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from player.sdk.navmesh.models import NAV_SEMANTIC_HAZARD

from wowborg.nav.route import NavState, RouteNavigator
from wowborg.nav.world_model import Point

KALIMDOR_MAP_ID = 1
TRAVERSE_START_WORLD_X = -9187.0
TRAVERSE_GOAL_WORLD_X = 6687.333052
FRONTIER_RADIUS_YARDS = 700.0
MIN_FRONTIER_DISTANCE_YARDS = 50.0
MAX_BACKTRACK_YARDS = 100.0
GOAL_RADIUS_YARDS = 8.0
CAT_FORM_SPELL_ID = 768
PROWL_SPELL_IDS = (9913, 6783, 5215)
TRAVEL_FORM_SPELL_ID = 783
PROWL_ROUTE_GUIDEPOINTS = 0

# Exact 0.1.160 Detour routes prove this prefix reaches the lower dock while
# avoiding every active Centipaar Wasp/Worker detection and wander envelope.
# Riding the lift remains separate so its hosted result stays attributable.
TRAVERSE_ROUTE_PREFIX = (
    ("tanaris-centipaar-bypass-1", Point(1, -8132.53, -2196.98, 7.41)),
    ("tanaris-centipaar-bypass-2", Point(1, -8032.96, -2228.0, -14.77)),
    ("tanaris-centipaar-bypass-3", Point(1, -7897.90, -2283.90, 22.30)),
    ("tanaris-centipaar-bypass-4", Point(1, -7577.28, -2467.20, -9.47)),
    ("great-lift-lower-dock", Point(1, -4677.066, -1853.667, -43.857)),
)


def _select_frontier(graph, *, best_world_x: float, visited: set[str]):
    candidates = [
        node
        for node in graph.nodes
        if node.key not in visited
        and node.distance_from_source >= MIN_FRONTIER_DISTANCE_YARDS
        and node.centroid.x >= best_world_x - MAX_BACKTRACK_YARDS
        and not node.semantic_flags & NAV_SEMANTIC_HAZARD
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda node: (node.centroid.x, node.distance_from_source))


def _activate_prowl(bridge, trace) -> None:
    frame = bridge.observe()
    if frame is None:
        trace("traverse_prowl", activation=0, reason="no_frame")
        return
    if frame.in_combat:
        trace("traverse_prowl", activation=0, reason="in_combat")
        return
    if any(spell_id in frame.active_aura_spell_ids for spell_id in PROWL_SPELL_IDS):
        trace("traverse_prowl", activation=0, reason="already_active")
        return

    if not frame.shapeshift_form_known or frame.shapeshift_form_id != 1:
        request_id = bridge.select_cast_without_target(
            frame,
            CAT_FORM_SPELL_ID,
            purpose="enter Cat Form for stealth Traverse",
        )
        if request_id is None:
            trace("traverse_cat_form", activation=0, reason="spell_unavailable")
            return
        outcome = bridge.wait_for_settlement(frame.frame_id)
        trace(
            "traverse_cat_form",
            activation=1,
            success=outcome is not None and outcome.success,
            detail=outcome.detail if outcome is not None else "unsettled",
        )
        frame = bridge.observe()
        if frame is None or not frame.shapeshift_form_known or frame.shapeshift_form_id != 1:
            trace("traverse_prowl", activation=0, reason="cat_form_not_active")
            return

    prowl_spell_id = next(
        (spell_id for spell_id in PROWL_SPELL_IDS if spell_id in frame.known_spells),
        None,
    )
    if prowl_spell_id is None:
        trace("traverse_prowl", activation=0, reason="spell_unavailable")
        return
    request_id = bridge.select_cast_without_target(
        frame,
        prowl_spell_id,
        purpose="activate Prowl for stealth Traverse",
    )
    if request_id is None:
        trace("traverse_prowl", activation=0, reason="cast_unavailable")
        return
    outcome = bridge.wait_for_settlement(frame.frame_id)
    trace(
        "traverse_prowl",
        activation=1,
        spell_id=prowl_spell_id,
        success=outcome is not None and outcome.success,
        detail=outcome.detail if outcome is not None else "unsettled",
    )


def _activate_travel_form(bridge, trace) -> None:
    frame = bridge.observe()
    if frame is None:
        trace("traverse_travel_form", activation=0, reason="no_frame")
        return
    if (
        frame.shapeshift_form_spell_known
        and frame.shapeshift_form_spell_id == TRAVEL_FORM_SPELL_ID
    ):
        trace("traverse_travel_form", activation=0, reason="already_active")
        return
    request_id = bridge.select_cast_without_target(
        frame,
        TRAVEL_FORM_SPELL_ID,
        purpose="activate Travel Form for speed-first Traverse",
    )
    if request_id is None:
        trace("traverse_travel_form", activation=0, reason="spell_unavailable")
        return
    outcome = bridge.wait_for_settlement(frame.frame_id)
    trace(
        "traverse_travel_form",
        activation=1,
        success=outcome is not None and outcome.success,
        detail=outcome.detail if outcome is not None else "unsettled",
    )


@dataclass
class TraverseStrategy:
    """Advance north over the connected local navmesh until time or goal."""

    best_world_x: float = TRAVERSE_START_WORLD_X
    frontiers_attempted: int = 0
    frontiers_arrived: int = 0
    route_failures: int = 0
    route_guidepoints_arrived: int = 0
    route_prefix_abandoned: bool = False
    visited_frontiers: set[str] = field(default_factory=set)

    def summary(self) -> dict[str, object]:
        northing = max(0.0, self.best_world_x - TRAVERSE_START_WORLD_X)
        full_distance = TRAVERSE_GOAL_WORLD_X - TRAVERSE_START_WORLD_X
        return {
            "best_world_x": round(self.best_world_x, 3),
            "northing_yards": round(northing, 3),
            "goal_fraction": round(min(1.0, northing / full_distance), 4),
            "reached_goal": self.best_world_x >= TRAVERSE_GOAL_WORLD_X,
            "frontiers_attempted": self.frontiers_attempted,
            "frontiers_arrived": self.frontiers_arrived,
            "route_failures": self.route_failures,
            "route_guidepoints_arrived": self.route_guidepoints_arrived,
            "route_prefix_completed": (
                self.route_guidepoints_arrived == len(TRAVERSE_ROUTE_PREFIX)
            ),
        }

    def run(self, bridge, *, until: float) -> None:
        tracer = getattr(bridge, "_tracer", None)

        def trace(kind: str, **payload) -> None:
            if tracer is not None:
                tracer.emit(kind, **payload)

        navigator = RouteNavigator(tracer=tracer)
        trace(
            "strategy_start",
            strategy="traverse",
            map_id=KALIMDOR_MAP_ID,
            goal_world_x=TRAVERSE_GOAL_WORLD_X,
        )
        while time.monotonic() < until and not getattr(bridge, "finished", False):
            if self.route_guidepoints_arrived < PROWL_ROUTE_GUIDEPOINTS:
                _activate_prowl(bridge, trace)
            else:
                _activate_travel_form(bridge, trace)
            here = navigator._observe_position(bridge)
            if here is None:
                time.sleep(1.0)
                continue
            if here.map_id != KALIMDOR_MAP_ID:
                trace("traverse_stopped", reason="left_kalimdor", map_id=here.map_id)
                break

            previous_best = self.best_world_x
            self.best_world_x = max(self.best_world_x, here.x)
            if self.best_world_x > previous_best:
                trace(
                    "traverse_progress",
                    world_x=round(here.x, 3),
                    **self.summary(),
                )
            if here.x >= TRAVERSE_GOAL_WORLD_X - GOAL_RADIUS_YARDS:
                self.best_world_x = max(self.best_world_x, TRAVERSE_GOAL_WORLD_X)
                break

            if (
                not self.route_prefix_abandoned
                and self.route_guidepoints_arrived < len(TRAVERSE_ROUTE_PREFIX)
            ):
                name, target = TRAVERSE_ROUTE_PREFIX[self.route_guidepoints_arrived]
                trace(
                    "traverse_route_guidepoint",
                    activation=self.route_guidepoints_arrived + 1,
                    name=name,
                    target=[target.x, target.y, target.z],
                )
                safe_resume = (
                    (lambda: _activate_prowl(bridge, trace))
                    if self.route_guidepoints_arrived < PROWL_ROUTE_GUIDEPOINTS
                    else None
                )
                result = navigator.navigate_to(
                    bridge,
                    target,
                    deadline=until,
                    on_safe_resume=safe_resume,
                    engage_attackers=False,
                )
                if result.end is not None:
                    self.best_world_x = max(self.best_world_x, result.end.x)
                if result.state == NavState.ARRIVED:
                    self.route_guidepoints_arrived += 1
                    trace(
                        "traverse_route_guidepoint_arrived",
                        activation=self.route_guidepoints_arrived,
                        name=name,
                        world_x=(round(result.end.x, 3) if result.end else None),
                    )
                else:
                    self.route_failures += 1
                    self.route_prefix_abandoned = True
                    trace(
                        "traverse_route_guidepoint_failed",
                        activation=self.route_guidepoints_arrived + 1,
                        name=name,
                        reason=result.reason,
                    )
                continue

            graph = bridge.local_navigation_graph(
                here,
                radius=FRONTIER_RADIUS_YARDS,
            )
            if not graph.ok:
                trace(
                    "traverse_stopped",
                    reason="local_graph_unavailable",
                    status=graph.status,
                    detail=graph.message,
                )
                break
            frontier = _select_frontier(
                graph,
                best_world_x=self.best_world_x,
                visited=self.visited_frontiers,
            )
            if frontier is None:
                trace("traverse_stopped", reason="no_untried_northbound_frontier")
                break

            self.visited_frontiers.add(frontier.key)
            self.frontiers_attempted += 1
            target = Point(
                KALIMDOR_MAP_ID,
                min(frontier.centroid.x, TRAVERSE_GOAL_WORLD_X),
                frontier.centroid.y,
                frontier.centroid.z,
            )
            trace(
                "traverse_frontier",
                activation=self.frontiers_attempted,
                key=frontier.key,
                target=[target.x, target.y, target.z],
                northing_gain=round(target.x - here.x, 3),
            )
            result = navigator.navigate_to(
                bridge,
                target,
                deadline=until,
                engage_attackers=False,
            )
            if result.end is not None:
                self.best_world_x = max(self.best_world_x, result.end.x)
            if result.state == NavState.ARRIVED:
                self.frontiers_arrived += 1
            else:
                self.route_failures += 1
                trace(
                    "traverse_route_failed",
                    key=frontier.key,
                    reason=result.reason,
                    failures=self.route_failures,
                )

        trace("strategy_end", strategy="traverse", **self.summary())
