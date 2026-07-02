"""Sample chat lines and compare the regex detector's (stance, target) call
against the event-warehouse's LLM-based `suss` labels, to bound confidence in
the regex-derived accuracy/effectiveness numbers computed elsewhere in this
package. The live LLM labels come from the existing
`crewrift-event-warehouse suss` job (Bedrock-backed) — this module only
consumes its output parquet, it does not call Bedrock itself.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

import pandas as pd

SUSPICION_LAB_TOOLS = Path(__file__).resolve().parents[2] / "suspicion_lab" / "tools"
sys.path.insert(0, str(SUSPICION_LAB_TOOLS))
from features import ACCUSE_HINT, DEFEND_HINT  # noqa: E402
from replay_parse import Game, parse_game  # noqa: E402


def _color_lookup(game: Game) -> tuple[re.Pattern, dict[str, int]]:
    by_color = {p.color.lower(): p.slot for p in game.players.values() if p.color}
    alternation = "|".join(sorted((re.escape(c) for c in by_color), key=len, reverse=True))
    return re.compile(rf"\b({alternation})\b", re.IGNORECASE), by_color


def regex_lines(game: Game) -> list[dict]:
    """Every classifiable chat line with tick + raw text, for sampling."""
    if not game.players or not game.meetings:
        return []
    pattern, by_color = _color_lookup(game)
    rows: list[dict] = []
    for mi, meeting in enumerate(game.meetings):
        for chat in meeting.chats:
            text = chat.text or ""
            named = [by_color[m.group(1).lower()] for m in pattern.finditer(text)]
            named = [s for s in named if s != chat.slot]
            if not named:
                continue
            if DEFEND_HINT.search(text):
                stance = "defends"
            elif ACCUSE_HINT.search(text):
                stance = "accuses"
            else:
                continue
            rows.append(
                {
                    "episode": game.episode,
                    "meeting_idx": mi,
                    "tick": chat.tick,
                    "speaker_slot": chat.slot,
                    "text": text,
                    "regex_stance": stance,
                    "regex_target_slot": named[0],
                }
            )
    return rows


def sample_lines(expanded: Path, n: int, seed: int) -> pd.DataFrame:
    paths = sorted(list(expanded.glob("*.jsonl.gz")) + list(expanded.glob("*.jsonl")))
    all_rows: list[dict] = []
    for path in paths:
        try:
            game = parse_game(path)
        except Exception:  # noqa: BLE001 - skip corrupt games
            continue
        if game.complete:
            all_rows.extend(regex_lines(game))
    rng = random.Random(seed)
    if len(all_rows) > n:
        all_rows = rng.sample(all_rows, n)
    return pd.DataFrame(all_rows)


def compute_agreement(sample: pd.DataFrame, chat_suss: pd.DataFrame) -> dict:
    """Join the regex sample to warehouse chat_suss rows on (episode, speaker
    slot, tick) and compute stance/target agreement rates.
    """
    if chat_suss.empty:
        return {"n_matched": 0, "stance_agreement": None, "target_agreement": None}
    suss = chat_suss.rename(columns={"episode_id": "episode", "slot": "speaker_slot", "ts": "tick"})
    joined = sample.merge(suss, on=["episode", "speaker_slot", "tick"], how="inner")
    if joined.empty:
        return {"n_matched": 0, "stance_agreement": None, "target_agreement": None}
    stance_agree = (joined["regex_stance"] == "accuses") == joined["is_suss"]
    accused_rows = joined[joined["is_suss"]]
    target_agree = (
        (accused_rows["regex_target_slot"] == accused_rows["suss_target_slot"]).mean()
        if len(accused_rows)
        else None
    )
    return {
        "n_matched": int(len(joined)),
        "n_sampled": int(len(sample)),
        "stance_agreement": float(stance_agree.mean()),
        "target_agreement": None if target_agree is None else float(target_agree),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the regex accusation detector against LLM suss labels.")
    parser.add_argument("--expanded", type=Path, required=True)
    parser.add_argument("--chat-suss", type=Path, required=True, help="events/key=chat_suss/*.parquet from the warehouse.")
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    sample = sample_lines(args.expanded, args.n, args.seed)
    chat_suss_raw = pd.read_parquet(args.chat_suss)
    value_df = pd.json_normalize(chat_suss_raw["value"].apply(json.loads))
    chat_suss = pd.concat([chat_suss_raw.drop(columns=["value"]), value_df], axis=1)

    agreement = compute_agreement(sample, chat_suss)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(agreement, indent=2))
    print(json.dumps(agreement, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
