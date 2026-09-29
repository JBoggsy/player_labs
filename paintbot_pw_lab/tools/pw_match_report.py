#!/usr/bin/env python3
"""One-page Paintbot PW match report per episode (lab tool T10): Ink & Print HTML + JSON.

For each verified episode: the result and Elo outcome score, the glory composition, a
timeline, per-seat metrics (pw_metrics), the top moments (first captures, hearts lost,
kill bursts, elimination) with a movement panel each (pw_viz), and replay links.
Failed episodes are listed and make the exit code 1; no report is written for them.

  uv run python paintbot_pw_lab/tools/pw_match_report.py EPISODE_DIR [MORE ...] [--out DIR]

Output (default): <episode dir>/pw_report/ for hosted episodes, NAME.pw_report/ beside a
local NAME.replay: report.html, report.json, timeline.png(+json), moment_N.png(+json).
Contract: paintbot_pw_lab/docs/tools/pw_match_report.md.
"""
from __future__ import annotations

import html
import json
import math
import sys
from pathlib import Path
from urllib.parse import quote

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pw_cli  # noqa: E402
import pw_episodes  # noqa: E402
import pw_mapdata  # noqa: E402
import pw_metrics  # noqa: E402
import pw_viz  # noqa: E402
from pw_viz import clock  # noqa: E402

# ---------------------------------------------------------------- named thresholds
TOP_MOMENTS = 6               # moments shown (first captures are always included)
KILL_BURST_GAP_TICKS = 72     # enemy kills by one team no more than 3 s apart form one burst
KILL_BURST_MIN_KILLS = 3      # ...and a burst needs at least this many kills
MOMENT_BEFORE_TICKS = 240     # movement panel: 10 s before the moment
MOMENT_AFTER_TICKS = 48       # ...and 2 s after
MOMENT_ZOOM_HALF = 1800       # panel half-width in world units around the moment (at least)
MOMENT_ZOOM_PAD = 500         # margin around a moment's victims and killers when they spread wider
# Ranking weight ("swing") per kind. A heuristic order for choosing what to show, not a
# measured win-probability change (that is plan T14).
SWING_ELIMINATION = 10
SWING_HEART_LOST = 2          # the heart difference moves by 2
SWING_FIRST_CAPTURE = 1

EPISODE_PAGE = "https://softmax.com/observatory/v2?tab=episode-requests&detail=episode-request:{ereq}"
REPLAY_WRAPPER = "https://softmax.com/observatory/coworld-replays/{coworld_id}?replay_uri={uri}"
TEAM = {0: "Ember", 1: "Azure"}


# ---------------------------------------------------------------- moments

def _heart_pos(ep, heart: int) -> tuple[float, float]:
    return tuple(ep.meta["hearts"][heart]["pos"])


def kill_bursts(kills: pd.DataFrame) -> list[dict]:
    """Runs of enemy kills by one team with gaps <= KILL_BURST_GAP_TICKS, at least KILL_BURST_MIN_KILLS long."""
    enemy = kills[kills.seat.notna() & ~kills.friendly.astype(bool) & ~kills["self"].astype(bool)]
    bursts = []
    for team, rows in enemy.groupby("team"):
        rows = rows.sort_values("t")
        run: list = []
        for row in [*rows.itertuples(), None]:
            if row is not None and (not run or row.t - run[-1].t <= KILL_BURST_GAP_TICKS):
                run.append(row)
                continue
            if len(run) >= KILL_BURST_MIN_KILLS:
                start, end = int(run[0].t), int(run[-1].t)
                lost = kills[(kills.victim_team == team) & (kills.t >= start) & (kills.t <= end)]
                bursts.append({"team": int(team), "start": start, "end": end, "kills": len(run), "lost": len(lost),
                               "victims": [int(r.victim) for r in run], "killers": sorted({int(r.seat) for r in run}),
                               "points": [[float(r.victim_x), float(r.victim_z)] for r in run],
                               "x": sum(r.victim_x for r in run) / len(run), "z": sum(r.victim_z for r in run) / len(run)})
            run = [row] if row is not None else []
    return bursts


def _killer_points(ep, burst: dict) -> list[list[float]]:
    """Where the killers stood for each fatal blow of the burst (damage rows with killed)."""
    damage = ep["damage"]
    fatal = damage[damage.killed.astype(bool) & damage.seat.isin(burst["killers"])
                   & damage.t.between(burst["start"], burst["end"]) & damage.attacker_x.notna()]
    return [[float(r.attacker_x), float(r.attacker_z)] for r in fatal.itertuples()]


def moment_bbox(moment: dict, mapdata) -> tuple[float, float, float, float]:
    """A square-ish box around the moment that also covers its points (victims and killers)."""
    xs = [moment["x"], *(p[0] for p in moment.get("points", []))]
    zs = [moment["z"], *(p[1] for p in moment.get("points", []))]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    half = max(MOMENT_ZOOM_HALF, (max(xs) - min(xs)) / 2 + MOMENT_ZOOM_PAD, (max(zs) - min(zs)) / 2 + MOMENT_ZOOM_PAD)
    return pw_viz.bbox_around(cx, cz, half, mapdata)


def find_moments(ep) -> list[dict]:
    """Candidate moments with an explicit swing weight; the caller picks the top ones."""
    moments = []
    caps = ep["captures"]
    completes = caps[caps.kind == "capture_complete"].sort_values("t")
    first_rows = {int(completes[completes.team == team].index[0]) for team in (0, 1) if (completes.team == team).any()}
    for index, row in completes.iterrows():
        team = int(row.team)
        taken = pd.notna(row.previous_owner) and int(row.previous_owner) in (0, 1) and int(row.previous_owner) != team
        first = index in first_rows
        if not (taken or first):
            continue
        x, z = _heart_pos(ep, int(row.heart))
        who = f" (seat {int(row.seat)})" if pd.notna(row.seat) else ""
        what = f"took H{int(row.heart)} from {TEAM[int(row.previous_owner)]}" if taken else f"captured H{int(row.heart)}"
        moments.append({"kind": "first_capture" if first else "heart_lost", "t": int(row.t), "team": team,
                        "swing": SWING_HEART_LOST if taken else SWING_FIRST_CAPTURE,
                        "title": f"{TEAM[team]} {what}{who}" + (": its first capture" if first else ""),
                        "x": x, "z": z, "from": int(row.t) - MOMENT_BEFORE_TICKS, "to": int(row.t) + MOMENT_AFTER_TICKS})
    for burst in kill_bursts(ep["kills"]):
        span = (burst["end"] - burst["start"]) / pw_viz.TICK_RATE
        moments.append({"kind": "kill_burst", "t": burst["start"], "team": burst["team"],
                        "swing": burst["kills"] - burst["lost"],
                        "title": f"{TEAM[burst['team']]} killed {burst['kills']} in {span:.1f} s (lost {burst['lost']})",
                        "x": burst["x"], "z": burst["z"], "points": burst["points"] + _killer_points(ep, burst),
                        "from": burst["start"] - MOMENT_BEFORE_TICKS // 2,
                        "to": burst["end"] + MOMENT_AFTER_TICKS})
    episode = ep["episodes"].iloc[0]
    per_team = int(episode.seats) // 2
    for team in (0, 1):
        if int(episode[f"cogs_out_{team}"]) == per_team:
            ts = ep["team_states"]
            out_at = ts[ts[f"cogs_out_{team}"] == per_team].t
            t = int(out_at.min()) if len(out_at) else int(episode.ticks)
            last = ep["kills"][ep["kills"].victim_team == team].sort_values("t")
            x, z = (float(last.iloc[-1].victim_x), float(last.iloc[-1].victim_z)) if len(last) else _heart_pos(ep, team)
            moments.append({"kind": "elimination", "t": t, "team": 1 - team, "swing": SWING_ELIMINATION,
                            "title": f"{TEAM[team]} eliminated: every cog out of lives",
                            "x": x, "z": z, "from": t - MOMENT_BEFORE_TICKS, "to": t + 1})
    return moments


def top_moments(moments: list[dict], limit: int = TOP_MOMENTS) -> list[dict]:
    """First captures always; the rest by swing (ties: earlier first); then shown in match order."""
    firsts = [m for m in moments if m["kind"] == "first_capture"]
    rest = sorted((m for m in moments if m["kind"] != "first_capture"), key=lambda m: (-m["swing"], m["t"]))
    chosen = sorted(firsts + rest[:max(0, limit - len(firsts))], key=lambda m: m["t"])
    for rank, moment in enumerate(chosen, 1):
        moment["rank"] = rank
    return chosen


# ---------------------------------------------------------------- links

def replay_links(ep, tick: int | None = None, viewer_base: str | None = None) -> dict:
    """Links for a hosted episode; empty for local tapes."""
    if ep.source.kind != "hosted" or not ep.source.episode_json:
        return {}
    info = json.loads(ep.source.episode_json.read_text())
    links = {}
    if str(info.get("id", "")).startswith("ereq_"):
        links["episode_page"] = EPISODE_PAGE.format(ereq=info["id"])
    replay_url = info.get("replay_url")
    if replay_url:
        links["replay_url"] = replay_url
        if info.get("coworld_id"):
            wrapper = REPLAY_WRAPPER.format(coworld_id=info["coworld_id"], uri=quote(replay_url, safe=""))
            links["observatory_replay"] = wrapper + (f"&t={tick}" if tick is not None else "")
        query = f"?replay={quote(replay_url, safe='')}" + (f"&t={tick}" if tick is not None else "")
        links["viewer_query"] = query
        if viewer_base:
            links["viewer"] = viewer_base.rstrip("?") + query
    return links


# ---------------------------------------------------------------- figures

def moment_panel(ep, moment: dict, out: Path) -> dict:
    mapdata = pw_mapdata.map_for_episode(ep.meta, tag=ep.tag)
    end = int(ep["episodes"].iloc[0].ticks)
    t0, t1 = max(0, moment["from"]), min(end, moment["to"])
    bbox = moment_bbox(moment, mapdata)
    states = ep["states"]
    near = states[(states.t >= t0) & (states.t <= t1) & states.alive.astype(bool)
                  & (states.x.between(bbox[0], bbox[2])) & (states.z.between(bbox[1], bbox[3]))]
    seats = sorted(int(s) for s in near.seat.unique()) or pw_viz.select_seats(ep)
    fig, ax = plt.subplots(figsize=(7.2, 5.4), facecolor=pw_viz.PAPER)
    data = pw_viz.movement_panel(ax, ep, mapdata, t0, t1, seats, bbox=bbox, label_size=8)
    ax.plot(moment["x"], moment["z"], marker="o", markersize=26, markerfacecolor="none",
            markeredgecolor=pw_viz.INK, markeredgewidth=0.8, ls="none", zorder=10)
    ax.set_title(f"{moment['rank']}.  {clock(t0)}–{clock(t1)}", fontsize=9, color=pw_viz.INK, loc="left",
                 fontfamily="serif", fontweight="bold")
    fig.tight_layout()
    data["moment"] = moment
    pw_viz._save(fig, out, data)
    return data


# ---------------------------------------------------------------- report data

def _num(value, digits: int = 0):
    if value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NA:
        return None
    return round(float(value), digits) if digits else int(value) if float(value).is_integer() else float(value)


def report_data(ep, viewer_base: str | None = None) -> dict:
    seats = pw_metrics.seat_metrics(ep)
    teams = pw_metrics.team_metrics(ep, seats)
    policies = pw_metrics.policy_metrics(ep, seats)
    episode = ep["episodes"].iloc[0]
    winner = int(episode.winner)
    chosen = top_moments(find_moments(ep))
    for moment in chosen:
        moment["links"] = replay_links(ep, moment["t"], viewer_base)
    team_rows = []
    for t in teams.itertuples():
        team_rows.append({
            "team": int(t.team), "name": TEAM[int(t.team)], "policies": t.policy_keys,
            "policy_names": sorted(set(seats[seats.team == t.team].policy_name.dropna())),
            "result": t.result, "glory": _num(t.glory_ours), "elo_outcome": _num(t.elo_outcome, 3),
            "glory_initial": _num(t.glory_initial), "glory_countdown": _num(t.glory_countdown),
            **{f"glory_{k}": _num(getattr(t, f"glory_{k}")) for k in pw_metrics.GLORY_KINDS},
            "glory_settled_loss": _num(t.glory_settled_loss), "meter_points": _num(t.meter_points, 1),
            "hearts_held_mean": _num(t.hearts_held_mean, 2), "hearts_held_end": _num(t.hearts_held_end),
            "first_capture_tick": _num(t.first_capture_tick), "captures": _num(t.captures_completed),
            "kills": _num(t.kills), "deaths": _num(t.deaths), "gun_enemy_accuracy": _num(t.gun_enemy_accuracy, 3),
            "cogs_out_end": _num(t.cogs_out_end), "team_lives_end": _num(t.team_lives_end)})
    seat_columns = ["seat", "team", "policy_name", "kills", "deaths", "kd", "shots", "gun_enemy_accuracy",
                    "dealt_hp_enemy", "taken_hp", "captures_completed", "pickups_medkit", "alive_share",
                    "heart_reach_share", "idle_share", "stuck_ticks", "vm_disabled_suspect"]
    seat_rows = [{c: (_num(r[c], 3) if isinstance(r[c], float) and not float(r[c]).is_integer() else
                      _num(r[c]) if isinstance(r[c], float) else r[c]) for c in seat_columns}
                 for r in seats.sort_values(["team", "seat"]).to_dict("records")]
    for row in seat_rows:
        row["vm_disabled_suspect"] = bool(row["vm_disabled_suspect"])
        row["team"], row["seat"] = int(row["team"]), int(row["seat"])
    policy_rows = [{"policy_key": p.policy_key, "policy_name": p.policy_name, "seats": int(p.seats),
                    "team": None if pd.isna(p.team) else int(p.team), "result": p.result,
                    "elo_outcome": _num(p.elo_outcome, 3)} for p in policies.itertuples()]
    return {
        "episode_id": ep.episode_id, "source": ep.source.kind, "path": str(episode.path),
        "coworld_version": episode.coworld_version if pd.notna(episode.coworld_version) else None,
        "engine_release": episode.engine_release, "rules": int(episode.rules),
        "map": episode["map"] or "heartwick", "ticks": int(episode.ticks), "tick_rate": int(episode.tick_rate),
        "winner": winner, "winner_name": TEAM.get(winner, "draw"), "decided_by": _decided_by(ep, chosen),
        "teams": team_rows, "policies": policy_rows, "seats": seat_rows, "moments": chosen,
        "links": replay_links(ep, None, viewer_base),
        "evidence": {"hash_verified": bool(ep.summary.get("verified")), "results_check": episode.results_check,
                     "notes": episode.notes or None, "state_every": int(episode.state_every),
                     "thresholds": {"KILL_BURST_GAP_TICKS": KILL_BURST_GAP_TICKS,
                                    "KILL_BURST_MIN_KILLS": KILL_BURST_MIN_KILLS,
                                    "ELO_MARGIN_SCALE": pw_metrics.ELO_MARGIN_SCALE,
                                    "STUCK_MAX_DISPLACEMENT": pw_metrics.STUCK_MAX_DISPLACEMENT,
                                    "VM_DISABLED_MIN_IDLE_TICKS": pw_metrics.VM_DISABLED_MIN_IDLE_TICKS}},
    }


def _decided_by(ep, moments: list[dict]) -> str:
    episode = ep["episodes"].iloc[0]
    winner = int(episode.winner)
    if winner not in (0, 1):
        return "draw: equal meters at the time limit"
    if int(episode[f"cogs_out_{1 - winner}"]) == int(episode.seats) // 2:
        return "elimination (the survivor's meter is filled to the target)"
    if int(episode[f"meter_ticks_{winner}"]) >= int(episode.meter_target_ticks):
        return "meter reached the target"
    return "higher meter at the time limit"


# ---------------------------------------------------------------- HTML

CSS = """
:root { --bg:#fffdf4; --surface:#fffaf0; --fg:#111827; --fg-subtle:#555555; --fg-muted:#6b6560;
  --ink-navy:#1a3875; --ink-sage:#5d6d41; --ink-terracotta:#945637; --border:#e4dac8;
  --border-strong:#d4c9b5; --ember:#b4532a; --azure:#1f4c9a; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 "Merriweather Sans", system-ui, sans-serif; }
main { max-width:1000px; margin:0 auto; padding:32px 16px 64px; }
h1 { font:700 1.7rem/1.25 Merriweather, Georgia, serif; margin:.2rem 0 .6rem; }
h2 { font:700 .82rem/1.3 Merriweather, Georgia, serif; text-transform:uppercase; letter-spacing:.12em;
  color:var(--ink-navy); margin:2.6rem 0 .8rem; padding-bottom:.35rem; border-bottom:2px solid var(--border-strong); }
.eyebrow { font-size:.7rem; font-weight:700; text-transform:uppercase; letter-spacing:.1em; color:var(--fg-subtle); }
.lead { font-size:1.05rem; max-width:62ch; }
.meta, .note { color:var(--fg-muted); font-size:.8rem; }
.mono, td.num { font-family: ui-monospace, Menlo, monospace; font-feature-settings:"tnum" 1; }
table { border-collapse:collapse; width:100%; font-size:.8rem; }
th { text-align:left; font-size:.66rem; text-transform:uppercase; letter-spacing:.08em; color:var(--fg-subtle);
  font-weight:700; border-bottom:2px solid var(--border-strong); padding:6px 8px; white-space:nowrap; }
td { padding:5px 8px; border-bottom:1px solid var(--border); }
td.num, th.num { text-align:right; }
td.policy, td.team { white-space:nowrap; }
tr.team-break td { border-top:2px solid var(--border-strong); }
.dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; vertical-align:baseline; }
.ember { background:var(--ember); } .azure { background:var(--azure); }
.scroll { overflow-x:auto; }
img { max-width:100%; height:auto; display:block; }
figure { margin:0; }
ol.moments { list-style:none; padding:0; margin:0; }
ol.moments > li { display:grid; grid-template-columns: minmax(0,1fr) minmax(0,1.25fr); gap:20px; padding:18px 0;
  border-bottom:1px solid var(--border); }
.moment-title { font:700 1rem/1.35 Merriweather, Georgia, serif; margin:.1rem 0 .3rem; }
.rank { font-family:Merriweather, Georgia, serif; color:var(--fg-muted); margin-right:.4rem; }
a { color:var(--ink-navy); text-underline-offset:2px; }
a:hover { color:#5573a0; }
.flag { color:var(--ink-terracotta); font-weight:700; }
@media (max-width: 720px) { ol.moments > li { grid-template-columns: 1fr; } h1 { font-size:1.35rem; } }
"""


def _cell(value, fmt: str = "{}", dash: str = "–") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return dash
    return html.escape(fmt.format(value))


def _pct(value) -> str:
    return _cell(None if value is None else value * 100, "{:.0f}%")


def _link_list(links: dict) -> str:
    parts = []
    if "episode_page" in links:
        parts.append(f'<a href="{html.escape(links["episode_page"])}">Observatory episode page</a>')
    if "observatory_replay" in links:
        parts.append(f'<a href="{html.escape(links["observatory_replay"])}">watch replay</a>')
    if "viewer" in links:
        parts.append(f'<a href="{html.escape(links["viewer"])}">web viewer at this tick</a>')
    return " · ".join(parts) if parts else '<span class="note">local tape: no hosted replay link</span>'


def render_html(data: dict) -> str:
    teams = {t["team"]: t for t in data["teams"]}
    winner = data["winner"]
    rate = data["tick_rate"]
    if winner in (0, 1):
        win, lose = teams[winner], teams[1 - winner]
        headline = (f"{win['name']} won on {data['decided_by'].split(' (')[0]} at {clock(data['ticks'])}; "
                    f"glory {win['glory']} to {lose['glory']}")
        lead = (f"{win['name']} ({', '.join(win['policy_names']) or 'unnamed'}) beat {lose['name']} "
                f"({', '.join(lose['policy_names']) or 'unnamed'}). The ladder scores this "
                f"{win['elo_outcome']:.3f} for {win['name']} and {lose['elo_outcome']:.3f} for {lose['name']} "
                f"(0.5 + glory margin / {2 * pw_metrics.ELO_MARGIN_SCALE}, clamped to 0–1). "
                f"Meter {win['meter_points']:.0f} to {lose['meter_points']:.0f} points; hearts held on average "
                f"{win['hearts_held_mean']:.2f} to {lose['hearts_held_mean']:.2f}; kills {win['kills']} to {lose['kills']}.")
    else:
        headline = f"Draw at {clock(data['ticks'])}"
        lead = f"Equal meters at the time limit; both teams score 0.5. Glory {teams[0]['glory']} to {teams[1]['glory']}."

    glory_rows = []
    for t in (teams[0], teams[1]):
        awards = " + ".join(f"{t['glory_' + k]} {k.replace('_', ' ')}" for k in pw_metrics.GLORY_KINDS
                            if t.get("glory_" + k))
        glory_rows.append(
            f"<tr><td class='team'><span class='dot {t['name'].lower()}'></span>{t['name']}</td><td>{html.escape(t['result'] or '–')}</td>"
            f"<td class='num'>{_cell(t['glory_initial'])}</td><td class='num'>−{_cell(t['glory_countdown'])}</td>"
            f"<td>{html.escape(awards) or '0 awards'}</td><td class='num'>−{_cell(t['glory_settled_loss'])}</td>"
            f"<td class='num'><b>{_cell(t['glory'])}</b></td><td class='num'>{_cell(t['elo_outcome'], '{:.3f}')}</td></tr>")

    moment_items = []
    for m in data["moments"]:
        moment_items.append(
            f"<li><div><div class='eyebrow'>{html.escape(m['kind'].replace('_', ' '))} · {clock(m['t'])} "
            f"· tick {m['t']}</div><p class='moment-title'><span class='rank'>{m['rank']}.</span>"
            f"{html.escape(m['title'])}</p><p class='note'>Panel: {clock(max(0, m['from']))}–{clock(m['to'])}, "
            f"{m['panel_width']:,} units wide, ring = where it happened. Ranking weight {m['swing']} "
            f"({html.escape(_swing_note(m['kind']))}).</p><p>{_link_list(m.get('links', {}))}</p></div>"
            f"<figure><img src='{html.escape(m['image'])}' alt='Movement around moment {m['rank']}: "
            f"{html.escape(m['title'])}'></figure></li>")
    if not moment_items:
        moment_items.append("<li><p class='note'><i>No captures, kill bursts or eliminations in this match.</i></p></li>")

    seat_rows, last_team = [], None
    for s in data["seats"]:
        css = " class='team-break'" if last_team is not None and s["team"] != last_team else ""
        last_team = s["team"]
        flag = " <span class='flag'>VM?</span>" if s["vm_disabled_suspect"] else ""
        seat_rows.append(
            f"<tr{css}><td class='num'>{s['seat']}</td><td class='policy'><span class='dot {TEAM[s['team']].lower()}'></span>"
            f"{html.escape(str(s['policy_name'] or '–'))}{flag}</td>"
            f"<td class='num'>{_cell(s['kills'])}</td><td class='num'>{_cell(s['deaths'])}</td>"
            f"<td class='num'>{_cell(s['kd'], '{:.2f}')}</td><td class='num'>{_cell(s['shots'])}</td>"
            f"<td class='num'>{_pct(s['gun_enemy_accuracy'])}</td><td class='num'>{_cell(s['dealt_hp_enemy'])}</td>"
            f"<td class='num'>{_cell(s['taken_hp'])}</td><td class='num'>{_cell(s['captures_completed'])}</td>"
            f"<td class='num'>{_pct(s['alive_share'])}</td><td class='num'>{_pct(s['heart_reach_share'])}</td>"
            f"<td class='num'>{_pct(s['idle_share'])}</td><td class='num'>{_cell(s['stuck_ticks'])}</td></tr>")

    ev = data["evidence"]
    links = data["links"]
    provenance = (
        f"Re-simulated with <span class='mono'>{html.escape(data['engine_release'])}</span>, rules {data['rules']}: "
        f"{'every tick hash-checked and the glory identity held' if ev['hash_verified'] else '<b>NOT verified</b>'}. "
        f"Final scores cross-checked against <span class='mono'>{html.escape(ev['results_check'])}</span>."
        + (f" Notes: <span class='mono'>{html.escape(ev['notes'])}</span>." if ev["notes"] else ""))
    link_note = (
        "The Observatory replay link wraps the web viewer; the viewer itself seeks to <span class='mono'>&amp;t=&lt;tick&gt;</span> "
        "(paintbot-pw <span class='mono'>viewer.js</span>), but whether the Observatory wrapper passes <span class='mono'>t</span> "
        "through is <b>unverified</b>: if it opens at the start, scrub to the tick shown. "
        "Episode-page links follow the pattern verified 2026-07-28 and were not re-checked for this report."
        if links else "Local tape: open it with a local viewer; there is no hosted link.")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Match report {html.escape(data['episode_id'][:18])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&family=Merriweather+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><main>
<div class="eyebrow">Paintbot PW · match report · {html.escape(data['map'])} · {data['ticks']:,} ticks ({clock(data['ticks'])})</div>
<h1>{html.escape(headline)}</h1>
<p class="lead">{html.escape(lead)}</p>
<p class="meta"><span class="mono">{html.escape(data['episode_id'])}</span> · coworld {html.escape(str(data['coworld_version'] or 'local'))} · {_link_list(links)}</p>

<h2>Glory</h2>
<div class="scroll"><table>
<thead><tr><th>Team</th><th>Result</th><th class="num">Start</th><th class="num">Countdown</th><th>Awards</th>
<th class="num">Settled away</th><th class="num">Final</th><th class="num">Elo outcome</th></tr></thead>
<tbody>{''.join(glory_rows)}</tbody></table></div>
<p class="note">Final = start − countdown (1 per second) + awards − what settling took (the loser's glory drops to 0).
Awards by kind are exact (deduplicated engine glory events).</p>

<h2>Timeline</h2>
<figure><img src="timeline.png" alt="Meter, glory, kills, captures and heart ownership over the match"></figure>
<p class="note">Numbered dotted lines mark the moments below. Meter and glory are sampled every {ev['state_every']} ticks;
captures, kills and heart ownership are exact.</p>

<h2>Top moments</h2>
<ol class="moments">{''.join(moment_items)}</ol>

<h2>Seats</h2>
<div class="scroll"><table>
<thead><tr><th class="num">Seat</th><th>Policy</th><th class="num">Kills</th><th class="num">Deaths</th><th class="num">K/D</th>
<th class="num">Shots</th><th class="num">Gun acc.</th><th class="num">HP dealt</th><th class="num">HP taken</th>
<th class="num">Captures</th><th class="num">Alive</th><th class="num">At a heart</th><th class="num">Idle</th>
<th class="num">Stuck ticks</th></tr></thead>
<tbody>{''.join(seat_rows)}</tbody></table></div>
<p class="note">Gun acc. = enemy hits / rays fired. Alive = alive ticks / match ticks. At a heart = alive ticks in capture reach
(140 units, line clear). Idle = decision ticks with an empty command. Stuck ticks are sampled and inferred
(moving &lt; {pw_metrics.STUCK_MAX_DISPLACEMENT} units per sample toward an unchanged goal ≥ {pw_metrics.STUCK_MIN_GOAL_DISTANCE} away);
<span class="flag">VM?</span> = empty commands for the last ≥ {pw_metrics.VM_DISABLED_MIN_IDLE_TICKS} alive ticks (inferred).
Definitions: <span class="mono">docs/tools/pw_metrics.md</span>.</p>

<h2>Evidence and links</h2>
<p class="note">{provenance}</p>
<p class="note">{link_note}</p>
<p class="note">Moment ranking is a heuristic for choosing what to show (elimination {SWING_ELIMINATION}, heart taken from the
other team {SWING_HEART_LOST}, kill burst = kills − own losses in the burst, first captures always shown), not a measured
win-probability swing. Kill bursts: ≥ {KILL_BURST_MIN_KILLS} enemy kills by one team, ≤ {KILL_BURST_GAP_TICKS} ticks apart.
Seconds = ticks / {rate}.</p>
</main></body></html>
"""


def _swing_note(kind: str) -> str:
    return {"elimination": "decides the match", "heart_lost": "heart difference moves by 2",
            "kill_burst": "kills minus own losses in the burst",
            "first_capture": "always shown"}.get(kind, "")


# ---------------------------------------------------------------- driver

def default_out(ep) -> Path:
    if ep.source.kind == "hosted":
        return ep.source.cache.parent / "pw_report"
    return ep.source.replay.with_suffix(".pw_report")


def write_report(ep, out_dir: Path, viewer_base: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = report_data(ep, viewer_base)
    pw_viz.plot_timeline(ep, out_dir / "timeline.png", data["moments"])
    for moment in data["moments"]:
        name = f"moment_{moment['rank']}.png"
        panel = moment_panel(ep, moment, out_dir / name)
        moment["panel_width"] = round(panel["bbox"][2] - panel["bbox"][0])
        moment["image"] = name
    data["images"] = ["timeline.png", *[m["image"] for m in data["moments"]]]
    (out_dir / "report.json").write_text(json.dumps(data, indent=1, default=pw_viz._json_default) + "\n")
    (out_dir / "report.html").write_text(render_html(data))
    return out_dir / "report.html"


def build_parser() -> pw_cli.ArgumentParser:
    parser = pw_cli.ArgumentParser("pw_match_report", __doc__, examples=[
        "uv run python paintbot_pw_lab/tools/pw_match_report.py paintbot_pw_lab/episode_data/20260928T214433_* --json",
        "uv run python paintbot_pw_lab/tools/pw_match_report.py EPISODE_DIR --out /tmp/report"])
    parser.add_argument("roots", nargs="+", type=Path, help="episode dirs, batch dirs or NAME.replay files")
    parser.add_argument("--out", type=Path, help="output directory (one episode) or parent directory (several); "
                                                 "default <episode dir>/pw_report/ or NAME.pw_report/")
    parser.add_argument("--viewer-base", help="a paintbot-pw web viewer URL; adds ?replay=<uri>&t=<tick> links")
    parser.add_argument("--tag", help="pw_trace build (default: tools/release.env)")
    return parser


def run_cli(args, report: pw_cli.Report) -> dict:
    batch = pw_episodes.load_batch(args.roots, tag=args.tag)
    report.add_batch(batch)
    episodes = sorted(batch.episodes, key=lambda e: e.episode_id)
    reports = []
    for ep in episodes:
        if args.out is None:
            out_dir = default_out(ep)
        else:
            out_dir = args.out if len(episodes) == 1 else args.out / ep.episode_id.replace(":", "_")
        html_path = write_report(ep, out_dir, args.viewer_base)
        print(f"wrote {html_path}")
        report.output(html_path)
        report.output(Path(html_path).with_name("report.json"))
        reports.append({"episode_id": ep.episode_id, "html": str(html_path),
                        "json": str(Path(html_path).with_name("report.json"))})
    print(f"{len(episodes)} reports, {len(batch.failures)} episodes failed")
    for path, code, message in batch.failures:
        print(f"FAILED [{code}] {path}: {message}  (no report)")
    return {"reports": reports}


def main(argv: list[str] | None = None) -> int:
    return pw_cli.run(build_parser(), run_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
