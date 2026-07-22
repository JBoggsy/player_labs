"""W3b mechanism metrics: changed-vote imposter hit rate + floor-passing
source-class attribution.

For the cand arm's slot-0 telemetry:
- every domain.chat_evidence_applied with changed_top_suspect: did the
  with-chat top_suspect hit an actual imposter (results.json ground truth)?
- source-class attribution: for each meeting with nonzero contributions,
  re-derive (fire_rate.py style) which speaker classes (HS / near-cleared)
  produced floor-passing testimony up to that point — the "HS sources
  predominate" prereg check.

Usage: uv run python crewrift_lab/tmp_probe/w3b_mechanism.py /tmp/w3b_cand_eps crewborg-chatev
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

from crewrift.crewborg.strategy.meeting import chat_evidence
from crewrift.crewborg.types import Belief, ChatEvent, PerceptionFrame, PlayerRecord

PALETTE = ("red", "blue", "green", "pink", "orange", "yellow", "purple", "cyan")

root = Path(sys.argv[1])
subject = sys.argv[2]


def make_belief() -> Belief:
    frame = PerceptionFrame(tick=1, camera_x=0, camera_y=0, players={}, bodies={}, visible_mask=None)
    belief = Belief(last_tick=1, self_role="crewmate", self_color=None, recent_frames=[frame, frame])
    belief.total_player_count = len(PALETTE)
    for color in PALETTE:
        belief.roster[color] = PlayerRecord(color=color, life_status="alive")
    return belief


n = {
    "crew_eps": 0,
    "applied": 0,
    "applied_nonzero": 0,
    "changed": 0,
    "changed_with_suspect": 0,
    "changed_hit_imposter": 0,
    "nonzero_meetings_hs_source": 0,
    "nonzero_meetings_nearclear_only": 0,
    "hs_claims": 0,
    "nearclear_claims": 0,
    "hs_kill_vent": 0,
}
changed_examples = []

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
    belief = make_belief()
    hs_trusted: set[str] = set()
    liars: set[str] = set()
    latest_susp: dict[str, float] = {}
    window_hs = False
    window_nc = False
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
            if name == "domain.honor_known_member":
                hs_trusted.add(data.get("color"))
            elif name == "domain.honor_liar":
                liars.add(data.get("color"))
            elif name == "domain.suspicion_snapshot":
                for entry in data.get("ranking", []):
                    latest_susp[entry.get("color")] = entry.get("p", 1.0)
            elif name == "domain.chat_received":
                speaker = data.get("speaker_color")
                text = str(data.get("text", ""))
                if speaker is None or text.startswith("HS1 "):
                    continue
                event = ChatEvent(tick=rec.get("tick", 1), speaker_color=speaker, text=text)
                claims, _ = chat_evidence._template_claims(belief, event)
                testimony = [
                    c for c in claims
                    if c.claim_type in ("kill", "vent", "accusation", "defense") and c.target_color != speaker
                ]
                if not testimony:
                    continue
                if speaker in hs_trusted and speaker not in liars:
                    window_hs = True
                    n["hs_claims"] += len(testimony)
                    n["hs_kill_vent"] += sum(1 for c in testimony if c.claim_type in ("kill", "vent"))
                elif latest_susp.get(speaker, 1.0) <= 0.1:
                    window_nc = True
                    n["nearclear_claims"] += len(testimony)
            elif name == "domain.chat_evidence_applied":
                n["applied"] += 1
                if data.get("contributions"):
                    n["applied_nonzero"] += 1
                    if window_hs:
                        n["nonzero_meetings_hs_source"] += 1
                    elif window_nc:
                        n["nonzero_meetings_nearclear_only"] += 1
                if data.get("changed_top_suspect"):
                    n["changed"] += 1
                    ts = data.get("top_suspect_with_chat")
                    if ts:
                        n["changed_with_suspect"] += 1
                        if ts in imposter_colors:
                            n["changed_hit_imposter"] += 1
                    if len(changed_examples) < 15:
                        changed_examples.append({"ep": d.name, **data})
                window_hs = False
                window_nc = False

print(json.dumps(n, indent=1))
if n["changed_with_suspect"]:
    print(f"\nchanged-vote imposter hit rate: {n['changed_hit_imposter']}/{n['changed_with_suspect']} "
          f"= {n['changed_hit_imposter']/n['changed_with_suspect']:.1%}")
if n["applied_nonzero"]:
    print(f"nonzero-contribution meetings with an HS source: {n['nonzero_meetings_hs_source']}"
          f"/{n['applied_nonzero']} (near-cleared-only: {n['nonzero_meetings_nearclear_only']})")
for ex in changed_examples:
    print(json.dumps(ex)[:280])
