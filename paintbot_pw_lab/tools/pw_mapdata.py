#!/usr/bin/env python3
"""Load Paintbot PW map geometry (terrain raster + features) for plots and metrics.

Runs the release's `pw_map` once per (release, map, rules, step) and caches the result
under paintbot_pw_lab/tools/.cache/maps/<tag>/ ($PW_CACHE_DIR/maps/<tag>/ when that env var
is set) as NAME.npz (heights, flags) + NAME.json (bounds, hearts, pickups, trenches, cover,
homes). Contract: docs/tools/pw_map.md.

    from pw_mapdata import load_map
    m = load_map("", rules=47)          # "" = the Heartwick island
    plt.imshow(m.heights, extent=m.extent)   # world z grows downward, as in the viewer
    m.water, m.blocked, m.trench         # boolean masks, shape (nz, nx)

CLI: uv run python paintbot_pw_lab/tools/pw_mapdata.py [--map NAME] [--rules N] [--step U] [--tag TAG]
         [--png OUT] [--json]
Exit codes: 0 ok; 2 usage or an unknown map (pw_map failed); 3 pw_map not built for the tag.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pw_cli  # noqa: E402
import pw_release  # noqa: E402

DEFAULT_TAG = pw_release.current_tag()  # tools/release.env, shared with build_tools.sh
FLAG_BITS = {"water": 1, "blocked": 2, "trench": 4, "off_island": 8, "blocked_for_cog": 16}


@dataclass
class MapData:
    meta: dict               # pw_map JSON: bounds, step, hearts, pickups, trenches, cover, homes
    heights: np.ndarray      # int16 terrain height, shape (nz, nx); row j is z = minZ + (j + 0.5) * step
    flags: np.ndarray        # uint8 bit set, FLAG_BITS

    def mask(self, name: str) -> np.ndarray:
        return (self.flags & FLAG_BITS[name]) != 0

    water = property(lambda self: self.mask("water"))
    blocked = property(lambda self: self.mask("blocked"))
    trench = property(lambda self: self.mask("trench"))
    off_island = property(lambda self: self.mask("off_island"))

    @property
    def extent(self) -> tuple[int, int, int, int]:
        """imshow extent (left, right, bottom, top) with world z growing downward."""
        x0, z0, x1, z1 = self.meta["bounds"]
        return (x0, x0 + self.meta["nx"] * self.meta["step"], z0 + self.meta["nz"] * self.meta["step"], z0)

    def cell(self, x: float, z: float) -> tuple[int, int]:
        """(row, column) of a world point, clipped to the grid."""
        x0, z0, _, _ = self.meta["bounds"]
        step = self.meta["step"]
        return (int(np.clip((z - z0) // step, 0, self.meta["nz"] - 1)),
                int(np.clip((x - x0) // step, 0, self.meta["nx"] - 1)))


def map_cache(tag: str | None = None) -> Path:
    """<cache root>/maps/<tag>/ (pw_release.cache_root: $PW_CACHE_DIR or tools/.cache)."""
    return pw_release.cache_root() / "maps" / (tag or DEFAULT_TAG)


def load_map(map_name: str = "", *, rules: int = 47, step: int = 25, tag: str | None = None,
             binary: Path | None = None) -> MapData:
    """The map raster for one release build; tag None = the pinned release (tools/release.env)."""
    tag = tag or DEFAULT_TAG
    cache = map_cache(tag)
    stem = f"{map_name or 'heartwick'}-r{rules}-s{step}"
    npz, meta_path = cache / f"{stem}.npz", cache / f"{stem}.json"
    if not (npz.is_file() and meta_path.is_file()):
        binary = binary or pw_release.require_built("pw_map", tag)   # NotBuilt: CLI exit 3 + build command
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as work:
            prefix = Path(work) / stem
            subprocess.run([str(binary), str(prefix), "--map", map_name, "--rules", str(rules),
                            "--step", str(step)], check=True, capture_output=True, text=True)
            meta = json.loads(prefix.with_suffix(".json").read_text())
            raw = prefix.with_suffix(".bin").read_bytes()
            cells = meta["nx"] * meta["nz"]
            if len(raw) != 3 * cells:
                raise ValueError(f"pw_map wrote {len(raw)} bytes, expected {3 * cells}")
            heights = np.frombuffer(raw[:2 * cells], dtype="<i2").reshape(meta["nz"], meta["nx"])
            flags = np.frombuffer(raw[2 * cells:], dtype=np.uint8).reshape(meta["nz"], meta["nx"])
            np.savez(prefix.with_suffix(".npz"), heights=heights, flags=flags)
            prefix.with_suffix(".npz").replace(npz)  # the json lands last: it marks a complete cache
            prefix.with_suffix(".json").replace(meta_path)
    arrays = np.load(npz)
    return MapData(json.loads(meta_path.read_text()), arrays["heights"], arrays["flags"])


def map_for_episode(meta: dict, **kwargs) -> MapData:
    """The map a traced episode played on (pw_trace meta row: map name and rules).

    Pass tag=episode.tag so the raster comes from the same build that traced the episode."""
    return load_map(meta["map"], rules=meta["rules"], **kwargs)


def build_parser() -> pw_cli.ArgumentParser:
    parser = pw_cli.ArgumentParser("pw_mapdata", __doc__, examples=[
        "uv run python paintbot_pw_lab/tools/pw_mapdata.py --json",
        "uv run python paintbot_pw_lab/tools/pw_mapdata.py --map twin-mesas --png /tmp/twin.png"])
    parser.add_argument("--map", default="", help="map name ('' = Heartwick, the league's map), e.g. --map twin-mesas")
    parser.add_argument("--rules", type=int, default=47, help="rules version (default %(default)s)")
    parser.add_argument("--step", type=int, default=25, help="grid step in world units (default %(default)s)")
    parser.add_argument("--tag", default=DEFAULT_TAG, help="release build (default %(default)s, tools/release.env)")
    parser.add_argument("--png", type=Path, help="write a quick-look terrain image, e.g. --png /tmp/map.png")
    return parser


def run_cli(args, report: pw_cli.Report) -> dict:
    try:
        m = load_map(args.map, rules=args.rules, step=args.step, tag=args.tag)
    except subprocess.CalledProcessError as error:
        raise pw_cli.UsageError(f"pw_map failed for map {args.map!r} rules {args.rules}: "
                                f"{(error.stderr or '').strip()[-300:]}") from error
    name = args.map or "heartwick"
    report.counts["processed"] = 1
    print(f"{name}: grid {m.meta['nx']}x{m.meta['nz']} at {m.meta['step']} units, "
          f"bounds {m.meta['bounds']}, {len(m.meta['hearts'])} hearts, {len(m.meta['pickups'])} pickups, "
          f"{len(m.meta['trenches'])} trenches, {len(m.meta['cover'])} cover; water {m.water.mean():.1%} of cells")
    stem = f"{name}-r{args.rules}-s{args.step}"
    cache = map_cache(args.tag)
    if args.png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.imshow(np.where(m.off_island, np.nan, m.heights), extent=m.extent, cmap="gist_earth")
        ax.imshow(np.ma.masked_where(~m.water, m.water), extent=m.extent, cmap="Blues", vmin=0, vmax=1.5)
        for h in m.meta["hearts"]:
            ax.plot(*h["pos"], "r*", markersize=10)
        ax.set_title(name)
        fig.savefig(args.png, dpi=100, bbox_inches="tight")
        print(f"wrote {args.png}")
        report.output(args.png)
    return {"map": name, "cache_json": str(cache / f"{stem}.json"), "cache_npz": str(cache / f"{stem}.npz"),
            "nx": m.meta["nx"], "nz": m.meta["nz"], "step": m.meta["step"], "bounds": m.meta["bounds"],
            "hearts": len(m.meta["hearts"]), "pickups": len(m.meta["pickups"]),
            "trenches": len(m.meta["trenches"]), "cover": len(m.meta["cover"]),
            "water_share": float(m.water.mean())}


def main(argv: list[str] | None = None) -> int:
    return pw_cli.run(build_parser(), run_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
