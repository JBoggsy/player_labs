"""Decompose crew ejections in our crew episodes: us ejected / other-crew ejected
WITH our vote on them that meeting / other-crew ejected WITHOUT our vote.

Reads slot-0 telemetry: domain.player_died (source=ejection) + our
domain.meeting_vote_selected targets, per meeting window. Also counts meetings.

Usage: uv run python ejection_decomp.py <eps_dir> <subject> [label]
"""
import json
import sys
import zipfile
from pathlib import Path

PALETTE = ("red", "blue", "green", "pink", "orange", "yellow", "purple", "cyan")

root = Path(sys.argv[1])
subject = sys.argv[2]
label = sys.argv[3] if len(sys.argv) > 3 else root.name

n = {
    "crew_eps": 0, "meetings": 0,
    "self_ejected": 0, "crew_ej_we_voted": 0, "crew_ej_no_vote": 0,
    "imp_ej_we_voted": 0, "imp_ej_no_vote": 0,
}

for d in sorted(p for p in root.iterdir() if p.is_dir()):
    ej, rj = d / "episode.json", d / "results.json"
    if not (ej.exists() and rj.exists()):
        continue
    ep = json.loads(ej.read_text())
    if not any(p.get("policy_name") == subject and p.get("position") == 0 for p in ep.get("participants", [])):
        continue
    r = json.loads(rj.read_text())
    if (r.get("connect_timeout") or [0] * 8)[0] or (r.get("disconnect_timeout") or [0] * 8)[0]:
        continue
    imposter_flags = r.get("imposter") or [0] * 8
    if imposter_flags[0]:
        continue
    n["crew_eps"] += 1
    imposter_colors = {PALETTE[i] for i, f in enumerate(imposter_flags) if f}

    z = d / "artifacts" / "policy_artifact_0.zip"
    if not z.exists():
        continue
    self_color = None
    last_vote = None  # our most recent vote target
    try:
        zf = zipfile.ZipFile(z)
    except zipfile.BadZipFile:
        continue
    with zf.open("telemetry.jsonl") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            name = rec.get("name") or ""
            data = rec.get("data") or {}
            if name == "domain.role_resolved":
                pass
            elif name == "domain.viewer_map":
                pass
            elif name == "domain.meeting_vote_selected":
                last_vote = data.get("target")
                n["meetings"] += 1
            elif name == "domain.player_died" and data.get("source") == "ejection":
                color = data.get("color")
                if color is None:
                    continue
                if data.get("is_self"):
                    n["self_ejected"] += 1
                    continue
                voted = last_vote == color
                if color in imposter_colors:
                    n["imp_ej_we_voted" if voted else "imp_ej_no_vote"] += 1
                else:
                    n["crew_ej_we_voted" if voted else "crew_ej_no_vote"] += 1
                last_vote = None

print(label, json.dumps(n, indent=1))
ce = n["crew_eps"] or 1
print(f"meetings/crew-ep {n['meetings']/ce:.2f}")
