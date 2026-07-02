#!/usr/bin/env python3
"""Empirical room population densities over game time, from event warehouses.

The imposter search-weighting artifact (movement investigation, direction 3):
measure — across many real episodes — how many LIVE CREW are in each room during
each band of Playing time, and emit a vendorable JSON the policy can load to weight
its room search toward where crew empirically are.

Method: `player_state` is sampled per tick (or every N ticks) for every slot. For
one episode and one (room, tick-bucket): the average live-crew headcount in that
room during that bucket = crew-state rows / distinct sampled ticks (cadence-proof).
Bucket densities are then averaged across episodes equally; later buckets average
over the episodes that lasted that long (density conditional on the game still
running). `share` normalizes each bucket's densities across rooms — the quantity a
search should weight by.

    uv run python crewrift_lab/tools/imposter_movement/room_density.py \
        --warehouse /tmp/prime_wh --warehouse .../base_wh --out room_density.json

Run from crewrift_lab/tools/event-warehouse/crewrift-event-warehouse via `uv run`
(the repo-root venv lacks duckdb).
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import duckdb

DEFAULT_BUCKET_TICKS = 600  # 25s of Playing time per band


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--warehouse", type=Path, action="append", required=True,
                    help="Event-warehouse dir (repeatable; episodes pooled).")
    ap.add_argument("--bucket-ticks", type=int, default=DEFAULT_BUCKET_TICKS)
    ap.add_argument("--max-tick", type=int, default=9000,
                    help="Ignore Playing ticks beyond this (defensive tail cap).")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    con = duckdb.connect()
    globs = ", ".join(f"'{w}/events/**/*.parquet'" for w in args.warehouse)
    con.execute(f"CREATE VIEW events AS SELECT * FROM read_parquet([{globs}], hive_partitioning=true)")

    # Per (episode, bucket, room): average live-crew headcount, cadence-normalized.
    rows = con.execute(f"""
        WITH crew AS (
          SELECT episode_id, ts, ts // {args.bucket_ticks} AS bucket,
                 json_extract_string(value,'$.room') AS room
          FROM events
          WHERE key='player_state' AND slot>=0 AND role='crew'
            AND json_extract_string(value,'$.phase')='Playing'
            AND json_extract_string(value,'$.alive')='true'
            AND ts <= {args.max_tick}
        ), ticks AS (       -- sampled tick count per (episode, bucket): the denominator
          SELECT episode_id, ts // {args.bucket_ticks} AS bucket, count(DISTINCT ts) AS n_ts
          FROM events
          WHERE key='player_state' AND slot>=0
            AND json_extract_string(value,'$.phase')='Playing' AND ts <= {args.max_tick}
          GROUP BY 1, 2
        ), per_ep AS (
          SELECT c.bucket, c.room, c.episode_id,
                 count(*)::double / any_value(t.n_ts) AS avg_crew
          FROM crew c JOIN ticks t ON t.episode_id=c.episode_id AND t.bucket=c.bucket
          GROUP BY 1, 2, 3
        )
        SELECT bucket, room, avg(avg_crew) AS density, count(DISTINCT episode_id) AS eps
        FROM per_ep GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchall()
    n_episodes = con.execute(
        "SELECT count(DISTINCT episode_id) FROM events WHERE key='player_state'").fetchone()[0]

    buckets = sorted({b for b, _, _, _ in rows})
    rooms = sorted({r for _, r, _, _ in rows if r})
    density: dict[str, list[float]] = {r: [0.0] * len(buckets) for r in rooms}
    support: list[int] = [0] * len(buckets)
    for b, r, d, eps in rows:
        if not r:
            continue
        i = buckets.index(b)
        density[r][i] = round(d, 4)
        support[i] = max(support[i], eps)

    # share: per-bucket normalization across rooms — the search weight.
    share = {r: [0.0] * len(buckets) for r in rooms}
    for i in range(len(buckets)):
        total = sum(density[r][i] for r in rooms)
        if total > 0:
            for r in rooms:
                share[r][i] = round(density[r][i] / total, 4)
    overall = {r: round(sum(density[r]) / max(1, len(buckets)), 4) for r in rooms}

    out = {
        "schema": "crewborg-room-density/v1",
        "generated": str(date.today()),
        "bucket_ticks": args.bucket_ticks,
        "bucket_start_ticks": [b * args.bucket_ticks for b in buckets],
        "episodes": n_episodes,
        "episodes_per_bucket": support,
        "rooms": rooms,
        "density": density,       # avg live-crew headcount in room, per Playing-time band
        "share": share,           # per-band normalization across rooms (the search weight)
        "overall_density": overall,
        "sources": [str(w) for w in args.warehouse],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print(f"wrote {args.out}: {len(rooms)} rooms x {len(buckets)} bands, "
          f"{n_episodes} episodes (per-band support {support[0]}..{support[-1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
