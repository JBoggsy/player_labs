"""Front-of-ship positioning prior for imposter Search (button-runner interception).

Covers the Tier-1 design (docs/designs/button-runner-interception.md §3.2): the pure
band/cluster helpers, the substrate-derived approach points, and the SearchMode wiring
that prepends them only when CREWBORG_FRONT_BIAS is set.
"""

from __future__ import annotations

import math

import numpy as np

from crewrift.crewborg.agent_tracking import OccupancySnapshot, update_agent_tracking
from crewrift.crewborg.map.types import MapData, MapPoint, MapRect, Room, TaskStation
from crewrift.crewborg.modes import SearchMode
from crewrift.crewborg.nav import build_nav_graph
from crewrift.crewborg.strategy import button_intercept as bi
from crewrift.crewborg.types import ActionState, Belief


# --------------------------------------------------------------------------- #
# Pure helpers                                                                #
# --------------------------------------------------------------------------- #


def test_band_point_picks_vertex_nearest_band_centre() -> None:
    button = (0, 0)
    points = ((10, 0), (bi.FRONT_BAND_CENTER, 0), (bi.FRONT_BAND_MAX + 50, 0))
    # Only the middle vertex sits in the band; it is also exactly at the centre.
    assert bi._band_point(points, button) == (bi.FRONT_BAND_CENTER, 0)


def test_band_point_none_when_route_skips_the_band() -> None:
    button = (0, 0)
    points = ((10, 0), (20, 0), (bi.FRONT_BAND_MAX + 100, 0))  # all below or above the band
    assert bi._band_point(points, button) is None


def test_cluster_groups_nearby_points_and_counts_convergence() -> None:
    # Three points near (300,300), one far away → two clusters, sizes 3 and 1.
    pts = [(300, 300), (310, 305), (295, 298), (900, 100)]
    clusters = dict(bi._cluster(pts))
    sizes = sorted(clusters.values())
    assert sizes == [1, 3]


# --------------------------------------------------------------------------- #
# Substrate-derived approach points                                           #
# --------------------------------------------------------------------------- #


def _corridor_map() -> MapData:
    """Bridge (with button) on the far west, two task rooms to the east, so every
    task→button route funnels back west through the band off the button."""

    return MapData(
        width=640, height=160,
        tasks=(
            TaskStation(name="east1", x=560, y=72, w=16, h=16),
            TaskStation(name="east2", x=560, y=8, w=16, h=16),
        ),
        vents=(),
        rooms=(
            Room(name="Bridge", x=0, y=0, w=160, h=160),
            Room(name="Mid", x=160, y=0, w=320, h=160),
            Room(name="East", x=480, y=0, w=160, h=160),
        ),
        button=MapRect(x=40, y=72, w=16, h=16),  # button anchor ≈ (48, 80), in the Bridge
        home=MapPoint(x=24, y=80),
    )


def _substrate_belief() -> Belief:
    map_data = _corridor_map()
    nav = build_nav_graph(np.ones((map_data.height, map_data.width), dtype=bool), map_data=map_data)
    belief = Belief(map=map_data, nav=nav, self_role="imposter", self_world_x=24, self_world_y=80, last_tick=5)
    update_agent_tracking(belief)  # builds the occupancy substrate (anchors + polylines)
    return belief


def test_approach_points_lie_in_the_band_off_the_button() -> None:
    belief = _substrate_belief()
    button = bi._button_anchor(belief, belief.agent_tracking.substrate)
    assert button is not None

    points = bi.button_approach_points(belief)
    assert points  # the east→button routes cross the band
    assert len(points) <= bi.MAX_APPROACH_POINTS
    # Each point is roughly within the band (reachable-snap can nudge it by ~a cell).
    for p in points:
        d = math.dist(p, button)
        assert bi.FRONT_BAND_MIN - 32 <= d <= bi.FRONT_BAND_MAX + 32


def test_approach_points_empty_without_substrate() -> None:
    belief = Belief(self_world_x=10, self_world_y=10)  # no map/nav → no substrate
    assert belief.agent_tracking.substrate is None
    assert bi.button_approach_points(belief) == []


# --------------------------------------------------------------------------- #
# SearchMode wiring (flag-gated prepend)                                       #
# --------------------------------------------------------------------------- #


def _occupancy_belief() -> tuple[Belief, tuple[int, int], tuple[int, int]]:
    map_data = _corridor_map()
    nav = build_nav_graph(np.ones((map_data.height, map_data.width), dtype=bool), map_data=map_data)
    belief = Belief(map=map_data, nav=nav, self_world_x=24, self_world_y=80, last_tick=5)
    update_agent_tracking(belief)
    substrate = belief.agent_tracking.substrate
    assert substrate is not None
    cells = list(substrate.cells.values())
    occ_cell = max(cells, key=lambda c: c.center[0])  # an easterly cell as the occupancy hot spot
    belief.agent_tracking.snapshot = OccupancySnapshot(
        tick=5, expected_by_cell={occ_cell.index: 1.0}, top_cell=occ_cell.index,
        top_point=occ_cell.center, top_expected=1.0, tracked_count=1, support_cell_count=1,
    )
    return belief, occ_cell.center, cells[0].center


def test_search_uses_occupancy_when_front_bias_disabled(monkeypatch) -> None:
    monkeypatch.delenv("CREWBORG_FRONT_BIAS", raising=False)
    belief, occ_center, front_stub = _occupancy_belief()
    monkeypatch.setattr(bi, "button_approach_points", lambda _b: [front_stub])  # would be ignored
    intent = SearchMode().decide(belief, ActionState())
    assert intent.kind == "navigate_to"
    assert intent.point == occ_center


def test_search_prepends_front_points_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_FRONT_BIAS", "1")
    belief, occ_center, front_stub = _occupancy_belief()
    assert front_stub != occ_center
    monkeypatch.setattr(bi, "button_approach_points", lambda _b: [front_stub])
    intent = SearchMode().decide(belief, ActionState())
    assert intent.kind == "navigate_to"
    assert intent.point == front_stub  # the corridor point wins over the occupancy hot spot


def test_search_still_follows_a_visible_victim_with_front_bias_on(monkeypatch) -> None:
    # Bird in hand: a visible victim pre-empts the positioning prior entirely.
    monkeypatch.setenv("CREWBORG_FRONT_BIAS", "1")
    belief = Belief(self_world_x=100, self_world_y=80, last_tick=5)
    from crewrift.crewborg.types import PlayerRecord

    belief.roster["green"] = PlayerRecord(
        object_id=1, color="green", world_x=130, world_y=80, last_seen_tick=5, life_status="alive"
    )
    intent = SearchMode().decide(belief, ActionState())
    assert intent.point == (130, 80)
    assert intent.reason == "search: following visible target"
