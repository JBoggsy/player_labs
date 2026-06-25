"""Head-to-head imposter behavior: crewborg (v42, us) vs crewborg-aaln (v17, Aaron).

Reads a crewrift-event-warehouse and compares the two policies AS IMPOSTER on the
behavioral dimensions James asked about: near-crew, following, same-room-with-crew,
room presence, search/movement, kill-cooldown→kill latency, and ejection rate.
Usage: uv run --with duckdb python /tmp/aaron_compare.py <warehouse_dir>
"""
import duckdb, sys, json

WH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/v42_warehouse"
US, AARON = "crewborg", "crewborg-aaln"
con = duckdb.connect()
def ev(key): return f"read_parquet('{WH}/events/key={key}/*.parquet')"
EP = f"read_parquet('{WH}/episode_players.parquet')"

# imposter (episode, slot) for each policy + the games they imposter in
imp = con.execute(f"""
  SELECT policy_name, episode_id, slot, win,
         CASE WHEN score < 0 THEN 1 ELSE 0 END AS ops
  FROM {EP} WHERE role='imposter' AND policy_name IN ('{US}','{AARON}')
""").df()
imp = imp[imp.ops == 0]
games = imp.groupby("policy_name").agg(g=("episode_id","nunique")).to_dict()["g"]
con.register("imp", imp)

def per_game(key, where, val_expr="json_extract(value,'$.duration_ticks')::DOUBLE"):
    """Sum val_expr per imposter-game, return mean & count per policy."""
    return con.execute(f"""
      WITH e AS (
        SELECT i.policy_name, i.episode_id, {val_expr} AS v
        FROM {ev(key)} t JOIN imp i
          ON t.episode_id=i.episode_id AND {where}
        WHERE json_extract_string(t.value,'$.phase')='Playing'
      )
      SELECT policy_name, COUNT(*) AS n_intervals, SUM(v) AS total_ticks
      FROM e GROUP BY 1
    """).df()

print(f"warehouse: {WH}")
print(f"imposter games (ops-filtered): us(crewborg)={games.get(US)}  aaron(crewborg-aaln)={games.get(AARON)}\n")

# 1. NEAR CREW (proximity involving the imposter + a crew teammate)
prox = con.execute(f"""
  WITH p AS (
    SELECT t.episode_id, t.value,
           json_extract(t.value,'$.player_a')::INT a, json_extract(t.value,'$.player_b')::INT b,
           json_extract(t.value,'$.duration_ticks')::DOUBLE dur
    FROM {ev('proximity_interval')} t
    WHERE json_extract_string(t.value,'$.phase')='Playing'
  )
  SELECT i.policy_name, COUNT(*) n, SUM(p.dur) ticks
  FROM p JOIN imp i ON p.episode_id=i.episode_id AND (p.a=i.slot OR p.b=i.slot)
  -- the OTHER endpoint must be crew in this episode
  JOIN {EP} o ON o.episode_id=p.episode_id
       AND o.slot = CASE WHEN p.a=i.slot THEN p.b ELSE p.a END AND o.role='crew'
  GROUP BY 1
""").df()
print("=== NEAR CREW (proximity intervals, imposter↔a crew, Playing) ===")
for _,r in prox.iterrows():
    g=games[r.policy_name]; print(f"  {r.policy_name:14} {r.n/g:6.1f} intervals/game  {r.ticks/g:7.0f} near-crew ticks/game")

# 2. ISOLATION (imposter alone with one crew — kill setup)
iso = con.execute(f"""
  WITH p AS (
    SELECT t.episode_id,
           json_extract(t.value,'$.player_a')::INT a, json_extract(t.value,'$.player_b')::INT b,
           json_extract(t.value,'$.duration_ticks')::DOUBLE dur
    FROM {ev('isolation_interval')} t
    WHERE json_extract_string(t.value,'$.phase')='Playing'
  )
  SELECT i.policy_name, COUNT(*) n, SUM(p.dur) ticks
  FROM p JOIN imp i ON p.episode_id=i.episode_id AND (p.a=i.slot OR p.b=i.slot)
  JOIN {EP} o ON o.episode_id=p.episode_id
       AND o.slot = CASE WHEN p.a=i.slot THEN p.b ELSE p.a END AND o.role='crew'
  GROUP BY 1
""").df()
print("\n=== ISOLATION (alone with 1 crew, no 3rd party — kill opportunity) ===")
for _,r in iso.iterrows():
    g=games[r.policy_name]; print(f"  {r.policy_name:14} {r.n/g:6.2f} isolations/game  {r.ticks/g:7.0f} isolated ticks/game")

# 3. FOLLOWING + CHASE (attributed to the imposter as follower/chaser)
fol = per_game('following_interval', "json_extract(t.value,'$.follower')::INT=i.slot")
cha = per_game('chase_interval', "json_extract(t.value,'$.chaser')::INT=i.slot")
print("\n=== FOLLOWING / CHASING (imposter is the follower/chaser) ===")
for pol in (US,AARON):
    g=games.get(pol)
    if not g: continue
    fr=fol[fol.policy_name==pol]; cr=cha[cha.policy_name==pol]
    fn=fr.n_intervals.sum()/g if len(fr) else 0; ft=fr.total_ticks.sum()/g if len(fr) else 0
    cn=cr.n_intervals.sum()/g if len(cr) else 0; ct=cr.total_ticks.sum()/g if len(cr) else 0
    print(f"  {pol:14} follow {fn:5.2f}/g ({ft:5.0f} ticks)   chase {cn:5.2f}/g ({ct:4.0f} ticks)")

# 6. ROOM CIRCULATION (entered_room during Playing)
rc = con.execute(f"""
  SELECT i.policy_name, COUNT(*) n
  FROM {ev('entered_room')} t JOIN imp i ON t.episode_id=i.episode_id AND t.slot=i.slot
  WHERE json_extract_string(t.value,'$.phase')='Playing'
  GROUP BY 1
""").df()
print("\n=== ROOM CIRCULATION (room entries/game during Playing) ===")
for _,r in rc.iterrows():
    print(f"  {r.policy_name:14} {r.n/games[r.policy_name]:5.1f} room-entries/game")

# 5. ROOM PRESENCE (where the imposter spends Playing ticks) — top rooms
rp = con.execute(f"""
  SELECT i.policy_name, json_extract_string(t.value,'$.room') room, COUNT(*) c
  FROM {ev('player_state')} t JOIN imp i ON t.episode_id=i.episode_id AND t.slot=i.slot
  WHERE json_extract_string(t.value,'$.phase')='Playing'
    AND json_extract_string(t.value,'$.alive')='true'
  GROUP BY 1,2
""").df()
print("\n=== ROOM PRESENCE (top rooms by alive-Playing time share) ===")
for pol in (US,AARON):
    d=rp[rp.policy_name==pol]; tot=d.c.sum()
    if not tot: continue
    top=d.sort_values("c",ascending=False).head(4)
    s="  ".join(f"{x.room}:{100*x.c/tot:.0f}%" for _,x in top.iterrows())
    print(f"  {pol:14} {s}")

# 8. EJECTION (imposter ended dead == ejected) + survival
ej = con.execute(f"""
  WITH last AS (
    SELECT t.episode_id, t.slot, i.policy_name,
           ARG_MAX(json_extract_string(t.value,'$.alive'), t.ts) AS alive_end,
           MAX(t.ts) AS end_ts
    FROM {ev('player_state')} t JOIN imp i ON t.episode_id=i.episode_id AND t.slot=i.slot
    GROUP BY 1,2,3
  )
  SELECT policy_name, COUNT(*) g, SUM(CASE WHEN alive_end='false' THEN 1 ELSE 0 END) ejected
  FROM last GROUP BY 1
""").df()
print("\n=== EJECTION (imposter ended dead = voted out) ===")
for _,r in ej.iterrows():
    print(f"  {r.policy_name:14} ejected {int(r.ejected)}/{int(r.g)} = {100*r.ejected/r.g:.0f}% of imposter games")
