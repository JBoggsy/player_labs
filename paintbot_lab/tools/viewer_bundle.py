"""Bundle one CTF-family episode for the belief-overlay replay viewer.

Supports both fixed-map Beacon/CTF and generated-map Stencil/Paintbot episodes.

Packages everything the viewer needs into a single JSON file:

  * **ground truth** — per-tick player/flag positions + the full event timeline,
    from the version-matched ``expand_replay_json`` binary run at ``pos_every=1``
    (build it first: ``tools/build_expand_replay.sh``);
  * **agent traces** — every bot's telemetry.jsonl from the episode's
    ``artifacts/policy_artifact_<slot>.zip`` (snapshots, order/objective/micro
    transitions, heard_chat/heard_sound events), tick-aligned to the engine axis
    the same way the warehouse does it (first spawn <-> phase=Playing);
  * **the map** — the exact per-pixel startup walkability mask emitted by the
    replay expander, with traced ``navigation_map`` and Beacon's baked
    ``nav.npz`` retained only as legacy fallbacks; the viewer draws walls and
    clips vision rays against them.

Usage:
    uv run python paintbot_lab/tools/viewer_bundle.py <episode_dir> [-o out.json]
    # then open paintbot_lab/tools/viewer.html and pick the bundle,
    # or serve both:  python -m http.server -d <dir>

``<episode_dir>`` is one fetched episode (needs replay.json/replay.bitreplay +
artifacts/*.zip for the overlay; runs without artifacts with overlays disabled).
The replay expander must match the episode's game version.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

LAB_DIR = Path(__file__).resolve().parent.parent          # paintbot_lab/
DEFAULT_EXPAND = LAB_DIR / "tools" / "bin" / "expand_replay_json"
# Beacon's baked CTF arena, used ONLY for fixed-map CTF episodes (allow_baked).
# ctf_lab is archived, so this reaches into the archive rather than moving with the
# tool; Paintbot episodes never touch it — they carry their own walkability mask.
NAV_NPZ = LAB_DIR.parent / "ctf_lab" / "ctf" / "beacon" / "mapdata" / "nav.npz"


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
        [str(expand_bin), str(replay), "1", "walkability"],
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
        # Lab-neutral: this bundler serves both CTF and Paintbot episodes, and a
        # Paintbot user following "bump CTF_REF" would build at the wrong game.
        log(
            f"! hash failed at tick {meta.get('fail_tick')} — the reader was built from a "
            f"different game version than recorded this replay. Rebuild at the episode's "
            f"source commit: paintbot_lab/tools/build_expand_replay.sh --ref <sha>."
        )
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
                      if r["name"] == "alive" and r["data"].get("alive", True)), None)
        if spawn is not None:
            offsets[slot] = playing - spawn
    return offsets


def _validated_replay_wall(replay_rows: list[dict]) -> dict | None:
    """Return the exact replay-start wall mask, rejecting malformed geometry."""
    wall = next(
        (row.get("value") for row in replay_rows if row.get("key") == "walkability_map"),
        None,
    )
    if wall is None:
        return None
    if wall.get("encoding") != "wall-runs-v1":
        raise ValueError(f"unsupported walkability encoding: {wall.get('encoding')}")
    width, height, rows = wall.get("w"), wall.get("h"), wall.get("rows")
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise ValueError("walkability map has invalid dimensions")
    if not isinstance(rows, list) or len(rows) != height:
        raise ValueError("walkability map row count does not match its height")
    for y, runs in enumerate(rows):
        if not isinstance(runs, list) or len(runs) % 2:
            raise ValueError(f"walkability row {y} is not x/length pairs")
        for index in range(0, len(runs), 2):
            start, length = runs[index:index + 2]
            if (not isinstance(start, int) or not isinstance(length, int) or
                    start < 0 or length <= 0 or start + length > width):
                raise ValueError(f"walkability row {y} has an invalid run")
    return {"w": width, "h": height, "rows": rows}


def _wall_runs(
    traces: dict[int, list[dict]], replay_rows: list[dict], *, allow_baked: bool
) -> dict:
    """The per-pixel wall mask, row-RLE encoded: rows[y] = [x0, len, x0, len, …]."""
    replay_wall = _validated_replay_wall(replay_rows)
    if replay_wall is not None:
        return replay_wall

    navigation = next(
        (
            record["data"]
            for records in traces.values()
            for record in records
            if record["name"] == "navigation_map"
        ),
        None,
    )
    if navigation is not None:
        map_w, map_h = navigation["map"]
        grid_w, grid_h = navigation["grid"]
        cell = navigation["cell_size"]
        walkable = navigation["walkable_rows"]
        rows = []
        for y in range(map_h):
            grid_y = min(y // cell, grid_h - 1)
            runs = []
            x = 0
            while x < map_w:
                grid_x = min(x // cell, grid_w - 1)
                x_next = min((x // cell + 1) * cell, map_w)
                if walkable[grid_y][grid_x] == "0":
                    if runs and runs[-2] + runs[-1] == x:
                        runs[-1] += x_next - x
                    else:
                        runs.extend([x, x_next - x])
                x = x_next
            rows.append(runs)
        return {"w": map_w, "h": map_h, "rows": rows}

    if not allow_baked:
        raise ValueError(
            "Paintbot replay has no startup walkability_map; rebuild its "
            "exact-version expand_replay_json reader"
        )

    import numpy as np

    wall = np.load(NAV_NPZ)["wall"]
    traced_size = next(
        (
            record["data"].get("worldmap")
            for records in traces.values()
            for record in records
            if record["name"] == "worldmap" and record["data"].get("worldmap")
        ),
        None,
    )
    if traced_size is not None and [wall.shape[1], wall.shape[0]] != [
            traced_size.get("w"), traced_size.get("h")]:
        raise ValueError(
            "replay expander did not emit walkability_map and the traced map "
            f"is {traced_size.get('w')}x{traced_size.get('h')}, not Beacon's "
            f"{wall.shape[1]}x{wall.shape[0]}; rebuild the exact-version replay reader"
        )
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
        game_config = e.get("game_config") or {}
        slots = game_config.get("slots") or []
        participants = []
        for participant in e.get("participants") or []:
            slot = participant.get("position")
            team = None
            if isinstance(slot, int) and slot < len(slots):
                team = slots[slot].get("team")
            participants.append({
                "slot": slot,
                "policy": participant.get("policy_name"),
                "version": participant.get("version"),
                "player": participant.get("player_name"),
                "team": team,
            })
        episode = {
            "id": e.get("id"),
            "coworld_name": e.get("coworld_name"),
            "coworld_version": e.get("coworld_version"),
            "variant_name": e.get("variant_name"),
            "teams": game_config.get("teams"),
            "participants": participants,
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
        elif k not in {"_meta", "walkability_map"}:
            events.append(r)

    return {
        "episode": episode,
        "wall": _wall_runs(
            traces, rows, allow_baked=episode.get("coworld_name") != "paintbot"
        ),
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
    log(f"view: open paintbot_lab/tools/viewer.html and load it, or "
        f"python3 -m http.server — file:// works too (single fetch via file picker)")


if __name__ == "__main__":
    main()
