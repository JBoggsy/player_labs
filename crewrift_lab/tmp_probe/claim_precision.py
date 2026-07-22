"""Ground-truth precision of chat testimony by speaker trust class.

For each testimony claim (template parse) in the W3 cand-arm telemetry, check
whether its TARGET is an actual imposter (results.json). Splits by speaker class:
HS-verified, near-cleared (p<=0.1 at claim time), and everyone else (the class
the floor removes). Also splits by claim type. This is the direct measure of
whether the floored evidence source is worth listening to.

Usage: uv run python crewrift_lab/tmp_probe/claim_precision.py /tmp/w3_cand_eps crewborg-chatev
"""

from __future__ import annotations

import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

from crewrift.crewborg.strategy.meeting import chat_evidence
from crewrift.crewborg.types import Belief, ChatEvent, PerceptionFrame, PlayerRecord

PALETTE = ("red", "blue", "green", "pink", "orange", "yellow", "purple", "cyan")

root = Path(sys.argv[1])
subject_prefix = sys.argv[2]


def make_belief() -> Belief:
    frame = PerceptionFrame(tick=1, camera_x=0, camera_y=0, players={}, bodies={}, visible_mask=None)
    belief = Belief(last_tick=1, self_role="crewmate", self_color=None, recent_frames=[frame, frame])
    belief.total_player_count = len(PALETTE)
    for color in PALETTE:
        belief.roster[color] = PlayerRecord(color=color, life_status="alive")
    return belief


# (speaker_class, claim_type) -> [hits_imposter, total]  (accusatory claims only;
# defenses tallied separately: a defense "hits" when its target is CREW)
acc: Counter = Counter()
tot: Counter = Counter()
def_hit: Counter = Counter()
def_tot: Counter = Counter()

for d in sorted(p for p in root.iterdir() if p.is_dir()):
    ej, rj = d / "episode.json", d / "results.json"
    if not (ej.exists() and rj.exists()):
        continue
    ep = json.loads(ej.read_text())
    if not any(
        str(p.get("policy_name", "")).startswith(subject_prefix) and p.get("position") == 0
        for p in ep.get("participants", [])
    ):
        continue
    r = json.loads(rj.read_text())
    if (r.get("connect_timeout") or [0] * 8)[0] or (r.get("disconnect_timeout") or [0] * 8)[0]:
        continue
    if bool((r.get("imposter") or [0] * 8)[0]):
        continue  # crew-side only (matches the runtime term's use)
    imposter_colors = {PALETTE[i] for i, f in enumerate(r.get("imposter") or [0] * 8) if f}

    z = d / "artifacts" / "policy_artifact_0.zip"
    if not z.exists():
        continue
    belief = make_belief()
    hs_trusted: set[str] = set()
    liars: set[str] = set()
    latest_susp: dict[str, float] = {}
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
                if speaker in hs_trusted and speaker not in liars:
                    klass = "hs"
                elif latest_susp.get(speaker, 1.0) <= 0.1:
                    klass = "nearclear"
                elif speaker in imposter_colors:
                    klass = "imposter_speaker"
                else:
                    klass = "stranger"
                for c in claims:
                    if c.target_color == speaker:
                        continue
                    if c.claim_type in ("kill", "vent", "accusation"):
                        tot[(klass, c.claim_type)] += 1
                        tot[(klass, "ALL")] += 1
                        if c.target_color in imposter_colors:
                            acc[(klass, c.claim_type)] += 1
                            acc[(klass, "ALL")] += 1
                    elif c.claim_type == "defense":
                        def_tot[klass] += 1
                        if c.target_color not in imposter_colors:
                            def_hit[klass] += 1

print(f"{'speaker class':<18}{'claim type':<12}{'hits-imp':>9}{'total':>7}{'precision':>11}")
for klass in ("hs", "nearclear", "stranger", "imposter_speaker"):
    for ct in ("kill", "vent", "accusation", "ALL"):
        t = tot[(klass, ct)]
        if not t:
            continue
        print(f"{klass:<18}{ct:<12}{acc[(klass, ct)]:>9}{t:>7}{acc[(klass, ct)]/t:>10.1%}")
    if def_tot[klass]:
        print(f"{klass:<18}{'defense*':<12}{def_hit[klass]:>9}{def_tot[klass]:>7}{def_hit[klass]/def_tot[klass]:>10.1%}")
print("\n*defense precision = target actually crew")
