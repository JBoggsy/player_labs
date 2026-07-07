"""Bake Heartleaf map assets into Cady runtime navigation data."""

from __future__ import annotations

import json
import math
import re
import struct
import zlib
from pathlib import Path

import numpy as np

from cady.nav import nearest_walkable

MAP_ASEPRITE = Path("/Users/jamesboggs/coding/coworld-heartleaf/data/map.aseprite")
MAP_RESOURCE = Path("/Users/jamesboggs/coding/coworld-heartleaf/data/map.resource")
HOME_ASEPRITE = Path("/Users/jamesboggs/coding/coworld-heartleaf/data/home_map.aseprite")
HOME_RESOURCE = Path("/Users/jamesboggs/coding/coworld-heartleaf/data/home_map.resource")
OUT_DIR = Path(__file__).resolve().parents[1] / "mapdata"
WORLD_TO_MAP = (0, 0)

Point = tuple[int, int]
Rect = tuple[int, int, int, int]


def main() -> None:
    """Parse source assets and write packed Cady map data."""

    walk = _parse_walk_grid(MAP_ASEPRITE, expected_shape=(941, 748))
    gardens, houses = _parse_resource_rects(MAP_RESOURCE)
    home_walk = _parse_walk_grid(HOME_ASEPRITE, expected_shape=(247, 251))
    home_layout = _parse_home_resource(HOME_RESOURCE, home_walk)

    garden_approaches = [_approach_for_garden(walk, rect) for rect in gardens]
    house_rects = [houses[f"house{i}"] for i in range(1, 10)]
    house_targets = [_target_for_rect(walk, rect) for rect in house_rects]
    garden_circuit = _garden_circuit(walk, garden_approaches)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_walk_grid(walk, OUT_DIR / "walk.npz")
    _write_walk_grid(home_walk, OUT_DIR / "home_walk.npz")
    _write_layout(
        OUT_DIR / "layout.json",
        gardens,
        garden_approaches,
        house_rects,
        house_targets,
        garden_circuit,
        home_layout,
    )

    walkable_pct = 100.0 * float(walk.mean())
    home_walkable_pct = 100.0 * float(home_walk.mean())
    print(f"wrote {OUT_DIR}")
    print(f"walk grid: {walk.shape[1]}x{walk.shape[0]}, {walkable_pct:.1f}% walkable")
    print(f"home walk grid: {home_walk.shape[1]}x{home_walk.shape[0]}, {home_walkable_pct:.1f}% walkable")
    print(f"GARDEN_CIRCUIT: {garden_circuit}")


def _parse_walk_grid(path: Path, *, expected_shape: tuple[int, int]) -> np.ndarray:
    data = path.read_bytes()
    _, magic, frames, width, height, depth = struct.unpack_from("<IHHHHH", data, 0)
    if magic != 0xA5E0 or depth != 32:
        raise ValueError(f"unexpected Aseprite header: magic={magic:#x}, depth={depth}")

    off = 128
    layers: list[str] = []
    cels: list[tuple[int, int, int, int, int, int]] = []
    for _ in range(frames):
        frame_bytes, _, old_count, _, _, new_count = struct.unpack_from("<IHHHHI", data, off)
        p = off + 16
        chunk_count = new_count if new_count else old_count
        for _ in range(chunk_count):
            chunk_size, chunk_type = struct.unpack_from("<IH", data, p)
            chunk_data = p + 6
            if chunk_type == 0x2004:
                name_len = struct.unpack_from("<H", data, chunk_data + 16)[0]
                layers.append(data[chunk_data + 18 : chunk_data + 18 + name_len].decode("utf-8", "replace"))
            elif chunk_type == 0x2005:
                layer_index, x, y, _, cel_type = struct.unpack_from("<HhhBH", data, chunk_data)
                cels.append((layer_index, x, y, cel_type, chunk_data, chunk_size))
            p += chunk_size
        off += frame_bytes

    walkable_layer = layers.index("walkable")
    layer_index, x, y, cel_type, chunk_data, chunk_size = next(cel for cel in cels if cel[0] == walkable_layer)
    if cel_type != 2:
        raise ValueError(f"walkable cel has unsupported type {cel_type}")
    if layer_index != walkable_layer:
        raise ValueError("walkable cel layer mismatch")

    cel_width, cel_height = struct.unpack_from("<HH", data, chunk_data + 16)
    raw = zlib.decompress(data[chunk_data + 20 : chunk_data + chunk_size])
    cel = np.frombuffer(raw[: cel_width * cel_height * 4], dtype=np.uint8).reshape(cel_height, cel_width, 4)
    walk = np.zeros((height, width), dtype=bool)
    walk[y : y + cel_height, x : x + cel_width] = cel[:, :, 3] > 0

    if walk.shape != expected_shape:
        raise ValueError(f"unexpected walk grid shape {walk.shape}")
    return walk


def _parse_resource_rects(path: Path) -> tuple[list[Rect], dict[str, Rect]]:
    named_rects = _parse_named_rects(path)
    gardens: list[Rect] = []
    houses: dict[str, Rect] = {}

    for name, rect in named_rects:
        if name == "garden":
            gardens.append(rect)
        elif re.fullmatch(r"house[1-9]", name):
            houses[name] = rect

    if len(gardens) != 39:
        raise ValueError(f"expected 39 gardens, found {len(gardens)}")
    missing = [f"house{i}" for i in range(1, 10) if f"house{i}" not in houses]
    if missing:
        raise ValueError(f"missing house rects: {missing}")
    return gardens, houses


def _parse_home_resource(path: Path, walk: np.ndarray) -> dict[str, object]:
    named_rects = _parse_named_rects(path)
    diner_rects: list[Rect] = []
    exit_rect: Rect | None = None
    cook_rect: Rect | None = None
    wash_rect: Rect | None = None

    for name, rect in named_rects:
        if name == "exit":
            exit_rect = rect
        elif name == "diner":
            diner_rects.append(rect)
        elif name == "cook":
            cook_rect = rect
        elif name == "wash":
            wash_rect = rect

    if exit_rect is None:
        raise ValueError("missing home exit rect")
    if len(diner_rects) != 6:
        raise ValueError(f"expected 6 home diner rects, found {len(diner_rects)}")
    if cook_rect is None:
        raise ValueError("missing home cook rect")
    if wash_rect is None:
        raise ValueError("missing home wash rect")

    return {
        "exit_rect": exit_rect,
        "exit": _target_for_rect(walk, exit_rect),
        "diner_rects": diner_rects,
        "diners": [_target_for_rect(walk, rect) for rect in diner_rects],
        "cook_rect": cook_rect,
        "cook": _target_for_rect(walk, cook_rect),
        "wash_rect": wash_rect,
        "wash": _target_for_rect(walk, wash_rect),
    }


def _parse_named_rects(path: Path) -> list[tuple[str, Rect]]:
    blocks = re.split(r"/\*\s*(.*?)\s*\*/", path.read_text())
    rects: list[tuple[str, Rect]] = []
    for i in range(1, len(blocks) - 1, 2):
        name = blocks[i].strip()
        rect = _rect(blocks[i + 1])
        if rect is not None:
            rects.append((name, rect))
    return rects


def _rect(body: str) -> Rect | None:
    values: list[int] = []
    for key in ("left", "top", "width", "height"):
        match = re.search(key + r":\s*(-?\d+)px", body)
        if match is None:
            return None
        values.append(int(match.group(1)))
    return (values[0], values[1], values[2], values[3])


def _approach_for_garden(walk: np.ndarray, rect: Rect) -> Point:
    center = _rect_center(rect)
    approach = nearest_walkable(walk, center)
    if approach is None:
        raise ValueError(f"no walkable approach for garden {rect}")
    if not walk[approach[1], approach[0]]:
        raise ValueError(f"garden approach is not walkable: {approach}")
    if math.hypot(approach[0] - center[0], approach[1] - center[1]) > 40.0:
        raise ValueError(f"garden approach {approach} is too far from {rect}")
    return approach


def _target_for_rect(walk: np.ndarray, rect: Rect) -> Point:
    center = _rect_center(rect)
    target = nearest_walkable(walk, center)
    if target is None:
        raise ValueError(f"no walkable target for rect {rect}")
    if not walk[target[1], target[0]]:
        raise ValueError(f"target is not walkable: {target}")
    return target


def _garden_circuit(walk: np.ndarray, approaches: list[Point]) -> list[int]:
    costs = _pairwise_costs(walk, approaches)
    center = (walk.shape[1] / 2.0, walk.shape[0] / 2.0)
    start = min(
        range(len(approaches)),
        key=lambda i: (approaches[i][0] - center[0]) ** 2 + (approaches[i][1] - center[1]) ** 2,
    )

    unvisited = set(range(len(approaches)))
    order = [start]
    unvisited.remove(start)
    while unvisited:
        current = order[-1]
        nxt = min(unvisited, key=lambda candidate: (costs[current][candidate], candidate))
        order.append(nxt)
        unvisited.remove(nxt)

    return _two_opt(order, costs)


def _pairwise_costs(walk: np.ndarray, points: list[Point]) -> list[list[float]]:
    # Euclidean distance between approach points. This orders the circuit ("cut the
    # TSP by pre-computing it") cheaply; geodesic (JPS/A*) distances would refine the
    # order marginally but cost an all-pairs pathfind over the full grid — deferred.
    costs = [[0.0 for _ in points] for _ in points]
    for i, a in enumerate(points):
        for j in range(i + 1, len(points)):
            b = points[j]
            cost = math.hypot(b[0] - a[0], b[1] - a[1])
            costs[i][j] = cost
            costs[j][i] = cost
    return costs


def _two_opt(order: list[int], costs: list[list[float]]) -> list[int]:
    improved = True
    while improved:
        improved = False
        for i in range(1, len(order) - 2):
            for j in range(i + 1, len(order) - 1):
                a, b = order[i - 1], order[i]
                c, d = order[j], order[j + 1]
                if costs[a][b] + costs[c][d] <= costs[a][c] + costs[b][d]:
                    continue
                order[i : j + 1] = reversed(order[i : j + 1])
                improved = True
    return order


def _write_walk_grid(walk: np.ndarray, path: Path) -> None:
    packed = np.packbits(walk.reshape(-1))
    shape = np.array(walk.shape, dtype=np.int32)
    np.savez_compressed(path, packed=packed, shape=shape)


def _write_layout(
    path: Path,
    garden_rects: list[Rect],
    garden_approaches: list[Point],
    house_rects: list[Rect],
    house_targets: list[Point],
    garden_circuit: list[int],
    home_layout: dict[str, object],
) -> None:
    layout = {
        "world_to_map": list(WORLD_TO_MAP),
        "garden_rects": [list(rect) for rect in garden_rects],
        "garden_approaches": [list(point) for point in garden_approaches],
        "house_rects": [list(rect) for rect in house_rects],
        "house_targets": [list(point) for point in house_targets],
        "garden_circuit": garden_circuit,
        "home": _json_home_layout(home_layout),
    }
    path.write_text(json.dumps(layout, indent=2) + "\n")


def _json_home_layout(home_layout: dict[str, object]) -> dict[str, object]:
    return {
        "exit_rect": list(home_layout["exit_rect"]),
        "exit": list(home_layout["exit"]),
        "diner_rects": [list(rect) for rect in home_layout["diner_rects"]],
        "diners": [list(point) for point in home_layout["diners"]],
        "cook_rect": list(home_layout["cook_rect"]),
        "cook": list(home_layout["cook"]),
        "wash_rect": list(home_layout["wash_rect"]),
        "wash": list(home_layout["wash"]),
    }


def _rect_center(rect: Rect) -> Point:
    left, top, width, height = rect
    return (left + width // 2, top + height // 2)


if __name__ == "__main__":
    main()
