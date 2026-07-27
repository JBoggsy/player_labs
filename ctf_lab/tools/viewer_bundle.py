"""Bundle one CTF episode for the belief-overlay replay viewer (viewer.html).

Packages everything the viewer needs into a single JSON file:

  * **ground truth** — per-tick player/flag positions + the full event timeline,
    from the version-matched ``expand_replay_json`` binary run at ``pos_every=1``
    (build it first: ``tools/build_expand_replay.sh``);
  * **beacon traces** — every bot's telemetry.jsonl from the episode's
    ``artifacts/policy_artifact_<slot>.zip`` (snapshots, order/objective/micro
    transitions, heard_chat/heard_sound events), tick-aligned to the engine axis
    the same way the warehouse does it (first spawn <-> phase=Playing);
  * **the arena** — the wall mask from beacon's baked ``nav.npz``, run-length
    encoded per row (the viewer draws walls and clips vision rays against them).

Usage:
    uv run python ctf_lab/tools/viewer_bundle.py <episode_dir> [-o out.json]
    # then open ctf_lab/tools/viewer.html and pick the bundle,
    # or serve both:  python -m http.server -d <dir>

``<episode_dir>`` is one fetched episode (needs replay.json/replay.bitreplay +
artifacts/*.zip for the overlay; runs without artifacts with overlays disabled).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

LAB_DIR = Path(__file__).resolve().parent.parent
DEFAULT_EXPAND = LAB_DIR / "tools" / "bin" / "expand_replay_json"
NAV_NPZ = LAB_DIR / "ctf" / "beacon" / "mapdata" / "nav.npz"


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _find_replay(ep_dir: Path) -> Path | None:
    for name in ("replay.json", "replay.bitreplay"):
        p = ep_dir / name
        if p.exists():
            return p
    return None


def _expand(replay: Path, expand_bin: Path) -> list[dict]:
    """All replay rows at per-tick pos resolution."""
    proc = subprocess.run(
        [str(expand_bin), str(replay), "1"],
        capture_output=True, text=True, timeout=300,
    )
    rows = []
    for line in proc.stdout.splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    meta = next((r["value"] for r in rows if r.get("key") == "_meta"), {})
    if meta.get("hash_failed"):
        log(f"! hash failed at tick {meta.get('fail_tick')} — bump CTF_REF (build_expand_replay.sh)")
    return rows


def _traces(ep_dir: Path) -> dict[int, list[dict]]:
    """slot -> raw trace records from the artifact zips."""
    out: dict[int, list[dict]] = {}
    art = ep_dir / "artifacts"
    if not art.is_dir():
        return out
    for zpath in sorted(art.glob("policy_artifact_*.zip")):
        try:
            slot = int(zpath.stem.rsplit("_", 1)[1])
        except (ValueError, IndexError):
            continue
        try:
            with zipfile.ZipFile(zpath) as zf:
                for name in zf.namelist():
                    if not name.endswith("telemetry.jsonl"):
                        continue
                    recs = []
                    for line in zf.read(name).decode("utf-8", "replace").splitlines():
                        try:
                            obj = json.loads(line)
                        except ValueError:
                            continue
                        if obj.get("kind") == "trace":
                            recs.append({
                                "tick": obj.get("tick"),
                                "name": obj.get("name") or obj.get("event"),
                                "data": obj.get("data", {}),
                            })
                    if recs:
                        out[slot] = recs
        except (zipfile.BadZipFile, OSError):
            continue
    return out


def _align(traces: dict[int, list[dict]], replay_rows: list[dict]) -> dict[int, int]:
    """slot -> engine-tick offset (add to a trace tick to get the engine tick)."""
    playing = next((r["ts"] for r in replay_rows
                    if r.get("key") == "phase" and "Playing" in json.dumps(r.get("value"))), None)
    offsets: dict[int, int] = {}
    if playing is None:
        return offsets
    for slot, recs in traces.items():
        spawn = next((r["tick"] for r in recs
                      if r["name"] == "alive" and r["data"].get("alive")), None)
        if spawn is not None:
            offsets[slot] = playing - spawn
    return offsets


def _wall_runs() -> dict:
    """The per-pixel wall mask, row-RLE encoded: rows[y] = [x0, len, x0, len, …]."""
    import numpy as np

    wall = np.load(NAV_NPZ)["wall"]
    rows = []
    for y in range(wall.shape[0]):
        runs, x = [], 0
        row = wall[y]
        w = row.shape[0]
        while x < w:
            if row[x]:
                x0 = x
                while x < w and row[x]:
                    x += 1
                runs.extend([x0, x - x0])
            else:
                x += 1
        rows.append(runs)
    return {"w": int(wall.shape[1]), "h": int(wall.shape[0]), "rows": rows}


def build_bundle(ep_dir: Path, expand_bin: Path) -> dict:
    replay = _find_replay(ep_dir)
    if replay is None:
        raise SystemExit(f"no replay in {ep_dir}")
    log(f"expanding {replay.name} (pos_every=1)…")
    rows = _expand(replay, expand_bin)

    episode = {}
    ej = ep_dir / "episode.json"
    if ej.exists():
        e = json.loads(ej.read_text())
        episode = {
            "id": e.get("id"),
            "coworld_version": e.get("coworld_version"),
            "participants": [
                {"slot": p.get("position"), "policy": p.get("policy_name"),
                 "version": p.get("version"), "player": p.get("player_name")}
                for p in e.get("participants") or []
            ],
        }

    traces = _traces(ep_dir)
    offsets = _align(traces, rows)
    log(f"traces: {len(traces)} slots, offsets {offsets}")

    # Split replay rows: per-tick pos/flag streams (dense) vs the event timeline (sparse).
    pos_rows, flag_rows, events = [], [], []
    for r in rows:
        k = r.get("key")
        if k == "pos":
            pos_rows.append(r)
        elif k == "flag_pos":
            flag_rows.append(r)
        elif k != "_meta":
            events.append(r)

    return {
        "episode": episode,
        "wall": _wall_runs(),
        "pos": pos_rows,
        "flags": flag_rows,
        "events": events,
        "traces": {str(s): recs for s, recs in traces.items()},
        "trace_offsets": {str(s): off for s, off in offsets.items()},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode_dir", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None,
                    help="output bundle path (default: <episode_dir>/viewer_bundle.json)")
    ap.add_argument("--expand-replay", type=Path, default=DEFAULT_EXPAND)
    args = ap.parse_args()

    bundle = build_bundle(args.episode_dir, args.expand_replay)
    out = args.out or (args.episode_dir / "viewer_bundle.json")
    out.write_text(json.dumps(bundle, separators=(",", ":")))
    log(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    log(f"view: open ctf_lab/tools/viewer.html and load it, or "
        f"python3 -m http.server — file:// works too (single fetch via file picker)")


if __name__ == "__main__":
    main()
