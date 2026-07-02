"""Shared extraction for imposter-movement analysis over a per-tick event warehouse.

Everything here is **meeting-aware**: movement analysis only ever looks at Playing-phase
ticks (meetings freeze movement for ~1300 ticks and teleport players — including them
poisons every latency/distance number; see `best_practices.md`).

The unit of analysis is an **imposter-game** (one imposter slot in one episode) broken
into **ready windows**: spans where the imposter is alive, Playing, and kill-ready
(`kill_cooldown == 0`). A window ends at the imposter's kill, the next meeting (which
resets the cooldown — so a later kill does NOT convert this window), its death, or game
end. Within a window, ticks split into `vis` (a live crew in the imposter's rendered
view per `player_visible_interval`) and `novis` (searching blind).

Requires a warehouse built with ``--snapshot-every 1``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import duckdb
import numpy as np
import pandas as pd

PLAYING = "Playing"
PARK_WINDOW = 120  # ticks
PARK_RADIUS = 40  # px


# --------------------------------------------------------------------------- loading
def connect(wh: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(
        f"CREATE VIEW events AS SELECT * FROM read_parquet('{wh}/events/**/*.parquet', hive_partitioning=true)"
    )
    con.execute(f"CREATE VIEW episode_players AS SELECT * FROM read_parquet('{wh}/episode_players.parquet')")
    return con


def episode_players(con) -> pd.DataFrame:
    return con.execute(
        "SELECT episode_id, slot, role, policy_name, win, kills, tasks FROM episode_players"
    ).df()


def imposter_games(con, policy_like: str | None = None) -> pd.DataFrame:
    """One row per (episode, imposter slot), optionally filtered by policy substring."""
    df = episode_players(con)
    imp = df[df.role == "imposter"].copy()
    if policy_like:
        imp = imp[imp.policy_name.str.contains(policy_like, na=False)]
    return imp.reset_index(drop=True)


def map_geometry(con, episode_id: str) -> dict:
    row = con.execute(
        "SELECT value FROM events WHERE key='map_geometry' AND episode_id=? LIMIT 1", [episode_id]
    ).fetchone()
    return json.loads(row[0]) if row else {}


def player_states(con, episode_id: str) -> pd.DataFrame:
    """All per-tick player states for one episode: slot, ts, x, y, room, alive, cd, phase."""
    return con.execute(
        """
        SELECT slot, ts,
               json_extract(value,'$.x')::INT AS x,
               json_extract(value,'$.y')::INT AS y,
               json_extract_string(value,'$.room') AS room,
               json_extract_string(value,'$.alive')='true' AS alive,
               json_extract(value,'$.kill_cooldown')::INT AS cd,
               json_extract_string(value,'$.phase') AS phase
        FROM events WHERE key='player_state' AND episode_id=? AND slot>=0
        ORDER BY slot, ts
        """,
        [episode_id],
    ).df()


def kills(con, episode_id: str) -> pd.DataFrame:
    return con.execute(
        """
        SELECT slot AS killer, ts, json_extract(value,'$.victim_slot')::INT AS victim
        FROM events WHERE key='kill' AND episode_id=? ORDER BY ts
        """,
        [episode_id],
    ).df()


def crew_vis_intervals(con, episode_id: str, observer_slot: int) -> pd.DataFrame:
    """Rendered-view intervals in which the observer saw a (then-alive) crew player."""
    return con.execute(
        """
        SELECT ts AS t0, json_extract(value,'$.tick_end')::BIGINT AS t1,
               json_extract(value,'$.target_slot')::INT AS target
        FROM events WHERE key='player_visible_interval' AND episode_id=? AND slot=?
          AND json_extract_string(value,'$.target_role')='crew'
        ORDER BY ts
        """,
        [episode_id, observer_slot],
    ).df()


# ------------------------------------------------------------------- per-game frame
@dataclass
class ImposterGame:
    """The per-tick analysis frame for one imposter in one episode."""

    episode_id: str
    slot: int
    policy_name: str
    imp: pd.DataFrame  # per-tick imposter frame (see build_imposter_game)
    states: pd.DataFrame  # full episode player_states
    kills: pd.DataFrame
    game_map: dict = field(default_factory=dict)
    windows: pd.DataFrame | None = None  # ready windows (see ready_windows)


def build_imposter_game(con, episode_id: str, slot: int, policy_name: str, with_map: bool = False) -> ImposterGame:
    """Assemble the per-tick frame for one imposter-game.

    The `imp` frame has one row per tick the imposter has a state sample, with:
    x, y, room, alive, cd, phase, playing, ready, crew_vis, near_crew (px to nearest
    live crew), near_crew_slot, crew_room_ct (live crew sharing the imposter's room),
    speed (px/tick, NaN across phase breaks).
    """
    states = player_states(con, episode_id)
    kdf = kills(con, episode_id)
    imp = states[states.slot == slot].drop(columns=["slot"]).reset_index(drop=True)

    # who is crew (never the imposter team)
    roles = episode_players(con)
    ep_roles = roles[roles.episode_id == episode_id].set_index("slot")["role"]
    crew_slots = [s for s, r in ep_roles.items() if r == "crew"]

    crew = states[states.slot.isin(crew_slots) & states.alive].copy()

    # nearest live crew per tick (vectorized: merge on ts)
    merged = imp[["ts", "x", "y"]].merge(crew[["slot", "ts", "x", "y", "room"]], on="ts", suffixes=("", "_c"))
    merged["d"] = np.hypot(merged.x - merged.x_c, merged.y - merged.y_c)
    near = merged.loc[merged.groupby("ts")["d"].idxmin(), ["ts", "d", "slot", "room"]]
    near.columns = ["ts", "near_crew", "near_crew_slot", "near_crew_room"]
    imp = imp.merge(near, on="ts", how="left")

    # live crew sharing the imposter's room
    room_ct = (
        imp[["ts", "room"]]
        .merge(crew[["ts", "room"]], on=["ts", "room"])
        .groupby("ts")
        .size()
        .rename("crew_room_ct")
    )
    imp = imp.merge(room_ct, on="ts", how="left")
    imp["crew_room_ct"] = imp.crew_room_ct.fillna(0).astype(int)

    imp["playing"] = imp.phase == PLAYING
    imp["ready"] = imp.playing & imp.alive & (imp.cd == 0)

    # rendered-view crew visibility flag
    vis = crew_vis_intervals(con, episode_id, slot)
    flag = np.zeros(len(imp), dtype=bool)
    ts_index = pd.Series(np.arange(len(imp)), index=imp.ts)
    for t0, t1 in zip(vis.t0, vis.t1):
        lo = ts_index.index.searchsorted(t0, "left")
        hi = ts_index.index.searchsorted(t1, "right")
        flag[lo:hi] = True
    imp["crew_vis"] = flag

    # speed: px/tick between consecutive Playing samples (NaN across gaps/phase breaks)
    dx = imp.x.diff()
    dy = imp.y.diff()
    dt = imp.ts.diff()
    speed = np.hypot(dx, dy) / dt
    contiguous = (dt == 1) & imp.playing & imp.playing.shift(1, fill_value=False)
    imp["speed"] = np.where(contiguous, speed, np.nan)
    # closing rate on the nearest crew: positive = the gap shrank this tick
    imp["closing"] = np.where(contiguous, -imp.near_crew.diff(), np.nan)

    # parked: net displacement over the trailing PARK_WINDOW ticks under PARK_RADIUS px
    # (the recon-stall signature: standing on a stale last-seen point; distinct from
    # per-tick "stationary", which misses slow jitter around a point)
    win = PARK_WINDOW
    x_then = imp.x.shift(win)
    y_then = imp.y.shift(win)
    ts_then = imp.ts.shift(win)
    net = np.hypot(imp.x - x_then, imp.y - y_then)
    imp["parked"] = (net < PARK_RADIUS) & ((imp.ts - ts_then) == win) & imp.playing

    game_map = map_geometry(con, episode_id) if with_map else {}
    return ImposterGame(episode_id, slot, policy_name, imp, states, kdf, game_map)


def ready_windows(game: ImposterGame) -> pd.DataFrame:
    """Meeting-aware ready windows for the imposter-game.

    One row per maximal run of consecutive `ready` ticks, with the window outcome:
    'kill' (this imposter killed inside the window), 'meeting' (phase break ended it),
    'death', or 'game_end'. Columns: t0, t1, len, outcome, kill_tick, ticks_to_kill,
    novis_ticks, vis_ticks, med_near_novis, first_vis_tick.
    """
    imp = game.imp
    r = imp.ready.to_numpy()
    ts = imp.ts.to_numpy()
    # maximal runs of ready ticks over *consecutive samples* (a phase break inserts
    # non-ready samples, so runs never span a meeting)
    edges = np.flatnonzero(np.diff(np.concatenate(([0], r.astype(int), [0]))))
    starts, ends = edges[::2], edges[1::2] - 1
    my_kills = game.kills[game.kills.killer == game.slot].ts.to_list()
    rows = []
    for a, b in zip(starts, ends):
        t0, t1 = int(ts[a]), int(ts[b])
        seg = imp.iloc[a : b + 1]
        kill_tick = next((k for k in my_kills if t0 <= k <= t1 + 1), None)
        if kill_tick is not None:
            outcome = "kill"
        else:
            after = imp.iloc[b + 1 :]
            if len(after) == 0:
                outcome = "game_end"
            elif not after.iloc[0].alive:
                outcome = "death"
            elif after.iloc[0].phase != PLAYING:
                outcome = "meeting"
            else:
                outcome = "cooldown_restart"  # e.g. a partner kill reset our cd
        novis = seg[~seg.crew_vis]
        vis_first = seg[seg.crew_vis].ts.min() if seg.crew_vis.any() else None
        parked_ticks = int(seg.parked.sum())
        near_at_ready = float(seg.near_crew.iloc[0]) if len(seg) and not pd.isna(seg.near_crew.iloc[0]) else None
        rows.append(
            dict(
                t0=t0,
                t1=t1,
                len=b - a + 1,
                outcome=outcome,
                kill_tick=kill_tick,
                ticks_to_kill=(kill_tick - t0) if kill_tick is not None else None,
                novis_ticks=len(novis),
                vis_ticks=int(seg.crew_vis.sum()),
                med_near_novis=float(novis.near_crew.median()) if len(novis) else None,
                first_vis_tick=vis_first,
                parked_ticks=parked_ticks,
                near_at_ready=near_at_ready,
            )
        )
    win = pd.DataFrame(
        rows,
        columns=[
            "t0", "t1", "len", "outcome", "kill_tick", "ticks_to_kill",
            "novis_ticks", "vis_ticks", "med_near_novis", "first_vis_tick", "parked_ticks", "near_at_ready",
        ],
    )
    game.windows = win
    return win


def room_transitions(con, episode_id: str, slot: int) -> list[str]:
    """Ordered room-entry sequence for one player (from entered_room events)."""
    rows = con.execute(
        """
        SELECT json_extract_string(value,'$.room') FROM events
        WHERE key='entered_room' AND episode_id=? AND slot=? ORDER BY ts
        """,
        [episode_id, slot],
    ).fetchall()
    return [r[0] for r in rows]
