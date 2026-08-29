"""Front-of-ship positioning helpers (button-runner interception).

Covers the Tier-1 design (docs/designs/button-runner-interception.md §3.2): the pure
band/cluster helpers and the substrate-derived approach points. The SearchMode
front-bias wiring was rejected and removed (see version_log.md, v28–v30), so only
the helpers remain.
"""

from __future__ import annotations

import math

import numpy as np

from crewrift.crewborg.agent_tracking import update_agent_tracking
from crewrift.crewborg.map.types import MapData, MapPoint, MapRect, Room, TaskStation
from crewrift.crewborg.nav import build_nav_graph
from crewrift.crewborg.strategy import button_intercept as bi
from crewrift.crewborg.types import Belief

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
