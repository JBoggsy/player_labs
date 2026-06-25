"""Suss-rate analysis: when crewborg is CREW, how often does it correctly finger the
imposter (Aaron) — via chat (the LLM-labelled chat_suss partition) and via votes — and
does our detection improve when the imposter is more AGGRESSIVE (James's hypothesis:
over-extension makes him catchable).

Run on a warehouse that has had `crewrift-event-warehouse suss` applied.
Usage: uv run --with duckdb python crewrift_lab/suss_rate.py <warehouse_dir>
"""
import duckdb, sys

WH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/suss_big_warehouse"
US = "crewborg"
con = duckdb.connect()
def ev(k): return f"read_parquet('{WH}/events/key={k}/*.parquet')"
EP = f"read_parquet('{WH}/episode_players.parquet')"

# ---- 1. CHAT suss accuracy (who do we accuse in chat; is it an imposter?) ----
print(f"warehouse: {WH}\n")
print("=== CHAT suss accuracy — when a policy/role accuses someone, is the target an imposter? ===")
chat = con.execute(f"""
  SELECT policy_name, role,
    COUNT(*) FILTER (WHERE json_extract_string(value,'$.is_suss')='true') AS susses,
    COUNT(*) FILTER (WHERE json_extract_string(value,'$.target_is_imposter')='true') AS hit_imp
  FROM {ev('chat_suss')} GROUP BY 1,2 HAVING susses>0 ORDER BY role, policy_name
""").df()
chat['suss_acc%'] = (100*chat.hit_imp/chat.susses).round(0)
print(chat.to_string())

# ---- 2. VOTE accuracy (who do we vote; is it an imposter?) ----
print("\n=== VOTE accuracy — of non-skip votes, fraction that hit an imposter ===")
vote = con.execute(f"""
  WITH v AS (
    SELECT vc.policy_name, vc.role, vc.episode_id,
           json_extract(vc.value,'$.target_slot')::INT tslot
    FROM {ev('vote_cast')} vc
    WHERE json_extract(vc.value,'$.target_slot')::INT >= 0   -- drop skips/abstains
  )
  SELECT v.policy_name, v.role, COUNT(*) votes,
         COUNT(*) FILTER (WHERE ep.role='imposter') hit_imp
  FROM v JOIN {EP} ep ON ep.episode_id=v.episode_id AND ep.slot=v.tslot
  GROUP BY 1,2 HAVING votes>0 ORDER BY v.role, v.policy_name
""").df()
vote['vote_acc%'] = (100*vote.hit_imp/vote.votes).round(0)
print(vote.to_string())

# ---- 3. OUR (crewborg) crew detection vs imposter AGGRESSION ----
# Aggression per game = total kills by the imposters (here both imposters are Aaron).
print(f"\n=== {US} as CREW: detection vs imposter aggression (kills/game by the imposters) ===")
agg = con.execute(f"""
  SELECT episode_id, SUM(kills) imp_kills FROM {EP} WHERE role='imposter' GROUP BY 1
""").df()
con.register("agg", agg)
res = con.execute(f"""
  WITH suss AS (
    SELECT episode_id,
      COUNT(*) FILTER (WHERE json_extract_string(value,'$.is_suss')='true') susses,
      COUNT(*) FILTER (WHERE json_extract_string(value,'$.target_is_imposter')='true') hit
    FROM {ev('chat_suss')} WHERE policy_name='{US}' AND role='crew' GROUP BY 1
  )
  SELECT CASE WHEN a.imp_kills<=1 THEN '0-1 (passive)'
              WHEN a.imp_kills<=3 THEN '2-3 (medium)'
              ELSE '4+ (aggressive)' END AS aggression,
         COUNT(DISTINCT a.episode_id) games,
         SUM(s.susses) susses, SUM(s.hit) hit_imp
  FROM agg a LEFT JOIN suss s ON a.episode_id=s.episode_id
  GROUP BY 1 ORDER BY 1
""").df()
res['chat_suss_acc%'] = (100*res.hit_imp/res.susses).round(0)
print(res.to_string())
print("\n(hypothesis: aggressive imposter -> more cues -> higher suss accuracy / more susses.")
print(" If accuracy/volume rises with aggression, our crew is already exploiting over-extension; if flat, it isn't.)")

# ---- 4. Engagement: how often do we even speak/suss as crew ----
print(f"\n=== {US} CREW engagement (do we talk at all?) ===")
eng = con.execute(f"""
  SELECT
    COUNT(*) chat_msgs,
    COUNT(*) FILTER (WHERE json_extract_string(value,'$.is_suss')='true') susses,
    COUNT(DISTINCT episode_id) games_with_chat
  FROM {ev('chat_suss')} WHERE policy_name='{US}' AND role='crew'
""").df()
print(eng.to_string())
