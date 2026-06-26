"""Kill-latency: ticks from kill-cooldown-ready to actual kill (James's hypothesis:
Aaron kills sooner after he's able to). Per imposter-game, from kill_cooldown series
+ kill events. Cooldown also resets at meetings, so 'ready' = cooldown last hit 0
(and stayed) before each kill; we count Playing-phase ticks."""
import duckdb, sys, json, statistics as st
from collections import defaultdict

WH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/v42_warehouse"
con = duckdb.connect()
def ev(k): return f"read_parquet('{WH}/events/key={k}/*.parquet')"
EP = f"read_parquet('{WH}/episode_players.parquet')"

# imposter (episode,slot) per policy, ops-filtered
imp = con.execute(f"""SELECT policy_name, episode_id, slot FROM {EP}
  WHERE role='imposter' AND policy_name IN ('crewborg','crewborg-aaln') AND score>=0""").df()
key = {(r.episode_id, r.slot): r.policy_name for _,r in imp.iterrows()}
eps = {r.episode_id for _,r in imp.iterrows()}

# kill_cooldown series for those imposter slots (Playing only)
ps = con.execute(f"""
  SELECT episode_id, slot, ts,
         json_extract(value,'$.kill_cooldown')::INT cd,
         json_extract_string(value,'$.alive') alive
  FROM {ev('player_state')}
  WHERE json_extract_string(value,'$.phase')='Playing'
  ORDER BY episode_id, slot, ts
""").df()
# kill events attributed to imposter slot
kills = con.execute(f"""
  SELECT episode_id, slot, ts FROM {ev('kill')}
  WHERE role='imposter' ORDER BY episode_id, slot, ts
""").df()

series = defaultdict(list)  # (ep,slot) -> [(ts,cd,alive)]
for r in ps.itertuples():
    if (r.episode_id, r.slot) in key:
        series[(r.episode_id, r.slot)].append((r.ts, r.cd, r.alive))
killmap = defaultdict(list)
for r in kills.itertuples():
    if (r.episode_id, r.slot) in key:
        killmap[(r.episode_id, r.slot)].append(r.ts)

dith = defaultdict(list)      # policy -> [dither ticks per kill]
ttfk = defaultdict(list)      # policy -> [time-to-first-kill ticks]
idle_ready = defaultdict(list) # policy -> [ticks alive & cd==0 but not killing] per game

# Measure durations by COUNTING Playing samples x snapshot interval, NEVER by subtracting
# raw ticks: the series is Playing-only, so a tick delta between two consecutive samples
# spans any meeting in between (~1272 ticks; a button meeting doesn't even reset cd) which
# is NOT idle/hunting time. Counting samples excludes meeting time automatically.
# (See best_practices.md: "Meeting/voting ticks are NOT idle time.")
steps = [b[0]-a[0] for rows in series.values() for a, b in zip(sorted(rows), sorted(rows)[1:]) if 0 < b[0]-a[0] < 100]
SNAP = st.median(steps) if steps else 1.0

for k, rows in series.items():
    pol = key[k]; rows.sort()
    play_start = rows[0][0]
    ks = sorted(killmap.get(k, []))
    if ks:  # TTFK = Playing samples from start to first kill x SNAP (drops any meeting before it)
        ttfk[pol].append(sum(1 for ts, _, _ in rows if play_start <= ts < ks[0]) * SNAP)
    ki = 0; idle_n = 0; ready_n = None  # ready_n = Playing+ready samples since becoming ready
    for ts, cd, alive in rows:
        if cd is None: continue
        while ki < len(ks) and ks[ki] <= ts:  # at each kill: dither = ready samples before it
            if ready_n is not None: dith[pol].append(ready_n * SNAP)
            ready_n = None; ki += 1
        if cd == 0 and alive == 'true':
            ready_n = (ready_n or 0) + 1
            idle_n += 1
        else:
            ready_n = None  # cd>0 (own cooldown / post-meeting reset) ends the ready window
    idle_ready[pol].append(idle_n * SNAP)

print(f"warehouse: {WH}\n")
print(f"{'policy':16}{'kills_seen':>11}{'median dither':>14}{'mean dither':>12}{'median TTFK':>13}{'idle-ready/g':>13}")
for pol in ('crewborg','crewborg-aaln'):
    d = dith[pol]; t = ttfk[pol]; ir = idle_ready[pol]
    tag = " <<us" if pol=='crewborg' else " (Aaron)"
    md = f"{st.median(d):.0f}" if d else "-"; mn = f"{st.mean(d):.0f}" if d else "-"
    mt = f"{st.median(t):.0f}" if t else "-"; mi = f"{st.mean(ir):.0f}" if ir else "-"
    print(f"{pol:16}{len(d):>11}{md:>14}{mn:>12}{mt:>13}{mi:>13}{tag}")
print("\n(dither = Playing-ticks between kill-cooldown reaching 0 and the kill; lower = kills sooner once able.")
print(" TTFK = ticks from Playing-start to first kill. idle-ready/g = ticks/game spent alive WITH cooldown ready but not killing. KillCooldown=800.)")
