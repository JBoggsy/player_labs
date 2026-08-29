#!/usr/bin/env python3
"""Measure which replay action tick explains each observed aim transition."""

from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path

from players.player_sdk import SpriteWorld

from actions import TURN_CCW, TURN_CW
from dataset import ActionTimeline, read_actions
from observation_text import ObservationSnapshot, snapshots_from_jsonl


AIM_PATTERN = re.compile(r"^own aim (\d+)$")


def aim(snapshot: ObservationSnapshot) -> int | None:
    for entity in snapshot.entities:
        match = AIM_PATTERN.match(entity.label)
        if match:
            return int(match.group(1))
    return None


def signed_delta(before: int, after: int, turn: int = 256) -> int:
    return (after - before + turn // 2) % turn - turn // 2


def expected_delta(mask: int, turn_rate: int) -> int:
    clockwise = bool(mask & TURN_CW)
    counterclockwise = bool(mask & TURN_CCW)
    if clockwise == counterclockwise:
        return 0
    return turn_rate if counterclockwise else -turn_rate


def measure(
    snapshots: list[ObservationSnapshot],
    timeline: ActionTimeline,
    *,
    offsets: tuple[int, ...] = (-1, 0, 1),
    turn_rate: int = 5,
) -> dict:
    scores = {offset: {"matches": 0, "eligible": 0, "turn_matches": 0, "turns": 0} for offset in offsets}
    consecutive_pairs = 0
    for before, after in zip(snapshots, snapshots[1:]):
        if before.tick is None or after.tick != before.tick + 1:
            continue
        before_aim = aim(before)
        after_aim = aim(after)
        if before_aim is None or after_aim is None:
            continue
        observed = signed_delta(before_aim, after_aim)
        # Respawns and other discontinuities are not controller turn transitions.
        if observed not in (-turn_rate, 0, turn_rate):
            continue
        consecutive_pairs += 1
        for offset in offsets:
            mask = timeline.mask_at(before.tick + offset)
            expected = expected_delta(mask, turn_rate)
            score = scores[offset]
            score["eligible"] += 1
            score["matches"] += observed == expected
            if expected != 0:
                score["turns"] += 1
                score["turn_matches"] += observed == expected

    for score in scores.values():
        score["accuracy"] = score["matches"] / score["eligible"] if score["eligible"] else 0
        score["turn_accuracy"] = score["turn_matches"] / score["turns"] if score["turns"] else 0
    return {"consecutive_pairs": consecutive_pairs, "offsets": scores}


def snapshots_from_wire(path: Path, game_version: str) -> list[ObservationSnapshot]:
    from capture_wire_observations import snapshot_world

    world = SpriteWorld()
    snapshots = []
    with path.open() as source:
        for line in source:
            event = json.loads(line)
            if event.get("direction") != "in" or event.get("type") != "binary":
                continue
            if not world.apply_frame(base64.b64decode(event["data"])):
                continue
            try:
                snapshots.append(
                    snapshot_world(
                        world,
                        game_version=game_version,
                        source=str(path),
                        tick=int(event["tick"]),
                    )
                )
            except ValueError:
                continue
    return snapshots


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--snapshots", type=Path)
    source.add_argument("--wire", type=Path)
    parser.add_argument("--game-version")
    parser.add_argument("--actions", type=Path, required=True)
    parser.add_argument("--turn-rate", type=int, default=5)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.wire:
        if not args.game_version:
            parser.error("--game-version is required with --wire")
        snapshots = snapshots_from_wire(args.wire, args.game_version)
    else:
        with args.snapshots.open() as snapshot_source:
            snapshots = list(snapshots_from_jsonl(snapshot_source))
    result = measure(
        snapshots,
        ActionTimeline(read_actions(args.actions)),
        turn_rate=args.turn_rate,
    )
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
