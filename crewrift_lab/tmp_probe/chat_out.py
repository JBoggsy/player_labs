"""Our outgoing meeting chat: accusation volume + whether no-vote crew ejections
were of colors OUR chat accused (the pile-seeding channel).

Usage: uv run python chat_out.py <eps_dir> <subject> [label]
"""
import json
import re
import sys
import zipfile
from pathlib import Path

PALETTE = ("red", "blue", "green", "pink", "orange", "yellow", "purple", "cyan")
COLOR_RE = re.compile(r"\b(" + "|".join(PALETTE) + r")\b")
ACCUSE_RE = re.compile(r"\b(sus|vote|vent|kill)\w*\b")

root = Path(sys.argv[1])
subject = sys.argv[2]
label = sys.argv[3] if len(sys.argv) > 3 else root.name

n = {"crew_eps": 0, "chats_sent": 0, "accusing_chats": 0,
     "crew_ej_no_vote": 0, "crew_ej_no_vote_our_chat_accused": 0}

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
    accused_by_us: set[str] = set()
    last_vote = None
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
            if name == "domain.meeting_chat_selected":
                text = str(data.get("text", "")).lower()
                n["chats_sent"] += 1
                colors = set(COLOR_RE.findall(text))
                if colors and ACCUSE_RE.search(text):
                    n["accusing_chats"] += 1
                    accused_by_us |= colors
            elif name == "domain.meeting_vote_selected":
                last_vote = data.get("target")
            elif name == "domain.player_died" and data.get("source") == "ejection":
                color = data.get("color")
                if color is None or data.get("is_self"):
                    continue
                if color not in imposter_colors and last_vote != color:
                    n["crew_ej_no_vote"] += 1
                    if color in accused_by_us:
                        n["crew_ej_no_vote_our_chat_accused"] += 1
                last_vote = None

print(label, json.dumps(n, indent=1))
