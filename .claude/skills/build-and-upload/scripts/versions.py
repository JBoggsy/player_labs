#!/usr/bin/env python3
"""List a policy's uploaded versions — for reconciling the version log.

Every `coworld upload-policy` creates a new version (`<name>:vN`). There is no
`coworld versions` command, so this lists them from the Observatory so you can keep the
version log (version -> the change it carries) honest against what's actually uploaded.

Usage (auth from `softmax login`; run inside `uv run`):

    uv run python versions.py --name crewborg

Route: GET /stats/policy-versions?mine=true&name_exact=<NAME>&limit=100. The API drifts —
read `<base>/openapi.json` if it 4xxs.
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


def rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("entries") or []
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="List uploaded versions for a policy name.")
    ap.add_argument("--name", required=True)
    args = ap.parse_args(argv)
    with client() as c:
        vs = []
        params = {"mine": True, "name_exact": args.name, "limit": 100}
        while True:
            r = c.get("/stats/policy-versions", params=params)
            r.raise_for_status()
            payload = r.json()
            vs.extend({"version": v.get("version"), "policy_version_id": v["id"],
                       "created_at": v.get("created_at")} for v in payload["entries"])
            if not payload.get("next_cursor"):
                break
            params["cursor"] = payload["next_cursor"]
    vs.sort(key=lambda v: (v["version"] or -1), reverse=True)
    print(f"{args.name}: {len(vs)} uploaded version(s)")
    for v in vs:
        print(f"  v{v['version']:<4} {v['policy_version_id']}  {v.get('created_at') or ''}")
    print("\n(use the exact returned policy version ID for evaluation and submission)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
