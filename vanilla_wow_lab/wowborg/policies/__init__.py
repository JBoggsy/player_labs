"""Policy registry — selected by the WOWBORG_POLICY env var (see wowborg.shim)."""

from __future__ import annotations

from typing import Any, Protocol


class Policy(Protocol):
    def run(self, bridge: Any, *, until: float) -> None:
        """Drive the bridge until the ``time.monotonic()`` deadline ``until``."""


def build_policy(name: str) -> Policy:
    if name == "random_walk":
        from wowborg.policies.random_walk import RandomWalkPolicy

        return RandomWalkPolicy()
    raise ValueError(f"unknown WOWBORG_POLICY {name!r}")
