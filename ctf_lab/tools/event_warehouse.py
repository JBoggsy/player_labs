"""CTF event warehouse — a policy-indexed DuckDB/Parquet dataset of gameplay events.

The lean CTF analogue of Crewrift's warehouse (one file, not two packages): it turns a
set of episode artifact dirs into a queryable store so you can ask cross-episode,
by-policy, by-team, by-role questions in SQL — e.g. "what fraction of flag steals get
delivered", "where do carriers die on the return", "is the escort actually near the
carrier". Two event feeds, both re-keyed from episode *slot* to
**policy / version / team / seat / role**:

  * **replay events** (ground truth) — from the version-matched `expand_replay_json`
    binary (`tools/build_expand_replay.sh`): kill / flag_steal / flag_return_home /
    capture / respawn / score / phase / game_over, with tick + actor slot.
  * **beacon trace events** (belief/decision side) — from beacon's per-episode trace
    (the `jsonl@artifact` member, or the folded `CTF_DIAG` policy log): snapshot /
    objective / alive / engage, with the full belief payload.

Tables written (DuckDB `warehouse.duckdb` + one Parquet per table):
  * ``episodes``     — one row per episode (ids, coworld version, winner, per-team score)
  * ``participants`` — one row per (episode, slot): policy/version/team/seat/role/outcome
  * ``replay_events``— one row per replay event, joined to the actor's participant
  * ``trace_events`` — one row per beacon trace event (belief snapshots + transitions)

Usage:
    uv run python ctf_lab/tools/event_warehouse.py \
        --episodes ctf_lab/scratch/eval_v5_baseline \
        --out ctf_lab/scratch/wh_v5 \
        [--expand-replay ctf_lab/tools/bin/expand_replay_json]

`--episodes` may be repeated / point at a dir of episode subdirs. The replay-JSON binary
defaults to the stable symlink built by build_expand_replay.sh; build it first.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import duckdb

DEFAULT_EXPAND = Path(__file__).resolve().parent / "bin" / "expand_replay_json"


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# Slot -> identity resolution (the re-keying that makes cross-episode queries work)
# --------------------------------------------------------------------------- #
def _team_for_slot(slot: int) -> str:
    return "red" if slot % 2 == 0 else "blue"


def _seat_for_slot(slot: int) -> int:
    return slot // 2


def _role_for_seat(seat: int, defender_count: int) -> str:
    return "defender" if seat < defender_count else "attacker"


def _load_episode_meta(ep_dir: Path) -> dict[str, Any] | None:
    """Read episode.json + results.json into a normalized per-slot identity table."""
    ep_path = ep_dir / "episode.json"
    res_path = ep_dir / "results.json"
    if not ep_path.exists():
        return None
    episode = json.loads(ep_path.read_text())
    results = json.loads(res_path.read_text()) if res_path.exists() else {}

    participants = episode.get("participants", [])
    scores = results.get("scores", [])
    wins = results.get("win", [])
    teams_res = results.get("team", [])
    kills = results.get("kills", [])
    deaths = results.get("deaths", [])
    captures = results.get("captures", [])

    # Guess DEFENDER_COUNT only to label beacon's roles; other policies get role=None.
    # beacon:v2-v4 => 5 defenders, v5 => 3. Resolve per-participant from its version.
    slot_rows: list[dict[str, Any]] = []
    for p in participants:
        slot = p.get("position", 0)
        policy = p.get("policy_name")
        version = p.get("version")
        defender_count = _beacon_defender_count(policy, version)
        seat = _seat_for_slot(slot)
        slot_rows.append({
            "episode_id": episode.get("id"),
            "slot": slot,
            "policy_name": policy,
            "policy_version": version,
            "policy_version_id": p.get("policy_version_id"),
            "player_name": p.get("player_name"),
            "team": teams_res[slot] if slot < len(teams_res) else _team_for_slot(slot),
            "seat": seat,
            "role": _role_for_seat(seat, defender_count) if defender_count is not None else None,
            "score": scores[slot] if slot < len(scores) else None,
            "win": wins[slot] if slot < len(wins) else None,
            "kills": kills[slot] if slot < len(kills) else None,
            "deaths": deaths[slot] if slot < len(deaths) else None,
            "captures": captures[slot] if slot < len(captures) else None,
        })

    red_score = sum(r["score"] or 0 for r in slot_rows if r["team"] == "red")
    blue_score = sum(r["score"] or 0 for r in slot_rows if r["team"] == "blue")
    winner = "red" if red_score > blue_score else "blue" if blue_score > red_score else "draw"
    ep_row = {
        "episode_id": episode.get("id"),
        "round_id": episode.get("round_id"),
        "coworld_version": episode.get("coworld_version"),
        "status": episode.get("status"),
        "job_id": episode.get("job_id"),
        "winner": winner,
        "red_score": red_score,
        "blue_score": blue_score,
        "n_participants": len(slot_rows),
    }
    return {"episode": ep_row, "slots": slot_rows}


def _beacon_defender_count(policy: str | None, version: int | None) -> int | None:
    """beacon's DEFENDER_COUNT by version (for role labelling). None for non-beacon."""
    if policy != "beacon" or version is None:
        return None
    return 3 if version >= 5 else 5  # v5 shifted 5->3


# --------------------------------------------------------------------------- #
# Replay events (ground truth) via the expand_replay_json binary
# --------------------------------------------------------------------------- #
def _find_replay(ep_dir: Path) -> Path | None:
    for name in ("replay.json", "replay.bitreplay"):
        p = ep_dir / name
        if p.exists():
            return p
    return None


def _expand_replay_events(replay: Path, expand_bin: Path) -> tuple[list[dict], dict]:
    """Run the JSONL emitter; return (event rows, meta). Empty on hash-fail/error."""
    try:
        proc = subprocess.run(
            [str(expand_bin), str(replay)],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"  ! expand_replay_json failed on {replay}: {exc}")
        return [], {"hash_failed": True, "error": str(exc)}
    rows, meta = [], {}
    for line in proc.stdout.splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if obj.get("key") == "_meta":
            meta = obj.get("value", {})
        else:
            rows.append(obj)
    if proc.returncode != 0:
        log(f"  ! expand_replay_json exit {proc.returncode} on {replay.parent.name} "
            f"(hash_failed={meta.get('hash_failed')}) — skipping its replay events")
        # A hash fail means version skew; keep meta so the caller can flag it.
    return rows, meta


# --------------------------------------------------------------------------- #
# beacon trace events (belief/decision side)
# --------------------------------------------------------------------------- #
def _load_trace_events(ep_dir: Path) -> list[dict]:
    """Beacon trace records from the folded CTF_DIAG policy logs (one per beacon slot).

    Records look like ``CTF_DIAG <name> {json}`` (stderr fallback) or structured
    ``{"kind":"trace","tick":..,"name":..,"data":{..}}`` lines (artifact). We accept both
    and tag each with the emitting slot (parsed from the log's header line)."""
    out: list[dict] = []
    logs_dir = ep_dir / "logs"
    if not logs_dir.is_dir():
        return out
    for log_file in sorted(logs_dir.glob("*.log")):
        raw = _decode_log(log_file.read_bytes())
        slot = _slot_from_log_header(raw)
        if slot is None:
            continue  # not a beacon log
        for line in raw.splitlines():
            rec = _parse_trace_line(line)
            if rec is not None:
                rec["slot"] = slot
                out.append(rec)
    return out


def _decode_log(data: bytes) -> str:
    """Decode a policy log to text. The artifact fetcher sometimes stores logs as a
    Python bytes-repr string (literally ``b'...\\n...'``) rather than raw text; detect
    that and unescape it so ``splitlines()`` sees real lines."""
    text = data.decode("utf-8", "replace")
    if text[:2] in ("b'", 'b"'):
        try:
            return ast.literal_eval(text).decode("utf-8", "replace")
        except (ValueError, SyntaxError):
            return text.encode("utf-8").decode("unicode_escape", "replace")
    return text


def _slot_from_log_header(raw: str) -> int | None:
    # beacon's first stderr line: "beacon: team=red seat=0 url=...slot=0&..."
    head = raw[:200]
    if "beacon:" not in head:
        return None
    marker = "slot="
    idx = head.find(marker)
    if idx < 0:
        return None
    digits = ""
    for ch in head[idx + len(marker):]:
        if ch.isdigit():
            digits += ch
        else:
            break
    return int(digits) if digits else None


def _parse_trace_line(line: str) -> dict | None:
    if "CTF_DIAG " in line:  # stderr-fallback form
        try:
            _, rest = line.split("CTF_DIAG ", 1)
            name, payload = rest.split(" ", 1)
            data = json.loads(payload)
            return {"tick": data.pop("tick", None), "name": name, "data": data}
        except (ValueError, KeyError):
            return None
    stripped = line.strip()
    if stripped.startswith("{") and '"kind":"trace"' in stripped.replace(" ", ""):
        try:
            obj = json.loads(stripped)
            return {"tick": obj.get("tick"), "name": obj.get("name"), "data": obj.get("data", {})}
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def _episode_dirs(paths: Iterable[Path]) -> list[Path]:
    """Expand each path into episode dirs (a dir containing episode.json, or a parent)."""
    dirs: list[Path] = []
    for p in paths:
        if (p / "episode.json").exists():
            dirs.append(p)
        elif p.is_dir():
            dirs.extend(sorted(d for d in p.iterdir() if (d / "episode.json").exists()))
    return dirs


def build_warehouse(episode_paths: list[Path], out_dir: Path, expand_bin: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    dirs = _episode_dirs(episode_paths)
    if not dirs:
        log("no episode dirs found (need dirs containing episode.json)")
        return
    log(f"building warehouse from {len(dirs)} episodes -> {out_dir}")

    episodes, participants, replay_events, trace_events = [], [], [], []
    slot_identity: dict[tuple[str, int], dict] = {}
    skew = 0

    for ep_dir in dirs:
        meta = _load_episode_meta(ep_dir)
        if meta is None:
            continue
        eid = meta["episode"]["episode_id"]
        episodes.append(meta["episode"])
        for row in meta["slots"]:
            participants.append(row)
            slot_identity[(eid, row["slot"])] = row

        replay = _find_replay(ep_dir)
        if replay is not None:
            rows, rmeta = _expand_replay_events(replay, expand_bin)
            if rmeta.get("hash_failed"):
                skew += 1
            for r in rows:
                ident = slot_identity.get((eid, r.get("player")), {})
                replay_events.append({
                    "episode_id": eid,
                    "tick": r.get("ts"),
                    "key": r.get("key"),
                    "actor_slot": r.get("player"),
                    "actor_policy": ident.get("policy_name"),
                    "actor_version": ident.get("policy_version"),
                    "actor_team": ident.get("team"),
                    "actor_seat": ident.get("seat"),
                    "actor_role": ident.get("role"),
                    "value_json": json.dumps(r.get("value", {})),
                })

        for t in _load_trace_events(ep_dir):
            ident = slot_identity.get((eid, t.get("slot")), {})
            data = t.get("data", {})
            trace_events.append({
                "episode_id": eid,
                "tick": t.get("tick"),
                "name": t.get("name"),
                "slot": t.get("slot"),
                "policy_name": ident.get("policy_name"),
                "policy_version": ident.get("policy_version"),
                "team": ident.get("team"),
                "seat": ident.get("seat"),
                "role": ident.get("role"),
                "self_x": (data.get("self_xy") or [None, None])[0],
                "self_y": (data.get("self_xy") or [None, None])[1],
                "objective": data.get("objective") or data.get("to"),
                "alive": data.get("alive"),
                "i_carry": data.get("i_carry"),
                "n_enemies": data.get("n_enemies"),
                "data_json": json.dumps(data),
            })

    con = duckdb.connect(str(out_dir / "warehouse.duckdb"))
    _write_table(con, "episodes", episodes, out_dir)
    _write_table(con, "participants", participants, out_dir)
    _write_table(con, "replay_events", replay_events, out_dir)
    _write_table(con, "trace_events", trace_events, out_dir)
    con.close()

    log(f"done: {len(episodes)} episodes, {len(participants)} participants, "
        f"{len(replay_events)} replay events, {len(trace_events)} trace events")
    if skew:
        log(f"  ! {skew} episode(s) hash-failed expansion (version skew — bump CTF_REF); "
            f"their replay events are absent")
    log(f"query it:  duckdb {out_dir / 'warehouse.duckdb'}")


def _write_table(con, name: str, rows: list[dict], out_dir: Path) -> None:
    """Create a DuckDB table + a Parquet mirror from a list of dict rows."""
    if not rows:
        log(f"  (table {name}: 0 rows — skipped)")
        return
    import pyarrow as pa

    cols = list(rows[0].keys())
    arrow_rows = pa.table({c: [r.get(c) for r in rows] for c in cols})  # DuckDB scans by name
    con.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM arrow_rows')
    con.execute(f"COPY \"{name}\" TO '{out_dir / (name + '.parquet')}' (FORMAT PARQUET)")
    log(f"  table {name}: {len(rows)} rows")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the CTF event warehouse.")
    ap.add_argument("--episodes", action="append", required=True, type=Path,
                    help="episode dir (containing episode.json) or a parent of such dirs; repeatable")
    ap.add_argument("--out", required=True, type=Path, help="output dir for warehouse.duckdb + parquet")
    ap.add_argument("--expand-replay", type=Path, default=DEFAULT_EXPAND,
                    help="path to the expand_replay_json binary (default: tools/bin/expand_replay_json)")
    args = ap.parse_args()

    if not args.expand_replay.exists():
        log(f"WARNING: expand_replay_json not found at {args.expand_replay} — "
            f"replay events will be empty. Build it: ctf_lab/tools/build_expand_replay.sh")
    build_warehouse(args.episodes, args.out, args.expand_replay)


if __name__ == "__main__":
    main()
