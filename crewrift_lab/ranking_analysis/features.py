#!/usr/bin/env python3
"""Per-(episode,seat) feature extraction from the event warehouse, then
differential analysis: crewborg vs the top-3 policies per role.

Unit of analysis: one row per (episode, seat) that the policy played in a given
role, restricted to the 728 CLEAN games (all 8 connected). Features are computed
per game so each policy gets a DISTRIBUTION we can test.
"""
from __future__ import annotations
import json, math
import os
from pathlib import Path
import duckdb

# The ONE script that needs the full 1.4 GB event warehouse. Point RANK_WH at it
# (rebuild via the README, or transfer the warehouse dir). Outputs the distilled
# per-seat feature table the rest of the pipeline reads.
HERE = Path(__file__).resolve().parent
WH = os.environ.get("RANK_WH", "/tmp/v96_rank_wh")
CLEAN = os.environ.get("RANK_CLEAN_EIDS", str(HERE / "data" / "clean_eids.txt"))
OUT = os.environ.get("RANK_FEATURES_OUT", str(HERE / "data" / "features.json"))

con = duckdb.connect()
con.execute(f"CREATE VIEW events AS SELECT * FROM read_parquet('{WH}/events/**/*.parquet', hive_partitioning=true)")
con.execute(f"CREATE VIEW ep AS SELECT * FROM read_parquet('{WH}/episode_players.parquet')")
clean = [l.strip() for l in open(CLEAN) if l.strip()]
con.execute("CREATE TABLE clean(eid VARCHAR)")
con.executemany("INSERT INTO clean VALUES (?)", [(c,) for c in clean])
con.execute("CREATE VIEW cep AS SELECT * FROM ep WHERE episode_id IN (SELECT eid FROM clean)")

# --- base: one row per (episode, slot) seat in clean games, with outcome ---
con.execute("""
CREATE TABLE seat AS
SELECT episode_id, slot, policy_name, role, win, tasks, kills
FROM cep WHERE slot >= 0
""")

def add(colsql, name):
    """LEFT JOIN a per-(episode,slot) aggregate onto seat as column `name`."""
    con.execute(f"ALTER TABLE seat ADD COLUMN {name} DOUBLE DEFAULT 0")
    con.execute(f"""
    UPDATE seat SET {name} = COALESCE(t.v, 0) FROM (
        {colsql}
    ) t WHERE seat.episode_id = t.episode_id AND seat.slot = t.slot
    """)

# chat count (voting-phase messages spoken)
add("SELECT episode_id, slot, count(*)::double v FROM events WHERE key='chat' AND slot>=0 GROUP BY 1,2", "chats")
# distinct rooms visited
add("SELECT episode_id, slot, count(DISTINCT json_extract_string(value,'$.room'))::double v FROM events WHERE key='entered_room' AND slot>=0 GROUP BY 1,2", "rooms_visited")
# votes cast on a player (non-skip)
add("SELECT episode_id, slot, count(*)::double v FROM events WHERE key='vote_cast' AND slot>=0 AND json_extract_string(value,'$.target') IS DISTINCT FROM 'skip' GROUP BY 1,2", "votes_player")
# votes skipped
add("SELECT episode_id, slot, count(*)::double v FROM events WHERE key='vote_cast' AND slot>=0 AND json_extract_string(value,'$.target')='skip' GROUP BY 1,2", "votes_skip")
# meetings called (body reports + buttons)
add("SELECT episode_id, slot, count(*)::double v FROM events WHERE key IN ('vote_called_body','vote_called_button') AND slot>=0 GROUP BY 1,2", "meetings_called")
# tasks completed while dead (ghost tasking)
add("SELECT episode_id, slot, count(*)::double v FROM events WHERE key='completed_task' AND slot>=0 AND json_extract(value,'$.while_dead')::boolean GROUP BY 1,2", "tasks_while_dead")
# following intervals initiated (tailing someone)
add("SELECT episode_id, slot, count(*)::double v FROM events WHERE key='following_interval' AND slot>=0 GROUP BY 1,2", "follows")
# chase intervals (closing distance — aggressive pursuit)
add("SELECT episode_id, slot, count(*)::double v FROM events WHERE key='chase_interval' AND slot>=0 GROUP BY 1,2", "chases")
# times this seat was a follow TARGET (got trailed)
add("SELECT episode_id, json_extract(value,'$.target')::int slot, count(*)::double v FROM events WHERE key='following_interval' AND slot>=0 GROUP BY 1,2", "got_trailed")
# isolation intervals involving this seat (alone with one other) — approximate via proximity player_a/player_b
add("""SELECT episode_id, slot, count(*)::double v FROM (
        SELECT episode_id, json_extract(value,'$.player_a')::int slot FROM events WHERE key='isolation_interval'
        UNION ALL SELECT episode_id, json_extract(value,'$.player_b')::int slot FROM events WHERE key='isolation_interval'
     ) GROUP BY 1,2""", "isolations")
# got killed (was a kill victim)
add("SELECT episode_id, json_extract(value,'$.victim_slot')::int slot, 1.0 v FROM events WHERE key='kill' GROUP BY 1,2", "got_killed")
# first-kill tick (imposter) — min ts of a kill by this seat
add("SELECT episode_id, slot, min(ts)::double v FROM events WHERE key='kill' AND slot>=0 GROUP BY 1,2", "first_kill_tick")
# suss chats: total, and deflection suss (accusing a non-teammate)
add("SELECT episode_id, slot, count(*)::double v FROM events WHERE key='chat_suss' AND slot>=0 AND json_extract(value,'$.is_suss')::boolean GROUP BY 1,2", "suss_chats")

con.execute("UPDATE seat SET first_kill_tick = NULL WHERE first_kill_tick = 0")

# --- witnesses per kill: for each kill, count DISTINCT living players who had the
# killer OR victim in view within a window, or who were near. Use player_visible_interval:
# other players who saw the killer at the kill tick. Approx: count distinct observers
# whose visible-interval of the killer spans the kill tick.
con.execute("""
CREATE TABLE kills AS
SELECT k.episode_id, k.slot AS killer_slot, k.ts AS kill_tick,
       json_extract(k.value,'$.victim_slot')::int AS victim_slot
FROM events k WHERE k.key='kill' AND k.slot>=0 AND k.episode_id IN (SELECT eid FROM clean)
""")
con.execute("""
CREATE TABLE kill_witness AS
SELECT ki.episode_id, ki.killer_slot, ki.kill_tick,
   count(DISTINCT v.slot) AS witnesses
FROM kills ki
LEFT JOIN events v ON v.episode_id=ki.episode_id AND v.key='player_visible_interval' AND v.slot>=0
   AND v.slot <> ki.killer_slot AND v.slot <> ki.victim_slot
   AND json_extract(v.value,'$.target_slot')::int = ki.killer_slot
   AND json_extract(v.value,'$.tick_start')::bigint <= ki.kill_tick
   AND json_extract(v.value,'$.tick_end')::bigint >= ki.kill_tick
GROUP BY 1,2,3
""")
# per-(episode,killer) mean witnesses-per-kill
add("SELECT episode_id, killer_slot AS slot, avg(witnesses)::double v FROM kill_witness GROUP BY 1,2", "witnesses_per_kill")

# --- kill room + death room (categorical, handled separately below) ---
# room where a kill happened = killer's room at kill tick (nearest player_state)
# For distributional room analysis we export raw kill/death room tallies per policy.

# --- ghost move latency: ticks from death to first movement while dead, EXCLUDING
# meeting phases. Approx: first player_state after death with vel != 0 AND alive=false,
# during a Playing phase. Compute per victim seat.
con.execute("""
CREATE TABLE deaths AS
SELECT episode_id, json_extract(value,'$.victim_slot')::int AS slot, ts AS death_tick
FROM events WHERE key='kill' AND episode_id IN (SELECT eid FROM clean)
""")
con.execute("""
CREATE TABLE ghost_move AS
SELECT d.episode_id, d.slot,
   min(s.ts) - min(d.death_tick) AS latency
FROM deaths d
JOIN events s ON s.episode_id=d.episode_id AND s.slot=d.slot AND s.key='player_state'
   AND s.ts > d.death_tick
   AND json_extract(s.value,'$.alive')::boolean = false
   AND abs(json_extract(s.value,'$.vel_x')::double) + abs(json_extract(s.value,'$.vel_y')::double) > 0
GROUP BY d.episode_id, d.slot
""")
add("SELECT episode_id, slot, avg(latency)::double v FROM ghost_move GROUP BY 1,2", "ghost_move_latency")
con.execute("UPDATE seat SET ghost_move_latency = NULL WHERE ghost_move_latency = 0 AND got_killed = 0")

# derived booleans / rates
con.execute("ALTER TABLE seat ADD COLUMN chatted DOUBLE")
con.execute("UPDATE seat SET chatted = CASE WHEN chats>0 THEN 1 ELSE 0 END")
con.execute("ALTER TABLE seat ADD COLUMN voted DOUBLE")
con.execute("UPDATE seat SET voted = CASE WHEN votes_player>0 THEN 1 ELSE 0 END")

# dump to pandas/json for the stats step
rows = con.execute("SELECT * FROM seat").fetchdf()
rows.to_json(OUT, orient="records")
print("seats:", len(rows), "| columns:", list(rows.columns))
print(con.execute("SELECT role, count(*) FROM seat GROUP BY 1").fetchall())
