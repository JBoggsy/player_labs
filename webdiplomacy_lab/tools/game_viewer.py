#!/usr/bin/env python3
"""Post-game slide-show viewer for one webDiplomacy episode: a single self-contained HTML file.

    uv run --with diplomacy==1.1.2 python webdiplomacy_lab/tools/game_viewer.py EPISODE_DIR [--out FILE]

EPISODE_DIR is a local run (`replay`, `results.json`, `logs/`) or a downloaded hosted episode
(`replay.json`, `results.json`, `logs/`). Slides:
- every movement phase: "Orders" (press of that phase as a chat log + the map with the orders
  as adjudicated) then "Resolution" (positions after adjudication and retreats, with what
  bounced, who was dislodged and how centres changed);
- every adjustment phase: "Builds" (press + the builds and disbands) then "Resolution";
- a final "Results" slide.

Press comes from the public messages file in the replay plus each seat's private-press archive
(the launcher's `private_press` log record), joined by message id. Maps are drawn by the
`diplomacy` package's renderer (`diplomacy` is a tool-only dependency, hence `uv run --with`).
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import diplomacy  # noqa: E402
from diplomacy.engine.renderer import Renderer  # noqa: E402

from webdip_bot.dipmap import POWER, DipMap  # noqa: E402
from webdip_episodes import read_log  # noqa: E402

NAMES = {c: p.title() for c, p in POWER.items()}
SHORT = {1: "ENG", 2: "FRA", 3: "ITA", 4: "GER", 5: "AUS", 6: "TUR", 7: "RUS"}


# --- loading -------------------------------------------------------------------------------

def load_episode(ep):
    replay_path = ep / "replay.json" if (ep / "replay.json").exists() else ep / "replay"
    frames = json.loads(replay_path.read_text())
    last = frames[-1]
    results = json.loads((ep / "results.json").read_text())
    messages = {}
    for frame in frames:
        for m in (frame.get("messages") or {}).get("messages", []):
            messages[m["id"]] = m
    seats, traces = {}, {}
    for log in sorted((ep / "logs").glob("policy_agent_*.log")):
        rows = read_log(log)
        slot = int(log.stem.rsplit("_", 1)[1])
        country = None
        for r in rows:
            if r.get("event") == "private_press":
                archive = r["archive"]
                country = archive.get("country_id")
                for m in archive.get("messages", []):
                    messages[m["id"]] = m
            if r.get("event") == "press_start" and r.get("country"):
                country = r["country"]
        policy = next((r.get("policy") for r in rows if r.get("policy")), None)
        if country:
            traces[int(country)] = collect_trace(rows)
        cost = sum(r.get("cost_usd", 0.0) for r in rows if r.get("event") == "llm_call")
        calls = sum(1 for r in rows if r.get("event") == "llm_call")
        seats[slot] = {"policy": policy, "country": country, "llm_cost": cost, "llm_calls": calls}
    return {"variant": last["variant"], "phases": last["history"]["phases"], "results": results,
            "messages": sorted(messages.values(), key=lambda m: (m["timeSent"], m["id"])), "seats": seats,
            "traces": traces}


TOOL_RESULT_CHARS = 4000


def collect_trace(rows):
    """Agent trace events of one seat, compacted and grouped by turn: {turn: [event, ...]}.

    Model requests contribute only their user messages (the wake briefing): the assistant
    turns and tool results they repeat are shown from `llm_call` and `tool_call` instead."""
    by_turn = {}

    def add(turn, event):
        if turn is not None:
            by_turn.setdefault(int(turn), []).append(event)

    for r in rows:
        e = r.get("event")
        wake = r.get("wake")
        turn = int(str(wake).split("-")[0]) if wake else r.get("turn")
        if e == "wake_start":
            add(turn, {"e": e, "wake": wake, "kind": r["kind"], "allowed": r.get("seconds_allowed"),
                       "unread": r.get("unread"), "t": r.get("t")})
        elif e == "wake":
            add(turn, {"e": e, "wake": wake, "kind": r["kind"], "status": r["status"], "seconds": r["seconds"],
                       "calls": r["calls"], "cost": r["cost_usd"], "final": r.get("final")})
        elif e == "wake_error":
            add(turn, {"e": e, "where": r.get("where")})
        elif e == "llm_request":
            for m in r.get("messages") or []:
                if m.get("role") == "user":
                    add(turn, {"e": "briefing", "wake": wake, "text": m.get("content") if isinstance(m.get("content"), str)
                               else json.dumps(m.get("content"))})
        elif e == "llm_call":
            reply = r.get("reply") or {}
            calls = [{"name": (c.get("function") or {}).get("name"), "arguments": (c.get("function") or {}).get("arguments")}
                     for c in reply.get("tool_calls") or []]
            add(turn, {"e": e, "wake": wake, "status": r.get("status"), "cost": r.get("cost_usd"),
                       "tokens": [r.get("prompt_tokens"), r.get("completion_tokens"), r.get("reasoning_tokens")],
                       "content": reply.get("content"), "reasoning": reply.get("reasoning"), "tool_calls": calls,
                       "error": r.get("error")})
        elif e == "tool_call":
            result = r.get("result") or ""
            add(turn, {"e": e, "wake": wake, "tool": r["tool"], "arguments": r.get("arguments"),
                       "result": result[:TOOL_RESULT_CHARS] + (" …(truncated)" if len(result) > TOOL_RESULT_CHARS else ""),
                       "seconds": r.get("seconds")})
        elif e == "press_out":
            add(turn, {"e": e, "to": r.get("to"), "text": r.get("text")})
        elif e == "press_in":
            add(turn, {"e": e, "frm": r.get("frm"), "text": r.get("text")})
        elif e in ("commitment", "commitment_verdict"):
            add(turn, {"e": e, "by": r.get("by"), "orders": r.get("orders"), "dmz": r.get("dmz"),
                       "note": r.get("note"), "verdict": r.get("verdict")})
        elif e == "press_commit":
            add(turn, {"e": e, "policy": r.get("press_policy"), "orders": r.get("orders"),
                       "expected": r.get("expected_centres")})
        elif e == "decision" and r.get("phase") == "Diplomacy":
            add(turn, {"e": e, "rejected": r.get("rejected"), "policy": r.get("press_policy"),
                       "cost": r.get("llm_cost_usd"), "trace": r.get("trace")})
        elif e == "workspace":
            add(turn, {"e": e, "plan": r.get("plan"), "notes": r.get("notes"), "commitments": r.get("commitments")})
    return by_turn


# --- map rendering -------------------------------------------------------------------------

class MapRenderer:
    def __init__(self, variant):
        self.terr = {t["id"]: t for t in variant["territories"]}
        self.dm = DipMap(variant["territories"])
        self.supply = {t for t, x in self.terr.items() if x["supply"] and x["coast"] != "Child"}
        self.count = 0

    def province(self, terr_id):
        return self.terr[terr_id]["coastParentID"]

    def owners(self, centers):
        return {c["terrID"]: c["countryID"] for c in centers if c["terrID"] in self.supply}

    def label(self, terr_id):
        return self.dm.loc[terr_id].split("/")[0] if terr_id else "?"

    def order_text(self, o):
        """Human order text from a history order (works without the unit table)."""
        unit = "A" if o.get("unitType") == "Army" else "F"
        here = self.label(o["terrID"])
        kind = o["type"]
        if kind == "Hold":
            return f"{unit} {here} holds"
        if kind == "Move":
            return f"{unit} {here} → {self.label(o['toTerrID'])}" + (" (convoy)" if o.get("viaConvoy") else "")
        if kind == "Support hold":
            return f"{unit} {here} supports {self.label(o['toTerrID'])}"
        if kind == "Support move":
            return f"{unit} {here} supports {self.label(o['fromTerrID'])} → {self.label(o['toTerrID'])}"
        if kind == "Convoy":
            return f"{unit} {here} convoys {self.label(o['fromTerrID'])} → {self.label(o['toTerrID'])}"
        if kind == "Retreat":
            return f"{unit} {here} retreats to {self.label(o['toTerrID'])}"
        if kind == "Disband":
            return f"{unit} {here} disbands"
        if kind in ("Build Army", "Build Fleet"):
            return f"builds {'army' if kind == 'Build Army' else 'fleet'} in {here}"
        if kind == "Destroy":
            return f"removes unit in {here}"
        return kind

    def render(self, units, owners, turn, orders=()):
        """SVG for a board (units, SC owners) with optional movement orders drawn."""
        game = diplomacy.Game()
        game.set_state(self.dm.state(units, owners, turn))
        unit_at = {}
        for u in units:
            unit_at[u["terrID"]] = u
            unit_at[self.province(u["terrID"])] = u
        by_power = {}
        for o in orders:
            if o["type"] not in ("Hold", "Move", "Support hold", "Support move", "Convoy"):
                continue
            try:
                by_power.setdefault(POWER[int(o["countryID"])], []).append(self.dm.order(o, unit_at))
            except (KeyError, ValueError):
                continue
        for power, texts in by_power.items():
            game.set_orders(power, texts)
        return self.clean(Renderer(game).render(incl_orders=bool(orders), incl_abbrev=True))

    def clean(self, svg):
        """Inline-ready SVG: no prolog or built-in styles, ids made unique per map."""
        self.count += 1
        prefix = f"m{self.count}-"
        svg = re.sub(r"<\?xml.*?\?>|<!DOCTYPE[^>]*>|<!--.*?-->", "", svg, flags=re.S)
        svg = re.sub(r"<style.*?</style>", "", svg, flags=re.S)
        svg = re.sub(r'\sid="([^"]+)"', lambda m: f' id="{prefix}{m.group(1)}"', svg)
        svg = re.sub(r'url\(#([^)]+)\)', lambda m: f"url(#{prefix}{m.group(1)})", svg)
        svg = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{prefix}{m.group(1)}"', svg)
        svg = re.sub(r'(<svg[^>]*?)\s(width|height)="[^"]*"', r"\1", svg, count=1)
        svg = re.sub(r'(<svg[^>]*?)\s(width|height)="[^"]*"', r"\1", svg, count=1)
        return svg


# --- slide content ---------------------------------------------------------------------------

def season(turn):
    return f"{'Spring' if turn % 2 == 0 else 'Autumn'} {1901 + turn // 2}"


def power_dot(cid):
    return f'<span class="dot p{cid}" aria-hidden="true"></span>'


def chat_html(messages):
    if not messages:
        return '<p class="empty">No press was sent in this phase.</p>'
    rows = []
    for m in messages:
        frm, to = int(m["fromCountryID"]), int(m["toCountryID"])
        when = datetime.fromtimestamp(m["timeSent"], tz=timezone.utc).strftime("%H:%M:%S")
        if to == 0:
            audience = '<span class="chip chip-public">Public</span> to everyone'
        else:
            audience = f'<span class="chip chip-private">Private</span> to <b class="name p{to}">{NAMES[to]}</b>'
        rows.append(
            f'<li class="msg{" private" if to else ""}">'
            f'<span class="avatar p{frm}" aria-hidden="true">{SHORT[frm][0]}</span>'
            f'<div class="msg-body"><div class="msg-head"><b class="name p{frm}">{NAMES[frm]}</b> {audience}'
            f'<time>{when}</time></div><p>{html.escape(html.unescape(m["message"]))}</p></div></li>')
    return f'<ol class="chat">{"".join(rows)}</ol>'


def centre_counts(owners):
    counts = {c: 0 for c in POWER}
    for owner in owners.values():
        if owner:
            counts[owner] = counts.get(owner, 0) + 1
    return counts


def resolution_html(r, movement, retreats, before, after):
    """Per-power outcome list: centre change, bounced moves, dislodgements and their retreats."""
    retreat_of = {o["terrID"]: o for o in retreats}
    blocks = []
    for cid in POWER:
        events = []
        for o in movement:
            if int(o["countryID"]) != cid:
                continue
            if o["type"] == "Move" and not o["success"]:
                events.append(f'<li class="bad">{r.order_text(o)} <em>bounced</em></li>')
            if o.get("dislodged"):
                follow = retreat_of.get(o["terrID"])
                fate = r.order_text(follow).split(" ", 2)[-1] if follow else "disbanded (no retreat)"
                events.append(f'<li class="bad">{"A" if o["unitType"] == "Army" else "F"} {r.label(o["terrID"])} '
                              f'<em>dislodged</em>, {html.escape(fate)}</li>')
            if o["type"] == "Move" and o["success"]:
                events.append(f'<li>{r.order_text(o)}</li>')
        b, a = before.get(cid, 0), after.get(cid, 0)
        if not b and not a and not events:
            continue
        delta = a - b
        sign = f'<span class="delta {"up" if delta > 0 else "down"}">{delta:+d}</span>' if delta else ""
        count = f"{b} → {a} centres" if delta else f"{a} centres"
        blocks.append(f'<section class="power-result"><h3>{power_dot(cid)}{NAMES[cid]} '
                      f'<span class="sc">{count}</span>{sign}</h3>'
                      f'<ul>{"".join(events) or "<li class=quiet>All units held</li>"}</ul></section>')
    return "".join(blocks)


def adjustment_html(r, orders):
    if not orders:
        return '<p class="empty">No builds or disbands.</p>'
    rows = []
    for cid in POWER:
        mine = [o for o in orders if int(o["countryID"]) == cid and o["type"] != "Wait"]
        if mine:
            items = "".join(f"<li>{r.order_text(o)}</li>" for o in mine)
            rows.append(f'<section class="power-result"><h3>{power_dot(cid)}{NAMES[cid]}</h3><ul>{items}</ul></section>')
    return "".join(rows) or '<p class="empty">No builds or disbands.</p>'


def final_owners(r, entry):
    """Final SC ownership: the Finished entry predates the last autumn's captures."""
    owners = r.owners(entry["centers"])
    for u in entry["units"]:
        prov = r.province(u["terrID"])
        if prov in r.supply and not u.get("retreating"):
            owners[prov] = int(u["countryID"])
    return owners


def build_slides(game, r):
    phases = [p for p in game["phases"]]
    slides = []

    def next_settled(i):
        """Index of the first entry after i that is not a retreat phase."""
        j = i + 1
        while j < len(phases) and phases[j]["phase"] == "Retreats":
            j += 1
        return j

    def board(entry):
        if entry["phase"] == "Finished":
            return entry["units"], final_owners(r, entry)
        return entry["units"], r.owners(entry["centers"])

    for i, p in enumerate(phases):
        turn, kind = p["turn"], p["phase"]
        if kind not in ("Diplomacy", "Builds"):
            continue
        press = [m for m in game["messages"] if m["turn"] == turn and m.get("phase", "Diplomacy") == kind]
        units, owners = board(p)
        j = next_settled(i)
        after_units, after_owners = board(phases[j]) if j < len(phases) else (units, owners)
        if kind == "Diplomacy":
            retreats = [o for k in range(i + 1, j) for o in phases[k]["orders"]]
            slides.append({"phase": season(turn), "kind": "Orders", "turn": turn,
                           "side_title": "Press", "side": chat_html(press),
                           "map": r.render(units, owners, turn, p["orders"]),
                           "note": f"{len(p['orders'])} orders, as adjudicated"})
            slides.append({"phase": season(turn), "kind": "Resolution", "turn": turn,
                           "side_title": "What happened",
                           "side": resolution_html(r, p["orders"], retreats, centre_counts(owners),
                                                   centre_counts(after_owners)),
                           "map": r.render(after_units, after_owners, turn),
                           "note": "after adjudication" + (" and retreats" if retreats else "")})
        else:
            year = 1901 + turn // 2
            slides.append({"phase": f"Winter {year}", "kind": "Builds", "turn": turn,
                           "side_title": "Press", "side": chat_html(press),
                           "map": r.render(units, owners, turn), "note": "positions before builds"})
            slides.append({"phase": f"Winter {year}", "kind": "Resolution", "turn": turn,
                           "side_title": "Builds and disbands", "side": adjustment_html(r, p["orders"]),
                           "map": r.render(after_units, after_owners, turn), "note": "after builds"})
    final = phases[-1]
    units, owners = board(final)
    slides.append({"phase": "Final", "kind": "Results", "turn": final["turn"], "side_title": "Standings",
                   "side": results_html(game, centre_counts(owners)), "map": r.render(units, owners, final["turn"]),
                   "note": "final positions"})
    return slides


def results_html(game, counts):
    res = game["results"]
    members = {int(m["countryID"]): int(m["supplyCenterNo"]) for m in res.get("members", [])}
    scores = {int(country): res["scores"][slot] for slot, country in enumerate(res.get("countries") or [])}
    seats = {s["country"]: s for s in game["seats"].values() if s.get("country")}
    policies = sorted({s.get("policy") or "?" for s in seats.values()})
    shared_policy = len(policies) == 1
    order = sorted(POWER, key=lambda c: (-scores.get(c, 0), -members.get(c, counts.get(c, 0))))
    rows = []
    for rank, cid in enumerate(order, 1):
        seat = seats.get(cid, {})
        policy = "" if shared_policy else f'<div class="mono sub">{html.escape(seat.get("policy") or "—")}</div>'
        spend = f"${seat['llm_cost']:.3f}" if seat.get("llm_calls") else "—"
        calls = f'<div class="sub">{seat["llm_calls"]} calls</div>' if seat.get("llm_calls") else ""
        rows.append(f'<tr><td class="num">{rank}</td><td class="power">{power_dot(cid)}{NAMES[cid]}{policy}</td>'
                    f'<td class="num">{members.get(cid, counts.get(cid, 0))}</td>'
                    f'<td class="num">{scores.get(cid, 0):.3f}</td><td class="num">{spend}{calls}</td></tr>')
    total = sum(s.get("llm_cost", 0.0) for s in game["seats"].values())
    who = f'Every seat played <span class="mono">{html.escape(policies[0])}</span>. ' if shared_policy else ""
    return (f'<p class="outcome">Game <b>{html.escape(res.get("outcome", "?"))}</b> '
            f'({html.escape(res.get("reason", "").replace("_", " "))}). {who}'
            f'Score is each survivor\'s share of centres squared; an even split is 1/7 = 0.143.</p>'
            f'<table class="standings"><thead><tr><th class="num">#</th><th>Power</th><th class="num">Centres</th>'
            f'<th class="num">Score</th><th class="num">LLM spend</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
            f'<p class="foot">Total LLM spend for this game: ${total:.3f}.</p>')


# --- page ----------------------------------------------------------------------------------

CSS = """
:root{--bg:#fffdf4;--surface:#fffaf0;--surface-alt:#f8f6ef;--fg:#111827;--fg-subtle:#555555;--fg-muted:#6b6560;
--ink-navy:#1a3875;--ink-sage:#5d6d41;--ink-terracotta:#945637;--ink-gold:#80601f;--accent:#5573a0;--accent-soft:#eef2f7;
--border:#e4dac8;--border-strong:#d4c9b5;--border-subtle:#f0ebe1;
--p1:#6d5a9c;--p2:#3f6f9f;--p3:#5d7f3e;--p4:#5f5953;--p5:#a3533a;--p6:#a8862a;--p7:#7d8794;
--t1:#ddd5ec;--t2:#d3e0ee;--t3:#dbe6cf;--t4:#dedad5;--t5:#efd6cc;--t6:#efe3c2;--t7:#e3e6ea;
--serif:'Merriweather',Georgia,serif;--sans:'Merriweather Sans','Helvetica Neue',sans-serif;--mono:ui-monospace,'SF Mono',Menlo,monospace}
*{box-sizing:border-box}html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:14px;line-height:1.5;display:flex;flex-direction:column;overflow:hidden}
header.bar{display:flex;align-items:baseline;gap:16px;padding:12px 20px 10px;border-bottom:2px solid var(--border-strong)}
header.bar h1{font-family:var(--serif);font-size:18px;margin:0}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--fg-subtle)}
header.bar .where{font-family:var(--serif);font-weight:700;font-size:16px;color:var(--ink-navy)}
header.bar .spacer{flex:1}
.counter{font-family:var(--mono);font-size:12px;color:var(--fg-muted)}
button{font:inherit;font-weight:600;font-size:13px;border-radius:3px;padding:5px 12px;cursor:pointer;background:var(--surface);color:var(--fg);border:1px solid var(--border-strong)}
button:hover{background:var(--surface-alt)}button:active{background:var(--border-subtle)}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button.primary{background:#0e2758;color:#fffdf4;border-color:#0a1c42}button.primary:hover{background:#1a3875}
main{flex:1;min-height:0;position:relative}
.slide{position:absolute;inset:0;display:none;grid-template-columns:minmax(320px,400px) 1fr;min-height:0}
.slide.on{display:grid}
aside{border-right:1px solid var(--border);background:var(--surface);display:flex;flex-direction:column;min-height:0}
aside h2{font-family:var(--serif);font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-navy);margin:0;padding:14px 16px 8px}
.side{overflow-y:auto;padding:0 16px 16px;min-height:0;flex:1;scrollbar-width:thin;scrollbar-color:rgba(148,86,55,.25) transparent}
.figure{display:flex;flex-direction:column;min-width:0;min-height:0;padding:12px 20px}
.figure .caption{display:flex;gap:10px;align-items:baseline;padding-bottom:6px}
.figure .kind{font-family:var(--serif);font-weight:700;font-size:20px}
.mapwrap{flex:1;min-height:0;display:flex;align-items:center;justify-content:center}
.mapwrap svg{max-width:100%;max-height:100%;width:auto;height:100%}
.chat{list-style:none;margin:0;padding:0}
.msg{display:grid;grid-template-columns:32px 1fr;gap:10px;padding:8px 0;border-bottom:1px solid var(--border-subtle)}
.msg.private .msg-body p{background:var(--surface-alt)}
.avatar{width:32px;height:32px;border-radius:50%;display:grid;place-items:center;color:#fffdf4;font-weight:700;font-size:13px}
.msg-head{font-size:12px;color:var(--fg-subtle);display:flex;flex-wrap:wrap;gap:4px 6px;align-items:baseline}
.msg-head time{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--fg-muted)}
.msg-body p{margin:4px 0 0;padding:6px 9px;border-radius:6px;font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere}
.name{font-weight:700}
.chip{display:inline-block;font-size:9.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;border-radius:999px;padding:1px 7px}
.chip-private{background:rgba(128,96,31,.14);color:var(--ink-gold)}
.chip-public{background:rgba(85,115,160,.16);color:var(--ink-navy)}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px;vertical-align:baseline}
.power-result{padding:10px 0;border-bottom:1px solid var(--border-subtle)}
.power-result h3{font-size:14px;margin:0 0 4px;display:flex;align-items:center;gap:6px}
.power-result .sc{font-weight:400;color:var(--fg-subtle);font-size:12px;font-family:var(--mono)}
.delta{font-family:var(--mono);font-size:12px;font-weight:700}.delta.up{color:var(--ink-sage)}.delta.down{color:var(--ink-terracotta)}
.power-result ul{margin:0;padding-left:18px;font-size:13px}.power-result li{margin:2px 0}
.power-result li.bad em{color:var(--ink-terracotta);font-style:normal;font-weight:700}
li.quiet,.empty{color:var(--fg-muted);font-style:italic}
.empty{border:1px dashed var(--border);padding:12px;border-radius:6px}
table.standings{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
.standings th{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--fg-subtle);text-align:left;border-bottom:2px solid var(--border-strong);padding:6px 4px}
.standings td{padding:7px 4px;border-bottom:1px solid var(--border-subtle)}
.standings td.power{white-space:nowrap}.standings .sub{font-size:11px;color:var(--fg-muted)}
.num{text-align:right;white-space:nowrap;font-family:var(--mono);font-feature-settings:"tnum" 1}.mono{font-family:var(--mono);font-size:11px}
.outcome,.foot{font-size:13px;color:var(--fg-subtle)}
nav.timeline{display:flex;gap:2px;padding:8px 20px 12px;border-top:1px solid var(--border);overflow-x:auto;scrollbar-width:thin}
nav.timeline button{padding:3px 7px;font-size:11px;font-family:var(--mono);font-weight:400;border-color:var(--border);white-space:nowrap}
nav.timeline button[aria-current="true"]{background:var(--accent-soft);border-color:var(--accent);color:var(--ink-navy);font-weight:700}
""" + "".join(f".p{c}{{color:var(--p{c})}}.avatar.p{c},.dot.p{c}{{background:var(--p{c});color:#fffdf4}}" for c in POWER) + """
/* map palette over the diplomacy renderer's classes */
.mapwrap .water{fill:#dbe6ea;stroke:#5a5650;stroke-width:1}.mapwrap .nopower{fill:#f5eedf;stroke:#5a5650;stroke-width:1}
.mapwrap .neutral{fill:#ebe4d4;stroke:#5a5650;stroke-width:1}.mapwrap .impassable{fill:#5f5953;stroke:#3a3633}
.mapwrap .currentnotetext,.mapwrap .currentphasetext,.mapwrap .currentnoterect{display:none}
.mapwrap .supportorder{stroke-width:6;fill:none;stroke-dasharray:5,5}.mapwrap .convoyorder{stroke-dasharray:15,5;stroke-width:6;fill:none}
.mapwrap .shadowdash{stroke-width:10;fill:none;stroke:#111827;opacity:.35}.mapwrap .varwidthorder{fill:none}.mapwrap .varwidthshadow{fill:none;stroke:#111827}
""" + "".join(f".mapwrap .{POWER[c].lower()}{{fill:var(--t{c});stroke:#5a5650;stroke-width:1}}"
              f".mapwrap .unit{POWER[c].lower()}{{fill:var(--p{c});fill-opacity:.95}}" for c in POWER) + """

/* province labels drawn by the renderer (incl_abbrev) */
.mapwrap .labeltext18,.mapwrap .labeltext24{font-family:var(--sans);font-weight:700;font-size:17px;letter-spacing:.04em;fill:#3a3633;text-anchor:middle;
paint-order:stroke;stroke:#fffdf4;stroke-width:3px;stroke-linejoin:round;pointer-events:none}
.mapwrap .labeltext24{font-size:19px;fill:#4d5f74}
/* debug mode */
.debug-toggle{font-size:13px;font-weight:600;display:flex;align-items:center;gap:5px;cursor:pointer}
.debug-toggle input{accent-color:#1a3875;width:15px;height:15px}
#power{font:inherit;font-size:13px;padding:4px 6px;border-radius:3px;border:1px solid var(--border-strong);background:var(--surface);display:none}
body.debug #power{display:inline-block}
aside .debug-panel{display:none;flex-direction:column;min-height:0;flex:1}
body.debug aside .debug-panel{display:flex}body.debug aside .normal{display:none}
aside .normal{display:flex;flex-direction:column;min-height:0;flex:1}
body.debug .slide.on{grid-template-columns:minmax(440px,46%) 1fr}
.trace{font-size:13px}
.wake{border-top:2px solid var(--border-strong);margin-top:12px;padding-top:8px}
.wake:first-child{margin-top:0}
.wake-head{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline}
.wake-head b{font-family:var(--serif);text-transform:capitalize}
.meta{font-family:var(--mono);font-size:11px;color:var(--fg-muted)}
.status-ok{color:var(--ink-sage)}.status-bad{color:var(--ink-terracotta)}
.ev{margin:6px 0}
.ev-model{border-left:2px solid var(--border);padding-left:9px}
.ev-model .text{white-space:pre-wrap;overflow-wrap:anywhere;margin:2px 0}
.ev-call{font-family:var(--mono);font-size:12px;color:var(--ink-navy)}
details{margin:4px 0}summary{cursor:pointer;font-weight:600;font-size:12px;color:var(--fg-subtle)}
summary:hover{color:var(--ink-navy)}summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-family:var(--mono);font-size:11.5px;background:var(--surface-alt);padding:8px;border-radius:6px;margin:4px 0;max-height:420px;overflow-y:auto}
.ev-press{padding:5px 9px;border-radius:6px;background:var(--surface-alt);white-space:pre-wrap;overflow-wrap:anywhere}
.ev-press .who{font-weight:700;font-size:12px}
.ev-error{color:var(--ink-terracotta)}
.trace h3{font-family:var(--serif);font-size:13px;margin:12px 0 4px;color:var(--ink-navy)}
@media (max-width:900px){body.debug .slide.on{grid-template-columns:1fr}.slide.on{grid-template-columns:1fr;grid-template-rows:45% 55%}aside{border-right:0;border-bottom:1px solid var(--border)}
header.bar{flex-wrap:wrap;gap:4px 10px;padding:10px 16px}header.bar>.eyebrow{display:none}header.bar h1{font-size:15px;flex-basis:100%}
.figure{padding:8px 16px}nav.timeline{padding:8px 16px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

JS = """
const slides=[...document.querySelectorAll('.slide')];const ticks=[...document.querySelectorAll('nav.timeline button')];
let i=0;function show(n){i=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,k)=>s.classList.toggle('on',k===i));
if(document.body.classList.contains('debug'))renderTrace(slides[i]);
document.getElementById('where').textContent=slides[i].dataset.phase;document.getElementById('count').textContent=`${i+1} / ${slides.length}`;
ticks.forEach(t=>t.setAttribute('aria-current',String(+t.dataset.slide===i||(+t.dataset.slide<=i&&+t.dataset.end>=i))));
const cur=ticks.find(t=>t.getAttribute('aria-current')==='true');if(cur)cur.scrollIntoView({block:'nearest',inline:'nearest'});
history.replaceState(null,'','#'+(i+1));}
document.getElementById('prev').onclick=()=>show(i-1);document.getElementById('next').onclick=()=>show(i+1);
ticks.forEach(t=>t.onclick=()=>show(+t.dataset.slide));
document.addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key===' '){e.preventDefault();show(i+1)}if(e.key==='ArrowLeft'){e.preventDefault();show(i-1)}
if(e.key==='Home')show(0);if(e.key==='End')show(slides.length-1)});

const TRACES=JSON.parse(document.getElementById('traces').textContent);
const NAMES={1:'England',2:'France',3:'Italy',4:'Germany',5:'Austria',6:'Turkey',7:'Russia'};
const debugBox=document.getElementById('debug'),powerSel=document.getElementById('power');
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined&&text!==null)n.textContent=text;return n}
function details(label,body){const d=el('details');d.append(el('summary',null,label),el('pre',null,body));return d}
function money(x){return x==null?'':'$'+Number(x).toFixed(4)}
function short(v,n){const t=typeof v==='string'?v:JSON.stringify(v);return t&&t.length>n?t.slice(0,n)+'…':t}
function renderEvents(box,events,turnKind){
  let wakeBox=null;const target=()=>wakeBox||box;
  for(const ev of events){
    if(turnKind==='orders'&&['decision','workspace','commitment_verdict'].includes(ev.e))continue;
    if(turnKind==='resolution'&&!['decision','workspace','commitment_verdict'].includes(ev.e))continue;
    if(ev.e==='wake_start'){wakeBox=el('section','wake');const h=el('div','wake-head');
      h.append(el('b',null,ev.kind+' wake'),el('span','meta',`${ev.wake} · up to ${ev.allowed}s · ${ev.unread} unread`));wakeBox.append(h);box.append(wakeBox);continue}
    if(ev.e==='wake'){const ok=ev.status==='ok';const line=el('div','meta');
      line.append(el('span',ok?'status-ok':'status-bad',ev.status),document.createTextNode(` · ${ev.calls} calls · ${ev.seconds}s · ${money(ev.cost)}`));
      target().append(line);if(ev.final)target().append(el('div','ev',`Final: ${ev.final}`));wakeBox=null;continue}
    if(ev.e==='briefing'){target().append(details(`Briefing (${ev.text.length} chars)`,ev.text));continue}
    if(ev.e==='llm_call'){const m=el('div','ev ev-model');
      m.append(el('div','meta',`model · ${ev.status} · in ${ev.tokens[0]} / out ${ev.tokens[1]} / reasoning ${ev.tokens[2]} · ${money(ev.cost)}`));
      if(ev.error)m.append(el('div','ev-error',ev.error));
      if(ev.reasoning)m.append(details('Reasoning',ev.reasoning));
      if(ev.content)m.append(el('div','text',ev.content));
      for(const c of ev.tool_calls||[])m.append(el('div','ev-call','→ '+c.name+'('+short(c.arguments,140)+')'));
      target().append(m);continue}
    if(ev.e==='tool_call'){const err=String(ev.result).startsWith('ERROR');
      const d=details(`${ev.tool}(${short(ev.arguments,80)}) · ${ev.seconds}s${err?' · error':''}`,
        'arguments: '+JSON.stringify(ev.arguments,null,1)+'\\n\\nresult: '+ev.result);if(err)d.querySelector('summary').classList.add('ev-error');
      target().append(d);continue}
    if(ev.e==='press_out'||ev.e==='press_in'){const b=el('div','ev ev-press');
      b.append(el('div','who',ev.e==='press_out'?`→ to ${ev.to}`:`← from ${ev.frm}`),document.createTextNode(ev.text||''));target().append(b);continue}
    if(ev.e==='commitment'){target().append(el('div','ev',`Commitment recorded: ${ev.by} — ${(ev.orders||[]).concat((ev.dmz||[]).map(d=>'no entry into '+d)).join('; ')}${ev.note?' ('+ev.note+')':''}`));continue}
    if(ev.e==='commitment_verdict'){const v=el('div','ev');v.append(el('b',null,ev.by+': '),el('span',ev.verdict==='kept'?'status-ok':'status-bad',ev.verdict));box.append(v);continue}
    if(ev.e==='press_commit'){const c=el('div','ev');c.append(el('b',null,`Committed (expected ${ev.expected} centres): `),document.createTextNode((ev.orders||[]).join(', ')));
      c.append(details('Policy',JSON.stringify(ev.policy,null,1)));target().append(c);continue}
    if(ev.e==='wake_error'){target().append(details('Wake error',ev.where||''));continue}
    if(ev.e==='decision'){box.append(el('h3',null,'Orders played'));
      box.append(el('div','meta',`${ev.rejected} rejected · phase LLM cost ${money(ev.cost)}`),details('Final policy',JSON.stringify(ev.policy,null,1)),details('Search trace counters',JSON.stringify(ev.trace,null,1)));continue}
    if(ev.e==='workspace'){box.append(el('h3',null,'Plan after this phase'),el('pre',null,ev.plan||''));
      for(const [p,t] of Object.entries(ev.notes||{}))box.append(details('Notes on '+p,t));continue}
  }
}
function renderTrace(slide){
  const title=slide.querySelector('.trace-title'),box=slide.querySelector('.trace');box.replaceChildren();
  const power=powerSel.value,turn=slide.dataset.turn,kind=slide.dataset.kind;
  title.textContent=`${NAMES[power]||'—'} · agent trace`;
  if(slide.dataset.winter==='1'){box.append(el('p','empty','Builds and disbands are chosen by DumbBot. The agent is not woken in winter.'));return}
  const events=(TRACES[power]||{})[turn]||[];
  if(kind==='Results'){const all=Object.values(TRACES[power]||{}).flat();
    const calls=all.filter(e=>e.e==='llm_call'),cost=calls.reduce((a,e)=>a+(e.cost||0),0);
    box.append(el('p',null,`${calls.length} model calls, ${money(cost)} for the game.`));
    const ws=all.filter(e=>e.e==='workspace').pop();if(ws)renderEvents(box,[ws],'resolution');return}
  renderEvents(box,events,kind==='Orders'?'orders':'resolution');
  if(!box.childElementCount)box.append(el('p','empty','No agent activity recorded for this phase.'));
}
function applyDebug(){document.body.classList.toggle('debug',debugBox.checked);if(debugBox.checked)renderTrace(slides[i]);
  try{localStorage.setItem('wd-debug',debugBox.checked?'1':'');localStorage.setItem('wd-power',powerSel.value)}catch(e){}}
debugBox.onchange=applyDebug;powerSel.onchange=applyDebug;
try{if(localStorage.getItem('wd-power'))powerSel.value=localStorage.getItem('wd-power');debugBox.checked=!!localStorage.getItem('wd-debug')&&!debugBox.disabled}catch(e){}
window.addEventListener('hashchange',()=>{const n=(parseInt(location.hash.slice(1))||1)-1;if(n!==i)show(n)});
show((parseInt(location.hash.slice(1))||1)-1);applyDebug();
"""


def page(title, slides, traces):
    blocks, ticks, start = [], [], {}
    for n, s in enumerate(slides):
        start.setdefault(s["phase"], n)
        blocks.append(
            f'<section class="slide" data-phase="{html.escape(s["phase"])}" data-turn="{s["turn"]}" '
            f'data-kind="{s["kind"]}" data-winter="{int(s["phase"].startswith("Winter"))}" '
            f'aria-label="{html.escape(s["phase"])} {s["kind"]}">'
            f'<aside><div class="normal"><h2>{s["side_title"]}</h2><div class="side">{s["side"]}</div></div>'
            f'<div class="debug-panel"><h2 class="trace-title"></h2><div class="side trace"></div></div></aside>'
            f'<div class="figure"><div class="caption"><span class="kind">{s["kind"]}</span>'
            f'<span class="eyebrow">{html.escape(s["phase"])} · {html.escape(s["note"])}</span></div>'
            f'<div class="mapwrap">{s["map"]}</div></div></section>')
    for phase, first in start.items():
        last = max(n for n, s in enumerate(slides) if s["phase"] == phase)
        label = phase.replace("Spring ", "S").replace("Autumn ", "A").replace("Winter ", "W")
        ticks.append(f'<button data-slide="{first}" data-end="{last}" title="{html.escape(phase)}">{label}</button>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&family=Merriweather+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header class="bar"><span class="eyebrow">webDiplomacy replay</span><h1>{html.escape(title)}</h1>
<span class="where" id="where"></span><span class="spacer"></span><span class="counter" id="count"></span>
<label class="debug-toggle"><input type="checkbox" id="debug"{" disabled" if not traces else ""}> Debug</label>
<select id="power" aria-label="Power to trace">{"".join(f'<option value="{c}">{NAMES[c]}</option>' for c in sorted(traces))}</select>
<button id="prev" aria-label="Previous slide">← Prev</button><button id="next" class="primary" aria-label="Next slide">Next →</button></header>
<main>{"".join(blocks)}</main><nav class="timeline" aria-label="Phases">{"".join(ticks)}</nav>
<script type="application/json" id="traces">{json.dumps(traces).replace("</", "<\\/")}</script>
<script>{JS}</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--out", help="output HTML (default: EPISODE/viewer.html)")
    ap.add_argument("--title")
    args = ap.parse_args()
    ep = Path(args.episode)
    game = load_episode(ep)
    renderer = MapRenderer(game["variant"])
    slides = build_slides(game, renderer)
    out = Path(args.out) if args.out else ep / "viewer.html"
    out.write_text(page(args.title or f"Episode {ep.name}", slides, game["traces"]))
    print(f"{out} ({len(slides)} slides, {out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
