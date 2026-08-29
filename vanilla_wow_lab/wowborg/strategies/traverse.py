"""Kalimdor Traverse strategy: keep selecting reachable northbound frontiers."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from environment.navigation import NAV_SEMANTIC_HAZARD

from wowborg.nav.route import NavState, RouteNavigator
from wowborg.nav.world_model import Point

KALIMDOR_MAP_ID = 1
TRAVERSE_START_WORLD_X = -9187.0
TRAVERSE_GOAL_WORLD_X = 6687.333052
FRONTIER_RADIUS_YARDS = 700.0
MIN_FRONTIER_DISTANCE_YARDS = 50.0
MAX_BACKTRACK_YARDS = 100.0
GOAL_RADIUS_YARDS = 8.0
CAT_FORM_SPELL_ID = 768
PROWL_SPELL_IDS = (9913, 6783, 5215)
TRAVEL_FORM_SPELL_ID = 783
RAMP_SCORPID_ENTRY = 5422
FERAL_CLAW_SPELL_IDS = (9850, 9849, 5201, 3029, 1082)
FERAL_RAKE_SPELL_IDS = (9904, 1824, 1823, 1822)
FERAL_RIP_SPELL_IDS = (9896, 9894, 9752, 9493, 9492, 1079)
WRATH_SPELL_IDS = (6780, 5180, 5179, 5178, 5177, 5176)
MOONFIRE_SPELL_IDS = (8929, 8928, 8927, 8926, 8925, 8924, 8921)
REJUVENATION_SPELL_IDS = (
    9841,
    9840,
    9839,
    8910,
    3627,
    2091,
    2090,
    1430,
    1058,
    774,
)
FERAL_MELEE_CLOSE_YARDS = 2.5
GREAT_LIFT_ENTRIES = (11898, 11899)
GREAT_LIFT_LOWER_DOCK = Point(1, -4677.066, -1853.667, -43.857)
GREAT_LIFT_UPPER_DOCK = Point(1, -4650.066, -1850.482, 85.705)
GREAT_LIFT_UPPER_ROAD = Point(1, -4583.315, -1908.142, 95.58)
GREAT_LIFT_VISIBLE_RANGE = 42.0
GREAT_LIFT_DOCK_Z_SLACK = 2.0
GREAT_LIFT_EXIT_Z = 80.0
TRAVERSE_INPUT_SECONDS = 0.75
ROAD_PRECISE_INPUT_SECONDS = 0.25
ROAD_OPEN_INPUT_SECONDS = 1.0
ROAD_CLEAR_INPUT_SECONDS = 1.5
ROAD_STEALTH_INPUT_SECONDS = 1.5
ROAD_ARRIVAL_RADIUS_YARDS = 8.0
ROAD_PASS_LATERAL_YARDS = 60.0
ROAD_CORRIDOR_PASS_LATERAL_YARDS = 6.0
ROAD_PASS_VERTICAL_YARDS = 10.0
ROAD_PASS_NORTHING_SLACK_YARDS = 20.0
ROAD_JUMP_EDGE_PASS_LATERAL_YARDS = 8.0
ROAD_JUMP_EDGE_PASS_VERTICAL_YARDS = 10.0
ROAD_CLIMB_EDGE_PASS_PLANAR_YARDS = 8.0
ROAD_CLIMB_EDGE_PASS_VERTICAL_SLACK_YARDS = 3.0
ROAD_ROUTE_RESUME_MIN_WORLD_X = -8000.0
ROAD_ROUTE_RESUME_RADIUS_YARDS = 50.0
ROAD_STALL_SECONDS = 8.0
ROAD_UNSTICK_ATTEMPTS = 2
ROAD_COLLISION_MOVEMENT_YARDS = 4.0
ROAD_HAZARD_ENTER_YARDS = 45.0
ROAD_HAZARD_EXIT_YARDS = 55.0
ROAD_HAZARD_LOOKAHEAD_YARDS = 60.0
ROAD_HAZARD_RESIDENT_RADIUS_YARDS = 30.0
ROAD_HAZARD_CORRIDOR_YARDS = 18.0
ROAD_HAZARD_TRACK_YARDS = 80.0
ROAD_HAZARD_FORWARD_YARDS = 20.0
ROAD_HAZARD_LATERAL_YARDS = (10.0, 15.0, 20.0, 25.0, 30.0, 45.0, 60.0)
ROAD_HAZARD_BASE_AGGRO_YARDS = 18.0
ROAD_HAZARD_MIN_AGGRO_YARDS = 5.0
ROAD_HAZARD_CLEARANCE_SLACK_YARDS = 3.0
ROAD_PROWL_CLEARANCE_YARDS = 2.5
ROAD_HAZARD_UNKNOWN_CLEARANCE_YARDS = 20.0
ROAD_TIGHT_HAZARD_HOLD_YARDS = 8.0
ROAD_HAZARD_CLEARANCE_FIGHT_DELAY_SECONDS = 3.0
ROAD_HAZARD_SWITCH_MARGIN_YARDS = 5.0
RAMP_FIGHT_ADD_CLEARANCE_YARDS = 12.0
CLEARANCE_FIGHT_ADD_HORIZON_SECONDS = 6.0
SECOND_DESCENT_MIN_HEALTH_FRACTION = 0.8
POST_FIGHT_HEAL_FRACTION = 0.8
ROAD_STEEP_GUIDEPOINTS = frozenset(
    f"tanaris-northern-direct-{index:02d}"
    for index in (
        49, 113, 114, 115, 116, 117,
        146, 156, 157, 158,
        175, 180, 185, 188, 190, 193,
        226, 249, 250, 251, 252, 258, 293, 296, 298, 302,
        349, 351, 355, 396,
    )
) | {
    "tanaris-northern-safe-bridge-05",
    "tanaris-northern-ridge-43",
    "tanaris-northern-ridge-70",
    "tanaris-northern-ridge-05",
    "tanaris-northern-ledge-landing",
    "tanaris-northern-direct-338",
} | frozenset(
    f"tanaris-northern-mesa-bypass-{index:02d}" for index in range(1, 21)
)
ROAD_STEEP_PASS_GUIDEPOINTS = frozenset()
ROAD_BOUNDED_STRAIGHT_JUMP_GUIDEPOINTS: dict[str, int] = {
    f"tanaris-northern-direct-{index:02d}": 64
    for index in (
        *range(93, 113),
        *range(118, 130),
        *range(140, 156),
        *range(162, 175),
        *range(176, 216),
        *range(258, 276),
    )
}
ROAD_BOUNDED_JUMP_FLOOR_Z: dict[str, float] = {
    **{
        f"tanaris-northern-direct-{index:02d}": 3.0
        for index in range(93, 100)
    },
    **{
        f"tanaris-northern-direct-{index:02d}": -8.0
        for index in range(104, 113)
    },
    **{
        f"tanaris-northern-direct-{index:02d}": 14.0
        for index in range(121, 130)
    },
    **{
        f"tanaris-northern-direct-{index:02d}": 20.0
        for index in range(118, 121)
    },
    **{
        f"tanaris-northern-direct-{index:02d}": 8.0
        for index in range(140, 146)
    },
    "tanaris-northern-direct-151": 10.0,
    "tanaris-northern-direct-152": 8.0,
    "tanaris-northern-direct-153": 5.0,
    "tanaris-northern-direct-154": -2.0,
    "tanaris-northern-direct-155": -5.0,
    "tanaris-northern-direct-162": 22.0,
    "tanaris-northern-direct-163": 19.0,
    "tanaris-northern-direct-164": 20.0,
    "tanaris-northern-direct-165": 15.0,
    "tanaris-northern-direct-166": 12.0,
    "tanaris-northern-direct-167": 2.0,
    "tanaris-northern-direct-168": 0.0,
    "tanaris-northern-direct-169": 8.0,
    "tanaris-northern-direct-170": 7.0,
    "tanaris-northern-direct-171": 2.0,
    "tanaris-northern-direct-172": 0.0,
    "tanaris-northern-direct-173": -2.0,
    "tanaris-northern-direct-174": -2.0,
    "tanaris-northern-direct-176": 2.0,
    "tanaris-northern-direct-177": 0.0,
    "tanaris-northern-direct-178": 4.0,
    "tanaris-northern-direct-179": -2.0,
    "tanaris-northern-direct-181": 0.0,
    "tanaris-northern-direct-182": -3.0,
    "tanaris-northern-direct-183": -8.0,
    "tanaris-northern-direct-184": -15.0,
    "tanaris-northern-direct-185": -10.0,
    "tanaris-northern-direct-186": -8.0,
    "tanaris-northern-direct-187": -4.0,
    "tanaris-northern-direct-188": 14.0,
    "tanaris-northern-direct-189": 20.0,
    "tanaris-northern-direct-190": 28.0,
    "tanaris-northern-direct-191": 35.0,
    "tanaris-northern-direct-192": 40.0,
    "tanaris-northern-direct-193": 45.0,
    "tanaris-northern-direct-194": 45.0,
    "tanaris-northern-direct-195": 35.0,
    "tanaris-northern-direct-196": 25.0,
    "tanaris-northern-direct-197": 25.0,
    "tanaris-northern-direct-198": 28.0,
    "tanaris-northern-direct-199": 28.0,
    "tanaris-northern-direct-200": 20.0,
    "tanaris-northern-direct-201": 22.0,
    "tanaris-northern-direct-202": 30.0,
    "tanaris-northern-direct-203": 32.0,
    "tanaris-northern-direct-204": 31.0,
    "tanaris-northern-direct-205": 23.0,
    "tanaris-northern-direct-206": 22.0,
    "tanaris-northern-direct-207": 22.0,
    "tanaris-northern-direct-208": 25.0,
    "tanaris-northern-direct-209": 29.0,
    "tanaris-northern-direct-210": 24.0,
    "tanaris-northern-direct-211": 26.0,
    "tanaris-northern-direct-212": 21.0,
    "tanaris-northern-direct-213": 21.0,
    "tanaris-northern-direct-214": 18.0,
    "tanaris-northern-direct-215": 19.0,
    "tanaris-northern-direct-258": 163.0,
    "tanaris-northern-direct-259": 171.0,
    "tanaris-northern-direct-260": 173.0,
    "tanaris-northern-direct-261": 184.0,
    "tanaris-northern-direct-262": 180.0,
    "tanaris-northern-direct-263": 151.0,
    "tanaris-northern-direct-264": 137.0,
    "tanaris-northern-direct-265": 130.0,
    "tanaris-northern-direct-266": 145.0,
    "tanaris-northern-direct-267": 146.0,
    "tanaris-northern-direct-268": 145.0,
    "tanaris-northern-direct-269": 138.0,
    "tanaris-northern-direct-270": 127.0,
    "tanaris-northern-direct-271": 119.0,
    "tanaris-northern-direct-272": 116.0,
    "tanaris-northern-direct-273": 115.0,
    "tanaris-northern-direct-274": 116.0,
    "tanaris-northern-direct-275": 116.0,
}
# The source route is a dense Detour corridor. On ordinary supported road, retain
# only the anchors needed to stay within four yards of that corridor; the
# physical jump bands below remain fully dense. Longer legs still observe and
# steer around hazards on every movement pulse.
ROAD_GUIDEPOINT_SKIP_AFTER: dict[str, str] = {
    f"tanaris-northern-direct-{after:02d}":
    f"tanaris-northern-direct-{next_index:02d}"
    for after, next_index in (
        (2, 6), (6, 8), (8, 10), (10, 12), (13, 15), (15, 18), (18, 21),
        (21, 23), (23, 26), (26, 28), (28, 30), (30, 32), (32, 36),
        (36, 41), (42, 46), (47, 49), (50, 53), (53, 55), (55, 57),
        (57, 60), (60, 62), (63, 69), (69, 79), (79, 81), (82, 84),
        (84, 86), (86, 88),
        (216, 224), (224, 226), (226, 231), (231, 233), (233, 235),
        (236, 239), (239, 243), (243, 245), (245, 247), (247, 249),
        (252, 257),
        (277, 279), (279, 281),
        (281, 284), (284, 287), (287, 289), (289, 292), (293, 296),
        (296, 298), (298, 301), (302, 304), (304, 307),
        (312, 314), (314, 316), (316, 319), (319, 321),
        (322, 324), (324, 328), (329, 336), (330, 332), (339, 341),
        (341, 343),
        (355, 359), (359, 362), (362, 364), (368, 370), (371, 375),
        (375, 378), (378, 380), (381, 384), (384, 387), (387, 391),
        (391, 394), (394, 396), (396, 398), (398, 400), (400, 402),
        (403, 408), (408, 411), (411, 414), (414, 416), (416, 419),
    )
} | {
    "tanaris-northern-direct-307": "tanaris-northern-ridge-05",
    "tanaris-northern-ridge-21": "tanaris-northern-ridge-43",
    "tanaris-northern-ridge-43": "tanaris-northern-ridge-70",
    "tanaris-northern-ledge-02": "tanaris-northern-ledge-landing",
}
ROAD_BOUNDED_TERRAIN_GUIDEPOINTS = frozenset(
    f"tanaris-northern-direct-{index:02d}"
    for index in (*range(90, 216), *range(258, 276))
) | frozenset(
    f"tanaris-northern-shelf-{index:02d}" for index in range(1, 27)
) | {
    "tanaris-northern-safe-bridge-05",
    "tanaris-northern-safe-bridge-06",
}
# Static stealth remains only for the historical direct-41 micro-zone, which is
# not on the active shortcut. Rank-1 Prowl makes level-46--48 Tanaris mobs detect
# this fixture farther away than its ordinary level-scaled aggro radius.
ROAD_STEALTH_GUIDEPOINTS = frozenset(
    {"tanaris-northern-direct-41", "tanaris-northern-direct-42"}
)
ROAD_LANDING_THEN_CLEAR_GUIDEPOINTS = frozenset(
    {"tanaris-northern-direct-339"}
)
ROAD_TIGHT_GUIDEPOINTS = frozenset(
    f"tanaris-northern-direct-{index:02d}" for index in range(90, 130)
) | frozenset(
    f"tanaris-northern-shelf-{index:02d}" for index in range(1, 27)
) | {
    "tanaris-northern-safe-bridge-05",
    "tanaris-northern-safe-bridge-06",
    "tanaris-northern-direct-336",
    "tanaris-northern-direct-337",
    "tanaris-northern-direct-338",
    "tanaris-northern-direct-339",
    "tanaris-northern-direct-309",
    "tanaris-northern-direct-308",
    "tanaris-northern-direct-343",
    "tanaris-northern-ledge-landing",
    "tanaris-northern-ledge-01",
    "tanaris-northern-ledge-02",
    "tanaris-northern-ledge-03",
} | frozenset(
    f"tanaris-northern-mesa-bypass-{index:02d}" for index in range(1, 21)
) | frozenset(
    f"tanaris-northern-ridge-{index:02d}" for index in range(1, 82)
)
ROAD_LATERAL_TIGHT_GUIDEPOINTS = frozenset(
    {
        "tanaris-northern-ledge-01",
        "tanaris-northern-ledge-02",
        "tanaris-northern-ledge-03",
    }
)
ROAD_DOWNSTREAM_GAP_GUIDEPOINTS = frozenset()
ROAD_DOWNSTREAM_GAP_JUMP_GUIDEPOINTS = frozenset()
ROAD_CORRIDOR_GUIDEPOINTS = frozenset(
    {f"thousand-needles-central-corridor-{index:02d}" for index in range(2, 13)}
    | {f"thousand-needles-west-join-{index:02d}" for index in range(1, 8)}
    | {f"thousand-needles-west-corridor-{index:02d}" for index in range(1, 13)}
    | {f"great-lift-lower-corridor-{index:02d}" for index in range(2, 14)}
    | {f"tanaris-northern-direct-{index:02d}" for index in range(1, 420)}
    | {f"tanaris-northern-shortcut-{index:02d}" for index in range(1, 35)}
    | {f"tanaris-northern-shelf-{index:02d}" for index in range(1, 27)}
    | {f"tanaris-northern-bypass-{index:02d}" for index in range(1, 18)}
    | {f"tanaris-northern-ledge-{index:02d}" for index in range(1, 4)}
    | {"tanaris-northern-ledge-landing"}
    | {f"tanaris-northern-mesa-bypass-{index:02d}" for index in range(1, 21)}
    | {f"tanaris-northern-ridge-{index:02d}" for index in range(1, 82)}
)
ROAD_SINGLE_JUMP_GUIDEPOINTS = frozenset(
    {
        "tanaris-northern-direct-92",
        "tanaris-northern-direct-337",
        "tanaris-northern-direct-338",
    }
    | {
        f"tanaris-northern-direct-{index:02d}"
        for index in range(332, 336)
    }
)
ROAD_DESCENT_GUIDEPOINTS = frozenset(
    f"tanaris-northern-direct-{index:02d}"
    for index in (
        41, 42, 88, 103, 167, 178, 183, 196, 200, 205,
        263, 264, 270, 271, 289, 332, 333, 334, 335,
        364, 365, 366, 368, 370, 371, 416,
    )
) | frozenset(
    {
        "tanaris-northern-safe-bridge-06",
    }
)
ROAD_EXACT_GUIDEPOINTS = (
    ROAD_STEEP_GUIDEPOINTS
    | ROAD_DESCENT_GUIDEPOINTS
    | ROAD_TIGHT_GUIDEPOINTS
    | {"great-lift-lower-dock"}
)
ROAD_TIGHT_ARRIVAL_GUIDEPOINTS = ROAD_EXACT_GUIDEPOINTS
ROAD_TERRAIN_CONSTRAINED_GUIDEPOINTS = (
    ROAD_TIGHT_ARRIVAL_GUIDEPOINTS | ROAD_BOUNDED_TERRAIN_GUIDEPOINTS
)
# Follow the deployed owner's level-51 Tanaris and Thousand Needles road spine
# to the Great Lift lower dock. Great Lift boarding is a separate campaign.
TRAVERSE_MOUNTAIN_ROUTE_PREFIX = (
    # The current host drops the next Observation when the opening movement
    # prefix turns east from the exact spawn. A short southwest prefix settles
    # normally and leaves the canonical road reachable on the following frame.
    ("tanaris-movement-bootstrap", Point(1, -9200.0, -2545.0, 13.5)),
    ("tanaris-north-road-1", Point(1, -8974.0117, -2741.5291, 41.0118)),
    ("tanaris-north-road-2", Point(1, -8761.0234, -2952.8083, 24.5674)),
    ("tanaris-north-road-3", Point(1, -8548.0352, -3164.0835, 10.1670)),
    # Keep v100's proven center-road trajectory until south of v101's Dunemaul
    # Brute, then cross east through the gap north of v100's Glasshide Gazer.
    ("tanaris-brute-gate-south", Point(1, -8401.8008, -3220.6948, 11.3410)),
    ("tanaris-gazer-gate-north", Point(1, -8300.0, -3220.0, 17.4170)),
    ("tanaris-north-road-4", Point(1, -8278.7275, -3284.8706, 23.8400)),
    ("tanaris-north-road-5", Point(1, -8085.3330, -3349.3330, 43.3455)),
    ("tanaris-north-road-6", Point(1, -7866.4028, -3550.8655, 58.3285)),
    ("tanaris-north-road-7", Point(1, -7577.2563, -3602.6570, 15.3188)),
    ("tanaris-north-road-8", Point(1, -7314.9946, -3715.9453, 9.9459)),
    # The Detour corridor bends around impassable terrain here. These exact
    # anchors preserve the bend even after hazard avoidance displaces us north
    # or south; northing-pass semantics would incorrectly skip the west anchor.
    ("tanaris-road-8-detour-west", Point(1, -7193.6000, -3733.3330, 8.9030)),
    ("tanaris-road-8-detour-south", Point(1, -7172.2670, -3753.6000, 9.0610)),
    ("tanaris-road-8-detour-east-turn", Point(1, -7128.8000, -3767.2000, 9.8100)),
    ("tanaris-road-8-detour-east", Point(1, -7096.5330, -3795.4670, 9.3110)),
    # The Detour path becomes too steep to walk after this measured point. Start
    # explicit jumps here, before the separate Shimmering Flats mountain pass.
    ("tanaris-road-9-climb-base", Point(1, -7000.6797, -3835.1392, 12.5631)),
    ("tanaris-road-9-climb-crest", Point(1, -6960.1099, -3851.4419, 34.0389)),
    ("tanaris-north-road-9", Point(1, -6948.5264, -3856.7524, 28.9407)),
    ("shimmering-flats-ramp-lip", Point(1, -6911.4570, -3859.3800, 39.2366)),
    ("shimmering-flats-ramp-approach", Point(1, -6905.4900, -3869.4600, 38.8900)),
    ("shimmering-flats-ramp-turn", Point(1, -6889.5900, -3885.4700, 47.9500)),
    ("shimmering-flats-ramp-base", Point(1, -6884.0000, -3900.0000, 53.6400)),
    # Bound the host's jump-aware Detour follower to one steep edge per action.
    ("shimmering-flats-ramp-ascent-01", Point(1, -6884.1777, -3902.7144, 59.8126)),
    ("shimmering-flats-ramp-ascent-02", Point(1, -6884.0815, -3905.7129, 68.2795)),
    ("shimmering-flats-ramp-ascent-03", Point(1, -6884.0000, -3908.2666, 76.3861)),
    ("shimmering-flats-ramp-ascent-04", Point(1, -6881.2847, -3909.5420, 83.8913)),
    ("shimmering-flats-ramp-ascent-05", Point(1, -6878.5693, -3910.8174, 91.8873)),
    ("shimmering-flats-ramp-ascent-06", Point(1, -6875.8540, -3912.0928, 100.0763)),
    ("shimmering-flats-ramp-ascent-07", Point(1, -6873.1387, -3913.3682, 106.4943)),
    ("shimmering-flats-ramp-ascent-08", Point(1, -6870.4233, -3914.6436, 111.2707)),
    ("shimmering-flats-ramp-ascent-09", Point(1, -6867.7080, -3915.9189, 115.0312)),
    ("shimmering-flats-ramp-ascent-10", Point(1, -6866.4004, -3916.5332, 116.6361)),
    ("shimmering-flats-ramp-ascent-11", Point(1, -6863.6938, -3917.8271, 119.3671)),
    ("shimmering-flats-ramp-ascent-12", Point(1, -6860.9873, -3919.1211, 122.0981)),
    ("shimmering-flats-ramp-ascent-13", Point(1, -6858.2808, -3920.4150, 122.9458)),
    ("shimmering-flats-ramp-ascent-14", Point(1, -6855.5742, -3921.7090, 123.9636)),
    ("shimmering-flats-ramp-ascent-15", Point(1, -6852.8677, -3923.0029, 124.4359)),
    ("shimmering-flats-ramp-ascent-16", Point(1, -6850.1611, -3924.2969, 124.3111)),
    ("shimmering-flats-ramp-crest", Point(1, -6848.0000, -3925.3300, 124.6400)),
    ("shimmering-flats-south-ramp", Point(1, -6794.0220, -3953.5276, 100.8641)),
    ("shimmering-flats-descent-01", Point(1, -6786.3184, -3956.7168, 93.9533)),
    ("shimmering-flats-descent-02", Point(1, -6775.4883, -3961.8838, 89.6143)),
    ("shimmering-flats-descent-03", Point(1, -6764.6582, -3967.0503, 88.9976)),
    ("shimmering-flats-descent-04", Point(1, -6754.1753, -3970.9795, 88.7609)),
    ("shimmering-flats-descent-05", Point(1, -6742.8530, -3974.9521, 87.0434)),
    ("shimmering-flats-descent-06", Point(1, -6731.5308, -3978.9248, 86.6695)),
    ("shimmering-flats-descent-07", Point(1, -6720.2085, -3982.8975, 86.4639)),
    ("shimmering-flats-descent-08", Point(1, -6708.8862, -3986.8704, 80.4466)),
    ("shimmering-flats-descent-09", Point(1, -6699.4258, -3991.0769, 71.4208)),
    # Hosted movement falls through the lower Detour edge when merely walking.
    # Keep its dense bearings; jump-aware movement begins here, above the
    # earliest observed discontinuity.
    ("shimmering-flats-descent-10", Point(1, -6696.9844, -3992.8206, 68.8040)),
    ("shimmering-flats-descent-11", Point(1, -6694.5435, -3994.5645, 65.0195)),
    ("shimmering-flats-descent-12", Point(1, -6692.5337, -3996.0000, 61.3861)),
    ("shimmering-flats-descent-13", Point(1, -6690.3750, -3998.0830, 57.0616)),
    ("shimmering-flats-descent-14", Point(1, -6688.2163, -4000.1660, 52.7371)),
    ("shimmering-flats-descent-15", Point(1, -6686.0576, -4002.2490, 49.3734)),
    ("shimmering-flats-descent-16", Point(1, -6683.8989, -4004.3320, 46.0482)),
    ("shimmering-flats-descent-17", Point(1, -6681.7397, -4006.4150, 41.8916)),
    ("shimmering-flats-descent-18", Point(1, -6679.5811, -4008.4980, 39.2277)),
    ("shimmering-flats-descent-19", Point(1, -6677.4219, -4010.5811, 37.2181)),
    ("shimmering-flats-descent-20", Point(1, -6675.3003, -4012.7021, 34.1338)),
    ("shimmering-flats-descent-21", Point(1, -6673.1787, -4014.8232, 30.4301)),
    ("shimmering-flats-descent-22", Point(1, -6671.0571, -4016.9443, 26.8428)),
    ("shimmering-flats-descent-23", Point(1, -6668.9355, -4019.0657, 25.3185)),
    ("shimmering-flats-descent-24", Point(1, -6666.8140, -4021.1870, 24.2839)),
    ("shimmering-flats-descent-25", Point(1, -6664.6924, -4023.3083, 21.0995)),
    ("shimmering-flats-descent-26", Point(1, -6662.5708, -4025.4297, 17.3810)),
    ("shimmering-flats-descent-27", Point(1, -6660.4492, -4027.5510, 10.7139)),
    ("shimmering-flats-descent-28", Point(1, -6658.3276, -4029.6724, 5.3928)),
    ("shimmering-flats-descent-29", Point(1, -6656.2065, -4031.7937, 2.3818)),
    ("shimmering-flats-descent-30", Point(1, -6653.6050, -4033.2876, -2.9036)),
    ("shimmering-flats-descent-31", Point(1, -6651.0034, -4034.7815, -6.7836)),
    ("shimmering-flats-descent-32", Point(1, -6648.4019, -4036.2754, -10.6365)),
    ("shimmering-flats-descent-33", Point(1, -6645.8003, -4037.7693, -14.4165)),
    ("shimmering-flats-descent-34", Point(1, -6643.1987, -4039.2632, -18.2413)),
    ("shimmering-flats-descent-35", Point(1, -6640.5972, -4040.7571, -22.1573)),
    ("shimmering-flats-descent-36", Point(1, -6637.9956, -4042.2510, -25.9313)),
    ("shimmering-flats-descent-37", Point(1, -6635.3940, -4043.7446, -29.5975)),
    ("shimmering-flats-descent-38", Point(1, -6632.7925, -4045.2383, -33.1935)),
    ("shimmering-flats-descent-39", Point(1, -6630.1909, -4046.7322, -36.3971)),
    ("shimmering-flats-descent-40", Point(1, -6627.5894, -4048.2258, -38.7222)),
    ("shimmering-flats-descent-41", Point(1, -6624.9878, -4049.7195, -40.9866)),
    ("shimmering-flats-south-road", Point(1, -6624.2671, -4050.1333, -41.6139)),
    # Real Detour corridor from south road to central road 1. This stays west of
    # the authored fence crossing and removes its collision-heavy detour.
    ("shimmering-flats-direct-01", Point(1, -6079.20, -3510.67, -54.02)),
    ("shimmering-flats-direct-02", Point(1, -5983.20, -3479.20, -46.27)),
    ("shimmering-flats-direct-03", Point(1, -5962.13, -3462.67, -49.02)),
    ("shimmering-flats-direct-04", Point(1, -5945.87, -3442.40, -39.02)),
    ("shimmering-flats-direct-05", Point(1, -5925.87, -3433.07, -42.52)),
    ("shimmering-flats-direct-06", Point(1, -5824.00, -3345.33, -34.19)),
    ("shimmering-flats-direct-07", Point(1, -5787.47, -3304.27, -20.94)),
    ("thousand-needles-central-road-1", Point(1, -5745.3672, -3200.0486, -40.1584)),
    ("thousand-needles-central-road-2", Point(1, -5629.6523, -2928.8188, -44.9830)),
    ("thousand-needles-central-road-3", Point(1, -5504.7778, -2670.9585, -49.1217)),
    ("thousand-needles-west-gap-1", Point(1, -5491.94, -2675.34, -46.49)),
    ("thousand-needles-west-gap-2", Point(1, -5480.34, -2663.74, -41.86)),
    ("thousand-needles-west-gap-3", Point(1, -5475.0, -2650.89, -34.78)),
    ("thousand-needles-west-gap-4", Point(1, -5475.0, -2638.4, -34.37)),
    ("thousand-needles-west-gap-5", Point(1, -5475.0, -2624.43, -37.37)),
    ("thousand-needles-west-gap-6", Point(1, -5474.41, -2611.73, -37.64)),
    ("thousand-needles-west-gap-7", Point(1, -5470.83, -2598.68, -37.91)),
    ("thousand-needles-west-road-1", Point(1, -5349.2344, -2439.9663, -31.8258)),
    ("thousand-needles-west-join-01", Point(1, -5356.38, -2452.38, -30.80)),
    ("thousand-needles-west-join-02", Point(1, -5346.52, -2434.62, -33.21)),
    ("thousand-needles-west-join-03", Point(1, -5337.16, -2417.58, -37.98)),
    ("thousand-needles-west-join-04", Point(1, -5330.53, -2399.00, -43.05)),
    ("thousand-needles-west-join-05", Point(1, -5325.61, -2378.58, -41.25)),
    ("thousand-needles-west-join-06", Point(1, -5320.70, -2358.17, -38.68)),
    ("thousand-needles-west-join-07", Point(1, -5315.79, -2337.75, -35.10)),
    ("thousand-needles-west-road-2", Point(1, -5312.8003, -2325.3333, -31.6509)),
    ("thousand-needles-west-corridor-01", Point(1, -5312.76, -2322.33, -31.70)),
    ("thousand-needles-west-corridor-02", Point(1, -5301.80, -2273.13, -38.79)),
    ("thousand-needles-west-corridor-03", Point(1, -5285.92, -2224.58, -48.51)),
    ("thousand-needles-west-corridor-04", Point(1, -5274.15, -2174.95, -51.24)),
    ("thousand-needles-west-corridor-05", Point(1, -5261.78, -2125.63, -48.28)),
    ("thousand-needles-west-corridor-06", Point(1, -5249.55, -2076.13, -55.76)),
    ("thousand-needles-west-corridor-07", Point(1, -5233.77, -2026.64, -60.86)),
    ("thousand-needles-west-corridor-08", Point(1, -5219.72, -1976.15, -62.27)),
    ("thousand-needles-west-corridor-09", Point(1, -5207.91, -1926.54, -61.41)),
    ("thousand-needles-west-corridor-10", Point(1, -5180.92, -1881.56, -55.92)),
    ("thousand-needles-west-corridor-11", Point(1, -5147.82, -1841.15, -47.35)),
    ("thousand-needles-west-corridor-12", Point(1, -5120.00, -1800.00, -53.46)),
    ("thousand-needles-west-3", Point(1, -5116.142, -1794.543, -55.277)),
    ("great-lift-south-road", Point(1, -4971.3, -1718.92, -59.379)),
    ("great-lift-lower-corridor-02", Point(1, -4950.90, -1741.49, -58.27)),
    ("great-lift-lower-corridor-03", Point(1, -4933.11, -1761.80, -52.81)),
    ("great-lift-lower-corridor-04", Point(1, -4915.32, -1782.11, -39.38)),
    ("great-lift-lower-corridor-05", Point(1, -4890.05, -1791.43, -33.24)),
    ("great-lift-lower-corridor-06", Point(1, -4865.89, -1803.26, -43.44)),
    ("great-lift-lower-corridor-07", Point(1, -4839.29, -1812.35, -51.69)),
    ("great-lift-lower-corridor-08", Point(1, -4813.06, -1818.73, -50.97)),
    ("great-lift-lower-corridor-09", Point(1, -4786.67, -1816.02, -42.44)),
    ("great-lift-lower-corridor-10", Point(1, -4759.60, -1809.07, -41.79)),
    ("great-lift-lower-corridor-11", Point(1, -4733.23, -1822.99, -40.99)),
    ("great-lift-lower-corridor-12", Point(1, -4710.47, -1836.84, -47.05)),
    ("great-lift-lower-corridor-13", Point(1, -4691.20, -1856.00, -48.29)),
    ("great-lift-lower-dock", GREAT_LIFT_LOWER_DOCK),
)
NORTHERN_DIRECT_POINTS = (
    Point(1, -9201.9385, -2547.2900, 12.8364),
    Point(1, -9225.2002, -2574.7705, 17.0310),
    Point(1, -9248.4590, -2602.2510, 13.0435),
    Point(1, -9265.9004, -2622.8613, 15.2396),
    Point(1, -9283.3428, -2643.4717, 11.3030),
    Point(1, -9311.9990, -2677.3333, 10.0711),
    Point(1, -9311.9990, -2680.3333, 10.1414),
    Point(1, -9311.9990, -2749.3333, 17.7515),
    Point(1, -9311.9990, -2784.0000, 15.9814),
    Point(1, -9311.9990, -2784.0000, 14.8836),
    Point(1, -9309.7412, -2785.9756, 15.8256),
    Point(1, -9287.1631, -2805.7314, 10.4937),
    Point(1, -9221.6865, -2863.0234, 15.2442),
    Point(1, -9183.3037, -2896.6084, 22.9341),
    Point(1, -9141.3330, -2933.3330, 37.7650),
    Point(1, -9141.3330, -2933.3330, 36.9461),
    Point(1, -9138.3330, -2933.3330, 38.9603),
    Point(1, -9111.3330, -2933.3330, 46.1851),
    Point(1, -9084.3330, -2933.3330, 46.2564),
    Point(1, -9024.3330, -2933.3330, 52.6850),
    Point(1, -8961.3330, -2933.3330, 54.1315),
    Point(1, -8946.3330, -2933.3330, 52.0335),
    Point(1, -8913.3330, -2933.3330, 42.5448),
    Point(1, -8901.3330, -2933.3330, 40.9573),
    Point(1, -8871.3330, -2933.3330, 41.7540),
    Point(1, -8844.3330, -2933.3330, 38.5190),
    Point(1, -8811.3330, -2933.3330, 26.2971),
    Point(1, -8799.3330, -2933.3330, 23.8282),
    Point(1, -8784.3330, -2933.3330, 22.0392),
    Point(1, -8739.3330, -2933.3330, 23.6317),
    Point(1, -8721.3330, -2933.3330, 20.8830),
    Point(1, -8693.3330, -2933.3330, 13.5493),
    Point(1, -8690.4873, -2932.3843, 13.2140),
    Point(1, -8661.3330, -2922.6665, 13.1642),
    Point(1, -8650.5986, -2917.3003, 13.5459),
    Point(1, -8618.6660, -2901.3333, 9.6642),
    Point(1, -8577.9238, -2891.1477, 9.4391),
    Point(1, -8557.5527, -2886.0549, 11.0500),
    Point(1, -8534.2715, -2880.2346, 9.9670),
    Point(1, -8513.9004, -2875.1418, 11.3841),
    Point(1, -8484.7988, -2867.8665, 9.3834),
    Point(1, -8448.0000, -2858.6665, 9.3054),
    Point(1, -8379.6963, -2848.9072, 10.0659),
    Point(1, -8352.9688, -2845.0894, 14.1907),
    Point(1, -8320.3018, -2840.4236, 12.5977),
    Point(1, -8298.6660, -2837.3333, 14.8054),
    Point(1, -8271.2002, -2815.9998, 19.5554),
    Point(1, -8264.3809, -2809.0518, 24.4245),
    Point(1, -8258.3994, -2804.2666, 30.8054),
    Point(1, -8256.0918, -2798.7280, 35.2331),
    Point(1, -8251.1572, -2789.6179, 30.7964),
    Point(1, -8246.2939, -2782.0452, 30.7621),
    Point(1, -8241.9551, -2775.2888, 32.6385),
    Point(1, -8241.9229, -2772.2891, 34.8848),
    Point(1, -8241.7314, -2754.2905, 35.8520),
    Point(1, -8241.5996, -2741.8665, 34.0554),
    Point(1, -8235.9824, -2726.1208, 27.7648),
    Point(1, -8230.5801, -2715.4050, 28.5342),
    Point(1, -8227.8789, -2710.0471, 26.4692),
    Point(1, -8222.4785, -2699.3308, 26.0194),
    Point(1, -8220.7998, -2696.0000, 24.0554),
    Point(1, -8218.8896, -2684.1533, 14.7061),
    Point(1, -8212.6816, -2645.6516, 10.0505),
    Point(1, -8208.8613, -2621.9583, 9.5544),
    Point(1, -8206.4736, -2607.1499, 11.7032),
    Point(1, -8203.6084, -2589.3789, 9.6460),
    Point(1, -8195.4941, -2539.0264, 9.5865),
    Point(1, -8193.5859, -2527.1787, 11.5551),
    Point(1, -8192.0000, -2517.3333, 9.5798),
    Point(1, -8191.0015, -2502.3662, 11.2059),
    Point(1, -8188.6050, -2466.4453, 9.8291),
    Point(1, -8187.8062, -2454.4717, 12.3227),
    Point(1, -8186.6089, -2436.5112, 9.6908),
    Point(1, -8185.4121, -2418.5508, 9.8297),
    Point(1, -8184.8140, -2409.5706, 13.3115),
    Point(1, -8184.2153, -2400.5903, 9.8641),
    Point(1, -8183.4175, -2388.6167, 9.8298),
    Point(1, -8182.8193, -2379.6365, 11.7712),
    Point(1, -8181.3330, -2357.3333, 10.3369),
    Point(1, -8180.3843, -2354.4873, 10.5691),
    Point(1, -8170.6665, -2325.3333, 10.8298),
    Point(1, -8166.3999, -2259.6001, 9.7366),
    Point(1, -8166.4966, -2256.6016, 9.7954),
    Point(1, -8166.9800, -2241.6089, 11.4980),
    Point(1, -8167.4634, -2226.6162, 23.4135),
    Point(1, -8167.5601, -2223.6177, 23.9801),
    Point(1, -8168.0000, -2210.0000, 14.2362),
    Point(1, -8168.0000, -2210.0000, 10.0000),
    Point(1, -8132.5300, -2196.9800, 7.4100),
    Point(1, -8131.9258, -2200.3137, 7.8621),
    Point(1, -8130.1172, -2212.1682, 5.4273),
    Point(1, -8128.0000, -2218.6667, 9.5798),
    Point(1, -8116.2109, -2220.9077, 2.0813),
    Point(1, -8107.3691, -2222.5884, 3.1145),
    Point(1, -8095.7329, -2224.8000, -1.4202),
    Point(1, -8092.8931, -2225.7668, -3.5216),
    Point(1, -8083.1997, -2229.0667, -18.1702),
    Point(1, -8074.9331, -2229.0667, -14.9202),
    Point(1, -8069.1899, -2230.8015, -5.7858),
    Point(1, -8063.4468, -2232.5364, -4.2638),
    Point(1, -8054.8315, -2235.1392, -4.5924),
    Point(1, -8049.3330, -2236.8000, -5.9202),
    Point(1, -8042.7637, -2235.8220, -11.7637),
    Point(1, -8037.8667, -2234.1333, -10.6702),
    Point(1, -8034.1187, -2229.4482, -10.8933),
    Point(1, -8032.9600, -2228.0000, -13.4828),
    Point(1, -8032.9600, -2228.0000, -14.7700),
    Point(1, -8031.0547, -2230.3171, -8.9216),
    Point(1, -8029.1494, -2232.6343, -7.0588),
    Point(1, -8025.0664, -2237.5999, -8.9202),
    Point(1, -8022.4580, -2243.0032, -13.6339),
    Point(1, -8021.3330, -2245.3333, -13.6702),
    Point(1, -8016.7998, -2254.6665, 2.0798),
    Point(1, -8011.6440, -2257.7354, 6.9312),
    Point(1, -8005.5996, -2261.3333, 9.0798),
    Point(1, -7999.6074, -2261.6299, 8.8308),
    Point(1, -7984.6270, -2262.3716, 19.8055),
    Point(1, -7975.2002, -2262.9333, 19.8298),
    Point(1, -7969.3057, -2264.0525, 22.1390),
    Point(1, -7963.4111, -2265.1716, 20.8129),
    Point(1, -7954.1333, -2266.9333, 15.8298),
    Point(1, -7943.1450, -2271.7556, 14.4956),
    Point(1, -7929.4097, -2277.7834, 22.8785),
    Point(1, -7921.1685, -2281.4001, 21.5892),
    Point(1, -7911.1831, -2284.3767, 25.2748),
    Point(1, -7906.3999, -2285.3333, 24.3298),
    Point(1, -7900.4839, -2284.3357, 24.7446),
    Point(1, -7897.8999, -2283.8999, 22.8882),
    Point(1, -7897.9000, -2283.9000, 22.3000),
    Point(1, -7897.4585, -2286.8672, 23.3076),
    Point(1, -7894.8086, -2304.6709, 17.9589),
    Point(1, -7893.0420, -2316.5400, 16.3619),
    Point(1, -7891.7334, -2325.3333, 18.0798),
    Point(1, -7889.0322, -2330.6912, 18.2174),
    Point(1, -7886.3311, -2336.0491, 20.9545),
    Point(1, -7882.2793, -2344.0859, 21.0762),
    Point(1, -7878.2275, -2352.1228, 19.2083),
    Point(1, -7875.5269, -2357.4805, 14.9387),
    Point(1, -7874.8003, -2363.4365, 10.7064),
    Point(1, -7872.9844, -2378.3267, 8.0475),
    Point(1, -7872.0000, -2386.3999, 10.8298),
    Point(1, -7874.3218, -2384.5002, 12.6104),
    Point(1, -7869.0669, -2389.3333, 10.0798),
    Point(1, -7866.0869, -2389.6787, 8.9939),
    Point(1, -7863.1069, -2390.0242, 9.5190),
    Point(1, -7857.1470, -2390.7151, 14.4460),
    Point(1, -7850.6665, -2391.4666, 14.8298),
    Point(1, -7848.4170, -2393.4514, 14.8297),
    Point(1, -7846.1675, -2395.4363, 13.1062),
    Point(1, -7841.3979, -2406.4480, 7.3884),
    Point(1, -7835.4668, -2419.2000, 12.0798),
    Point(1, -7829.0186, -2425.4783, 9.9304),
    Point(1, -7825.3335, -2429.0667, 6.5798),
    Point(1, -7804.2666, -2442.1333, -0.9202),
    Point(1, -7795.9185, -2445.4944, -4.3391),
    Point(1, -7790.3530, -2447.7351, 0.5030),
    Point(1, -7783.7334, -2450.3999, 10.8298),
    Point(1, -7768.9897, -2453.1643, 24.6981),
    Point(1, -7766.0410, -2453.7173, 24.8884),
    Point(1, -7759.4189, -2454.7361, 21.4830),
    Point(1, -7750.4761, -2455.7446, 21.4280),
    Point(1, -7738.5522, -2457.0894, 26.9996),
    Point(1, -7723.6475, -2458.7703, 21.2382),
    Point(1, -7699.7998, -2461.4600, 22.9797),
    Point(1, -7685.6914, -2464.0259, 17.3194),
    Point(1, -7674.1406, -2467.2778, 14.3720),
    Point(1, -7664.0000, -2470.1333, 4.0798),
    Point(1, -7658.6670, -2471.2000, 1.8298),
    Point(1, -7639.1348, -2474.6179, 10.2492),
    Point(1, -7634.3521, -2475.2666, 9.3357),
    Point(1, -7625.4077, -2476.2673, 3.9295),
    Point(1, -7616.4634, -2477.2683, 2.6377),
    Point(1, -7596.2021, -2479.3069, -12.0472),
    Point(1, -7591.7334, -2479.4666, -8.1702),
    Point(1, -7587.2002, -2479.2000, 3.3298),
    Point(1, -7585.2886, -2476.8877, 4.2524),
    Point(1, -7581.4653, -2472.2632, 0.4810),
    Point(1, -7577.2798, -2467.2000, -8.5278),
    Point(1, -7577.2800, -2467.2000, -9.4700),
    Point(1, -7575.8779, -2469.8523, -4.2756),
    Point(1, -7573.3335, -2474.6665, -3.4202),
    Point(1, -7571.9478, -2477.3271, -7.2362),
    Point(1, -7569.1763, -2482.6484, -22.7980),
    Point(1, -7566.6670, -2487.4666, -23.9202),
    Point(1, -7560.2056, -2493.7317, -7.1856),
    Point(1, -7556.2666, -2497.5999, -5.4202),
    Point(1, -7554.0840, -2506.3311, 1.1431),
    Point(1, -7552.0000, -2514.6665, 11.5798),
    Point(1, -7549.2266, -2523.2285, 15.4369),
    Point(1, -7545.8667, -2533.5999, 24.5798),
    Point(1, -7533.6001, -2545.8665, 32.8298),
    Point(1, -7525.1758, -2549.0342, 37.3776),
    Point(1, -7519.5596, -2551.1460, 42.5397),
    Point(1, -7513.9434, -2553.2576, 43.4257),
    Point(1, -7500.2666, -2558.3999, 32.0798),
    Point(1, -7491.3428, -2559.5637, 23.8795),
    Point(1, -7467.8604, -2564.4668, 25.0653),
    Point(1, -7457.8667, -2566.6665, 27.2416),
    Point(1, -7443.7212, -2571.6592, 25.4716),
    Point(1, -7433.7422, -2573.3860, 17.2756),
    Point(1, -7421.7598, -2574.0251, 20.3718),
    Point(1, -7403.7861, -2574.9839, 28.9064),
    Point(1, -7395.4663, -2574.9331, 30.7416),
    Point(1, -7389.4819, -2574.4937, 29.2980),
    Point(1, -7380.5054, -2573.8345, 21.5866),
    Point(1, -7374.5210, -2573.3950, 18.6695),
    Point(1, -7368.5366, -2572.9556, 18.5862),
    Point(1, -7359.5601, -2572.2964, 21.8581),
    Point(1, -7338.6147, -2570.7583, 25.8802),
    Point(1, -7323.6538, -2569.6602, 20.4117),
    Point(1, -7319.1997, -2569.3333, 22.4916),
    Point(1, -7304.2852, -2570.9312, 17.2463),
    Point(1, -7299.5635, -2574.6338, 17.6205),
    Point(1, -7292.4810, -2580.1877, 14.7256),
    Point(1, -7274.6665, -2592.2666, 15.7416),
    Point(1, -7266.6665, -2600.5332, 17.9916),
    Point(1, -7265.0664, -2601.8665, 16.9916),
    Point(1, -7259.0801, -2602.2747, 18.6300),
    Point(1, -7253.3330, -2602.6665, 14.9916),
    Point(1, -7253.7051, -2599.6897, 16.2706),
    Point(1, -7247.7314, -2599.1272, 12.8014),
    Point(1, -7238.7710, -2598.2834, 13.0280),
    Point(1, -7217.8633, -2596.3147, 10.1519),
    Point(1, -7182.0215, -2592.9382, 11.0536),
    Point(1, -7173.0610, -2592.0940, 12.6795),
    Point(1, -7163.4092, -2591.2334, 21.0953),
    Point(1, -7157.4277, -2590.7671, 24.1201),
    Point(1, -7148.4556, -2590.0681, 20.8275),
    Point(1, -7130.5112, -2588.6699, 19.0316),
    Point(1, -7112.0000, -2587.4666, 11.9916),
    Point(1, -7097.0317, -2586.4827, 11.1806),
    Point(1, -7079.0698, -2585.3020, 13.2119),
    Point(1, -7067.0952, -2584.5149, 17.6372),
    Point(1, -7052.1270, -2583.5315, 18.1103),
    Point(1, -7043.1460, -2582.9414, 15.0833),
    Point(1, -7018.6665, -2581.3333, 23.2416),
    Point(1, -7021.6665, -2581.3333, 22.0815),
    Point(1, -7013.6978, -2585.5161, 23.3823),
    Point(1, -7005.8667, -2589.5999, 20.2416),
    Point(1, -6988.0396, -2592.0813, 20.6176),
    Point(1, -6979.1260, -2593.3220, 16.7264),
    Point(1, -6964.2700, -2595.3899, 14.7523),
    Point(1, -6946.4429, -2597.8713, 9.7389),
    Point(1, -6912.0000, -2602.6665, 9.5822),
    Point(1, -6849.0513, -2605.0813, 10.5875),
    Point(1, -6814.6670, -2606.3999, 19.3322),
    Point(1, -6799.9429, -2603.5300, 25.9150),
    Point(1, -6785.2192, -2600.6602, 37.1922),
    Point(1, -6777.4199, -2598.6567, 48.1412),
    Point(1, -6760.0791, -2593.8276, 84.2516),
    Point(1, -6741.0669, -2588.5332, 102.0822),
    Point(1, -6720.1421, -2586.7627, 120.0921),
    Point(1, -6714.1636, -2586.2568, 123.0829),
    Point(1, -6702.2065, -2585.2446, 125.7116),
    Point(1, -6669.3247, -2582.4612, 141.0981),
    Point(1, -6656.0000, -2581.3333, 144.0822),
    Point(1, -6659.0000, -2581.3333, 143.8889),
    Point(1, -6652.5337, -2569.3333, 160.3322),
    Point(1, -6634.6670, -2559.9998, 168.3322),
    Point(1, -6637.6670, -2559.9998, 169.7825),
    Point(1, -6624.4370, -2552.9304, 180.5508),
    Point(1, -6619.1450, -2550.1023, 176.2039),
    Point(1, -6605.9150, -2543.0325, 147.0294),
    Point(1, -6596.6567, -2536.3059, 133.9622),
    Point(1, -6591.9390, -2532.5989, 132.2688),
    Point(1, -6575.4268, -2519.6248, 147.0687),
    Point(1, -6566.4004, -2512.5332, 148.0822),
    Point(1, -6560.8896, -2510.1606, 147.4729),
    Point(1, -6552.6235, -2506.6018, 141.3670),
    Point(1, -6544.3574, -2503.0427, 130.5368),
    Point(1, -6536.0913, -2499.4836, 122.6805),
    Point(1, -6530.5806, -2497.1108, 119.6088),
    Point(1, -6517.4517, -2490.2786, 117.7037),
    Point(1, -6512.2671, -2487.4666, 118.5822),
    Point(1, -6508.5244, -2482.7771, 118.5862),
    Point(1, -6502.9106, -2475.7429, 124.6978),
    Point(1, -6497.2969, -2468.7087, 127.8431),
    Point(1, -6486.0693, -2454.6404, 123.8259),
    Point(1, -6482.3267, -2449.9509, 124.4162),
    Point(1, -6472.9702, -2438.2273, 129.8940),
    Point(1, -6468.0005, -2432.0000, 136.0822),
    Point(1, -6464.7246, -2420.4561, 140.5209),
    Point(1, -6462.4004, -2412.2666, 139.0822),
    Point(1, -6455.1885, -2403.8513, 140.4027),
    Point(1, -6449.3101, -2397.0361, 139.6039),
    Point(1, -6436.3032, -2382.9692, 131.0386),
    Point(1, -6427.8174, -2374.4839, 128.4914),
    Point(1, -6421.4536, -2368.1199, 121.7101),
    Point(1, -6409.5396, -2366.6863, 109.1332),
    Point(1, -6403.5825, -2365.9692, 105.7175),
    Point(1, -6397.6255, -2365.2522, 104.7709),
    Point(1, -6391.1113, -2363.6133, 106.3131),
    Point(1, -6371.8237, -2355.3071, 121.3402),
    Point(1, -6366.3130, -2352.9338, 119.0181),
    Point(1, -6358.0469, -2349.3738, 112.1594),
    Point(1, -6354.4619, -2348.1985, 111.5797),
    Point(1, -6345.8667, -2345.5999, 115.3834),
    Point(1, -6337.0659, -2337.4426, 124.8030),
    Point(1, -6325.3633, -2328.2263, 125.5028),
    Point(1, -6315.7930, -2320.9863, 123.7618),
    Point(1, -6304.2666, -2312.2666, 127.1334),
    Point(1, -6287.0078, -2307.1514, 143.3981),
    Point(1, -6278.3784, -2304.5938, 147.7012),
    Point(1, -6272.6255, -2302.8887, 148.4481),
    Point(1, -6263.9961, -2300.3311, 145.8576),
    Point(1, -6246.7373, -2295.2158, 134.0245),
    Point(1, -6240.9844, -2293.5107, 133.1837),
    Point(1, -6229.4785, -2290.1006, 139.1790),
    Point(1, -6223.7256, -2288.3953, 140.2462),
    Point(1, -6212.2197, -2284.9844, 136.0812),
    Point(1, -6199.6138, -2280.4661, 127.3121),
    Point(1, -6194.0229, -2278.2881, 125.3706),
    Point(1, -6160.4780, -2265.2200, 123.6080),
    Point(1, -6124.1377, -2251.0630, 127.6573),
    Point(1, -6103.5649, -2247.1453, 124.5589),
    Point(1, -6068.0103, -2241.4871, 124.1941),
    Point(1, -6058.6670, -2240.0000, 122.3834),
    Point(1, -6042.1377, -2232.8706, 113.6905),
    Point(1, -6033.8730, -2229.3059, 111.0816),
    Point(1, -6025.6084, -2225.7412, 112.2733),
    Point(1, -6003.5693, -2216.2358, 122.5178),
    Point(1, -5984.2852, -2207.9185, 121.2503),
    Point(1, -5975.2002, -2204.0000, 126.1334),
    Point(1, -5966.2456, -2203.0940, 131.5926),
    Point(1, -5957.2910, -2202.1877, 131.0534),
    Point(1, -5948.3364, -2201.2812, 128.4365),
    Point(1, -5936.3970, -2200.0728, 129.6926),
    Point(1, -5909.5332, -2197.3535, 129.1378),
    Point(1, -5888.2305, -2176.2288, 129.1334),
    Point(1, -5867.7192, -1897.9780, 129.0857),
    Point(1, -5867.4990, -1894.9861, 128.8932),
    Point(1, -5867.1567, -1887.9337, 122.5503),
    Point(1, -5866.6670, -1870.1333, 116.8615),
    Point(1, -5862.6665, -1866.6666, 102.9566),
    Point(1, -5858.1333, -1865.6000, 91.4566),
    Point(1, -5852.1675, -1866.2413, 87.2719),
    Point(1, -5802.5332, -1870.9333, 84.9537),
    Point(1, -5770.3999, -1870.9333, 86.4566),
    Point(1, -5584.3838, -1837.5579, 87.3734),
    Point(1, -5575.5259, -1835.9689, 86.3791),
    Point(1, -5568.2666, -1834.6666, 81.9566),
    Point(1, -5566.6880, -1828.8781, 83.9306),
    Point(1, -5562.7808, -1820.7706, 84.9418),
    Point(1, -5550.3999, -1808.0000, 82.7066),
    Point(1, -5546.1572, -1803.7574, 77.1880),
    Point(1, -5540.2153, -1797.9438, 73.7610),
    Point(1, -5538.0308, -1795.8878, 70.9237),
    Point(1, -5530.1333, -1792.0000, 52.2066),
    Point(1, -5532.7319, -1793.4991, 58.7740),
    Point(1, -5531.6235, -1787.6024, 61.0697),
    Point(1, -5529.9609, -1778.7573, 76.5083),
    Point(1, -5527.7441, -1766.9639, 82.2137),
    Point(1, -5526.6362, -1761.0670, 81.7792),
    Point(1, -5526.0820, -1758.1187, 83.0841),
    Point(1, -5525.3335, -1754.1333, 87.4566),
    Point(1, -5520.7998, -1745.3334, 88.9566),
    Point(1, -5516.6240, -1741.0250, 87.9559),
    Point(1, -5512.4482, -1736.7167, 89.6121),
    Point(1, -5504.0967, -1728.0997, 89.2186),
    Point(1, -5504.0581, -1719.0997, 90.1524),
    Point(1, -5504.0000, -1700.6667, 88.7816),
    Point(1, -5504.0000, -1685.3334, 83.9566),
    Point(1, -5503.1177, -1682.4661, 82.0266),
    Point(1, -5496.9458, -1675.9158, 74.5815),
    Point(1, -5479.4668, -1658.1334, 48.4566),
    Point(1, -5474.9619, -1666.6024, 24.8270),
    Point(1, -5466.6665, -1685.3334, 8.7066),
    Point(1, -5460.7778, -1686.4855, -5.8479),
    Point(1, -5454.3999, -1687.7334, -11.0434),
    Point(1, -5448.9380, -1690.2163, -29.0782),
    Point(1, -5442.9766, -1693.1881, -37.3050),
    Point(1, -5429.8589, -1700.4615, -39.5816),
    Point(1, -5418.6665, -1706.6667, -37.0434),
    Point(1, -5419.3252, -1703.7399, -38.6898),
    Point(1, -5403.3467, -1712.0281, -35.6595),
    Point(1, -5363.4004, -1732.7498, -41.4343),
    Point(1, -5350.0850, -1739.6569, -45.1391),
    Point(1, -5339.4326, -1745.1826, -44.8302),
    Point(1, -5324.7271, -1758.7141, -49.2350),
    Point(1, -5302.4004, -1780.5333, -53.2137),
    Point(1, -5291.7334, -1782.4000, -54.2137),
    Point(1, -5240.7832, -1780.1173, -57.5238),
    Point(1, -5228.7949, -1779.5802, -59.8076),
    Point(1, -5144.8770, -1775.8206, -63.7546),
    Point(1, -5132.8887, -1775.2837, -63.3656),
    Point(1, -5129.8916, -1775.1494, -60.2706),
    Point(1, -5125.0669, -1774.9333, -59.4637),
    Point(1, -5043.5601, -1776.7823, -60.5711),
    Point(1, -5025.5659, -1777.1932, -58.7370),
    Point(1, -5016.5688, -1777.3986, -62.2212),
    Point(1, -4998.5747, -1777.8091, -62.5693),
    Point(1, -4989.5776, -1778.0143, -61.7267),
    Point(1, -4980.5806, -1778.2196, -56.9252),
    Point(1, -4962.5864, -1778.6301, -53.2733),
    Point(1, -4959.5874, -1778.6985, -51.9847),
    Point(1, -4953.5894, -1778.8353, -45.2705),
    Point(1, -4941.5933, -1779.1090, -43.6104),
    Point(1, -4937.6001, -1779.2001, -46.4637),
    Point(1, -4918.5483, -1788.0355, -36.9807),
    Point(1, -4902.2183, -1795.6088, -33.1211),
    Point(1, -4891.3315, -1800.6576, -34.5680),
    Point(1, -4864.1147, -1813.2803, -48.1557),
    Point(1, -4831.3726, -1817.4125, -52.7648),
    Point(1, -4819.4663, -1818.9153, -52.8628),
    Point(1, -4813.5132, -1819.6666, -51.1006),
    Point(1, -4807.5601, -1820.4181, -46.5805),
    Point(1, -4804.5835, -1820.7937, -46.4637),
    Point(1, -4798.7314, -1819.8679, -42.9528),
    Point(1, -4773.0630, -1811.4995, -43.3515),
    Point(1, -4765.6001, -1809.0667, -41.7949),
    Point(1, -4758.9331, -1809.0667, -41.7949),
    Point(1, -4748.9077, -1814.1479, -42.5778),
    Point(1, -4730.6182, -1824.4653, -40.6555),
    Point(1, -4722.7798, -1828.8870, -41.7848),
    Point(1, -4712.5332, -1834.6666, -44.2949),
    Point(1, -4707.5342, -1837.9845, -50.5449),
    Point(1, -4705.0347, -1839.6436, -51.4340),
    Point(1, -4692.5371, -1847.9384, -51.4638),
    Point(1, -4681.9976, -1854.7472, -49.2949),
)

# The pinned 0.1.209 Detour chain from the movement bootstrap exposes a
# materially shorter northern corridor than the older partial-path frontier.
# It rejoins the proven dense route at direct 218, preserving all downstream
# terrain controls while removing roughly 1,300 route yards from Tanaris.
NORTHERN_SHORTCUT_POINTS = (
    Point(1, -9062.0000, -2547.0889, 22.3725),
    Point(1, -8879.0000, -2549.8589, 18.0541),
    Point(1, -8810.0000, -2550.9033, 11.8095),
    Point(1, -8726.0000, -2552.1746, 18.2192),
    Point(1, -8669.0000, -2553.0352, 32.3304),
    Point(1, -8618.0000, -2553.8049, 32.9351),
    Point(1, -8552.0000, -2554.8015, 47.5041),
    Point(1, -8492.0000, -2555.7073, 42.4412),
    Point(1, -8435.0000, -2556.5679, 47.5975),
    Point(1, -8384.0000, -2557.3379, 39.1105),
    Point(1, -8321.0000, -2558.2891, 38.6434),
    Point(1, -8300.0000, -2558.6062, 33.0068),
    Point(1, -8277.3330, -2562.1333, 14.8298),
    Point(1, -8253.3408, -2562.7114, 10.5071),
    Point(1, -8089.0664, -2566.6665, 9.0798),
    Point(1, -8080.0664, -2566.6665, 13.2536),
    Point(1, -8062.6763, -2566.1665, 9.1319),
    Point(1, -7914.6665, -2559.9998, 10.3298),
    Point(1, -7824.9893, -2530.3213, 9.2457),
    Point(1, -7808.0000, -2524.7998, 13.5798),
    Point(1, -7636.2666, -2524.9746, 9.8039),
    Point(1, -7558.2666, -2525.0540, 22.3125),
    Point(1, -7541.8667, -2524.7998, 12.5798),
    Point(1, -7535.9565, -2534.5874, 13.7895),
    Point(1, -7513.8555, -2551.5498, 39.4051),
    Point(1, -7491.3428, -2559.5637, 23.8795),
    Point(1, -7457.8667, -2566.6665, 27.2416),
    Point(1, -7443.7212, -2571.6592, 25.4716),
    Point(1, -7433.7422, -2573.3860, 17.2756),
    Point(1, -7395.4663, -2574.9331, 30.7416),
    Point(1, -7374.5210, -2573.3950, 18.6695),
    Point(1, -7338.6147, -2570.7583, 25.8802),
    Point(1, -7304.2852, -2570.9312, 17.2463),
    Point(1, -7265.0664, -2601.8665, 16.9916),
)

# One-yard simplification of the pinned Detour sub-corridor across the narrow
# shortcut shelf. The earlier three-yard whole-route simplification omitted the
# -7979/-7899 bends and placed one exact anchor just outside its polygon.
NORTHERN_SHORTCUT_SHELF_POINTS = (
    Point(1, -8250.3418, -2562.7837, 10.2155),
    Point(1, -8238.3457, -2563.0728, 11.8713),
    Point(1, -8229.3486, -2563.2896, 9.8298),
    Point(1, -8211.3545, -2563.7231, 10.9396),
    Point(1, -8193.3604, -2564.1567, 9.6162),
    Point(1, -8142.3770, -2565.3840, 10.5191),
    Point(1, -8089.0664, -2566.6665, 9.0798),
    Point(1, -8080.0664, -2566.6665, 13.2536),
    Point(1, -8065.6885, -2566.0432, 9.0316),
    Point(1, -7978.9009, -2560.0161, 9.5798),
    Point(1, -7899.4697, -2544.1523, 10.9336),
    Point(1, -7884.7603, -2541.2148, 9.5798),
    Point(1, -7830.9375, -2529.5471, 9.6098),
    Point(1, -7808.0000, -2524.7998, 13.5798),
    Point(1, -7793.0000, -2524.6802, 15.0539),
    Point(1, -7745.0000, -2524.2974, 9.4583),
    Point(1, -7703.0000, -2523.9624, 9.5546),
    Point(1, -7688.0000, -2523.8430, 11.2673),
    Point(1, -7679.0000, -2523.7715, 9.5413),
    Point(1, -7637.0000, -2523.4382, 9.7781),
    Point(1, -7625.0000, -2523.3430, 10.6010),
    Point(1, -7607.0000, -2523.2002, 17.8603),
    Point(1, -7592.0000, -2523.0813, 16.2083),
    Point(1, -7561.3530, -2522.2417, 22.2424),
    Point(1, -7545.6001, -2521.3333, 12.5798),
    Point(1, -7541.8667, -2524.7998, 12.5798),
)

# Alternate 5.66k-yard pinned chain from the exact spawn. Unlike the bootstrap
# frontier above, it stays on the northern component and bypasses the hazardous
# -8250..-7540 shelf before rejoining the proven dense route at direct 221.
NORTHERN_BYPASS_POINTS = (
    Point(1, -9061.0410, -2526.8816, 19.6295),
    Point(1, -8911.0898, -2522.8716, 17.8200),
    Point(1, -8812.1221, -2520.2249, 11.0412),
    Point(1, -8767.1367, -2519.0217, 14.2344),
    Point(1, -8704.1572, -2517.3374, 26.1498),
    Point(1, -8671.8232, -2510.7498, 33.5284),
    Point(1, -8639.9990, -2504.2666, 34.1890),
    Point(1, -8592.1934, -2490.7046, 45.9575),
    Point(1, -8527.4824, -2477.7625, 42.1040),
    Point(1, -8458.2637, -2469.2744, 48.0096),
    Point(1, -8419.4541, -2465.3796, 42.7073),
    Point(1, -8356.7617, -2459.0854, 44.4646),
    Point(1, -8323.9229, -2455.7886, 36.9721),
    Point(1, -8311.9814, -2454.5896, 41.8894),
    Point(1, -8287.7402, -2450.7922, 14.5818),
    Point(1, -8280.5225, -2449.2913, 11.7463),
    Point(1, -8192.1924, -2432.0376, 9.6074),
    Point(1, -7876.7627, -2425.4487, 9.8283),
    Point(1, -7861.7651, -2425.1956, 13.5082),
    Point(1, -7845.3164, -2426.8750, 25.8298),
    Point(1, -7795.6606, -2444.7678, -5.9771),
    Point(1, -7785.6001, -2447.4666, 0.5798),
    Point(1, -7783.7334, -2450.3999, 10.8298),
    Point(1, -7769.0752, -2453.5864, 25.3965),
    Point(1, -7755.6558, -2461.4966, 20.3847),
    Point(1, -7743.3721, -2470.2776, 22.3941),
    Point(1, -7724.3867, -2482.5088, 10.2233),
    Point(1, -7616.0000, -2538.6665, 10.0798),
    Point(1, -7616.0894, -2535.6677, 10.3819),
    Point(1, -7573.3335, -2538.6665, 12.0798),
    Point(1, -7525.8276, -2571.9609, 33.1852),
    Point(1, -7517.3335, -2578.6665, 29.8298),
    Point(1, -7519.5269, -2576.6196, 31.7488),
    Point(1, -7503.4668, -2579.2000, 30.3298),
    Point(1, -7505.2314, -2576.7737, 35.0858),
    Point(1, -7496.0000, -2574.9331, 32.5798),
    Point(1, -7497.9526, -2577.2109, 29.8342),
    Point(1, -7480.6704, -2572.1807, 36.9307),
    Point(1, -7442.0088, -2572.9116, 24.1222),
    Point(1, -7433.7422, -2573.3860, 17.2756),
    Point(1, -7395.4663, -2574.9331, 30.7416),
    Point(1, -7374.5210, -2573.3950, 18.6695),
    Point(1, -7338.6147, -2570.7583, 25.8802),
    Point(1, -7319.1997, -2569.3333, 22.4916),
    Point(1, -7304.2852, -2570.9312, 17.2463),
    Point(1, -7266.6665, -2600.5332, 17.9916),
    Point(1, -7253.3330, -2602.6665, 14.9916),
    Point(1, -7253.7051, -2599.6897, 16.2706),
)

NORTHERN_SAFE_BRIDGE_POINTS = (
    Point(1, -8189.1924, -2432.0325, 9.6129),
    Point(1, -8180.0000, -2300.0000, 10.1657),
    Point(1, -7940.0000, -2300.0000, 9.9131),
    Point(1, -7872.0850, -2386.4590, 10.9503),
)

# The source route's direct 336 -> 337 chord is a 50-yard, five-degree line on
# a narrow ledge. Coarse heading control holds the starting y until the ledge
# falls away. These real-navmesh anchors keep lateral error observable.
NORTHERN_LEDGE_POINTS = (
    Point(1, -5837.2529, -1867.8451, 86.7066),
    Point(1, -5822.3384, -1869.4489, 86.5288),
    Point(1, -5808.5332, -1870.9333, 85.4566),
)

# Runners reach direct 338 airborne over the narrow east-west ledge. Hold that
# heading until the observed z86 landing surface instead of turning northeast
# toward distant direct 339 while still falling.
NORTHERN_LEDGE_LANDING = Point(1, -5759.0, -1876.0, 86.1)

# The source direct 309--312 chord and short southern arc both cross a narrow
# ridge lip. This longer lower-shelf route approaches west of the lip, descends
# onto broad terrain, crosses east, and climbs gradually back to direct 312.
NORTHERN_RIDGE_POINTS = (
    Point(1, -6224.7402, -2291.2185, 142.0094),
    Point(1, -6225.7549, -2294.0417, 142.2566),
    Point(1, -6226.7695, -2296.8650, 141.8102),
    Point(1, -6227.7842, -2299.6882, 140.1807),
    Point(1, -6228.7988, -2302.5115, 136.5739),
    Point(1, -6229.3335, -2304.0000, 134.3834),
    Point(1, -6229.3335, -2307.0000, 131.8521),
    Point(1, -6229.3335, -2310.0000, 129.3209),
    Point(1, -6228.4829, -2312.8770, 127.4413),
    Point(1, -6227.6323, -2315.7539, 124.0089),
    Point(1, -6226.7817, -2318.6309, 120.9073),
    Point(1, -6225.9312, -2321.5078, 117.8889),
    Point(1, -6225.0806, -2324.3848, 114.4282),
    Point(1, -6224.8003, -2325.3333, 113.3834),
    Point(1, -6222.7788, -2327.5500, 113.1883),
    Point(1, -6220.7573, -2329.7668, 112.9932),
    Point(1, -6218.7363, -2331.9836, 112.7983),
    Point(1, -6216.7148, -2334.2004, 112.0390),
    Point(1, -6216.2666, -2336.8000, 110.3834),
    Point(1, -6216.2666, -2339.8000, 107.6333),
    Point(1, -6216.2666, -2340.8000, 106.8834),
    Point(1, -6216.8281, -2343.7471, 105.6831),
    Point(1, -6217.3892, -2346.6941, 103.9701),
    Point(1, -6217.9507, -2349.6411, 102.1997),
    Point(1, -6218.3999, -2352.0000, 101.3834),
    Point(1, -6219.1895, -2354.8943, 102.2836),
    Point(1, -6219.9785, -2357.7886, 103.6341),
    Point(1, -6217.2676, -2356.5037, 95.8968),
    Point(1, -6214.5566, -2355.2188, 91.1645),
    Point(1, -6212.2666, -2354.1333, 88.3834),
    Point(1, -6209.2744, -2353.9197, 89.3852),
    Point(1, -6208.5332, -2353.8667, 89.6334),
    Point(1, -6205.5586, -2354.2546, 94.5724),
    Point(1, -6202.5840, -2354.6426, 98.2898),
    Point(1, -6199.6094, -2355.0305, 101.0398),
    Point(1, -6196.6348, -2355.4185, 103.0465),
    Point(1, -6193.6602, -2355.8066, 103.4183),
    Point(1, -6190.6855, -2356.1946, 102.8327),
    Point(1, -6190.1333, -2356.2666, 101.8834),
    Point(1, -6187.1348, -2356.3665, 103.7085),
    Point(1, -6184.1362, -2356.4663, 104.0003),
    Point(1, -6182.1333, -2356.5332, 103.8834),
    Point(1, -6180.8003, -2356.5332, 104.3834),
    Point(1, -6177.8501, -2355.9897, 107.3651),
    Point(1, -6174.8999, -2355.4463, 106.0035),
    Point(1, -6171.9497, -2354.9028, 104.3410),
    Point(1, -6170.6665, -2354.6665, 102.8834),
    Point(1, -6168.0459, -2353.2058, 101.7124),
    Point(1, -6165.4253, -2351.7451, 100.0414),
    Point(1, -6162.8047, -2350.2847, 99.3426),
    Point(1, -6160.1841, -2348.8240, 100.6532),
    Point(1, -6157.5635, -2347.3633, 101.1098),
    Point(1, -6154.9429, -2345.9026, 101.3035),
    Point(1, -6154.3999, -2345.5999, 101.3834),
    Point(1, -6155.0605, -2342.6736, 104.9396),
    Point(1, -6155.7212, -2339.7473, 110.5119),
    Point(1, -6156.3818, -2336.8210, 115.7431),
    Point(1, -6157.0430, -2333.8948, 119.5904),
    Point(1, -6157.7036, -2330.9685, 122.6773),
    Point(1, -6158.1333, -2329.0667, 124.1334),
    Point(1, -6159.8647, -2326.6167, 126.6666),
    Point(1, -6161.5962, -2324.1667, 128.6014),
    Point(1, -6163.3276, -2321.7168, 129.4352),
    Point(1, -6165.0591, -2319.2668, 129.9904),
    Point(1, -6166.7905, -2316.8169, 130.6159),
    Point(1, -6168.5220, -2314.3669, 131.8730),
    Point(1, -6170.2534, -2311.9170, 133.5742),
    Point(1, -6171.9849, -2309.4673, 136.0926),
    Point(1, -6173.7163, -2307.0176, 137.7106),
    Point(1, -6175.4478, -2304.5679, 138.1201),
    Point(1, -6177.1792, -2302.1182, 138.2551),
    Point(1, -6178.9106, -2299.6685, 138.1596),
    Point(1, -6180.6421, -2297.2188, 138.1730),
    Point(1, -6182.3735, -2294.7690, 137.7140),
    Point(1, -6184.1050, -2292.3193, 136.9100),
    Point(1, -6185.8364, -2289.8696, 135.5476),
    Point(1, -6187.5679, -2287.4199, 133.4513),
    Point(1, -6189.2993, -2284.9702, 131.4034),
    Point(1, -6191.0312, -2282.5205, 128.9093),
    Point(1, -6192.7627, -2280.0708, 126.6077),
    Point(1, -6194.0229, -2278.2881, 125.3706),
)

# The source corridor briefly switches to a false lower navmesh layer at
# direct 344--354. These pinned real-navmesh anchors stay on the supported
# z84--88 mesa surface and rejoin the source route at direct 355.
NORTHERN_MESA_BYPASS_POINTS = (
    Point(1, -5561.3149, -1818.1532, 85.3223),
    Point(1, -5559.8491, -1815.5358, 85.7416),
    Point(1, -5558.3833, -1812.9183, 86.1857),
    Point(1, -5556.9175, -1810.3009, 86.4120),
    Point(1, -5555.4512, -1807.6836, 86.6463),
    Point(1, -5549.5869, -1797.2141, 87.2760),
    Point(1, -5546.6665, -1792.0000, 87.7066),
    Point(1, -5541.6001, -1782.9333, 87.4566),
    Point(1, -5540.0469, -1780.3668, 86.4591),
    Point(1, -5538.4937, -1777.8003, 85.5238),
    Point(1, -5536.9404, -1775.2338, 86.4857),
    Point(1, -5535.3867, -1772.6674, 86.5890),
    Point(1, -5533.8335, -1770.1008, 86.6413),
    Point(1, -5532.2798, -1767.5344, 86.3178),
    Point(1, -5530.7266, -1764.9679, 85.6174),
    Point(1, -5529.3335, -1762.6667, 84.7066),
    Point(1, -5528.0601, -1759.9503, 84.4527),
    Point(1, -5526.7866, -1757.2339, 85.0537),
    Point(1, -5525.5137, -1754.5175, 87.2316),
    Point(1, -5525.3335, -1754.1333, 87.4566),
)

NORTHERN_DIRECT_ROUTE_PREFIX = (
    ("tanaris-movement-bootstrap", Point(1, -9200.0, -2545.0, 13.5)),
    *(
        (f"tanaris-northern-bypass-{index:02d}", point)
        for index, point in enumerate(NORTHERN_BYPASS_POINTS[:17], start=1)
    ),
    *(
        (f"tanaris-northern-safe-bridge-{index:02d}", point)
        for index, point in enumerate(NORTHERN_SAFE_BRIDGE_POINTS, start=1)
    ),
    *(
        (f"tanaris-northern-direct-{index:02d}", point)
        for index, point in enumerate(NORTHERN_DIRECT_POINTS[140:309], start=141)
    ),
    *(
        (f"tanaris-northern-ridge-{index:02d}", point)
        for index, point in enumerate(NORTHERN_RIDGE_POINTS, start=1)
    ),
    *(
        (f"tanaris-northern-direct-{index:02d}", point)
        for index, point in enumerate(NORTHERN_DIRECT_POINTS[311:336], start=312)
    ),
    *(
        (f"tanaris-northern-ledge-{index:02d}", point)
        for index, point in enumerate(NORTHERN_LEDGE_POINTS, start=1)
    ),
    *(
        (f"tanaris-northern-direct-{index:02d}", point)
        for index, point in enumerate(NORTHERN_DIRECT_POINTS[336:338], start=337)
    ),
    ("tanaris-northern-ledge-landing", NORTHERN_LEDGE_LANDING),
    *(
        (f"tanaris-northern-direct-{index:02d}", point)
        for index, point in enumerate(NORTHERN_DIRECT_POINTS[338:343], start=339)
    ),
    *(
        (f"tanaris-northern-mesa-bypass-{index:02d}", point)
        for index, point in enumerate(NORTHERN_MESA_BYPASS_POINTS, start=1)
    ),
    *(
        (f"tanaris-northern-direct-{index:02d}", point)
        for index, point in enumerate(NORTHERN_DIRECT_POINTS[354:], start=355)
    ),
    ("great-lift-lower-dock", GREAT_LIFT_LOWER_DOCK),
)

TRAVERSE_ROUTE_PREFIX = NORTHERN_DIRECT_ROUTE_PREFIX
ROAD_CONTROL_START_GUIDEPOINT = 1


def _observed_lift_at_lower_dock(frame):
    lifts = (
        obj
        for obj in frame.objects
        if obj.entry in GREAT_LIFT_ENTRIES
        and obj.distance <= GREAT_LIFT_VISIBLE_RANGE
        and abs(obj.location.z - GREAT_LIFT_LOWER_DOCK.z)
        <= GREAT_LIFT_DOCK_Z_SLACK
    )
    return min(lifts, key=lambda obj: obj.distance, default=None)


def _steer_toward(
    bridge,
    frame,
    target: Point,
    *,
    purpose: str,
    precise_arrival: bool = False,
    translation_seconds: float = TRAVERSE_INPUT_SECONDS,
    jump_when_moving: bool = False,
    jump_while_turning: bool = False,
    jump_strafe: bool = True,
    strafe_deadband: float = math.pi / 8,
    trace=None,
) -> str | None:
    delta = _heading_delta(frame, target)
    if abs(delta) > math.pi / 4:
        return bridge.select_move_vector(
            frame,
            forward=0.0,
            turn=1.0 if delta > 0 else -1.0,
            jump=jump_when_moving and jump_while_turning,
            duration=0.25,
            purpose=purpose,
        )
    duration = ROAD_PRECISE_INPUT_SECONDS if precise_arrival else translation_seconds
    if trace is not None and duration in (
        ROAD_OPEN_INPUT_SECONDS,
        ROAD_CLEAR_INPUT_SECONDS,
    ):
        trace(
            "traverse_road_open_stride",
            activation=1,
            duration_seconds=duration,
        )
    return bridge.select_move_vector(
        frame,
        forward=1.0,
        strafe=(
            (1.0 if delta > 0 else -1.0)
            if (not jump_when_moving or jump_strafe) and abs(delta) > strafe_deadband
            else 0.0
        ),
        jump=jump_when_moving,
        duration=duration,
        purpose=purpose,
    )


def _heading_delta(frame, target: Point) -> float:
    desired = math.atan2(target.y - frame.location.y, target.x - frame.location.x)
    return (desired - frame.location.orientation + math.pi) % (2 * math.pi) - math.pi


def _point_segment_distance(
    point_x: float,
    point_y: float,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
) -> float:
    segment_x = end_x - start_x
    segment_y = end_y - start_y
    segment_length_squared = segment_x * segment_x + segment_y * segment_y
    if segment_length_squared == 0:
        return math.hypot(point_x - start_x, point_y - start_y)
    progress = max(
        0.0,
        min(
            1.0,
            (
                (point_x - start_x) * segment_x
                + (point_y - start_y) * segment_y
            )
            / segment_length_squared,
        ),
    )
    return math.hypot(
        point_x - (start_x + progress * segment_x),
        point_y - (start_y + progress * segment_y),
    )


def _unit_path(unit) -> tuple[float, float, float, float]:
    if (
        unit.movement_destination_known
        and unit.movement_destination.map_id == unit.location.map_id
    ):
        return (
            unit.location.x,
            unit.location.y,
            unit.movement_destination.x,
            unit.movement_destination.y,
        )
    return unit.location.x, unit.location.y, unit.location.x, unit.location.y


def _unit_path_horizon(unit, seconds: float) -> tuple[float, float, float, float]:
    start_x, start_y, end_x, end_y = _unit_path(unit)
    if unit.movement_remaining_seconds <= 0:
        return start_x, start_y, start_x, start_y
    progress = min(1.0, seconds / unit.movement_remaining_seconds)
    return (
        start_x,
        start_y,
        start_x + (end_x - start_x) * progress,
        start_y + (end_y - start_y) * progress,
    )


def _unit_alive(unit) -> bool:
    return not unit.is_dead and (not unit.health_known or unit.health > 1)


def _hazard_clearance_yards(frame, unit) -> float:
    if any(
        spell_id in frame.active_aura_spell_ids for spell_id in PROWL_SPELL_IDS
    ):
        # VMaNGOS floors creature stealth detection at 1.5 yards. This level-60
        # route template has more stealth skill than the ordinary route mobs
        # have detection skill, so retain one extra yard of collision margin.
        return ROAD_PROWL_CLEARANCE_YARDS
    if frame.level <= 0 or unit.level <= 0:
        return ROAD_HAZARD_UNKNOWN_CLEARANCE_YARDS
    # VMaNGOS starts ordinary equal-level aggro near 18 yards, subtracts one
    # yard per player level advantage, and floors the result at five yards.
    aggro_radius = max(
        ROAD_HAZARD_MIN_AGGRO_YARDS,
        ROAD_HAZARD_BASE_AGGRO_YARDS - (frame.level - unit.level),
    )
    return aggro_radius + ROAD_HAZARD_CLEARANCE_SLACK_YARDS


def _segment_clearance(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    unit,
) -> float:
    unit_start_x, unit_start_y, unit_end_x, unit_end_y = _unit_path(unit)
    route_x = end_x - start_x
    route_y = end_y - start_y
    unit_x = unit_end_x - unit_start_x
    unit_y = unit_end_y - unit_start_y
    cross = route_x * unit_y - route_y * unit_x
    if cross != 0:
        offset_x = unit_start_x - start_x
        offset_y = unit_start_y - start_y
        route_progress = (offset_x * unit_y - offset_y * unit_x) / cross
        unit_progress = (offset_x * route_y - offset_y * route_x) / cross
        if 0.0 <= route_progress <= 1.0 and 0.0 <= unit_progress <= 1.0:
            return 0.0
    return min(
        _point_segment_distance(
            unit_start_x, unit_start_y, start_x, start_y, end_x, end_y
        ),
        _point_segment_distance(
            unit_end_x, unit_end_y, start_x, start_y, end_x, end_y
        ),
        _point_segment_distance(
            start_x, start_y, unit_start_x, unit_start_y, unit_end_x, unit_end_y
        ),
        _point_segment_distance(
            end_x, end_y, unit_start_x, unit_start_y, unit_end_x, unit_end_y
        ),
    )


def _hazard_avoidance_target(
    frame,
    target: Point,
    *,
    side: float | None,
    active_holding_guids: set[str],
    hold_terrain_hazards: bool = False,
):
    route_x = target.x - frame.location.x
    route_y = target.y - frame.location.y
    route_length = math.hypot(route_x, route_y)
    if route_length == 0:
        return target, None, [], [], {}, {}, False
    route_x /= route_length
    route_y /= route_length
    left_x, left_y = -route_y, route_x
    detection_radius = (
        ROAD_HAZARD_EXIT_YARDS if side is not None else ROAD_HAZARD_ENTER_YARDS
    )
    tracked = [
        unit
        for unit in frame.units
        if unit.player_reaction_hostile
        and _unit_alive(unit)
        and unit.distance <= ROAD_HAZARD_TRACK_YARDS
    ]
    required_clearance = max(
        (_hazard_clearance_yards(frame, unit) for unit in tracked),
        default=ROAD_HAZARD_MIN_AGGRO_YARDS
        + ROAD_HAZARD_CLEARANCE_SLACK_YARDS,
    )
    safe_active_holding_guids = {
        unit.guid
        for unit in tracked
        if unit.guid in active_holding_guids
        and unit.distance >= required_clearance
        and unit.movement_destination_known
        and _point_segment_distance(
            frame.location.x,
            frame.location.y,
            *_unit_path(unit),
        )
        >= required_clearance
    }
    immediate_end_x = frame.location.x + route_x * detection_radius
    immediate_end_y = frame.location.y + route_y * detection_radius
    immediate_hazards = [
        unit
        for unit in tracked
        if unit.guid not in safe_active_holding_guids
        and _segment_clearance(
            frame.location.x,
            frame.location.y,
            immediate_end_x,
            immediate_end_y,
            unit,
        )
        <= ROAD_HAZARD_CORRIDOR_YARDS
    ]
    lookahead_end_x = frame.location.x + route_x * ROAD_HAZARD_LOOKAHEAD_YARDS
    lookahead_end_y = frame.location.y + route_y * ROAD_HAZARD_LOOKAHEAD_YARDS
    lookahead_hazards = [
        unit
        for unit in tracked
        if _segment_clearance(
            frame.location.x,
            frame.location.y,
            lookahead_end_x,
            lookahead_end_y,
            unit,
        )
        <= ROAD_HAZARD_CORRIDOR_YARDS
    ]
    immediate_guids = {unit.guid for unit in immediate_hazards}
    threatening_crossings = [
        unit
        for unit in lookahead_hazards
        if unit.guid not in immediate_guids
        and unit.movement_destination_known
        and _point_segment_distance(
            frame.location.x,
            frame.location.y,
            *_unit_path(unit),
        )
        < required_clearance
    ]
    resident_hazards = [
        unit
        for unit in lookahead_hazards
        if unit.movement_destination_known
        and math.dist(
            (unit.movement_destination.x, unit.movement_destination.y),
            (target.x, target.y),
        )
        <= ROAD_HAZARD_RESIDENT_RADIUS_YARDS
    ]
    terrain_hazards_by_guid = {
        unit.guid: unit
        for unit in (*immediate_hazards, *resident_hazards)
        if unit.distance <= required_clearance
    }
    if hold_terrain_hazards and terrain_hazards_by_guid:
        return (
            target,
            None,
            list(terrain_hazards_by_guid.values()),
            tracked,
            {},
            {},
            True,
        )
    if threatening_crossings and not immediate_hazards and not resident_hazards:
        return (
            target,
            None,
            threatening_crossings,
            tracked,
            {},
            {},
            True,
        )
    hazards_by_guid = (
        {} if hold_terrain_hazards else {unit.guid: unit for unit in immediate_hazards}
    )
    if not hold_terrain_hazards:
        hazards_by_guid.update((unit.guid, unit) for unit in resident_hazards)
    hazards = list(hazards_by_guid.values())
    if not hazards:
        return target, None, [], tracked, {}, {}, False

    def clearance(candidate_side: float, lateral_yards: float) -> float:
        candidate_x = (
            frame.location.x
            + route_x * ROAD_HAZARD_FORWARD_YARDS
            + left_x * candidate_side * lateral_yards
        )
        candidate_y = (
            frame.location.y
            + route_y * ROAD_HAZARD_FORWARD_YARDS
            + left_y * candidate_side * lateral_yards
        )
        return min(
            _segment_clearance(
                frame.location.x,
                frame.location.y,
                candidate_x,
                candidate_y,
                unit,
            )
            for unit in tracked
        )

    candidate_clearances = {
        side: {
            lateral_yards: clearance(side, lateral_yards)
            for lateral_yards in ROAD_HAZARD_LATERAL_YARDS
        }
        for side in (-1.0, 1.0)
    }

    def choose_lateral(candidate_side: float) -> float:
        safe = [
            lateral_yards
            for lateral_yards, candidate_clearance in candidate_clearances[
                candidate_side
            ].items()
            if candidate_clearance >= required_clearance
        ]
        if safe:
            return min(safe)
        return max(
            ROAD_HAZARD_LATERAL_YARDS,
            key=lambda lateral_yards: (
                candidate_clearances[candidate_side][lateral_yards],
                -lateral_yards,
            ),
        )

    lateral_by_side = {
        candidate_side: choose_lateral(candidate_side)
        for candidate_side in (-1.0, 1.0)
    }
    clearances = {
        candidate_side: candidate_clearances[candidate_side][
            lateral_by_side[candidate_side]
        ]
        for candidate_side in (-1.0, 1.0)
    }
    best_side = max((-1.0, 1.0), key=clearances.get)
    if side is None:
        side = best_side
    else:
        other_side = -side
        if (
            clearances[side] < required_clearance
            and clearances[other_side]
            >= clearances[side] + ROAD_HAZARD_SWITCH_MARGIN_YARDS
        ):
            side = other_side

    return (
        Point(
            frame.location.map_id,
            frame.location.x
            + route_x * ROAD_HAZARD_FORWARD_YARDS
            + left_x * side * lateral_by_side[side],
            frame.location.y
            + route_y * ROAD_HAZARD_FORWARD_YARDS
            + left_y * side * lateral_by_side[side],
            frame.location.z,
        ),
        side,
        hazards,
        tracked,
        clearances,
        lateral_by_side,
        False,
    )


def _combat_escape_target(frame, target: Point) -> Point:
    attackers = [
        unit
        for unit in frame.units
        if unit.player_reaction_hostile
        and _unit_alive(unit)
        and unit.target_guid_known
        and unit.target_guid == frame.player_guid
    ]
    if not attackers:
        return target
    away_x = sum(frame.location.x - unit.location.x for unit in attackers)
    away_y = sum(frame.location.y - unit.location.y for unit in attackers)
    away_length = math.hypot(away_x, away_y)
    if away_length == 0:
        return target
    return Point(
        frame.location.map_id,
        frame.location.x + away_x / away_length * ROAD_HAZARD_EXIT_YARDS,
        frame.location.y + away_y / away_length * ROAD_HAZARD_EXIT_YARDS,
        frame.location.z,
    )


def _hazard_evasion_target(frame, hazards, target: Point) -> Point:
    if not hazards:
        return target
    away_x = sum(
        (frame.location.x - unit.location.x) / max(1.0, unit.distance)
        for unit in hazards
    )
    away_y = sum(
        (frame.location.y - unit.location.y) / max(1.0, unit.distance)
        for unit in hazards
    )
    away_length = math.hypot(away_x, away_y)
    if away_length == 0:
        return target
    return Point(
        frame.location.map_id,
        frame.location.x + away_x / away_length * ROAD_HAZARD_EXIT_YARDS,
        frame.location.y + away_y / away_length * ROAD_HAZARD_EXIT_YARDS,
        frame.location.z,
    )


def _visible_attackers(frame):
    return [
        unit
        for unit in frame.units
        if unit.player_reaction_hostile
        and _unit_alive(unit)
        and unit.target_guid_known
        and unit.target_guid == frame.player_guid
    ]


def _qualifying_ramp_scorpid(unit) -> bool:
    return (
        unit.player_reaction_hostile
        and _unit_alive(unit)
        and unit.entry == RAMP_SCORPID_ENTRY
        and unit.level_known
        and unit.level <= 41
        and (not unit.creature_rank_known or unit.creature_rank == 0)
    )


def _qualifying_reactive_attacker(unit) -> bool:
    return (
        unit.player_reaction_hostile
        and _unit_alive(unit)
        and unit.level_known
        and unit.level <= 49
        and (not unit.creature_rank_known or unit.creature_rank == 0)
    )


def _traverse_fight_attacker(
    frame,
    *,
    active_guid: str | None,
    allow_proactive: bool,
    proactive_clearance_guids: set[str],
):
    if active_guid is not None:
        attacker = next(
            (
                unit
                for unit in frame.units
                if unit.guid == active_guid and _unit_alive(unit)
            ),
            None,
        )
        if attacker is None:
            return None
        if frame.in_combat:
            attackers = _visible_attackers(frame)
            if frame.threat.attacker_count != 1 or len(attackers) != 1:
                return None
            return attacker if attackers[0].guid == active_guid else None
        return attacker

    if frame.in_combat:
        attackers = _visible_attackers(frame)
        if frame.threat.attacker_count != 1 or len(attackers) != 1:
            return None
        attacker = attackers[0]
        if not _qualifying_reactive_attacker(attacker):
            return None
        if frame.threat.elite_attacker_known and frame.threat.elite_attacker_present:
            return None
        return attacker

    if not allow_proactive:
        return None

    nearby_hazards = [
        unit
        for unit in frame.units
        if unit.player_reaction_hostile
        and _unit_alive(unit)
        and unit.distance <= ROAD_HAZARD_ENTER_YARDS
    ]
    if proactive_clearance_guids:
        if (
            frame.max_health <= 0
            or frame.health < frame.max_health * POST_FIGHT_HEAL_FRACTION
        ):
            return None
        candidates = [
            unit
            for unit in nearby_hazards
            if unit.guid in proactive_clearance_guids
            and _qualifying_reactive_attacker(unit)
        ]
    else:
        candidates = [
            unit
            for unit in nearby_hazards
            if unit.distance <= ROAD_TIGHT_HAZARD_HOLD_YARDS
            and _qualifying_ramp_scorpid(unit)
        ]
    if len(candidates) != 1:
        return None
    attacker = candidates[0]
    likely_add = any(
        unit.guid != attacker.guid
        and _point_segment_distance(
            attacker.location.x,
            attacker.location.y,
            *_unit_path_horizon(unit, CLEARANCE_FIGHT_ADD_HORIZON_SECONDS),
        )
        < RAMP_FIGHT_ADD_CLEARANCE_YARDS
        for unit in nearby_hazards
    )
    return None if likely_add else attacker


def _cast_combat_spell(
    bridge,
    frame,
    spell_ids,
    *,
    purpose: str,
    trace,
    target_guid: str | None = None,
    failed_spell_ids: set[int] | None = None,
    trace_kind: str = "traverse_combat_feral_spell",
) -> bool:
    spell_id = next(
        (
            spell_id
            for spell_id in spell_ids
            if spell_id in frame.known_spells
            and (failed_spell_ids is None or spell_id not in failed_spell_ids)
        ),
        None,
    )
    if spell_id is None:
        return False
    request_id = (
        bridge.select_cast_target(frame, spell_id, target_guid)
        if target_guid is not None
        else bridge.select_cast_without_target(frame, spell_id, purpose=purpose)
    )
    if request_id is None:
        return False
    outcome = bridge.wait_for_settlement(frame.frame_id)
    trace(
        trace_kind,
        activation=1,
        spell_id=spell_id,
        purpose=purpose,
        combo_points_before=(
            frame.combo_points if frame.combo_points_known else None
        ),
        active_power_before=(
            frame.active_power if frame.active_power_known else None
        ),
        success=outcome is not None and outcome.success,
        detail=outcome.detail if outcome is not None else "unsettled",
    )
    if failed_spell_ids is not None:
        if outcome is not None and outcome.success:
            failed_spell_ids.difference_update(spell_ids)
        else:
            failed_spell_ids.update(spell_ids)
    return True


@dataclass
class TraverseCombatState:
    failed_feral_spell_ids: set[int] = field(default_factory=set)
    failed_ranged_spell_ids: set[int] = field(default_factory=set)
    melee_refaces: int = 0
    ranged_fallback: bool = False


def _fight_traverse_attacker(
    bridge,
    navigator,
    frame,
    attacker,
    trace,
    combat: TraverseCombatState,
) -> bool:
    if combat.ranged_fallback:
        if frame.active_cast_spell_id:
            request_id = bridge.select_wait(frame)
            if request_id is None:
                return False
            trace(
                "traverse_combat_ranged_fallback",
                activation=1,
                phase="finish_active_cast",
                spell_id=frame.active_cast_spell_id,
            )
            return True
        if frame.shapeshift_form_known and frame.shapeshift_form_id != 0:
            if not frame.shapeshift_form_spell_known:
                return False
            spell_id = frame.shapeshift_form_spell_id
            request_id = bridge.select_cancel_aura(frame, spell_id)
            if request_id is None:
                return False
            outcome = bridge.wait_for_settlement(frame.frame_id)
            trace(
                "traverse_combat_ranged_fallback",
                activation=1,
                phase="exit_current_form",
                spell_id=spell_id,
                success=outcome is not None and outcome.success,
                detail=outcome.detail if outcome is not None else "unsettled",
            )
            return True
        moonfire_unavailable = all(
            spell_id not in frame.known_spells
            or spell_id in combat.failed_ranged_spell_ids
            for spell_id in MOONFIRE_SPELL_IDS
        )
        ranged_spell_ids = (
            WRATH_SPELL_IDS
            if moonfire_unavailable
            or set(attacker.active_aura_spell_ids).intersection(MOONFIRE_SPELL_IDS)
            else MOONFIRE_SPELL_IDS
        )
        return _cast_combat_spell(
            bridge,
            frame,
            ranged_spell_ids,
            purpose="damage the traverse attacker after repeated melee failure",
            trace=trace,
            target_guid=attacker.guid,
            failed_spell_ids=combat.failed_ranged_spell_ids,
            trace_kind="traverse_combat_ranged_spell",
        )

    if frame.shapeshift_form_known and frame.shapeshift_form_id not in (0, 1):
        if not frame.shapeshift_form_spell_known:
            return False
        spell_id = frame.shapeshift_form_spell_id
        request_id = bridge.select_cancel_aura(frame, spell_id)
        if request_id is None:
            return False
        outcome = bridge.wait_for_settlement(frame.frame_id)
        trace(
            "traverse_combat_form_exit",
            activation=1,
            spell_id=spell_id,
            success=outcome is not None and outcome.success,
            detail=outcome.detail if outcome is not None else "unsettled",
        )
        return True
    if not frame.shapeshift_form_known or frame.shapeshift_form_id != 1:
        return _cast_combat_spell(
            bridge,
            frame,
            (CAT_FORM_SPELL_ID,),
            purpose="enter Cat Form for traverse combat",
            trace=trace,
        )
    if (
        attacker.combat_distance_known
        and attacker.combat_distance > FERAL_MELEE_CLOSE_YARDS
    ):
        request_id = (
            _steer_toward(
                bridge,
                frame,
                attacker.location,
                purpose="close on the traverse attacker in combat",
                precise_arrival=True,
            )
            if frame.in_combat
            else bridge.select_move_to(
                frame,
                attacker.location.x,
                attacker.location.y,
                attacker.location.z,
                frame.location.map_id,
            )
        )
        if request_id is None:
            return False
        trace(
            "traverse_combat_fight_closing",
            activation=1,
            distance=round(attacker.combat_distance, 3),
            proactive=not frame.in_combat,
        )
        return True
    if frame.auto_attack_guid != attacker.guid:
        if not frame.in_combat:
            request_id = bridge.select_target_action(frame, "attack", attacker.guid)
            if request_id is None:
                return False
            outcome = bridge.wait_for_settlement(frame.frame_id)
            trace(
                "traverse_combat_fight_attack",
                activation=1,
                success=outcome is not None and outcome.success,
                detail=outcome.detail if outcome is not None else "unsettled",
            )
            return True
        return navigator._engage_exact_attacker(bridge, frame)

    active_auras = set(attacker.active_aura_spell_ids)
    target_healthy = (
        not attacker.health_known
        or not attacker.max_health_known
        or attacker.max_health <= 0
        or attacker.health / attacker.max_health > 0.4
    )
    if (
        frame.combo_points_known
        and frame.combo_points >= 3
        and target_healthy
        and not active_auras.intersection(FERAL_RIP_SPELL_IDS)
        and _cast_combat_spell(
            bridge,
            frame,
            FERAL_RIP_SPELL_IDS,
            purpose="finish the traverse attacker with Rip",
            trace=trace,
            target_guid=attacker.guid,
            failed_spell_ids=combat.failed_feral_spell_ids,
        )
    ):
        return True
    if (
        target_healthy
        and not active_auras.intersection(FERAL_RAKE_SPELL_IDS)
        and _cast_combat_spell(
            bridge,
            frame,
            FERAL_RAKE_SPELL_IDS,
            purpose="bleed the traverse attacker with Rake",
            trace=trace,
            target_guid=attacker.guid,
            failed_spell_ids=combat.failed_feral_spell_ids,
        )
    ):
        return True
    if _cast_combat_spell(
        bridge,
        frame,
        FERAL_CLAW_SPELL_IDS,
        purpose="build on the traverse attacker with Claw",
        trace=trace,
        target_guid=attacker.guid,
        failed_spell_ids=combat.failed_feral_spell_ids,
    ):
        return True
    if combat.failed_feral_spell_ids:
        combat.failed_feral_spell_ids.clear()
        if combat.melee_refaces:
            combat.ranged_fallback = True
            trace(
                "traverse_combat_ranged_fallback",
                activation=1,
                phase="activated",
                target_guid=attacker.guid,
            )
            return _fight_traverse_attacker(
                bridge,
                navigator,
                frame,
                attacker,
                trace,
                combat,
            )
        navigator._faced_attacker_guid = None
        combat.melee_refaces += 1
        trace(
            "traverse_combat_fight_reface",
            activation=1,
            target_guid=attacker.guid,
        )
    return navigator._engage_exact_attacker(bridge, frame)


@dataclass
class HazardAvoidanceState:
    side: float | None = None
    holding: bool = False
    holding_started: float | None = None
    holding_guids: set[str] = field(default_factory=set)
    evading: bool = False
    settled_pulses: int = 0


def _steer_road_leg(
    bridge,
    navigator: RouteNavigator,
    target: Point,
    *,
    deadline: float,
    trace,
    avoidance: HazardAvoidanceState,
    allow_northing_pass: bool,
    pass_lateral_yards: float,
    arrival_radius: float,
    hold_terrain_hazards: bool,
    jump_terrain: bool,
    jump_once: bool,
    straight_jump_pulses: int,
    bounded_jump_floor_z: float | None,
    downstream_route: bool,
    stealth_route: bool,
    landing_then_clear: bool = False,
    tight_lateral_control: bool = False,
):
    closest = math.inf
    last_progress = time.monotonic()
    road_unstick_attempts = 0
    combat_escape_started: float | None = None
    fight_guid: str | None = None
    fight_started: float | None = None
    post_fight_healing = False
    combat = TraverseCombatState()
    single_jump_used = False
    travel_form_attempted = False
    travel_form_fallback_traced = False
    straight_jumps_used = 0
    while time.monotonic() < deadline and not getattr(bridge, "finished", False):
        frame = bridge.observe()
        if frame is None:
            return None, "no_frame"
        if frame.is_dead or frame.is_ghost:
            return None, "death"
        prowl_active = any(
            spell_id in frame.active_aura_spell_ids for spell_id in PROWL_SPELL_IDS
        )
        travel_form_active = (
            frame.shapeshift_form_known
            and frame.shapeshift_form_spell_known
            and frame.shapeshift_form_spell_id == TRAVEL_FORM_SPELL_ID
        )
        if post_fight_healing and not frame.in_combat:
            if _activate_rejuvenation(
                bridge,
                trace,
                trace_kind="traverse_post_fight_rejuvenation",
                purpose="restore health after Traverse combat",
            ):
                post_fight_healing = False
            last_progress = time.monotonic()
            continue
        if downstream_route and not frame.in_combat:
            if stealth_route and not prowl_active:
                _activate_prowl(bridge, trace)
                last_progress = time.monotonic()
                continue
            if (
                not stealth_route
                and not travel_form_active
                and not travel_form_attempted
            ):
                travel_form_attempted = True
                _activate_travel_form(bridge, trace)
                last_progress = time.monotonic()
                continue
            if (
                not stealth_route
                and not travel_form_active
                and not travel_form_fallback_traced
            ):
                trace(
                    "traverse_travel_form_unavailable",
                    activation=1,
                    reason="form_did_not_persist",
                )
                travel_form_fallback_traced = True
        fight_attacker = _traverse_fight_attacker(
            frame,
            active_guid=fight_guid,
            allow_proactive=True,
            proactive_clearance_guids=(
                avoidance.holding_guids
                if avoidance.holding_started is not None
                and time.monotonic() - avoidance.holding_started
                >= ROAD_HAZARD_CLEARANCE_FIGHT_DELAY_SECONDS
                else set()
            ),
        )
        if fight_attacker is not None:
            if fight_started is None:
                fight_started = time.monotonic()
                fight_guid = fight_attacker.guid
                combat = TraverseCombatState()
                trace(
                    "traverse_combat_fight",
                    activation=1,
                    health=frame.health,
                    max_health=frame.max_health,
                    attacker_count=frame.threat.attacker_count,
                    proactive=not frame.in_combat,
                    player_level=frame.level,
                    attacker={
                        "entry": fight_attacker.entry,
                        "name": fight_attacker.name,
                        "level": fight_attacker.level,
                        "health": (
                            fight_attacker.health
                            if fight_attacker.health_known
                            else None
                        ),
                        "max_health": (
                            fight_attacker.max_health
                            if fight_attacker.max_health_known
                            else None
                        ),
                        "distance": round(fight_attacker.distance, 3),
                    },
                )
            last_progress = time.monotonic()
            if _fight_traverse_attacker(
                bridge,
                navigator,
                frame,
                fight_attacker,
                trace,
                combat,
            ):
                continue
        elif fight_started is not None:
            trace(
                "traverse_combat_fight_ended",
                activation=1,
                reason="combat_ended" if not frame.in_combat else "gate_lost",
                duration_seconds=round(time.monotonic() - fight_started, 3),
                health=frame.health,
                max_health=frame.max_health,
                damage_done=frame.combat_damage_done_total,
                damage_taken=frame.combat_damage_taken_total,
            )
            fight_started = None
            fight_guid = None
            combat = TraverseCombatState()
            if (
                frame.max_health > 0
                and frame.health < frame.max_health * POST_FIGHT_HEAL_FRACTION
            ):
                post_fight_healing = True
                continue

        if frame.in_combat:
            if combat_escape_started is None:
                combat_escape_started = time.monotonic()
                visible_attackers = [
                    {
                        "entry": unit.entry,
                        "name": unit.name,
                        "distance": round(unit.distance, 3),
                    }
                    for unit in frame.units
                    if unit.player_reaction_hostile
                    and _unit_alive(unit)
                    and unit.target_guid_known
                    and unit.target_guid == frame.player_guid
                ]
                trace(
                    "traverse_combat_escape",
                    activation=1,
                    health=frame.health,
                    max_health=frame.max_health,
                    attacker_count=frame.threat.attacker_count,
                    visible_attackers=visible_attackers,
                )
        elif combat_escape_started is not None:
            trace(
                "traverse_combat_escape_ended",
                activation=1,
                duration_seconds=round(time.monotonic() - combat_escape_started, 3),
                health=frame.health,
                max_health=frame.max_health,
            )
            combat_escape_started = None

        distance = math.dist(
            (frame.location.x, frame.location.y, frame.location.z),
            (target.x, target.y, target.z),
        )
        if distance <= arrival_radius:
            return Point(
                frame.location.map_id,
                frame.location.x,
                frame.location.y,
                frame.location.z,
            ), ""
        lateral_distance = abs(frame.location.y - target.y)
        vertical_distance = abs(frame.location.z - target.z)
        if (
            allow_northing_pass
            and frame.location.x >= target.x - ROAD_PASS_NORTHING_SLACK_YARDS
            and lateral_distance <= pass_lateral_yards
            and vertical_distance <= ROAD_PASS_VERTICAL_YARDS
        ):
            trace(
                "traverse_road_guidepoint_passed",
                activation=1,
                distance=round(distance, 3),
                lateral_distance=round(lateral_distance, 3),
                vertical_distance=round(vertical_distance, 3),
            )
            return Point(
                frame.location.map_id,
                frame.location.x,
                frame.location.y,
                frame.location.z,
            ), ""
        planar_distance = math.dist(
            (frame.location.x, frame.location.y),
            (target.x, target.y),
        )
        if (
            jump_terrain
            and not allow_northing_pass
            and frame.location.z
            >= target.z - ROAD_CLIMB_EDGE_PASS_VERTICAL_SLACK_YARDS
            and planar_distance <= ROAD_CLIMB_EDGE_PASS_PLANAR_YARDS
        ):
            trace(
                "traverse_road_climb_edge_passed",
                activation=1,
                distance=round(distance, 3),
                planar_distance=round(planar_distance, 3),
                vertical_distance=round(vertical_distance, 3),
            )
            return Point(
                frame.location.map_id,
                frame.location.x,
                frame.location.y,
                frame.location.z,
            ), ""
        if (
            bounded_jump_floor_z is not None
            and frame.location.z >= target.z
            and planar_distance <= arrival_radius
        ):
            trace(
                "traverse_road_bounded_edge_passed",
                activation=1,
                distance=round(distance, 3),
                planar_distance=round(planar_distance, 3),
                vertical_distance=round(vertical_distance, 3),
            )
            return Point(
                frame.location.map_id,
                frame.location.x,
                frame.location.y,
                frame.location.z,
            ), ""
        if (
            jump_once
            and single_jump_used
            and frame.location.x >= target.x
            and lateral_distance <= ROAD_JUMP_EDGE_PASS_LATERAL_YARDS
            and vertical_distance <= ROAD_JUMP_EDGE_PASS_VERTICAL_YARDS
        ):
            trace(
                "traverse_road_jump_edge_passed",
                activation=1,
                distance=round(distance, 3),
                lateral_distance=round(lateral_distance, 3),
                vertical_distance=round(vertical_distance, 3),
            )
            return Point(
                frame.location.map_id,
                frame.location.x,
                frame.location.y,
                frame.location.z,
            ), ""
        if distance < closest - 1.0:
            closest = distance
            last_progress = time.monotonic()
            road_unstick_attempts = 0
        elif time.monotonic() - last_progress >= ROAD_STALL_SECONDS:
            if road_unstick_attempts >= ROAD_UNSTICK_ATTEMPTS:
                trace(
                    "traverse_road_stalled",
                    activation=1,
                    distance=round(distance, 3),
                    recovery_exhausted=True,
                )
                return None, "no_progress"
            side = 1.0 if road_unstick_attempts == 0 else -1.0
            trace(
                "traverse_road_unstick",
                activation=1,
                attempt=road_unstick_attempts + 1,
                side="left" if side > 0 else "right",
                distance=round(distance, 3),
            )
            bridge.select_move_vector(
                frame,
                forward=1.0,
                strafe=side,
                duration=TRAVERSE_INPUT_SECONDS,
                purpose="sidestep a blocked Traverse road translation",
            )
            settle_frame = bridge.observe()
            if settle_frame is None:
                return None, "no_frame"
            movement = math.dist(
                (frame.location.x, frame.location.y),
                (settle_frame.location.x, settle_frame.location.y),
            )
            road_unstick_attempts += 1
            trace(
                "traverse_road_unstick_settled",
                activation=1,
                attempt=road_unstick_attempts,
                movement=round(movement, 3),
            )
            if movement >= 0.5:
                closest = math.inf
                last_progress = time.monotonic()
                road_unstick_attempts = 0
            avoidance.settled_pulses += 1
            trace("traverse_road_pulse_settled", frame_id=settle_frame.frame_id)
            continue

        if frame.in_combat:
            steering_target = _combat_escape_target(frame, target)
            next_avoidance_side = avoidance.side
            hazards = []
            tracked_hazards = []
            should_hold = False
        else:
            (
                steering_target,
                next_avoidance_side,
                hazards,
                tracked_hazards,
                side_clearances,
                side_lateral_yards,
                should_hold,
            ) = _hazard_avoidance_target(
                frame,
                target,
                side=avoidance.side,
                active_holding_guids=avoidance.holding_guids,
                hold_terrain_hazards=hold_terrain_hazards,
            )
        if should_hold:
            if not avoidance.holding:
                avoidance.holding_started = time.monotonic()
                trace(
                    "traverse_hazard_hold",
                    activation=1,
                    reason=(
                        "terrain_constrained_hazard"
                        if hold_terrain_hazards
                        else "projected_crossing"
                    ),
                    hazards=[
                        {
                            "entry": unit.entry,
                            "name": unit.name,
                            "distance": round(unit.distance, 3),
                            "destination": [
                                round(unit.movement_destination.x, 3),
                                round(unit.movement_destination.y, 3),
                            ],
                        }
                        for unit in hazards
                    ],
                )
            if avoidance.side is not None:
                trace("traverse_hazard_avoidance_ended", activation=1, reason="hold")
            if avoidance.evading:
                trace("traverse_hazard_evasion_ended", activation=1, reason="hold")
            avoidance.holding = True
            avoidance.holding_guids = {unit.guid for unit in hazards}
            avoidance.side = None
            avoidance.evading = False
            last_progress = time.monotonic()
            bridge.select_wait(frame)
            trace("traverse_hazard_hold_pulse", frame_id=frame.frame_id)
            continue
        if avoidance.holding:
            trace("traverse_hazard_hold_ended", activation=1)
            avoidance.holding = False
            avoidance.holding_started = None
            avoidance.holding_guids = set()
        if next_avoidance_side is not None and avoidance.side is None:
            trace(
                "traverse_hazard_avoidance",
                activation=1,
                side="left" if next_avoidance_side > 0 else "right",
                side_clearances={
                    "right": round(side_clearances[-1.0], 3),
                    "left": round(side_clearances[1.0], 3),
                },
                side_lateral_yards={
                    "right": side_lateral_yards[-1.0],
                    "left": side_lateral_yards[1.0],
                },
                hazards=[
                    {
                        "entry": unit.entry,
                        "name": unit.name,
                        "distance": round(unit.distance, 3),
                        "location": [
                            round(unit.location.x, 3),
                            round(unit.location.y, 3),
                            round(unit.location.z, 3),
                        ],
                    }
                    for unit in hazards
                ],
                tracked_hazards=[
                    {
                        "entry": unit.entry,
                        "name": unit.name,
                        "distance": round(unit.distance, 3),
                        "moving": unit.movement_known and unit.is_moving,
                        "movement_speed": round(unit.movement_speed, 3),
                        "movement_remaining_seconds": round(
                            unit.movement_remaining_seconds, 3
                        ),
                        "destination": (
                            [
                                round(unit.movement_destination.x, 3),
                                round(unit.movement_destination.y, 3),
                            ]
                            if unit.movement_destination_known
                            else None
                        ),
                    }
                    for unit in tracked_hazards
                ],
                resident_blocker_count=sum(
                    unit.movement_destination_known
                    and math.dist(
                        (
                            unit.movement_destination.x,
                            unit.movement_destination.y,
                        ),
                        (target.x, target.y),
                    )
                    <= ROAD_HAZARD_RESIDENT_RADIUS_YARDS
                    for unit in hazards
                ),
            )
        elif next_avoidance_side is None and avoidance.side is not None:
            trace("traverse_hazard_avoidance_ended", activation=1)
        elif (
            next_avoidance_side is not None
            and avoidance.side is not None
            and next_avoidance_side != avoidance.side
        ):
            trace(
                "traverse_hazard_avoidance_switched",
                activation=1,
                side="left" if next_avoidance_side > 0 else "right",
                side_clearances={
                    "right": round(side_clearances[-1.0], 3),
                    "left": round(side_clearances[1.0], 3),
                },
                side_lateral_yards={
                    "right": side_lateral_yards[-1.0],
                    "left": side_lateral_yards[1.0],
                },
            )
        avoidance.side = next_avoidance_side

        unsafe = (
            not frame.in_combat
            and avoidance.side is not None
            and side_clearances[avoidance.side]
            < max(
                (
                    _hazard_clearance_yards(frame, unit)
                    for unit in tracked_hazards
                ),
                default=ROAD_HAZARD_MIN_AGGRO_YARDS
                + ROAD_HAZARD_CLEARANCE_SLACK_YARDS,
            )
        )
        should_evade = unsafe
        if should_evade:
            if not avoidance.evading:
                trace(
                    "traverse_hazard_evasion",
                    activation=1,
                    side="left" if avoidance.side > 0 else "right",
                    clearance=round(side_clearances[avoidance.side], 3),
                )
                avoidance.evading = True
            last_progress = time.monotonic()
            steering_target = _hazard_evasion_target(frame, hazards, target)
        elif avoidance.evading:
            trace("traverse_hazard_evasion_ended", activation=1)
            avoidance.evading = False

        if frame.in_combat:
            steering_purpose = "flee directly away from current Traverse attackers"
        elif should_evade:
            steering_purpose = "move away from hazards at the Traverse holding point"
        elif hazards:
            steering_purpose = "steer around visible Traverse hazards"
        else:
            steering_purpose = (
                "steer the canonical Traverse road after movement bootstrap"
            )
        jump_when_moving = (
            jump_terrain
            or (
                straight_jumps_used < straight_jump_pulses
                and bounded_jump_floor_z is not None
                and frame.location.z <= bounded_jump_floor_z
            )
            or (
                jump_once
                and not single_jump_used
                and abs(_heading_delta(frame, steering_target)) <= math.pi / 4
            )
        ) and not frame.in_combat and (
            (not hazards and not should_evade)
            or (prowl_active and bounded_jump_floor_z is not None)
        )
        translating = abs(_heading_delta(frame, steering_target)) <= math.pi / 4
        landing_unsettled = (
            landing_then_clear
            and abs(frame.location.z - target.z) > 3.0
        )
        precise_road_input = (
            should_evade
            or distance <= ROAD_HAZARD_FORWARD_YARDS
            or landing_unsettled
            or (hold_terrain_hazards and not landing_then_clear)
        )
        request_id = _steer_toward(
            bridge,
            frame,
            steering_target,
            purpose=steering_purpose,
            precise_arrival=precise_road_input,
            translation_seconds=(
                (
                    ROAD_STEALTH_INPUT_SECONDS
                    if stealth_route
                    else ROAD_CLEAR_INPUT_SECONDS
                )
                if not frame.in_combat and not hazards
                else (
                    ROAD_OPEN_INPUT_SECONDS
                    if not frame.in_combat
                    else TRAVERSE_INPUT_SECONDS
                )
            ),
            jump_when_moving=jump_when_moving,
            jump_while_turning=bounded_jump_floor_z is not None,
            jump_strafe=(
                straight_jump_pulses == 0
                or (
                    straight_jump_pulses > 0
                    and straight_jumps_used >= straight_jump_pulses
                )
            ),
            strafe_deadband=(math.pi / 90 if tight_lateral_control else math.pi / 8),
            trace=trace,
        )
        if (
            request_id is not None
            and jump_when_moving
            and translating
        ):
            straight_jumps_used += 1
        if request_id is not None and jump_when_moving and jump_once:
            single_jump_used = True
        settle_frame = bridge.observe()
        if settle_frame is None:
            return None, "no_frame"
        movement = math.dist(
            (frame.location.x, frame.location.y),
            (settle_frame.location.x, settle_frame.location.y),
        )
        if (
            downstream_route
            and request_id is not None
            and translating
            and not precise_road_input
            and movement < ROAD_COLLISION_MOVEMENT_YARDS
        ):
            side = 1.0 if road_unstick_attempts % 2 == 0 else -1.0
            trace(
                "traverse_road_collision_unstick",
                activation=1,
                side="left" if side > 0 else "right",
                movement=round(movement, 3),
            )
            bridge.select_move_vector(
                settle_frame,
                forward=1.0,
                strafe=side,
                jump=True,
                duration=0.25,
                purpose="jump-sidestep a blocked stealth road translation",
            )
            unstick_frame = bridge.observe()
            if unstick_frame is None:
                return None, "no_frame"
            unstick_movement = math.dist(
                (settle_frame.location.x, settle_frame.location.y),
                (unstick_frame.location.x, unstick_frame.location.y),
            )
            road_unstick_attempts += 1
            last_progress = time.monotonic()
            trace(
                "traverse_road_collision_unstick_settled",
                activation=1,
                movement=round(unstick_movement, 3),
            )
            avoidance.settled_pulses += 1
            trace("traverse_road_pulse_settled", frame_id=unstick_frame.frame_id)
            continue
        avoidance.settled_pulses += 1
        trace("traverse_road_pulse_settled", frame_id=settle_frame.frame_id)
    return None, "deadline"


def _select_frontier(graph, *, best_world_x: float, visited: set[str]):
    candidates = [
        node
        for node in graph.nodes
        if node.key not in visited
        and node.distance_from_source >= MIN_FRONTIER_DISTANCE_YARDS
        and node.centroid.x >= best_world_x - MAX_BACKTRACK_YARDS
        and not node.semantic_flags & NAV_SEMANTIC_HAZARD
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda node: (node.centroid.x, node.distance_from_source))


def _activate_prowl(bridge, trace) -> None:
    frame = bridge.observe()
    if frame is None:
        trace("traverse_prowl", activation=0, reason="no_frame")
        return
    if frame.in_combat:
        trace("traverse_prowl", activation=0, reason="in_combat")
        return
    if any(spell_id in frame.active_aura_spell_ids for spell_id in PROWL_SPELL_IDS):
        trace("traverse_prowl", activation=0, reason="already_active")
        return

    if frame.shapeshift_form_known and frame.shapeshift_form_id not in (0, 1):
        if not frame.shapeshift_form_spell_known:
            trace("traverse_prowl", activation=0, reason="current_form_unknown")
            return
        spell_id = frame.shapeshift_form_spell_id
        request_id = bridge.select_cancel_aura(frame, spell_id)
        if request_id is None:
            trace("traverse_prowl", activation=0, reason="form_exit_unavailable")
            return
        outcome = bridge.wait_for_settlement(frame.frame_id)
        trace(
            "traverse_prowl_form_exit",
            activation=1,
            spell_id=spell_id,
            success=outcome is not None and outcome.success,
            detail=outcome.detail if outcome is not None else "unsettled",
        )
        frame = bridge.observe()
        if frame is None:
            trace("traverse_prowl", activation=0, reason="no_frame_after_form_exit")
            return

    if not frame.shapeshift_form_known or frame.shapeshift_form_id != 1:
        request_id = bridge.select_cast_without_target(
            frame,
            CAT_FORM_SPELL_ID,
            purpose="enter Cat Form for stealth Traverse",
        )
        if request_id is None:
            trace("traverse_cat_form", activation=0, reason="spell_unavailable")
            return
        outcome = bridge.wait_for_settlement(frame.frame_id)
        trace(
            "traverse_cat_form",
            activation=1,
            success=outcome is not None and outcome.success,
            detail=outcome.detail if outcome is not None else "unsettled",
        )
        frame = bridge.observe()
        for _ in range(4):
            if (
                frame is None
                or not frame.shapeshift_form_known
                or frame.shapeshift_form_id == 1
            ):
                break
            bridge.select_wait(frame)
            frame = bridge.observe()
        if (
            frame is None
            or not frame.shapeshift_form_known
            or frame.shapeshift_form_id != 1
        ):
            trace("traverse_prowl", activation=0, reason="cat_form_not_active")
            return

    prowl_spell_id = next(
        (spell_id for spell_id in PROWL_SPELL_IDS if spell_id in frame.known_spells),
        None,
    )
    if prowl_spell_id is None:
        trace("traverse_prowl", activation=0, reason="spell_unavailable")
        return
    request_id = bridge.select_cast_without_target(
        frame,
        prowl_spell_id,
        purpose="activate Prowl for stealth Traverse",
    )
    if request_id is None:
        trace("traverse_prowl", activation=0, reason="cast_unavailable")
        return
    outcome = bridge.wait_for_settlement(frame.frame_id)
    trace(
        "traverse_prowl",
        activation=1,
        spell_id=prowl_spell_id,
        success=outcome is not None and outcome.success,
        detail=outcome.detail if outcome is not None else "unsettled",
    )


def _activate_travel_form(bridge, trace) -> None:
    frame = bridge.observe()
    if frame is None:
        trace("traverse_travel_form", activation=0, reason="no_frame")
        return
    if (
        frame.shapeshift_form_spell_known
        and frame.shapeshift_form_spell_id == TRAVEL_FORM_SPELL_ID
    ):
        trace("traverse_travel_form", activation=0, reason="already_active")
        return
    if frame.in_combat:
        trace("traverse_travel_form", activation=0, reason="in_combat")
        return
    if frame.shapeshift_form_known and frame.shapeshift_form_id != 0:
        if not frame.shapeshift_form_spell_known:
            trace("traverse_travel_form", activation=0, reason="form_unknown")
            return
        spell_id = frame.shapeshift_form_spell_id
        request_id = bridge.select_cancel_aura(frame, spell_id)
        if request_id is None:
            return
        outcome = bridge.wait_for_settlement(frame.frame_id)
        trace(
            "traverse_travel_form_exit",
            activation=1,
            spell_id=spell_id,
            success=outcome is not None and outcome.success,
            detail=outcome.detail if outcome is not None else "unsettled",
        )
        frame = bridge.observe()
        if frame is None:
            trace("traverse_travel_form", activation=0, reason="no_frame_after_form_exit")
            return
        for _ in range(4):
            if not frame.shapeshift_form_known or frame.shapeshift_form_id == 0:
                break
            bridge.select_wait(frame)
            frame = bridge.observe()
            if frame is None:
                trace(
                    "traverse_travel_form",
                    activation=0,
                    reason="no_frame_after_form_exit",
                )
                return
        if frame.shapeshift_form_known and frame.shapeshift_form_id != 0:
            trace(
                "traverse_travel_form",
                activation=0,
                reason="caster_form_not_active",
            )
            return
    request_id = bridge.select_cast_without_target(
        frame,
        TRAVEL_FORM_SPELL_ID,
        purpose="activate Travel Form for speed-first Traverse",
    )
    if request_id is None:
        trace("traverse_travel_form", activation=0, reason="spell_unavailable")
        return
    outcome = bridge.wait_for_settlement(frame.frame_id)
    trace(
        "traverse_travel_form",
        activation=1,
        success=outcome is not None and outcome.success,
        detail=outcome.detail if outcome is not None else "unsettled",
    )


def _activate_rejuvenation(
    bridge,
    trace,
    *,
    trace_kind: str,
    purpose: str,
) -> bool:
    frame = bridge.observe()
    if frame is None:
        trace(trace_kind, activation=0, reason="no_frame")
        return False
    if set(frame.active_aura_spell_ids).intersection(REJUVENATION_SPELL_IDS):
        trace(trace_kind, activation=0, reason="already_active")
        return True
    if frame.shapeshift_form_known and frame.shapeshift_form_id != 0:
        if not frame.shapeshift_form_spell_known:
            trace(trace_kind, activation=0, reason="form_unknown")
            return False
        request_id = bridge.select_cancel_aura(
            frame,
            frame.shapeshift_form_spell_id,
        )
        if request_id is None:
            trace(
                trace_kind,
                activation=0,
                reason="exit_unavailable",
            )
            return False
        outcome = bridge.wait_for_settlement(frame.frame_id)
        trace(
            trace_kind,
            activation=1,
            phase="exit_current_form",
            success=outcome is not None and outcome.success,
            detail=outcome.detail if outcome is not None else "unsettled",
        )
        return False
    spell_id = next(
        (
            spell_id
            for spell_id in REJUVENATION_SPELL_IDS
            if spell_id in frame.known_spells
        ),
        None,
    )
    if spell_id is None:
        trace(trace_kind, activation=0, reason="spell_unknown")
        return True
    request_id = bridge.select_cast_without_target(
        frame,
        spell_id,
        purpose=purpose,
    )
    if request_id is None:
        trace(trace_kind, activation=0, reason="cast_unavailable")
        return False
    outcome = bridge.wait_for_settlement(frame.frame_id)
    trace(
        trace_kind,
        activation=1,
        phase="cast",
        spell_id=spell_id,
        success=outcome is not None and outcome.success,
        detail=outcome.detail if outcome is not None else "unsettled",
    )
    return False


@dataclass
class TraverseStrategy:
    """Advance north over the connected local navmesh until time or goal."""

    best_world_x: float = TRAVERSE_START_WORLD_X
    frontiers_attempted: int = 0
    frontiers_arrived: int = 0
    route_failures: int = 0
    route_guidepoints_arrived: int = 0
    route_prefix_abandoned: bool = False
    great_lift_boarded: bool = False
    great_lift_completed: bool = False
    great_lift_upper_road_arrived: bool = False
    hazard_avoidance: HazardAvoidanceState = field(
        default_factory=HazardAvoidanceState
    )
    visited_frontiers: set[str] = field(default_factory=set)

    def summary(self) -> dict[str, object]:
        northing = max(0.0, self.best_world_x - TRAVERSE_START_WORLD_X)
        full_distance = TRAVERSE_GOAL_WORLD_X - TRAVERSE_START_WORLD_X
        return {
            "best_world_x": round(self.best_world_x, 3),
            "northing_yards": round(northing, 3),
            "goal_fraction": round(min(1.0, northing / full_distance), 4),
            "reached_goal": self.best_world_x >= TRAVERSE_GOAL_WORLD_X,
            "frontiers_attempted": self.frontiers_attempted,
            "frontiers_arrived": self.frontiers_arrived,
            "route_failures": self.route_failures,
            "route_guidepoints_arrived": self.route_guidepoints_arrived,
            "route_prefix_completed": (
                self.route_guidepoints_arrived == len(TRAVERSE_ROUTE_PREFIX)
            ),
            "great_lift_boarded": self.great_lift_boarded,
            "great_lift_completed": self.great_lift_completed,
            "great_lift_upper_road_arrived": self.great_lift_upper_road_arrived,
        }

    def run(self, bridge, *, until: float) -> None:
        tracer = getattr(bridge, "_tracer", None)

        def trace(kind: str, **payload) -> None:
            if tracer is not None:
                tracer.emit(kind, **payload)

        navigator = RouteNavigator(tracer=tracer)
        trace(
            "strategy_start",
            strategy="traverse",
            map_id=KALIMDOR_MAP_ID,
            goal_world_x=TRAVERSE_GOAL_WORLD_X,
        )
        while time.monotonic() < until and not getattr(bridge, "finished", False):
            descending_shimmering_flats = (
                not self.route_prefix_abandoned
                and self.route_guidepoints_arrived < len(TRAVERSE_ROUTE_PREFIX)
                and (
                    TRAVERSE_ROUTE_PREFIX[self.route_guidepoints_arrived][0]
                    .startswith("shimmering-flats-descent-")
                    or TRAVERSE_ROUTE_PREFIX[self.route_guidepoints_arrived][0]
                    == "shimmering-flats-south-road"
                )
            )
            if descending_shimmering_flats:
                if not _activate_rejuvenation(
                    bridge,
                    trace,
                    trace_kind="traverse_descent_rejuvenation",
                    purpose="keep Rejuvenation active across the Shimmering Flats drops",
                ):
                    continue
                if (
                    TRAVERSE_ROUTE_PREFIX[self.route_guidepoints_arrived][0]
                    == "shimmering-flats-south-road"
                ):
                    descent_frame = bridge.observe()
                    if descent_frame is None:
                        continue
                    if (
                        descent_frame.health
                        < descent_frame.max_health
                        * SECOND_DESCENT_MIN_HEALTH_FRACTION
                    ):
                        bridge.select_wait(descent_frame)
                        trace(
                            "traverse_descent_healing",
                            activation=1,
                            health=descent_frame.health,
                            max_health=descent_frame.max_health,
                            required_fraction=SECOND_DESCENT_MIN_HEALTH_FRACTION,
                        )
                        continue
            elif self.route_guidepoints_arrived < ROAD_CONTROL_START_GUIDEPOINT:
                _activate_travel_form(bridge, trace)
            here = navigator._observe_position(bridge)
            if here is None:
                time.sleep(1.0)
                continue
            if here.map_id != KALIMDOR_MAP_ID:
                trace("traverse_stopped", reason="left_kalimdor", map_id=here.map_id)
                break

            if (
                self.route_guidepoints_arrived == 0
                and here.x >= ROAD_ROUTE_RESUME_MIN_WORLD_X
            ):
                resume_index, (resume_name, resume_point) = min(
                    enumerate(TRAVERSE_ROUTE_PREFIX),
                    key=lambda item: math.dist(
                        (here.x, here.y, here.z),
                        (item[1][1].x, item[1][1].y, item[1][1].z),
                    ),
                )
                resume_distance = math.dist(
                    (here.x, here.y, here.z),
                    (resume_point.x, resume_point.y, resume_point.z),
                )
                if resume_distance <= ROAD_ROUTE_RESUME_RADIUS_YARDS:
                    self.route_guidepoints_arrived = resume_index + 1
                    trace(
                        "traverse_route_resumed",
                        activation=1,
                        name=resume_name,
                        route_guidepoints_arrived=self.route_guidepoints_arrived,
                        distance=round(resume_distance, 3),
                    )

            previous_best = self.best_world_x
            self.best_world_x = max(self.best_world_x, here.x)
            if self.best_world_x > previous_best:
                trace(
                    "traverse_progress",
                    world_x=round(here.x, 3),
                    **self.summary(),
                )
            if here.x >= TRAVERSE_GOAL_WORLD_X - GOAL_RADIUS_YARDS:
                self.best_world_x = max(self.best_world_x, TRAVERSE_GOAL_WORLD_X)
                break

            if (
                not self.route_prefix_abandoned
                and self.route_guidepoints_arrived < len(TRAVERSE_ROUTE_PREFIX)
            ):
                name, target = TRAVERSE_ROUTE_PREFIX[self.route_guidepoints_arrived]
                trace(
                    "traverse_route_guidepoint",
                    activation=self.route_guidepoints_arrived + 1,
                    name=name,
                    target=[target.x, target.y, target.z],
                )
                if self.route_guidepoints_arrived > 0:
                    end, failure_reason = _steer_road_leg(
                        bridge,
                        navigator,
                        target,
                        deadline=until,
                        trace=trace,
                        avoidance=self.hazard_avoidance,
                        allow_northing_pass=(
                            name not in ROAD_EXACT_GUIDEPOINTS
                            or name in ROAD_STEEP_PASS_GUIDEPOINTS
                        ),
                        pass_lateral_yards=(
                            ROAD_CORRIDOR_PASS_LATERAL_YARDS
                            if name in ROAD_CORRIDOR_GUIDEPOINTS
                            else ROAD_PASS_LATERAL_YARDS
                        ),
                        arrival_radius=(
                            3.0
                            if name in ROAD_TIGHT_ARRIVAL_GUIDEPOINTS
                            else ROAD_ARRIVAL_RADIUS_YARDS
                        ),
                        hold_terrain_hazards=(
                            name in ROAD_TERRAIN_CONSTRAINED_GUIDEPOINTS
                        ),
                        jump_terrain=name in ROAD_STEEP_GUIDEPOINTS,
                        jump_once=name in ROAD_SINGLE_JUMP_GUIDEPOINTS,
                        straight_jump_pulses=(
                            ROAD_BOUNDED_STRAIGHT_JUMP_GUIDEPOINTS.get(name, 0)
                        ),
                        bounded_jump_floor_z=ROAD_BOUNDED_JUMP_FLOOR_Z.get(name),
                        downstream_route=(
                            self.route_guidepoints_arrived
                            >= ROAD_CONTROL_START_GUIDEPOINT
                        ),
                        stealth_route=name in ROAD_STEALTH_GUIDEPOINTS,
                        landing_then_clear=(
                            name in ROAD_LANDING_THEN_CLEAR_GUIDEPOINTS
                        ),
                        tight_lateral_control=(
                            name in ROAD_LATERAL_TIGHT_GUIDEPOINTS
                        ),
                    )
                    if end is not None:
                        self.best_world_x = max(self.best_world_x, end.x)
                        skip_target = ROAD_GUIDEPOINT_SKIP_AFTER.get(name)
                        if skip_target is None:
                            self.route_guidepoints_arrived += 1
                        else:
                            self.route_guidepoints_arrived = next(
                                index
                                for index, (route_name, _point) in enumerate(
                                    TRAVERSE_ROUTE_PREFIX
                                )
                                if route_name == skip_target
                            )
                            trace(
                                "traverse_route_guidepoints_skipped",
                                activation=1,
                                after=name,
                                next=skip_target,
                            )
                        trace(
                            "traverse_route_guidepoint_arrived",
                            activation=self.route_guidepoints_arrived,
                            name=name,
                            world_x=round(end.x, 3),
                        )
                        if self.route_guidepoints_arrived == len(TRAVERSE_ROUTE_PREFIX):
                            trace(
                                "traverse_great_lift_arrived",
                                world_x=round(end.x, 3),
                                world_y=round(end.y, 3),
                                world_z=round(end.z, 3),
                            )
                            break
                    else:
                        self.route_failures += 1
                        self.route_prefix_abandoned = True
                        trace(
                            "traverse_route_guidepoint_failed",
                            activation=self.route_guidepoints_arrived + 1,
                            name=name,
                            reason=failure_reason,
                        )
                    continue
                safe_resume = lambda: _activate_travel_form(bridge, trace)
                result = navigator.navigate_to(
                    bridge,
                    target,
                    deadline=until,
                    on_safe_resume=safe_resume,
                    engage_attackers=False,
                )
                if result.end is not None:
                    self.best_world_x = max(self.best_world_x, result.end.x)
                if result.state == NavState.ARRIVED:
                    self.route_guidepoints_arrived += 1
                    trace(
                        "traverse_route_guidepoint_arrived",
                        activation=self.route_guidepoints_arrived,
                        name=name,
                        world_x=(round(result.end.x, 3) if result.end else None),
                    )
                    if self.route_guidepoints_arrived == len(TRAVERSE_ROUTE_PREFIX):
                        trace(
                            "traverse_great_lift_arrived",
                            world_x=(round(result.end.x, 3) if result.end else None),
                            world_y=(round(result.end.y, 3) if result.end else None),
                            world_z=(round(result.end.z, 3) if result.end else None),
                        )
                        break
                else:
                    self.route_failures += 1
                    self.route_prefix_abandoned = True
                    trace(
                        "traverse_route_guidepoint_failed",
                        activation=self.route_guidepoints_arrived + 1,
                        name=name,
                        reason=result.reason,
                    )
                continue

            if (
                self.route_guidepoints_arrived == len(TRAVERSE_ROUTE_PREFIX)
                and not self.great_lift_completed
            ):
                frame = bridge.observe()
                if frame is None:
                    time.sleep(1.0)
                    continue
                if frame.on_transport:
                    if not self.great_lift_boarded:
                        self.great_lift_boarded = True
                        trace(
                            "traverse_great_lift_boarded",
                            world_z=round(frame.location.z, 3),
                        )
                    if frame.location.z >= GREAT_LIFT_EXIT_Z:
                        _steer_toward(
                            bridge,
                            frame,
                            GREAT_LIFT_UPPER_DOCK,
                            purpose="walk off the observed Great Lift at its upper dock",
                        )
                        trace(
                            "traverse_great_lift_disembarking",
                            world_z=round(frame.location.z, 3),
                        )
                    else:
                        bridge.select_wait(frame)
                    continue

                if frame.location.z >= GREAT_LIFT_EXIT_Z:
                    self.great_lift_completed = True
                    trace(
                        "traverse_great_lift_completed",
                        world_z=round(frame.location.z, 3),
                    )
                    continue

                lift = _observed_lift_at_lower_dock(frame)
                if lift is None:
                    bridge.select_wait(frame)
                    trace("traverse_great_lift_waiting")
                    continue
                _steer_toward(
                    bridge,
                    frame,
                    Point(
                        frame.location.map_id,
                        lift.location.x,
                        lift.location.y,
                        lift.location.z,
                    ),
                    purpose="board the observed Great Lift through ordinary movement",
                )
                trace(
                    "traverse_great_lift_boarding",
                    lift_entry=lift.entry,
                    lift_guid=lift.guid,
                    lift_distance=round(lift.distance, 3),
                    lift_z=round(lift.location.z, 3),
                )
                continue

            if self.great_lift_completed and not self.great_lift_upper_road_arrived:
                result = navigator.navigate_to(
                    bridge,
                    GREAT_LIFT_UPPER_ROAD,
                    deadline=until,
                    engage_attackers=False,
                )
                if result.end is not None:
                    self.best_world_x = max(self.best_world_x, result.end.x)
                if result.state == NavState.ARRIVED:
                    self.great_lift_upper_road_arrived = True
                    trace("traverse_great_lift_upper_road_arrived")
                else:
                    self.route_failures += 1
                    trace(
                        "traverse_great_lift_upper_road_failed",
                        reason=result.reason,
                    )
                continue

            graph = bridge.local_navigation_graph(
                here,
                radius=FRONTIER_RADIUS_YARDS,
            )
            if not graph.ok:
                trace(
                    "traverse_stopped",
                    reason="local_graph_unavailable",
                    status=graph.status,
                    detail=graph.message,
                )
                break
            frontier = _select_frontier(
                graph,
                best_world_x=self.best_world_x,
                visited=self.visited_frontiers,
            )
            if frontier is None:
                trace("traverse_stopped", reason="no_untried_northbound_frontier")
                break

            self.visited_frontiers.add(frontier.key)
            self.frontiers_attempted += 1
            target = Point(
                KALIMDOR_MAP_ID,
                min(frontier.centroid.x, TRAVERSE_GOAL_WORLD_X),
                frontier.centroid.y,
                frontier.centroid.z,
            )
            trace(
                "traverse_frontier",
                activation=self.frontiers_attempted,
                key=frontier.key,
                target=[target.x, target.y, target.z],
                northing_gain=round(target.x - here.x, 3),
            )
            result = navigator.navigate_to(
                bridge,
                target,
                deadline=until,
                engage_attackers=False,
            )
            if result.end is not None:
                self.best_world_x = max(self.best_world_x, result.end.x)
            if result.state == NavState.ARRIVED:
                self.frontiers_arrived += 1
            else:
                self.route_failures += 1
                trace(
                    "traverse_route_failed",
                    key=frontier.key,
                    reason=result.reason,
                    failures=self.route_failures,
                )

        trace("strategy_end", strategy="traverse", **self.summary())
