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


def test_single_claimant_per_item():
    # Across all 8 seats, each fetchable spawn is claimed by at most one seat.
    from ctf.beacon import items

    claims: dict[tuple[int, int], int] = {}
    for seat in range(8):
        b = Belief(team="red", seat=seat, alive=True, tick=10, self_xy=(200, 329))
        b.item_spawns = items.build_spawn_table()
        spawn = items.assigned_fetch(b)
        if spawn is not None:
            assert spawn.pos not in claims, f"seats {claims[spawn.pos]} and {seat} both claim {spawn.pos}"
            claims[spawn.pos] = seat
    assert len(claims) == 3  # shield + two grenades on our side


def test_assigned_fetch_respects_carried_item():
    from ctf.beacon import items

    b = Belief(team="red", seat=2, alive=True, tick=10, self_xy=(200, 329))
    b.item_spawns = items.build_spawn_table()
    assert items.assigned_fetch(b) is not None
    b.i_have_shield = True
    assert items.assigned_fetch(b) is None


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
    assert items.medkit_target(b, 420) is None
    b.hp_pips = 1
    kit = items.medkit_target(b, 420)
    assert kit is not None and kit.kind == "medkit"


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


def test_ordered_hold_uses_spread_point():
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


def test_member_obeys_own_leaders_order_only():
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


def test_death_snapshots_rejoin_and_respawn_enters_rejoin():
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


def test_rejoin_exits_on_squad_contact():
    b = Belief(team="red", seat=6, role="attacker", alive=True, self_xy=(640, 340))
    b.rejoin_point = (650, 350)
    b.rejoin_until = 10_000
    b.tick = 200
    # A squadmate (seat 7 badge) right next to us -> contact -> rejoin ends.
    b.teammates = (Enemy(pos=(660, 350), facing="left", identity=7),)
    intent, _ = decide_objective(b)
    assert b.rejoin_until == -1 and intent.reason != "rejoin"


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


def test_order_decay_becomes_backoff_hold():
    from ctf.beacon.config import ORDER_TTL_TICKS
    # Seat 6 (member, not leader) holds a stale P order, forward of the rally.
    b = Belief(team="red", seat=6, role="attacker", alive=True, self_xy=(700, 300))
    b.tick = 1000
    b.order = ("P", (900, 329), 1000 - ORDER_TTL_TICKS - 1)  # stale
    intent, _ = decide_objective(b)
    # Decayed into a self-issued hold, stepped back toward home.
    assert b.order[0] == "H" and b.order[1][0] < 700
    assert intent.reason in ("order_to_hold", "order_hold")


def test_order_decay_behind_rally_holds_in_place():
    from ctf.beacon.config import ORDER_TTL_TICKS
    b = Belief(team="red", seat=6, role="attacker", alive=True, self_xy=(300, 300))
    b.tick = 1000
    b.order = ("P", (900, 329), 1000 - ORDER_TTL_TICKS - 1)  # stale, we're home-side
    decide_objective(b)
    assert b.order[0] == "H" and b.order[1] == (300, 300)  # no home-creep
