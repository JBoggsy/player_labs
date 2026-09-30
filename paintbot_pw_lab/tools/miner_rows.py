#!/usr/bin/env python3
"""Build the JSONL rows the `coworld-hypothesis-miner` engine mines for Paintbot PW.

One row per (episode, our policy): the policy's 8 seats in one episode are one sample, never
eight (lab doctrine; the unit of pw_metrics.policy_metrics). Rows come from hash-checked
episodes loaded by pw_episodes.py; numbers come from pw_metrics.py (policy and team level),
engagement and opening-duel counts from pw_fights.py, anomaly-flag counts from pw_flags.py,
a few first-event ticks read from the tables here, and, when our seat logs exist, the PWI
intent summary (pw_intent.py). `features.py` is the matching adapter.

Every episode under the roots is accounted for: loaded and used, policy absent, mirror
(the policy on both teams: no own-vs-other score), or failed to load. The counts print to
stderr and the command exits 1 when any episode failed to load.

Usage:
  uv run python paintbot_pw_lab/tools/miner_rows.py ROOT [ROOT ...] --policy KEY_OR_NAME \
      --out /tmp/mine/rows.jsonl
  MINER=.claude/skills/coworld-hypothesis-miner/scripts
  uv run python $MINER/mine_hypotheses.py --rows /tmp/mine/rows.jsonl \
      --adapter paintbot_pw_lab/tools/features.py --top 5

Score (`--score`, stored in each row; the adapter reads it):
  elo   the ladder's Elo outcome score, clamp(0.5 + (our glory - their glory)/2000, 0, 1) (default;
        what league rank moves by, docs/mechanics.md §1.3)
  win   1 win, 0.5 draw, 0 loss
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pw_cli  # noqa: E402
import pw_episodes as pe  # noqa: E402
import pw_fights  # noqa: E402
import pw_flags  # noqa: E402
import pw_intent  # noqa: E402
import pw_metrics as pm  # noqa: E402

SCORES = ("elo", "win")
RESULT_SCORE = {"win": 1.0, "draw": 0.5, "loss": 0.0}
# Flags that describe the outcome rather than a behavior are left out of the rows.
OUTCOME_FLAGS = {"zero_glory_win"}
TEAM_FIELDS = ("first_capture_tick", "capture_starts", "capture_resets", "contests", "lead_changes",
               "hearts_held_mean", "longest_supply_gap_ticks", "glory_glory_heart", "cogs_out_end", "team_lives_end")


def _clean(value):
    """JSON-safe scalar: NaN/NA -> None, numpy -> Python."""
    if isinstance(value, (str, list, dict)):
        return value
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def _first(frame, mask) -> int | None:
    ticks = frame.loc[mask, "t"]
    return None if ticks.empty else int(ticks.min())


def first_ticks(ep, team: int) -> dict:
    """First-event ticks for one team (None = never happened in the match)."""
    kills, captures, damage = ep["kills"], ep["captures"], ep["damage"]
    enemy_kill = kills["seat"].notna() & ~kills["friendly"].fillna(False).astype(bool) & ~kills["self"].fillna(False).astype(bool)
    complete = captures["kind"] == "capture_complete"
    return {
        "first_kill_tick": _first(kills, enemy_kill & (kills["team"] == team)),
        "first_death_tick": _first(kills, kills["victim_team"] == team),
        "enemy_first_death_tick": _first(kills, kills["victim_team"] == 1 - team),
        "first_heart_lost_tick": _first(captures, complete & (captures["previous_owner"] == team) & (captures["team"] != team)),
        "first_friendly_hit_tick": _first(damage, damage["friendly"].fillna(False).astype(bool) & (damage["team"] == team)
                                          & ~damage["self"].fillna(False).astype(bool)),
    }


def intent_block(ep, seats: list[int]) -> dict | None:
    """Our seats' PWI summary, or None when none of them has a seat log (unknown, not zero)."""
    summary = pw_intent.intent_summary(ep)
    if summary.empty:
        return None
    mine = summary[summary["seat"].isin(seats)]
    if mine.empty:
        return None
    lines = int(mine["intent_lines"].sum())
    block = {"seats_logged": int(len(mine)), "intent_lines": lines, "bad_lines": int(mine["bad_lines"].sum()),
             "vm_errors": int(mine["vm_errors"].sum()), "heart_switches": int(mine["heart_switches"].sum())}
    # Line-weighted mode shares across our seats (sum of per-seat shares x lines / all lines).
    for name in pw_intent.MODE_NAMES.values():
        column = f"mode_share_{name}"
        block[column] = None if lines == 0 else float((mine[column].fillna(0) * mine["intent_lines"]).sum() / lines)
    return block


def flag_counts(flags, key: str, team: int) -> dict:
    """Our policy's flags by name (seat flags of our seats, plus team-level flags of our team)."""
    mine = flags[(flags["policy_key"] == key) | (flags["seat"].isna() & (flags["team"] == team))]
    counts = {name: 0 for name in pw_flags.FLAG_NAMES if name not in OUTCOME_FLAGS}
    for name, count in mine["flag"].value_counts().items():
        if name in counts:
            counts[name] = int(count)
    return counts


def episode_row(ep, policy_row, team_row, score_kind: str, fights_row=None, flags=None) -> dict:
    team = int(policy_row["team"])
    seats = ep["seats"]
    our_seats = [int(s) for s in seats.loc[seats["policy_key"] == policy_row["policy_key"], "seat"]]
    opponents = sorted(set(seats.loc[seats["team"] != team, "policy_key"].astype(str)))
    ticks = int(ep["episodes"]["ticks"].iloc[0])
    result = str(policy_row["result"])
    score = _clean(policy_row["elo_outcome"]) if score_kind == "elo" else RESULT_SCORE.get(result)
    metrics = {key: _clean(value) for key, value in policy_row.items()
               if key not in ("episode_id", "policy_key", "policy_version_id", "policy_name", "result")}
    return {
        "episode_id": ep.episode_id, "policy_key": str(policy_row["policy_key"]),
        "policy_name": _clean(policy_row["policy_name"]), "team": team, "opponents": opponents,
        "source": str(ep["episodes"]["source"].iloc[0]), "rules": int(ep["episodes"]["rules"].iloc[0]),
        "ticks": ticks, "result": result, "score_kind": score_kind, "score": score,
        "metrics": metrics,
        "team_metrics": {key: _clean(team_row[key]) for key in TEAM_FIELDS},
        "timing": first_ticks(ep, team),
        "fights": None if fights_row is None else {key: _clean(value) for key, value in fights_row.items()
                                                   if key not in ("episode_id", "policy_key", "policy_name", "team")},
        "flags": None if flags is None else flag_counts(flags, str(policy_row["policy_key"]), team),
        "intent": intent_block(ep, our_seats),
    }


def matches(policy_row, wanted: str) -> bool:
    return wanted in (str(policy_row["policy_key"]), str(policy_row["policy_name"]))


def build_rows(batch, wanted: str, score_kind: str) -> tuple[list[dict], Counter]:
    rows, tally = [], Counter()
    for ep in batch.episodes:
        seat_rows = pm.seat_metrics(ep)
        policies = pm.policy_metrics(ep, seat_rows)
        teams = pm.team_metrics(ep, seat_rows)
        fights = pw_fights.fight_policy_metrics(ep)
        flags = pw_flags.episode_flags(ep)
        hits = [row for _, row in policies.iterrows() if matches(row, wanted)]
        if not hits:
            tally["policy_absent"] += 1
            continue
        for row in hits:
            if _clean(row["team"]) is None:
                tally["mirror_both_teams"] += 1
                continue
            team_row = teams[teams["team"] == int(row["team"])].iloc[0]
            fights_row = fights[fights["policy_key"] == row["policy_key"]]
            out = episode_row(ep, row, team_row, score_kind, None if fights_row.empty else fights_row.iloc[0], flags)
            if out["score"] is None:
                tally["no_score"] += 1
                continue
            rows.append(out)
            tally["used"] += 1
    return rows, tally


def build_parser() -> pw_cli.ArgumentParser:
    parser = pw_cli.ArgumentParser("miner_rows", __doc__, examples=[
        "uv run python paintbot_pw_lab/tools/miner_rows.py ROOT --policy james-pw --out /tmp/mine/rows.jsonl --json",
        "uv run python paintbot_pw_lab/tools/miner_rows.py ROOT --json    # lists the policies (exit 2)"])
    parser.add_argument("roots", nargs="+", type=Path, help="episode dirs, batch dirs or NAME.replay files")
    parser.add_argument("--policy", help="policy_key (policy_version_id or local:<name>) or policy_name; "
                                         "omitted or unknown: exit 2 listing the batch's policies")
    parser.add_argument("--score", choices=SCORES, default="elo", help="row score (default %(default)s)")
    parser.add_argument("--out", type=Path, help="JSONL output (default: stdout; required with --json), "
                                                 "e.g. paintbot_pw_lab/analysis/miner/rows.jsonl")
    parser.add_argument("--refresh", action="store_true", help="re-trace even when the cache is valid")
    return parser


def run_cli(args, report: pw_cli.Report) -> dict:
    if report.json_mode and not args.out:
        raise pw_cli.UsageError("--json needs --out FILE (stdout carries the envelope, not the rows)")
    batch = pe.load_batch(args.roots, refresh=args.refresh)
    report.add_batch(batch)
    for path, code, message in batch.failures:
        print(f"FAILED {code}: {path}: {message}", file=sys.stderr)
    keys = Counter()
    for ep in batch.episodes:
        for row in pm.policy_metrics(ep).itertuples():
            keys[(row.policy_key, row.policy_name)] += 1
    valid = sorted({str(v) for key in keys for v in key if v is not None and v == v})
    if not args.policy or (batch.episodes and args.policy not in valid):
        print("pass --policy; policies in this batch (episodes):", file=sys.stderr)
        for (key, name), count in keys.most_common():
            print(f"  {count:4d}  {key}  ({name})", file=sys.stderr)
        raise pw_cli.UsageError("--policy is required" if not args.policy else f"--policy {args.policy!r} is not in "
                                "these episodes", valid)
    rows, tally = build_rows(batch, args.policy, args.score)
    tally["load_failed"] = len(batch.failures)
    text = "".join(json.dumps(row) + "\n" for row in rows)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        report.output(args.out)
        report.suggest("uv run python .claude/skills/coworld-hypothesis-miner/scripts/mine_hypotheses.py "
                       f"--rows {args.out} --adapter paintbot_pw_lab/tools/features.py --top 5")
    else:
        sys.stdout.write(text)
    print(f"{len(batch.episodes) + len(batch.failures)} episodes: " +
          ", ".join(f"{key} {count}" for key, count in sorted(tally.items())) +
          (f" -> {args.out}" if args.out else ""), file=sys.stderr)
    warning = None
    if len(rows) < 8:
        warning = f"{len(rows)} rows; the miner needs at least 8 usable episodes"
        print(f"warning: {warning}", file=sys.stderr)
    report.counts.update(rows=len(rows), excluded=sum(v for k, v in tally.items() if k not in ("used", "load_failed")))
    return {"rows": len(rows), "tally": dict(tally), "out": str(args.out) if args.out else None, "warning": warning}


def main(argv: list[str] | None = None) -> int:
    return pw_cli.run(build_parser(), run_cli, argv)


if __name__ == "__main__":
    raise SystemExit(main())
