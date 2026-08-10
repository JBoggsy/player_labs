"""Focused checks for the competition strategy boundary."""

from __future__ import annotations

import time
from types import SimpleNamespace

from environment.contract.policy import Observation, SpellObservation
from environment.navigation import NAV_SEMANTIC_HAZARD

import wowborg.environment  # noqa: F401 - installs host contract compatibility
from wowborg.nav.world_model import Point
from wowborg.strategies import build_strategy
from wowborg.strategies.traverse import (
    CAT_FORM_SPELL_ID,
    GREAT_LIFT_LOWER_DOCK,
    FINAL_TRAVEL_ROUTE_START_GUIDEPOINT,
    OPEN_TRAVEL_ROUTE_START_GUIDEPOINT,
    PROWL_SPELL_IDS,
    ROAD_STEEP_GUIDEPOINTS,
    STEALTH_ROUTE_START_GUIDEPOINT,
    TERRAIN_PROWL_ROUTE_START_GUIDEPOINT,
    TRAVERSE_ROUTE_PREFIX,
    HazardAvoidanceState,
    TraverseCombatState,
    TraverseStrategy,
    _activate_prowl,
    _activate_travel_form,
    _fight_traverse_attacker,
    _hazard_clearance_yards,
    _observed_lift_at_lower_dock,
    _select_frontier,
    _steer_road_leg,
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
    travel_frame = SimpleNamespace(
        frame_id=6,
        in_combat=False,
        shapeshift_form_known=True,
        shapeshift_form_id=3,
        shapeshift_form_spell_known=True,
        shapeshift_form_spell_id=783,
        active_aura_spell_ids=[783],
        known_spells=[CAT_FORM_SPELL_ID, PROWL_SPELL_IDS[-1]],
    )
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

    def cancel(frame, spell_id):
        selected.append((frame.frame_id, spell_id, "cancel current form"))
        return f"frame-{frame.frame_id}"

    def cast(frame, spell_id, purpose):
        selected.append((frame.frame_id, spell_id, purpose))
        return f"frame-{frame.frame_id}"

    bridge = SimpleNamespace(
        observe=lambda: (travel_frame, caster_frame, cat_frame)[len(selected)],
        select_cancel_aura=cancel,
        select_cast_without_target=cast,
        wait_for_settlement=lambda _frame_id: outcome,
    )

    _activate_prowl(bridge, lambda kind, **payload: events.append((kind, payload)))

    assert selected == [
        (6, 783, "cancel current form"),
        (7, CAT_FORM_SPELL_ID, "enter Cat Form for stealth Traverse"),
        (8, PROWL_SPELL_IDS[-1], "activate Prowl for stealth Traverse"),
    ]
    assert events == [
        (
            "traverse_prowl_form_exit",
            {"activation": 1, "spell_id": 783, "success": True, "detail": ""},
        ),
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


def test_ranged_fallback_waits_for_the_observed_active_cast() -> None:
    events = []
    waits = []
    frame = SimpleNamespace(frame_id=12, active_cast_spell_id=5176)
    bridge = SimpleNamespace(
        select_wait=lambda selected: waits.append(selected) or "frame-12"
    )

    acted = _fight_traverse_attacker(
        bridge,
        navigator=None,
        frame=frame,
        attacker=None,
        trace=lambda kind, **payload: events.append((kind, payload)),
        combat=TraverseCombatState(ranged_fallback=True),
    )

    assert acted is True
    assert waits == [frame]
    assert events == [
        (
            "traverse_combat_ranged_fallback",
            {"activation": 1, "phase": "finish_active_cast", "spell_id": 5176},
        )
    ]


def test_travel_form_exits_the_current_form_before_casting() -> None:
    events = []
    frame = SimpleNamespace(
        frame_id=13,
        in_combat=False,
        shapeshift_form_known=True,
        shapeshift_form_id=1,
        shapeshift_form_spell_known=True,
        shapeshift_form_spell_id=CAT_FORM_SPELL_ID,
    )
    outcome = SimpleNamespace(success=True, detail="")
    cancelled = []
    bridge = SimpleNamespace(
        observe=lambda: frame,
        select_cancel_aura=lambda selected, spell_id: (
            cancelled.append((selected, spell_id)) or "frame-13"
        ),
        wait_for_settlement=lambda _frame_id: outcome,
    )

    _activate_travel_form(
        bridge,
        lambda kind, **payload: events.append((kind, payload)),
    )

    assert cancelled == [(frame, CAT_FORM_SPELL_ID)]
    assert events == [
        (
            "traverse_travel_form_exit",
            {
                "activation": 1,
                "spell_id": CAT_FORM_SPELL_ID,
                "success": True,
                "detail": "",
            },
        )
    ]


def test_road_leg_continues_when_travel_form_does_not_persist(monkeypatch) -> None:
    events = []
    casts = []
    frame = SimpleNamespace(
        frame_id=14,
        is_dead=False,
        is_ghost=False,
        in_combat=False,
        shapeshift_form_known=True,
        shapeshift_form_id=0,
        shapeshift_form_spell_known=True,
        shapeshift_form_spell_id=0,
        active_aura_spell_ids=[],
        location=SimpleNamespace(map_id=1, x=10.0, y=20.0, z=30.0),
    )
    bridge = SimpleNamespace(
        finished=False,
        observe=lambda: frame,
        select_cast_without_target=lambda selected, spell_id, purpose: (
            casts.append((selected, spell_id, purpose)) or "frame-14"
        ),
        wait_for_settlement=lambda _frame_id: SimpleNamespace(
            success=True,
            detail="cast cooldown observed",
        ),
    )
    monkeypatch.setattr(
        "wowborg.strategies.traverse._traverse_fight_attacker",
        lambda *_args, **_kwargs: None,
    )

    end, reason = _steer_road_leg(
        bridge,
        navigator=None,
        target=Point(1, 10.0, 20.0, 30.0),
        deadline=time.monotonic() + 1.0,
        trace=lambda kind, **payload: events.append((kind, payload)),
        avoidance=HazardAvoidanceState(),
        allow_northing_pass=True,
        pass_lateral_yards=20.0,
        arrival_radius=6.0,
        hold_terrain_hazards=False,
        jump_terrain=False,
        jump_once=False,
        downstream_route=True,
        stealth_route=False,
    )

    assert end == Point(1, 10.0, 20.0, 30.0)
    assert reason == ""
    assert len(casts) == 1
    assert events[-1] == (
        "traverse_travel_form_unavailable",
        {"activation": 1, "reason": "form_did_not_persist"},
    )


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

    assert TRAVERSE_ROUTE_PREFIX[0][1] == Point(1, -9200.0, -2545.0, 13.5)
    assert TRAVERSE_ROUTE_PREFIX[1][1] == Point(1, -8974.0117, -2741.5291, 41.0118)
    assert TRAVERSE_ROUTE_PREFIX[-1][1] == Point(1, -4677.066, -1853.667, -43.857)
    assert names[-1] == "great-lift-lower-dock"
    assert len(names) == len(set(names))
    assert names[STEALTH_ROUTE_START_GUIDEPOINT] == "shimmering-flats-road"
    assert names[OPEN_TRAVEL_ROUTE_START_GUIDEPOINT - 1] == (
        "thousand-needles-central-road-3"
    )
    assert names[TERRAIN_PROWL_ROUTE_START_GUIDEPOINT] == (
        "thousand-needles-west-gap-1"
    )
    assert names[FINAL_TRAVEL_ROUTE_START_GUIDEPOINT - 1] == (
        "thousand-needles-west-3"
    )

    ascent_start = names.index("shimmering-flats-ramp-ascent-01")
    assert names[ascent_start : ascent_start + 17] == [
        *(f"shimmering-flats-ramp-ascent-{index:02d}" for index in range(1, 17)),
        "shimmering-flats-ramp-crest",
    ]
    assert set(names[ascent_start : ascent_start + 17]) == (
        set(ROAD_STEEP_GUIDEPOINTS) - {"tanaris-road-9-climb-crest"}
    )
    assert "tanaris-road-9-climb-crest" in ROAD_STEEP_GUIDEPOINTS
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


def test_hazard_clearance_tracks_vmangos_level_scaled_aggro() -> None:
    frame = SimpleNamespace(level=60)

    assert _hazard_clearance_yards(frame, SimpleNamespace(level=47)) == 8.0
    assert _hazard_clearance_yards(frame, SimpleNamespace(level=60)) == 21.0
    assert _hazard_clearance_yards(frame, SimpleNamespace(level=0)) == 20.0


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
