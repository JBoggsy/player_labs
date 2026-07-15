"""Critical-invariant tests for beacon (sparing, per the lab's testing discipline).

These cover the few things that would silently lose games or crash an episode:
brad arithmetic (aim rotation direction), the mask stays legal, flow-field routing
reaches the goal, flag-state detection, team-from-slot, and the folded belief
memory (player tracks + danger field).
"""

from __future__ import annotations

import math

from ctf.beacon import mapdata, nav
from ctf.beacon.perception import perceive
from players.player_sdk import SpriteDef, SpriteObject, SpriteWorld
from ctf.beacon.action import _brad_error, _brads_of, _rotation_button, resolve_action
from ctf.beacon.config import AIM_BRADS_TURN, DEFENDER_COUNT, PEDESTAL
from ctf.beacon.main import seat_from_url, team_from_url
from ctf.beacon.roles import hold_point_for_seat, role_for_seat
from ctf.beacon.strategy import decide_objective
from ctf.beacon.types import ActionState, Belief, Enemy, Intent
from players.player_sdk import Button


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


def test_defender_holds_when_arrived():
    b = Belief(team="red", seat=0, role="defender", hold_point=(390, 300),
               alive=True, self_xy=(390, 300))
    intent, flow = decide_objective(b)
    assert intent.kind == "hold" and intent.reason == "hold_line"


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


# --- perception at the 0.7.3 wire format --------------------------------------------
# Since 0.6.0 the zoomable map layer is wire-scaled: object coordinates and sprite
# sizes arrive at RENDER_SCALE (3x) map resolution, every sprite centered on its
# scaled map point. These helpers build worlds exactly as global.nim emits them
# (HD crew canvas 96 = 32 map px, heart canvas 60 = 20 map px).
from ctf.beacon.config import RENDER_SCALE

_HD_CREW = 96
_HD_FLAG = 60


def _add_player(w, obj_id, sprite_id, label, center_xy):
    """Place a player-like sprite as addHdPlayerObject does: 3*x - canvas/2."""
    w.sprites[sprite_id] = SpriteDef(sprite_id, _HD_CREW, _HD_CREW, label, b"")
    w.objects[obj_id] = SpriteObject(
        obj_id,
        center_xy[0] * RENDER_SCALE - _HD_CREW // 2,
        center_xy[1] * RENDER_SCALE - _HD_CREW // 2,
        0, 0, sprite_id,
    )


def _add_heart(w, obj_id, sprite_id, label, center_xy, lift=0):
    """Place a heart as the per-player packet does: map-px offset, wire-scaled."""
    w.sprites[sprite_id] = SpriteDef(sprite_id, _HD_FLAG, _HD_FLAG, label, b"")
    map_x = center_xy[0] - _HD_FLAG // (2 * RENDER_SCALE)
    map_y = center_xy[1] - _HD_FLAG // (2 * RENDER_SCALE) - lift
    w.objects[obj_id] = SpriteObject(
        obj_id, map_x * RENDER_SCALE, map_y * RENDER_SCALE, 0, 0, sprite_id
    )


def _world_with_self_and_heart(self_xy, heart_center, lift=0):
    w = SpriteWorld()
    _add_player(w, 10, 1, "self red right", self_xy)
    _add_heart(w, 20, 2, "blue heart", heart_center, lift=lift)
    w.frame = 1
    return w


def _obs(w):
    return type("O", (), {"world": w, "frame": 1})()


def test_wire_scale_recovers_map_coordinates():
    # A self sprite placed at map (600, 329) through the 3x wire math must read
    # back as exactly (600, 329) after perception's divide-at-the-seam.
    st = perceive(_obs(_world_with_self_and_heart((600, 329), (1049, 329))), "red")
    assert st.self_xy == (600, 329)


def test_carry_detected_when_heart_rides_above_us():
    # Carried heart sits ~10px above the carrier (CarriedFlagLift) — the old 6px
    # threshold missed this, so beacon never ran the heart home.
    st = perceive(_obs(_world_with_self_and_heart((600, 329), (600, 329), lift=10)), "red")
    assert st.i_carry_enemy_flag and not st.enemy_flag_on_pedestal


def test_standing_on_pedestal_with_resting_heart_is_not_carry():
    st = perceive(_obs(_world_with_self_and_heart((1049, 329), (1049, 329))), "red")
    assert not st.i_carry_enemy_flag and st.enemy_flag_on_pedestal


def test_grab_on_pedestal_registers_carry():
    # The instant we grab it on the pedestal, it lifts to ~10px above -> carry.
    st = perceive(_obs(_world_with_self_and_heart((1049, 329), (1049, 329), lift=10)), "red")
    assert st.i_carry_enemy_flag


def test_enemy_players_read_at_map_scale():
    w = _world_with_self_and_heart((300, 329), (1049, 329))
    _add_player(w, 11, 3, "player blue left", (450, 300))
    st = perceive(_obs(w), "red")
    assert len(st.enemies) == 1 and st.enemies[0].pos == (450, 300)


def test_corpse_is_not_a_live_player_and_we_read_dead():
    # While dead (0.7.x: fog does NOT lift), our own body is labeled "corpse ...",
    # so self is not found -> not ready/alive; and a corpse never counts as an enemy.
    w = SpriteWorld()
    _add_player(w, 10, 1, "corpse red right", (300, 329))
    _add_heart(w, 20, 2, "blue heart", (1049, 329))
    _add_heart(w, 21, 3, "red heart", (186, 329))
    w.frame = 1
    st = perceive(_obs(w), "red")
    assert not st.ready and st.self_xy is None
    assert st.enemies == () and st.teammates == ()
    # Pedestal hearts stay readable through death (they never fog).
    assert st.enemy_flag_on_pedestal and not st.own_flag_stolen
