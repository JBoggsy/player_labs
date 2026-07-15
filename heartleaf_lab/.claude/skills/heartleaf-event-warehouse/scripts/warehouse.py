#!/usr/bin/env python3
"""Fetch (and trigger) the hosted Heartleaf round-warehouse reporter's outputs.

The `heartleaf-round-warehouse` reporter (a v2 wasm reporter on Observatory)
re-simulates every episode of a subject and emits five parts:

    events        Parquet — one row per player-tagged event (join/harvest/
                  enter_house/exit_house/chat/dinner/score/leave), day-stamped
    manifest      JSON — per-episode status + totals + heartleaf_ref
    player_stats  Parquet — one row per (episode, slot): ~45 behavioural columns
    dinner_edges  Parquet — directed host->guest dining network
    chats         Parquet — one row per chat, LLM-classified is_invitation +
                  a deterministic party-attendance success measure

It runs AUTOMATICALLY on every closed Heartleaf league round, so for league
data the warehouse already exists — just fetch it. For your own experience
requests, trigger an on-demand run (`run-xreq`).

Usage (auth from `softmax login`; run inside `uv run`):

    uv run python warehouse.py list-runs [--limit 20]
    uv run python warehouse.py fetch --out DIR (--run rrun_… | --round round_… | --last N)
    uv run python warehouse.py run-xreq --xreq xreq_… --out DIR

`fetch` writes one subdirectory per run:  DIR/<rrun_id>/{events,player_stats,
dinner_edges,chats}.parquet + manifest.json — so multi-run warehouses are a
DuckDB glob away:  read_parquet('DIR/*/events.parquet', filename=true).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

REPORTER_ID = "rptr_5c331a88-9403-455e-b736-316f63622714"  # heartleaf-round-warehouse
PARQUET_PARTS = ("events", "player_stats", "dinner_edges", "chats")
PENDING_STATUSES = {"pending", "queued", "claimed", "running"}


def _client() -> httpx.Client:
    try:
        import softmax.auth as auth
    except ImportError as exc:
        sys.exit(f"Could not import softmax.auth ({exc}). Run inside `uv run`.")
    server = auth.get_api_server()
    token = auth.load_current_token(server=server)
    if not token:
        sys.exit("Not authenticated. Run: uv run softmax login")
    return httpx.Client(
        base_url=server.rstrip("/") + "/observatory",
        headers={"X-Auth-Token": token},
        timeout=120.0,
        follow_redirects=True,
    )


def _get_json(c: httpx.Client, path: str, **params: Any) -> Any:
    r = c.get(path, params=params or None)
    r.raise_for_status()
    return r.json()


def _reporter_runs(c: httpx.Client) -> list[dict[str, Any]]:
    """Latest 100 runs of the warehouse reporter, newest first."""
    return _get_json(c, f"/v2/reporters/{REPORTER_ID}/runs")


def _describe(run: dict[str, Any]) -> str:
    subj = run.get("subject") or {}
    ref = subj.get("round_id") or f"{len(subj.get('episode_request_ids') or [])} episodes"
    return f"{run['id']}  {run['status']:<10} {subj.get('kind', '?'):<8} {ref}  {run.get('created_at', '')[:19]}"


def cmd_list_runs(args: argparse.Namespace) -> None:
    with _client() as c:
        for run in _reporter_runs(c)[: args.limit]:
            print(_describe(run))


def _fetch_run(c: httpx.Client, run_id: str, out: Path) -> dict[str, Any]:
    """Download all five parts of one completed run into out/<run_id>/."""
    run_dir = out / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = _get_json(c, f"/v2/reporters/runs/{run_id}/output/manifest")
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    for part in PARQUET_PARTS:
        r = c.get(f"/v2/reporters/runs/{run_id}/output/{part}")
        r.raise_for_status()
        (run_dir / f"{part}.parquet").write_bytes(r.content)
    print(
        f"{run_id}: episodes {manifest.get('episodes_ok')}/{manifest.get('episodes_total')} ok, "
        f"{manifest.get('events_written')} events, ref {manifest.get('heartleaf_ref')} -> {run_dir}"
    )
    failed = [e for e in manifest.get("episodes", []) if e.get("status") != "ok"]
    for e in failed:
        print(f"  ! {e.get('episode_id')}: {e.get('status')} — {e.get('message', '')}", file=sys.stderr)
    return manifest


def cmd_fetch(args: argparse.Namespace) -> None:
    out = Path(args.out)
    with _client() as c:
        run_ids: list[str] = list(args.run or [])
        if args.round or args.last:
            runs = [r for r in _reporter_runs(c) if r["status"] == "completed"]
            if args.round:
                wanted = set(args.round)
                run_ids += [r["id"] for r in runs if (r.get("subject") or {}).get("round_id") in wanted]
                missing = wanted - {(r.get("subject") or {}).get("round_id") for r in runs}
                if missing:
                    sys.exit(f"No completed warehouse run found for round(s): {sorted(missing)} "
                             "(only the latest 100 runs are searchable — older rounds need their rrun_ id)")
            if args.last:
                round_runs = [r for r in runs if (r.get("subject") or {}).get("kind") == "round"]
                run_ids += [r["id"] for r in round_runs[: args.last]]
        if not run_ids:
            sys.exit("Nothing to fetch: pass --run, --round, or --last.")
        for run_id in dict.fromkeys(run_ids):  # dedupe, keep order
            _fetch_run(c, run_id, out)
    _print_duckdb_hint(out)


def cmd_run_xreq(args: argparse.Namespace) -> None:
    out = Path(args.out)
    with _client() as c:
        episodes = _get_json(c, f"/v2/experience-requests/{args.xreq}/episodes")
        ereq_ids = [e["id"] for e in episodes]
        if not ereq_ids:
            sys.exit(f"{args.xreq} has no episodes.")
        versions = _get_json(c, f"/v2/reporters/{REPORTER_ID}/versions")
        latest = max(versions, key=lambda v: v["version"])
        print(f"Triggering warehouse v{latest['version']} over {len(ereq_ids)} episodes of {args.xreq}…")
        r = c.post(
            "/v2/reporters/runs",
            json={
                "reporter_version_id": latest["id"],
                "subject": {"kind": "episodes", "episode_request_ids": ereq_ids},
            },
        )
        if r.status_code == 409:
            sys.exit(f"Experience request not terminal yet: {r.json().get('detail')}")
        r.raise_for_status()
        run = r.json()
        print(f"Run {run['id']} accepted; polling (episodes re-simulate ~10-30s each)…")
        deadline = time.time() + args.timeout
        while run["status"] in PENDING_STATUSES:
            if time.time() > deadline:
                sys.exit(f"Timed out; check later with: fetch --run {run['id']} --out {out}")
            time.sleep(10)
            run = _get_json(c, f"/v2/reporters/runs/{run['id']}")
        if run["status"] != "completed":
            sys.exit(f"Run {run['id']} ended {run['status']}.")
        _fetch_run(c, run["id"], out)
    _print_duckdb_hint(out)


def _print_duckdb_hint(out: Path) -> None:
    print(
        "\nQuery it (duckdb):\n"
        f"  CREATE VIEW events AS SELECT * FROM read_parquet('{out}/*/events.parquet', filename=true);\n"
        f"  CREATE VIEW player_stats AS SELECT * FROM read_parquet('{out}/*/player_stats.parquet');\n"
        f"  CREATE VIEW dinner_edges AS SELECT * FROM read_parquet('{out}/*/dinner_edges.parquet');\n"
        f"  CREATE VIEW chats AS SELECT * FROM read_parquet('{out}/*/chats.parquet');"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list-runs", help="list recent warehouse runs (newest first)")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_list_runs)

    p = sub.add_parser("fetch", help="download parts of completed run(s)")
    p.add_argument("--run", action="append", help="rrun_… id (repeatable)")
    p.add_argument("--round", action="append", help="round_… id (repeatable; resolved via recent runs)")
    p.add_argument("--last", type=int, help="fetch the N most recent completed round runs")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("run-xreq", help="trigger an on-demand run over an experience request's episodes")
    p.add_argument("--xreq", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--timeout", type=int, default=1200, help="poll timeout in seconds (default 20 min)")
    p.set_defaults(func=cmd_run_xreq)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
