#!/usr/bin/env python
"""Stage 1 — build the per-chat dataset for the chat-persuasion study.

Merges the vote-target-carrying event warehouses into one deduped corpus, segments
every meeting, and emits ONE ROW PER natural-language chat message (both roles) with:

  - SYMBOLIC features (computed here, free): speaking order, latency after the meeting
    opened, message length, is-question, self-reference, names-a-color, first-accusation
    in the meeting, speaker role, alive-count at the meeting.
  - Identity: episode, meeting, speaker slot/color/role/policy.
  - The raw text (LLM-semantic features are added in stage 2, label_chats.py).
  - TWO LABELS from real votes:
      * suspicion_drawn   = votes cast AGAINST the speaker AFTER this message,
                            minus votes against them before it (within the meeting).
      * persuasion        = votes cast against the speaker's NAMED target after the
                            message minus before (0 when the message named no target;
                            the target is filled from the LLM pass in stage 2, so this
                            column is computed there — stage 1 emits the per-target
                            vote timeline needed to compute it).

Vote targets live in ``vote_cast.value.target_slot`` / ``target_label`` (NOT ``.target``,
which is only set for skips). Chats + votes interleave by ``ts``; a meeting is the
``MeetingCall -> VoteResult`` window (votes/chat happen in its ``Voting`` sub-window).

Output: ``chat_study/dataset/chats.parquet`` (+ ``votes.parquet`` for the target timeline).
Idempotent: re-run overwrites.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import duckdb
import pandas as pd

# The three warehouses that carry resolved vote targets (built with a new-enough
# extractor). Disjoint episodes: 727 + 100 + 24 = 851. The other ~34 warehouses predate
# vote_cast target extraction — including them adds episodes with no usable label.
DEFAULT_WAREHOUSES = ["/tmp/v96_rank_wh", "/tmp/crew_wh", "/tmp/v101_wh"]

COLORS = {
    "red", "blue", "green", "yellow", "orange", "pink",
    "purple", "cyan", "white", "black", "lime", "brown",
}
LABEL_COLOR_RE = re.compile(r"^([a-z]+)\(")


def _color_of_label(label: str | None) -> str | None:
    """`red(Name)` -> `red`."""
    if not label:
        return None
    m = LABEL_COLOR_RE.match(label)
    return m.group(1) if m else None


def _is_real_chat(text: str | None) -> bool:
    """Drop Honor Society handshake lines and crewborg's non-chat placeholder."""
    if not text:
        return False
    if text.startswith("HS1 "):
        return False
    if "no read" in text.lower():
        return False
    return True


def has_vote_targets(warehouse: str) -> bool:
    """True if this warehouse carries resolved vote targets (built with a new-enough
    extractor). Warehouses without them add episodes with no usable persuasion label, so we
    skip them. Cheap check: one vote_cast row with a non-null target_slot."""
    if not Path(warehouse, "events").is_dir():
        return False
    try:
        con = duckdb.connect()
        n = con.execute(
            f"SELECT COUNT(*) FROM read_parquet(['{warehouse}/events/**/*.parquet'], "
            "hive_partitioning=true, union_by_name=true) "
            "WHERE key='vote_cast' AND json_extract_string(value,'$.target_slot') IS NOT NULL"
        ).fetchone()[0]
        con.close()
        return n > 0
    except Exception:
        return False


def resolve_warehouses(warehouses: list[str] | None, glob_dir: str | None) -> list[str]:
    """Resolve the warehouse list: explicit --warehouses, and/or every ``*_wh`` under
    --glob-dir. Keeps only those that actually carry vote targets (warns on the rest), so
    new data can be dropped in and picked up automatically."""
    import glob as _glob

    candidates: list[str] = list(warehouses or [])
    if glob_dir:
        candidates += sorted(
            d for d in _glob.glob(f"{glob_dir.rstrip('/')}/*_wh") + _glob.glob(f"{glob_dir.rstrip('/')}/*wh")
            if Path(d, "events").is_dir()
        )
    candidates = list(dict.fromkeys(candidates))  # dedup, preserve order
    good, skipped = [], []
    for w in candidates:
        (good if has_vote_targets(w) else skipped).append(w)
    if skipped:
        print(f"skipping {len(skipped)} warehouse(s) without vote targets: "
              + ", ".join(Path(s).name for s in skipped))
    if not good:
        raise SystemExit("no warehouses with vote targets found")
    print(f"using {len(good)} warehouse(s): " + ", ".join(Path(g).name for g in good))
    return good


def load_events(warehouses: list[str]) -> duckdb.DuckDBPyConnection:
    """Union the warehouses' event + player tables into one connection, deduped by
    (episode_id, ts, slot, key, value) so overlapping warehouses don't double-count."""
    con = duckdb.connect()
    event_globs = [f"'{w}/events/**/*.parquet'" for w in warehouses if Path(w, "events").is_dir()]
    player_globs = [f"'{w}/episode_players.parquet'" for w in warehouses if Path(w, "episode_players.parquet").is_file()]
    if not event_globs:
        raise SystemExit("no warehouses with events found")
    # Only the four keys the study uses — restricting BEFORE the DISTINCT is what keeps this
    # tractable (the full event union is millions of rows incl. per-tick player_state; the
    # partitioned parquet lets DuckDB prune to just these key= partitions).
    keys = "('chat','vote_cast','player_joined','phase')"
    con.execute(
        "CREATE TABLE ev AS SELECT DISTINCT episode_id, ts, slot, key, value FROM ("
        + " UNION ALL ".join(
            f"SELECT episode_id, ts, slot, key, value "
            f"FROM read_parquet([{g}], hive_partitioning=true, union_by_name=true) WHERE key IN {keys}"
            for g in event_globs
        )
        + ")"
    )
    con.execute(
        "CREATE TABLE players AS SELECT DISTINCT * FROM read_parquet(["
        + ",".join(player_globs)
        + "], union_by_name=true)"
    )
    return con


def color_maps(con: duckdb.DuckDBPyConnection) -> dict[tuple[str, int], str]:
    """(episode_id, slot) -> color, from player_joined labels."""
    rows = con.execute(
        "SELECT episode_id, slot, json_extract_string(value,'$.label') "
        "FROM ev WHERE key='player_joined' AND slot>=0"
    ).fetchall()
    out: dict[tuple[str, int], str] = {}
    for eid, slot, label in rows:
        c = _color_of_label(label)
        if c:
            out[(eid, slot)] = c
    return out


def role_maps(con: duckdb.DuckDBPyConnection) -> dict[tuple[str, int], tuple[str, str]]:
    """(episode_id, slot) -> (role, policy_name)."""
    rows = con.execute("SELECT episode_id, slot, role, policy_name FROM players").fetchall()
    return {(eid, slot): (role, pol) for eid, slot, role, pol in rows}


def meeting_windows(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """One row per meeting: (episode_id, meeting_idx, call_ts, voting_ts, end_ts)."""
    ph = con.execute(
        "SELECT episode_id, ts, json_extract_string(value,'$.phase') AS phase "
        "FROM ev WHERE key='phase' ORDER BY episode_id, ts"
    ).df()
    rows = []
    for eid, grp in ph.groupby("episode_id"):
        grp = grp.sort_values("ts").reset_index(drop=True)
        idx = 0
        call_ts = voting_ts = None
        for _, r in grp.iterrows():
            if r["phase"] == "MeetingCall":
                call_ts, voting_ts = r["ts"], None
            elif r["phase"] == "Voting":
                voting_ts = r["ts"]
            elif r["phase"] in ("VoteResult", "Playing", "GameOver") and call_ts is not None:
                rows.append((eid, idx, call_ts, voting_ts, r["ts"]))
                idx += 1
                call_ts = voting_ts = None
    return pd.DataFrame(rows, columns=["episode_id", "meeting_idx", "call_ts", "voting_ts", "end_ts"])


def build(warehouses: list[str], out_dir: Path) -> None:
    con = load_events(warehouses)
    colors = color_maps(con)
    roles = role_maps(con)
    meetings = meeting_windows(con)
    print(f"episodes={con.execute('SELECT COUNT(DISTINCT episode_id) FROM ev').fetchone()[0]} "
          f"meetings={len(meetings)}")

    # All chats + votes, ordered. Votes carry the resolved target.
    chats = con.execute(
        "SELECT episode_id, ts, slot, json_extract_string(value,'$.text') AS text, "
        "json_extract_string(value,'$.actor_role') AS role "
        "FROM ev WHERE key='chat' AND slot>=0 ORDER BY episode_id, ts"
    ).df()
    votes = con.execute(
        "SELECT episode_id, ts, slot AS voter_slot, "
        "TRY_CAST(json_extract_string(value,'$.target_slot') AS INT) AS target_slot, "
        "CASE WHEN json_extract_string(value,'$.target')='skip' THEN 1 ELSE 0 END AS is_skip "
        "FROM ev WHERE key='vote_cast' AND slot>=0 ORDER BY episode_id, ts"
    ).df()

    # Assign each chat/vote to its meeting by ts window [call_ts, end_ts). Precompute
    # sorted (call_ts, end_ts, meeting_idx, voting_ts) tuples per episode and bisect —
    # a per-row DataFrame filter here is O(n²) and hangs on 13k chats × 851 episodes.
    import bisect

    mtree: dict[str, tuple[list[int], list[tuple]]] = {}
    for eid, g in meetings.groupby("episode_id"):
        g = g.sort_values("call_ts")
        starts = g["call_ts"].astype(int).tolist()
        spans = [
            (int(r.call_ts), int(r.end_ts), int(r.meeting_idx), (None if pd.isna(r.voting_ts) else int(r.voting_ts)))
            for r in g.itertuples()
        ]
        mtree[eid] = (starts, spans)

    def assign_meeting(eid: str, ts: int):
        entry = mtree.get(eid)
        if entry is None:
            return None
        starts, spans = entry
        i = bisect.bisect_right(starts, ts) - 1  # latest meeting whose call_ts <= ts
        if i < 0:
            return None
        call_ts, end_ts, midx, voting_ts = spans[i]
        if ts < end_ts:
            return midx, call_ts, voting_ts
        return None

    # Resolve vote target colors + roles; keep the vote timeline for label computation.
    vote_rows = []
    for _, v in votes.iterrows():
        m = assign_meeting(v["episode_id"], v["ts"])
        if m is None:
            continue
        midx, call_ts, _ = m
        tgt_color = colors.get((v["episode_id"], int(v["target_slot"]))) if not v["is_skip"] and pd.notna(v["target_slot"]) else None
        tgt_role = roles.get((v["episode_id"], int(v["target_slot"])), (None, None))[0] if not v["is_skip"] and pd.notna(v["target_slot"]) else None
        vote_rows.append(dict(
            episode_id=v["episode_id"], meeting_idx=midx, ts=int(v["ts"]),
            voter_slot=int(v["voter_slot"]), target_slot=(None if v["is_skip"] or pd.isna(v["target_slot"]) else int(v["target_slot"])),
            target_color=tgt_color, target_role=tgt_role, is_skip=int(v["is_skip"]),
        ))
    votes_df = pd.DataFrame(vote_rows)

    # Pre-group votes-against-a-color by (episode, meeting, target_color) into sorted ts
    # lists, so the per-chat suspicion label is a bisect, not a DataFrame filter.
    from collections import defaultdict

    votes_by_color: dict[tuple, list[int]] = defaultdict(list)
    if len(votes_df):
        for r in votes_df.itertuples():
            if r.target_color is not None:
                votes_by_color[(r.episode_id, r.meeting_idx, r.target_color)].append(int(r.ts))
        for k in votes_by_color:
            votes_by_color[k].sort()

    # Per-chat symbolic features + speaker suspicion label (persuasion label needs the
    # LLM-derived named target, so it's computed in stage 3 from votes.parquet).
    chat_rows = []
    for eid, cg in chats.groupby("episode_id"):
        cg = cg[cg["text"].map(_is_real_chat)].sort_values("ts").reset_index(drop=True)
        ts_list = cg["ts"].astype(int).tolist()
        for pos, ch in enumerate(cg.itertuples()):
            m = assign_meeting(eid, ch.ts)
            if m is None:
                continue
            midx, call_ts, voting_ts = m
            slot = int(ch.slot)
            color = colors.get((eid, slot))
            role, policy = roles.get((eid, slot), (ch.role, None))
            text = ch.text
            tl = text.lower()

            # speaking order within the meeting: count real chats in [call_ts, ts) via bisect
            lo = bisect.bisect_left(ts_list, call_ts)
            speak_order = pos - lo + 1
            first_speaker = speak_order == 1
            # suspicion label: votes against THIS speaker after vs before the message
            against = votes_by_color.get((eid, midx, color)) if color is not None else None
            if against:
                cut = bisect.bisect_right(against, ch.ts)
                before, after = cut, len(against) - cut
            else:
                before = after = 0

            chat_rows.append(dict(
                episode_id=eid, meeting_idx=midx, ts=int(ch.ts), slot=slot,
                color=color, role=role, policy=policy, text=text,
                # symbolic features
                f_speak_order=speak_order,
                f_first_speaker=int(first_speaker),
                f_latency_ticks=int(ch.ts - (voting_ts or call_ts)),
                f_msg_len=len(text),
                f_word_count=len(text.split()),
                f_is_question=int("?" in text),
                f_names_color=int(any(c in tl for c in COLORS)),
                f_self_reference=int(bool(re.search(r"\b(not me|i was|i did|my |me\b|wasn'?t me)\b", tl))),
                f_says_vote=int("vote" in tl),
                f_says_sus=int("sus" in tl),
                # label parts (persuasion filled in stage 3)
                lbl_votes_against_speaker_before=before,
                lbl_votes_against_speaker_after=after,
            ))

    out_dir.mkdir(parents=True, exist_ok=True)
    chats_out = pd.DataFrame(chat_rows)
    chats_out.to_parquet(out_dir / "chats.parquet")
    votes_df.to_parquet(out_dir / "votes.parquet")
    print(f"wrote {len(chats_out)} chat rows -> {out_dir/'chats.parquet'}")
    print(f"wrote {len(votes_df)} vote rows -> {out_dir/'votes.parquet'}")
    print("role split:", chats_out.role.value_counts().to_dict())


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Merge any vote-target event warehouses into the chat-persuasion dataset. "
        "Add more data later by passing new --warehouses or dropping them under --glob-dir."
    )
    ap.add_argument("--warehouses", nargs="+", default=None,
                    help=f"explicit warehouse dirs (default: {DEFAULT_WAREHOUSES})")
    ap.add_argument("--glob-dir", default=None,
                    help="also include every *_wh under this dir (e.g. /tmp) that carries vote targets")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "dataset")
    args = ap.parse_args()
    # default to the known-good set only when neither selector is given
    explicit = args.warehouses if (args.warehouses or args.glob_dir) else DEFAULT_WAREHOUSES
    warehouses = resolve_warehouses(explicit, args.glob_dir)
    build(warehouses, args.out)


if __name__ == "__main__":
    main()
