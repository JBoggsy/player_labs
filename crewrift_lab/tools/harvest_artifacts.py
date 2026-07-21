#!/usr/bin/env python3
"""Harvest crewborg's league telemetry artifacts (policy_artifact_*.zip + results.json).

Pulls the policy artifacts crewborg uploads from its recent Crewrift Prime league
episodes into crewrift_lab/telemetry_harvest/episodes/ (gitignored), one
timestamp-prefixed directory per episode. Idempotent: episodes already complete
on disk are skipped, so it is safe and cheap to run on a timer.

Why this exists: flagged 2026-07-01 when league artifacts appeared to vanish
after ~one round. Re-measured 2026-07-21: artifacts are durable (>= 20 days,
no platform TTL — see docs/telemetry-harvest.md), so the harvest is now about
ACCUMULATING continuous telemetry locally for the event warehouse, not racing
deletion. Running it every ~10 min keeps the local corpus current.

How it works (thin wrapper over the lab's episode-artifact downloader):
  1. Find crewborg's current league-entrant version(s): intersect recent
     rounds' entrant_policy_version_ids with crewborg's policy-version ids.
  2. List crewborg's newest N league episodes for each entrant version
     (`coworld episodes -p crewborg:vV --json`) — these are ereq_… rows, the
     only handle the v2 policy-artifact routes accept (league episode uuids
     have NO artifact route; that is why fetch_artifacts --policy can't be
     used here).
  3. For completed episodes not already complete on disk, run
     fetch_artifacts.py --ereq … --elevated --no-replay --no-logs.
  4. Append a one-line summary to telemetry_harvest/harvest.log.

Usage:
    uv run python crewrift_lab/tools/harvest_artifacts.py           # newest 60 eps
    uv run python crewrift_lab/tools/harvest_artifacts.py -n 300    # deeper catch-up

Run every ~10 minutes via crontab (a caught-up run finishes in seconds; the
lockfile makes overlapping runs a no-op):

    */10 * * * * cd /Users/jamesboggs/coding/personal_labs/personal_labs_crewrift && /Users/jamesboggs/.local/bin/uv run python crewrift_lab/tools/harvest_artifacts.py >> crewrift_lab/telemetry_harvest/cron.log 2>&1

Auth comes from `softmax login` (check with `uv run softmax status`). See
crewrift_lab/docs/telemetry-harvest.md for the how-to and retention findings.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

LAB_ROOT = Path(__file__).resolve().parent.parent          # crewrift_lab/
REPO_ROOT = LAB_ROOT.parent
FETCH_SCRIPT = REPO_ROOT / ".claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py"
HARVEST_ROOT = LAB_ROOT / "telemetry_harvest"
CREWRIFT_PRIME_LEAGUE = "league_a12f5172-0907-4d04-8bcb-ca02f5360e3a"
POLICY_NAME = "crewborg"

# Statuses that mean the episode will never change again (mirrors
# fetch_artifacts.TERMINAL_EPISODE_STATUSES).
TERMINAL_STATUSES = {"completed", "success", "failed", "error", "cancelled", "canceled"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def observatory_client() -> httpx.Client:
    import softmax.auth as auth

    server = auth.get_api_server().rstrip("/") + "/observatory"
    token = auth.load_current_token(server=auth.get_api_server())
    if not token:
        sys.exit("Not authenticated. Run: uv run softmax login")
    return httpx.Client(
        base_url=server,
        headers={"X-Auth-Token": token},
        timeout=60.0,
        follow_redirects=True,
    )


def current_entrant_versions(client: httpx.Client, league_id: str) -> list[int]:
    """crewborg versions entered in the league's newest rounds (usually one).

    Falls back to crewborg's newest version if no recent round lists it (e.g.
    between submissions), so the harvest still pulls whatever it played last.
    """
    rows = client.get("/stats/policy-versions", params={"name_exact": POLICY_NAME, "limit": 200})
    rows.raise_for_status()
    entries = rows.json()
    entries = entries.get("entries", entries) if isinstance(entries, dict) else entries
    id_to_version = {str(r["id"]): r.get("version") for r in entries}
    if not id_to_version:
        sys.exit(f"No policy versions found for '{POLICY_NAME}'.")

    rounds = client.get("/v2/rounds", params={"league_id": league_id, "limit": 10})
    rounds.raise_for_status()
    round_rows = rounds.json()
    round_rows = round_rows.get("entries", round_rows) if isinstance(round_rows, dict) else round_rows

    versions: set[int] = set()
    for rnd in round_rows:
        for pvid in (rnd.get("round_config") or {}).get("entrant_policy_version_ids", []):
            v = id_to_version.get(str(pvid))
            if v is not None:
                versions.add(v)
    if not versions:
        newest = max(v for v in id_to_version.values() if v is not None)
        log(f"No {POLICY_NAME} entrant in recent rounds; falling back to newest version v{newest}")
        return [newest]
    return sorted(versions)


def list_recent_ereqs(version: int, num: int) -> list[dict]:
    """crewborg's newest league episode rows (ereq_… rows) for one version."""
    result = subprocess.run(
        ["uv", "run", "coworld", "episodes", "-p", f"{POLICY_NAME}:v{version}",
         "--limit", str(num), "--json"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        log(f"coworld episodes failed for v{version}:\n{result.stderr[-1000:]}")
        return []
    rows = json.loads(result.stdout)
    return rows if isinstance(rows, list) else rows.get("entries", [])


def episode_already_complete(out_dir: Path, ereq_id: str) -> bool:
    """True if this ereq's directory on disk already has its artifacts.

    Matches by the ereq-id fragment fetch_artifacts.py bakes into the dirname
    (ref_id[:16]) so we don't have to replicate its timestamp mangling.
    """
    for d in out_dir.glob(f"*_{ereq_id[:16]}"):
        if (d / "episode.json").exists() and (d / "artifacts").exists():
            return True
    return False


def run_fetch(ereq_ids: list[str], out_dir: Path) -> dict:
    """Invoke fetch_artifacts.py for a batch of ereqs; return its index.json."""
    cmd = [
        "uv", "run", "python", str(FETCH_SCRIPT),
        "--elevated", "--no-replay", "--no-logs",
        "-n", str(len(ereq_ids)),
        "--out", str(out_dir),
    ]
    for eid in ereq_ids:
        cmd += ["--ereq", eid]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"fetch_artifacts failed:\n{result.stderr[-2000:]}")
        return {}
    index_path = out_dir / "index.json"
    return json.loads(index_path.read_text()) if index_path.exists() else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-n", "--num", type=int, default=60,
                        help="Newest N episodes to consider per entrant version (default 60, "
                             "~1h of league play; already-pulled episodes are skipped).")
    parser.add_argument("--league", default=CREWRIFT_PRIME_LEAGUE,
                        help="League id whose rounds define the current entrant version.")
    args = parser.parse_args(argv)

    out_dir = HARVEST_ROOT / "episodes"
    out_dir.mkdir(parents=True, exist_ok=True)

    # One harvester at a time; a second concurrent run exits quietly.
    lock = (HARVEST_ROOT / ".harvest.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("Another harvest run holds the lock; exiting.")
        return 0

    with observatory_client() as client:
        versions = current_entrant_versions(client, args.league)

    to_fetch: list[str] = []
    considered = skipped = pending = 0
    for version in versions:
        for row in list_recent_ereqs(version, args.num):
            considered += 1
            status = str(row.get("status") or "").lower()
            if status not in TERMINAL_STATUSES:
                pending += 1
                continue
            eid = str(row["id"])
            if episode_already_complete(out_dir, eid):
                skipped += 1
                continue
            to_fetch.append(eid)

    new = with_artifacts = errored = 0
    if to_fetch:
        index = run_fetch(to_fetch, out_dir)
        for ep in index.get("episodes", []):
            if ep.get("skipped"):
                skipped += 1
                continue
            new += 1
            if ep.get("policy_artifacts"):
                with_artifacts += 1
            if ep.get("errors"):
                errored += 1

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = (f"{stamp} versions={','.join(f'v{v}' for v in versions)} "
               f"considered={considered} new={new} new_with_artifacts={with_artifacts} "
               f"skipped={skipped} pending={pending} errored={errored}")
    with (HARVEST_ROOT / "harvest.log").open("a") as fh:
        fh.write(summary + "\n")
    log(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
