#!/usr/bin/env python3
"""Render the self-contained HTML voting-behaviour report from voting_metrics.json.

Companion to report_gen.py (same visual system); reads the OUTPUT of
voting_metrics.py rather than the event warehouse directly.
"""
from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
B = str(os.environ.get("RANK_DATA", HERE / "data"))
ME = "crewborg"

plt.rcParams.update({"font.size": 11})

ACCENT = "#e8663a"
TOP = "#3a9e6a"
GREY = "#8a94a6"
BLUE = "#4a7fc0"


def png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="none", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def short(n):
    return n.replace("crewrift-prime-", "cp-").replace("-crewborg", "-cb")


metrics = json.load(open(f"{B}/voting_metrics.json"))
pol = metrics["policies"]
# stable order: by crew win rate desc
order = sorted(pol.keys(), key=lambda p: -pol[p]["crew_win_rate"]["pct"])


def colors_for(names):
    return [ACCENT if n == ME else (TOP if i < 3 else GREY) for i, n in enumerate(names)]


def hbar_chart(values, names, title, xlabel, fmt="{:.1f}", highlight_rank=True):
    fig, ax = plt.subplots(figsize=(7.2, max(3.2, 0.34 * len(names))))
    y = np.arange(len(names))[::-1]
    cols = colors_for(names) if highlight_rank else [ACCENT if n == ME else GREY for n in names]
    ax.barh(y, values, color=cols)
    ax.set_yticks(y)
    ax.set_yticklabels([short(n) for n in names], fontsize=8.5)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontweight="bold")
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.patch.set_alpha(0)
    return png(fig)


def grouped_eject_chart():
    names = [p for p in order if pol[p]["eject_when_voted_imposter"]["n"] > 0 or pol[p]["eject_when_voted_crewmate"]["n"] > 0]
    imp_pct = [pol[p]["eject_when_voted_imposter"]["pct"] or 0 for p in names]
    crew_pct = [pol[p]["eject_when_voted_crewmate"]["pct"] or 0 for p in names]
    y = np.arange(len(names))[::-1]
    h = 0.36
    fig, ax = plt.subplots(figsize=(7.4, max(3.4, 0.5 * len(names))))
    ax.barh(y + h / 2, imp_pct, h, label="target truly IMPOSTER (conversion)", color=TOP)
    ax.barh(y - h / 2, crew_pct, h, label="target truly CREWMATE (friendly fire)", color=ACCENT)
    ax.set_yticks(y)
    ax.set_yticklabels([short(n) for n in names], fontsize=8.5)
    ax.set_xlabel("% of that policy's non-skip votes where the target actually got ejected")
    ax.set_title("Ejection effectiveness: does the room act on the vote?", fontweight="bold")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.patch.set_alpha(0)
    return png(fig)


def scatter_chart(xkey, xlabel, title):
    xs, ys, names = [], [], []
    for p in order:
        x = pol[p][xkey]["mean"] if "mean" in pol[p][xkey] else pol[p][xkey]["pct"]
        if x is None:
            continue
        xs.append(x)
        ys.append(pol[p]["crew_win_rate"]["pct"])
        names.append(p)
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    cols = [ACCENT if n == ME else GREY for n in names]
    sizes = [70 if n == ME else 40 for n in names]
    ax.scatter(xs, ys, c=cols, s=sizes, zorder=3, edgecolor="white", linewidth=0.6)
    for x, y, n in zip(xs, ys, names):
        ax.annotate(short(n), (x, y), fontsize=7.5, xytext=(4, 3), textcoords="offset points",
                    color=(ACCENT if n == ME else "#5b6472"))
    if len(xs) >= 3:
        r, p_val = stats.pearsonr(xs, ys)
        ax.set_title(f"{title}  (r={r:+.2f}, p={p_val:.3f})", fontweight="bold", fontsize=12)
    else:
        ax.set_title(title, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("crew win rate (%)")
    ax.grid(alpha=0.25)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.patch.set_alpha(0)
    return png(fig), (r if len(xs) >= 3 else float("nan")), (p_val if len(xs) >= 3 else float("nan"))


charts = {}
charts["win"] = hbar_chart([pol[p]["crew_win_rate"]["pct"] for p in order], order,
                            "Crew win rate", "win rate (%)")
charts["votes"] = hbar_chart([pol[p]["votes_per_game"]["mean"] for p in order], order,
                              "Player-votes cast per game (crew)", "votes / game (mean)")
charts["chats"] = hbar_chart([pol[p]["chats_per_game"]["mean"] for p in order], order,
                              "Chat messages per game (crew)", "messages / game (mean)")
acc_names = [p for p in order if pol[p]["vote_accuracy"]["pct"] is not None]
charts["accuracy"] = hbar_chart([pol[p]["vote_accuracy"]["pct"] for p in acc_names], acc_names,
                                 "Vote accuracy (% of non-skip votes that hit the real imposter)", "accuracy (%)")
charts["eject"] = grouped_eject_chart()
charts["scatter_votes"], r_votes, p_votes = scatter_chart("votes_per_game", "votes cast / game (mean)",
                                                           "Vote RATE vs crew win rate")
charts["scatter_acc"], r_acc, p_acc = scatter_chart("vote_accuracy", "vote accuracy (%)",
                                                     "Vote ACCURACY vs crew win rate")
charts["scatter_chat"], r_chat, p_chat = scatter_chart("chats_per_game", "chat messages / game (mean)",
                                                        "Chat RATE vs crew win rate")


def fmt_pct(row_key_dict):
    n = row_key_dict.get("n", 0)
    pct = row_key_dict.get("pct")
    if not n or pct is None:
        return f"<span class='na'>N/A (n=0)</span>"
    return f"{pct:.1f}% <span class='n'>(n={n})</span>"


def summary_rows():
    out = []
    for i, p in enumerate(order, 1):
        row = pol[p]
        cls = " class='me'" if p == ME else (" class='top'" if i <= 3 else "")
        vpg, cpg = row["votes_per_game"], row["chats_per_game"]
        out.append(
            f"<tr{cls}>"
            f"<td>{i}</td><td>{p}</td>"
            f"<td>{row['crew_win_rate']['pct']:.1f}%</td><td class='n'>{row['crew_win_rate']['n']}</td>"
            f"<td>{vpg['mean']:.2f}</td><td>{vpg['median']:.1f}</td><td>{vpg['std']:.2f}</td>"
            f"<td>{cpg['mean']:.2f}</td><td>{cpg['median']:.1f}</td><td>{cpg['std']:.2f}</td>"
            f"<td>{fmt_pct(row['vote_accuracy'])}</td>"
            f"<td>{fmt_pct(row['eject_when_voted_imposter'])}</td>"
            f"<td>{fmt_pct(row['eject_when_voted_crewmate'])}</td>"
            f"</tr>"
        )
    return "\n".join(out)


me_row = pol[ME]
n_games = metrics["n_clean_games"]
n_meetings = metrics["n_meetings"]
n_ejections = metrics["n_ejections_resolved"]
n_skewed = metrics["n_trace_warning_episodes"]

HTML = f"""<div class="wrap">
<header>
<h1>crewborg v96 — crew voting behaviour &amp; effectiveness</h1>
<p class="sub">{n_games} clean games vs the live Crewrift Prime champion field, same corpus as the v96 ranking/differential
report. Rebuilt event warehouse ({n_meetings} meetings, {n_ejections} ejections resolved, {n_skewed} version-skewed
episodes excluded). All metrics below are scoped to games played <b>as crew</b> — this is the study of "how do the
other crewmates vote effectively" that motivated it.</p>
</header>

<section class="cards">
  <div class="card"><div class="k">crewborg crew win</div><div class="v">{me_row['crew_win_rate']['pct']:.0f}%</div><div class="r">rank {order.index(ME)+1} / {len(order)}</div></div>
  <div class="card"><div class="k">votes / game</div><div class="v">{me_row['votes_per_game']['mean']:.2f}</div><div class="r">median {me_row['votes_per_game']['median']:.0f}, std {me_row['votes_per_game']['std']:.2f}</div></div>
  <div class="card"><div class="k">vote accuracy</div><div class="v">{(me_row['vote_accuracy']['pct'] or 0):.0f}%</div><div class="r">n={me_row['vote_accuracy']['n']}</div></div>
  <div class="card"><div class="k">eject|voted imposter</div><div class="v">{(me_row['eject_when_voted_imposter']['pct'] or 0):.0f}%</div><div class="r">n={me_row['eject_when_voted_imposter']['n']}</div></div>
</section>

<section>
<h2>1 · Summary table — sorted by crew win rate</h2>
<div class="tablewrap">
<table class="wide">
<tr>
  <th>#</th><th>policy</th>
  <th>crew win</th><th>n</th>
  <th colspan="3">votes/game (mean · median · std)</th>
  <th colspan="3">chats/game (mean · median · std)</th>
  <th>vote accuracy</th>
  <th>eject | voted imposter</th>
  <th>eject | voted crewmate</th>
</tr>
{summary_rows()}
</table>
</div>
<p class="note">"Vote accuracy" = of a policy's non-skip votes, % whose target was truly the imposter. "Eject | voted
imposter/crewmate" = of those same non-skip votes, conditioned on the target's true role, % where the room actually
ejected that target that meeting (i.e. did the vote convert to an ejection, whether correct or a friendly-fire miss).
N/A rows are policies with zero non-skip votes recorded (near-silent voters, not a zero rounded down).</p>
</section>

<section>
<h2>2 · Vote rate &amp; chat rate</h2>
<div class="split">
<figure><img src="{charts['votes']}"></figure>
<figure><img src="{charts['chats']}"></figure>
</div>
</section>

<section>
<h2>3 · Vote accuracy &amp; ejection effectiveness</h2>
<div class="split">
<figure><img src="{charts['accuracy']}"><figcaption>Of non-skip votes, % that targeted the real imposter.</figcaption></figure>
<figure><img src="{charts['eject']}"><figcaption>Conversion (correct target ejected) vs friendly fire (innocent target ejected).</figcaption></figure>
</div>
</section>

<section>
<h2>4 · Does voting MORE, more ACCURATELY, or chatting more actually correlate with winning?</h2>
<p class="note">Cross-policy correlation across the {len(order)} policies in this field — observational, not causal (small
N of policies; confounded by everything else that differs between them).</p>
<div class="grid3">
<figure><img src="{charts['scatter_votes']}"></figure>
<figure><img src="{charts['scatter_acc']}"></figure>
<figure><img src="{charts['scatter_chat']}"></figure>
</div>
</section>

<footer>crewborg v96 · event-warehouse voting analysis · derived ejection ground truth (died-after-VoteResult, see
voting_metrics.py) · effect sizes/correlations are associational, not causal</footer>
</div>"""

STYLE = """
:root{--bg:#f7f8fa;--fg:#1a1e26;--mut:#5b6472;--card:#fff;--line:#e4e7ec;--accent:#e8663a;--top:#3a9e6a}
@media(prefers-color-scheme:dark){:root{--bg:#12151b;--fg:#e6e9ef;--mut:#9aa4b2;--card:#1b1f27;--line:#2a2f3a}}
:root[data-theme=dark]{--bg:#12151b;--fg:#e6e9ef;--mut:#9aa4b2;--card:#1b1f27;--line:#2a2f3a}
:root[data-theme=light]{--bg:#f7f8fa;--fg:#1a1e26;--mut:#5b6472;--card:#fff;--line:#e4e7ec}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
header h1{font-size:26px;margin:0 0 6px}.sub{color:var(--mut);margin:0}
h2{font-size:20px;margin:38px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--line)}
h3{font-size:15px;margin:14px 0 6px}
.cards{display:flex;gap:14px;margin:22px 0}
.card{flex:1;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card .k{color:var(--mut);font-size:13px}.card .v{font-size:30px;font-weight:700;color:var(--accent)}.card .r{color:var(--mut);font-size:13px}
figure{margin:0}img{max-width:100%;border-radius:8px}figcaption{color:var(--mut);font-size:12.5px;margin-top:4px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.split{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:center;margin:16px 0}
.tablewrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:12.5px}
table.wide{min-width:1000px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--mut);font-weight:600}
.n{color:var(--mut);font-size:11px}
.na{color:var(--mut);font-style:italic}
tr.me{background:color-mix(in srgb,var(--accent) 16%,transparent);font-weight:600}
tr.top{background:color-mix(in srgb,var(--top) 12%,transparent)}
.note{color:var(--mut);font-size:13px}
footer{margin-top:40px;color:var(--mut);font-size:12px;text-align:center}
@media(max-width:820px){.grid3,.split{grid-template-columns:1fr}.cards{flex-direction:column}}
"""

OUT_HTML = f"{B}/voting_report.html"
open(OUT_HTML, "w").write(
    f"<!doctype html><html><head><meta charset=utf-8>"
    f"<meta name=viewport content='width=device-width,initial-scale=1'>"
    f"<title>crewborg v96 voting report</title><style>{STYLE}</style></head><body>{HTML}</body></html>"
)
print(f"wrote {OUT_HTML} ({len(HTML)} chars body)")
print(f"votes-vs-winrate r={r_votes:+.2f} p={p_votes:.3f}")
print(f"accuracy-vs-winrate r={r_acc:+.2f} p={p_acc:.3f}")
print(f"chat-vs-winrate r={r_chat:+.2f} p={p_chat:.3f}")
