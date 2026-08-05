"""Focused checks for the competition strategy boundary."""

from __future__ import annotations

from types import SimpleNamespace

from environment.contract.agent import AgentFrame, SpellObservation
from player.sdk.navmesh.models import NAV_SEMANTIC_HAZARD

import wowborg.environment  # noqa: F401 - installs host contract compatibility
from wowborg.strategies import build_strategy
from wowborg.strategies.traverse import TraverseStrategy, _select_frontier


def node(key: str, *, x: float, distance: float, semantic_flags: int = 0):
    return SimpleNamespace(
        key=key,
        centroid=SimpleNamespace(x=x, y=0.0, z=0.0),
        distance_from_source=distance,
        semantic_flags=semantic_flags,
    )


def test_registry_builds_traverse_strategy() -> None:
    assert isinstance(build_strategy("traverse"), TraverseStrategy)


def test_host_spell_intents_are_open_strings() -> None:
    required = {
        name: 1 if name == "spell_id" else True
        for name, field in SpellObservation.model_fields.items()
        if field.is_required()
    }
    spell = SpellObservation.model_validate(
        {**required, "intent_names": ["threat", "threat_reduction"]}
    )

    assert spell.intent_names == ["threat", "threat_reduction"]
    intent_schema = AgentFrame.model_json_schema()["$defs"]["SpellObservation"][
        "properties"
    ]["intent_names"]["items"]
    assert intent_schema == {"type": "string"}


def test_frontier_prefers_farthest_safe_northing() -> None:
    graph = SimpleNamespace(
        nodes=[
            node("near", x=100.0, distance=10.0),
            node("north", x=500.0, distance=300.0),
            node("visited", x=600.0, distance=350.0),
            node("backtrack", x=-200.0, distance=400.0),
            node(
                "hazard",
                x=700.0,
                distance=450.0,
                semantic_flags=NAV_SEMANTIC_HAZARD,
            ),
        ]
    )

    selected = _select_frontier(graph, best_world_x=0.0, visited={"visited"})

    assert selected.key == "north"


def test_summary_uses_authoritative_northing_formula() -> None:
    strategy = TraverseStrategy(best_world_x=1476.91)

    summary = strategy.summary()

    assert summary["northing_yards"] == 10663.91
    assert summary["reached_goal"] is False
