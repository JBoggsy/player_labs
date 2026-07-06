#!/usr/bin/env python3
"""Generate the self-contained HTML ranking + differential report."""
from __future__ import annotations
import base64, glob, io, json, math, os
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _data import seats_df

HERE = Path(__file__).resolve().parent
B = str(os.environ.get("RANK_DATA", HERE / "data"))
ME = "crewborg"
plt.rcParams.update({"font.size": 11, "figure.dpi": 110, "savefig.bbox": "tight",
                     "axes.spmath": False} if False else {"font.size": 11})

def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),)*3
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return p, c-h, c+h

# ---- clean-game win rates (overall / crew / imposter) from episode_players ----
S = defaultdict(lambda: {"overall":[0,0], "crew":[0,0], "imposter":[0,0]})
for _, row in seats_df().iterrows():
    nm = row.policy_name
    w = int(bool(row.win))
    S[nm]["overall"][0]+=w; S[nm]["overall"][1]+=1
    S[nm][row.role][0]+=w; S[nm][row.role][1]+=1

bt = json.load(open(f"{B}/bt_ranks.json"))
diff = json.load(open(f"{B}/differential.json"))
rooms = json.load(open(f"{B}/rooms.json"))
repl = json.load(open(f"{B}/replays.json"))

def short(n): return n.replace("crewrift-prime-","cp-").replace("-crewborg","-cb").replace("crewborg","crewborg")

def png(fig):
    buf = io.BytesIO(); fig.savefig(buf, format="png", facecolor="none", bbox_inches="tight", pad_inches=0.15); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

ACCENT="#e8663a"; TOP="#3a9e6a"; GREY="#8a94a6"
def winrate_chart(metric, title):
    data = sorted(((nm, *wilson(*S[nm][metric]), S[nm][metric][1]) for nm in S), key=lambda t:-t[1])
    names=[short(n) for n,*_ in data]; ps=[p for _,p,_,_,_ in data]
    los=[p-lo for _,p,lo,_,_ in data]; his=[hi-p for _,p,_,hi,_ in data]
    cols=[ACCENT if n==ME else (TOP if i<3 else GREY) for i,(n,*_) in enumerate(data)]
    fig,ax=plt.subplots(figsize=(7.2, 4.3))
    y=np.arange(len(names))[::-1]
    ax.barh(y,[p*100 for p in ps],xerr=[np.array(los)*100,np.array(his)*100],
            color=cols,error_kw={"ecolor":"#00000055","capsize":2,"lw":1})
    ax.set_yticks(y); ax.set_yticklabels(names,fontsize=8.5)
    ax.set_xlabel("win rate (%)  — bars = 95% Wilson CI"); ax.set_title(title,fontweight="bold")
    ax.grid(axis="x",alpha=.25); ax.set_axisbelow(True)
    for sp in ("top","right"): ax.spines[sp].set_visible(False)
    fig.patch.set_alpha(0)
    return png(fig)

def diff_chart(role, title):
    rows=[r for r in diff[role] if abs(r["cohen_d"])>=0.12][:10]
    feats=[r["feature"] for r in rows]; ds=[r["cohen_d"] for r in rows]
    cols=[ACCENT if d>0 else "#4a7fc0" for d in ds]
    fig,ax=plt.subplots(figsize=(7.2, 4.0))
    y=np.arange(len(feats))[::-1]
    ax.barh(y,ds,color=cols)
    ax.set_yticks(y); ax.set_yticklabels(feats,fontsize=9)
    ax.axvline(0,color="#444",lw=.8)
    ax.set_xlabel("Cohen's d   (→ crewborg higher · ← crewborg lower)")
    ax.set_title(title,fontweight="bold"); ax.grid(axis="x",alpha=.25); ax.set_axisbelow(True)
    for sp in ("top","right"): ax.spines[sp].set_visible(False)
    fig.patch.set_alpha(0)
    return png(fig)

def room_chart(me_key, top_key, title):
    me=dict((r[0],r[2]) for r in rooms[me_key]); tp=dict((r[0],r[2]) for r in rooms[top_key])
    allr=[r for r,_ in sorted({**me,**tp}.items(), key=lambda kv:-(me.get(kv[0],0)+tp.get(kv[0],0)))][:8]
    x=np.arange(len(allr)); w=0.4
    fig,ax=plt.subplots(figsize=(7.2,3.6))
    ax.bar(x-w/2,[me.get(r,0)*100 for r in allr],w,label="crewborg",color=ACCENT)
    ax.bar(x+w/2,[tp.get(r,0)*100 for r in allr],w,label="top-3",color=TOP)
    ax.set_xticks(x); ax.set_xticklabels(allr,rotation=35,ha="right",fontsize=8.5)
    ax.set_ylabel("% of bodies"); ax.set_title(title,fontweight="bold"); ax.legend(frameon=False)
    ax.grid(axis="y",alpha=.25); ax.set_axisbelow(True)
    for sp in ("top","right"): ax.spines[sp].set_visible(False)
    fig.patch.set_alpha(0)
    return png(fig)

charts = {
    "overall": winrate_chart("overall","Overall win rate (role-mixed)"),
    "crew": winrate_chart("crew","Crew win rate"),
    "imposter": winrate_chart("imposter","Imposter win rate"),
    "diff_crew": diff_chart("crew","Crew: what most separates crewborg from top-3"),
    "diff_imp": diff_chart("imposter","Imposter: what most separates crewborg from top-3"),
    "kill_rooms": room_chart("kill_rooms_crewborg","kill_rooms_top","Where crewborg kills (imposter)"),
    "death_rooms": room_chart("death_rooms_crewborg","death_rooms_top","Where crewborg dies (crew)"),
}

def rank_table(metric):
    data = sorted(((nm, *wilson(*S[nm][metric]), S[nm][metric][1]) for nm in S), key=lambda t:-t[1])
    btk = "crew" if metric=="crew" else ("imposter" if metric=="imposter" else None)
    out=[]
    for i,(nm,p,lo,hi,n) in enumerate(data,1):
        b = bt.get(btk,{}).get(nm) if btk else None
        btcol = (f"{int(b['rank_med'])} ({int(b['rank_lo'])}–{int(b['rank_hi'])})" if b else "—")
        cls=" class='me'" if nm==ME else (" class='top'" if i<=3 else "")
        out.append(f"<tr{cls}><td>{i}</td><td>{nm}</td><td>{p*100:.1f}%</td>"
                   f"<td class='ci'>{lo*100:.1f}–{hi*100:.1f}</td><td>{n}</td><td>{btcol}</td></tr>")
    return "\n".join(out)

def diff_table(role):
    out=[]
    for r in diff[role]:
        cb,t3=r["crewborg_mean"],r["top3_mean"]
        dpct=(cb-t3)/t3*100 if t3 else float("nan")
        sig="***" if r["p"]<0.001 else "**" if r["p"]<0.01 else "*" if r["p"]<0.05 else "ns"
        big=" class='big'" if abs(r["cohen_d"])>=0.3 else ""
        arrow="▲" if cb>t3 else "▼"
        out.append(f"<tr{big}><td>{r['feature']}</td><td>{cb:.2f}</td><td>{t3:.2f}</td>"
                   f"<td class='{'hi' if cb>t3 else 'lo'}'>{arrow} {dpct:+.0f}%</td>"
                   f"<td>{r['cohen_d']:+.2f}</td><td>{sig}</td></tr>")
    return "\n".join(out)

repl_rows=""
for eid,tasks,url in repl["crew_losses"][:5]:
    repl_rows+=f"<tr><td>crew loss, {int(tasks)}/8 tasks done</td><td><a href='{url}'>replay</a></td></tr>"
for eid,kills,url in repl["imp_losses"][:5]:
    repl_rows+=f"<tr><td>imposter loss, {int(kills)} kills</td><td><a href='{url}'>replay</a></td></tr>"

cb_ov=wilson(*S[ME]["overall"]); cb_cr=wilson(*S[ME]["crew"]); cb_im=wilson(*S[ME]["imposter"])

HTML=f"""<div class="wrap">
<header>
<h1>crewborg&nbsp;v96 — where we rank & what separates us</h1>
<p class="sub">728 clean games vs the live Crewrift Prime champion field · balanced 12-policy pool · natural roles.
Dead connect-timeout games dropped (see caveat). Generated from the event warehouse.</p>
</header>

<section class="cards">
  <div class="card"><div class="k">Overall</div><div class="v">{cb_ov[0]*100:.0f}%</div><div class="r">rank 4 / 13</div></div>
  <div class="card"><div class="k">As crew</div><div class="v">{cb_cr[0]*100:.0f}%</div><div class="r">BT rank {int(bt['crew'][ME]['rank_med'])} ({int(bt['crew'][ME]['rank_lo'])}–{int(bt['crew'][ME]['rank_hi'])})</div></div>
  <div class="card"><div class="k">As imposter</div><div class="v">{cb_im[0]*100:.0f}%</div><div class="r">BT rank {int(bt['imposter'][ME]['rank_med'])} ({int(bt['imposter'][ME]['rank_lo'])}–{int(bt['imposter'][ME]['rank_hi'])})</div></div>
</section>

<section>
<h2>1 · Where we rank</h2>
<p>crewborg is a solid <b>upper-middle</b> policy in this field — confidently not top-tier, confidently not bottom, at
both roles. We can state the <i>tier</i> with confidence; the middle of each table is a cluster of statistical ties
(overlapping CIs), so an exact rank isn't resolved even at 728 games. The Bradley-Terry column controls for who our
teammates and opponents were; it agrees with the raw win-rate order.</p>
<div class="grid3">
  <figure><img src="{charts['overall']}"><figcaption>Overall (role-mixed — mostly reflects the 75/25 crew/imposter split)</figcaption></figure>
  <figure><img src="{charts['crew']}"><figcaption>Crew</figcaption></figure>
  <figure><img src="{charts['imposter']}"><figcaption>Imposter</figcaption></figure>
</div>
<div class="tbls">
<div><h3>Overall</h3><table><tr><th>#</th><th>policy</th><th>win</th><th>95% CI</th><th>n</th><th>BT</th></tr>{rank_table('overall')}</table></div>
<div><h3>Crew</h3><table><tr><th>#</th><th>policy</th><th>win</th><th>95% CI</th><th>n</th><th>BT rank</th></tr>{rank_table('crew')}</table></div>
<div><h3>Imposter</h3><table><tr><th>#</th><th>policy</th><th>win</th><th>95% CI</th><th>n</th><th>BT rank</th></tr>{rank_table('imposter')}</table></div>
</div>
</section>

<section>
<h2>2 · Who's doing well, and how they differ from us</h2>
<p><b>crewborg-mv, scott-crewborg-hs1 and forgeling-focusfire</b> lead the <b>crew</b> table (45–49%).
<b>relhalpha, jordan-crewborg-aaln and sasmith-crewborg-hs1</b> lead <b>imposter</b> (78–83%).
softmaxwell-crewborg is the clear tail in both. Below is the surface-level, <i>non-causal</i> read of which
measured behaviours most separate crewborg from those leaders — ranked by effect size (Cohen's d). *** = p&lt;0.001.</p>

<div class="split">
<figure><img src="{charts['diff_crew']}"></figure>
<div><h3>Crew — most differentiating</h3>
<table><tr><th>feature (per game)</th><th>crewborg</th><th>top-3</th><th>Δ</th><th>d</th><th>p</th></tr>{diff_table('crew')}</table></div>
</div>

<div class="split">
<figure><img src="{charts['diff_imp']}"></figure>
<div><h3>Imposter — most differentiating</h3>
<table><tr><th>feature (per game)</th><th>crewborg</th><th>top-3</th><th>Δ</th><th>d</th><th>p</th></tr>{diff_table('imposter')}</table></div>
</div>
</section>

<section>
<h2>3 · Rooms — where we kill and where we die</h2>
<div class="split">
<figure><img src="{charts['kill_rooms']}"><figcaption>As imposter: crewborg over-indexes Science Bay for kills; the top imposters concentrate on Bridge.</figcaption></figure>
<figure><img src="{charts['death_rooms']}"><figcaption>As crew: crewborg's deaths spread across Storage Deck &amp; Bridge; top crew die overwhelmingly in Bridge (a meeting-adjacent hub).</figcaption></figure>
</div>
<p class="note">Body-location share (sampled corpse snapshots), a proxy for kill/death location. Rooms are moderately
differentiating but far smaller effects than the behavioural stats above.</p>
</section>

<section>
<h2>4 · Surface-level dig: where we're leaking games</h2>
<div class="callout">
<p><b>The single loudest signal (crew):</b> crewborg <b>skips votes ~2× as often</b> as top crew (1.76 vs 0.86 skips/game,
d=+0.78), calls <b>~half the meetings</b> (0.30 vs 0.71, d=−0.65), and casts <b>~half the player-votes</b> (0.64 vs 1.35,
d=−0.61) — <i>despite chatting MORE</i> (d=+0.38) and completing <b>more tasks</b> (6.79 vs 6.10). We talk and do tasks
but won't pull the voting trigger. Corroboration: <b>256 of our clean crew games were losses where we'd completed 6+ of
8 tasks</b> — tasks aren't the bottleneck; converting reads into ejections is.</p>
<p><b>Imposter:</b> crewborg gets the <b>same kill count</b> as the top imposters (1.77 vs 1.78) but <b>follows/tails 37% less</b>
(d=−0.80), <b>chases 35% less</b>, <b>chats 39% less</b> and stays silent in more meetings (d=−0.46), and gets its
<b>first kill ~20% later</b> (d=+0.36). Same kills, quieter and more passive social+hunting game.</p>
</div>
<h3>Replays to open (crewborg losses)</h3>
<table class="repl"><tr><th>situation</th><th>link</th></tr>{repl_rows}</table>
</section>

<section>
<h2>Caveat — data quality</h2>
<p class="note">Of 1,500 requested games, <b>772 (51%) were dead connect-timeouts</b> — a crew seat's container failed
to start (no gameplay, auto-scored an imposter win). Those are dropped here; all stats are on the 728 fully-played
games. crewborg's own connect-timeout rate was 24% (heavy LLM cold-start vs a tight platform deadline) — you noted
this is now fixed, so a fresh batch should retain the full N and tighten every CI on this page.</p>
</section>
<footer>crewborg v96 · event-warehouse analysis · effect sizes are associational, not causal</footer>
</div>"""

STYLE="""
:root{--bg:#f7f8fa;--fg:#1a1e26;--mut:#5b6472;--card:#fff;--line:#e4e7ec;--accent:#e8663a;--top:#3a9e6a}
@media(prefers-color-scheme:dark){:root{--bg:#12151b;--fg:#e6e9ef;--mut:#9aa4b2;--card:#1b1f27;--line:#2a2f3a}}
:root[data-theme=dark]{--bg:#12151b;--fg:#e6e9ef;--mut:#9aa4b2;--card:#1b1f27;--line:#2a2f3a}
:root[data-theme=light]{--bg:#f7f8fa;--fg:#1a1e26;--mut:#5b6472;--card:#fff;--line:#e4e7ec}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 60px}
header h1{font-size:26px;margin:0 0 6px}.sub{color:var(--mut);margin:0}
h2{font-size:20px;margin:38px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--line)}
h3{font-size:15px;margin:14px 0 6px}
.cards{display:flex;gap:14px;margin:22px 0}
.card{flex:1;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card .k{color:var(--mut);font-size:13px}.card .v{font-size:30px;font-weight:700;color:var(--accent)}.card .r{color:var(--mut);font-size:13px}
figure{margin:0}img{max-width:100%;border-radius:8px}figcaption{color:var(--mut);font-size:12.5px;margin-top:4px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.tbls{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-top:16px}
.split{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:center;margin:16px 0}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:left;padding:4px 7px;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:600}.ci{color:var(--mut)}
tr.me{background:color-mix(in srgb,var(--accent) 16%,transparent);font-weight:600}
tr.top{background:color-mix(in srgb,var(--top) 12%,transparent)}
tr.big td{font-weight:600}td.hi{color:var(--accent)}td.lo{color:#4a7fc0}
.callout{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;padding:6px 18px;margin:12px 0}
.note{color:var(--mut);font-size:13px}
.repl a{color:var(--accent)}
footer{margin-top:40px;color:var(--mut);font-size:12px;text-align:center}
@media(max-width:820px){.grid3,.tbls,.split{grid-template-columns:1fr}.cards{flex-direction:column}}
"""
open(f"{B}/report.html","w").write(f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>crewborg v96 ranking</title><style>{STYLE}</style></head><body>{HTML}</body></html>")
print("wrote report.html", len(HTML), "chars body")
