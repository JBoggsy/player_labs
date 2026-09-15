#!/usr/bin/env python3
"""Print the polyworld commit the league actually runs, and compare it to what our docs cite.

Every mechanics document in gods_of_the_arena_lab/docs/ names the commit it was
verified against. Playback, host-surface, and balance claims are only valid at the
deployed commit, so run this before trusting any of them.

Usage: .venv/bin/python gods_of_the_arena_lab/tools/deployed_ref.py [--docs-sha SHA]
"""
import argparse, re, sys
import httpx
from softmax import auth

COWORLD = "cow_252fb6a6-cbc3-4d4f-9fa2-8b5250a9d2a2"
DOCS_SHA = "5422fb0c"   # the deployed commit the current docs were checked against


def main():
    p = argparse.ArgumentParser(); p.add_argument("--docs-sha", default=DOCS_SHA); a = p.parse_args()
    server = auth.get_api_server(); base = server.rstrip("/") + "/observatory"
    token = auth.load_current_token(server=server)
    r = httpx.get(f"{base}/v2/coworlds/{COWORLD}", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    body = r.json(); runnable = body.get("manifest", {}).get("game", {}).get("runnable", {})
    url = runnable.get("source_url", ""); version = body.get("version") or body.get("coworld_version")
    m = re.search(r"/tree/([0-9a-f]{7,40})", url)
    sha = m.group(1) if m else "?"
    print(f"coworld version : {version}")
    print(f"source_url      : {url}")
    print(f"deployed commit : {sha}")
    print(f"docs verified at: {a.docs_sha}")
    if sha.startswith(a.docs_sha) or a.docs_sha.startswith(sha[:7]):
        print("STATUS: docs are current for the deployed build")
        return 0
    print("STATUS: DEPLOYED COMMIT CHANGED. Diff the cited files before trusting the docs:")
    print(f"  git -C <polyworld clone> diff {a.docs_sha} {sha} -- examples/gods_of_the_arena src/polyworld/basic.nim")
    return 1


if __name__ == "__main__":
    sys.exit(main())
