"""Small dependency-free value types shared by navigation and tracing."""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Position:
    x: float
    y: float
    z: float
    orientation: float


@dataclass(frozen=True)
class ActionOutcome:
    """Policy-facing summary of one Gymnasium step."""

    request_id: str
    kind: str
    success: bool
    settlement_kind: str | None  # movement intents only
    displacement_yards: float | None
    end_position: Position | None
    detail: str  # human-readable, for logs only
    frame_id: int | None = None  # exact settlement correlation (audit #11)
    settled_tick: int | None = None


@dataclass(frozen=True)
class PlannedRoute:
    """A Detour route from the game host's /player/navigation service (L1 input).

    ``status`` values: ok | partial | no_path | unreachable_target | unavailable |
    error (normalized). ``waypoints`` are full 3D map-scoped points along the walkable
    path; ``route_distance`` is TRUE path length (budgets derive from this, never
    straight-line). ``projected_target_distance`` > a few yards on an "ok" route means
    the target itself is off-mesh (arrival should verify against the projection).
    """

    status: str
    map_id: int
    waypoints: list[Position]
    route_distance: float
    partial: bool
    projected_target_distance: float | None
    jump_required: bool
    message: str
