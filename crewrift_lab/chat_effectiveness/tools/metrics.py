"""Join accusation events to ground-truth outcomes and compute the three
study metrics: crew accusation accuracy, same-meeting effectiveness, and
seat-normalized win-rate association — all per player/policy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def enrich_accusations(accusations: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    """Add speaker/target policy identity + speaker's win, by (episode, slot)."""
    speaker_cols = outcomes.rename(
        columns={"slot": "speaker_slot", "policy_name": "speaker_policy", "win": "speaker_win"}
    )[["episode", "speaker_slot", "speaker_policy", "speaker_win"]]
    target_cols = outcomes.rename(
        columns={"slot": "target_slot", "policy_name": "target_policy"}
    )[["episode", "target_slot", "target_policy"]]
    enriched = accusations.merge(speaker_cols, on=["episode", "speaker_slot"], how="left")
    enriched = enriched.merge(target_cols, on=["episode", "target_slot"], how="left")
    return enriched


def crew_accuracy_table(enriched: pd.DataFrame) -> pd.DataFrame:
    """Per crew speaker policy: accusation accuracy vs. actual imposter identity."""
    crew_accusations = enriched[(enriched.speaker_role == "crew") & (enriched.stance == "accuses")]
    grouped = crew_accusations.groupby("speaker_policy").agg(
        n=("target_is_imposter", "size"),
        accuracy=("target_is_imposter", "mean"),
    )
    return grouped.reset_index().sort_values("accuracy", ascending=False)


def effectiveness_table(enriched: pd.DataFrame) -> pd.DataFrame:
    """Per (speaker_policy, speaker_role): does an accusation move the room?"""
    accusations = enriched[enriched.stance == "accuses"]
    grouped = accusations.groupby(["speaker_policy", "speaker_role"]).agg(
        n=("target_voted_same_meeting", "size"),
        p_target_voted=("target_voted_same_meeting", "mean"),
        p_target_ejected=("target_ejected_same_meeting", "mean"),
        mean_baseline_rate=("num_candidates", lambda s: (1 / s).mean() if len(s) else float("nan")),
    )
    return grouped.reset_index()


def winrate_association_table(enriched: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    """Per (policy_name, role): seat-normalized win rate vs. accusation volume/accuracy.

    Uses `outcomes` (every seat-game, not just those with an accusation) so a
    policy that never accuses gets an explicit accusations_made=0 row instead
    of being silently absent.
    """
    seat_games = outcomes.groupby(["policy_name", "role"]).agg(
        seat_games=("win", "size"),
        seat_win_rate=("win", "mean"),
    )
    accusations = enriched[enriched.stance == "accuses"]
    accusation_stats = accusations.groupby(["speaker_policy", "speaker_role"]).agg(
        accusations_made=("target_is_imposter", "size"),
        accuracy=("target_is_imposter", "mean"),
    )
    accusation_stats.index = accusation_stats.index.set_names(["policy_name", "role"])
    joined = seat_games.join(accusation_stats, how="left")
    joined["accusations_made"] = joined["accusations_made"].fillna(0).astype(int)
    return joined.reset_index()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute chat-effectiveness metric tables.")
    parser.add_argument("--accusations", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    accusations = pd.read_parquet(args.accusations)
    outcomes = pd.read_parquet(args.outcomes)
    enriched = enrich_accusations(accusations, outcomes)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    crew_accuracy_table(enriched).to_parquet(args.out_dir / "crew_accuracy.parquet", index=False)
    effectiveness_table(enriched).to_parquet(args.out_dir / "effectiveness.parquet", index=False)
    winrate_association_table(enriched, outcomes).to_parquet(args.out_dir / "winrate_association.parquet", index=False)
    print(f"Wrote metric tables -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
