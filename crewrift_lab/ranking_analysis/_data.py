"""Shared data access for the ranking/differential analysis.

Everything the RANKING needs (per-seat policy, role, win/tasks/kills for the 728
clean games) comes from the committed ``data/episode_players.parquet`` (a small
warehouse dimension) filtered by ``data/clean_eids.txt`` — so the ranking, the
Bradley-Terry model and the report regenerate on any checkout WITHOUT the 1.4 GB
event warehouse or the 8.5 GB raw episodes. Only ``features.py`` (new behavioural
feature extraction) needs the full warehouse (env ``RANK_WH``).
"""
from __future__ import annotations
import os
from pathlib import Path
import duckdb

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("RANK_DATA", HERE / "data"))
WAREHOUSE = Path(os.environ.get("RANK_WH", "/tmp/v96_rank_wh"))
EPISODE_PLAYERS = Path(os.environ.get("RANK_EPISODE_PLAYERS", DATA / "episode_players.parquet"))
CLEAN_EIDS = Path(os.environ.get("RANK_CLEAN_EIDS", DATA / "clean_eids.txt"))


def clean_ids() -> list[str]:
    return [l.strip() for l in open(CLEAN_EIDS) if l.strip()]


def seats_df():
    """One row per (episode, seat) for the CLEAN games, with outcome + identity."""
    con = duckdb.connect()
    con.execute(f"CREATE VIEW ep AS SELECT * FROM read_parquet('{EPISODE_PLAYERS.as_posix()}')")
    ids = clean_ids()
    con.execute("CREATE TABLE clean(eid VARCHAR)")
    con.executemany("INSERT INTO clean VALUES (?)", [(c,) for c in ids])
    return con.execute("""
        SELECT episode_id, slot, policy_name, role, win, tasks, kills
        FROM ep WHERE slot >= 0 AND policy_name IS NOT NULL
              AND episode_id IN (SELECT eid FROM clean)
    """).fetchdf()


def clean_games():
    """List of (crew_policy_indices, imp_policy_indices, crew_won) + the policy list,
    for the team Bradley-Terry model. Reconstructed from the seat table."""
    df = seats_df()
    policies = sorted(df.policy_name.unique())
    pidx = {p: i for i, p in enumerate(policies)}
    games = []
    for eid, g in df.groupby("episode_id"):
        crew = [pidx[p] for p in g[g.role == "crew"].policy_name]
        imp = [pidx[p] for p in g[g.role == "imposter"].policy_name]
        if len(crew) != 6 or len(imp) != 2:
            continue  # not a well-formed 8-player/2-imposter game
        crew_won = int(bool(g[g.role == "crew"].win.iloc[0]))
        games.append((tuple(crew), tuple(imp), crew_won))
    return games, policies
