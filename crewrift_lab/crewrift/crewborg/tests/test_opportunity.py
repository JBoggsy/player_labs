"""Victim-selection + witness logic tests (design §7.2, §10)."""

from __future__ import annotations

from crewrift.crewborg.strategy.opportunity import (
    ALLOWED_WITNESSES_MAX,
    ALLOWED_WITNESSES_MIN,
    DEFAULT_KILL_COOLDOWN_TICKS,
    TRACK_WINDOW_TICKS,
    URGENCY_FULL_TICKS,
    allowed_witnesses_max,
    allowed_witnesses_min,
    has_trackable_victim,
    has_visible_victim,
    kill_urgency_ticks,
    most_isolated_recon_candidate,
    recon_target,
    select_victim,
    ticks_until_kill_ready,
    travel_ticks,
    unwitnessed,
    urgency_full_ticks,
    witness_tolerance,
)
from crewrift.crewborg.strategy.trajectory import AGENT_SPEED_PX
from crewrift.crewborg.types import Belief, PlayerRecord


def test_ticks_until_kill_ready() -> None:
    # Ready now ⇒ 0.
    assert ticks_until_kill_ready(Belief(self_kill_ready=True)) == 0
    # No cooldown start observed yet ⇒ assume a full cooldown remains (don't pre-position).
    assert ticks_until_kill_ready(Belief(self_kill_ready=False)) == DEFAULT_KILL_COOLDOWN_TICKS
    # Mid-cooldown with a learned duration: start 100 + estimate 900 − now 700 = 300 left.
    b = Belief(self_kill_ready=False, last_tick=700, kill_cooldown_start_tick=100, kill_cooldown_estimate=900)
    assert ticks_until_kill_ready(b) == 300
    # Past the estimate (overdue) clamps to 0, never negative.
    b2 = Belief(self_kill_ready=False, last_tick=1200, kill_cooldown_start_tick=100, kill_cooldown_estimate=900)
    assert ticks_until_kill_ready(b2) == 0
    # No learned estimate falls back to the default duration.
    b3 = Belief(self_kill_ready=False, last_tick=100, kill_cooldown_start_tick=0)
    assert ticks_until_kill_ready(b3) == DEFAULT_KILL_COOLDOWN_TICKS - 100


def _crew(belief: Belief, object_id: int, xy: tuple[int, int], color: str, tick: int) -> None:
    belief.roster[color] = PlayerRecord(
        object_id=object_id,
        color=color,
        facing="left",
        world_x=xy[0],
        world_y=xy[1],
        last_seen_tick=tick,
        life_status="alive",
    )


# --- urgency ----------------------------------------------------------------


def test_kill_urgency_is_zero_until_kill_ready() -> None:
    assert kill_urgency_ticks(Belief(last_tick=100)) == 0
    assert kill_urgency_ticks(Belief(last_tick=100, self_kill_ready=True)) == 0  # since-tick unknown
    assert kill_urgency_ticks(Belief(last_tick=100, self_kill_ready=True, kill_ready_since_tick=70)) == 30


# --- has_trackable_victim (selector gate) -----------------------------------


def test_trackable_when_a_crewmate_was_seen_recently() -> None:
    belief = Belief(last_tick=200)
    _crew(belief, 1, (50, 50), "green", 200 - (TRACK_WINDOW_TICKS - 1))  # within the window
    assert has_trackable_victim(belief)


def test_not_trackable_when_only_stale_or_teammates() -> None:
    belief = Belief(last_tick=500, teammate_colors={"red"})
    _crew(belief, 1, (50, 50), "green", 500 - (TRACK_WINDOW_TICKS + 50))  # too stale
    _crew(belief, 2, (60, 50), "red", 500)  # a teammate, never a victim
    assert not has_trackable_victim(belief)


def test_visible_victim_requires_current_tick_visibility() -> None:
    belief = Belief(last_tick=200)
    _crew(belief, 1, (50, 50), "green", 199)
    assert not has_visible_victim(belief)
    belief.roster["green"].last_seen_tick = 200
    assert has_visible_victim(belief)


# --- select_victim ----------------------------------------------------------


def test_select_victim_needs_a_self_position() -> None:
    belief = Belief(last_tick=5)
    _crew(belief, 1, (50, 50), "green", 5)
    assert select_victim(belief) is None


def test_select_victim_takes_a_lone_visible_crewmate() -> None:
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=5)
    _crew(belief, 1, (50, 50), "green", 5)
    v = select_victim(belief)
    assert v is not None and v.object_id == 1


def test_select_victim_requires_a_visible_crewmate() -> None:
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=50)
    _crew(belief, 1, (50, 50), "green", 20)
    assert select_victim(belief) is None


def test_select_victim_ignores_too_stale_crewmates() -> None:
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=500)
    _crew(belief, 1, (50, 50), "green", 20)
    assert select_victim(belief) is None


def test_select_victim_prefers_the_isolated_straggler() -> None:
    # Two clustered crewmates and one straggler far from everyone ⇒ pick the straggler
    # (easiest to finish off unwitnessed), even though it's farther from us.
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=5)
    _crew(belief, 1, (40, 0), "green", 5)  # clustered pair...
    _crew(belief, 2, (50, 0), "blue", 5)  # ...10px apart
    _crew(belief, 3, (300, 0), "white", 5)  # the straggler, far from the others
    v = select_victim(belief)
    assert v is not None and v.object_id == 3


def test_select_victim_prefers_unclaimed_target_when_teammate_is_closer() -> None:
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=5, teammate_colors={"pink"})
    _crew(belief, 1, (100, 0), "green", 5)
    _crew(belief, 2, (0, 100), "blue", 5)
    _crew(belief, 3, (96, 0), "pink", 5)  # teammate is already closer to green

    v = select_victim(belief)
    assert v is not None and v.color == "blue"


def test_select_victim_still_takes_claimed_target_if_it_is_the_only_option() -> None:
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=5, teammate_colors={"pink"})
    _crew(belief, 1, (100, 0), "green", 5)
    _crew(belief, 2, (96, 0), "pink", 5)  # teammate is closer, but there is no other victim

    v = select_victim(belief)
    assert v is not None and v.color == "green"


# --- unwitnessed / witness_tolerance -----------------------------------------


def _witnesses(belief: Belief, n: int, tick: int) -> None:
    """Add ``n`` OTHER live non-teammate crewmates, all currently visible, at
    distinct (and deliberately scattered, some far from the victim) positions."""

    for i in range(n):
        _crew(belief, 100 + i, (500 * (i + 1), 500 * (i + 1)), f"witness{i}", tick)


def test_unwitnessed_true_for_a_lone_target() -> None:
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=5)
    _crew(belief, 1, (50, 50), "green", 5)
    assert unwitnessed(belief, belief.roster["green"])


def test_unwitnessed_true_with_a_single_witness_even_at_zero_urgency() -> None:
    # A lone witness no longer vetoes a strike at all -- ALLOWED_WITNESSES_MIN=1 is
    # tolerated regardless of urgency (James, 2026-07-06).
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=5)
    _crew(belief, 1, (50, 50), "green", 5)
    _witnesses(belief, 1, tick=5)
    assert unwitnessed(belief, belief.roster["green"])


def test_unwitnessed_false_with_two_witnesses_at_zero_urgency() -> None:
    # Two witnesses exceed the zero-urgency tolerance (1) ⇒ still vetoed.
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=5)
    _crew(belief, 1, (50, 50), "green", 5)
    _witnesses(belief, 2, tick=5)
    assert not unwitnessed(belief, belief.roster["green"])


def test_unwitnessed_ignores_a_stale_witness() -> None:
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=500)
    _crew(belief, 1, (50, 50), "green", 500)
    _crew(belief, 2, (60, 50), "blue", 100)  # last seen 400 ticks ago ⇒ not counted
    assert unwitnessed(belief, belief.roster["green"])


def test_unwitnessed_counts_a_witness_far_from_the_victim_if_visible_now() -> None:
    # A witness need not be near the VICTIM specifically -- being visible to us at all,
    # this tick, is enough (vision is symmetric; see the module docstring). Two such
    # far-away witnesses still exceed the zero-urgency tolerance (1) -- distance never
    # mattered, only current-tick visibility does.
    belief = Belief(self_world_x=0, self_world_y=0, last_tick=5)
    _crew(belief, 1, (50, 50), "green", 5)
    _witnesses(belief, 2, tick=5)
    assert not unwitnessed(belief, belief.roster["green"])


def test_full_urgency_strikes_through_several_witnesses() -> None:
    # At full urgency the tolerance (ALLOWED_WITNESSES_MAX=6) exceeds the max possible
    # witness count in this game's fixed 6-crew format (5 other live crew) -- an
    # effective "always strike," reached via the ramp rather than a hard cutover.
    belief = Belief(
        self_world_x=0, self_world_y=0, last_tick=URGENCY_FULL_TICKS,
        self_kill_ready=True, kill_ready_since_tick=0,
    )
    _crew(belief, 1, (50, 50), "green", URGENCY_FULL_TICKS)
    _witnesses(belief, 5, tick=URGENCY_FULL_TICKS)
    assert unwitnessed(belief, belief.roster["green"])


def test_urgency_full_ticks_default_env_and_clamp(monkeypatch) -> None:
    monkeypatch.delenv("CREWBORG_URGENCY_FULL_TICKS", raising=False)
    assert urgency_full_ticks() == URGENCY_FULL_TICKS
    monkeypatch.setenv("CREWBORG_URGENCY_FULL_TICKS", "80")
    assert urgency_full_ticks() == 80
    monkeypatch.setenv("CREWBORG_URGENCY_FULL_TICKS", "0")
    assert urgency_full_ticks() == 1  # clamped: it is a divisor
    monkeypatch.setenv("CREWBORG_URGENCY_FULL_TICKS", "garbage")
    assert urgency_full_ticks() == URGENCY_FULL_TICKS  # invalid falls back to default


def test_allowed_witnesses_min_max_default_env(monkeypatch) -> None:
    monkeypatch.delenv("CREWBORG_ALLOWED_WITNESSES_MIN", raising=False)
    monkeypatch.delenv("CREWBORG_ALLOWED_WITNESSES_MAX", raising=False)
    assert allowed_witnesses_min() == ALLOWED_WITNESSES_MIN == 1
    assert allowed_witnesses_max() == ALLOWED_WITNESSES_MAX == 6
    monkeypatch.setenv("CREWBORG_ALLOWED_WITNESSES_MIN", "2")
    monkeypatch.setenv("CREWBORG_ALLOWED_WITNESSES_MAX", "4")
    assert allowed_witnesses_min() == 2
    assert allowed_witnesses_max() == 4


def test_witness_tolerance_ramps_linearly_with_urgency() -> None:
    belief = Belief(self_kill_ready=True, kill_ready_since_tick=0)
    belief.last_tick = 0
    assert witness_tolerance(belief) == ALLOWED_WITNESSES_MIN  # zero urgency ⇒ 1
    belief.last_tick = URGENCY_FULL_TICKS // 2
    assert witness_tolerance(belief) == 3  # halfway ⇒ 1 + 5*0.5 = 3.5, floored to 3
    belief.last_tick = URGENCY_FULL_TICKS
    assert witness_tolerance(belief) == ALLOWED_WITNESSES_MAX  # full urgency ⇒ 6
    belief.last_tick = URGENCY_FULL_TICKS * 10  # past full urgency never exceeds the max
    assert witness_tolerance(belief) == ALLOWED_WITNESSES_MAX


def test_fast_urgency_ramp_strikes_through_more_witnesses_sooner(monkeypatch) -> None:
    # Same absolute urgency (80 ticks) and the same 3 witnesses; only the ramp LENGTH
    # differs. Shortened to 80 ticks ⇒ full urgency ⇒ tolerance 6 ⇒ strikes. Left at the
    # default 240 ⇒ frac 0.33 ⇒ tolerance 2 ⇒ 3 witnesses still exceed it ⇒ vetoed.
    monkeypatch.setenv("CREWBORG_URGENCY_FULL_TICKS", "80")
    belief = Belief(
        self_world_x=0, self_world_y=0, last_tick=80,
        self_kill_ready=True, kill_ready_since_tick=0,
    )
    _crew(belief, 1, (50, 50), "green", 80)
    _witnesses(belief, 3, tick=80)
    assert unwitnessed(belief, belief.roster["green"])
    monkeypatch.delenv("CREWBORG_URGENCY_FULL_TICKS")
    assert not unwitnessed(belief, belief.roster["green"])  # default ramp still vetoes 3


# --- travel_ticks / most_isolated_recon_candidate (2026-07-06) --------------


def test_travel_ticks_straight_line_without_a_nav_graph() -> None:
    belief = Belief(last_tick=5)  # no belief.nav
    assert travel_ticks(belief, (0, 0), (30, 40)) == 50.0 / AGENT_SPEED_PX  # a 3-4-5 triangle


def test_travel_ticks_follows_the_nav_route_around_a_wall() -> None:
    import numpy as np

    from crewrift.crewborg.map.types import MapData, MapPoint, MapRect
    from crewrift.crewborg.nav import build_nav_graph

    # A wall splits the map in two, with a single gap at the bottom to walk through --
    # so the real route is much longer than the straight-line distance through the wall.
    m = MapData(width=200, height=100, tasks=(), vents=(), rooms=(),
                button=MapRect(x=4, y=4, w=8, h=8), home=MapPoint(x=10, y=10))
    walk = np.ones((m.height, m.width), dtype=bool)
    walk[:80, 95:105] = False  # wall from y=0..79, leaving a gap at y=80..99
    nav = build_nav_graph(walk, map_data=m)
    belief = Belief(map=m, nav=nav, last_tick=5)

    straight_line = travel_ticks(Belief(last_tick=5), (50, 10), (150, 10))
    routed = travel_ticks(belief, (50, 10), (150, 10))
    assert routed > straight_line  # must detour around the wall, not cut through it


def test_most_isolated_recon_candidate_prefers_the_outlier() -> None:
    belief = Belief(last_tick=100)
    _crew(belief, 1, (0, 0), "green", 100)
    _crew(belief, 2, (10, 0), "blue", 100)     # clustered with green
    _crew(belief, 3, (1000, 1000), "purple", 100)  # far from both
    assert most_isolated_recon_candidate(belief) is belief.roster["purple"]


def test_most_isolated_recon_candidate_excludes_teammates_dead_and_stale() -> None:
    belief = Belief(last_tick=1000, teammate_colors={"pink"})
    _crew(belief, 1, (1000, 1000), "pink", 1000)      # teammate -- excluded even though isolated
    _crew(belief, 2, (2000, 2000), "grey", 1000)
    belief.roster["grey"].life_status = "dead"          # dead -- excluded
    _crew(belief, 3, (3000, 3000), "white", 500)        # 500 ticks old -- stale, excluded
    _crew(belief, 4, (0, 0), "green", 1000)
    _crew(belief, 5, (10, 0), "blue", 1000)
    assert most_isolated_recon_candidate(belief).color in {"green", "blue"}


def test_most_isolated_recon_candidate_ties_break_toward_more_recent() -> None:
    belief = Belief(last_tick=100)
    _crew(belief, 1, (0, 0), "green", 60)
    _crew(belief, 2, (100, 0), "blue", 90)  # same single gap to the other -- isolation ties
    assert most_isolated_recon_candidate(belief).color == "blue"


def test_recon_target_is_none_with_no_fresh_candidate() -> None:
    assert recon_target(Belief(last_tick=100)) is None
