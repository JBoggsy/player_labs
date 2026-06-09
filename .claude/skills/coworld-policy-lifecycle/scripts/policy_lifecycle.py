#!/usr/bin/env python3
"""Policy-lifecycle helpers: list your uploaded versions, and monitor live standings.

The lifecycle is: build an image → `coworld upload-policy` (a new, *inert* version) →
[gated] `coworld submit` (the public, irreversible league entry) → monitor standings.
Upload and submit are done with the `coworld` CLI (they handle the Docker push); this
script covers the two API-mechanical parts the CLI doesn't:

  versions  --name NAME            list every uploaded version for a policy name, so you
                                   can reconcile the version log (version -> changes)
  monitor   --name NAME            for that policy: each league membership's status /
                                   champion flag / division, and its rank + score on the
                                   live division leaderboard

Usage (auth from `softmax login`; run inside `uv run`):

    uv run python policy_lifecycle.py versions --name crewborg
    uv run python policy_lifecycle.py monitor  --name crewborg

Routes used (Observatory gateway): /stats/policy-versions, /v2/league-policy-memberships,
/v2/league-submissions, /v2/divisions/{id}/leaderboard. The API drifts — read
`<base>/openapi.json` if a route 4xxs.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx


def client() -> httpx.Client:
    try:
        import softmax.auth as auth
    except ImportError as exc:  # pragma: no cover
        sys.exit(f"Could not import softmax.auth ({exc}). Run inside `uv run`.")
    api = auth.get_api_server()
    tok = auth.load_current_token(server=api)
    if not tok:
        sys.exit("Not authenticated. Run: uv run softmax login")
    return httpx.Client(base_url=api.rstrip("/") + "/observatory",
                        headers={"X-Auth-Token": tok}, timeout=60.0, follow_redirects=True)


def get(c: httpx.Client, path: str, **params: Any) -> Any:
    r = c.get(path, params=params or None)
    r.raise_for_status()
    return r.json()


def rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("entries") or payload.get("memberships") or payload.get("submissions") or []
    return []


def policy_name_of(obj: dict[str, Any]) -> str | None:
    pv = obj.get("policy_version") or {}
    return (pv.get("policy") or {}).get("name") or pv.get("policy_name") or obj.get("policy_name")


def cmd_versions(c: httpx.Client, args: argparse.Namespace) -> int:
    payload = get(c, "/stats/policy-versions", mine=True, name_exact=args.name, limit=100)
    vs = rows(payload)
    vs = [{"version": v.get("version"), "policy_version_id": v.get("id") or v.get("policy_version_id"),
           "created_at": v.get("created_at")} for v in vs]
    vs.sort(key=lambda v: (v["version"] or -1), reverse=True)
    print(f"{args.name}: {len(vs)} uploaded version(s)")
    for v in vs:
        print(f"  v{v['version']:<4} {v['policy_version_id']}  {v.get('created_at') or ''}")
    print("\n(reconcile these against the version log — each version should map to the change it carries)")
    return 0


def cmd_monitor(c: httpx.Client, args: argparse.Namespace) -> int:
    mine = rows(get(c, "/v2/league-policy-memberships", mine=True, limit=1000))
    mine = [m for m in mine if policy_name_of(m) == args.name]
    subs = rows(get(c, "/v2/league-submissions", mine=True, limit=200))
    subs = [s for s in subs if policy_name_of(s) == args.name]

    print(f"=== {args.name} — submissions ===")
    if not subs:
        print("  (none — has it been submitted to a league yet?)")
    for s in subs[:20]:
        pv = s.get("policy_version") or {}
        print(f"  {s.get('id')}  status={s.get('status')}  v{pv.get('version')}  "
              f"membership={s.get('league_policy_membership_id') or '-'}")

    print(f"\n=== {args.name} — memberships (am I active / champion?) ===")
    if not mine:
        print("  (no active memberships)")
    # cache leaderboards per division
    boards: dict[str, list[dict[str, Any]]] = {}
    for m in mine:
        div = m.get("division_id") or (m.get("division") or {}).get("id")
        pv = m.get("policy_version") or {}
        champ = m.get("is_champion")
        print(f"  membership {m.get('id')}  div={div}  status={m.get('status')}/"
              f"{m.get('substatus') or '-'}  champion={champ}  v{pv.get('version')}")
        if not div:
            continue
        if div not in boards:
            try:
                boards[div] = rows(get(c, f"/v2/divisions/{div}/leaderboard", include_recent_rounds=args.recent_rounds))
            except httpx.HTTPStatusError as exc:
                print(f"      ! leaderboard {div}: {exc}")
                boards[div] = []
        # The division leaderboard is ranked per PLAYER, so match on player_id.
        player_id = (m.get("player") or {}).get("id") or m.get("player_id")
        hits = [e for e in boards[div] if e.get("player_id") == player_id]
        for e in hits:
            print(f"      leaderboard: rank {e.get('rank')}  score {e.get('score')}  "
                  f"rounds {e.get('rounds_played')}  (player {e.get('player_name')})")
        if not hits and boards[div]:
            print("      (player not on this leaderboard yet — placement may still be running)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="List policy versions / monitor live standings.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("versions", help="List uploaded versions for a policy name.")
    pv.add_argument("--name", required=True)
    pv.set_defaults(func=cmd_versions)
    pm = sub.add_parser("monitor", help="Show membership status + leaderboard rank for a policy.")
    pm.add_argument("--name", required=True)
    pm.add_argument("--recent-rounds", type=int, default=5)
    pm.set_defaults(func=cmd_monitor)
    args = ap.parse_args(argv)
    with client() as c:
        return args.func(c, args)


if __name__ == "__main__":
    raise SystemExit(main())
