"""Shared wowborg policy-facing types — deliberately dependency-free.

Policies import from here (and duck-type the bridge); only ``wowborg.bridge`` imports
``wow_sdk``. This keeps policies runnable/testable anywhere and makes the shim swappable:
a new shim reimplements the bridge against these same types.
"""

from __future__ import annotations

from dataclasses import dataclass

# Movement-settlement kinds counted as success (vanilla_wow.movement_settlement.v1;
# mirrors wow_sdk.protocol.SUCCESSFUL_MOVEMENT_SETTLEMENT_KINDS).
SUCCESS_SETTLEMENT_KINDS = frozenset(
    {"reached_target", "advanced_corridor", "combat_interrupted"}
)


@dataclass(frozen=True)
class Position:
    x: float
    y: float
    z: float
    orientation: float


@dataclass(frozen=True)
class Observation:
    """The T0 observation slice: self pose + vitals + death state + freshness."""

    tick: int
    captured_at: float  # our wall clock at read time
    map_id: int
    zone: str
    position: Position
    health: int
    max_health: int
    in_combat: bool
    is_dead: bool
    is_ghost: bool


@dataclass(frozen=True)
class ActionOutcome:
    """Typed result of one intent — never classify from message text."""

    request_id: str
    kind: str
    success: bool
    settlement_kind: str | None  # movement intents only
    displacement_yards: float | None
    end_position: Position | None
    detail: str  # human-readable, for logs only
