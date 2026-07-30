"""Critical-invariant tests for beacon (sparing, per the lab's testing discipline).

These cover the few things that would silently lose games or crash an episode:
brad arithmetic (aim rotation direction), the mask stays legal, flow-field routing
reaches the goal, flag-state detection, team-from-slot, and the folded belief
memory (player tracks + danger field).
"""

from __future__ import annotations

import math

import numpy as np

from ctf.beacon import mapdata, nav
from ctf.beacon.perception import perceive
from players.player_sdk import SpriteDef, SpriteObject, SpriteWorld
from ctf.beacon.action import _brad_error, _brads_of, _rotation_button, resolve_action
from ctf.beacon.config import AIM_BRADS_TURN, DEFENDER_COUNT, PEDESTAL
from ctf.beacon.main import seat_from_url, team_from_url
from ctf.beacon.roles import hold_point_for_seat, role_for_seat
from ctf.beacon.strategy import decide_objective
from ctf.beacon.types import (
    ActionState,
    Belief,
    Command,
    Enemy,
    Intent,
    TargetCandidate,
    TargetRef,
)
from players.player_sdk import Button

import pytest


@pytest.fixture
def squads_on(monkeypatch):
    """Force the squad layer ON for tests of squad behavior.

    SQUADS / SQUAD_COMMAND default OFF since v29 (rollback to the static role
    split), but the machinery stays maintained for A/Bs — these tests pin the
    behavior for whenever a flag-on build runs. Both flags are baked into each
    consuming module's namespace at import, so patch them everywhere."""
    from ctf.beacon import action as _action, belief as _belief, chat as _chat
    from ctf.beacon import strategy as _strategy

    for mod in (_strategy, _belief, _chat):
        monkeypatch.setattr(mod, "SQUAD_COMMAND", True, raising=False)
    for mod in (_strategy, _action):
        monkeypatch.setattr(mod, "SQUADS", True, raising=False)


@pytest.fixture
def posts_on(monkeypatch):
    """Enable post positioning without implicitly enabling post-facing."""
    from ctf.beacon import chat as _chat, strategy as _strategy

    monkeypatch.setattr(_strategy, "POSTS", True)
    monkeypatch.setattr(_chat, "POSTS", True)


# --- brad arithmetic --------------------------------------------------------------
def test_brads_of_cardinals():
    assert _brads_of(1, 0) == 0  # east
    assert _brads_of(0, -1) == 64  # north (screen up)
    assert _brads_of(-1, 0) == 128  # west
    assert _brads_of(0, 1) == 192  # south (screen down)


def test_brad_error_shortest_arc():
    assert _brad_error(10, 0) == 10  # CCW
    assert _brad_error(250, 0) == -6  # wraps: shortest is CW
    assert abs(_brad_error(128, 0)) == 128


def test_rotation_button_direction():
    st = ActionState()
    # target CCW of current -> B, recorded +1
    assert _rotation_button(30, st) == int(Button.B)
    assert st.last_rot == 1
    # target CW -> Select, recorded -1
    assert _rotation_button(-30, st) == int(Button.SELECT)
    assert st.last_rot == -1
    # within deadband -> no rotation
    assert _rotation_button(1, st) == 0
    assert st.last_rot == 0


# --- mask legality ----------------------------------------------------------------
def test_mask_is_seven_bits_when_dead():
    b = Belief(team="red", alive=False, self_xy=None)
    cmd = resolve_action(Intent(kind="hold"), b, ActionState())
    assert cmd.held_mask == 0


def test_mask_within_range_while_playing():
    b = Belief(team="red", alive=True, self_xy=(300, 329), aim_brads=0)
    cmd = resolve_action(Intent(kind="navigate_to", point=PEDESTAL["blue"], reason="steal"), b, ActionState())
    assert 0 <= cmd.held_mask <= 0x7F


# --- flow-field navigation --------------------------------------------------------
def test_flow_field_routes_toward_pedestal():
    # From Red spawn, the "steal" flow should step us generally toward Blue (east).
    self_xy = (250, 329)
    wp = nav.flow_waypoint("red", "steal", self_xy)
    assert wp[0] >= self_xy[0]  # eastward, toward Blue's pedestal at x=1049


def test_flow_field_home_routes_back():
    # Carrying home as Red: from midfield, "home" flow should step us west.
    self_xy = (700, 329)
    wp = nav.flow_waypoint("red", "home", self_xy)
    assert wp[0] <= self_xy[0]


def test_every_walkable_cell_routes_to_goal():
    grid = mapdata.walkable_grid()
    field = mapdata.flow_field("red", "steal")
    # Every walkable cell either is the goal (code 0 at goal) or has a next hop.
    walkable = int(grid.sum())
    routed = int((field > 0).sum())
    assert routed >= walkable - 1  # all but the single goal cell have a hop


def test_local_movement_bias_cannot_cross_lineup_wall():
    # The middle lineup pane is glass, but remains solid to the full player body.
    assert not nav.walkable_segment((260, 340), (292, 340))
    assert not nav.walkable_segment((975, 340), (943, 340))


def test_local_movement_bias_can_use_lineup_gap():
    assert nav.walkable_segment((260, 380), (292, 380))
    assert nav.walkable_segment((975, 380), (943, 380))


# --- team / seat from slot --------------------------------------------------------
def test_team_from_slot():
    assert team_from_url("ws://h:2000/player?slot=0&token=x") == "red"
    assert team_from_url("ws://h:2000/player?slot=1&token=x") == "blue"
    assert team_from_url("ws://h:2000/player?slot=14&token=x") == "red"
    assert team_from_url("ws://h:2000/player?slot=7&token=x") == "blue"


def test_seat_from_slot():
    assert seat_from_url("ws://h/p?slot=0") == 0
    assert seat_from_url("ws://h/p?slot=1") == 0  # slot 1 (blue) is also seat 0
    assert seat_from_url("ws://h/p?slot=14") == 7
    assert seat_from_url("ws://h/p?slot=15") == 7


# --- roles (v2) -------------------------------------------------------------------
def test_role_split_by_seat():
    assert role_for_seat(0) == "defender"
    assert role_for_seat(DEFENDER_COUNT - 1) == "defender"
    assert role_for_seat(DEFENDER_COUNT) == "attacker"
    assert role_for_seat(7) == "attacker"


def test_defender_hold_points_on_own_turf():
    # Red defenders hold left of centre; Blue defenders hold right of centre.
    rx = hold_point_for_seat("red", 0)[0]
    bx = hold_point_for_seat("blue", 0)[0]
    assert rx < PEDESTAL["blue"][0] and rx < 617
    assert bx > PEDESTAL["red"][0] and bx > 617


def test_hold_points_snap_to_cover():
    # Every defender hold point should be a cover cell (adjacent to a wall) — v3.
    from ctf.beacon.config import GRID_W, NAV_CELL
    cover = mapdata.cover_grid()
    for team in ("red", "blue"):
        for seat in range(DEFENDER_COUNT):
            hx, hy = hold_point_for_seat(team, seat)
            gx, gy = hx // NAV_CELL, hy // NAV_CELL
            assert cover[gy, gx], f"{team} seat {seat} hold {(hx,hy)} not on cover"


def test_defender_holds_when_arrived(squads_on):
    # Seat 0 is the D-squad LEADER (v22): it orders itself to hold its choke, so
    # the reason is order-driven; the behavior (hold on our turf) is unchanged.
    b = Belief(team="red", seat=0, role="defender", hold_point=(390, 300),
               alive=True, self_xy=(390, 300))
    intent, flow = decide_objective(b)
    assert intent.kind in ("hold", "navigate_to")
    assert intent.reason in ("hold_line", "order_hold", "order_to_hold")
    assert b.order is not None and b.order[0] == "H"  # leader set a hold order


def test_carrier_overrides_role():
    b = Belief(team="red", seat=0, role="defender", hold_point=(390, 300),
               alive=True, self_xy=(390, 300), i_carry_enemy_flag=True)
    intent, flow = decide_objective(b)
    assert intent.reason == "carry_home" and flow == "home"


def test_intercept_visible_thief():
    b = Belief(team="red", seat=7, role="attacker", alive=True, self_xy=(300, 329),
               own_flag_stolen=True, own_flag_thief_pos=(250, 300))
    intent, flow = decide_objective(b)
    assert intent.reason == "intercept_thief" and intent.point == (250, 300)


def test_attacker_escorts_visible_carrier():
    # Enemy flag off its pedestal + visible + we don't carry it => a teammate has it;
    # an attacker moves to the carrier to escort it home (v5).
    b = Belief(team="red", seat=7, role="attacker", alive=True, self_xy=(600, 329),
               i_carry_enemy_flag=False, enemy_flag_on_pedestal=False,
               enemy_flag_pos=(800, 300))
    intent, flow = decide_objective(b)
    assert intent.reason == "escort_carrier" and intent.point == (800, 300)


def test_carrier_still_runs_home_not_escort():
    # The actual carrier runs home (rung 1) even though the flag is off-pedestal.
    b = Belief(team="red", seat=7, role="attacker", alive=True, self_xy=(800, 300),
               i_carry_enemy_flag=True, enemy_flag_on_pedestal=False,
               enemy_flag_pos=(800, 300))
    intent, flow = decide_objective(b)
    assert intent.reason == "carry_home" and flow == "home"


# --- combat overlay ---------------------------------------------------------------
def test_fires_when_aimed_at_close_enemy():
    b = Belief(team="red", alive=True, self_xy=(300, 329), aim_brads=0, fire_ready=True)
    b.enemies = (Enemy(pos=(360, 329), facing="left"),)  # due east, aim already 0
    cmd = resolve_action(Intent(kind="navigate_to", point=PEDESTAL["blue"], reason="steal"), b, ActionState())
    assert cmd.held_mask & int(Button.A)


def test_no_fire_when_aim_off_target():
    b = Belief(team="red", alive=True, self_xy=(300, 329), aim_brads=64, fire_ready=True)
    b.enemies = (Enemy(pos=(360, 329), facing="left"),)  # east, but we aim north
    cmd = resolve_action(Intent(kind="navigate_to", point=PEDESTAL["blue"], reason="steal"), b, ActionState())
    assert not (cmd.held_mask & int(Button.A))  # rotate to close the arc, don't fire
    assert cmd.held_mask & (int(Button.B) | int(Button.SELECT))


def test_friendly_fire_gate_holds_when_teammate_in_line():
    from ctf.beacon.action import _teammate_blocks_shot
    b = Belief(team="red", self_xy=(300, 329))
    b.teammates = (Enemy(pos=(340, 329), facing="right"),)  # between us and target
    assert _teammate_blocks_shot(b, (400, 329)) is True
    b.teammates = (Enemy(pos=(340, 380), facing="right"),)  # off the axis
    assert _teammate_blocks_shot(b, (400, 329)) is False
    b.teammates = (Enemy(pos=(340, 329), facing="right"),)  # beyond the target
    assert _teammate_blocks_shot(b, (320, 329)) is False


def test_no_fire_through_teammate():
    b = Belief(team="red", alive=True, self_xy=(300, 329), aim_brads=0, fire_ready=True)
    b.enemies = (Enemy(pos=(400, 329), facing="left"),)  # aimed dead-on east
    b.teammates = (Enemy(pos=(350, 329), facing="right"),)  # teammate in the corridor
    cmd = resolve_action(Intent(kind="hold", reason="hold_line"), b, ActionState())
    assert not (cmd.held_mask & int(Button.A))  # holds fire — would hit the teammate
    assert b.friendly_fire_suppressed == 1


def test_lighthouse_sweeps_when_no_enemy():
    b = Belief(team="red", alive=True, self_xy=(300, 329), aim_brads=0)
    st = ActionState()
    # Axis toward Blue pedestal is ~east (0); sweep should command a rotation.
    cmd = resolve_action(Intent(kind="navigate_to", point=PEDESTAL["blue"], reason="steal"), b, st)
    # Aim starts on-axis so the sweep steps off it -> a rotation button is pressed.
    assert cmd.held_mask & (int(Button.B) | int(Button.SELECT))


# --- belief memory: player tracks + danger field ------------------------------------
def _percept(enemies=(), teammates=(), self_xy=(300, 329)):
    from ctf.beacon.types import CtfState
    return CtfState(
        ready=True, self_xy=self_xy, self_facing="right", observed_aim=None,
        fire_ready=False, enemies=tuple(enemies), teammates=tuple(teammates),
        i_carry_enemy_flag=False, enemy_flag_on_pedestal=True, enemy_flag_pos=None,
        own_flag_stolen=False, own_flag_thief_pos=None,
    )


def test_track_persists_after_sighting_lost():
    from ctf.beacon.belief import update_belief
    from ctf.beacon.config import TRACK_TTL_TICKS
    b, st = Belief(team="red"), ActionState()
    update_belief(b, _percept(enemies=[Enemy(pos=(500, 300), facing="left")]), st, tick=1)
    assert len(b.enemy_tracks) == 1 and b.enemy_tracks[0].pos == (500, 300)
    # Enemy leaves the cone: the track outlives the sighting...
    update_belief(b, _percept(), st, tick=2)
    assert len(b.enemy_tracks) == 1 and b.enemy_tracks[0].last_tick == 1
    # ...until TTL, when it drops.
    update_belief(b, _percept(), st, tick=2 + TRACK_TTL_TICKS)
    assert b.enemy_tracks == []


def test_track_velocity_from_consecutive_sightings():
    from ctf.beacon.belief import update_belief
    b, st = Belief(team="red"), ActionState()
    update_belief(b, _percept(enemies=[Enemy(pos=(500, 300), facing="left")]), st, tick=1)
    assert b.enemy_tracks[0].vel is None  # one sighting can't yield a velocity
    update_belief(b, _percept(enemies=[Enemy(pos=(502, 299), facing="left")]), st, tick=2)
    t = b.enemy_tracks[0]
    assert len(b.enemy_tracks) == 1 and t.frames_seen == 2  # associated, not a new track
    assert t.vel == (2.0, -1.0)


def test_far_sighting_starts_new_track():
    from ctf.beacon.belief import update_belief
    b, st = Belief(team="red"), ActionState()
    update_belief(b, _percept(enemies=[Enemy(pos=(500, 300), facing="left")]), st, tick=1)
    # Next tick, a sighting across the map: unreachable at max speed => a second track.
    update_belief(b, _percept(enemies=[Enemy(pos=(900, 300), facing="left")]), st, tick=2)
    assert len(b.enemy_tracks) == 2


def test_teammates_tracked_separately():
    from ctf.beacon.belief import update_belief
    b, st = Belief(team="red"), ActionState()
    update_belief(b, _percept(teammates=[Enemy(pos=(320, 329), facing="right")]), st, tick=1)
    assert len(b.teammate_tracks) == 1 and b.enemy_tracks == []


def test_danger_initialized_hot_on_enemy_half_only():
    from ctf.beacon.belief import update_belief
    from ctf.beacon.config import NAV_CELL
    b, st = Belief(team="red"), ActionState()
    update_belief(b, _percept(), st, tick=1)
    grid = mapdata.walkable_grid()
    east = b.danger[:, (900 // NAV_CELL)][grid[:, (900 // NAV_CELL)]]
    west = b.danger[:, (300 // NAV_CELL)][grid[:, (300 // NAV_CELL)]]
    assert east.size and (east > 0.9).all()  # enemy (Blue) half starts hot
    assert west.size and (west == 0.0).all()  # our half starts cold


def test_danger_stamped_by_visible_enemy_and_decays():
    from ctf.beacon.belief import update_belief
    from ctf.beacon.config import NAV_CELL
    b, st = Belief(team="red"), ActionState()
    enemy_xy = (400, 329)  # on OUR (cold) half
    gx, gy = enemy_xy[0] // NAV_CELL, enemy_xy[1] // NAV_CELL
    update_belief(b, _percept(enemies=[Enemy(pos=enemy_xy, facing="left")]), st, tick=1)
    assert b.danger[gy, gx] == 1.0
    # Enemy vanishes: the hot spot decays but lingers (diffusion <1x speed).
    update_belief(b, _percept(), st, tick=2)
    assert 0.5 < b.danger[gy, gx] < 1.0


def test_danger_never_on_walls():
    from ctf.beacon.belief import update_belief
    b, st = Belief(team="red"), ActionState()
    for tick in range(1, 30):
        update_belief(b, _percept(enemies=[Enemy(pos=(617, 329), facing="left")]), st, tick=tick)
    assert (b.danger[~mapdata.walkable_grid()] == 0.0).all()


# --- perception at the 0.7.49 wire format --------------------------------------------
# The 0.7.8 renderer restore put the PLAYER stream back to 1x map pixels (spectator
# supersampling is boardScale-gated and never touches POV packets), retired the
# aim-dot indicator (self sprite id 5100+rot IS the aim readback), and split the
# flag into "<color> flag planted" (pedestal) / "<color> flag" (centered on its
# carrier). Helpers build worlds exactly as global.nim's POV branch emits them.
from ctf.beacon.config import RENDER_SCALE

_SOLDIER_CANVAS = 72
_FLAG_BANNER = 20
_PLANTED_W = 60  # FlagBannerW * PlantedFlagScale(3)
_SELF_SPRITE_BASE = 5100


def _add_player(w, obj_id, sprite_id, label, center_xy):
    """Place a soldier as the POV branch does: canvas centered on the player."""
    w.sprites[sprite_id] = SpriteDef(sprite_id, _SOLDIER_CANVAS, _SOLDIER_CANVAS, label, b"")
    w.objects[obj_id] = SpriteObject(
        obj_id,
        center_xy[0] * RENDER_SCALE - _SOLDIER_CANVAS // 2,
        center_xy[1] * RENDER_SCALE - _SOLDIER_CANVAS // 2,
        0, 0, sprite_id,
    )


def _add_flag(w, obj_id, sprite_id, label, center_xy, planted=False):
    """Place a flag sprite centered on its point (planted pedestal or carrier)."""
    size = _PLANTED_W if planted else _FLAG_BANNER
    w.sprites[sprite_id] = SpriteDef(sprite_id, size, size, label, b"")
    w.objects[obj_id] = SpriteObject(
        obj_id, center_xy[0] - size // 2, center_xy[1] - size // 2, 0, 0, sprite_id
    )


def _world_with_self(self_xy, aim_rot=0):
    w = SpriteWorld()
    _add_player(w, 10, _SELF_SPRITE_BASE + aim_rot, "self red right", self_xy)
    # Own flag safe at home by default (so own_flag_stolen doesn't trip).
    _add_flag(w, 30, 700, "red flag planted", (186, 329), planted=True)
    w.frame = 1
    return w


def _obs(w):
    return type("O", (), {"world": w, "frame": 1})()


def test_planted_enemy_flag_reads_stealable():
    w = _world_with_self((600, 329))
    _add_flag(w, 20, 701, "blue flag planted", (1049, 329), planted=True)
    st = perceive(_obs(w), "red")
    assert st.self_xy == (600, 329)
    assert st.enemy_flag_on_pedestal and not st.i_carry_enemy_flag


def test_carry_detected_when_flag_centered_on_us():
    w = _world_with_self((600, 329))
    _add_flag(w, 20, 702, "blue flag", (600, 329))  # carried: centered on carrier
    st = perceive(_obs(w), "red")
    assert st.i_carry_enemy_flag and not st.enemy_flag_on_pedestal


def test_teammate_carried_flag_is_not_our_carry():
    w = _world_with_self((600, 329))
    _add_flag(w, 20, 702, "blue flag", (400, 300))  # carried by someone far away
    st = perceive(_obs(w), "red")
    assert not st.i_carry_enemy_flag and not st.enemy_flag_on_pedestal
    assert st.enemy_flag_pos == (400, 300)


def test_own_flag_stolen_with_thief_fix():
    w = SpriteWorld()
    _add_player(w, 10, _SELF_SPRITE_BASE, "self red right", (600, 329))
    _add_flag(w, 30, 702, "red flag", (500, 300))  # our flag carried by a thief
    w.frame = 1
    st = perceive(_obs(w), "red")
    assert st.own_flag_stolen and st.own_flag_thief_pos == (500, 300)


def test_own_flag_stolen_when_absent():
    w = SpriteWorld()
    _add_player(w, 10, _SELF_SPRITE_BASE, "self red right", (600, 329))
    w.frame = 1
    st = perceive(_obs(w), "red")
    assert st.own_flag_stolen and st.own_flag_thief_pos is None


def test_enemy_players_read_at_map_scale():
    w = _world_with_self((300, 329))
    _add_player(w, 11, 3, "player blue left", (450, 300))
    st = perceive(_obs(w), "red")
    assert len(st.enemies) == 1 and st.enemies[0].pos == (450, 300)


def test_observed_aim_from_self_sprite_rotation():
    # Self sprite id 5100 + rot encodes the aim in 16-brad steps.
    st = perceive(_obs(_world_with_self((600, 329), aim_rot=4)), "red")
    assert st.observed_aim == 64  # rot 4 = north


def test_item_pickups_perceived():
    w = _world_with_self((600, 329))
    w.sprites[40] = SpriteDef(40, 10, 10, "grenade", b"")
    w.objects[40] = SpriteObject(40, 45, 45, 0, 0, 40)
    w.sprites[41] = SpriteDef(41, 26, 26, "shield", b"")
    w.objects[41] = SpriteObject(41, 37, 481, 0, 0, 41)
    st = perceive(_obs(w), "red")
    kinds = {k for k, _ in st.visible_items}
    assert kinds == {"grenade", "shield"}


def test_own_hp_and_carried_markers_read_from_overhead():
    w = _world_with_self((600, 329))
    # hp bar sits ~21px above the body centre; carried marker next to it.
    w.sprites[50] = SpriteDef(50, 14, 2, "hp 2/3", b"")
    w.objects[50] = SpriteObject(50, 593, 306, 0, 0, 50)
    w.sprites[51] = SpriteDef(51, 10, 10, "grenade carried", b"")
    w.objects[51] = SpriteObject(51, 580, 301, 0, 0, 51)
    st = perceive(_obs(w), "red")
    assert st.hp_pips == 2
    assert st.i_have_grenade and not st.i_have_shield


# --- peek-fire-duck micro (v7) -------------------------------------------------------
# Geometry anchor: the arena's first rect obstacle spans x 268-286, y 10-72 (bake_map
# _RECTS[0]), so (250, 40) and (300, 40) are on opposite sides of a wall.


def test_ray_blocked_by_wall_and_clear_in_open():
    assert not mapdata.ray_clear((250, 40), (300, 40))  # through the rect
    assert mapdata.ray_clear((560, 329), (680, 329))  # across the open center ring


def _combat_belief(**kw):
    from ctf.beacon.types import PlayerTrack
    b = Belief(team="red", alive=True, fire_ready=True, tick=100, **kw)
    return b


def test_duck_moves_behind_cover_when_gun_down():
    from ctf.beacon.action import _peek_duck_override
    from ctf.beacon.types import PlayerTrack
    # We stand west of the rect wall; a fresh threat is east of it, in the open,
    # with clear LoS to us. Gun down => duck should move us (or hold behind cover).
    b = _combat_belief()
    b.fire_ready = False
    b.self_xy = (250, 90)  # south of the rect, open ground
    b.enemy_tracks = [PlayerTrack(pos=(340, 90), last_tick=95, facing="left")]
    out = _peek_duck_override(Intent(kind="navigate_to", point=(1049, 329), reason="steal"), b)
    assert out is not None
    mask, aim = out
    assert aim is not None  # aim stays laid on the threat's arc


def test_duck_holds_still_when_already_covered():
    from ctf.beacon.action import _peek_duck_override
    from ctf.beacon.types import PlayerTrack
    b = _combat_belief()
    b.fire_ready = False
    b.self_xy = (250, 40)  # west of the rect
    b.enemy_tracks = [PlayerTrack(pos=(300, 40), last_tick=95, facing="left")]  # east of it
    out = _peek_duck_override(Intent(kind="navigate_to", point=(1049, 329), reason="steal"), b)
    assert out is not None
    mask, aim = out
    assert mask == 0  # wall already breaks the line: hold, watch the arc


def test_peek_pre_lays_aim_at_blocked_track():
    from ctf.beacon.action import _peek_duck_override
    from ctf.beacon.types import PlayerTrack
    b = _combat_belief()  # gun UP
    # Near the rect's south end (y=72): a ~2-cell sidestep south opens the line.
    b.self_xy = (250, 56)
    b.enemy_tracks = [PlayerTrack(pos=(300, 56), last_tick=90, facing="left")]  # blocked
    out = _peek_duck_override(Intent(kind="navigate_to", point=(1049, 329), reason="steal"), b)
    assert out is not None
    mask, aim = out
    assert aim is not None  # pre-laid on the blocked target
    assert mask != 0  # sidestepping toward the peek cell


def test_no_override_when_carrying_or_rushing():
    from ctf.beacon.action import _peek_duck_override
    from ctf.beacon.types import PlayerTrack
    tracks = [PlayerTrack(pos=(300, 40), last_tick=95, facing="left")]
    b = _combat_belief(i_carry_enemy_flag=True)
    b.fire_ready = False
    b.self_xy = (250, 40)
    b.enemy_tracks = tracks
    assert _peek_duck_override(Intent(kind="navigate_to", point=(150, 329), reason="carry_home"), b) is None
    # Final pedestal approach: exempt even with a fresh threat.
    b2 = _combat_belief()
    b2.fire_ready = False
    b2.self_xy = (1000, 329)  # 49px from Blue pedestal (1049, 329)
    b2.enemy_tracks = [PlayerTrack(pos=(1010, 300), last_tick=95, facing="left")]
    assert _peek_duck_override(Intent(kind="navigate_to", point=(1049, 329), reason="steal"), b2) is None


def test_micro_state_set_and_cleared_by_resolve_action():
    from ctf.beacon.types import PlayerTrack
    # Duck engages -> belief.micro == "duck"; next tick with no threat -> cleared.
    b = _combat_belief()
    b.fire_ready = False
    b.self_xy = (250, 40)
    b.enemy_tracks = [PlayerTrack(pos=(300, 40), last_tick=95, facing="left")]
    resolve_action(Intent(kind="navigate_to", point=(1049, 329), reason="steal"), b, ActionState())
    assert b.micro == "duck"
    b.enemy_tracks = []
    resolve_action(Intent(kind="navigate_to", point=(1049, 329), reason="steal"), b, ActionState())
    assert b.micro is None


def test_no_duck_from_stale_track():
    from ctf.beacon.action import _peek_duck_override
    from ctf.beacon.types import PlayerTrack
    b = _combat_belief()
    b.fire_ready = False
    b.self_xy = (250, 90)
    b.enemy_tracks = [PlayerTrack(pos=(340, 90), last_tick=10, facing="left")]  # 90 ticks stale
    assert _peek_duck_override(Intent(kind="navigate_to", point=(1049, 329), reason="steal"), b) is None


def test_corpse_is_not_a_live_player_and_we_read_dead():
    # While dead (0.7.x: fog does NOT lift), our own body is labeled "corpse ...",
    # so self is not found -> not ready/alive; and a corpse never counts as an enemy.
    w = SpriteWorld()
    _add_player(w, 10, 1, "corpse red right", (300, 329))
    _add_flag(w, 20, 701, "blue flag planted", (1049, 329), planted=True)
    _add_flag(w, 21, 700, "red flag planted", (186, 329), planted=True)
    w.frame = 1
    st = perceive(_obs(w), "red")
    assert not st.ready and st.self_xy is None
    assert st.enemies == () and st.teammates == ()
    # Pedestal hearts stay readable through death (they never fog).
    assert st.enemy_flag_on_pedestal and not st.own_flag_stolen


# --- v10: lead aim -------------------------------------------------------------------


def test_lead_aim_extrapolates_along_velocity():
    from ctf.beacon.action import _lead_aim_pos
    from ctf.beacon.config import LEAD_TICKS
    from ctf.beacon.types import PlayerTrack

    b = Belief(team="red", alive=True, tick=100, self_xy=(300, 329))
    enemy = Enemy(pos=(500, 329), facing="left")
    # A settled track moving straight down at 2 px/tick, seen this tick.
    b.enemy_tracks = [
        PlayerTrack(pos=(500, 329), last_tick=100, facing="left", vel=(0.0, 2.0), frames_seen=5)
    ]
    aim_pos, lead = _lead_aim_pos(b, enemy)
    assert aim_pos == (500, 329 + round(2.0 * LEAD_TICKS))
    assert lead != 0


def test_lead_aim_declines_thin_tracks():
    from ctf.beacon.action import _lead_aim_pos
    from ctf.beacon.types import PlayerTrack

    b = Belief(team="red", alive=True, tick=100, self_xy=(300, 329))
    enemy = Enemy(pos=(500, 329), facing="left")
    b.enemy_tracks = [
        PlayerTrack(pos=(500, 329), last_tick=100, facing="left", vel=(0.0, 2.0), frames_seen=2)
    ]
    aim_pos, lead = _lead_aim_pos(b, enemy)
    assert aim_pos == enemy.pos and lead == 0


# --- v10: items ----------------------------------------------------------------------


def test_spawn_table_matches_sim_formulas():
    # Mirror sim.nim: inset = ArenaBorder(10) + GrenadeSpawnInset(40) = 50.
    from ctf.beacon.config import ARC_SPAWNS, GRENADE_SPAWNS, MEDKIT_SPAWNS, SHIELD_SPAWNS

    assert GRENADE_SPAWNS == ((50, 50), (50, 609), (1185, 50), (1185, 609))
    assert SHIELD_SPAWNS == ((50, 494), (1185, 494))
    assert ARC_SPAWNS == ((50, 164), (1185, 164))
    assert MEDKIT_SPAWNS == ((617, 219), (617, 439))


def test_convenience_uses_marginal_route_cost():
    from ctf.beacon import items

    b = Belief(team="red", seat=0, alive=True, tick=10, self_xy=(600, 300), hp_pips=1)
    b.item_spawns = items.build_spawn_table()
    choice = items.evaluate_fetch(b, (1049, 329), anchor_kind="role")
    assert choice is not None
    assert choice.spawn.kind == "medkit"
    assert choice.accepted
    assert choice.detour_px <= choice.threshold_px
    assert choice.route_via_item_px >= choice.route_to_item_px


def test_route_distance_is_finite_and_symmetric():
    from ctf.beacon import nav

    start = (100, 100)
    goal = (1049, 329)
    forward = nav.route_distance(start, goal)
    reverse = nav.route_distance(goal, start)
    assert math.isfinite(forward)
    assert forward == pytest.approx(reverse)


def test_settled_post_rejects_a_long_item_excursion():
    from ctf.beacon import items

    b = Belief(team="red", seat=2, alive=True, tick=10, self_xy=(200, 329), hp_pips=3)
    b.item_spawns = items.build_spawn_table()
    choice = items.evaluate_fetch(b, b.self_xy, anchor_kind="post")
    assert choice is not None
    assert not choice.accepted
    assert choice.reason == "too_far"
    assert choice.threshold_px == 48


def test_respawn_bonus_makes_a_corner_grenade_convenient():
    from ctf.beacon import items

    b = Belief(team="red", seat=2, alive=True, tick=10, self_xy=(100, 100), hp_pips=3)
    b.item_spawns = items.build_spawn_table()
    choice = items.evaluate_fetch(
        b,
        (1049, 329),
        anchor_kind="rejoin",
        respawning=True,
    )
    assert choice is not None
    assert choice.spawn.kind == "grenade"
    assert choice.spawn.pos == (50, 50)
    assert choice.accepted
    assert choice.threshold_px == 288


def test_fresh_respawn_fetches_corner_item_with_squads_disabled(monkeypatch):
    from ctf.beacon import items, strategy

    monkeypatch.setattr(strategy, "SQUAD_COMMAND", False)
    monkeypatch.setattr(strategy, "ITEM_CONVENIENCE", True)
    b = Belief(
        team="red",
        seat=0,
        role="attacker",
        alive=True,
        tick=100,
        respawned_tick=100,
        self_xy=(100, 100),
        hp_pips=3,
    )
    b.item_spawns = items.build_spawn_table()
    intent, flow = strategy.decide_objective(b)
    assert intent.kind == "navigate_to"
    assert intent.point == (50, 50)
    assert intent.reason == "fetch_item"
    assert flow is None


def test_active_convenience_preserves_legacy_assignment(monkeypatch):
    from ctf.beacon import items, strategy

    monkeypatch.setattr(strategy, "ITEM_CONVENIENCE", True)
    b = Belief(
        team="red",
        seat=2,
        role="attacker",
        alive=True,
        tick=100,
        respawned_tick=100,
        self_xy=(100, 100),
        hp_pips=3,
    )
    b.item_spawns = items.build_spawn_table()
    intent, flow = strategy.decide_objective(b)
    assert intent.point == (50, 494)
    assert intent.reason == "fetch_item"
    assert flow is None


def test_incidental_fetch_rejects_nonlegacy_grenade_beyond_route_cap():
    from ctf.beacon import items

    b = Belief(
        team="red",
        seat=0,
        alive=True,
        tick=500,
        self_xy=(150, 100),
        hp_pips=3,
    )
    b.item_spawns = items.build_spawn_table()
    choice = items.evaluate_fetch(
        b,
        (1049, 329),
        anchor_kind="role",
        incidental_only=True,
    )
    assert choice is not None
    assert not choice.accepted
    assert choice.reason == "too_far"


def test_shadow_convenience_preserves_legacy_item_assignment(monkeypatch):
    from ctf.beacon import items, strategy

    monkeypatch.setattr(strategy, "ITEM_CONVENIENCE", False)
    b = Belief(
        team="red",
        seat=3,
        role="attacker",
        alive=True,
        tick=105,
        self_xy=(100, 100),
        hp_pips=3,
    )
    b.item_spawns = items.build_spawn_table()
    intent, flow = strategy.decide_objective(b)
    assert intent.point == (50, 50)
    assert intent.reason == "fetch_item"
    assert flow is None
    assert b.item_options


def test_item_anchor_does_not_advance_plan_buddy_wait(monkeypatch):
    from types import SimpleNamespace

    from ctf.beacon import strategy

    order = SimpleNamespace(
        kind="move",
        target="enemy_pedestal",
        fallback=None,
    )
    book = SimpleNamespace(
        group_of=lambda seat, phase: "push",
        primary_order=lambda group, phase: order,
    )
    monkeypatch.setattr(strategy, "PLAN_NAME", "test")
    monkeypatch.setattr(
        strategy._plan.PlanBook,
        "load",
        lambda name: book,
    )
    monkeypatch.setattr(
        strategy.poi,
        "resolve",
        lambda target, team: (1049, 329),
    )
    b = Belief(
        team="red",
        seat=3,
        alive=True,
        self_xy=(400, 329),
        plan_buddy_wait_ticks=17,
    )
    assert strategy._item_anchor(b, "blue") == ((1049, 329), "plan")
    assert b.plan_buddy_wait_ticks == 17


def test_unassigned_shield_and_distant_spray_wait_for_tactical_doctrine():
    from ctf.beacon import items

    b = Belief(
        team="red",
        seat=0,
        alive=True,
        tick=10,
        self_xy=(100, 329),
        hp_pips=3,
    )
    b.item_spawns = items.build_spawn_table()
    items.evaluate_fetch(b, (1049, 329), anchor_kind="role")
    gated = [
        option
        for option in b.item_options
        if option.spawn.kind in ("shield", "arc")
    ]
    assert gated
    assert all(not option.accepted for option in gated)
    assert all(option.reason == "tactics_not_ready" for option in gated)


def test_legacy_item_owner_only_gets_its_own_side_assignment():
    from ctf.beacon import items

    b = Belief(
        team="red",
        seat=2,
        alive=True,
        tick=10,
        self_xy=(200, 329),
        hp_pips=3,
    )
    b.item_spawns = items.build_spawn_table()
    items.evaluate_fetch(b, (1049, 329), anchor_kind="role")
    shields = [
        option for option in b.item_options if option.spawn.kind == "shield"
    ]
    own = next(option for option in shields if option.spawn.pos[0] < 617)
    enemy = next(option for option in shields if option.spawn.pos[0] > 617)
    assert own.threshold_px == 420
    assert enemy.reason == "tactics_not_ready"


def test_visible_closer_teammate_wins_item_contention():
    from ctf.beacon import items

    b = Belief(
        team="red",
        seat=2,
        alive=True,
        tick=10,
        self_xy=(100, 100),
        hp_pips=3,
        teammates=(Enemy(pos=(50, 50), facing="right"),),
    )
    b.item_spawns = items.build_spawn_table()
    choice = items.evaluate_fetch(b, (1049, 329), anchor_kind="role")
    grenade = next(
        option
        for option in b.item_options
        if option.spawn.kind == "grenade" and option.spawn.pos == (50, 50)
    )
    assert not grenade.accepted
    assert grenade.reason == "closer_teammate"
    assert choice is not None


def test_equidistant_teammates_choose_exactly_one_item_pursuer():
    from ctf.beacon import items

    left = Belief(
        team="red",
        seat=2,
        alive=True,
        tick=10,
        self_xy=(40, 60),
        hp_pips=3,
        teammates=(Enemy(pos=(60, 40), facing="right"),),
    )
    right = Belief(
        team="red",
        seat=3,
        alive=True,
        tick=10,
        self_xy=(60, 40),
        hp_pips=3,
        teammates=(Enemy(pos=(40, 60), facing="right"),),
    )
    for belief in (left, right):
        belief.item_spawns = items.build_spawn_table()
        items.evaluate_fetch(
            belief,
            (1049, 329),
            anchor_kind="role",
            respawning=True,
        )
    left_grenade = next(
        option
        for option in left.item_options
        if option.spawn.kind == "grenade" and option.spawn.pos == (50, 50)
    )
    right_grenade = next(
        option
        for option in right.item_options
        if option.spawn.kind == "grenade" and option.spawn.pos == (50, 50)
    )
    assert left_grenade.accepted != right_grenade.accepted


def test_absent_spawn_backs_off_then_recovers():
    from ctf.beacon import items
    from ctf.beacon.config import SHIELD_RESPAWN_TICKS
    from ctf.beacon.types import CtfState

    b = Belief(team="red", seat=0, alive=True, tick=100, aim_brads=180)
    b.item_spawns = items.build_spawn_table()
    shield = next(s for s in b.item_spawns if s.kind == "shield" and s.pos[0] < 617)
    # Stand near the shield spawn looking at it, with NO shield sighting -> absent.
    b.self_xy = (shield.pos[0] + 40, shield.pos[1])
    percept = CtfState(
        ready=True, self_xy=b.self_xy, self_facing="left", observed_aim=None,
        fire_ready=True, enemies=(), teammates=(), i_carry_enemy_flag=False,
        enemy_flag_on_pedestal=True, enemy_flag_pos=None, own_flag_stolen=False,
        own_flag_thief_pos=None, visible_items=(),
    )
    items.update_items(b, percept)
    assert not shield.present
    # After the respawn back-off it turns optimistic again.
    b.tick = 100 + SHIELD_RESPAWN_TICKS
    b.self_xy = (300, 100)  # far away, not looking
    items.update_items(b, percept)
    assert shield.present


def test_medkit_fetch_only_when_hurt():
    from ctf.beacon import items

    b = Belief(team="red", seat=0, alive=True, tick=10, self_xy=(600, 300))
    b.item_spawns = items.build_spawn_table()
    b.hp_pips = 3
    items.evaluate_fetch(b, (1049, 329), anchor_kind="role")
    assert all(option.spawn.kind != "medkit" for option in b.item_options)
    b.hp_pips = 1
    choice = items.evaluate_fetch(b, (1049, 329), anchor_kind="role")
    assert choice is not None and choice.spawn.kind == "medkit"


def test_grenade_charge_holds_c_and_mask_survives():
    # The C press (bit 128) must survive resolve_action's mask clamp.
    from ctf.beacon.config import BUTTON_C
    from ctf.beacon.types import PlayerTrack

    b = Belief(team="red", alive=True, fire_ready=True, tick=100, self_xy=(250, 40))
    b.i_have_grenade = True
    # A fresh wall-blocked track east of the rect obstacle (see peek/duck tests),
    # beyond GRENADE_MIN_THROW_PX so the lob is worth it.
    b.enemy_tracks = [
        PlayerTrack(pos=(350, 40), last_tick=98, facing="left", vel=None, frames_seen=4)
    ]
    cmd = resolve_action(Intent(kind="hold", reason="hold_line"), b, ActionState())
    assert cmd.held_mask & BUTTON_C
    assert b.throw_charge_ticks == 1


def test_fire_freezes_movement_through_windup():
    # Firing must drop movement bits on the trigger tick and hold them for the
    # windup, so the bullet leaves from where the aim was laid.
    b = Belief(team="red", alive=True, fire_ready=True, tick=100, self_xy=(300, 329))
    b.aim_brads = 0
    b.enemies = (Enemy(pos=(400, 329), facing="left"),)  # due east, on-aim
    st = ActionState()
    cmd = resolve_action(Intent(kind="navigate_to", point=(1049, 329), reason="steal"), b, st)
    assert cmd.held_mask & int(Button.A)
    assert not cmd.held_mask & (int(Button.UP) | int(Button.DOWN) | int(Button.LEFT) | int(Button.RIGHT))
    assert st.fire_hold_ticks == 5
    # Next tick (gun now down): still frozen while the windup runs.
    b.fire_ready = False
    b.enemies = ()
    cmd2 = resolve_action(Intent(kind="navigate_to", point=(1049, 329), reason="steal"), b, st)
    assert not cmd2.held_mask & (int(Button.UP) | int(Button.DOWN) | int(Button.LEFT) | int(Button.RIGHT))
    assert st.fire_hold_ticks == 4


# --- v16: hearing ----------------------------------------------------------------


def test_sound_rings_perceived():
    w = _world_with_self((600, 329))
    w.sprites[60] = SpriteDef(60, 16, 16, "shot impact", b"")
    w.objects[60] = SpriteObject(60, 392, 292, 0, 0, 60)
    w.sprites[61] = SpriteDef(61, 16, 16, "grenade sound", b"")
    w.objects[61] = SpriteObject(61, 692, 392, 0, 0, 61)
    st = perceive(_obs(w), "red")
    kinds = sorted(k for k, _ in st.heard_impacts)
    assert kinds == ["grenade", "shot"]


def test_heard_events_dedup_and_expire():
    from ctf.beacon.belief import _update_heard
    from ctf.beacon.config import HEARD_TTL_TICKS
    from ctf.beacon.types import CtfState

    def percept(impacts):
        return CtfState(
            ready=True, self_xy=(600, 329), self_facing="right", observed_aim=None,
            fire_ready=True, enemies=(), teammates=(), i_carry_enemy_flag=False,
            enemy_flag_on_pedestal=True, enemy_flag_pos=None, own_flag_stolen=False,
            own_flag_thief_pos=None, heard_impacts=impacts,
        )

    b = Belief(team="red", alive=True, self_xy=(600, 329))
    # Same ring sighted twice (stable jittered position) -> ONE event.
    _update_heard(b, percept((("shot", (400, 300)),)), tick=100)
    _update_heard(b, percept((("shot", (400, 300)),)), tick=101)
    assert len(b.heard_events) == 1 and b.heard_events[0].first_tick == 100
    # A distinct landing far away -> a second event.
    _update_heard(b, percept((("shot", (700, 300)),)), tick=102)
    assert len(b.heard_events) == 2
    # Expiry after TTL from last sighting.
    _update_heard(b, percept(()), tick=101 + HEARD_TTL_TICKS + 1)
    assert len(b.heard_events) == 1  # only the 102 event survives


def test_heard_impact_triggers_duck_when_gun_down():
    from ctf.beacon.action import _peek_duck_override
    from ctf.beacon.types import HeardImpact

    b = Belief(team="red", alive=True, fire_ready=False, tick=100, self_xy=(250, 90))
    b.aim_brads = 0  # aiming east
    # Fresh impact NORTH of us (off our aim line), within duck range.
    b.heard_events = [HeardImpact(kind="shot", pos=(250, 30), first_tick=95, last_tick=100)]
    out = _peek_duck_override(Intent(kind="navigate_to", point=(1049, 329), reason="steal"), b)
    assert out is not None and b.micro == "duck" and b.heard_duck


def test_own_fire_landing_does_not_trigger_duck():
    from ctf.beacon.action import _fresh_heard_impact
    from ctf.beacon.types import HeardImpact

    b = Belief(team="red", alive=True, fire_ready=False, tick=100, self_xy=(250, 90))
    b.aim_brads = 0  # aiming east
    # An impact due east ON our aim ray = probably our own shot landing.
    b.heard_events = [HeardImpact(kind="shot", pos=(360, 90), first_tick=98, last_tick=100)]
    assert _fresh_heard_impact(b) is None


def test_heard_impact_stamps_danger():
    from ctf.beacon.belief import update_belief
    from ctf.beacon.config import HEARD_DANGER_HEAT, NAV_CELL
    from ctf.beacon.types import CtfState

    b = Belief(team="red", seat=0, alive=True, self_xy=(600, 329))
    st = ActionState()
    percept = CtfState(
        ready=True, self_xy=(600, 329), self_facing="right", observed_aim=None,
        fire_ready=True, enemies=(), teammates=(), i_carry_enemy_flag=False,
        enemy_flag_on_pedestal=True, enemy_flag_pos=None, own_flag_stolen=False,
        own_flag_thief_pos=None, heard_impacts=(("shot", (560, 329)),),
    )
    update_belief(b, percept, st, tick=1)
    gx, gy = 560 // NAV_CELL, 329 // NAV_CELL
    assert b.danger is not None and b.danger[gy, gx] >= HEARD_DANGER_HEAT - 1e-6


# --- v18: chat --------------------------------------------------------------------


def _chat_percept(**kw):
    from ctf.beacon.types import CtfState
    base = dict(
        ready=True, self_xy=(600, 329), self_facing="right", observed_aim=None,
        fire_ready=True, enemies=(), teammates=(), i_carry_enemy_flag=False,
        enemy_flag_on_pedestal=True, enemy_flag_pos=None, own_flag_stolen=False,
        own_flag_thief_pos=None,
    )
    base.update(kw)
    return CtfState(**base)


def test_chat_codec_roundtrip():
    from ctf.beacon import chat
    for kind in ("enemy", "under_fire", "grenade", "thief"):
        code = chat.encode(kind, (487, 315))
        assert len(code) <= 10
        msg = chat.decode(code)
        assert msg.kind == kind
        # cell-quantized: within one nav cell
        assert abs(msg.pos[0] - 487) <= 8 and abs(msg.pos[1] - 315) <= 8
    code = chat.encode("carrier", (1049, 329), heading=5)
    msg = chat.decode(code)
    assert msg.kind == "carrier" and msg.heading == 5


def test_chat_decode_rejects_garbage():
    from ctf.beacon import chat
    assert chat.decode("") is None
    assert chat.decode("hello") is None
    assert chat.decode("Ezz~~") is None  # out-of-range cell
    assert chat.decode("X0000") is None  # unknown type


def test_carrier_heartbeat_wins_priority():
    from ctf.beacon.chat import choose_shout
    b = Belief(team="red", alive=True, tick=1000, self_xy=(700, 300))
    b.i_carry_enemy_flag = True
    b.enemies = (Enemy(pos=(750, 300), facing="left"),)  # would also be an E
    shout = choose_shout(b)
    assert shout is not None and shout.startswith("C")
    assert b.chat_sent_counts.get("carrier") == 1


def test_enemy_shout_edge_trigger_and_rearm():
    from ctf.beacon.chat import choose_shout
    from ctf.beacon.config import CHAT_ENEMY_REARM_TICKS, CHAT_MIN_INTERVAL_TICKS
    b = Belief(team="red", alive=True, tick=1000, self_xy=(600, 329))
    b.enemies = (Enemy(pos=(700, 329), facing="left"),)
    assert choose_shout(b) is not None  # first sighting -> E
    b.tick += CHAT_MIN_INTERVAL_TICKS + 1
    assert choose_shout(b) is None  # not re-armed: enemy still in view
    # Enemy leaves vision; wait past re-arm, then a NEW sighting fires again.
    b.enemies = ()
    for _ in range(CHAT_ENEMY_REARM_TICKS + 2):
        b.tick += 1
        choose_shout(b)
    b.enemies = (Enemy(pos=(700, 329), facing="left"),)
    b.tick += 1
    assert choose_shout(b) is not None


def test_shout_bubbles_perceived_and_parsed():
    w = _world_with_self((600, 329))
    w.sprites[70] = SpriteDef(70, 40, 12, "red shout James Boggs (3): T4c95", b"")
    w.objects[70] = SpriteObject(70, 480, 294, 0, 0, 70)
    st = perceive(_obs(w), "red")
    assert len(st.heard_shouts) == 1
    team, addr, text, pos = st.heard_shouts[0]
    assert team == "red" and addr == "James Boggs (3)" and text == "T4c95"


def test_teammate_thief_shout_sets_fix_and_intercept():
    from ctf.beacon.belief import update_belief
    from ctf.beacon import chat
    b = Belief(team="red", seat=7, role="attacker", alive=True, self_xy=(300, 329))
    st = ActionState()
    code = chat.encode("thief", (500, 300))
    update_belief(b, _chat_percept(
        own_flag_stolen=True,
        heard_shouts=(("red", "mate (2)", code, (505, 305)),),
    ), st, tick=10)
    assert b.thief_fix is not None
    intent, _ = decide_objective(b)
    assert intent.reason == "intercept_thief_heard"
    # And the fix created an enemy track too.
    assert any(t.last_tick == 10 for t in b.enemy_tracks)


def test_carrier_shout_drives_escort_with_heading_projection():
    from ctf.beacon.belief import update_belief
    from ctf.beacon import chat
    b = Belief(team="red", seat=7, role="attacker", alive=True, self_xy=(300, 329))
    st = ActionState()
    code = chat.encode("carrier", (700, 300), heading=4)  # heading west (home for red)
    update_belief(b, _chat_percept(
        enemy_flag_on_pedestal=False,
        heard_shouts=(("red", "mate (4)", code, (700, 300)),),
    ), st, tick=10)
    assert b.carrier_fix is not None
    b.tick = 34  # 24 ticks later
    intent, _ = decide_objective(b)
    assert intent.reason == "escort_carrier_heard"
    assert intent.point[0] < 700  # projected west along the shouted heading


def test_grenade_warning_clears_teammates():
    from ctf.beacon.belief import update_belief
    from ctf.beacon import chat
    b = Belief(team="red", seat=7, role="attacker", alive=True, self_xy=(600, 329))
    st = ActionState()
    code = chat.encode("grenade", (610, 329))  # landing basically on us
    update_belief(b, _chat_percept(
        heard_shouts=(("red", "mate (6)", code, (610, 329)),),
    ), st, tick=10)
    intent, _ = decide_objective(b)
    assert intent.reason == "clear_grenade"
    # Flee point is away from the landing cell.
    assert intent.point[0] < 600 or abs(intent.point[1] - 329) > 40


def test_enemy_bubble_is_position_fix_not_payload():
    from ctf.beacon.belief import update_belief
    b = Belief(team="red", seat=0, alive=True, self_xy=(600, 329))
    st = ActionState()
    # A BLUE shout claiming a thief at some cell: do NOT set thief_fix; DO track
    # the bubble position as an enemy fix.
    update_belief(b, _chat_percept(
        heard_shouts=(("blue", "foe (1)", "T4c95", (800, 400)),),
    ), st, tick=10)
    assert b.thief_fix is None
    assert any(t.pos == (800, 400) for t in b.enemy_tracks)


def test_same_bubble_processed_once():
    from ctf.beacon.belief import update_belief
    b = Belief(team="red", seat=0, alive=True, self_xy=(600, 329))
    st = ActionState()
    from ctf.beacon import chat
    code = chat.encode("under_fire", (500, 300))
    shout = (("red", "mate (2)", code, (505, 305)),)
    update_belief(b, _chat_percept(heard_shouts=shout), st, tick=10)
    update_belief(b, _chat_percept(heard_shouts=shout), st, tick=11)
    assert b.chat_heard_counts.get("under_fire") == 1


def test_under_fire_set_by_nearby_fresh_impact():
    from ctf.beacon.belief import update_belief
    b = Belief(team="red", seat=0, alive=True, self_xy=(600, 329))
    st = ActionState()
    update_belief(b, _chat_percept(heard_impacts=(("shot", (630, 329)),)), st, tick=10)
    assert b.under_fire
    update_belief(b, _chat_percept(), st, tick=100)  # stale now
    assert not b.under_fire


# --- v19: squads --------------------------------------------------------------------


def test_squad_membership_covers_all_seats_deterministically():
    from ctf.beacon import squads
    seen = {}
    for seat in range(8):
        name, seats = squads.squad_of(seat)
        assert seat in seats
        assert squads.rank_of(seat) == seats.index(seat)
        seen.setdefault(name, set()).add(seat)
    assert seen == {"A": {0, 1, 2}, "C": {3, 4}, "B": {5, 6, 7}}


def test_sector_offsets_spread_by_rank():
    from ctf.beacon import squads
    from ctf.beacon.config import SQUAD_SECTOR_BRADS
    # D squad seats 0,1,2 -> ranks 0,1,2 -> offsets 0, +S, -S.
    assert squads.sector_offset_brads(0) == 0
    assert squads.sector_offset_brads(1) == SQUAD_SECTOR_BRADS
    assert squads.sector_offset_brads(2) == -SQUAD_SECTOR_BRADS


def test_separation_pushes_apart_cohesion_pulls_together():
    from ctf.beacon import squads
    b = Belief(team="red", seat=5, alive=True, tick=100, self_xy=(400, 300))
    # Teammate on top of us -> separation (points away).
    b.teammates = (Enemy(pos=(410, 300), facing="left"),)
    bias = squads.formation_bias(b)
    assert bias is not None and bias[0] < 0
    # Teammate far away, nobody near -> cohesion (points toward).
    b.teammates = (Enemy(pos=(700, 300), facing="left"),)
    bias = squads.formation_bias(b)
    assert bias is not None and bias[0] > 0


def test_spread_point_fans_squad_across_lane():
    from ctf.beacon import squads
    from ctf.beacon.config import SQUAD_SPREAD_PX
    # Squad A = seats 0,1,2 share one order point; spread must give 3 distinct
    # points, rank 0 on the anchor, ranks 1/2 offset ~SPREAD_PX up/down (the
    # exact y may snap to the nearest cover cell).
    anchor = (390, 165)
    pts = [squads.spread_point(seat, anchor) for seat in (0, 1, 2)]
    assert len(set(pts)) == 3
    assert pts[0] == anchor  # rank 0 holds the anchor itself
    offsets = sorted(p[1] - anchor[1] for p in pts)
    assert offsets[0] < -SQUAD_SPREAD_PX // 2  # one member well above
    assert offsets[-1] > SQUAD_SPREAD_PX // 2  # one member well below


def test_spread_point_clamps_on_map():
    from ctf.beacon import squads
    # An anchor at the map edge must not push a member off-map.
    for seat in (0, 1, 2):
        x, y = squads.spread_point(seat, (390, 10))
        assert 0 <= y <= 658


def test_team_scores_parse_from_scoreboard_labels():
    w = _world_with_self((600, 329))
    w.sprites[90] = SpriteDef(90, 40, 8, "team score RED 12/9", b"")
    w.objects[90] = SpriteObject(90, 500, 1, 0, 11, 90)
    w.sprites[91] = SpriteDef(91, 40, 8, "team score BLUE 9/18", b"")
    w.objects[91] = SpriteObject(91, 560, 1, 0, 11, 91)
    st = perceive(_obs(w), "red")
    assert st.own_team_score == (12, 9)
    assert st.enemy_team_score == (9, 18)


def test_enemy_lives_left_derives_from_deaths():
    from ctf.beacon import squads
    b = Belief(team="red", seat=0, alive=True, tick=100, self_xy=(400, 300))
    assert squads.enemy_lives_left(b) is None  # no scoreboard read yet
    b.enemy_team_score = (9, 18)  # 18 enemy deaths
    assert squads.enemy_lives_left(b) == 6  # 24 - 18
    assert squads.wipe_in_reach(b)  # <= CONVERT_ENEMY_LIVES (6)
    b.enemy_team_score = (9, 10)
    assert squads.enemy_lives_left(b) == 14
    assert not squads.wipe_in_reach(b)


def test_leader_orders_convert_hunt_when_wipe_in_reach():
    from ctf.beacon import squads
    # Seat 0 leads squad A; enemy down to 5 lives -> T order, not the default H.
    b = Belief(team="red", seat=0, role="defender", alive=True, tick=500,
               self_xy=(390, 165))
    b.enemy_team_score = (0, 19)
    squads.lead_squad(b)
    assert b.order is not None and b.order[0] == "T"
    assert b.convert_events == 1
    # Enemy at full strength -> the default side-hold, no convert.
    b2 = Belief(team="red", seat=0, role="defender", alive=True, tick=500,
                self_xy=(390, 165))
    b2.enemy_team_score = (0, 2)
    squads.lead_squad(b2)
    assert b2.order is not None and b2.order[0] == "H"
    assert b2.convert_events == 0


def test_order_decay_converts_instead_of_backing_off_when_wipe_in_reach(squads_on):
    from ctf.beacon.config import ORDER_TTL_TICKS
    # A member (non-leader seat 1) with a STALE order and the wipe in reach must
    # flip to T (hunt), not the v24 backoff-hold.
    b = Belief(team="red", seat=1, role="defender", alive=True,
               tick=1000 + ORDER_TTL_TICKS + 1, self_xy=(600, 300))
    b.order = ("P", (617, 329), 1000)  # stale
    b.enemy_team_score = (0, 20)  # 4 enemy lives left
    intent, _ = decide_objective(b)
    assert b.order[0] == "T"
    assert intent.reason == "order_hunt"


# --- v30: POI loader + battle-plan interpreter --------------------------------------


def test_poi_resolves_names_and_mirrors():
    from ctf.beacon import poi
    assert poi.point("red_pedestal") == (186, 329)
    # Blue frame: prefix-swap when the twin exists…
    assert poi.point("red_rally_top", "blue") == poi.point("blue_rally_top")
    # …and geometric mirror for side-neutral names.
    nm = poi.point("north_medkit")
    assert poi.point("north_medkit", "blue") == nm  # medkit is on the mirror line
    assert poi.resolve({"x": 100, "y": 200}, "blue") == (1134, 200)
    assert poi.resolve("no_such_poi") is None
    assert poi.area("center_ring").contains(617, 329)


def test_plan_book_groups_and_splits():
    from ctf.beacon.plan import PlanBook
    book = PlanBook.load("staged_push_top")
    assert book is not None and len(book.phases) == 4
    g0 = book.groups_at(0)
    assert set(g0) == {"pushers", "rear"}
    g2 = book.groups_at(2)  # phase 3 splits pushers -> flank_n/flank_s
    assert set(g2) == {"rear", "flank_n", "flank_s"}
    assert book.group_of(3, 0) == "pushers"
    assert book.group_of(3, 2) == "flank_n"
    assert book.group_of(0, 2) == "rear"


def test_plan_objective_drives_intent_and_emergencies_preempt():
    from ctf.beacon import poi
    # Seat 3 (pushers) at spawn in phase 0: plan sends it toward red_rally_top.
    b = Belief(team="red", seat=3, role="attacker", alive=True, tick=50,
               self_xy=(110, 329))
    intent, _ = decide_objective(b)
    assert intent.reason == "plan_move"
    assert intent.point == poi.point("red_rally_top")
    # Carrying the flag preempts the plan entirely.
    b2 = Belief(team="red", seat=3, role="attacker", alive=True, tick=50,
                self_xy=(110, 329), i_carry_enemy_flag=True)
    intent2, flow = decide_objective(b2)
    assert intent2.reason == "carry_home" and flow == "home"
    # Convert trigger preempts the plan too.
    b3 = Belief(team="red", seat=3, role="attacker", alive=True, tick=50,
                self_xy=(110, 329))
    b3.enemy_team_score = (0, 20)  # 4 enemy lives -> wipe in reach
    intent3, _ = decide_objective(b3)
    assert intent3.reason == "convert_hunt"


def test_plan_phase_advances_on_milestone_and_timeout():
    from ctf.beacon import plan as planmod, poi
    from ctf.beacon.config import PLAN_PHASE_TIMEOUT_TICKS
    book = planmod.PlanBook.load("staged_push_top")
    # Milestone: seat 3 standing on its phase-0 target advances to phase 1.
    b = Belief(team="red", seat=3, role="attacker", alive=True, tick=100,
               self_xy=poi.point("red_rally_top"))
    planmod.advance(b, book)
    assert b.plan_phase == 1 and b.plan_milestone_hit
    # Timeout: far from any target, but the phase clock expires -> advance.
    b2 = Belief(team="red", seat=3, role="attacker", alive=True,
                tick=PLAN_PHASE_TIMEOUT_TICKS + 5, self_xy=(110, 329))
    planmod.advance(b2, book)
    assert b2.plan_phase == 1 and not b2.plan_milestone_hit
    # No advance when neither holds.
    b3 = Belief(team="red", seat=3, role="attacker", alive=True, tick=100,
                self_xy=(110, 329))
    planmod.advance(b3, book)
    assert b3.plan_phase == 0


def test_plan_hold_fallback_trips_under_fire():
    from ctf.beacon import plan as planmod, poi
    book = planmod.PlanBook.load("staged_push_top")
    # Seat 0 (rear) in phase 3 holds at (323,333) with fallback red_lineup.
    b = Belief(team="red", seat=0, role="defender", alive=True, tick=2000,
               self_xy=(323, 333))
    b.plan_phase = 2
    b.under_fire = True
    b.enemies = (Enemy(pos=(400, 340), facing="left"), Enemy(pos=(410, 320), facing="left"))
    kind, xy, order = planmod.current_objective(b, book)
    assert b.plan_fell_back
    assert xy == poi.point("red_lineup")  # retreat target, not the forward hold


def test_plan_buddy_wait_gates_dangerous_solo_pushes():
    from ctf.beacon import plan as planmod
    from ctf.beacon.config import PLAN_BUDDY_WAIT_TICKS
    book = planmod.PlanBook.load("staged_push_top")
    # Phase 3, seat 3 = flank_n (2 seats): its move target (802,27) is on the
    # enemy half -> dangerous. Alone (no teammate evidence): buddy-wait holds.
    b = Belief(team="red", seat=3, role="attacker", alive=True, tick=2000,
               self_xy=(630, 60))
    b.plan_phase = 2
    kind, xy, _ = planmod.current_objective(b, book)
    assert b.plan_buddy_waiting and kind == "hold" and xy == (630, 60)
    # With its flank buddy (seat 4) visible nearby: pushes.
    b2 = Belief(team="red", seat=3, role="attacker", alive=True, tick=2000,
                self_xy=(630, 60))
    b2.plan_phase = 2
    b2.teammates = (Enemy(pos=(660, 70), facing="right", identity=4),)
    kind2, xy2, _ = planmod.current_objective(b2, book)
    assert kind2 == "move" and not b2.plan_buddy_waiting
    # Wait budget exhausted: pushes alone (no deadlock — the v19 lesson).
    b3 = Belief(team="red", seat=3, role="attacker", alive=True, tick=2000,
                self_xy=(630, 60))
    b3.plan_phase = 2
    b3.plan_buddy_wait_ticks = PLAN_BUDDY_WAIT_TICKS
    kind3, _, _ = planmod.current_objective(b3, book)
    assert kind3 == "move"
    # A non-dangerous move (own half, phase 0) never waits.
    b4 = Belief(team="red", seat=3, role="attacker", alive=True, tick=50,
                self_xy=(110, 329))
    kind4, _, _ = planmod.current_objective(b4, book)
    assert kind4 == "move" and not b4.plan_buddy_waiting


def test_plan_blue_frame_mirrors_targets():
    from ctf.beacon import plan as planmod, poi
    book = planmod.PlanBook.load("staged_push_top")
    b = Belief(team="blue", seat=3, role="attacker", alive=True, tick=50,
               self_xy=(1124, 329))
    kind, xy, _ = planmod.current_objective(b, book)
    # Phase 0 pushers -> red_rally_top; in blue's frame that's blue_rally_top.
    assert xy == poi.point("blue_rally_top")


def test_ordered_hold_uses_spread_point(squads_on):
    from ctf.beacon import squads
    # Two members of squad A obeying the same H order must navigate to
    # DIFFERENT points (the v24 stacking root cause).
    points = {}
    for seat in (1, 2):
        b = Belief(team="red", seat=seat, role="defender", alive=True, tick=100,
                   self_xy=(200, 300))
        b.order = ("H", (390, 165), 90)
        intent, _ = decide_objective(b)
        assert intent.kind == "navigate_to" and intent.reason == "order_to_hold"
        points[seat] = intent.point
    assert points[1] != points[2]


def test_separation_bias_fires_only_when_stacked():
    from ctf.beacon import squads
    b = Belief(team="red", seat=5, alive=True, tick=100, self_xy=(400, 300))
    b.teammates = (Enemy(pos=(410, 300), facing="left"),)  # 10px: stacked
    sep = squads.separation_bias(b)
    assert sep is not None and sep[0] < 0
    b.teammates = (Enemy(pos=(500, 300), facing="left"),)  # 100px: fine
    assert squads.separation_bias(b) is None


# --- covered posts + sightlines ----------------------------------------------------


def test_sightline_artifact_shape_dtype_and_orientation():
    """Fail loudly when tests are run against a stale, pre-posts nav artifact."""
    from ctf.beacon import posts
    from ctf.beacon.config import GRID_H, GRID_W, SIGHTLINE_DIRECTIONS

    field = mapdata.sightline_field()
    assert field.shape == (SIGHTLINE_DIRECTIONS, GRID_H, GRID_W)
    assert field.dtype == np.uint8
    # At the verified top-lane post, east is open to the 400px cap. Direction
    # 29 (-33.75 degrees) reaches the nearby wall after two 4px samples.
    assert posts.sightline((548, 20), 0) == 400
    assert posts.sightline((548, 20), 29) == 8


def test_cover_toward_distinguishes_side_wall_from_blocked_lane():
    from ctf.beacon import posts

    # Looking east, the wall is useful flank cover while the firing lane is open.
    assert posts.sightline((548, 20), 0) == 400
    assert posts.cover_toward((548, 20), 0) == pytest.approx(0.875)
    # Looking toward the nearby wall does not mistake that blocked forward ray
    # for useful directional cover.
    assert posts.sightline((548, 20), 29) == 8
    assert posts.cover_toward((548, 20), 29) < 0.5


def test_phase_two_push_waypoint_selects_forward_rank_zero_post():
    from ctf.beacon import posts
    from ctf.beacon.config import GRID_H, GRID_W

    belief = Belief(
        team="red",
        seat=3,
        alive=True,
        self_xy=(628, 59),
        danger=np.zeros((GRID_H, GRID_W), dtype=np.float32),
    )
    post = posts.choose_post(belief, (628, 59), 0, mode="push")
    assert post is not None
    assert post.cell == (724, 20)
    assert post.reach == pytest.approx(0.56)
    assert post.cover == pytest.approx(0.8125)
    assert post.stance > 0.8


def test_threat_axis_quantisation_mirrors_for_blue():
    from ctf.beacon import posts

    red = Belief(team="red", alive=True, self_xy=(548, 20))
    blue = Belief(team="blue", alive=True, self_xy=(686, 20))
    assert posts.threat_axis(red, (548, 20)).direction == 29
    assert posts.threat_axis(blue, (686, 20)).direction == 19
    assert posts.direction_to_brads(29) == 232


def test_stance_prefers_forward_side_for_push_and_hold(monkeypatch):
    from ctf.beacon import posts
    from ctf.beacon.config import GRID_H, GRID_W, NAV_CELL, SIGHTLINE_DIRECTIONS

    walkable = np.zeros((GRID_H, GRID_W), dtype=bool)
    field = np.zeros((SIGHTLINE_DIRECTIONS, GRID_H, GRID_W), dtype=np.uint8)
    behind = (84, 100)
    ahead = (116, 100)
    for x, y in (behind, ahead):
        gx, gy = x // NAV_CELL, y // NAV_CELL
        walkable[gy, gx] = True
        field[0, gy, gx] = 100  # equal 400px reach
        field[4, gy, gx] = 1
        field[28, gy, gx] = 1  # equal strong flank cover
    monkeypatch.setattr(posts.mapdata, "walkable_grid", lambda: walkable)
    monkeypatch.setattr(posts.mapdata, "sightline_field", lambda: field)

    belief = Belief(
        team="red",
        seat=3,
        alive=True,
        self_xy=(100, 100),
        danger=np.zeros((GRID_H, GRID_W), dtype=np.float32),
    )
    push = posts.choose_post(belief, (100, 100), 0, mode="push")
    hold = posts.choose_post(belief, (100, 100), 0, mode="hold")
    assert push is not None and push.cell == ahead
    assert hold is not None and hold.cell == ahead


def test_post_claim_codec_and_arbitration(monkeypatch):
    from ctf.beacon import chat

    code = chat.encode_claim(5, (548, 20))
    assert len(code) == 6
    decoded = chat.decode(code)
    assert decoded is not None
    assert decoded.kind == "post_claim"
    assert decoded.seat == 5
    assert decoded.pos == (548, 20)

    monkeypatch.setattr(chat, "POSTS", True)
    monkeypatch.setattr(chat, "SQUAD_COMMAND", True)

    # Existing O orders retain priority over K.
    ordered = Belief(team="red", seat=0, alive=True, tick=1000, self_xy=(600, 300))
    ordered.order = ("H", (500, 300), 999)
    ordered.post_active = True
    ordered.post_cell = (548, 20)
    assert chat.choose_shout(ordered).startswith("O")

    # U remains live intel and wins over K.
    under_fire = Belief(team="red", seat=3, alive=True, tick=1000, self_xy=(600, 300))
    under_fire.under_fire = True
    under_fire.post_active = True
    under_fire.post_cell = (548, 20)
    assert chat.choose_shout(under_fire).startswith("U")

    # K wins over both E and the lowest-priority P heartbeat.
    claiming = Belief(team="red", seat=3, alive=True, tick=1000, self_xy=(600, 300))
    claiming.post_active = True
    claiming.post_cell = (548, 20)
    claiming.enemies = (Enemy(pos=(700, 300), facing="left"),)
    assert chat.choose_shout(claiming).startswith("K")


def test_lower_seat_claim_displaces_post_choice():
    from ctf.beacon import posts
    from ctf.beacon.config import GRID_H, GRID_W
    from ctf.beacon.types import PostClaim

    belief = Belief(
        team="red",
        seat=4,
        tick=100,
        alive=True,
        self_xy=(628, 59),
        danger=np.zeros((GRID_H, GRID_W), dtype=np.float32),
    )
    belief.post_claims[2] = PostClaim(seat=2, cell=(724, 20), tick=100)
    post = posts.choose_post(belief, (628, 59), 0, mode="push")
    assert post is not None
    assert post.cell == (548, 20)
    assert post.claim_source == "heard_K:2"


def test_post_claim_decays_and_under_fire_is_not_a_bearing():
    from ctf.beacon import chat
    from ctf.beacon.belief import update_belief
    from ctf.beacon.config import POST_CLAIM_TTL_TICKS

    belief = Belief(team="red", seat=4, alive=True, self_xy=(600, 329))
    state = ActionState()
    claim = chat.encode_claim(2, (548, 20))
    update_belief(
        belief,
        _chat_percept(
            heard_shouts=(("red", "mate (2)", claim, (550, 20)),),
        ),
        state,
        tick=10,
    )
    assert belief.post_claims[2].cell == (548, 20)

    under_fire = chat.encode("under_fire", (700, 300))
    update_belief(
        belief,
        _chat_percept(
            heard_shouts=(("red", "mate (3)", under_fire, (700, 300)),),
        ),
        state,
        tick=11,
    )
    assert belief.enemy_tracks == []

    update_belief(
        belief,
        _chat_percept(heard_shouts=()),
        state,
        tick=10 + POST_CLAIM_TTL_TICKS + 1,
    )
    assert 2 not in belief.post_claims


def test_post_plan_milestone_waits_for_post_arrival_not_dwell(posts_on):
    from ctf.beacon import poi

    center = poi.point("red_rally_top")
    belief = Belief(
        team="red",
        seat=3,
        role="attacker",
        alive=True,
        tick=100,
        self_xy=center,
    )
    intent, _ = decide_objective(belief)
    assert belief.plan_phase == 0
    assert belief.post_cell is not None
    assert intent.reason == "plan_post"

    belief.tick += 1
    belief.self_xy = belief.post_cell
    decide_objective(belief)
    assert belief.plan_phase == 1
    assert belief.plan_milestone_hit
    assert belief.post_settled_ticks < 96


def test_carrying_preempts_and_deactivates_latched_post(posts_on):
    belief = Belief(
        team="red",
        seat=3,
        role="attacker",
        alive=True,
        tick=100,
        self_xy=(548, 20),
        i_carry_enemy_flag=True,
        post_active=True,
        post_cell=(548, 20),
        post_direction=0,
    )
    intent, flow = decide_objective(belief)
    assert intent.reason == "carry_home"
    assert flow == "home"
    assert not belief.post_active


def test_settled_post_scans_baked_sightlines_and_ignores_squad_sector(monkeypatch):
    from ctf.beacon import action

    monkeypatch.setattr(action, "POST_FACING", True)
    monkeypatch.setattr(action, "SQUADS", True)
    monkeypatch.setattr(
        action.posts,
        "scan_directions",
        lambda cell, direction: (direction, 3, direction, 27),
    )
    belief = Belief(
        team="red",
        seat=2,
        tick=0,
        alive=True,
        self_xy=(548, 20),
        post_active=True,
        post_cell=(548, 20),
        post_direction=29,
        post_settled_ticks=1,
    )
    # Seat 2 starts on the repeated primary lane: direction 29 is 232 brads.
    # Its ordinary squad-sector offset must not move this post-owned sightline.
    assert action._sweep_target(belief) == 232
    assert belief.post_scan_direction == 29


def test_post_scan_directions_choose_open_lane_on_each_side(monkeypatch):
    from ctf.beacon import posts

    reach = {0: 400, 3: 260, 5: 120, 29: 180, 27: 300}
    monkeypatch.setattr(
        posts,
        "sightline",
        lambda cell, direction: reach.get(direction % 32, 20),
    )
    assert posts.scan_directions((548, 20), 0) == (0, 3, 0, 27)


def test_committed_post_survives_local_traffic_and_contact(monkeypatch):
    from ctf.beacon import posts

    belief = Belief(
        team="red",
        seat=3,
        tick=100,
        alive=True,
        self_xy=(100, 100),
        post_cell=(100, 100),
        post_direction=0,
        post_center=(100, 100),
        post_mode="hold",
        post_context="plan",
        post_committed=True,
        post_committed_tick=90,
        post_score=1.0,
    )
    belief.teammates = (Enemy(pos=(102, 100), facing="right"),)
    belief.enemies = (Enemy(pos=(104, 100), facing="left"),)
    monkeypatch.setattr(
        posts,
        "threat_axis",
        lambda belief, center, facing=None: posts.ThreatAxis(0, "plan_facing"),
    )
    assert posts.resolve_post_target(
        belief,
        (100, 100),
        mode="hold",
        context="plan",
    ).cell == (100, 100)
    assert belief.post_committed


def test_wave_gate_holds_outside_window_when_enabled(monkeypatch):
    from ctf.beacon import squads
    from ctf.beacon.config import SQUAD_WAVE_PERIOD_TICKS, SQUAD_WAVE_WINDOW_TICKS
    monkeypatch.setattr(squads, "SQUAD_WAVE_GATE", True)  # off by default since v21
    b = Belief(team="red", seat=5, role="attacker", alive=True,
               self_xy=(430, 300))  # near the red rally line (450), our side
    # Mid-period (outside the commit window): hold.
    b.tick = SQUAD_WAVE_PERIOD_TICKS * 10 + SQUAD_WAVE_WINDOW_TICKS + 5
    assert squads.should_wait_for_squad(b)
    # Inside the window: commit.
    b.tick = SQUAD_WAVE_PERIOD_TICKS * 10 + 2
    assert not squads.should_wait_for_squad(b)


def test_no_wait_once_committed_past_rally():
    from ctf.beacon import squads
    from ctf.beacon.config import SQUAD_WAVE_PERIOD_TICKS, SQUAD_WAVE_WINDOW_TICKS
    b = Belief(team="red", seat=5, role="attacker", alive=True,
               self_xy=(600, 300))  # already past the line
    b.tick = SQUAD_WAVE_PERIOD_TICKS * 10 + SQUAD_WAVE_WINDOW_TICKS + 5  # outside window
    assert not squads.should_wait_for_squad(b)


def test_carrier_never_waits():
    b = Belief(team="red", seat=5, role="attacker", alive=True, tick=1000,
               self_xy=(430, 300), i_carry_enemy_flag=True)
    b.teammates = ()
    intent, _ = decide_objective(b)
    assert intent.reason == "carry_home"


# --- v21: nameplates + squadmate cohesion ------------------------------------------


def test_identity_badge_resolves_on_players():
    w = _world_with_self((600, 329))
    _add_player(w, 11, 3, "player red left", (450, 300))
    # Badge at the body's bottom-right corner (~17px diagonal).
    w.sprites[80] = SpriteDef(80, 11, 11, "identity red gamma", b"")
    w.objects[80] = SpriteObject(80, 462, 312, 0, 0, 80)
    st = perceive(_obs(w), "red")
    assert len(st.teammates) == 1 and st.teammates[0].identity == 2  # gamma


def test_identity_sticks_to_track_and_gates_association():
    from ctf.beacon.belief import _update_tracks
    from ctf.beacon.types import PlayerTrack
    tracks: list = []
    _update_tracks(tracks, (Enemy(pos=(400, 300), facing="left", identity=3),), tick=10)
    assert tracks[0].identity == 3
    # A sighting with a DIFFERENT identity nearby must NOT claim delta's track.
    _update_tracks(tracks, (Enemy(pos=(405, 300), facing="left", identity=5),), tick=11)
    assert len(tracks) == 2
    idents = {t.identity for t in tracks}
    assert idents == {3, 5}


def test_cohesion_prefers_identified_squadmate():
    from ctf.beacon import squads
    # Seat 5 (squad A2 = 5,6,7). Two teammates visible: an identified NON-squad
    # mate (beta=1) nearby-ish, and an identified squadmate (eta=6) farther.
    b = Belief(team="red", seat=5, alive=True, tick=100, self_xy=(400, 300))
    b.teammates = (
        Enemy(pos=(700, 300), facing="left", identity=1),   # beta: not in A2
        Enemy(pos=(400, 600), facing="left", identity=6),   # eta: squadmate
    )
    bias = squads.formation_bias(b)
    assert bias is not None
    # Pull should point toward the SQUADMATE (south), not beta (east).
    assert bias[1] > 0.7


def test_wave_gate_disabled_by_default():
    from ctf.beacon import squads
    from ctf.beacon.config import SQUAD_WAVE_PERIOD_TICKS, SQUAD_WAVE_WINDOW_TICKS
    b = Belief(team="red", seat=5, role="attacker", alive=True, self_xy=(430, 300))
    b.tick = SQUAD_WAVE_PERIOD_TICKS * 10 + SQUAD_WAVE_WINDOW_TICKS + 5  # outside window
    assert not squads.should_wait_for_squad(b)  # gate off (v21 default)


# --- v22: squad command ---------------------------------------------------------------


def test_order_codec_roundtrip():
    from ctf.beacon import chat
    code = chat.encode_order(3, "P", (800, 400))
    assert len(code) <= 10
    msg = chat.decode(code)
    assert msg.kind == "order" and msg.seat == 3 and msg.goal == "P"
    assert abs(msg.pos[0] - 800) <= 8 and abs(msg.pos[1] - 400) <= 8
    ping = chat.decode(chat.encode_ping(6, (200, 300)))
    assert ping.kind == "ping" and ping.seat == 6


def test_leader_is_lowest_seat():
    from ctf.beacon import squads
    assert squads.leader_of(0) == 0 and squads.leader_of(2) == 0
    assert squads.leader_of(4) == 3
    assert squads.leader_of(7) == 5


def test_member_obeys_own_leaders_order_only(squads_on):
    from ctf.beacon.belief import update_belief
    from ctf.beacon import chat
    # Seat 6 (A2, leader = 5): obeys seat 5's order, ignores seat 0's (D leader).
    b = Belief(team="red", seat=6, role="attacker", alive=True, self_xy=(400, 300))
    st = ActionState()
    good = chat.encode_order(5, "H", (500, 300))
    bad = chat.encode_order(0, "P", (900, 300))
    update_belief(b, _chat_percept(heard_shouts=(
        ("red", "mate (0)", bad, (400, 320)),
        ("red", "mate (5)", good, (420, 300)),
    )), st, tick=10)
    assert b.order is not None and b.order[0] == "H"
    intent, _ = decide_objective(b)
    assert intent.reason in ("order_to_hold", "order_hold")


def test_leader_backs_off_when_squadmate_lost():
    from ctf.beacon import squads
    # Seat 5 leads A2 (5,6,7). Past the rally line, mates silent -> H order
    # stepped back toward home, and a backoff event is counted.
    b = Belief(team="red", seat=5, role="attacker", alive=True, tick=5000,
               self_xy=(700, 300))
    b.presence = {6: 100, 7: 120}  # long stale
    squads.lead_squad(b)
    assert b.order is not None and b.order[0] == "H"
    assert b.order[1][0] < 700  # stepped back toward red home
    assert b.backoff_events == 1
    # With mates fresh, the default push order returns instead.
    b2 = Belief(team="red", seat=5, role="attacker", alive=True, tick=5000,
                self_xy=(700, 300))
    b2.presence = {6: 4950, 7: 4990}
    squads.lead_squad(b2)
    # v24 default for B (seats 5-7): HOLD the bottom side lane.
    assert b2.order is not None and b2.order[0] == "H"
    assert b2.order[1][1] > 400  # bottom-side anchor


def test_death_snapshots_rejoin_and_respawn_enters_rejoin(squads_on):
    from ctf.beacon.belief import update_belief
    from ctf.beacon.types import PlayerTrack
    b = Belief(team="red", seat=6, role="attacker", alive=True, self_xy=(700, 300))
    st = ActionState()
    # Freshest squadmate memory: seat 7 at (650, 350).
    b.teammate_tracks = [PlayerTrack(pos=(650, 350), last_tick=90, facing="left", identity=7)]
    update_belief(b, _chat_percept(self_xy=(700, 300)), st, tick=100)
    # Die: percept has no self.
    update_belief(b, _chat_percept(self_xy=None, ready=False), st, tick=101)
    assert not b.alive and b.rejoin_point == (650, 350)
    # Respawn: rejoin mode armed; objective is the rejoin rung.
    update_belief(b, _chat_percept(self_xy=(80, 300)), st, tick=180)
    assert b.rejoin_until > 180
    intent, _ = decide_objective(b)
    assert intent.reason == "rejoin" and intent.point == (650, 350)


def test_rejoin_exits_on_squad_contact(squads_on):
    b = Belief(team="red", seat=6, role="attacker", alive=True, self_xy=(640, 340))
    b.rejoin_point = (650, 350)
    b.rejoin_until = 10_000
    b.tick = 200
    # A squadmate (seat 7 badge) right next to us -> contact -> rejoin ends.
    b.teammates = (Enemy(pos=(660, 350), facing="left", identity=7),)
    intent, _ = decide_objective(b)
    assert b.rejoin_until == -1 and intent.reason != "rejoin"


# --- firefight target selection + focus claims --------------------------------------


def _ff_candidate(
    identity: int,
    *,
    distance: float = 250.0,
    hp_segments: int | None = 3,
    shootable: bool = True,
    aim_cost: float = 0.0,
    shielded: bool = False,
) -> TargetCandidate:
    enemy = Enemy(
        pos=(200 + identity * 10, 100),
        facing="left",
        identity=identity,
        hp_segments=hp_segments,
        shielded=shielded,
    )
    return TargetCandidate(
        enemy=enemy,
        target=TargetRef(identity=identity, pos=enemy.pos),
        aim_pos=enemy.pos,
        lead_brads=0,
        distance_px=distance,
        aim_cost=aim_cost,
        line_clear=shootable,
        teammate_blocked=False,
        shootable=shootable,
    )


@pytest.mark.parametrize(
    ("term", "first", "second"),
    (
        ("wound", {"hp_segments": 3}, {"hp_segments": 1}),
        ("range", {"distance": 60.0}, {"distance": 260.0}),
        ("claim", {}, {}),
        ("shootability", {"shootable": False}, {"shootable": True}),
        ("aim_cost", {"aim_cost": 1.0}, {"aim_cost": 0.0}),
        ("shield", {"shielded": True}, {"shielded": False}),
    ),
)
def test_each_firefight_score_term_changes_choice_in_isolation(
    monkeypatch,
    term,
    first,
    second,
):
    from ctf.beacon import fight
    from ctf.beacon.types import FocusClaim

    weight_names = {
        "wound": "FF_WOUND_WEIGHT",
        "range": "FF_RANGE_WEIGHT",
        "claim": "FF_CLAIM_WEIGHT",
        "shootability": "FF_SHOOTABILITY_WEIGHT",
        "aim_cost": "FF_AIM_COST_WEIGHT",
        "shield": "FF_SHIELD_WEIGHT",
    }
    for name in weight_names.values():
        monkeypatch.setattr(fight, name, 0.0)
    monkeypatch.setattr(fight, weight_names[term], 1.0)
    monkeypatch.setattr(fight, "FIREFIGHT", True)
    monkeypatch.setattr(fight, "FOCUS_CLAIMS", term == "claim")

    candidates = (_ff_candidate(0, **first), _ff_candidate(1, **second))
    belief = Belief(
        team="red",
        seat=3,
        tick=100,
        alive=True,
        self_xy=(100, 100),
        firefight_active=True,
    )
    if term == "claim":
        belief.focus_claim = FocusClaim(
            claimant_seat=2,
            target=candidates[1].target,
            first_tick=100,
            refreshed_tick=100,
            last_seen_tick=100,
            enemy_deaths_at_last_seen=None,
        )

    selected = fight.select_target(belief, candidates)
    assert selected is not None
    assert selected.candidate.target.identity == 1


def test_wound_score_distinguishes_unknown_from_confirmed_healthy():
    from ctf.beacon import fight

    healthy = fight.score_target(_ff_candidate(0, hp_segments=3), claimed=False)
    unknown = fight.score_target(_ff_candidate(1, hp_segments=None), claimed=False)
    wounded = fight.score_target(_ff_candidate(2, hp_segments=1), claimed=False)
    assert healthy.wound == 0.0
    assert unknown.wound == 0.15
    assert wounded.wound == 1.0
    assert wounded.score > unknown.score > healthy.score


def test_firefight_range_band_rejects_too_close_and_beyond_gate():
    from ctf.beacon import fight
    from ctf.beacon.config import FIRE_MAX_RANGE_PX

    assert fight._range_term(60.0) == 0.0
    assert fight._range_term(260.0) == 1.0
    assert fight._range_term(FIRE_MAX_RANGE_PX + 1.0) == 0.0


def test_shootability_default_swing_is_point_seven():
    from ctf.beacon import fight

    blocked = fight.score_target(_ff_candidate(0, shootable=False), claimed=False)
    clear = fight.score_target(_ff_candidate(0, shootable=True), claimed=False)
    assert clear.score - blocked.score == pytest.approx(0.70)


def test_firefight_target_latch_prevents_thrash_then_switches(monkeypatch):
    from ctf.beacon import fight

    monkeypatch.setattr(fight, "FIREFIGHT", True)
    for name in (
        "FF_WOUND_WEIGHT",
        "FF_RANGE_WEIGHT",
        "FF_CLAIM_WEIGHT",
        "FF_SHOOTABILITY_WEIGHT",
        "FF_SHIELD_WEIGHT",
    ):
        monkeypatch.setattr(fight, name, 0.0)
    monkeypatch.setattr(fight, "FF_AIM_COST_WEIGHT", 1.0)

    belief = Belief(
        team="red",
        tick=100,
        alive=True,
        self_xy=(100, 100),
        firefight_active=True,
    )
    selected = fight.select_target(
        belief,
        (_ff_candidate(0, aim_cost=0.0), _ff_candidate(1, aim_cost=0.2)),
    )
    assert selected.candidate.target.identity == 0

    belief.tick = 104
    selected = fight.select_target(
        belief,
        (_ff_candidate(0, aim_cost=0.2), _ff_candidate(1, aim_cost=0.0)),
    )
    assert selected.candidate.target.identity == 0
    assert belief.firefight_target_switches == 0

    belief.tick = 108
    selected = fight.select_target(
        belief,
        (_ff_candidate(0, aim_cost=0.2), _ff_candidate(1, aim_cost=0.0)),
    )
    assert selected.candidate.target.identity == 1
    assert belief.firefight_target_switches == 1


def test_unshootable_current_target_switches_immediately(monkeypatch):
    from ctf.beacon import fight

    monkeypatch.setattr(fight, "FIREFIGHT", True)
    belief = Belief(
        team="red",
        tick=100,
        alive=True,
        self_xy=(100, 100),
        firefight_active=True,
    )
    fight.select_target(
        belief,
        (_ff_candidate(0), _ff_candidate(1, aim_cost=0.5)),
    )
    belief.tick = 101
    selected = fight.select_target(
        belief,
        (
            _ff_candidate(0, shootable=False),
            _ff_candidate(1, aim_cost=0.5),
        ),
    )
    assert selected.candidate.target.identity == 1
    assert belief.firefight_target_switches == 1


def test_anonymous_target_promotes_to_late_badge_without_switch(monkeypatch):
    from ctf.beacon import fight

    monkeypatch.setattr(fight, "FIREFIGHT", True)
    belief = Belief(
        team="red",
        tick=100,
        alive=True,
        self_xy=(100, 100),
        firefight_active=True,
        firefight_target=TargetRef(identity=None, pos=(230, 100)),
        firefight_target_selected_tick=90,
        firefight_target_last_seen_tick=99,
    )
    selected = fight.select_target(belief, (_ff_candidate(3),))
    assert selected is not None
    assert belief.firefight_target.identity == 3
    assert belief.firefight_target_switches == 0


def test_firefight_mode_hysteresis_and_arc_exemption(monkeypatch):
    from ctf.beacon import fight
    from ctf.beacon.config import FF_DWELL_TICKS

    monkeypatch.setattr(fight, "FIREFIGHT", True)
    belief = Belief(
        team="red",
        tick=10,
        alive=True,
        self_xy=(100, 100),
        enemies=(Enemy(pos=(300, 100), facing="left"),),
    )
    fight.update_firefight(belief)
    assert belief.firefight_active
    assert belief.firefight_engagements == 1

    belief.enemies = ()
    belief.tick = 10 + FF_DWELL_TICKS
    fight.update_firefight(belief)
    assert belief.firefight_active
    belief.tick += 1
    fight.update_firefight(belief)
    assert not belief.firefight_active

    belief.tick += 1
    belief.enemies = (Enemy(pos=(300, 100), facing="left"),)
    belief.i_have_arc = True
    fight.update_firefight(belief)
    assert not belief.firefight_active
    assert belief.firefight_arc_exempt_ticks == 1


def test_enemy_hp_and_shield_attach_without_stealing_own_bar():
    w = _world_with_self((600, 329))
    _add_player(w, 11, 3, "player blue left", (650, 329))
    w.sprites[50] = SpriteDef(50, 14, 2, "hp 3/3", b"")
    w.objects[50] = SpriteObject(50, 593, 306, 0, 0, 50)
    w.sprites[51] = SpriteDef(51, 14, 2, "hp 1/3", b"")
    w.objects[51] = SpriteObject(51, 643, 306, 0, 0, 51)
    w.sprites[52] = SpriteDef(52, 10, 10, "shield carried", b"")
    w.objects[52] = SpriteObject(52, 655, 301, 0, 0, 52)

    state = perceive(_obs(w), "red")
    assert state.hp_pips == 3
    assert not state.i_have_shield
    assert state.enemies[0].hp_segments == 1
    assert state.enemies[0].shielded


def test_focus_claim_codec_roundtrip():
    from ctf.beacon import chat

    for target, expected_len in (
        (TargetRef(identity=6, pos=(487, 315)), 8),
        (TargetRef(identity=None, pos=(487, 315)), 7),
    ):
        code = chat.encode_focus_claim(3, target)
        message = chat.decode(code)
        assert len(code) == expected_len
        assert message is not None
        assert message.kind == "focus_claim"
        assert message.seat == 3
        assert message.target_identity == target.identity
        assert abs(message.pos[0] - target.pos[0]) <= 8
        assert abs(message.pos[1] - target.pos[1]) <= 8


def test_focus_claim_arbitration_preserves_existing_priority(monkeypatch):
    from ctf.beacon import chat

    target = TargetRef(identity=1, pos=(700, 300))
    monkeypatch.setattr(chat.fight, "focus_claim_to_send", lambda _belief: target)
    monkeypatch.setattr(chat.fight, "note_focus_claim_sent", lambda _belief, _target: None)
    monkeypatch.setattr(chat, "POSTS", True)
    monkeypatch.setattr(chat, "SQUAD_COMMAND", True)

    def base() -> Belief:
        return Belief(
            team="red",
            seat=0,
            alive=True,
            tick=1000,
            self_xy=(600, 300),
        )

    cases: list[tuple[Belief, str]] = []
    carrier = base()
    carrier.i_carry_enemy_flag = True
    cases.append((carrier, "C"))
    thief = base()
    thief.own_flag_stolen = True
    thief.own_flag_thief_pos = (700, 300)
    cases.append((thief, "T"))
    ordered = base()
    ordered.order = ("H", (500, 300), 999)
    cases.append((ordered, "O"))
    grenade = base()
    grenade.throw_target = (700, 300)
    grenade.throw_charge_ticks = 1
    cases.append((grenade, "G"))
    under_fire = base()
    under_fire.under_fire = True
    cases.append((under_fire, "U"))
    post = base()
    post.post_active = True
    post.post_cell = (548, 20)
    cases.append((post, "K"))
    enemy = base()
    enemy.enemies = (Enemy(pos=(700, 300), facing="left"),)
    cases.append((enemy, "F"))
    presence = base()
    cases.append((presence, "F"))

    for belief, expected_prefix in cases:
        shout = chat.choose_shout(belief)
        assert shout is not None
        assert shout.startswith(expected_prefix)


def test_focus_claim_exclusivity_is_local_to_one_fight(monkeypatch):
    from ctf.beacon import fight
    from ctf.beacon.types import FocusClaim

    monkeypatch.setattr(fight, "FIREFIGHT", True)
    monkeypatch.setattr(fight, "FOCUS_CLAIMS", True)
    selected = fight.score_target(_ff_candidate(1), claimed=False)
    belief = Belief(
        team="red",
        seat=3,
        tick=100,
        alive=True,
        self_xy=(100, 100),
        firefight_active=True,
        firefight_target_score=selected,
    )
    belief.focus_claim = FocusClaim(
        claimant_seat=2,
        target=_ff_candidate(0).target,
        first_tick=99,
        refreshed_tick=99,
        last_seen_tick=99,
        enemy_deaths_at_last_seen=None,
    )
    assert fight.focus_claim_to_send(belief) is None
    assert belief.focus_claims_suppressed == 1

    belief.focus_claim = FocusClaim(
        claimant_seat=2,
        target=TargetRef(identity=0, pos=(900, 600)),
        first_tick=99,
        refreshed_tick=99,
        last_seen_tick=99,
        enemy_deaths_at_last_seen=None,
    )
    assert fight.focus_claim_to_send(belief) == selected.candidate.target


def test_focus_claim_releases_on_ttl_missing_and_scoreboard_death(monkeypatch):
    from ctf.beacon import fight
    from ctf.beacon.config import (
        FF_CLAIM_TTL_TICKS,
        FF_DEATH_MISSING_TICKS,
        FF_TARGET_MISSING_TICKS,
    )
    from ctf.beacon.types import FocusClaim

    monkeypatch.setattr(fight, "FIREFIGHT", True)
    target = _ff_candidate(1).target

    ttl = Belief(team="red", tick=100, alive=True, self_xy=(100, 100))
    ttl.focus_claim = FocusClaim(2, target, 1, 100 - FF_CLAIM_TTL_TICKS - 1, 100, None)
    ttl.enemies = (_ff_candidate(1).enemy,)
    fight.update_firefight(ttl)
    assert ttl.focus_claim is None
    assert ttl.focus_last_release_reason == "claim_ttl"

    missing = Belief(
        team="red",
        tick=100,
        alive=True,
        self_xy=(100, 100),
        focus_claim=FocusClaim(
            2,
            target,
            90,
            100,
            100 - FF_TARGET_MISSING_TICKS,
            None,
        ),
    )
    fight.update_firefight(missing)
    assert missing.focus_claim is None
    assert missing.focus_last_release_reason == "target_missing"

    death = Belief(
        team="red",
        tick=100,
        alive=True,
        self_xy=(100, 100),
        enemy_team_score=(0, 5),
        focus_claim=FocusClaim(
            2,
            target,
            90,
            100,
            100 - FF_DEATH_MISSING_TICKS,
            4,
        ),
    )
    fight.update_firefight(death)
    assert death.focus_claim is None
    assert death.focus_last_release_reason == "scoreboard_death"


def test_focus_claim_refresh_rebases_death_inference_and_claimant_death_releases(
    monkeypatch,
):
    from ctf.beacon import fight

    monkeypatch.setattr(fight, "FIREFIGHT", True)
    monkeypatch.setattr(fight, "FOCUS_CLAIMS", True)
    belief = Belief(
        team="red",
        seat=3,
        tick=100,
        alive=True,
        self_xy=(100, 100),
        enemy_team_score=(0, 4),
    )
    fight.receive_focus_claim(
        belief,
        claimant_seat=2,
        target_identity=1,
        target_cell=(210, 100),
    )
    belief.tick = 110
    belief.enemy_team_score = (0, 5)
    fight.receive_focus_claim(
        belief,
        claimant_seat=2,
        target_identity=1,
        target_cell=(220, 100),
    )
    assert belief.focus_claim is not None
    assert belief.focus_claim.last_seen_tick == 110
    assert belief.focus_claim.enemy_deaths_at_last_seen == 5

    belief.focus_claim = type(belief.focus_claim)(
        claimant_seat=belief.seat,
        target=belief.focus_claim.target,
        first_tick=100,
        refreshed_tick=110,
        last_seen_tick=110,
        enemy_deaths_at_last_seen=5,
    )
    belief.alive = False
    belief.self_xy = None
    fight.update_firefight(belief)
    assert belief.focus_claim is None
    assert belief.focus_last_release_reason == "claimant_dead"


def test_firefight_off_path_command_is_identical(monkeypatch):
    from copy import deepcopy
    from ctf.beacon import action, fight

    monkeypatch.setattr(action, "FIREFIGHT", False)
    monkeypatch.setattr(fight, "FIREFIGHT", False)
    legacy = Belief(
        team="red",
        alive=True,
        self_xy=(300, 329),
        aim_brads=0,
        fire_ready=True,
        enemies=(
            Enemy(pos=(360, 329), facing="left", hp_segments=3),
            Enemy(pos=(300, 579), facing="left", hp_segments=1),
        ),
    )
    primed = deepcopy(legacy)
    primed.firefight_active = True
    primed.firefight_target = TargetRef(identity=None, pos=(300, 579))

    expected = resolve_action(Intent(kind="hold", reason="hold_line"), legacy, ActionState())
    actual = resolve_action(Intent(kind="hold", reason="hold_line"), primed, ActionState())
    assert expected == actual
    assert actual.held_mask == int(Button.A)


def test_firefight_does_not_preempt_carrier_movement(monkeypatch):
    from ctf.beacon import fight

    monkeypatch.setattr(fight, "FIREFIGHT", True)
    belief = Belief(
        team="red",
        seat=7,
        role="attacker",
        tick=100,
        alive=True,
        self_xy=(800, 300),
        i_carry_enemy_flag=True,
        firefight_active=True,
        enemies=(Enemy(pos=(850, 300), facing="left"),),
    )
    intent, flow = decide_objective(belief)
    assert intent.reason == "carry_home"
    assert flow == "home"


def test_firefight_snapshot_contains_activation_and_range_traces():
    from ctf.beacon.decide import _DiagnosticLogger
    from ctf.beacon.runtime import StepInfo

    sink = type("Sink", (), {"record": lambda self, event: None})()
    logger = _DiagnosticLogger(sink, team="red", seat=3)
    belief = Belief(
        team="red",
        seat=3,
        tick=100,
        alive=True,
        self_xy=(100, 100),
        firefight_active=True,
        firefight_arc_exempt_ticks=4,
        firefight_target_switches=2,
        friendly_fire_suppressed=3,
        firefight_target_range_counts={"200_299": 9},
        firefight_shot_range_counts={"200_299": 4},
    )
    step = StepInfo(
        tick=100,
        percept=_chat_percept(self_xy=(100, 100)),
        belief=belief,
        intent=Intent(kind="hold", reason="hold_line"),
        flow_kind=None,
        command=Command(held_mask=0),
    )
    payload = logger._payload(step)
    assert payload["firefight_target_switches"] == 2
    assert payload["firefight_arc_exempt_ticks"] == 4
    assert payload["friendly_fire_suppressed"] == 3
    assert payload["firefight_target_ranges"] == {"200_299": 9}
    assert payload["firefight_shot_ranges"] == {"200_299": 4}


def test_firefight_tunable_registry_drives_defaults_and_covers_all_ff_envs():
    import re
    from pathlib import Path
    from ctf.beacon import config

    specs = {
        name: spec
        for name, spec in config.TUNABLE_REGISTRY.items()
        if spec.family == "firefight"
    }
    assert specs
    for name, spec in specs.items():
        assert getattr(config, name) == spec.default
        assert spec.description and "\n" not in spec.description
        assert spec.choices is not None or spec.minimum is not None

    source = Path(config.__file__).read_text()
    ff_envs_in_config = set(
        re.findall(r'"(BEACON_FF_[A-Z0-9_]+)"', source)
    )
    registered_ff_envs = {
        spec.env_var
        for spec in specs.values()
        if spec.env_var.startswith("BEACON_FF_")
    }
    assert registered_ff_envs == ff_envs_in_config
    assert specs["FIREFIGHT"].env_var == "BEACON_FIREFIGHT"
    assert specs["FOCUS_CLAIMS"].env_var == "BEACON_FOCUS_CLAIMS"


@pytest.mark.parametrize(
    "assignment",
    (
        {"FF_RANGE_CLOSE_PX": 220},
        {"FF_RANGE_IDEAL_MAX_PX": 351},
        {"FF_RADIUS_PX": 349},
        {"FF_TARGET_MIN_DWELL_TICKS": 49},
        {"FF_CLAIM_REBROADCAST_TICKS": 72},
        {"FF_DEATH_MISSING_TICKS": 36},
        {"FF_TARGET_MISSING_TICKS": 72},
        {"FF_CLAIM_MATCH_PX": 401},
        {"FOCUS_CLAIMS": True},
        {"FF_CLAIM_WEIGHT": 0.26},
        {"FF_SHOOTABILITY_WEIGHT": -0.01},
        {"FF_WOUND_WEIGHT": "nan"},
    ),
)
def test_firefight_tunable_validation_rejects_invalid_assignments(assignment):
    from ctf.beacon.config import validate_tunable_values

    with pytest.raises(ValueError):
        validate_tunable_values(assignment)


def test_firefight_tunable_validation_normalizes_names_and_env_vars():
    from ctf.beacon.config import validate_tunable_values

    values = validate_tunable_values(
        {
            "BEACON_FIREFIGHT": "1",
            "BEACON_FOCUS_CLAIMS": "true",
            "BEACON_FF_WOUND_WEIGHT": "0.6",
            "FF_CLAIM_WEIGHT": 0.15,
        }
    )
    assert values["FIREFIGHT"] is True
    assert values["FOCUS_CLAIMS"] is True
    assert values["FF_WOUND_WEIGHT"] == 0.6
    assert values["FF_CLAIM_WEIGHT"] == 0.15


def test_firefight_tuning_cli_dump_and_secret_env(capsys):
    import json
    from ctf.beacon import tuning

    tuning.main(["dump", "--family", "firefight"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["tunables"]
    assert all(item["family"] == "firefight" for item in payload["tunables"])
    assert {item["name"] for item in payload["invariants"]} >= {
        "range_band_order",
        "claim_release_clock_order",
        "focus_requires_firefight",
    }

    tuning.main(
        [
            "secret-env",
            "FIREFIGHT=true",
            "FOCUS_CLAIMS=true",
            "FF_WOUND_WEIGHT=0.6",
            "FF_CLAIM_WEIGHT=0.15",
        ]
    )
    assert capsys.readouterr().out.strip() == (
        "--secret-env BEACON_FIREFIGHT=1 "
        "--secret-env BEACON_FOCUS_CLAIMS=1 "
        "--secret-env BEACON_FF_WOUND_WEIGHT=0.6 "
        "--secret-env BEACON_FF_CLAIM_WEIGHT=0.15"
    )


# --- v24: squad defaults + order decay ------------------------------------------------


def test_v24_default_orders_side_holds_and_middle_push():
    from ctf.beacon import squads
    from ctf.beacon.config import CHOKE_X
    # A leader (seat 0): hold TOP side at the choke.
    a = Belief(team="red", seat=0, alive=True, tick=100, self_xy=(200, 329))
    a.presence = {1: 95, 2: 96}
    squads.lead_squad(a)
    assert a.order[0] == "H" and a.order[1] == (CHOKE_X["red"], 165)
    # B leader (seat 5): hold BOTTOM side.
    b = Belief(team="red", seat=5, alive=True, tick=100, self_xy=(200, 329))
    b.presence = {6: 95, 7: 96}
    squads.lead_squad(b)
    assert b.order[0] == "H" and b.order[1] == (CHOKE_X["red"], 494)
    # C leader (seat 3): push the middle.
    c = Belief(team="red", seat=3, alive=True, tick=100, self_xy=(200, 329))
    c.presence = {4: 95}
    squads.lead_squad(c)
    assert c.order[0] == "P" and c.order[1] == (617, 329)


def test_order_decay_becomes_backoff_hold(squads_on):
    from ctf.beacon.config import ORDER_TTL_TICKS
    # Seat 6 (member, not leader) holds a stale P order, forward of the rally.
    b = Belief(team="red", seat=6, role="attacker", alive=True, self_xy=(700, 300))
    b.tick = 1000
    b.order = ("P", (900, 329), 1000 - ORDER_TTL_TICKS - 1)  # stale
    intent, _ = decide_objective(b)
    # Decayed into a self-issued hold, stepped back toward home.
    assert b.order[0] == "H" and b.order[1][0] < 700
    assert intent.reason in ("order_to_hold", "order_hold")


def test_order_decay_behind_rally_holds_in_place(squads_on):
    from ctf.beacon.config import ORDER_TTL_TICKS
    b = Belief(team="red", seat=6, role="attacker", alive=True, self_xy=(300, 300))
    b.tick = 1000
    b.order = ("P", (900, 329), 1000 - ORDER_TTL_TICKS - 1)  # stale, we're home-side
    decide_objective(b)
    assert b.order[0] == "H" and b.order[1] == (300, 300)  # no home-creep
