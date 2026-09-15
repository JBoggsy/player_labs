"""Paintbot event warehouse — a policy-indexed DuckDB/Parquet dataset of gameplay events.

The inherited CTF-based analogue of Crewrift's warehouse (one file, not two packages): it turns a
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

Outcome normalization supports two/four-team Paintbot results. The Beacon trace
parser below remains format-specific; use Stencil viewer tools for Stencil traces.
Role columns are retained as null: team/seat alone does not establish a role.
Invalid identity or contradictory outcomes abort the build so exclusions cannot
silently change the evidence cohort; repair or explicitly exclude that input.

Tables written (DuckDB `warehouse.duckdb` + one Parquet per table):
  * ``episodes``     — one row per episode (ids, coworld version, winner, per-team score)
  * ``participants`` — one row per (episode, slot): policy/version/team/seat/role/outcome
  * ``replay_events``— one row per replay event, joined to the actor's participant
  * ``trace_events`` — one row per beacon trace event (belief snapshots + transitions)

Usage:
    uv run python paintbot_lab/tools/event_warehouse.py \
        --episodes paintbot_lab/scratch/eval_v5_baseline \
        --out paintbot_lab/scratch/wh_v5 \
        [--replay-only] \
        [--expand-replay paintbot_lab/tools/bin/expand_replay_json]

`--episodes` may be repeated / point at a dir of episode subdirs. The replay-JSON binary
defaults to the stable symlink built by build_expand_replay.sh; build it first.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

import duckdb

DEFAULT_EXPAND = Path(__file__).resolve().parent / "bin" / "expand_replay_json"


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# Slot -> identity resolution (the re-keying that makes cross-episode queries work)
# --------------------------------------------------------------------------- #
def _load_episode_meta(ep_dir: Path) -> dict[str, Any] | None:
    """Normalize completed artifact outcomes without inferring teams from slot parity."""
    ep_path, res_path = ep_dir / "episode.json", ep_dir / "results.json"
    if not ep_path.exists():
        return None
    episode = json.loads(ep_path.read_text())
    results = json.loads(res_path.read_text()) if res_path.exists() else {}
    eid = episode.get("id") or ep_dir.name
    participants = episode.get("participants") or []
    if not participants:
        participants = []
        for entry in episode.get("policy_results") or []:
            policy = entry.get("policy") or {}
            positions = ([entry["position"]] if entry.get("position") is not None else
                         [agent["agent_id"] for agent in entry.get("agents") or []])
            participants.extend({
                "position": slot, "policy_name": policy.get("name"),
                "version": policy.get("version"), "policy_version_id": policy.get("id"),
            } for slot in positions)
    config_slots = (episode.get("game_config") or {}).get("slots") or []
    teams = results.get("team") or [slot.get("team") for slot in config_slots]
    if config_slots and teams != [slot.get("team") for slot in config_slots]:
        raise ValueError(f"{eid}: results team order differs from game_config.slots")
    rows = []
    seen = set()
    for participant in participants:
        slot = participant["position"]
        if not isinstance(slot, int) or slot < 0 or slot in seen:
            raise ValueError(f"{eid}: invalid or duplicate participant slot {slot}")
        seen.add(slot)
        team = teams[slot] if slot < len(teams) else None
        row = {
            "episode_id": eid, "slot": slot,
            "policy_name": participant.get("policy_name"),
            "policy_version": participant.get("version"),
            "policy_version_id": participant.get("policy_version_id"),
            "player_name": participant.get("player_name"),
            "team": team,
            "seat": sum(value == team for value in teams[:slot]) if team is not None else None,
            "role": None,
        }
        for output, source in [("score", "scores"), ("win", "win"), ("kills", "kills"),
                               ("deaths", "deaths"), ("captures", "captures")]:
            values = results.get(source) or []
            row[output] = values[slot] if slot < len(values) else None
        rows.append(row)
    wins = results.get("win") or []
    complete = (episode.get("status") == "completed" and not episode.get("error_type")
                and episode.get("failed_policy_index") is None
                and episode.get("failed_agent_index") is None
                and not any(results.get("connect_timeout") or [])
                and not any(results.get("disconnect_timeout") or []))
    have_outcome = (complete and len(wins) == len(teams) and bool(teams)
                    and all(win in (True, False) for win in wins)
                    and all(team in {"red", "blue", "green", "yellow"} for team in teams))
    winner = None
    if have_outcome:
        winning_teams = {team for team, win in zip(teams, wins) if win}
        if len(winning_teams) > 1 or any(
            len({win for team, win in zip(teams, wins) if team == color}) != 1
            for color in set(teams)
        ):
            raise ValueError(f"{eid}: contradictory team win flags")
        winner = next(iter(winning_teams), "draw")
    ep_row = {
        "episode_id": eid, "round_id": episode.get("round_id"),
        "coworld_version": episode.get("coworld_version"),
        "status": episode.get("status"), "job_id": episode.get("job_id"),
        "winner": winner, "n_participants": len(rows),
    }
    for color in ("red", "blue", "green", "yellow"):
        values = [row["score"] for row in rows if row["team"] == color]
        ep_row[f"{color}_score"] = (
            sum(values) if values and all(value is not None for value in values) else None
        )
    return {"episode": ep_row, "slots": rows}


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
    """Beacon trace records for one episode, from BOTH trace transports:

    1. **Artifact zips** (the default since v18: ``jsonl@artifact``):
       ``artifacts/policy_artifact_<slot>.zip`` containing ``telemetry.jsonl`` with
       ``{"kind":"trace","tick":..,"event":..,"name":..,"data":{..}}`` lines. The
       slot is parsed from the zip filename (the runner names them by slot).
    2. **Policy logs** (the stderr fallback): ``logs/*.log`` with
       ``CTF_DIAG <name> {json}`` lines, slot parsed from the log's header line.

    Both are tagged with the emitting slot. Prior to 2026-07-27 only (2) was read,
    so the trace table was silently EMPTY whenever traces went to the artifact
    (which is the default) — every event also carries seat/team in its data since
    beacon v28, so downstream queries should prefer those fields."""
    out: list[dict] = []
    art_dir = ep_dir / "artifacts"
    if art_dir.is_dir():
        for zpath in sorted(art_dir.glob("policy_artifact_*.zip")):
            try:
                slot = int(zpath.stem.rsplit("_", 1)[1])
            except (ValueError, IndexError):
                continue
            try:
                with zipfile.ZipFile(zpath) as zf:
                    names = [n for n in zf.namelist() if n.endswith("telemetry.jsonl")]
                    for name in names:
                        for line in zf.read(name).decode("utf-8", "replace").splitlines():
                            rec = _parse_trace_line(line)
                            if rec is not None:
                                rec["slot"] = slot
                                out.append(rec)
            except (zipfile.BadZipFile, OSError):
                continue
    if out:
        return out
    # Fallback: stderr-format traces folded into the policy logs.
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


def build_warehouse(
    episode_paths: list[Path],
    out_dir: Path,
    expand_bin: Path,
    *,
    include_traces: bool = True,
) -> None:
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

        for t in _load_trace_events(ep_dir) if include_traces else ():
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
                # Squad-command state (v27+ traces; None on older data). For `order`
                # transition events these are the event payload; for snapshots the
                # live order state.
                "order_goal": data.get("goal") or (data.get("order") or [None])[0],
                "order_source": data.get("source") or data.get("order_source"),
                "enemy_lives_left": data.get("enemy_lives_left"),
                "data_json": json.dumps(data),
            })

    # Engine-tick alignment (v27 tracing): a bot's trace `tick` is its own frame
    # counter since websocket connect — NOT the engine tick — and the offset varies
    # per slot (connect order) and per episode. All players spawn at the engine's
    # phase=Playing tick, so per (episode, slot):
    #   eng_tick = tick + (replay Playing tick - first trace alive=true tick).
    # Stamped as a real column so cross-bot queries just GROUP BY eng_tick.
    playing_tick: dict[str, int] = {}
    for r in replay_events:
        if r["key"] == "phase" and "Playing" in r["value_json"]:
            playing_tick.setdefault(r["episode_id"], r["tick"])
    first_spawn: dict[tuple[str, int], int] = {}
    for t in trace_events:
        if t["name"] == "alive" and t.get("alive") and t.get("tick") is not None:
            key = (t["episode_id"], t["slot"])
            if key not in first_spawn or t["tick"] < first_spawn[key]:
                first_spawn[key] = t["tick"]
    for t in trace_events:
        key = (t["episode_id"], t["slot"])
        base = playing_tick.get(t["episode_id"])
        spawn = first_spawn.get(key)
        t["eng_tick"] = (
            t["tick"] + (base - spawn)
            if t.get("tick") is not None and base is not None and spawn is not None
            else None
        )

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
    ap.add_argument("--replay-only", action="store_true",
                    help="skip policy telemetry when only ground-truth replay events are needed")
    args = ap.parse_args()

    if not args.expand_replay.exists():
        log(f"WARNING: expand_replay_json not found at {args.expand_replay} — "
            f"replay events will be empty. Build it: paintbot_lab/tools/build_expand_replay.sh")
    build_warehouse(
        args.episodes,
        args.out,
        args.expand_replay,
        include_traces=not args.replay_only,
    )


if __name__ == "__main__":
    main()
