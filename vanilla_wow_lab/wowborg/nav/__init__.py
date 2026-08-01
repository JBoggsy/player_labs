"""wowborg navigation v2 — general three-level navigation.

Design: docs/designs/wowborg-nav-v2.md. Levels:

- L0 ``local_mover``  — one executor move: 3D arrival, oscillation detection, unstick.
- L1 ``route_navigator`` — same-map any-distance: plans via the game host's
  /player/navigation Detour service, walks planned waypoints as L0 hops, owns the
  nav state machine (combat_paused / recovering / failed-with-reason).
- L2 ``journey_planner`` — anywhere: legs over the declared world-model graph
  (walk edges = L1 routes; portal edges = area_trigger).

World knowledge lives ONLY in ``world_model`` (declared data); layer constants are
executor facts or online-measured, never zone calibration (codex audit, 2026-07-22).
"""

from wowborg.nav.journey import JourneyPlanner, JourneyResult
from wowborg.nav.local import LocalMover, LocalMoveResult
from wowborg.nav.route import NavState, RouteNavigator, RouteResult

__all__ = [
    "JourneyPlanner",
    "JourneyResult",
    "LocalMover",
    "LocalMoveResult",
    "NavState",
    "RouteNavigator",
    "RouteResult",
]
