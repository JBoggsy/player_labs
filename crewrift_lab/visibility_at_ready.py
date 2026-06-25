"""At the moment kill-cooldown comes off (and the 50 ticks before), do we already
have a crewmate in VIEW? If yes, the dither is pure hesitation (just kill). If no, we
must pre-position. Measures crewborg:v42 (us) vs crewborg-aaln:v17 (Aaron)."""
import duckdb, sys, json, statistics as st
from collections import defaultdict

WH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/v42_warehouse"
WINDOW = 50
con = duckdb.connect()
def ev(k): return f"read_parquet('{WH}/events/key={k}/*.parquet')"
EP = f"read_parquet('{WH}/episode_players.parquet')"

imp = con.execute(f"""SELECT policy_name, episode_id, slot FROM {EP}
  WHERE role='imposter' AND policy_name IN ('crewborg','crewborg-aaln') AND score>=0""").df()
key = {(r.episode_id, r.slot): r.policy_name for _,r in imp.iterrows()}

# cooldown series (Playing, alive) for imposter slots
ps = con.execute(f"""SELECT episode_id, slot, ts,
    json_extract(value,'$.kill_cooldown')::INT cd, json_extract_string(value,'$.alive') alive
  FROM {ev('player_state')} WHERE json_extract_string(value,'$.phase')='Playing'
  ORDER BY episode_id, slot, ts""").df()
# crew-visibility intervals where the imposter is the OBSERVER
vis = con.execute(f"""SELECT episode_id,
    json_extract(value,'$.observer_slot')::INT obs,
    json_extract(value,'$.tick_start')::INT t0, json_extract(value,'$.tick_end')::INT t1
  FROM {ev('player_visible_interval')}
  WHERE json_extract_string(value,'$.target_kind')='player'
    AND json_extract_string(value,'$.target_role')='crew'""").df()

cdser = defaultdict(list)
for r in ps.itertuples():
    if (r.episode_id, r.slot) in key: cdser[(r.episode_id, r.slot)].append((r.ts, r.cd, r.alive))
vismap = defaultdict(list)
for r in vis.itertuples():
    if (r.episode_id, r.obs) in key: vismap[(r.episode_id, r.obs)].append((r.t0, r.t1))

# per policy: for each cooldown-ready transition: visible AT R, and visible within
# each lookback window; plus the gap to the most-recent crew sighting at/before R.
WINDOWS = [0, 50, 100, 200, 400, 800]
res = defaultdict(lambda: {"ready":0, "win":defaultdict(int), "gaps":[], "ncrew_at":[]})
for k, rows in cdser.items():
    pol = key[k]; rows.sort()
    ivals = sorted(vismap.get(k, []))
    last = None
    for ts, cd, alive in rows:
        if cd is None: continue
        if last is not None and cd == 0 and last > 0 and alive == 'true':  # became ready
            R = ts
            res[pol]["ready"] += 1
            res[pol]["ncrew_at"].append(sum(1 for t0,t1 in ivals if t0 <= R <= t1))
            for w in WINDOWS:
                if any(t1 >= R-w and t0 <= R for t0,t1 in ivals): res[pol]["win"][w] += 1
            # gap to most-recent sighting at/before R (visible spans count as gap 0)
            recent = [min(t1, R) for t0,t1 in ivals if t0 <= R]
            res[pol]["gaps"].append(R - max(recent) if recent else None)
        last = cd

print(f"warehouse: {WH}\n")
print("Share of cooldown-ready moments with a CREW in view at/within N ticks before ready:")
hdr = "policy".ljust(16) + "ready".rjust(7) + "".join(f"≤{w}t".rjust(8) for w in WINDOWS) + "avg#@R".rjust(9)
print(hdr)
for pol in ('crewborg','crewborg-aaln'):
    d = res[pol]; n = d["ready"] or 1
    tag = " <<us" if pol=='crewborg' else " (Aaron)"
    cells = "".join(f"{100*d['win'][w]/n:.0f}%".rjust(8) for w in WINDOWS)
    avg = st.mean(d["ncrew_at"]) if d["ncrew_at"] else 0
    print(f"{pol:16}{d['ready']:>7}{cells}{avg:>9.2f}{tag}")
print("\n(≤0t = visible exactly AT the ready tick. Reading across shows how early we'd")
print(" have to start approaching to have a target in hand when cooldown ends.)")
print("\nMedian ticks since last crew sighting at the ready moment (lower = a target was just there):")
for pol in ('crewborg','crewborg-aaln'):
    g = [x for x in res[pol]["gaps"] if x is not None]
    none_n = sum(1 for x in res[pol]["gaps"] if x is None)
    md = f"{st.median(g):.0f}" if g else "-"
    print(f"  {pol:16} median gap {md:>6} ticks   (never-seen-before-ready: {none_n}/{res[pol]['ready']})")
