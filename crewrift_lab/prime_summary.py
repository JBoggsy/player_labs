"""Natural Prime round-robin standings: per-policy win rate by role, imposter kills,
and crew detection (chat-suss + vote accuracy). Run on a suss'd warehouse.
Usage: uv run --with duckdb python crewrift_lab/prime_summary.py <warehouse_dir>
"""
import duckdb, sys

WH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/prime_warehouse"
LABEL = {
    "e67fa49f-bedc-46f4-b6c9-eb8480e7460a": "crewborg:v43 (us)",
    "50dd7947-c883-4ee4-8758-57d4f6c8a95e": "crewborg-aaln:v17 (Aaron)",
    "ada3fe84-2000-4c92-861e-289e60f510de": "truecrew:v27 (Andre champ)",
    "ba730308-b41d-4dcd-b4a9-124d479ae70f": "truecrew:v28 (Andre latest)",
}
con = duckdb.connect()
def ev(k): return f"read_parquet('{WH}/events/key={k}/*.parquet')"
EP = f"read_parquet('{WH}/episode_players.parquet')"
def lab(pv): return LABEL.get(pv, (pv or "?")[:12])

# ---- win/role/kills per policy version ----
rows = con.execute(f"""
  SELECT policy_version pv,
    COUNT(*) FILTER (WHERE role='crew') crew_g,
    COUNT(*) FILTER (WHERE role='crew' AND win) crew_w,
    COUNT(*) FILTER (WHERE role='imposter') imp_g,
    COUNT(*) FILTER (WHERE role='imposter' AND win) imp_w,
    SUM(kills) FILTER (WHERE role='imposter') imp_kills
  FROM {EP} WHERE score >= 0 GROUP BY 1
""").df()
print(f"{'policy':30}{'crew win':>12}{'imp win':>12}{'imp k/g':>9}")
for _, r in rows.sort_values("pv").iterrows():
    cw = f"{r.crew_w}/{r.crew_g}={100*r.crew_w/max(r.crew_g,1):.0f}%"
    iw = f"{r.imp_w}/{r.imp_g}={100*r.imp_w/max(r.imp_g,1):.0f}%"
    ik = f"{r.imp_kills/max(r.imp_g,1):.2f}"
    print(f"{lab(r.pv):30}{cw:>12}{iw:>12}{ik:>9}")

# ---- crew detection: chat-suss accuracy + vote accuracy ----
print(f"\n{'policy (as CREW)':30}{'chat suss acc':>15}{'vote acc':>12}{'susses':>8}{'votes':>8}")
chat = con.execute(f"""
  SELECT policy_version pv,
    COUNT(*) FILTER (WHERE json_extract_string(value,'$.is_suss')='true') susses,
    COUNT(*) FILTER (WHERE json_extract_string(value,'$.target_is_imposter')='true') hit
  FROM {ev('chat_suss')} WHERE role='crew' GROUP BY 1
""").df()
vote = con.execute(f"""
  WITH v AS (SELECT vc.policy_version pv, vc.episode_id, json_extract(vc.value,'$.target_slot')::INT t
             FROM {ev('vote_cast')} vc WHERE vc.role='crew' AND json_extract(vc.value,'$.target_slot')::INT>=0)
  SELECT v.pv, COUNT(*) votes, COUNT(*) FILTER (WHERE ep.role='imposter') hit
  FROM v JOIN {EP} ep ON ep.episode_id=v.episode_id AND ep.slot=v.t GROUP BY 1
""").df()
chat = chat.set_index("pv"); vote = vote.set_index("pv")
for pv in sorted(set(chat.index) | set(vote.index)):
    s = int(chat.loc[pv].susses) if pv in chat.index else 0
    sh = int(chat.loc[pv].hit) if pv in chat.index else 0
    vt = int(vote.loc[pv].votes) if pv in vote.index else 0
    vh = int(vote.loc[pv].hit) if pv in vote.index else 0
    ca = f"{100*sh/s:.0f}%" if s else "-"
    va = f"{100*vh/vt:.0f}%" if vt else "-"
    print(f"{lab(pv):30}{ca:>15}{va:>12}{s:>8}{vt:>8}")
