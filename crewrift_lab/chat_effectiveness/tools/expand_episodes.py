#!/usr/bin/env python3
"""Expand every downloaded episode's replay.json into <out>/<episode>.jsonl via
a version-matched expand_replay binary — the join key this whole lab uses
(the episode directory name) becomes the output filename stem, matching
replay_parse.parse_game's default and episode_outcomes.py's convention.

Usage:
    uv run python crewrift_lab/chat_effectiveness/tools/expand_episodes.py \
        --episodes /tmp/chat_eff_eps --expand-replay /tmp/expand-043 \
        --out /tmp/chat_eff_expanded
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def expand_one(expand_replay_bin: Path, replay_path: Path, out_path: Path) -> tuple[bool, str]:
    """Returns (ok, reason). ok=False on nonzero exit or a missing/false trace_complete."""
    result = subprocess.run(
        [str(expand_replay_bin), "--format", "jsonl", "--snapshot-every", "24", str(replay_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, f"expand_replay exit {result.returncode}: {result.stderr.strip()[:200]}"
    out_path.write_text(result.stdout)
    if '"key":"trace_complete"' not in result.stdout.replace(" ", ""):
        return False, "no trace_complete event in output"
    if '"complete":true' not in result.stdout.replace(" ", ""):
        return False, "trace_complete present but complete=false (hash-fail / version skew)"
    return True, "ok"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=Path, required=True, help="Dir of episode subdirs (each with replay.json).")
    parser.add_argument("--expand-replay", type=Path, required=True, help="Version-matched expand_replay binary.")
    parser.add_argument("--out", type=Path, required=True, help="Output dir for <episode>.jsonl files.")
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    episode_dirs = sorted(d for d in args.episodes.iterdir() if d.is_dir())
    if not episode_dirs:
        sys.exit(f"No episode subdirs in {args.episodes}")

    ok_count = 0
    failures: list[str] = []
    for d in episode_dirs:
        replay_path = d / "replay.json"
        if not replay_path.exists():
            failures.append(f"{d.name}: no replay.json")
            continue
        out_path = args.out / f"{d.name}.jsonl"
        ok, reason = expand_one(args.expand_replay, replay_path, out_path)
        if ok:
            ok_count += 1
        else:
            failures.append(f"{d.name}: {reason}")
            out_path.unlink(missing_ok=True)

    print(f"Expanded {ok_count}/{len(episode_dirs)} episodes -> {args.out}", file=sys.stderr)
    if failures:
        print(f"{len(failures)} failures:", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        print(
            "A nonzero failure count usually means the expand_replay binary doesn't match "
            "the deployed game build (version/button-vote-resolution skew) — verify against "
            "the live coworld's source_url commit before trusting a partial expand.",
            file=sys.stderr,
        )
    return 1 if failures and ok_count == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
