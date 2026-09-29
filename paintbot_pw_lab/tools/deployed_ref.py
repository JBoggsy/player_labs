#!/usr/bin/env python3
"""Which paintbot-pw commit the league runs, versus the lab's pins in tools/release.env.

Answers two questions an agent loop must settle before trusting lab output:
  1. Are the tools current? The league's release tag/commit vs PW_RELEASE_TAG/PW_RELEASE_SHA.
     `--write` moves release.env to the league's release when it moved (then rebuild).
  2. Do the docs need re-verification? It always prints the diffstat of the rule-bearing
     engine files between PW_DOCS_SHA (where the docs' line citations are exact) and the
     deployed commit. Empty diff = the docs' rule claims still describe the deployed game.

Resolution: league -> game.coworld_id -> that coworld's name and release version -> the
release tag in Metta-AI/paintbot-pw (`git ls-remote`, annotated tags peeled). The manifest's
`source_url` is the bare repository URL, so the tag is the only link from version to source.
One repository publishes two coworlds: `paintbot-pw` (tags `coworld-v<version>`, tracked) and
`heartland` (tags `heartland-v<version>`, printed for reference only).

Exit codes (agent CLI contract): 0 tools current; 1 release.env is behind the league, or was
just updated by --write (rebuild next), or the league's version has no tag; 2 usage error;
3 environment missing (no softmax login, network/git failure, no source clone) with the fix.
Reference: paintbot_pw_lab/docs/tools/deployed_ref.md. Makes 2 API reads per league plus one
`git ls-remote`; do not loop it.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pw_release  # noqa: E402

# label -> (league id, whether the lab's release pins track this league's build)
LEAGUES = {
    "paintbot-pw (teams)": ("league_b9458ff8-0854-4e21-82b8-3c99942902e0", True),
    "Heartland (ffa_kin)": ("league_40996eb3-4a80-457d-86d5-866f72882995", False),
}
TAG_PREFIX = {"paintbot-pw": "coworld-v", "heartland": "heartland-v"}  # coworld name -> tag prefix
SOURCE_REPO = "https://github.com/Metta-AI/paintbot-pw"
DEFAULT_CLONE = Path(os.environ.get("PW_CLONE", Path.home() / "coding/coworlds/paintbot-pw"))
# Source files whose changes can change a rule, a host call, the upload surface or a line
# citation in the lab docs: the rules engine, the BASIC dialect, plus the files
# docs/policy-surface.md names as its re-verify triggers (oracle, neural lane, upload staging).
RULE_FILES = (
    "examples/paintbot/sim.nim", "examples/paintbot/mechanics.nim", "examples/paintbot/bots.nim",
    "examples/paintbot/game.nim", "examples/paintbot/match_config.nim", "src/polyworld/basic.nim",
    "coworld/paintbot/coworld_manifest_template.json",
    "examples/paintbot/oracle.nim", "examples/paintbot/neural_host.nim",
    "coworld/paintbot/runtime/host.py", "coworld/paintbot/runtime/neural_package.py",
)
DOCS_TO_REVERIFY = ("docs/mechanics.md", "docs/policy-surface.md", "docs/evidence-pipeline.md")
REBUILD = ["paintbot_pw_lab/tools/build_tools.sh", "paintbot_pw_lab/tools/build_native.sh",
           "uv run python -m pytest -q paintbot_pw_lab/tools/tests tools/tests"]


class EnvironmentMissing(RuntimeError):
    """Something outside the tool is missing; str() includes the fixing command."""


def release_tags() -> dict[str, str]:
    """Map release tag name -> commit, peeling annotated tags."""
    try:
        out = subprocess.run(["git", "ls-remote", "--tags", SOURCE_REPO],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as err:
        raise EnvironmentMissing(f"git ls-remote {SOURCE_REPO} failed ({err}); check network/git "
                                 "access, then rerun this command") from err
    tags = {}
    for line in out.splitlines():
        sha, ref = line.split("\t")
        name = ref.removeprefix("refs/tags/")
        if name.endswith("^{}"):
            tags[name[:-3]] = sha          # peeled commit wins over the tag object
        else:
            tags.setdefault(name, sha)
    return tags


def resolve_leagues(tags: dict[str, str]) -> list[dict]:
    """One record per league: coworld name/version, release tag and commit (None when untagged)."""
    import httpx
    from softmax import auth

    server = auth.get_api_server()
    token = auth.load_current_token(server=server)
    if not token:
        raise EnvironmentMissing("no softmax login token: run `uv run softmax login`")
    base = server.rstrip("/") + "/observatory"
    headers = {"Authorization": f"Bearer {token}"}
    rows = []
    try:
        for label, (league_id, tracked) in LEAGUES.items():
            r = httpx.get(f"{base}/v2/leagues/{league_id}", headers=headers, timeout=30)
            r.raise_for_status()
            coworld_id = r.json()["game"]["coworld_id"]
            c = httpx.get(f"{base}/v2/coworlds/{coworld_id}", headers=headers, timeout=30)
            c.raise_for_status()
            name, version = c.json()["name"], c.json()["version"]
            prefix = TAG_PREFIX.get(name)
            tag = f"{prefix}{version}" if prefix else None
            rows.append({"label": label, "league_id": league_id, "tracked": tracked,
                         "coworld_id": coworld_id, "coworld": name, "version": version,
                         "tag": tag, "sha": tags.get(tag) if tag else None})
    except httpx.HTTPStatusError as err:
        fix = "run `uv run softmax login`" if err.response.status_code in (401, 403) else "retry later"
        raise EnvironmentMissing(f"Observatory API {err.response.status_code} on {err.request.url}: {fix}") from err
    except httpx.HTTPError as err:
        raise EnvironmentMissing(f"Observatory API unreachable ({err}); check network, then rerun") from err
    return rows


def rule_diffstat(clone: Path, from_sha: str, to_sha: str) -> list[dict]:
    """Per rule-bearing file changed between two commits: {path, added, deleted}.

    Fetches the clone (never changes its checkout) when a commit is not present yet."""
    if not (clone / ".git").exists():
        raise EnvironmentMissing(f"no paintbot-pw clone at {clone}: run `git clone {SOURCE_REPO} {clone}` "
                                 "(or set PW_CLONE)")
    git = ["git", "-C", str(clone)]

    def have(sha: str) -> bool:
        return subprocess.run(git + ["cat-file", "-e", f"{sha}^{{commit}}"], capture_output=True).returncode == 0

    if not (have(from_sha) and have(to_sha)):
        subprocess.run(git + ["fetch", "--quiet", "--tags", "origin"], capture_output=True)
        if not (have(from_sha) and have(to_sha)):
            raise EnvironmentMissing(f"{clone} lacks {from_sha} or {to_sha} even after fetch: "
                                     f"run `git -C {clone} fetch --tags origin`")
    out = subprocess.run(git + ["diff", "--numstat", from_sha, to_sha, "--", *RULE_FILES],
                         capture_output=True, text=True, check=True).stdout
    return parse_numstat(out)


def parse_numstat(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        added, deleted, path = line.split("\t", 2)
        rows.append({"path": path, "added": int(added) if added != "-" else None,
                     "deleted": int(deleted) if deleted != "-" else None})
    return rows


def tools_current(league_tag: str | None, league_sha: str | None, env: dict[str, str]) -> bool:
    """release.env matches the league: same tag and the pinned sha is a prefix of the league's."""
    return bool(league_tag and league_sha and league_tag == env["PW_RELEASE_TAG"]
                and league_sha.startswith(env["PW_RELEASE_SHA"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog="examples:\n"
               "  uv run python paintbot_pw_lab/tools/deployed_ref.py            # check, exit 0/1\n"
               "  uv run python paintbot_pw_lab/tools/deployed_ref.py --json     # one JSON object\n"
               "  uv run python paintbot_pw_lab/tools/deployed_ref.py --write    # move release.env, then rebuild\n"
               "  uv run python paintbot_pw_lab/tools/deployed_ref.py --docs-sha 7b2b19f5  # diff from another basis\n"
               "exit: 0 current; 1 behind league / just written / untagged; 2 usage; 3 environment missing",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true",
                        help="print exactly one JSON object to stdout; human text goes to stderr")
    parser.add_argument("--write", action="store_true",
                        help="if the league moved, set PW_RELEASE_TAG/PW_RELEASE_SHA in tools/release.env "
                             "to its release (exit 1: rebuild next). Never touches PW_DOCS_SHA.")
    parser.add_argument("--docs-sha", help="diff the rule files from this commit instead of release.env's "
                                           "PW_DOCS_SHA (e.g. --docs-sha 570174a2)")
    parser.add_argument("--clone", type=Path, default=DEFAULT_CLONE,
                        help=f"paintbot-pw source clone for the diffstat, only fetched (default {DEFAULT_CLONE}; "
                             "env PW_CLONE)")
    args = parser.parse_args(argv)
    say = (lambda *a: print(*a, file=sys.stderr)) if args.json else print  # noqa: E731

    try:
        env = pw_release.read_env()
    except (OSError, ValueError) as err:
        parser.error(f"cannot read {pw_release.RELEASE_ENV}: {err}")
    docs_sha = args.docs_sha or env["PW_DOCS_SHA"]
    envelope = {"ok": False, "tool": "deployed_ref", "release_tag": env["PW_RELEASE_TAG"],
                "inputs": {"write": args.write, "docs_sha": docs_sha, "clone": str(args.clone),
                           "release_env": str(pw_release.RELEASE_ENV)},
                "outputs": [], "counts": {"processed": 0, "failed": 0, "excluded": 0},
                "failures": [], "result": None, "next": []}

    def finish(code: int) -> int:
        if args.json:
            print(json.dumps(envelope))
        return code

    try:
        leagues = resolve_leagues(release_tags())
        tracked = next(row for row in leagues if row["tracked"])
        diff = rule_diffstat(args.clone, docs_sha, tracked["sha"]) if tracked["sha"] else []
    except EnvironmentMissing as err:
        say(f"ERROR: {err}")
        envelope["failures"].append({"id": "environment", "code": "environment_missing", "message": str(err)})
        envelope["counts"]["failed"] = 1
        return finish(3)

    envelope["counts"]["processed"] = len(leagues)
    for row in leagues:
        note = "" if row["tracked"] else "  (reference only; not what the lab pins track)"
        say(f"{row['label']:22} coworld {row['coworld']} {row['coworld_id']} version {row['version']} -> "
            f"{row['tag'] or 'UNKNOWN COWORLD NAME'} {row['sha'][:8] if row['sha'] else 'NO TAG'}{note}")

    current = tools_current(tracked["tag"], tracked["sha"], env)
    written = False
    if tracked["sha"] is None:
        msg = (f"league version {tracked['version']} has no release tag {tracked['tag']} in {SOURCE_REPO}"
               if tracked["tag"] else f"unknown coworld name {tracked['coworld']!r}: add it to TAG_PREFIX")
        envelope["failures"].append({"id": tracked["label"], "code": "untagged", "message": msg})
        envelope["counts"]["failed"] = 1
        say(f"ERROR: {msg}")
    elif not current and args.write:
        pw_release.write_env(tracked["tag"], tracked["sha"])
        written = True
        envelope["outputs"].append(str(pw_release.RELEASE_ENV))

    say(f"tools pinned at: {env['PW_RELEASE_TAG']} {env['PW_RELEASE_SHA']} (tools/release.env)")
    if current:
        say("TOOLS: current for the deployed build")
    elif written:
        say(f"TOOLS: release.env UPDATED to {tracked['tag']} {tracked['sha'][:8]}; rebuild before using the tools:")
        envelope["next"] += REBUILD
    elif tracked["sha"]:
        say(f"TOOLS: BEHIND the league ({tracked['tag']} {tracked['sha'][:8]}). Move the pin and rebuild:")
        envelope["next"] += ["uv run python paintbot_pw_lab/tools/deployed_ref.py --write", *REBUILD]
    for command in envelope["next"]:
        say(f"  {command}")

    changed = [d for d in diff if d["added"] or d["deleted"] or d["added"] is None]
    if tracked["sha"]:
        say(f"docs verified at: {docs_sha}; rule-bearing engine files {docs_sha}..{tracked['sha'][:8]}:")
        for d in diff:
            say(f"  {d['path']:52} +{d['added']} -{d['deleted']}")
        if changed:
            say(f"DOCS: {len(changed)} rule-bearing file(s) changed since {docs_sha}. Read the diff and re-verify "
                f"any affected claim in {', '.join(DOCS_TO_REVERIFY)} (paintbot_pw_lab/) before trusting it:")
            diff_cmd = (f"git -C {args.clone} diff {docs_sha} {tracked['sha'][:8]} -- " + " ".join(RULE_FILES))
            say(f"  {diff_cmd}")
            envelope["next"].append(diff_cmd)
        else:
            say("DOCS: no rule-bearing file changed; the docs' rule claims and line citations still hold.")

    envelope["result"] = {
        "leagues": leagues,
        "tracked": {"tag": tracked["tag"], "sha": tracked["sha"]},
        "release_env": {"before": env, "after": pw_release.read_env()},
        "tools_current": current, "written": written,
        "docs_sha": docs_sha, "rule_files": list(RULE_FILES), "rule_diffstat": diff,
        "docs_rule_files_changed": len(changed), "docs_to_reverify": list(DOCS_TO_REVERIFY) if changed else [],
    }
    envelope["ok"] = current
    return finish(0 if current else 1)


if __name__ == "__main__":
    sys.exit(main())
