"""Competition-level strategy selection for wowborg."""

from __future__ import annotations

from typing import Any, Protocol


class Strategy(Protocol):
    def run(self, session: Any, *, until: float) -> None:
        """Pursue one competition objective until the session deadline."""

    def summary(self) -> dict[str, object]:
        """Return the strategy's final structured result."""


def build_strategy(name: str) -> Strategy:
    if name == "traverse":
        from wowborg.strategies.traverse import TraverseStrategy

        return TraverseStrategy()
    raise ValueError(f"unknown WOWBORG_STRATEGY {name!r}")
