#!/usr/bin/env python3
"""Print the polyworld commit the league actually runs, and compare it to what our docs cite.

Every mechanics document in gods_of_the_arena_lab/docs/ names the commit it was
verified against. Playback, host-surface, and balance claims are only valid at the
deployed commit, so run this before trusting any of them.

Resolution: league -> game.coworld_id -> that coworld's manifest source_url. Each
Gods of the Arena release is a separate coworld record (one per version), so a
hardcoded coworld id is a frozen snapshot, not "the current game"; the league's game
record is what the round runner follows. The canonical release is printed too, so a
league locked to an older version is visible.

Usage: .venv/bin/python gods_of_the_arena_lab/tools/deployed_ref.py [--docs-sha SHA]
"""
import argparse, re, sys
import httpx
from softmax import auth

LEAGUE = "league_3c60897b-25cf-4b37-9d1a-8554c1198f28"   # Gods of the Arena, Competition
DOCS_SHA = "7365e4e9"   # the deployed commit the current docs were checked against


def commit_of(base, headers, coworld_id):
    r = httpx.get(f"{base}/v2/coworlds/{coworld_id}", headers=headers, timeout=30)
    r.raise_for_status()
    body = r.json()
    url = body.get("manifest", {}).get("game", {}).get("runnable", {}).get("source_url", "")
    m = re.search(r"/tree/([0-9a-f]{7,40})", url)
    return body.get("version"), url, (m.group(1) if m else "?")


def main():
    p = argparse.ArgumentParser(); p.add_argument("--docs-sha", default=DOCS_SHA); a = p.parse_args()
    server = auth.get_api_server(); base = server.rstrip("/") + "/observatory"
    headers = {"Authorization": f"Bearer {auth.load_current_token(server=server)}"}
    r = httpx.get(f"{base}/v2/leagues/{LEAGUE}", headers=headers, timeout=30)
    r.raise_for_status()
    game = r.json()["game"]
    league_cow, canonical_cow = game["coworld_id"], game.get("canonical_coworld_id")
    version, url, sha = commit_of(base, headers, league_cow)
    print(f"league coworld  : {league_cow} (version {version})")
    if canonical_cow and canonical_cow != league_cow:
        cversion, _, csha = commit_of(base, headers, canonical_cow)
        print(f"canonical       : {canonical_cow} (version {cversion}, commit {csha[:8]}) -- league is NOT on canonical")
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
