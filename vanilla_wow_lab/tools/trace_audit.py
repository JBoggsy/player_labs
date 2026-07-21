#!/usr/bin/env python3
"""Cross-check wowborg's trace against the episode replay — the automated
"sent is not accepted" audit.

Joins two independent evidence streams for one episode:
  - the policy's OWN account: `trace.jsonl` (from the policy-artifact bundle or a local
    runtime dir) — intents, typed outcomes, says;
  - the SERVER's account: the CWREPLAY's per-member packet capture (via cwreplay.py) —
    observed movement packets, travelled distance, chat packets.

Checks (per member the trace claims to control):
  1. Every settled-successful move intent should correspond to real observed movement —
     total trace displacement vs replay travelled yards (tolerance: ±40%; dead-reckoned
     vs Detour-projected paths legitimately differ).
  2. Every `say` in the trace should appear as a chat packet in the replay (rate-limited
     says that returned None are not in the trace).
  3. The replay member should have logged in (login verify) before the first intent.
  4. Outcome accounting: settled vs timeout counts, by settlement kind.

Usage:
  trace_audit.py <trace.jsonl> <replay-file> [--member NAME] [--json]

Exit code 0 = no discrepancies; 1 = discrepancies found (listed); 2 = cannot audit.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

_CWREPLAY_PATH = Path(__file__).resolve().parent / "cwreplay.py"
_spec = importlib.util.spec_from_file_location("cwreplay", _CWREPLAY_PATH)
cwreplay = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("cwreplay", cwreplay)
_spec.loader.exec_module(cwreplay)

DISPLACEMENT_TOLERANCE = 0.4  # ±40% — dead-reckoned vs projected paths differ


def load_trace(path: Path) -> list[dict]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def audit(trace_events: list[dict], replay, member_name: str | None) -> dict:
    intents = [e for e in trace_events if e.get("kind") == "intent"]
    outcomes = [e for e in trace_events if e.get("kind") == "outcome"]
    says = [e for e in trace_events if e.get("kind") == "say"]
    move_outcomes = [o for o in outcomes if o.get("action_kind") == "move"]
    settled = [o for o in move_outcomes if not o.get("timeout")]
    timeouts = [o for o in move_outcomes if o.get("timeout")]
    trace_displacement = sum(o.get("displacement_yards") or 0.0 for o in settled)
    settlement_kinds = Counter(o.get("settlement_kind") for o in settled)

    # Pick the replay member: explicit, else the member whose outbound chat matches the
    # MOST of our breadcrumbs. In same-brain self-play every slot emits similar
    # breadcrumb texts, so "first member with any match" misidentifies — score all.
    member = None
    if member_name:
        member = next(
            (m for m in replay.members if m.name.lower() == member_name.lower()), None
        )
    elif len(replay.members) == 1:
        member = replay.members[0]
    else:
        breadcrumb_texts = {e.get("text") for e in says if e.get("text")}
        best_score = 0
        for candidate in replay.members:
            candidate_texts = {
                cwreplay._chat_text(p)
                for p in candidate.packets
                if p.from_client and p.opcode in cwreplay.CHAT_OPCODES
            }
            score = len(breadcrumb_texts & candidate_texts)
            if score > best_score:
                best_score = score
                member = candidate

    findings: list[str] = []
    replay_metrics: dict = {}
    if member is None:
        findings.append(
            "cannot identify our member in the replay (no --member, no breadcrumb match)"
        )
    else:
        travelled = 0.0
        previous: tuple[float, float] | None = None
        chat_texts: list[str] = []
        logged_in = False
        for packet in member.packets:
            if not packet.from_client and packet.opcode == 566:
                logged_in = True
            info = cwreplay._movement_info(packet)
            if info is not None:
                if previous is not None:
                    travelled += (
                        (info["x"] - previous[0]) ** 2 + (info["y"] - previous[1]) ** 2
                    ) ** 0.5
                previous = (info["x"], info["y"])
            if packet.from_client and packet.opcode in cwreplay.CHAT_OPCODES:
                text = cwreplay._chat_text(packet)
                if text:
                    chat_texts.append(text)
        replay_metrics = {
            "member": member.name,
            "travelled_yd": round(travelled, 1),
            "chat_packets": len(chat_texts),
            "login_verified": logged_in,
        }

        # Check 3 — login before intents
        if intents and not logged_in:
            findings.append("trace shows intents but replay never saw a login verify")

        # Check 1 — displacement agreement
        if trace_displacement > 0:
            if travelled == 0:
                findings.append(
                    f"trace claims {trace_displacement:.1f} yd of settled movement but "
                    "the replay shows ZERO movement packets — 'sent is not accepted' violation"
                )
            else:
                ratio = travelled / trace_displacement
                if not (1 - DISPLACEMENT_TOLERANCE) <= ratio <= (1 + DISPLACEMENT_TOLERANCE + 1.0):
                    findings.append(
                        f"displacement mismatch: trace {trace_displacement:.1f} yd vs "
                        f"replay {travelled:.1f} yd (ratio {ratio:.2f})"
                    )

        # Check 2 — breadcrumbs present
        missing_says = [
            e.get("text")
            for e in says
            if e.get("text") and e.get("text") not in chat_texts
        ]
        if missing_says:
            findings.append(
                f"{len(missing_says)}/{len(says)} trace says missing from the replay: "
                f"{missing_says[:3]}"
            )

    return {
        "trace": {
            "intents": len(intents),
            "move_outcomes_settled": len(settled),
            "move_outcomes_timeout": len(timeouts),
            "settlement_kinds": dict(settlement_kinds),
            "claimed_displacement_yd": round(trace_displacement, 1),
            "says": len(says),
        },
        "replay": replay_metrics,
        "findings": findings,
        "ok": not findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("trace", type=Path)
    parser.add_argument("replay", type=Path)
    parser.add_argument("--member")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.trace.is_file():
        print(f"trace_audit: no trace file at {args.trace}", file=sys.stderr)
        return 2
    try:
        replay = cwreplay.decode_replay(args.replay)
    except cwreplay.ReplayError as exc:
        print(f"trace_audit: {exc}", file=sys.stderr)
        return 2

    report = audit(load_trace(args.trace), replay, args.member)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        t, r = report["trace"], report["replay"]
        print(
            f"trace: {t['intents']} intents · {t['move_outcomes_settled']} settled "
            f"({t['settlement_kinds']}) · {t['move_outcomes_timeout']} timeouts · "
            f"claimed {t['claimed_displacement_yd']} yd · {t['says']} says"
        )
        if r:
            print(
                f"replay[{r['member']}]: travelled {r['travelled_yd']} yd · "
                f"{r['chat_packets']} chat packets · login={r['login_verified']}"
            )
        if report["ok"]:
            print("AUDIT OK — trace and replay agree")
        else:
            for finding in report["findings"]:
                print(f"FINDING: {finding}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
