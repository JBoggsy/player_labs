#!/usr/bin/env python3
"""Bake crewborg's per-task-station visibility masks offline (run when the map changes).

Search's WATCH camouflage stands the imposter at the task spot with the best view over
the crew (see crewborg/docs/designs/watch-camouflage.md). Scoring that needs vision
from every task station — a heavy pure-Python LOS pass (~16k segment walks), far over
the hosted first-tick budget. This tool bakes it ONCE into the vendored asset
`crewrift/crewborg/map/croatoan_visionbake.pkl.gz`, loaded and validated at runtime by
`crewrift/crewborg/visionbake.py` (any mismatch degrades to a nearest-task fallback).

Unlike the nav bake there is no capture step: the authoritative walkability mask and
the task-station anchors are read straight out of the existing vendored NAV bake, so
the two assets are always fingerprint-consistent. Re-run this AFTER re-running
tools/nav_bake.py whenever the league redeploys a changed map:

    uv run tools/vision_bake.py
    # -> writes crewrift/crewborg/map/croatoan_visionbake.pkl.gz (+ prints timing)

Then rebuild the image (tools/build_player.sh crewborg) so the asset ships.
"""

from __future__ import annotations

import argparse
import gzip
import pickle
import sys
import time
from pathlib import Path

# crewborg is importable as the top-level `crewrift.crewborg` package (PYTHONPATH).
from crewrift.crewborg.map import load_croatoan_map
from crewrift.crewborg.navbake import NAVBAKE_FORMAT, NAVBAKE_PACKAGE, NAVBAKE_RESOURCE
from crewrift.crewborg.visionbake import (
    VISIONBAKE_RESOURCE,
    build_task_vision,
    load_visionbake,
    serialize_visionbake,
)

_MAP_DIR = Path(__file__).resolve().parents[1] / "crewrift" / "crewborg" / "map"


def _load_nav():
    """The nav graph out of the vendored nav bake (walkability + task anchors)."""

    navbake_path = _MAP_DIR / NAVBAKE_RESOURCE
    if not navbake_path.is_file():
        sys.exit(f"missing nav bake {navbake_path} — run tools/nav_bake.py first ({NAVBAKE_PACKAGE})")
    payload = pickle.loads(gzip.decompress(navbake_path.read_bytes()))
    if payload.get("format") != NAVBAKE_FORMAT:
        sys.exit(f"nav bake format {payload.get('format')} != {NAVBAKE_FORMAT} — re-run tools/nav_bake.py")
    return payload["nav"]


def bake(out_path: Path) -> None:
    nav = _load_nav()
    map_data = load_croatoan_map()
    walkability = nav.walkability
    print(f"walkability: shape={walkability.shape}  tasks={len(map_data.tasks)}")

    t0 = time.perf_counter()
    vision = build_task_vision(walkability, map_data, nav)
    t1 = time.perf_counter()
    print(f"  build_task_vision: {t1 - t0:8.2f}s  "
          f"(masks {vision.masks.shape}, visible cells/task "
          f"min={int(vision.counts.min())} median={int(sorted(vision.counts)[len(vision.counts) // 2])} "
          f"max={int(vision.counts.max())})")
    if int(vision.counts.min()) == 0:
        print("  WARNING: some task station sees zero cells — check anchors/walkability")

    blob = serialize_visionbake(vision)
    out_path.write_bytes(blob)
    print(f"wrote {out_path}  ({len(blob) / 1024:.1f} KiB gzipped)")

    # Round-trip sanity: the vendored asset must load against the same mask.
    if out_path == _MAP_DIR / VISIONBAKE_RESOURCE:
        loaded = load_visionbake(walkability, len(map_data.tasks))
        print("round-trip load:", "OK" if loaded is not None else "FAILED (asset will be ignored at runtime!)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out", type=Path, default=_MAP_DIR / VISIONBAKE_RESOURCE,
                        help="output asset path (default: the vendored asset)")
    args = parser.parse_args(argv)
    bake(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
