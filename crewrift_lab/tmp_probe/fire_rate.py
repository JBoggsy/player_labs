"""Offline fire-rate estimate for the HS-only (trust-floored) chat-evidence variant.

Replays W3's retained cand-arm telemetry (/tmp/w3_cand_eps — chat_evidence ON,
un-floored) and asks: with the 0.9 trust floor, how much testimony would have
survived? A speaker passes the floor when (a) HS-verified at claim time
(honor_known_member seen, not later honor_liar'd), or (b) near-cleared: their
posterior p <= 0.1 in the nearest preceding suspicion_snapshot.

Claims are extracted with the REAL template parser (chat_evidence._template_claims,
spaCy off) — a mild undercount vs runtime (no free-form/defense parse), noted in
the report. Only crew-side episodes count (imposter meetings don't trace).

Usage: uv run python crewrift_lab/tmp_probe/fire_rate.py /tmp/w3_cand_eps crewborg-chatev
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
subject_prefix = sys.argv[2]  # participant policy_name startswith


def make_belief() -> Belief:
    frame = PerceptionFrame(tick=1, camera_x=0, camera_y=0, players={}, bodies={}, visible_mask=None)
    belief = Belief(last_tick=1, self_role="crewmate", self_color=None, recent_frames=[frame, frame])
    belief.total_player_count = len(PALETTE)
    for color in PALETTE:
        belief.roster[color] = PlayerRecord(color=color, life_status="alive")
    return belief


totals = {
    "eps": 0,
    "crew_eps": 0,
    "meetings": 0,  # chat_evidence_applied count (crew meetings we voted in)
    "chat_lines": 0,
    "template_claims_any": 0,  # testimony-type claims from ANY speaker (v1 fuel)
    "hs_claims": 0,  # claims whose speaker was HS-verified at the time
    "nearclear_claims": 0,  # claims whose speaker was near-cleared (p<=0.1)
    "hs_kill_vent": 0,  # the materially-moving class from HS speakers
    "meetings_with_floor_pass": 0,
    "eps_with_floor_pass": 0,
    "eps_with_hs_member": 0,
    "changed_votes_v1": 0,  # for reference: un-floored changed votes observed
}

for d in sorted(p for p in root.iterdir() if p.is_dir()):
    ej, rj = d / "episode.json", d / "results.json"
    if not (ej.exists() and rj.exists()):
        continue
    ep = json.loads(ej.read_text())
    me = None
    for p in ep.get("participants", []):
        if str(p.get("policy_name", "")).startswith(subject_prefix) and p.get("position") == 0:
            me = p
            break
    if me is None:
        continue
    r = json.loads(rj.read_text())
    conn = (r.get("connect_timeout") or [0] * 8)[0]
    disc = (r.get("disconnect_timeout") or [0] * 8)[0]
    if conn or disc:
        continue
    totals["eps"] += 1
    is_imp = bool((r.get("imposter") or [0] * 8)[0])
    if is_imp:
        continue
    totals["crew_eps"] += 1

    z = d / "artifacts" / "policy_artifact_0.zip"
    if not z.exists():
        continue

    belief = make_belief()
    hs_trusted: set[str] = set()
    liars: set[str] = set()
    self_color: str | None = None
    latest_susp: dict[str, float] = {}
    ep_floor_pass = False
    meeting_floor_pass = False

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
            elif name == "domain.honor_known_member":
                hs_trusted.add(data.get("color"))
            elif name == "domain.honor_liar":
                liars.add(data.get("color"))
            elif name == "domain.suspicion_snapshot":
                for entry in data.get("ranking", []):
                    latest_susp[entry.get("color")] = entry.get("p", 1.0)
            elif name == "domain.chat_received":
                totals["chat_lines"] += 1
                speaker = data.get("speaker_color")
                text = str(data.get("text", ""))
                if speaker is None or text.startswith("HS1 "):
                    continue
                event = ChatEvent(tick=rec.get("tick", 1), speaker_color=speaker, text=text)
                claims, _ = chat_evidence._template_claims(belief, event)
                testimony = [
                    c for c in claims
                    if c.claim_type in ("kill", "vent", "accusation", "defense")
                    and c.target_color != speaker
                ]
                if not testimony:
                    continue
                totals["template_claims_any"] += len(testimony)
                speaker_hs = speaker in hs_trusted and speaker not in liars
                speaker_nc = latest_susp.get(speaker, 1.0) <= 0.1 and not speaker_hs
                if speaker_hs:
                    totals["hs_claims"] += len(testimony)
                    totals["hs_kill_vent"] += sum(1 for c in testimony if c.claim_type in ("kill", "vent"))
                if speaker_nc:
                    totals["nearclear_claims"] += len(testimony)
                if speaker_hs or speaker_nc:
                    meeting_floor_pass = True
                    ep_floor_pass = True
            elif name == "domain.chat_evidence_applied":
                totals["meetings"] += 1
                if meeting_floor_pass:
                    totals["meetings_with_floor_pass"] += 1
                meeting_floor_pass = False
                if data.get("changed_top_suspect"):
                    totals["changed_votes_v1"] += 1
    if hs_trusted - liars:
        totals["eps_with_hs_member"] += 1
    if ep_floor_pass:
        totals["eps_with_floor_pass"] += 1

ce = totals["crew_eps"] or 1
print(json.dumps(totals, indent=1))
print()
print(f"crew eps: {totals['crew_eps']}   meetings traced: {totals['meetings']}")
print(f"eps with an HS-verified (trusted) member visible: {totals['eps_with_hs_member']} "
      f"({totals['eps_with_hs_member']/ce:.1%} of crew eps)")
print(f"floor-passing testimony claims: HS {totals['hs_claims']} "
      f"(kill/vent {totals['hs_kill_vent']}), near-cleared {totals['nearclear_claims']}")
print(f"eps with ANY floor-passing claim: {totals['eps_with_floor_pass']} "
      f"({totals['eps_with_floor_pass']/ce:.2f}/crew-ep would-fire rate)")
print(f"meetings with a floor-passing claim: {totals['meetings_with_floor_pass']} "
      f"of {totals['meetings']}")
print(f"reference (un-floored v1): changed votes {totals['changed_votes_v1']}, "
      f"any-speaker testimony claims {totals['template_claims_any']}")
