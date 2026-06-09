#!/usr/bin/env python3
"""Tier-2 per-episode fact sheet from the objective replay timeline.

Runs the version-matched ``expand_replay`` binary on one episode's replay, parses the
event timeline, and extracts the facts Tier 1 can't get from results.json:

  - the target policy's outcome: killed by an imposter (who/when), ejected by vote
    (which meeting), or survived to the end;
  - its score breakdown, itemized by reason (tasks / killing / winning / idle / missed
    vote) — the precise "why" behind a high or low score;
  - vote correctness: as crew, did it vote a *real* imposter, or eject a *real*
    crewmate? (true roles come from results.json);
  - an event-feature vector for the episode (kills, bodies, meetings, ticks, the
    target's votes/ticks-alive) — the basis for spotting "unusual" episodes.

Needs the version-matched binary (build it with ``tools/build_expand_replay.sh``;
replays from Observatory match ``CREWRIFT_REF``). Run this on episodes the Tier-1
report flagged. See SKILL.md.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path


TOKEN = re.compile(r"^(?P<color>[a-z][a-z ]*?)\((?P<name>.*)\)$")


def parse_token(tok: str) -> tuple[str, str] | None:
    """'pale blue(Some Player)' -> ('pale blue', 'Some Player')."""
    m = TOKEN.match(tok.strip())
    return (m.group("color"), m.group("name")) if m else None


@dataclass
class Episode:
    ticks: int = 0
    kills: list[dict] = field(default_factory=list)        # {tick, killer, victim}
    bodies: list[dict] = field(default_factory=list)       # {tick, victim, room}
    reports: list[dict] = field(default_factory=list)      # {tick, reporter, victim, room}
    emergencies: list[dict] = field(default_factory=list)  # {tick, caller}
    meetings: list[dict] = field(default_factory=list)     # {tick, votes:{voter:target|'skip'}, ejected}
    scores: list[dict] = field(default_factory=list)       # {tick, who, amount, reason}
    join_order: list[str] = field(default_factory=list)    # colors in join order


def run_expand(binary: Path, replay: Path) -> str:
    proc = subprocess.run([str(binary), str(replay)], capture_output=True, text=True)
    out = proc.stdout
    if "hash failed" in out:
        n = len(out.splitlines())
        raise SystemExit(
            f"expand_replay hash-failed after ~{n} lines — the binary doesn't match the "
            f"replay's recording build. Rebuild a matching one with tools/build_expand_replay.sh "
            f"(use --ref if this replay isn't from the current upload). See crewrift-replays.md §B.")
    return out


def parse_timeline(text: str) -> Episode:
    ep = Episode()
    tick = 0
    cur_meeting: dict | None = None

    def color_of(tok: str) -> str:
        ct = parse_token(tok)
        return ct[0] if ct else tok

    for raw in text.splitlines():
        if raw.startswith("tick "):
            tick = int(raw[5:].strip() or 0)
            ep.ticks = max(ep.ticks, tick)
            continue
        line = raw.strip()
        if line.startswith("phase "):
            phase = line[6:].strip()
            if phase == "Voting":
                cur_meeting = {"tick": tick, "votes": {}, "ejected": None}
                ep.meetings.append(cur_meeting)
            elif phase in ("Playing", "GameOver"):
                cur_meeting = None
            continue
        if line.startswith("score player "):
            m = re.match(r"score player (.+?) ([+-]\d+) \(for (.+)\)$", line)
            if m:
                ep.scores.append({"tick": tick, "who": color_of(m.group(1)),
                                  "amount": int(m.group(2)), "reason": m.group(3)})
            continue
        if line.startswith("player "):
            rest = line[len("player "):]
            if rest.endswith(" joined"):
                ep.join_order.append(color_of(rest[:-len(" joined")]))
            elif " killed " in rest:
                a, b = rest.split(" killed ", 1)
                ep.kills.append({"tick": tick, "killer": color_of(a), "victim": color_of(b)})
            elif rest.endswith(" voted skip"):
                if cur_meeting is not None:
                    cur_meeting["votes"][color_of(rest[:-len(" voted skip")])] = "skip"
            elif " voted " in rest:
                a, b = rest.split(" voted ", 1)
                if cur_meeting is not None:
                    cur_meeting["votes"][color_of(a)] = color_of(b)
            elif rest.endswith(" called emergency button"):
                ep.emergencies.append({"tick": tick, "caller": color_of(rest[:-len(" called emergency button")])})
            elif " reported body " in rest:
                a, b = rest.split(" reported body ", 1)
                victim, _, room = b.partition(" room ")
                ep.reports.append({"tick": tick, "reporter": color_of(a),
                                   "victim": color_of(victim), "room": room})
            continue
        if line.startswith("body "):
            victim, _, room = line[len("body "):].partition(" room ")
            ep.bodies.append({"tick": tick, "victim": color_of(victim), "room": room})

    # Resolve each meeting's ejection: the player-target with the most votes, if it
    # beats skip. (Ties / skip-majority -> no one ejected.)
    for mtg in ep.meetings:
        tally: dict[str, int] = {}
        skip = 0
        for target in mtg["votes"].values():
            if target == "skip":
                skip += 1
            else:
                tally[target] = tally.get(target, 0) + 1
        if tally:
            top, n = max(tally.items(), key=lambda kv: kv[1])
            others = [v for k, v in tally.items() if k != top]
            if n > skip and (not others or n > max(others)):
                mtg["ejected"] = top
    return ep


def load_target(ep_dir: Path, policy: str, version: int | None):
    """Return (slot, name, role, imposter_colors_by_name) using results + episode json."""
    episode = json.loads((ep_dir / "episode.json").read_text())
    results = json.loads((ep_dir / "results.json").read_text())
    slot = None
    for entry in episode.get("policy_results") or []:
        pol = entry.get("policy") or {}
        if pol.get("name") == policy and (version is None or pol.get("version") == version):
            slot = entry.get("position")
            break
    if slot is None:
        raise SystemExit(f"policy '{policy}' not found in {ep_dir/'episode.json'}")
    names = results.get("names") or []
    imp = results.get("imposter") or []
    name = names[slot] if slot < len(names) else ""
    role = "imposter" if (slot < len(imp) and imp[slot]) else "crew"
    imposter_names = {names[j] for j in range(len(names)) if j < len(imp) and imp[j]}
    return slot, name, role, imposter_names, names, imp


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode_dir", help="One episode directory (replay.json + episode.json + results.json).")
    ap.add_argument("--policy", required=True, help="Target policy name, optionally name:vN.")
    ap.add_argument("--version", type=int, default=None)
    ap.add_argument("--bin", default=None, help="expand_replay binary (default: lab tools/bin/expand_replay).")
    ap.add_argument("--json", help="Write the fact sheet as JSON here.")
    args = ap.parse_args()

    policy, version = args.policy, args.version
    if ":v" in policy and version is None:
        policy, v = policy.split(":v", 1)
        version = int(v)

    ep_dir = Path(args.episode_dir)
    replay = ep_dir / "replay.json"
    if not replay.exists():
        raise SystemExit(f"no replay.json in {ep_dir}")

    binary = Path(args.bin) if args.bin else (
        Path(__file__).resolve().parents[4] / "tools" / "bin" / "expand_replay")
    if not binary.exists():
        raise SystemExit(f"expand_replay not found at {binary}\n"
                         f"  build it: crewrift_lab/tools/build_expand_replay.sh")

    slot, name, role, imposter_names, names, imp_flags = load_target(ep_dir, policy, version)
    full = run_expand(binary, replay)
    ep = parse_timeline(full)

    # Map name -> color from the joined tokens (results arrays are slot-indexed; the
    # timeline labels by color, so join the two through the shared player name).
    name_to_color = {}
    for line in full.splitlines():
        s = line.strip()
        if s.startswith("player ") and s.endswith(" joined"):
            ct = parse_token(s[len("player "):-len(" joined")])
            if ct:
                name_to_color[ct[1]] = ct[0]
    target_color = name_to_color.get(name)
    imposter_colors = {name_to_color.get(n) for n in imposter_names if name_to_color.get(n)}

    # --- outcome: killed / ejected / survived -------------------------------------
    outcome = {"kind": "survived", "detail": None, "tick": None}
    for k in ep.kills:
        if k["victim"] == target_color:
            outcome = {"kind": "killed_by_imposter", "detail": k["killer"], "tick": k["tick"]}
            break
    for mtg in ep.meetings:
        if mtg["ejected"] == target_color:
            outcome = {"kind": "ejected_by_vote", "detail": f"meeting@{mtg['tick']}", "tick": mtg["tick"]}
            break

    # --- score breakdown (itemized) -----------------------------------------------
    breakdown: dict[str, int] = {}
    for s in ep.scores:
        if s["who"] == target_color:
            breakdown[s["reason"]] = breakdown.get(s["reason"], 0) + s["amount"]
    total = sum(breakdown.values())

    # --- vote behavior + correctness (crew) ---------------------------------------
    target_votes = []
    correct_imposter_votes = 0
    wrong_crew_votes = 0
    for mtg in ep.meetings:
        v = mtg["votes"].get(target_color)
        if v is None:
            target_votes.append("(no vote)")
            continue
        target_votes.append(v)
        if v != "skip":
            if v in imposter_colors:
                correct_imposter_votes += 1
            else:
                wrong_crew_votes += 1

    # --- event-feature vector ------------------------------------------------------
    features = {
        "game_ticks": ep.ticks,
        "total_kills": len(ep.kills),
        "total_bodies": len(ep.bodies),
        "total_reports": len(ep.reports),
        "total_meetings": len(ep.meetings),
        "total_emergencies": len(ep.emergencies),
        "target_votes_cast": sum(1 for v in target_votes if v not in ("(no vote)",)),
        "target_skips": sum(1 for v in target_votes if v == "skip"),
        "target_missed_votes": sum(1 for v in target_votes if v == "(no vote)"),
        "target_ticks_alive": outcome["tick"] if outcome["tick"] else ep.ticks,
        "target_kills": sum(1 for k in ep.kills if k["killer"] == target_color),
    }

    sheet = {
        "episode_dir": ep_dir.name,
        "policy": policy, "version": version, "slot": slot,
        "name": name, "color": target_color, "role": role,
        "imposter_colors": sorted(c for c in imposter_colors if c),
        "outcome": outcome,
        "score_total": total,
        "score_breakdown": breakdown,
        "votes": target_votes,
        "vote_correctness": {"voted_real_imposter": correct_imposter_votes,
                             "voted_out_real_crewmate": wrong_crew_votes},
        "features": features,
    }

    # --- render --------------------------------------------------------------------
    print(f"# Episode {ep_dir.name} — {policy}" + (f":v{version}" if version is not None else ""))
    print(f"\n**{name}** ({target_color}), role **{role}**, slot {slot}. "
          f"Imposters: {', '.join(sheet['imposter_colors']) or '?'}.")
    oc = outcome
    label = {"killed_by_imposter": f"💀 KILLED by {oc['detail']} @tick {oc['tick']}",
             "ejected_by_vote": f"🗳 EJECTED by vote ({oc['detail']})",
             "survived": "✅ survived to game end"}[oc["kind"]]
    print(f"\n**Outcome:** {label}")
    print(f"\n**Score: {total}** — " + ", ".join(f"{r} {a:+d}" for r, a in breakdown.items()))
    if ep.meetings:
        vc = sheet["vote_correctness"]
        print(f"\n**Voting:** {target_votes}  "
              f"(voted real imposter ×{vc['voted_real_imposter']}, "
              f"voted out real crewmate ×{vc['voted_out_real_crewmate']})")
    print("\n**Event features:**")
    for k, v in features.items():
        print(f"  - {k}: {v}")

    if args.json:
        Path(args.json).write_text(json.dumps(sheet, indent=2))
        print(f"\n[wrote JSON: {args.json}]")


if __name__ == "__main__":
    main()
