"""Focused checks for the competition strategy boundary."""

from __future__ import annotations

from types import SimpleNamespace

from environment.contract.policy import Observation, SpellObservation
from environment.navigation import NAV_SEMANTIC_HAZARD

import wowborg.environment  # noqa: F401 - installs host contract compatibility
from wowborg.nav.world_model import Point
from wowborg.strategies import build_strategy
from wowborg.strategies.traverse import (
    CAT_FORM_SPELL_ID,
    GREAT_LIFT_LOWER_DOCK,
    PROWL_SPELL_IDS,
    TRAVERSE_ROUTE_PREFIX,
    TraverseStrategy,
    _activate_prowl,
    _observed_lift_at_lower_dock,
    _select_frontier,
    _steer_toward,
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
    intent_schema = Observation.model_json_schema()["$defs"]["SpellObservation"][
        "properties"
    ]["intent_names"]["items"]
    assert intent_schema == {"type": "string"}


def test_traverse_enters_cat_form_and_activates_prowl() -> None:
    events = []
    caster_frame = SimpleNamespace(
        frame_id=7,
        in_combat=False,
        shapeshift_form_known=True,
        shapeshift_form_id=0,
        active_aura_spell_ids=[],
        known_spells=[CAT_FORM_SPELL_ID, PROWL_SPELL_IDS[-1]],
    )
    cat_frame = SimpleNamespace(
        frame_id=8,
        in_combat=False,
        shapeshift_form_known=True,
        shapeshift_form_id=1,
        active_aura_spell_ids=[],
        known_spells=[CAT_FORM_SPELL_ID, PROWL_SPELL_IDS[-1]],
    )
    outcome = SimpleNamespace(success=True, detail="")
    selected = []

    def cast(frame, spell_id, purpose):
        selected.append((frame.frame_id, spell_id, purpose))
        return f"frame-{frame.frame_id}"

    bridge = SimpleNamespace(
        observe=lambda: cat_frame if selected else caster_frame,
        select_cast_without_target=cast,
        wait_for_settlement=lambda _frame_id: outcome,
    )

    _activate_prowl(bridge, lambda kind, **payload: events.append((kind, payload)))

    assert selected == [
        (7, CAT_FORM_SPELL_ID, "enter Cat Form for stealth Traverse"),
        (8, PROWL_SPELL_IDS[-1], "activate Prowl for stealth Traverse"),
    ]
    assert events == [
        ("traverse_cat_form", {"activation": 1, "success": True, "detail": ""}),
        (
            "traverse_prowl",
            {
                "activation": 1,
                "spell_id": PROWL_SPELL_IDS[-1],
                "success": True,
                "detail": "",
            },
        ),
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
        "tanaris-start-safe-1",
        "tanaris-start-safe-2",
        "tanaris-start-safe-3",
        "tanaris-start-safe-4",
        "tanaris-start-safe-5",
        "tanaris-start-safe-6",
        "tanaris-start-safe-7",
        "tanaris-start-safe-8",
        "tanaris-centipaar-bypass-1",
        "tanaris-centipaar-bypass-2",
        "tanaris-centipaar-bypass-3",
        "tanaris-centipaar-bypass-4",
        "great-lift-lower-dock",
    ]
    assert TRAVERSE_ROUTE_PREFIX[:9] == (
        (
            "tanaris-start-safe-1",
            Point(1, -9311.9990234375, -2677.333251953125, 9.571125984191895),
        ),
        (
            "tanaris-start-safe-2",
            Point(1, -9311.9990234375, -2784.0, 14.883625984191895),
        ),
        (
            "tanaris-start-safe-3",
            Point(1, -9141.3330078125, -2933.3330078125, 36.94612503051758),
        ),
        (
            "tanaris-start-safe-4",
            Point(1, -8693.3330078125, -2933.3330078125, 14.039186477661133),
        ),
        (
            "tanaris-start-safe-5",
            Point(1, -8241.955078125, -2775.288818359375, 33.05540084838867),
        ),
        (
            "tanaris-start-safe-6",
            Point(1, -8181.3330078125, -2357.333251953125, 10.32977294921875),
        ),
        ("tanaris-start-safe-7", Point(1, -8166.4, -2259.6, 10.0)),
        ("tanaris-start-safe-8", Point(1, -8168.0, -2210.0, 10.0)),
        ("tanaris-centipaar-bypass-1", Point(1, -8132.53, -2196.98, 7.41)),
    )
    assert TRAVERSE_ROUTE_PREFIX[-1][1] == Point(1, -4677.066, -1853.667, -43.857)
    assert len(names) == len(set(names)) == 13


def test_lift_detection_uses_only_visible_platform_at_lower_dock() -> None:
    upper = SimpleNamespace(
        entry=11898,
        distance=10.0,
        location=SimpleNamespace(z=85.7),
    )
    lower = SimpleNamespace(
        entry=11899,
        distance=8.0,
        location=SimpleNamespace(z=GREAT_LIFT_LOWER_DOCK.z),
    )

    selected = _observed_lift_at_lower_dock(
        SimpleNamespace(objects=[upper, lower])
    )

    assert selected is lower


def test_lift_steering_turns_before_walking_forward() -> None:
    actions = []
    bridge = SimpleNamespace(
        select_move_vector=lambda frame, **action: actions.append(action)
    )
    frame = SimpleNamespace(
        location=SimpleNamespace(x=0.0, y=0.0, orientation=0.0)
    )

    _steer_toward(bridge, frame, Point(1, 0.0, 10.0, 0.0), purpose="board")
    _steer_toward(bridge, frame, Point(1, 10.0, 0.0, 0.0), purpose="board")

    assert actions[0]["turn"] == 1.0
    assert actions[0].get("forward", 0.0) == 0.0
    assert actions[1]["forward"] == 1.0
    assert actions[1].get("turn", 0.0) == 0.0
