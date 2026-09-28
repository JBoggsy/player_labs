#!/usr/bin/env python3
"""Print the paintbot-pw source commit each league actually runs, and compare it to what our docs cite.

Every mechanics document in paintbot_pw_lab/docs/ names the commit it was verified
against. Rules, host-surface and replay claims are only valid at the deployed commit,
so run this before trusting any of them.

Resolution: league -> game.coworld_id -> that coworld's release version -> the
`coworld-v<version>` tag in Metta-AI/paintbot-pw. Unlike Gods of the Arena, the
paintbot-pw manifest's `source_url` is the bare repository URL with no commit, so the
release tag is the only link from a deployed version to source. The repo ships
several releases a day; `main` is usually ahead of the league.

Usage: uv run python paintbot_pw_lab/tools/deployed_ref.py [--docs-sha SHA]
"""
import argparse
import subprocess
import sys

import httpx
from softmax import auth

LEAGUES = {
    "paintbot-pw (teams)": "league_b9458ff8-0854-4e21-82b8-3c99942902e0",
    "Heartland (ffa_kin)": "league_40996eb3-4a80-457d-86d5-866f72882995",
}
SOURCE_REPO = "https://github.com/Metta-AI/paintbot-pw"
DOCS_SHA = "7b2b19f5"   # the deployed commit the current docs were checked against (coworld 0.3.65)


def release_tags():
    """Map release tag name -> commit, peeling annotated tags."""
    out = subprocess.run(["git", "ls-remote", "--tags", SOURCE_REPO],
                         capture_output=True, text=True, check=True).stdout
    tags = {}
    for line in out.splitlines():
        sha, ref = line.split("\t")
        name = ref.removeprefix("refs/tags/")
        if name.endswith("^{}"):
            tags[name[:-3]] = sha          # peeled commit wins over the tag object
        else:
            tags.setdefault(name, sha)
    return tags


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--docs-sha", default=DOCS_SHA)
    a = p.parse_args()
    server = auth.get_api_server()
    base = server.rstrip("/") + "/observatory"
    headers = {"Authorization": f"Bearer {auth.load_current_token(server=server)}"}
    tags = release_tags()

    stale = False
    for label, league_id in LEAGUES.items():
        r = httpx.get(f"{base}/v2/leagues/{league_id}", headers=headers, timeout=30)
        r.raise_for_status()
        coworld_id = r.json()["game"]["coworld_id"]
        c = httpx.get(f"{base}/v2/coworlds/{coworld_id}", headers=headers, timeout=30)
        c.raise_for_status()
        version = c.json()["version"]
        sha = tags.get(f"coworld-v{version}")
        print(f"{label:22} coworld {coworld_id} version {version} -> commit {sha[:8] if sha else 'NO TAG'}")
        if sha is None or not sha.startswith(a.docs_sha):
            stale = True

    print(f"docs verified at: {a.docs_sha}")
    if not stale:
        print("STATUS: docs are current for the deployed build")
        return 0
    print("STATUS: DEPLOYED COMMIT CHANGED (or untagged). Diff the cited files before trusting the docs:")
    print(f"  git -C ~/coding/coworlds/paintbot-pw diff {a.docs_sha} <deployed> -- examples/paintbot src/polyworld/basic.nim coworld/paintbot/guide.md")
    return 1


if __name__ == "__main__":
    sys.exit(main())
