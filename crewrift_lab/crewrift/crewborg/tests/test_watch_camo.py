"""WATCH camouflage tests (modes/search.py + docs/designs/watch-camouflage.md).

Camouflage: while Search WATCHes a room with crew and the kill is far from
ready, fake a task at the in-room task spot with the best baked view over the
visible crew instead of hovering. Covered here: the trigger gates (each blocks
individually), spot selection (bake scoring + no-bake fallback), the idle
duration, every escape path, and the ParkedGuard exemption.
"""

from __future__ import annotations

import numpy as np

from crewrift.crewborg.map.types import MapData, MapPoint, MapRect, Room, TaskStation
from crewrift.crewborg.modes import imposter_common as ic
from crewrift.crewborg.modes import search as search_mod
from crewrift.crewborg.modes.search import SearchMode, camo_buffer_ticks
from crewrift.crewborg.nav import build_nav_graph
from crewrift.crewborg.types import ActionState, Belief, Intent, PlayerRecord
from crewrift.crewborg.visionbake import TaskVisionBake
from players.player_sdk import EventEmitter, ListTraceSink, ModeDirective

CELL = 32


def _map() -> MapData:
    # Left room holds TWO task stations (A near the west wall, B near the east wall)
    # so spot selection has a real choice; Mid is the spawn room; Right has one task.
    return MapData(
        width=320, height=96,
        tasks=(
            TaskStation(name="A", x=16, y=44, w=8, h=8),
            TaskStation(name="B", x=76, y=44, w=8, h=8),
            TaskStation(name="R", x=260, y=44, w=8, h=8),
        ),
        vents=(),
        rooms=(
            Room(name="Left", x=0, y=0, w=100, h=96),
            Room(name="Mid", x=100, y=0, w=100, h=96),
            Room(name="Right", x=200, y=0, w=120, h=96),
        ),
        button=MapRect(x=4, y=4, w=8, h=8),
        home=MapPoint(x=150, y=48),  # spawn in Mid
    )


def _belief(self_xy=(50, 48), tick=100) -> Belief:
    m = _map()
    nav = build_nav_graph(np.ones((m.height, m.width), dtype=bool), map_data=m)
    # No kill cooldown observed yet -> ticks_until_kill_ready == 500 (far from ready).
    return Belief(map=m, nav=nav, self_role="imposter", phase="Playing",
                  self_world_x=self_xy[0], self_world_y=self_xy[1], last_tick=tick)


def _crew(belief: Belief, color: str, xy, tick=None) -> PlayerRecord:
    rec = PlayerRecord(color=color, world_x=xy[0], world_y=xy[1],
                       last_seen_tick=belief.last_tick if tick is None else tick, life_status="alive")
    belief.roster[color] = rec
    return rec


def _watching(belief: Belief, room: str = "Left") -> SearchMode:
    """A SearchMode already in WATCH on ``room``, with a captured trace."""

    mode = SearchMode()
    mode._state = "watch"
    mode._target_room = room
    mode.emit = EventEmitter(ListTraceSink(), tick=belief.last_tick)
    return mode


def _events(mode: SearchMode, name: str):
    return [e for e in mode.emit.trace_sink.events if e.name == name]


def _keep_crew_visible(belief: Belief) -> None:
    for rec in belief.roster.values():
        rec.record(belief.last_tick, rec.world_x, rec.world_y, "left", 1001)


def _no_bake(monkeypatch) -> None:
    monkeypatch.setattr(search_mod, "_vision_cache", None)


def _bake(masks: np.ndarray) -> TaskVisionBake:
    return TaskVisionBake(
        cell_size=CELL, range_px=360, masks=masks,
        counts=masks.sum(axis=(1, 2)).astype(np.int64),
        walkability_sha1="test", walkability_shape=(96, 320),
    )


# --- trigger gating (each condition blocks individually) ---------------------------------- #


def test_camo_fires_in_watch_with_crew_and_cold_kill(monkeypatch) -> None:
    _no_bake(monkeypatch)
    belief = _belief()
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    intent = mode.decide(belief, ActionState())
    assert mode._camo_active()
    assert "camo" in intent.reason
    [enter] = _events(mode, "domain.camo_idle")
    assert enter.data["phase"] == "enter"
    assert enter.data["visible_crew"] == 1
    assert enter.data["ticks_until_ready"] > search_mod.camo_min_cd_ticks()
    assert enter.data["bake_used"] is False


def test_gate_a_no_camo_outside_watch(monkeypatch) -> None:
    # Same crew + cold kill, but the FSM is en route (GO_TO_ROOM): a visible
    # crewmate triggers FOLLOW, never camo. (Camo is WATCH-only by construction.)
    _no_bake(monkeypatch)
    belief = _belief(self_xy=(150, 48))
    _crew(belief, "green", (60, 48))
    mode = SearchMode()
    mode.emit = EventEmitter(ListTraceSink(), tick=belief.last_tick)
    mode._state = "go_to_room"
    mode._target_room = "Left"
    mode._goto_point = (50, 48)
    intent = mode.decide(belief, ActionState())
    assert mode._state == "follow"
    assert not mode._camo_active()
    assert "camo" not in intent.reason


def test_gate_b_no_camo_without_visible_crew_in_room(monkeypatch) -> None:
    _no_bake(monkeypatch)
    belief = _belief()  # nobody in the roster
    mode = _watching(belief)
    mode.decide(belief, ActionState())
    assert not mode._camo_active()
    assert not _events(mode, "domain.camo_idle")


def test_gate_c_no_camo_when_kill_is_close_to_ready(monkeypatch) -> None:
    _no_bake(monkeypatch)
    belief = _belief()
    # Cooldown started 450 ticks ago with the 500-tick default -> 50 ticks remain (< 100).
    belief.kill_cooldown_start_tick = belief.last_tick - 450
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    intent = mode.decide(belief, ActionState())
    assert not mode._camo_active()
    assert "camo" not in intent.reason


def test_gate_c_threshold_is_env_tunable(monkeypatch) -> None:
    _no_bake(monkeypatch)
    monkeypatch.setenv("CREWBORG_CAMO_MIN_CD_TICKS", "460")
    belief = _belief()
    belief.kill_cooldown_start_tick = belief.last_tick - 450  # 50 remain — still > gate? no: 50 <= 460
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    mode.decide(belief, ActionState())
    assert not mode._camo_active()
    monkeypatch.setenv("CREWBORG_CAMO_MIN_CD_TICKS", "40")  # 50 > 40 — camo allowed
    mode2 = _watching(belief)
    mode2.decide(belief, ActionState())
    assert mode2._camo_active()


def test_kill_switch_disables_camo(monkeypatch) -> None:
    _no_bake(monkeypatch)
    monkeypatch.setenv("CREWBORG_CAMO", "0")
    belief = _belief()
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    intent = mode.decide(belief, ActionState())
    assert not mode._camo_active()
    assert "camo" not in intent.reason


def test_no_camo_in_a_room_without_task_spots(monkeypatch) -> None:
    _no_bake(monkeypatch)
    belief = _belief(self_xy=(150, 48))
    _crew(belief, "green", (160, 48))
    mode = _watching(belief, room="Mid")  # Mid has no task station
    mode.decide(belief, ActionState())
    assert not mode._camo_active()
    assert not _events(mode, "domain.camo_idle")


# --- spot selection ------------------------------------------------------------------------ #


def test_bake_scoring_picks_the_spot_seeing_the_most_visible_crew(monkeypatch) -> None:
    # Crew at (60, 48) -> cell (row 1, col 1). Task A (index 0) sees that cell,
    # task B (index 1) does not — A must win although B is nearer to self.
    masks = np.zeros((3, 3, 10), dtype=bool)
    masks[0, 1, 1] = True
    masks[1, 2, 2] = True
    monkeypatch.setattr(search_mod, "_vision_cache", _bake(masks))
    belief = _belief(self_xy=(76, 48))  # standing on B
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    mode.decide(belief, ActionState())
    assert mode._camo_task_index == 0
    [enter] = _events(mode, "domain.camo_idle")
    assert enter.data["bake_used"] is True


def test_bake_tie_breaks_on_larger_visible_area(monkeypatch) -> None:
    # Both spots see the crew cell; B sees strictly more cells overall -> B wins.
    masks = np.zeros((3, 3, 10), dtype=bool)
    masks[0, 1, 1] = True
    masks[1, 1, 1] = True
    masks[1, 1, 2] = True
    monkeypatch.setattr(search_mod, "_vision_cache", _bake(masks))
    belief = _belief(self_xy=(16, 44))  # standing on A
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    mode.decide(belief, ActionState())
    assert mode._camo_task_index == 1


def test_missing_bake_falls_back_to_nearest_task_spot(monkeypatch) -> None:
    _no_bake(monkeypatch)
    belief = _belief(self_xy=(70, 48))  # B (index 1) is nearest
    _crew(belief, "green", (30, 48))
    mode = _watching(belief)
    intent = mode.decide(belief, ActionState())
    assert mode._camo_task_index == 1
    assert intent.kind in {"navigate_to", "idle"}  # never crash, never stall


# --- idle duration + escapes --------------------------------------------------------------- #


def _advance(ticks: int, mode: SearchMode, belief: Belief) -> list[Intent]:
    """Advance ``ticks`` ticks with crew kept visible, collecting intents."""

    out = []
    for _ in range(ticks):
        belief.last_tick += 1
        _keep_crew_visible(belief)
        out.append(mode.decide(belief, ActionState()))
    return out


def test_idle_lasts_one_task_duration_plus_buffer_then_resumes_watch(monkeypatch) -> None:
    _no_bake(monkeypatch)
    belief = _belief(self_xy=(16, 44))
    anchor = ic.task_point(belief, 0)
    belief.self_world_x, belief.self_world_y = anchor  # already standing at the spot
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    first = mode.decide(belief, ActionState())
    assert first.kind == "idle" and "camo" in first.reason  # arrived -> hold starts

    hold = ic.FAKE_TASK_TICKS + camo_buffer_ticks()
    intents = _advance(hold, mode, belief)
    # Idles for exactly the hold (the first decide + hold-1 more), then exits
    # "done" on the deadline tick and resumes normal WATCH.
    assert all(i.kind == "idle" and "camo" in i.reason for i in intents[:-1])
    assert len(intents[:-1]) == hold - 1
    assert "camo" not in intents[-1].reason
    assert not mode._camo_active()
    assert mode._camo_done
    exits = [e for e in _events(mode, "domain.camo_idle") if e.data["phase"] == "exit"]
    assert [e.data["reason"] for e in exits] == ["done"]
    assert exits[0].data["arrived"] is True

    # One camo per room visit: conditions still hold, but no re-trigger...
    belief.last_tick += 1
    _keep_crew_visible(belief)
    mode.decide(belief, ActionState())
    assert not mode._camo_active()
    # ...until a fresh room entry re-arms it.
    mode._enter_search_room(belief, anchor, "Left")
    assert not mode._camo_done


def test_escape_kill_soon(monkeypatch) -> None:
    _no_bake(monkeypatch)
    belief = _belief(self_xy=(16, 44))
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    mode.decide(belief, ActionState())
    assert mode._camo_active()
    belief.last_tick += 1
    _keep_crew_visible(belief)
    belief.self_kill_ready = True  # the estimate was wrong — the kill is ready NOW
    intent = mode.decide(belief, ActionState())
    assert not mode._camo_active()
    assert "camo" not in intent.reason
    exits = [e for e in _events(mode, "domain.camo_idle") if e.data["phase"] == "exit"]
    assert [e.data["reason"] for e in exits] == ["kill_soon"]


def test_escape_crew_lost(monkeypatch) -> None:
    _no_bake(monkeypatch)
    belief = _belief(self_xy=(16, 44))
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    mode.decide(belief, ActionState())
    assert mode._camo_active()
    # Crew vanish: advance past the crew-lost window without refreshing sightings.
    belief.last_tick += search_mod.camo_crew_lost_ticks() + 1
    mode.decide(belief, ActionState())
    assert not mode._camo_active()
    exits = [e for e in _events(mode, "domain.camo_idle") if e.data["phase"] == "exit"]
    assert [e.data["reason"] for e in exits] == ["crew_lost"]


def test_escape_travel_timeout(monkeypatch) -> None:
    _no_bake(monkeypatch)
    belief = _belief(self_xy=(90, 90))  # in Left, far from both spots; never moves
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    intent = mode.decide(belief, ActionState())
    assert intent.kind == "navigate_to" and "camo" in intent.reason
    intents = _advance(search_mod.CAMO_TRAVEL_CAP_TICKS + 1, mode, belief)
    assert not mode._camo_active()
    assert "camo" not in intents[-1].reason
    exits = [e for e in _events(mode, "domain.camo_idle") if e.data["phase"] == "exit"]
    assert [e.data["reason"] for e in exits] == ["travel_timeout"]
    assert exits[0].data["arrived"] is False


def test_escape_preempted_on_mode_exit(monkeypatch) -> None:
    # A meeting (or Recon/Hunt/Evade) replaces the mode instance; on_exit closes
    # the camo visibly so every enter pairs with an exit.
    _no_bake(monkeypatch)
    belief = _belief(self_xy=(16, 44))
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    mode.decide(belief, ActionState())
    assert mode._camo_active()
    mode.on_exit(belief, ActionState(), ModeDirective(mode="attend_meeting", source="strategy"))
    assert not mode._camo_active()
    exits = [e for e in _events(mode, "domain.camo_idle") if e.data["phase"] == "exit"]
    assert [e.data["reason"] for e in exits] == ["preempted"]


# --- ParkedGuard exemption ------------------------------------------------------------------ #


def test_parked_guard_exempts_intentional_idle() -> None:
    guard = ic.ParkedGuard()
    ready = Belief(phase="Playing", self_kill_ready=True, last_tick=1)
    idle = Intent(kind="idle", reason="camo")
    for _ in range(ic.PARKED_GUARD_TICKS * 3):
        assert not guard.fires(ready, (100, 100), idle, intentional_idle=True)
    # The exemption also RESETS the streak — an interleaved intentional idle
    # cannot be combined with unintentional ticks to reach the trigger.
    for _ in range(ic.PARKED_GUARD_TICKS - 1):
        assert not guard.fires(ready, (100, 100), idle)
    assert not guard.fires(ready, (100, 100), idle, intentional_idle=True)
    assert not guard.fires(ready, (100, 100), idle)  # streak restarted from 1
    # And the guard still fully fires for plain unintentional parking.
    for _ in range(ic.PARKED_GUARD_TICKS - 2):
        assert not guard.fires(ready, (100, 100), idle)
    assert guard.fires(ready, (100, 100), idle)


def test_camo_never_carries_a_kill_ready_idle(monkeypatch) -> None:
    # The invariant behind the exemption: by the time a tick is kill-ready the
    # kill-soon escape has already ended the camo, so no camo idle coincides
    # with a kill-ready tick (and camo_guard_exempt stays unreachable).
    _no_bake(monkeypatch)
    belief = _belief(self_xy=(16, 44))
    _crew(belief, "green", (60, 48))
    mode = _watching(belief)
    mode.decide(belief, ActionState())
    belief.last_tick += 1
    _keep_crew_visible(belief)
    belief.self_kill_ready = True
    intent = mode.decide(belief, ActionState())
    assert not (intent.kind == "idle" and "camo" in intent.reason)
    assert not _events(mode, "domain.camo_guard_exempt")
