#!/usr/bin/env python3
"""Resolve the current top-N champions' exact policy_ref labels and emit a
ready-to-POST experience-request roster body — pinned refs, not top_n/random.

`top_n`/`random` roster selectors hit a real server-side 500 (a query timeout
on the eligible_champions/mean_reward ranking join) as of 2026-07-02. Pinning
explicit `policy_ref`s sidesteps that query entirely and works immediately, at
the cost of resolving the roster yourself instead of letting the server do it.

The API requires exactly one roster entry per game seat (Crewrift = 8), so
--top-n should match the target game's seat count — if fewer champions than
requested are resolved (thin field), pad the roster by hand before posting.

Usage:
    uv run python crewrift_lab/chat_effectiveness/tools/resolve_champion_roster.py \
        --division div_... --top-n 8 --num-episodes 100 \
        --notes "field eval, natural roles" --out /tmp/req.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def _coworld_json(*args: str) -> object:
    result = subprocess.run(
        ["coworld", *args, "--json"], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def resolve_champion_labels(division_id: str, top_n: int) -> list[dict]:
    """Top-N players by leaderboard rank -> their current champion policy label.

    Returns a list of {"player_name", "player_id", "policy_ref"} dicts, ranked.
    """
    results = _coworld_json("results", division_id)
    memberships = _coworld_json("memberships", "--division", division_id, "--active-only")

    champion_label_by_player: dict[str, str] = {
        m["player"]["id"]: m["policy_version"]["label"]
        for m in memberships
        if m.get("is_champion") and m["status"] == "competing"
    }

    roster: list[dict] = []
    for row in results[:top_n]:
        player_id = row["player_id"]
        label = champion_label_by_player.get(player_id)
        if label is None:
            print(
                f"  ! no active champion membership for {row['player_name']} ({player_id}) — skipped",
                file=sys.stderr,
            )
            continue
        roster.append({"player_name": row["player_name"], "player_id": player_id, "policy_ref": label})
    return roster


def build_request_body(roster: list[dict], num_episodes: int, division_id: str, notes: str) -> dict:
    return {
        "target": {"division_id": division_id},
        "roster": [{"player": {"policy_ref": entry["policy_ref"]}} for entry in roster],
        "num_episodes": num_episodes,
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--division", required=True, help="division_id (div_...).")
    parser.add_argument("--top-n", type=int, default=8, help="How many top-ranked players to pin.")
    parser.add_argument("--num-episodes", type=int, default=100, help="Per-request episode count (API caps at 100).")
    parser.add_argument("--notes", default="pinned-champion field eval, natural roles, rotating seats")
    parser.add_argument("--out", required=True, help="Path to write the request body JSON.")
    args = parser.parse_args(argv)

    roster = resolve_champion_labels(args.division, args.top_n)
    if not roster:
        sys.exit("No champions resolved — check the division id and that it has active competing champions.")

    print(f"Resolved {len(roster)} champions:", file=sys.stderr)
    for entry in roster:
        print(f"  {entry['player_name']:<24} {entry['policy_ref']}", file=sys.stderr)

    body = build_request_body(roster, args.num_episodes, args.division, args.notes)
    with open(args.out, "w") as f:
        json.dump(body, f, indent=2)
    print(f"Wrote roster body ({args.num_episodes} episodes) -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
