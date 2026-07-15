#!/usr/bin/env python3
"""Fast batch survey over Vanilla WoW episode artifacts → self-contained HTML report.

The vanilla_wow analogue of crewrift-survey, adapted to this game's evidence reality:
episodes carry `episode.json` (+ `results.json` when the platform retains it) and a
CWREPLAY binary; per-member health signals (login verified, in-world duration, movement
packets, travelled yards, `/say` breadcrumbs) come from the lab's stateless replay
decoder (`cwreplay.py`, imported as a sibling module).

Usage:
  wow_survey.py <episode_dir> [--out survey.html] [--title "..."] [--reasons reasons.json]

Reads every `<episode_dir>/*/episode.json`; writes the HTML report plus a
`<out>.survey.json` sidecar with the per-episode metrics (the machine-readable half).
Ink & Print house style (see crewrift_lab/docs/report-style.md for the canon).
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import statistics
import sys
from pathlib import Path

_CWREPLAY_PATH = Path(__file__).resolve().parent / "cwreplay.py"
_spec = importlib.util.spec_from_file_location("cwreplay", _CWREPLAY_PATH)
cwreplay = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("cwreplay", cwreplay)
_spec.loader.exec_module(cwreplay)


def member_metrics(member) -> dict:
    client = [p for p in member.packets if p.from_client]
    moves = [p for p in client if p.opcode in cwreplay.MOVE_OPCODES_CLIENT]
    travelled = 0.0
    previous: tuple[float, float] | None = None
    for packet in moves:
        info = cwreplay._movement_info(packet)
        if info is None:
            continue
        if previous is not None:
            travelled += ((info["x"] - previous[0]) ** 2 + (info["y"] - previous[1]) ** 2) ** 0.5
        previous = (info["x"], info["y"])
    says = []
    for packet in client:
        if packet.opcode in cwreplay.CHAT_OPCODES:
            text = cwreplay._chat_text(packet)
            if text:
                says.append(text)
    duration_s = 0.0
    if member.packets:
        duration_s = (member.packets[-1].server_ms - member.packets[0].server_ms) / 1000.0
    return {
        "name": member.name,
        "login_verified": any(not p.from_client and p.opcode == 566 for p in member.packets),
        "duration_s": round(duration_s, 1),
        "packets_out": len(client),
        "movement_packets": len(moves),
        "travelled_yd": round(travelled, 1),
        "says": says,
    }


def survey_episode(episode_dir: Path) -> dict | None:
    episode_file = episode_dir / "episode.json"
    if not episode_file.is_file():
        return None
    episode = json.loads(episode_file.read_text(encoding="utf-8"))
    row: dict = {
        "dir": episode_dir.name,
        "episode_id": episode.get("episode_id") or episode.get("id"),
        "job_id": episode.get("job_id"),
        "status": episode.get("status"),
        "variant": episode.get("variant_name"),
        "scores": episode.get("scores"),
        "participants": [
            {
                "slot": p.get("position", p.get("agent_idx", p.get("slot"))),
                "policy": (
                    f"{p['policy_name']}:v{p['version']}"
                    if p.get("policy_name") and p.get("version") is not None
                    else p.get("policy_version_id")
                ),
            }
            for p in episode.get("participants", [])
        ],
        "cost_usd": episode.get("cost_usd"),
        "members": [],
        "flags": [],
    }
    results_file = episode_dir / "results.json"
    row["results_retained"] = results_file.is_file()
    if row["results_retained"]:
        row["results"] = json.loads(results_file.read_text(encoding="utf-8"))
    replay_file = episode_dir / "replay.json"
    if replay_file.is_file():
        try:
            replay = cwreplay.decode_replay(replay_file)
            row["members"] = [member_metrics(m) for m in replay.members]
        except cwreplay.ReplayError as exc:
            row["flags"].append(f"replay undecodable: {exc}")
    else:
        row["flags"].append("no replay downloaded")

    for member in row["members"]:
        if not member["login_verified"]:
            row["flags"].append(f"{member['name']}: never entered world")
        elif member["movement_packets"] == 0:
            row["flags"].append(f"{member['name']}: logged in but never moved")
    if row["status"] not in ("completed", None):
        row["flags"].append(f"episode status {row['status']}")
    return row


# ---- HTML rendering (Ink & Print) ------------------------------------------------

CSS = """
:root{--bg:#fffdf4;--surface:#fffaf0;--fg:#111827;--fg-subtle:#555;--fg-muted:#999;
--navy:#1a3875;--sage:#6e8050;--terracotta:#b36e4e;--border:#e4dac8;--border-strong:#d4c9b5;
--border-subtle:#f0ebe1}
body{margin:0;background:var(--bg);color:var(--fg);
font:400 0.82rem/1.6 "Merriweather Sans",-apple-system,sans-serif}
main{max-width:1060px;margin:0 auto;padding:0 28px 80px}
header{border-bottom:2px solid var(--border-strong);padding:36px 0 16px;margin-bottom:8px}
.eyebrow{font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;
color:var(--fg-subtle);margin:0 0 8px}
h1{font-family:Merriweather,Georgia,serif;font-weight:900;font-size:1.7rem;margin:0 0 8px}
h2{font-family:Merriweather,Georgia,serif;font-weight:700;font-size:.84rem;
text-transform:uppercase;letter-spacing:.12em;color:var(--navy);
border-bottom:1px solid var(--border);padding-bottom:7px;margin:44px 0 14px}
.dek{color:var(--fg-subtle);max-width:70ch;margin:0}
table{width:100%;border-collapse:collapse;font-size:.76rem;margin:12px 0 22px}
th{text-align:left;font-size:.6rem;font-weight:700;text-transform:uppercase;
letter-spacing:.1em;color:var(--fg-subtle);border-bottom:2px solid var(--border-strong);
padding:5px 12px 5px 0}
td{border-bottom:1px solid var(--border-subtle);padding:6px 12px 6px 0;vertical-align:top}
td.num{text-align:right;font-family:ui-monospace,Menlo,monospace;font-feature-settings:"tnum" 1}
td.mono{font-family:ui-monospace,Menlo,monospace;font-size:.72rem}
.ok{color:var(--sage);font-weight:600}.bad{color:var(--terracotta);font-weight:600}
.muted{color:var(--fg-muted)}
.flag{border-left:3px solid var(--terracotta);background:rgba(179,110,78,.06);
padding:9px 14px;margin:9px 0;max-width:78ch;font-size:.78rem}
.say{font-family:ui-monospace,Menlo,monospace;font-size:.72rem;color:var(--fg-subtle);
padding-left:1em}
.empty{border:1px dashed var(--border);color:var(--fg-muted);font-style:italic;
padding:14px 18px;max-width:70ch}
"""


def esc(value) -> str:
    return html.escape(str(value))


def render_html(rows: list[dict], title: str, reasons: dict[str, str]) -> str:
    total = len(rows)
    logged_in = sum(
        1 for r in rows if r["members"] and all(m["login_verified"] for m in r["members"])
    )
    moved = sum(
        1 for r in rows if r["members"] and any(m["movement_packets"] > 0 for m in r["members"])
    )
    durations = [m["duration_s"] for r in rows for m in r["members"]]
    body: list[str] = [
        "<header>",
        '<p class="eyebrow">Vanilla WoW Lab · Batch Survey</p>',
        f"<h1>{esc(title)}</h1>",
        f'<p class="dek">{total} episode{"s" if total != 1 else ""} · '
        f"all-members-in-world in {logged_in}/{total} · movement observed in {moved}/{total}"
        + (
            f" · median in-world {statistics.median(durations):.0f}s per member"
            if durations
            else ""
        )
        + "</p>",
        "</header>",
    ]

    body.append("<h2>Episodes</h2>")
    if not rows:
        body.append('<p class="empty">No episodes found — nothing fetched yet.</p>')
    body.append("<table><thead><tr><th>Episode</th><th>Status</th><th>Score</th>"
                "<th>In world</th><th>Moved</th><th>Travelled (max yd)</th><th>Results?</th></tr></thead><tbody>")
    for row in rows:
        members = row["members"]
        n_in = sum(1 for m in members if m["login_verified"])
        n_moved = sum(1 for m in members if m["movement_packets"] > 0)
        max_travel = max((m["travelled_yd"] for m in members), default=0.0)
        # scores is a list of {policy_version_id, score} rows in live episode.json
        raw_scores = row.get("scores") or []
        values = [
            s["score"] if isinstance(s, dict) and "score" in s else s
            for s in (raw_scores if isinstance(raw_scores, list) else [raw_scores])
            if isinstance(s, (int, float)) or (isinstance(s, dict) and "score" in s)
        ]
        score_txt = (
            f"{min(values):g}–{max(values):g}" if len(set(values)) > 1
            else (f"{values[0]:g}" if values else "—")
        )
        ok = n_in == len(members) and members
        body.append(
            f'<tr><td class="mono">{esc(row["dir"])}</td>'
            f"<td>{esc(row['status'] or '—')}</td>"
            f'<td class="num">{esc(score_txt)}</td>'
            f'<td class="{"ok" if ok else "bad"}">{n_in}/{len(members) or "?"}</td>'
            f'<td class="num">{n_moved}</td>'
            f'<td class="num">{max_travel:g}</td>'
            f"<td>{'yes' if row['results_retained'] else '<span class=muted>no</span>'}</td></tr>"
        )
    body.append("</tbody></table>")

    body.append("<h2>Per-member detail</h2>")
    for row in rows:
        body.append(f'<h3 class="mono" style="font-size:.8rem">{esc(row["dir"])}</h3>')
        if not row["members"]:
            body.append('<p class="empty">No decodable replay for this episode.</p>')
            continue
        body.append(
            "<table><thead><tr><th>Member</th><th>Login</th><th>Duration (s)</th>"
            "<th>Move pkts</th><th>Travelled (yd)</th><th>Breadcrumbs</th></tr></thead><tbody>"
        )
        for m in row["members"]:
            says = "<br>".join(f'<span class="say">{esc(s)}</span>' for s in m["says"][:8]) or (
                '<span class="muted">none</span>'
            )
            body.append(
                f"<tr><td>{esc(m['name'])}</td>"
                f'<td class="{"ok" if m["login_verified"] else "bad"}">'
                f"{'verified' if m['login_verified'] else 'MISSING'}</td>"
                f'<td class="num">{m["duration_s"]:g}</td>'
                f'<td class="num">{m["movement_packets"]}</td>'
                f'<td class="num">{m["travelled_yd"]:g}</td>'
                f"<td>{says}</td></tr>"
            )
        body.append("</tbody></table>")

    flagged = [r for r in rows if r["flags"]]
    body.append("<h2>Flagged episodes</h2>")
    if not flagged:
        body.append('<p class="empty">Nothing flagged — every member entered the world and moved.</p>')
    for row in flagged:
        reason = reasons.get(row["dir"])
        body.append('<div class="flag"><b class="mono">' + esc(row["dir"]) + "</b><br>")
        body.append(" · ".join(esc(f) for f in row["flags"]))
        if reason:
            body.append(f"<br><i>{esc(reason)}</i>")
        body.append("</div>")

    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(title)}</title><style>{CSS}</style></head><body><main>"
        + "".join(body)
        + "</main></body></html>"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("episode_dir", type=Path)
    parser.add_argument("--out", type=Path, default=Path("wow-survey.html"))
    parser.add_argument("--title", default="Vanilla WoW batch survey")
    parser.add_argument("--reasons", type=Path, help="JSON: {episode_dir_name: reason}")
    args = parser.parse_args(argv)

    reasons: dict[str, str] = {}
    if args.reasons and args.reasons.is_file():
        reasons = json.loads(args.reasons.read_text(encoding="utf-8"))

    rows = []
    for child in sorted(args.episode_dir.iterdir()):
        if child.is_dir():
            row = survey_episode(child)
            if row is not None:
                rows.append(row)

    args.out.write_text(render_html(rows, args.title, reasons), encoding="utf-8")
    sidecar = args.out.with_suffix(".survey.json")
    sidecar.write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    print(f"wrote {args.out} and {sidecar} ({len(rows)} episodes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
