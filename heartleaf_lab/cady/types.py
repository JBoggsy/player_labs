"""Shared Cady runtime types.

These dataclasses are the six AgentRuntime type parameters Cady phases share:
``Observation``, ``HeartleafState``/percept, ``Belief``, ``ActionState``,
``Intent``, and ``Command``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from players.player_sdk import SpriteWorld


@dataclass(frozen=True)
class Observation:
    """Raw SDK world plus the bridge frame number."""

    world: SpriteWorld
    frame: int


@dataclass(frozen=True)
class Garden:
    """A visible food marker in the garden map."""

    object_id: int
    pos: tuple[int, int]
    has_food: bool


@dataclass(frozen=True)
class Gnome:
    """A visible Heartleaf gnome resolved from its labeled sprite."""

    index: int
    pos: tuple[int, int]
    facing: str


@dataclass(frozen=True)
class House:
    """A known house entrance.

    House geometry is not available to v1 perception yet; the field stays in the
    shared contract for later phases.
    """

    index: int
    entrance: tuple[int, int]


@dataclass(frozen=True)
class HeartleafState:
    """Per-frame label-only Heartleaf state."""

    ready: bool
    self_xy: tuple[int, int] | None
    time_minutes: int | None
    gardens: tuple[Garden, ...]
    gnomes: tuple[Gnome, ...]
    own_house_index: int | None
    houses: tuple[House, ...]
    inventory_count: int


@dataclass
class Belief:
    """Long-lived mutable state folded across perception frames."""

    home_anchor: tuple[int, int] | None = None
    home_anchor_is_morning: bool = False
    own_house_index: int | None = None
    garden_positions: dict[int, tuple[int, int]] = field(default_factory=dict)
    house_entrances: dict[int, tuple[int, int]] = field(default_factory=dict)
    last_time_minutes: int | None = None
    inventory_count: int = 0
    current_target: tuple[int, int] | None = None


@dataclass
class ActionState:
    """Mutable action bookkeeping.

    Phase 4 will add held-mask, movement, arrival, and edge-trigger press state.
    """


IntentKind = Literal["gather_at", "navigate_to", "enter_house", "hold", "idle"]


@dataclass(frozen=True)
class Intent:
    """A symbolic action request emitted by strategy/modes."""

    kind: IntentKind
    point: tuple[int, int] | None = None
    house_index: int | None = None


@dataclass(frozen=True)
class Command:
    """Bridge command produced by action resolution."""

    held_mask: int = 0
    chat: str | None = None


if TYPE_CHECKING:

    def perceive(obs: Observation) -> HeartleafState: ...

    def update_belief(belief: Belief, percept: HeartleafState) -> None: ...

    def resolve_action(intent: Intent, belief: Belief, state: ActionState) -> Command: ...


__all__ = [
    "ActionState",
    "Belief",
    "Command",
    "Garden",
    "Gnome",
    "HeartleafState",
    "House",
    "Intent",
    "IntentKind",
    "Observation",
]
