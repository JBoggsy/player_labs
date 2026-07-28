#!/usr/bin/env python3
"""Sync crewborg's belief telemetry into an event warehouse as belief_* partitions.

The warehouse holds objective replay ground truth; crewborg's policy-artifact
telemetry holds what it perceived/believed/decided. This script joins them into
ONE queryable dataset: for every subject seat it extracts the belief-relevant
domain.* trace events and writes them as native warehouse partitions
(events/key=belief_<name>/…), so ground truth and belief share (episode_id, ts)
and one SQL query can read both sides.

Why the join is trustworthy:
  - telemetry `tick` IS the server tick (the bridge drives the SDK runtime from
    the engine's tick-marker sprite — crewborg/docs/trace-logs.md "Line format"),
    so belief ticks align to warehouse `ts` directly, no offset estimation.
    The sync-check pass (on by default) verifies this per episode by comparing
    domain.phase_change ticks against the replay's phase events; a large offset
    means a broken episode (reconnect/stall), and the episode is flagged.
  - identity: crewborg speaks COLORS, the warehouse speaks SLOTS. Each belief
    row's value is enriched at write time with `truth_roles` — a {color: role}
    map (ground truth from the replay player_manifest) for every color the
    payload mentions — plus self_color/self_slot, so divergence queries never
    need the artifact zips again.

Usage (episodes fetched by coworld-episode-artifacts, warehouse already built):
    uv run python crewrift_lab/.claude/skills/crewrift-belief-audit/scripts/build_belief_log.py \
        --warehouse /tmp/wh --episodes /tmp/wh_episodes [--policy crewborg] \
        [--include domain.decision_snapshot] [--no-sync-check]

Idempotent: re-running rewrites the belief_* partitions from scratch.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from belief_common import (  # noqa: E402
    BELIEF_EVENTS,
    EpisodeIdentity,
    SubjectSeat,
    belief_key,
    connect,
    episode_identities,
    events_glob,
    find_subject_seats,
    iter_telemetry,
)

# Mirrors crewrift_event_warehouse.schema.EVENTS_SCHEMA (the vendored package is
# not importable from the repo root env; the 8-column shape is stable).
EVENTS_SCHEMA = pa.schema(
    [
        ("ts", pa.int64()),
        ("episode_id", pa.string()),
        ("slot", pa.int32()),
        ("policy_version", pa.string()),
        ("policy_name", pa.string()),
        ("role", pa.string()),
        ("key", pa.string()),
        ("value", pa.string()),
    ]
)

# Belief clock vs server clock tolerance for the phase-alignment sync check.
# Trace ticks are server ticks, so genuine offsets should be ~0-2 ticks; a
# large offset marks a degraded episode (reconnect stall / marker loss).
SYNC_TOL_TICKS = 30


def harvest_colors(data: object, into: set[str]) -> None:
    """Collect every player-color string mentioned anywhere in a belief payload.

    Colors appear under many field names (color, target, added, believed,
    teammate_colors, ranking[].color, …); rather than schema-per-event, harvest
    every string value that looks like a color and let the identity map filter —
    only strings that ARE a color in this episode survive the truth_roles join.
    """
    if isinstance(data, dict):
        for v in data.values():
            harvest_colors(v, into)
    elif isinstance(data, list):
        for v in data:
            harvest_colors(v, into)
    elif isinstance(data, str) and 0 < len(data) <= 12 and data.isalpha():
        into.add(data.lower())


def enrich(data: dict, ident: EpisodeIdentity, seat: SubjectSeat) -> dict:
    mentioned: set[str] = set()
    harvest_colors(data, mentioned)
    truth = {
        c: ident.slot_role.get(ident.color_to_slot[c])
        for c in sorted(mentioned)
        if c in ident.color_to_slot
    }
    out = dict(data)
    out["truth_roles"] = truth
    out["self_slot"] = seat.slot
    out["self_color"] = ident.slot_to_color.get(seat.slot)
    return out


def phase_sync_offset(
    belief_phases: list[tuple[int, str]], truth_phases: list[tuple[int, str]]
) -> int | None:
    """Median |belief tick - nearest truth tick| over same-named phase entries.
    None when either side is empty."""
    if not belief_phases or not truth_phases:
        return None
    offsets: list[int] = []
    for tick, phase in belief_phases:
        candidates = [ts for ts, p in truth_phases if p == phase]
        if candidates:
            offsets.append(min(abs(tick - ts) for ts in candidates))
    if not offsets:
        return None
    offsets.sort()
    return offsets[len(offsets) // 2]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--warehouse", type=Path, required=True, help="Built event-warehouse dir.")
    ap.add_argument("--episodes", type=Path, required=True,
                    help="Fetched episode dirs (with artifacts/policy_artifact_<slot>.zip).")
    ap.add_argument("--policy", action="append", default=None,
                    help="Subject policy name(s); repeatable. Default: crewborg.")
    ap.add_argument("--include", action="append", default=[],
                    help="Extra domain.* event names to extract beyond the default belief set.")
    ap.add_argument("--no-sync-check", action="store_true",
                    help="Skip the per-episode phase-alignment verification.")
    args = ap.parse_args(argv)
    policies = set(args.policy or ["crewborg"])
    wanted = set(BELIEF_EVENTS) | set(args.include)

    st: Counter = Counter()
    seats = find_subject_seats(args.warehouse, args.episodes, policies, st)
    if not seats:
        print(f"no subject seats found (policies={sorted(policies)}); stats={dict(st)}", file=sys.stderr)
        return 1

    con = connect(args.warehouse)
    idents = episode_identities(con, args.warehouse)

    # Ground-truth phase timeline per episode, for the sync check.
    truth_phases: dict[str, list[tuple[int, str]]] = {}
    if not args.no_sync_check:
        import glob as _glob
        if _glob.glob(events_glob(args.warehouse, "phase")):
            for ep, ts, phase in con.execute(
                f"SELECT episode_id, ts, json_extract_string(value,'$.phase') "
                f"FROM read_parquet('{events_glob(args.warehouse, 'phase')}') ORDER BY ts"
            ).fetchall():
                truth_phases.setdefault(ep, []).append((int(ts), phase))

    # rows per partition key
    parts: dict[str, dict[str, list]] = {}
    sync_report: list[dict] = []

    def cols_for(key: str) -> dict[str, list]:
        return parts.setdefault(
            key, {c: [] for c in ("ts", "episode_id", "slot", "policy_version",
                                  "policy_name", "role", "key", "value")}
        )

    for seat in seats:
        ident = idents.get(seat.episode_id)
        if ident is None:
            st["no_identity"] += 1
            continue
        belief_phase_ticks: list[tuple[int, str]] = []
        n_events = 0
        for tick, name, data in iter_telemetry(seat.zip_path, wanted):
            if name == "domain.phase_change":
                to_phase = data.get("to")
                if isinstance(to_phase, str):
                    belief_phase_ticks.append((tick, to_phase))
            key = belief_key(name)
            cols = cols_for(key)
            cols["ts"].append(tick)
            cols["episode_id"].append(seat.episode_id)
            cols["slot"].append(seat.slot)
            cols["policy_version"].append(seat.policy_version)
            cols["policy_name"].append(seat.policy_name)
            cols["role"].append(seat.role)
            cols["key"].append(key)
            cols["value"].append(json.dumps(enrich(data, ident, seat)))
            n_events += 1
        st["events"] += n_events
        if n_events == 0:
            st["empty_telemetry"] += 1

        if not args.no_sync_check:
            offset = phase_sync_offset(belief_phase_ticks, truth_phases.get(seat.episode_id, []))
            ok = offset is not None and offset <= SYNC_TOL_TICKS
            sync_report.append({
                "episode_id": seat.episode_id, "slot": seat.slot,
                "phase_offset_ticks": offset, "sync_ok": ok,
            })
            st["sync_ok" if ok else "sync_flagged"] += 1

    total_rows = 0
    for key, cols in sorted(parts.items()):
        out_dir = args.warehouse / "events" / f"key={key}"
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("*.parquet"):
            old.unlink()
        pq.write_table(pa.table(cols, schema=EVENTS_SCHEMA), out_dir / f"{key}.parquet")
        total_rows += len(cols["ts"])
        print(f"  {key}: {len(cols['ts'])} rows")

    if sync_report:
        (args.warehouse / "belief_sync_report.json").write_text(json.dumps(sync_report, indent=1))
        flagged = [r for r in sync_report if not r["sync_ok"]]
        print(f"\nsync check: {len(sync_report) - len(flagged)}/{len(sync_report)} seats aligned "
              f"(phase offset ≤ {SYNC_TOL_TICKS} ticks); report -> belief_sync_report.json")
        for r in flagged[:10]:
            print(f"  ⚠️  {r['episode_id']} slot {r['slot']}: phase offset {r['phase_offset_ticks']}")

    print(f"\nwrote {total_rows} belief rows across {len(parts)} partitions "
          f"from {st['seats']} seats; stats: {dict(st)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
