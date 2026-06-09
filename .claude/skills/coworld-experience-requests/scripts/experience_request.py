#!/usr/bin/env python3
"""Create and monitor Coworld experience requests, and resolve the IDs they need.

An experience request is a hosted batch of episodes you define (target + roster +
roles + count); the server runs them and you poll the `xreq_…` to completion, then
pull artifacts (the `coworld-episode-artifacts` skill). This tool handles the
mechanical parts — auth, live-schema validation, the POST + readback race, polling,
and ID resolution — and leaves *composition of the request body* to you (see
`references/api.md` for every field).

Three subcommands:

  resolve  --policy NAME [--version N]      -> policy_version_id(s)
  resolve  --division DIV [--top N]         -> ranked opponents (name + pv id) for the roster
  create   <body.json | ->  [--check-schema]  -> validate keys vs live schema, POST, read back
  monitor  <xreq_id>  [--once] [--interval S] -> poll status counts until every child episode is terminal

Usage (auth from `softmax login`; run inside `uv run` so `softmax` imports):

    uv run python experience_request.py resolve --policy crewborg --version <N>
    uv run python experience_request.py resolve --division div_… --top 7
    uv run python experience_request.py create body.json
    uv run python experience_request.py create - < body.json --check-schema
    uv run python experience_request.py monitor xreq_…

The API drifts; `create` validates your body's keys against the live
`V2CreateExperienceRequestRequest` schema before POSTing and refuses unknown keys
(`additionalProperties: false`). When a route 4xxs, read the live `<base>/openapi.json`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from typing import Any

import httpx


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# Auth + client
# --------------------------------------------------------------------------- #

def _auth():
    try:
        import softmax.auth as auth
    except ImportError as exc:  # pragma: no cover
        sys.exit(f"Could not import softmax.auth ({exc}). Run inside `uv run`.")
    return auth


def observatory_client(server: str | None) -> httpx.Client:
    """Authenticated client over the Observatory gateway.

    NB the current auth API is `load_current_token(server=...)`; the older
    `load_current_cogames_token(api_server=...)` was removed.
    """
    auth = _auth()
    api = auth.get_api_server()
    token = auth.load_current_token(server=api)
    if not token:
        sys.exit("Not authenticated. Run: uv run softmax login")
    base = server.rstrip("/") if server else api.rstrip("/") + "/observatory"
    return httpx.Client(
        base_url=base,
        headers={"X-Auth-Token": token},
        timeout=120.0,
        follow_redirects=True,
    )


def get_json(client: httpx.Client, path: str, **params: Any) -> Any:
    r = client.get(path, params=params or None)
    r.raise_for_status()
    return r.json()


def emit(obj: Any) -> None:
    print(json.dumps(obj, indent=2))


# --------------------------------------------------------------------------- #
# resolve
# --------------------------------------------------------------------------- #

def cmd_resolve(args: argparse.Namespace) -> int:
    if not args.policy and not args.division:
        sys.exit("resolve needs --policy NAME or --division DIV_ID")
    with observatory_client(args.server) as client:
        if args.policy:
            rows = get_json(client, "/stats/policy-versions", name_exact=args.policy, limit=100)
            rows = rows.get("entries", rows) if isinstance(rows, dict) else rows
            pvs = [
                {"policy_version_id": r["id"], "version": r.get("version"), "policy_id": r.get("policy_id")}
                for r in rows
            ]
            if args.version is not None:
                pvs = [p for p in pvs if p["version"] == args.version]
            pvs.sort(key=lambda p: (p["version"] or -1), reverse=True)
            emit({"policy": args.policy, "versions": pvs})
            return 0

        # --division: rank the leaderboard, join to active runnable memberships
        leaderboard = get_json(
            client, f"/v2/divisions/{args.division}/leaderboard", include_recent_rounds=args.include_recent_rounds
        )
        memberships = get_json(
            client, "/v2/league-policy-memberships", division_id=args.division, active_only=True, limit=1000
        )
        by_player: dict[str, list[dict[str, Any]]] = {}
        for m in memberships or []:
            pid = (m.get("player") or {}).get("id")
            if pid:
                by_player.setdefault(pid, []).append(m)

        def msort(m: dict[str, Any]) -> tuple[bool, str]:
            return (m.get("end_time") is None, m.get("start_time") or m.get("created_at") or "")

        excl_names = set(args.exclude_policy_name or [])
        opponents: list[dict[str, Any]] = []
        for entry in (leaderboard or []):
            pid = entry.get("player_id")
            cands = sorted(by_player.get(pid, []), key=msort, reverse=True)
            if not cands:
                continue
            pv = cands[0].get("policy_version") or {}
            pname = (pv.get("policy") or {}).get("name")
            if pname in excl_names:
                continue
            opponents.append({
                "rank": entry.get("rank"),
                "player_name": entry.get("player_name") or (cands[0].get("player") or {}).get("name"),
                "policy_name": pname,
                "version": pv.get("version"),
                "policy_version_id": pv.get("id"),
                "leaderboard_score": entry.get("score"),
            })
            if args.top and len(opponents) >= args.top:
                break
        emit({"division": args.division, "opponents": opponents})
        return 0


# --------------------------------------------------------------------------- #
# create
# --------------------------------------------------------------------------- #

def create_schema(client: httpx.Client) -> dict[str, Any]:
    spec = get_json(client, "/openapi.json")
    schema = spec.get("components", {}).get("schemas", {}).get("V2CreateExperienceRequestRequest")
    if not schema:
        sys.exit("Could not find V2CreateExperienceRequestRequest in the live OpenAPI schema.")
    return schema


def validate_keys(payload: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Return a list of payload keys the live schema does not allow (top level)."""
    allowed = set((schema.get("properties") or {}).keys())
    additional = schema.get("additionalProperties", True)
    if additional is not False:
        return []  # server accepts extras; nothing to flag
    return sorted(k for k in payload if k not in allowed)


def cmd_create(args: argparse.Namespace) -> int:
    raw = sys.stdin.read() if args.body == "-" else open(args.body, encoding="utf-8").read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        sys.exit("Request body must be a JSON object.")

    with observatory_client(args.server) as client:
        bad = validate_keys(payload, create_schema(client))
        if bad:
            sys.exit(f"Body has keys the live schema rejects (additionalProperties: false): {bad}\n"
                     f"Read references/api.md / the live V2CreateExperienceRequestRequest schema.")
        if args.check_schema:
            log("Schema check passed (keys valid); not posting (--check-schema).")
            emit({"check_schema": "ok", "keys": sorted(payload)})
            return 0

        r = client.post("/v2/experience-requests", json=payload, timeout=120.0)
        if r.status_code < 400:
            xreq = r.json()["id"]
        else:
            # Known create-then-replica-read race: a 404 can still name the request.
            m = re.search(r"(xreq_[0-9a-f-]{36})", r.text)
            if r.status_code == 404 and m:
                xreq = m.group(1)
            else:
                sys.exit(f"Create failed HTTP {r.status_code}: {r.text}")

        # Read back (retry through replica lag).
        detail = None
        for _ in range(30):
            rr = client.get(f"/v2/experience-requests/{xreq}")
            if rr.status_code == 200:
                detail = rr.json()
                break
            time.sleep(0.5)
        if detail is None:
            log(f"Created {xreq} but readback did not resolve; check `monitor {xreq}`.")
            emit({"id": xreq, "readback": "pending"})
            return 0
    emit(_summary(detail))
    return 0


# --------------------------------------------------------------------------- #
# monitor
# --------------------------------------------------------------------------- #

def _summary(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": detail.get("id"),
        "status": detail.get("status"),
        "coworld": f"{detail.get('coworld_name')} v{detail.get('coworld_version')}",
        "episode_count": detail.get("episode_count"),
        "pending": detail.get("pending_count"),
        "running": detail.get("running_count"),
        "completed": detail.get("completed_count"),
        "failed": detail.get("failed_count"),
        "error": detail.get("error"),
    }


def _terminal(d: dict[str, Any]) -> bool:
    total = d.get("episode_count") or 0
    done = (d.get("completed_count") or 0) + (d.get("failed_count") or 0)
    return total > 0 and done >= total


def cmd_monitor(args: argparse.Namespace) -> int:
    with observatory_client(args.server) as client:
        while True:
            d = get_json(client, f"/v2/experience-requests/{args.xreq}")
            s = _summary(d)
            log(f"  {s['status']}: {s['completed']}✓ {s['failed']}✗ {s['running']}▶ "
                f"{s['pending']}… / {s['episode_count']}")
            if args.once or _terminal(d):
                emit(s)
                return 0
            time.sleep(args.interval)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create and monitor Coworld experience requests.")
    parser.add_argument("--server", default=None, help="Observatory API base URL (default: <api-server>/observatory).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("resolve", help="Resolve policy_version_ids or division opponents.")
    pr.add_argument("--policy", help="Policy name -> its version ids.")
    pr.add_argument("--version", type=int, default=None, help="With --policy: keep only this version.")
    pr.add_argument("--division", help="Division id -> ranked active opponents.")
    pr.add_argument("--top", type=int, default=None, help="With --division: keep the top N ranked opponents.")
    pr.add_argument("--exclude-policy-name", action="append", help="Drop these policy names from opponents.")
    pr.add_argument("--include-recent-rounds", type=int, default=3, help="Leaderboard recency window.")
    pr.set_defaults(func=cmd_resolve)

    pc = sub.add_parser("create", help="Validate + POST a request body, read it back.")
    pc.add_argument("body", help="Path to a V2CreateExperienceRequestRequest JSON body, or '-' for stdin.")
    pc.add_argument("--check-schema", action="store_true", help="Validate keys vs live schema and exit (no POST).")
    pc.set_defaults(func=cmd_create)

    pm = sub.add_parser("monitor", help="Poll an experience request to completion.")
    pm.add_argument("xreq", help="Experience request id (xreq_...).")
    pm.add_argument("--once", action="store_true", help="Print status once and exit.")
    pm.add_argument("--interval", type=float, default=15.0, help="Seconds between polls.")
    pm.set_defaults(func=cmd_monitor)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
