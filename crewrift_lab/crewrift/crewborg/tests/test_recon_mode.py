"""Recon mode tests (modes/recon.py).

Recon pre-positions on the most ISOLATED fresh crewmate (timed by the selector to
arrive right as the kill comes off cooldown), so a victim is in hand the instant we
can kill.
"""

from __future__ import annotations

from crewrift.crewborg.modes.recon import ReconMode
from crewrift.crewborg.strategy.opportunity import most_recent_victim
from crewrift.crewborg.types import ActionState, Belief, CommanderPriorities, PlayerRecord


def _imposter() -> Belief:
    b = Belief(phase="Playing", self_role="imposter", self_world_x=100, self_world_y=100, last_tick=50)
    b.teammate_colors = {"red"}  # crewborg's partner
    return b


def _seen(belief: Belief, color: str, xy, tick) -> PlayerRecord:
    rec = PlayerRecord(color=color, world_x=xy[0], world_y=xy[1], last_seen_tick=tick, life_status="alive")
    belief.roster[color] = rec
    return rec


def test_recon_beelines_to_the_most_isolated_crewmate() -> None:
    # green and blue are clustered close together; purple is far from both -- the
    # target is purple (farthest from every other candidate), even though it's the
    # STALEST sighting of the three (recency is only the tie-break, not the criterion).
    b = _imposter()
    _seen(b, "green", (200, 60), tick=45)
    _seen(b, "blue", (210, 65), tick=40)
    _seen(b, "purple", (600, 400), tick=10)
    intent = ReconMode().decide(b, ActionState())
    assert intent.kind == "navigate_to"
    assert intent.point == (600, 400)


def test_recon_isolation_ties_break_toward_more_recently_seen() -> None:
    # Exactly two candidates: each is "farthest" from the other by definition (the
    # same single gap), so isolation ties and the more recent sighting wins.
    b = _imposter()
    _seen(b, "green", (200, 60), tick=20)
    _seen(b, "blue", (300, 80), tick=45)
    intent = ReconMode().decide(b, ActionState())
    assert intent.kind == "navigate_to"
    assert intent.point == (300, 80)


def test_recon_prefers_commander_target_player_when_alive_and_known() -> None:
    b = _imposter()
    _seen(b, "green", (200, 60), tick=45)  # current default target
    _seen(b, "blue", (300, 80), tick=20)
    b.commander = CommanderPriorities(target_player="blue", as_of_tick=b.last_tick)
    intent = ReconMode().decide(b, ActionState())
    assert intent.kind == "navigate_to"
    assert intent.point == (300, 80)


def test_recon_target_player_falls_back_when_unknown_or_dead() -> None:
    b = _imposter()
    _seen(b, "green", (200, 60), tick=45)
    b.commander = CommanderPriorities(target_player="blue", as_of_tick=b.last_tick)
    assert ReconMode().decide(b, ActionState()).point == (200, 60)

    dead_target = _seen(b, "blue", (300, 80), tick=49)
    dead_target.life_status = "dead"
    assert ReconMode().decide(b, ActionState()).point == (200, 60)


def test_recon_ignores_the_teammate_imposter() -> None:
    b = _imposter()
    _seen(b, "red", (300, 80), tick=49)   # teammate, most recent — must be skipped
    _seen(b, "green", (200, 60), tick=30)  # the only real crewmate
    intent = ReconMode().decide(b, ActionState())
    assert intent.point == (200, 60)


def test_recon_ignores_dead_crew() -> None:
    b = _imposter()
    dead = _seen(b, "green", (300, 80), tick=49)
    dead.life_status = "dead"
    _seen(b, "blue", (200, 60), tick=30)
    intent = ReconMode().decide(b, ActionState())
    assert intent.point == (200, 60)


def test_recon_idles_with_no_known_crew() -> None:
    b = _imposter()  # roster empty
    assert ReconMode().decide(b, ActionState()).kind == "idle"
    assert most_recent_victim(b) is None


def test_recon_parked_guard_escapes_a_zero_length_seek(monkeypatch) -> None:
    # Insurance path: kill-ready (the selector shouldn't send us here blind, but if
    # anything ever does), the target's last-known point is where we stand, and the
    # occupancy fallback ALSO points at our own feet ⇒ after the guard streak, recon
    # must move somewhere else rather than stand on a ready kill.
    from crewrift.crewborg.modes import imposter_common as ic
    from players.player_sdk import EventEmitter, ListTraceSink

    b = _imposter()
    b.self_kill_ready = True
    _seen(b, "green", (100, 100), tick=10)  # stale, not visible, exactly underfoot
    monkeypatch.setattr("crewrift.crewborg.modes.recon.best_seek_point", lambda belief: (100, 100))
    monkeypatch.setattr(
        "crewrift.crewborg.modes.recon.ranked_seek_points", lambda belief: [(100, 100), (300, 80)]
    )
    mode = ReconMode()
    trace = ListTraceSink()
    mode.emit = EventEmitter(trace, tick=b.last_tick)
    for _ in range(ic.PARKED_GUARD_TICKS - 1):
        intent = mode.decide(b, ActionState())
        assert intent.point == (100, 100)  # the parked zero-length seek
    intent = mode.decide(b, ActionState())
    assert intent.kind == "navigate_to"
    assert intent.point == (300, 80)  # first ranked seek point that is elsewhere
    [event] = [e for e in trace.events if e.name == "domain.parked_guard"]
    assert event.data["mode"] == "recon"


def test_recon_escape_point_is_sticky_until_reached_or_crew_appears(monkeypatch) -> None:
    from crewrift.crewborg.modes import imposter_common as ic

    b = _imposter()
    b.self_kill_ready = True
    _seen(b, "green", (100, 100), tick=10)  # stale, underfoot
    monkeypatch.setattr("crewrift.crewborg.modes.recon.best_seek_point", lambda belief: (100, 100))
    monkeypatch.setattr(
        "crewrift.crewborg.modes.recon.ranked_seek_points", lambda belief: [(300, 80)]
    )
    mode = ReconMode()
    for _ in range(ic.PARKED_GUARD_TICKS):
        intent = mode.decide(b, ActionState())
    assert intent.point == (300, 80)  # guard fired -> escape committed
    # The escape persists on later ticks (a one-tick escape would immediately
    # re-derive the same parked seek target and never actually move).
    assert mode.decide(b, ActionState()).point == (300, 80)
    # A crewmate coming into view releases the escape back to normal recon.
    _seen(b, "blue", (200, 60), tick=b.last_tick)
    assert mode.decide(b, ActionState()).point == (200, 60)
