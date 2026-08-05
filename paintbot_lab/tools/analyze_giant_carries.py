#!/usr/bin/env python3
"""
Analyze giant map steal-to-capture conversion for v22 baseline vs Daveey.
Focus on carrier behavior, route efficiency, and failure modes.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import zipfile
import tempfile

def load_episode_data(episode_dir: Path) -> Dict:
    """Load episode metadata and events."""
    with open(episode_dir / "episode.json") as f:
        episode = json.load(f)

    events = []
    with open(episode_dir / "events.jsonl") as f:
        for line in f:
            events.append(json.loads(line))

    # Identify which position is Stencil
    stencil_pos = None
    daveey_pos = None
    for p in episode["participants"]:
        if "stencil" in p["policy_name"].lower():
            stencil_pos = p["position"]
        elif "focusfire" in p["policy_name"].lower():
            daveey_pos = p["position"]

    return {
        "episode_id": episode["episode_id"],
        "stencil_pos": stencil_pos,
        "daveey_pos": daveey_pos,
        "events": events,
        "scores": episode["participant_scores"],
        "episode_dir": episode_dir
    }

def extract_stencil_telemetry(episode_dir: Path, position: int) -> Optional[List[Dict]]:
    """Extract Stencil's ticks.jsonl telemetry from policy artifact."""
    artifact_path = episode_dir / "artifacts" / f"policy_artifact_{position}.zip"
    if not artifact_path.exists():
        return None

    ticks = []
    with zipfile.ZipFile(artifact_path, 'r') as zf:
        if 'ticks.jsonl' in zf.namelist():
            with zf.open('ticks.jsonl') as f:
                for line in f:
                    ticks.append(json.loads(line.decode('utf-8')))
    return ticks

def analyze_carry_sequence(events: List[Dict], steal_tick: int, pos: int) -> Dict:
    """Analyze what happened to a flag steal."""
    # Find all events after steal involving this carrier
    carrier_deaths = []
    captures = []
    returns = []

    for evt in events:
        if not isinstance(evt, dict) or "tick" not in evt:
            continue
        if evt["tick"] < steal_tick:
            continue
        if evt["tick"] > steal_tick + 10000:  # 10k tick window
            break

        # Death of carrier
        if evt.get("kind") == "death" and evt.get("source") == pos:
            carrier_deaths.append(evt["tick"])

        # Capture
        if evt.get("kind") == "capture" and evt.get("source") == pos:
            captures.append(evt["tick"])
            break

        # Return (enemy reclaims)
        if evt.get("kind") == "flag_return":
            returns.append(evt["tick"])
            break

    outcome = "timeout"
    outcome_tick = None
    duration = None

    if captures:
        outcome = "capture"
        outcome_tick = captures[0]
        duration = outcome_tick - steal_tick
    elif carrier_deaths:
        outcome = "death"
        outcome_tick = carrier_deaths[0]
        duration = outcome_tick - steal_tick
    elif returns:
        outcome = "return"
        outcome_tick = returns[0]
        duration = outcome_tick - steal_tick

    return {
        "steal_tick": steal_tick,
        "outcome": outcome,
        "outcome_tick": outcome_tick,
        "duration": duration,
        "deaths_during": len(carrier_deaths)
    }

def main():
    giant_dir = Path("/tmp/stencil_daveey_baseline/artifacts/giant")
    episode_dirs = sorted([d for d in giant_dir.iterdir() if d.is_dir() and d.name.startswith("20260805")])

    print(f"Analyzing {len(episode_dirs)} giant episodes...")
    print()

    stencil_steals = []
    daveey_steals = []
    stencil_wins = 0
    daveey_wins = 0

    for ep_dir in episode_dirs:
        data = load_episode_data(ep_dir)
        stencil_pos = data["stencil_pos"]
        daveey_pos = data["daveey_pos"]

        # Track winner
        if data["scores"][stencil_pos]["score"] > 0:
            stencil_wins += 1
        else:
            daveey_wins += 1

        # Extract all flag steals
        for evt in data["events"]:
            if not isinstance(evt, dict):
                continue
            if evt.get("kind") == "flag_steal":
                if evt.get("source") == stencil_pos:
                    analysis = analyze_carry_sequence(data["events"], evt["tick"], stencil_pos)
                    analysis["episode_id"] = data["episode_id"]
                    stencil_steals.append(analysis)
                elif evt.get("source") == daveey_pos:
                    analysis = analyze_carry_sequence(data["events"], evt["tick"], daveey_pos)
                    analysis["episode_id"] = data["episode_id"]
                    daveey_steals.append(analysis)

    print(f"=== GIANT MAP BASELINE SUMMARY ===")
    print(f"Total episodes: {len(episode_dirs)}")
    print(f"Stencil wins: {stencil_wins} ({stencil_wins/len(episode_dirs)*100:.1f}%)")
    print(f"Daveey wins: {daveey_wins}")
    print()

    # Analyze steal outcomes
    print(f"=== STENCIL STEALS (n={len(stencil_steals)}) ===")
    stencil_outcomes = defaultdict(int)
    stencil_durations = defaultdict(list)
    for steal in stencil_steals:
        stencil_outcomes[steal["outcome"]] += 1
        if steal["duration"]:
            stencil_durations[steal["outcome"]].append(steal["duration"])

    for outcome in ["capture", "death", "return", "timeout"]:
        count = stencil_outcomes[outcome]
        if count > 0:
            avg_dur = sum(stencil_durations[outcome]) / len(stencil_durations[outcome]) if stencil_durations[outcome] else 0
            print(f"  {outcome}: {count} ({count/len(stencil_steals)*100:.1f}%) | avg duration: {avg_dur:.0f} ticks")

    print()
    print(f"=== DAVEEY STEALS (n={len(daveey_steals)}) ===")
    daveey_outcomes = defaultdict(int)
    daveey_durations = defaultdict(list)
    for steal in daveey_steals:
        daveey_outcomes[steal["outcome"]] += 1
        if steal["duration"]:
            daveey_durations[steal["outcome"]].append(steal["duration"])

    for outcome in ["capture", "death", "return", "timeout"]:
        count = daveey_outcomes[outcome]
        if count > 0:
            avg_dur = sum(daveey_durations[outcome]) / len(daveey_durations[outcome]) if daveey_durations[outcome] else 0
            print(f"  {outcome}: {count} ({count/len(daveey_steals)*100:.1f}%) | avg duration: {avg_dur:.0f} ticks")

    print()
    print(f"=== CONVERSION EFFICIENCY ===")
    stencil_conv = stencil_outcomes["capture"] / len(stencil_steals) if stencil_steals else 0
    daveey_conv = daveey_outcomes["capture"] / len(daveey_steals) if daveey_steals else 0
    print(f"Stencil steal→capture: {stencil_outcomes['capture']}/{len(stencil_steals)} = {stencil_conv*100:.1f}%")
    print(f"Daveey steal→capture: {daveey_outcomes['capture']}/{len(daveey_steals)} = {daveey_conv*100:.1f}%")
    print()

    # Show detailed failed carries
    print(f"=== STENCIL FAILED CARRIES (returns) ===")
    failed = [s for s in stencil_steals if s["outcome"] == "return"]
    for f in failed[:5]:
        print(f"  Episode {f['episode_id'][:16]}: steal@{f['steal_tick']} → return@{f['outcome_tick']} ({f['duration']} ticks)")

    print()
    print(f"=== DAVEEY SUCCESSFUL CARRIES ===")
    success = [s for s in daveey_steals if s["outcome"] == "capture"]
    for s in success[:5]:
        print(f"  Episode {s['episode_id'][:16]}: steal@{s['steal_tick']} → capture@{s['outcome_tick']} ({s['duration']} ticks)")

    print()
    print(f"=== KEY INSIGHT ===")
    print(f"Steal attempts: Stencil {len(stencil_steals)}, Daveey {len(daveey_steals)}")
    print(f"Daveey steals {len(daveey_steals)/len(stencil_steals) if stencil_steals else 0:.1f}x more often")
    print(f"This suggests Stencil's problem is OPPORTUNITY (getting to the heart), not conversion efficiency")

    # Analyze early game steals
    early_steals_stencil = [s for s in stencil_steals if s["steal_tick"] < 3000]
    early_steals_daveey = [s for s in daveey_steals if s["steal_tick"] < 3000]
    print()
    print(f"=== EARLY GAME (< tick 3000) ===")
    print(f"Stencil early steals: {len(early_steals_stencil)}/{len(stencil_steals)}")
    print(f"Daveey early steals: {len(early_steals_daveey)}/{len(daveey_steals)}")

    if early_steals_daveey:
        print(f"Daveey's earliest steal: tick {min(s['steal_tick'] for s in early_steals_daveey)}")
    if early_steals_stencil:
        print(f"Stencil's earliest steal: tick {min(s['steal_tick'] for s in early_steals_stencil)}")

if __name__ == "__main__":
    main()
