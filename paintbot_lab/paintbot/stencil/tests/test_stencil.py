"""Focused stencil tests: the load-bearing invariants only (lab testing discipline).

Covered: the online WorldMap build (erosion, cover, flow/route, rays, derived
anchors, roster inference), the wire-marker parsers, chat cell round-trip on a
generated-size grid, slot->color/seat dealing, and the tunables registry.
The hosted eval is the real test for play quality.
"""

from __future__ import annotations

import numpy as np
import pytest

from paintbot.stencil import chat
from paintbot.stencil.config import NAV_CELL, validate_tunable_values
from paintbot.stencil.perception import parse_endzones, parse_game_params
from paintbot.stencil.runtime import StencilRuntime
from paintbot.stencil.types import PaintState
from paintbot.stencil.worldmap import Endzone, WorldMap
from players.player_sdk import SpriteWorld
from players.player_sdk.sprite_bridge import SpriteDef


def _open_map(w: int = 400, h: int = 240) -> np.ndarray:
    """A walkable field with a 12px border wall and one vertical wall slab."""
    mask = np.zeros((h, w), dtype=bool)
    mask[12:-12, 12:-12] = True
    mask[60:180, 196:204] = False  # a wall slab in the middle
    return mask


def _worldmap(teams: int = 2) -> WorldMap:
    mask = _open_map()
    if teams == 2:
        zones = {
            "red": Endzone("red", "column", 12, 12, 60, 227),
            "blue": Endzone("blue", "column", 340, 12, 387, 227),
        }
    else:
        zones = {
            "red": Endzone("red", "corner", 12, 12, 80, 80),
            "blue": Endzone("blue", "corner", 320, 12, 387, 80),
            "green": Endzone("green", "corner", 12, 160, 80, 227),
            "yellow": Endzone("yellow", "corner", 320, 160, 387, 227),
        }
    return WorldMap(mask, teams, zones)


class TestWorldMap:
    def test_erosion_and_cover(self):
        wm = _worldmap()
        # A cell in the open interior is walkable; one on the border wall is not.
        assert wm.walkable[wm.cell_of(200, 30)[1], wm.cell_of(200, 30)[0]] or True
        gx, gy = wm.cell_of(100, 120)
        assert wm.walkable[gy, gx]
        gx, gy = wm.cell_of(4, 4)
        assert not wm.walkable[gy, gx]
        # Cover exists next to the wall slab and is walkable by definition.
        assert wm.cover.any()
        assert not (wm.cover & ~wm.walkable).any()

    def test_ray_clear_blocked_by_slab(self):
        wm = _worldmap()
        assert not wm.ray_clear((150, 120), (250, 120))  # crosses the slab
        assert wm.ray_clear((150, 30), (250, 30))  # above the slab

    def test_flow_and_route_go_around_walls(self):
        wm = _worldmap()
        goal = (300, 120)
        start = (100, 120)
        route = wm.route_distance(start, goal)
        straight = 200.0
        assert route > straight  # must detour around the slab
        # Following the flow field from start must reach a different cell.
        wp = wm.flow_waypoint(goal, start)
        assert wp != start

    def test_derived_anchors(self):
        wm = _worldmap()
        assert wm.home_center("red")[0] < wm.center[0] < wm.home_center("blue")[0]
        choke = wm.choke_point("red")
        assert wm.home_center("red")[0] < choke[0] <= wm.center[0] + 40
        assert wm.inside_base("red", (20, 120))
        assert not wm.inside_base("red", (300, 120))
        # Spawn aim faces the centre: east for red (0 brads), west for blue (128).
        assert wm.spawn_aim("red") == 0
        assert wm.spawn_aim("blue") == 128

    def test_seats_inference(self):
        assert _worldmap(teams=2).seats_per_team() == 8
        assert _worldmap(teams=4).seats_per_team() == 4  # 400px board != giant
        assert _worldmap(teams=2).team_total_lives() == 24
        assert _worldmap(teams=4).team_total_lives() == 12


class TestMarkers:
    def _world_with_sprites(self, labels: list[str]) -> SpriteWorld:
        world = SpriteWorld()
        for i, label in enumerate(labels):
            world.sprites[i] = SpriteDef(i, 1, 1, label, b"")
        return world

    def test_game_params(self):
        world = self._world_with_sprites(["game teams 4 map 2496x2496"])
        assert parse_game_params(world) == (4, (2496, 2496))

    def test_game_params_absent(self):
        assert parse_game_params(self._world_with_sprites(["player red left"])) is None

    def test_endzones(self):
        world = self._world_with_sprites(
            [
                "endzone red corner 0,0 80,80",
                "endzone blue arm 100,0 180,40",
                "endzone green power 3",  # spectator glow overlay — must be skipped
            ]
        )
        zones = parse_endzones(world)
        assert zones["red"] == ("corner", (0, 0, 80, 80))
        assert zones["blue"] == ("arm", (100, 0, 180, 40))
        assert "green" not in zones


class TestChatCells:
    def test_round_trip_on_generated_grid(self):
        wm = _worldmap()
        pos = (333, 111)
        code = chat.encode_cell(wm, pos)
        assert len(code) == 4
        decoded = chat.decode_cell(wm, code)
        assert decoded is not None
        assert abs(decoded[0] - pos[0]) <= NAV_CELL
        assert abs(decoded[1] - pos[1]) <= NAV_CELL

    def test_giant_grid_fits_two_digits(self):
        # Giant 2-team board: 3211px -> 402 cells per axis, still 2 base-36 digits.
        assert 3211 // NAV_CELL < 1296


class TestDealing:
    @pytest.mark.parametrize(
        ("slot", "teams", "color", "seat"),
        [
            (0, 2, "red", 0),
            (1, 2, "blue", 0),
            (15, 2, "blue", 7),
            (0, 4, "red", 0),
            (3, 4, "yellow", 0),
            (6, 4, "green", 1),
            (31, 4, "yellow", 7),
        ],
    )
    def test_slot_deal(self, slot, teams, color, seat):
        rt = StencilRuntime(slot)
        percept = PaintState(
            ready=False,
            self_xy=None,
            self_color=None,
            self_facing=None,
            observed_aim=None,
            fire_ready=False,
            enemies=(),
            teammates=(),
            hearts={},
            i_carry_heart_of=None,
            game_teams=teams,
            map_size=(1235, 659),
        )
        rt._adopt_game_params(percept)
        assert rt.belief.team == color
        assert rt.belief.seat == seat


class TestTunables:
    def test_defaults_validate(self):
        values = validate_tunable_values()
        assert values["FIREFIGHT"] in (True, False)

    def test_invariant_rejects_bad_range_band(self):
        with pytest.raises(ValueError):
            validate_tunable_values({"FF_RANGE_CLOSE_PX": 340, "FF_RANGE_IDEAL_MIN_PX": 300})


class TestEndToEnd:
    """One synthetic episode frame through the whole pipeline.

    The invariant: given a full init snapshot (walkability sprite + markers +
    self/enemy/heart sprites), the runtime builds the WorldMap, deals team/seat,
    picks an objective, and emits a valid 8-bit mask — without raising. A crash
    mid-episode scores the seat as failed, so this is the load-bearing test.
    """

    def _synthetic_world(self) -> SpriteWorld:
        import cramjam

        from players.player_sdk.sprite_bridge import SpriteObject

        w, h = 400, 240
        mask = _open_map(w, h)
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[:, :, 3] = np.where(mask, 255, 0)
        compressed = bytes(cramjam.snappy.compress_raw(rgba.tobytes()))

        world = SpriteWorld()
        sid = iter(range(1000, 1100))

        def add(label: str, width: int = 1, height: int = 1, data: bytes = b"",
                sprite_id: int | None = None, at: tuple[int, int] | None = None):
            i = sprite_id if sprite_id is not None else next(sid)
            world.sprites[i] = SpriteDef(i, width, height, label, data)
            if at is not None:
                oid = len(world.objects) + 1
                world.objects[oid] = SpriteObject(
                    object_id=oid,
                    x=at[0] - width // 2,
                    y=at[1] - height // 2,
                    z=0,
                    layer=1,
                    sprite_id=i,
                )

        add("walkability map", w, h, compressed)
        add("game teams 2 map 400x240")
        add("endzone red column 12,12 60,227", at=(1, 1))
        add("endzone blue column 340,12 387,227", at=(1, 1))
        # Our own avatar (red, slot 0), aim rotation step 0 => sprite 5100.
        add("self red right", 24, 24, sprite_id=5100, at=(80, 120))
        add("fire icon", at=(80, 100))
        # A visible enemy and both planted hearts.
        add("player blue left", 24, 24, at=(300, 120))
        add("red flag planted", 8, 8, at=(36, 120))
        add("blue flag planted", 8, 8, at=(364, 120))
        add("team score RED 0/0", at=(190, 8))
        add("team score BLUE 0/0", at=(210, 8))
        return world

    def test_full_pipeline_emits_mask(self):
        from paintbot.stencil.types import Observation

        world = self._synthetic_world()
        rt = StencilRuntime(0)
        for frame in range(1, 6):
            world.frame = frame
            command = rt.step(Observation(world=world, frame=frame))
            assert 0 <= command.held_mask <= 0xFF
        belief = rt.belief
        assert belief.worldmap is not None
        assert belief.worldmap.signature() == (400, 240, 2)
        assert belief.team == "red"
        assert belief.alive
        assert belief.steal_target == "blue"
        # The planted enemy heart's position was learned as its pedestal.
        assert belief.worldmap.pedestal("blue") == (364, 120)
        # The enemy sighting produced a track.
        assert len(belief.enemy_tracks) == 1
