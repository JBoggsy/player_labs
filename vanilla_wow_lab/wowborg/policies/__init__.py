"""Policy registry selected by the ``WOWBORG_POLICY`` environment variable."""

from __future__ import annotations

from typing import Any, Protocol


class Policy(Protocol):
    def run(self, session: Any, *, until: float) -> None:
        """Drive the environment session until the monotonic deadline ``until``."""


def build_policy(name: str) -> Policy:
    if name == "random_walk":
        from wowborg.policies.random_walk import RandomWalkPolicy

        return RandomWalkPolicy()
    if name == "waypoint_race":
        from wowborg.policies.waypoint_race import WaypointRacePolicy

        return WaypointRacePolicy()
    if name == "world_race":
        from wowborg.policies.world_race import WorldRacePolicy

        return WorldRacePolicy()
    raise ValueError(f"unknown WOWBORG_POLICY {name!r}")
