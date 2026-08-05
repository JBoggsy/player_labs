"""Focused checks for the competition strategy boundary."""

from __future__ import annotations

from types import SimpleNamespace

from environment.contract.agent import AgentFrame, SpellObservation
from player.sdk.navmesh.models import NAV_SEMANTIC_HAZARD

import wowborg.environment  # noqa: F401 - installs host contract compatibility
from wowborg.nav.world_model import Point
from wowborg.strategies import build_strategy
from wowborg.strategies.traverse import (
    TRAVERSE_ROUTE_PREFIX,
    TRAVEL_FORM_SPELL_ID,
    TraverseStrategy,
    _activate_travel_form,
    _select_frontier,
)


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


def test_traverse_activates_travel_form() -> None:
    events = []
    frame = SimpleNamespace(
        frame_id=7,
        shapeshift_form_spell_known=True,
        shapeshift_form_spell_id=0,
    )
    outcome = SimpleNamespace(success=True, detail="")
    bridge = SimpleNamespace(
        observe=lambda: frame,
        select_cast_without_target=lambda observed, spell_id, purpose: (
            "frame-7"
            if observed is frame
            and spell_id == TRAVEL_FORM_SPELL_ID
            and purpose == "activate Travel Form for Traverse"
            else None
        ),
        wait_for_settlement=lambda frame_id: outcome if frame_id == 7 else None,
    )

    _activate_travel_form(bridge, lambda kind, **payload: events.append((kind, payload)))

    assert events == [
        ("traverse_travel_form", {"activation": 1, "success": True, "detail": ""})
    ]


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


def test_traverse_route_prefix_reaches_great_lift_lower_dock() -> None:
    names = [name for name, _point in TRAVERSE_ROUTE_PREFIX]

    assert names == [
        "tanaris-centipaar-bypass-1",
        "tanaris-centipaar-bypass-2",
        "tanaris-centipaar-bypass-3",
        "tanaris-centipaar-bypass-4",
        "great-lift-lower-dock",
    ]
    assert TRAVERSE_ROUTE_PREFIX[-1][1] == Point(1, -4677.066, -1853.667, -43.857)
    assert len(names) == len(set(names)) == 5
