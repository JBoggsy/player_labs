"""Per-(episode, slot) ground-truth outcomes: policy identity, role, win.

Reads a downloaded episode directory's episode.json (policy identity per
seat) and results.json (per-slot win/role arrays) into one row per seat.
The join key is the episode directory's own name (matches
expand_corpus.py's `<ep_dir.name>.jsonl.gz` output and
replay_parse.parse_game's default episode-from-path-stem) — NOT
episode.json's internal id/episode_id fields, which don't correspond to it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

OUTCOME_COLUMNS = ["episode", "slot", "policy_name", "policy_version", "role", "win", "score"]


def _policy_by_position(episode: dict) -> dict[int, dict]:
    """slot/position -> {policy_name, policy_version, player_name}."""
    by_position: dict[int, dict] = {}
    for pt in episode.get("participants", []):
        by_position[pt["position"]] = {
            "policy_name": pt["policy_name"],
            "policy_version": pt["version"],
            "player_name": pt.get("player_name", ""),
        }
    if by_position:
        return by_position
    # League-shaped episode.json fallback (policy_results[] instead of
    # participants[]) — unverified against real local data as of this plan;
    # confirm against a real league-scraped episode.json before trusting it.
    for pr in episode.get("policy_results", []):
        by_position[pr["position"]] = {
            "policy_name": pr["policy"]["name"],
            "policy_version": pr["policy"]["version"],
            "player_name": pr.get("policy", {}).get("player_name", ""),
        }
    return by_position


def parse_episode_outcome(episode_dir: Path) -> list[dict]:
    episode = json.loads((episode_dir / "episode.json").read_text())
    results = json.loads((episode_dir / "results.json").read_text())
    episode_key = episode_dir.name
    policies = _policy_by_position(episode)

    rows: list[dict] = []
    for slot in range(len(results["win"])):
        policy = policies.get(slot, {"policy_name": "", "policy_version": None, "player_name": ""})
        rows.append(
            {
                "episode": episode_key,
                "slot": slot,
                "policy_name": policy["policy_name"],
                "policy_version": policy["policy_version"],
                "role": "imposter" if results["imposter"][slot] else "crew",
                "win": bool(results["win"][slot]),
                "score": results["scores"][slot],
            }
        )
    return rows


def build_outcomes_table(episodes_root: Path) -> pd.DataFrame:
    rows: list[dict] = []
    for d in sorted(episodes_root.iterdir()):
        if not d.is_dir():
            continue
        if not (d / "episode.json").exists() or not (d / "results.json").exists():
            continue
        rows.extend(parse_episode_outcome(d))
    return pd.DataFrame(rows, columns=OUTCOME_COLUMNS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the per-slot outcomes table.")
    parser.add_argument("--episodes", type=Path, required=True, help="Dir of episode subdirs (episode.json + results.json each).")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    df = build_outcomes_table(args.episodes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"Wrote {len(df)} outcome rows -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
