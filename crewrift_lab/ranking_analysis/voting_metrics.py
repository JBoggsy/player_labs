#!/usr/bin/env python3
"""Crew voting behaviour + effectiveness, per policy, from the event warehouse.

Answers (all scoped to games played AS CREW, since that's the deficit under
study — see ranking_analysis/README.md and the v96 differential):

  1. vote rate per game (mean/median/std) — non-skip player-votes cast.
  2. chat rate per game (mean/median/std) — voting-phase messages sent.
  3. vote accuracy — of non-skip votes, % whose target is truly the imposter.
  4. ejection effectiveness — of non-skip votes: when the target is truly the
     imposter, how often does the room actually eject them (conversion)? When
     the target is truly a crewmate, how often does the room eject them anyway
     (friendly fire)? Both conditional on "voted for that true-role target",
     not on all votes cast — see the report's methodology note.
  5. win rate as crewmate.

Ejection ground truth has NO native event in the warehouse (verified against
the extractor source and empirically against real replays — see
crewrift_lab/TENTATIVE_LESSONS.md). It's derived here: a `died` event fires
exactly at the phase transition immediately after a meeting's `VoteResult`
(confirmed on real 0.4.42 replays: MeetingCall -> Voting -> VoteResult ->
{Playing,GameOver}, with `died` timestamped at that final transition, no
matching `kill`/`body` that tick). Each `died` is attributed to the meeting
whose `vote_called_body`/`vote_called_button` call is the most recent one at
or before it — implemented as a meeting-window join (this meeting's ts up to
the next meeting's ts), which also attributes every `vote_cast` to its meeting.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
WH = os.environ.get("RANK_WH", "/tmp/v96_rank_wh")
CLEAN = os.environ.get("RANK_CLEAN_EIDS", str(HERE / "data" / "clean_eids.txt"))
OUT = os.environ.get("RANK_VOTING_OUT", str(HERE / "data" / "voting_metrics.json"))

con = duckdb.connect()
con.execute(f"CREATE VIEW events AS SELECT * FROM read_parquet('{WH}/events/**/*.parquet', hive_partitioning=true)")
con.execute(f"CREATE VIEW ep AS SELECT * FROM read_parquet('{WH}/episode_players.parquet')")
clean = [l.strip() for l in open(CLEAN) if l.strip()]
con.execute("CREATE TABLE clean(eid VARCHAR)")
con.executemany("INSERT INTO clean VALUES (?)", [(c,) for c in clean])

# --- version-skew / replay-non-determinism check (see SKILL.md) ---
# Verified empirically (2026-07-06): ALL available expand_replay builds hash-fail at the
# IDENTICAL tick on the same replay -- this is intrinsic replay non-determinism ("fastMode"
# non-determinism, a previously-documented phenomenon in this lab), not a version mismatch
# a different binary could fix. Hash-failed episodes have sparse/truncated events past the
# fail tick, so they're excluded here (mirrors the existing connect-timeout clean-game
# philosophy) rather than silently biasing vote/chat/ejection counts downward.
skewed_ids = [r[0] for r in con.execute(
    "SELECT DISTINCT episode_id FROM events WHERE key='trace_warning' AND episode_id IN (SELECT eid FROM clean)"
).fetchall()]
n_skewed = len(skewed_ids)
con.execute("CREATE TABLE skewed(eid VARCHAR)")
con.executemany("INSERT INTO skewed VALUES (?)", [(c,) for c in skewed_ids])
con.execute("""
CREATE VIEW cevents AS SELECT * FROM events
WHERE episode_id IN (SELECT eid FROM clean) AND episode_id NOT IN (SELECT eid FROM skewed)
""")
con.execute("""
CREATE VIEW cep AS SELECT * FROM ep
WHERE episode_id IN (SELECT eid FROM clean) AND episode_id NOT IN (SELECT eid FROM skewed)
      AND slot >= 0 AND policy_name IS NOT NULL
""")
n_clean = len(clean) - n_skewed
print(f"clean episodes: {len(clean)}; trace_warning (excluded): {n_skewed}; analyzed: {n_clean}")

# --- meeting windows: each meeting call -> its ts and the NEXT meeting's ts (or NULL) ---
con.execute("""
CREATE TABLE meeting_windows AS
SELECT episode_id, ts AS meeting_ts,
       LEAD(ts) OVER (PARTITION BY episode_id ORDER BY ts) AS next_meeting_ts,
       row_number() OVER (PARTITION BY episode_id ORDER BY ts) AS meeting_idx
FROM cevents WHERE key IN ('vote_called_body','vote_called_button')
""")
n_meetings = con.execute("SELECT count(*) FROM meeting_windows").fetchone()[0]

# --- ejected slot per meeting: a `died` event inside the meeting's window ---
con.execute("""
CREATE TABLE ejections AS
SELECT mw.episode_id, mw.meeting_ts, d.slot AS ejected_slot
FROM cevents d
JOIN meeting_windows mw ON mw.episode_id = d.episode_id
  AND d.ts >= mw.meeting_ts AND (mw.next_meeting_ts IS NULL OR d.ts < mw.next_meeting_ts)
WHERE d.key = 'died' AND d.slot >= 0
""")
n_ejections = con.execute("SELECT count(*) FROM ejections").fetchone()[0]
# sanity: at most one ejection per meeting
dupe_meetings = con.execute("""
    SELECT count(*) FROM (SELECT episode_id, meeting_ts, count(*) c FROM ejections GROUP BY 1,2 HAVING c > 1)
""").fetchone()[0]
print(f"meetings: {n_meetings}; ejections resolved: {n_ejections}; meetings w/ >1 ejection (should be 0): {dupe_meetings}")

# --- votes cast, attributed to their meeting, with the target's TRUE role/policy + whether ejected ---
con.execute("""
CREATE TABLE vote_facts AS
SELECT mw.episode_id, mw.meeting_ts,
       v.slot AS voter_slot, v.policy_name AS voter_policy, v.role AS voter_role,
       json_extract_string(v.value,'$.target') AS raw_target,
       TRY_CAST(json_extract(v.value,'$.target_slot') AS INT) AS target_slot,
       tgt.role AS target_role, tgt.policy_name AS target_policy,
       (ej.ejected_slot IS NOT NULL) AS target_ejected
FROM cevents v
JOIN meeting_windows mw ON mw.episode_id = v.episode_id
  AND v.ts >= mw.meeting_ts AND (mw.next_meeting_ts IS NULL OR v.ts < mw.next_meeting_ts)
LEFT JOIN cep tgt ON tgt.episode_id = v.episode_id AND tgt.slot = TRY_CAST(json_extract(v.value,'$.target_slot') AS INT)
LEFT JOIN ejections ej ON ej.episode_id = mw.episode_id AND ej.meeting_ts = mw.meeting_ts AND ej.ejected_slot = tgt.slot
WHERE v.key = 'vote_cast' AND v.slot >= 0
""")

votes = con.execute("SELECT * FROM vote_facts").fetchdf()
crew_votes = votes[(votes.voter_role == "crew") & (votes.raw_target != "skip")].copy()

# --- per-(episode,seat) base for crew games: vote count + chat count per game (0 if none) ---
con.execute("""
CREATE TABLE crew_seat AS
SELECT episode_id, slot, policy_name, win FROM cep WHERE role = 'crew'
""")
con.execute("ALTER TABLE crew_seat ADD COLUMN votes_cast DOUBLE DEFAULT 0")
con.execute("""
UPDATE crew_seat SET votes_cast = COALESCE(t.v, 0) FROM (
    SELECT episode_id, slot, count(*)::double v FROM cevents
    WHERE key='vote_cast' AND slot>=0 AND role='crew' AND json_extract_string(value,'$.target') IS DISTINCT FROM 'skip'
    GROUP BY 1,2
) t WHERE crew_seat.episode_id = t.episode_id AND crew_seat.slot = t.slot
""")
con.execute("ALTER TABLE crew_seat ADD COLUMN chats DOUBLE DEFAULT 0")
con.execute("""
UPDATE crew_seat SET chats = COALESCE(t.v, 0) FROM (
    SELECT episode_id, slot, count(*)::double v FROM cevents
    WHERE key='chat' AND slot>=0 AND role='crew' GROUP BY 1,2
) t WHERE crew_seat.episode_id = t.episode_id AND crew_seat.slot = t.slot
""")
seat_df = con.execute("SELECT * FROM crew_seat").fetchdf()


def mms(series: pd.Series) -> dict:
    a = series.to_numpy(dtype=float)
    return {"mean": float(np.mean(a)), "median": float(np.median(a)), "std": float(np.std(a, ddof=1)) if len(a) > 1 else 0.0}


policies = sorted(seat_df.policy_name.unique())
out = {
    "warehouse": str(WH),
    "n_clean_games": n_clean,
    "n_trace_warning_episodes": int(n_skewed),
    "n_meetings": int(n_meetings),
    "n_ejections_resolved": int(n_ejections),
    "n_meetings_multi_ejection": int(dupe_meetings),
    "policies": {},
}

for p in policies:
    sg = seat_df[seat_df.policy_name == p]
    n_games = len(sg)
    row = {
        "crew_games": int(n_games),
        "votes_per_game": mms(sg.votes_cast),
        "chats_per_game": mms(sg.chats),
        "crew_win_rate": {"n": int(n_games), "pct": float(100 * sg.win.astype(bool).mean())},
    }

    cv = crew_votes[crew_votes.voter_policy == p]
    n_votes = len(cv)
    if n_votes > 0:
        n_correct = int((cv.target_role == "imposter").sum())
        row["vote_accuracy"] = {"n": n_votes, "pct": 100 * n_correct / n_votes}
    else:
        row["vote_accuracy"] = {"n": 0, "pct": None}

    voted_imp = cv[cv.target_role == "imposter"]
    if len(voted_imp) > 0:
        row["eject_when_voted_imposter"] = {
            "n": int(len(voted_imp)),
            "pct": 100 * float(voted_imp.target_ejected.astype(bool).mean()),
        }
    else:
        row["eject_when_voted_imposter"] = {"n": 0, "pct": None}

    voted_crew = cv[cv.target_role == "crew"]
    if len(voted_crew) > 0:
        row["eject_when_voted_crewmate"] = {
            "n": int(len(voted_crew)),
            "pct": 100 * float(voted_crew.target_ejected.astype(bool).mean()),
        }
    else:
        row["eject_when_voted_crewmate"] = {"n": 0, "pct": None}

    out["policies"][p] = row

Path(OUT).parent.mkdir(parents=True, exist_ok=True)
json.dump(out, open(OUT, "w"), indent=2)
print(f"wrote {OUT}")
for p, row in sorted(out["policies"].items(), key=lambda kv: -kv[1]["crew_win_rate"]["pct"]):
    print(f"{p:45s} crew_win={row['crew_win_rate']['pct']:5.1f}%  votes/g={row['votes_per_game']['mean']:.2f}"
          f"  chats/g={row['chats_per_game']['mean']:.2f}  vote_acc={row['vote_accuracy']['pct']}")
