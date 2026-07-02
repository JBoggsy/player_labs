"""Extract (speaker, stance, target) accusation events per meeting, joined to
same-meeting vote/ejection outcomes and ground-truth roles — for ALL
speakers (crew and imposter), unlike suspicion_lab's build_dataset.py, which
aggregates crew-observer-only, prior-meetings-only cumulative features for
training crewborg's own suspicion model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

SUSPICION_LAB_TOOLS = Path(__file__).resolve().parents[2] / "suspicion_lab" / "tools"
sys.path.insert(0, str(SUSPICION_LAB_TOOLS))
from features import chat_stances  # noqa: E402
from replay_parse import Game, parse_game  # noqa: E402

ACCUSATION_COLUMNS = [
    "episode", "meeting_idx", "call_tick", "speaker_slot", "speaker_role",
    "stance", "target_slot", "target_role", "target_is_imposter",
    "target_voted_same_meeting", "target_ejected_same_meeting", "num_candidates",
]


def _alive_at(game: Game, slot: int, tick: int) -> bool:
    state = game.state_at(slot, tick)
    return bool(state and state.alive and state.connected)


def _ejected_slot_by_meeting(game: Game) -> dict[int, int]:
    """meeting_idx -> ejected slot, derived from game.ejections (the raw,
    reliably-populated list) rather than Meeting.ejected_slot.

    replay_parse.py's per-meeting ejected_slot assignment is order-sensitive:
    it's only set if the meeting's end_tick is still None when the `died`
    event is processed, but the `phase: Playing/GameOver` event that CLOSES
    the meeting (setting end_tick) fires at the SAME tick as `died` and is
    emitted first in the stream — so ejected_slot silently never gets set in
    practice (verified: 0/73 meetings across a 30-game sample). game.ejections
    is appended to unconditionally, so bucket each ejection tick into the
    meeting whose [call_tick, next_call_tick) window contains it instead.
    """
    call_ticks = [m.call_tick for m in game.meetings] + [game.tick_count + 1]
    result: dict[int, int] = {}
    for tick, slot in game.ejections:
        for idx in range(len(game.meetings)):
            if call_ticks[idx] <= tick < call_ticks[idx + 1]:
                result[idx] = slot
                break
    return result


def extract_accusation_rows(game: Game) -> list[dict]:
    if not game.players or not game.meetings:
        return []
    stances = chat_stances(game)
    ejected_by_meeting = _ejected_slot_by_meeting(game)
    rows: list[dict] = []
    for triple in stances:
        meeting = game.meetings[triple.meeting_idx]
        speaker = game.players.get(triple.speaker_slot)
        target = game.players.get(triple.target_slot)
        if speaker is None or target is None:
            continue
        candidates = [
            slot for slot in game.players
            if slot != triple.speaker_slot and _alive_at(game, slot, meeting.call_tick)
        ]
        rows.append(
            {
                "episode": game.episode,
                "meeting_idx": triple.meeting_idx,
                "call_tick": meeting.call_tick,
                "speaker_slot": triple.speaker_slot,
                "speaker_role": speaker.role,
                "stance": triple.stance,
                "target_slot": triple.target_slot,
                "target_role": target.role,
                "target_is_imposter": target.role == "imposter",
                "target_voted_same_meeting": any(v.target_slot == triple.target_slot for v in meeting.votes),
                "target_ejected_same_meeting": ejected_by_meeting.get(triple.meeting_idx) == triple.target_slot,
                "num_candidates": len(candidates),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract accusation events from expanded replays.")
    parser.add_argument("--expanded", type=Path, required=True, help="Dir of *.jsonl(.gz) expanded replays.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    paths = sorted(list(args.expanded.glob("*.jsonl.gz")) + list(args.expanded.glob("*.jsonl")))
    if args.limit:
        paths = paths[: args.limit]
    if not paths:
        sys.exit(f"No expanded episodes in {args.expanded}")

    all_rows: list[dict] = []
    skipped = 0
    for i, path in enumerate(paths):
        try:
            game = parse_game(path)
            if not game.complete:
                skipped += 1
                continue
            all_rows.extend(extract_accusation_rows(game))
        except Exception as exc:  # noqa: BLE001 - skip corrupt games, keep building
            print(f"  skip {path.name}: {exc}", file=sys.stderr)
            skipped += 1
        if (i + 1) % 100 == 0:
            print(f"  …{i + 1}/{len(paths)} episodes, {len(all_rows)} rows", file=sys.stderr)

    df = pd.DataFrame(all_rows, columns=ACCUSATION_COLUMNS)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"Wrote {len(df)} accusation rows from {len(paths) - skipped} games ({skipped} skipped) -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
