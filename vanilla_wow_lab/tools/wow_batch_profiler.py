#!/usr/bin/env python3
"""Aggregate stateful gameplay diagnostics across Vanilla WoW replays.

This is deliberately a thin consumer of the owner repo's canonical
``player.sdk.replay_diagnostics`` reducer. It does not decode WoW packets itself.

Usage:
  uv run python vanilla_wow_lab/tools/wow_batch_profiler.py EPISODE_OR_BATCH ...
  uv run python vanilla_wow_lab/tools/wow_batch_profiler.py BATCH --json-out report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from player.sdk.replay_diagnostics import PlayerReplayDiagnostics, inspect_replay


DEFAULT_OWNER_REPO = Path(
    os.environ.get(
        "VANILLA_WOW_OWNER_REPO",
        Path.home() / "coding/coworlds/coworld-vanilla-wow",
    )
)
REPLAY_NAMES = ("replay.json", "replay.cwreplay")

# Spell IDs are stable Vanilla 1.12 facts. Unknown spells remain visible by ID.
FORM_SPELLS = {
    768: "Cat Form",
    783: "Travel Form",
    1066: "Aquatic Form",
    5215: "Prowl (Rank 1)",
    6783: "Prowl (Rank 2)",
    9913: "Prowl (Rank 3)",
    5487: "Bear Form",
    9634: "Dire Bear Form",
    24858: "Moonkin Form",
    8326: "Ghost",
}


def discover_replays(inputs: list[Path]) -> list[Path]:
    """Resolve replay files, episode directories, and batch directories."""

    found: set[Path] = set()
    for raw in inputs:
        path = raw.expanduser().resolve()
        if path.is_file():
            found.add(path)
            continue
        if not path.is_dir():
            raise ValueError(f"input does not exist: {raw}")
        direct = next((path / name for name in REPLAY_NAMES if (path / name).is_file()), None)
        if direct is not None:
            found.add(direct)
            continue
        for name in REPLAY_NAMES:
            found.update(candidate.resolve() for candidate in path.rglob(name))
        found.update(candidate.resolve() for candidate in path.rglob("*.cwreplay"))
    return sorted(found)


def replay_metadata(replay: Path) -> dict[str, Any]:
    """Read the artifact downloader's adjacent episode provenance, when present."""

    episode_path = replay.parent / "episode.json"
    if not episode_path.is_file():
        return {}
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    participants = episode.get("participants") or []
    wowborg = next(
        (row for row in participants if row.get("policy_name") == "wowborg"), None
    )
    policy_results = episode.get("policy_results") or []
    if wowborg is None:
        result = next(
            (
                row
                for row in policy_results
                if (row.get("policy") or {}).get("name") == "wowborg"
            ),
            None,
        )
        wowborg = (result or {}).get("policy")
    tags = episode.get("tags") or {}
    request_id = tags.get("experience_request_id")
    if request_id is None:
        request_id = next(
            (part for part in replay.parts if part.startswith("xreq_")), None
        )
    score = None
    scores = episode.get("participant_scores") or []
    if scores:
        score = scores[0].get("score")
    elif policy_results:
        score = policy_results[0].get("avg_reward")
    return {
        "episode_id": episode.get("episode_id") or episode.get("id"),
        "experience_request_id": request_id,
        "created_at": episode.get("created_at"),
        "policy_version": (wowborg or {}).get("version"),
        "score": score,
    }


def unique_replays(replays: list[Path]) -> tuple[list[Path], list[dict[str, str]]]:
    """Drop exact replay duplicates while retaining an auditable duplicate list."""

    seen: dict[str, Path] = {}
    unique: list[Path] = []
    duplicates: list[dict[str, str]] = []
    for replay in replays:
        digest = hashlib.sha256(replay.read_bytes()).hexdigest()
        if digest in seen:
            duplicates.append({"replay": str(replay), "same_as": str(seen[digest])})
        else:
            seen[digest] = replay
            unique.append(replay)
    return unique, duplicates


def _distance(left: dict[str, Any], right: dict[str, Any]) -> float:
    return math.dist((left["x"], left["y"], left["z"]), (right["x"], right["y"], right["z"]))


def cluster_unstuck_incidents(incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse retry bursts into one stuck episode at one location.

    Requests within 60 seconds and 10 yards belong to the same episode. The
    duration begins at the earliest request minus its preceding stationary time.
    Raw invocations and outcomes remain available alongside these clusters.
    """

    clusters: list[dict[str, Any]] = []
    for incident in sorted(incidents, key=lambda row: row["requested_elapsed_seconds"]):
        requested = incident["requested_elapsed_seconds"]
        origin = incident["origin"]
        joins_previous = bool(
            clusters
            and requested - clusters[-1]["last_request_seconds"] <= 60.0
            and _distance(origin, clusters[-1]["location"]) <= 10.0
        )
        if not joins_previous:
            clusters.append(
                {
                    "started_seconds": max(
                        0.0, requested - incident["preceding_stationary_seconds"]
                    ),
                    "ended_seconds": requested,
                    "last_request_seconds": requested,
                    "location": origin,
                    "invocations": 0,
                    "outcomes": {},
                }
            )
        cluster = clusters[-1]
        cluster["started_seconds"] = min(
            cluster["started_seconds"],
            max(0.0, requested - incident["preceding_stationary_seconds"]),
        )
        cluster["ended_seconds"] = max(
            requested,
            incident.get("failure_elapsed_seconds") or 0.0,
            incident.get("relocation_elapsed_seconds") or 0.0,
            cluster["ended_seconds"],
        )
        cluster["last_request_seconds"] = requested
        cluster["invocations"] += 1
        outcome = incident["outcome"]
        cluster["outcomes"][outcome] = cluster["outcomes"].get(outcome, 0) + 1

    for cluster in clusters:
        cluster["duration_seconds"] = round(
            cluster["ended_seconds"] - cluster["started_seconds"], 2
        )
        cluster.pop("last_request_seconds")
    return clusters


def interval_union_seconds(intervals: list[tuple[float, float]]) -> float:
    """Return elapsed time covered by overlapping intervals exactly once."""

    total = 0.0
    current_start: float | None = None
    current_end: float | None = None
    for start, end in sorted(intervals):
        if current_start is None:
            current_start, current_end = start, end
        elif start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    if current_start is not None:
        total += current_end - current_start
    return round(total, 2)


def _nearest_location(events: list[dict[str, Any]], elapsed: float) -> dict[str, Any] | None:
    candidates = [event for event in events if event.get("player_location") is not None]
    if not candidates:
        return None
    return min(candidates, key=lambda event: abs(event["elapsed_seconds"] - elapsed))[
        "player_location"
    ]


def _death_events(pov: dict[str, Any]) -> list[dict[str, Any]]:
    timeline = pov["timeline"]
    return [
        {
            "elapsed_seconds": event["elapsed_seconds"],
            "location": _nearest_location(timeline["events"], event["elapsed_seconds"]),
            "label": event["label"],
        }
        for event in timeline["semantic_events"]
        if event["category"] == "death"
    ]


def _damage_events(pov: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "elapsed_seconds": event["elapsed_seconds"],
            "amount": event["amount"],
            "source_guid": event["actor_guid"],
            "source_name": event["target_name"],
            "player_health_before": event["player_health"],
            "location": event["player_location"],
        }
        for event in pov["timeline"]["events"]
        if event["kind"] == "CombatPacketDamage" and event.get("amount") is not None
    ]


def _aura_evidence(pov: dict[str, Any]) -> dict[str, Any]:
    observed: set[int] = set(pov["start_state"]["active_aura_spell_ids"])
    observed.update(pov["end_state"]["active_aura_spell_ids"])
    movement = next(
        observation for observation in pov["observations"] if observation["domain"] == "movement"
    )
    longest = movement["evidence"].get("longest_stationary_interval")
    if longest:
        observed.update(longest["start_state"]["active_aura_spell_ids"])
        observed.update(longest["end_state"]["active_aura_spell_ids"])
    return {
        "start_ids": pov["start_state"]["active_aura_spell_ids"],
        "end_ids": pov["end_state"]["active_aura_spell_ids"],
        "observed_ids": sorted(observed),
        "observed_named": {
            str(spell_id): FORM_SPELLS[spell_id]
            for spell_id in sorted(observed)
            if spell_id in FORM_SPELLS
        },
    }


def profile_pov(
    pov: dict[str, Any], *, replay: Path, metadata: dict[str, Any]
) -> dict[str, Any]:
    progress = pov["progress"]
    traffic = pov["traffic"]
    combat = pov["combat"]
    movement = next(
        observation for observation in pov["observations"] if observation["domain"] == "movement"
    )["evidence"]
    recovery = next(
        observation for observation in pov["observations"] if observation["domain"] == "recovery"
    )
    incidents = pov["unstuck_incidents"]
    duration = sum(progress["life_state_seconds"].values())
    requested_forms = {
        spell_id: count
        for spell_id_text, count in traffic["cast_spell_ids"].items()
        if (spell_id := int(spell_id_text)) in FORM_SPELLS
    }
    longest = movement.get("longest_stationary_interval")
    stuck_episodes = cluster_unstuck_incidents(incidents)
    return {
        "replay": str(replay),
        "provenance": metadata,
        "member": pov["name"],
        "duration_seconds": round(duration, 2),
        "life": {
            "start": pov["start_state"]["life_state"],
            "end": pov["end_state"]["life_state"],
            "seconds": progress["life_state_seconds"],
            "ghost_fraction": round(progress["life_state_seconds"]["ghost"] / duration, 4)
            if duration
            else 0.0,
            "deaths": _death_events(pov),
        },
        "movement": {
            "path_yards": progress["path_distance_yards"],
            "displacement_yards": progress["displacement_yards"],
            "maximum_excursion_yards": movement.get("maximum_displacement_yards"),
            "efficiency": progress["path_efficiency"],
            "longest_stationary_seconds": progress["longest_stationary_seconds"],
            "longest_stationary_interval": longest,
            "stuck_episode_count": len(stuck_episodes),
            "stuck_episodes": stuck_episodes,
            "stuck_union_seconds": interval_union_seconds(
                [
                    (episode["started_seconds"], episode["ended_seconds"])
                    for episode in stuck_episodes
                ]
            ),
            "unstuck_invocations": len(incidents),
            "unstuck_outcomes": dict(Counter(row["outcome"] for row in incidents)),
        },
        "combat": {
            "seconds": progress["combat_seconds"],
            "damage_in": combat["incoming_damage"],
            "damage_in_events": combat["incoming_damage_events"],
            "damage_out": combat["outgoing_damage"],
            "damage_out_events": combat["outgoing_damage_events"],
            "attack_packets": traffic["attack_packets"],
            "damage_sources": pov["combat_attention"]["incoming_damage_sources"],
            "damage_events": _damage_events(pov),
        },
        "recovery": {
            "status": recovery["status"],
            "release_spirit": traffic["release_spirit_packets"],
            "reclaim_corpse": traffic["reclaim_corpse_packets"],
            "spirit_healer": traffic["spirit_healer_packets"],
            "spirit_healer_confirmed": traffic[
                "spirit_healer_confirmation_admitted_packets"
            ],
            "resurrect_responses": traffic["resurrect_response_packets"],
        },
        "spells": {
            "requests": traffic["cast_spell_ids"],
            "starts": combat["spell_start_ids"],
            "effects": combat["spell_go_ids"],
            "failed_spell_events": combat["failed_spell_ids"],
            "failure_codes": combat["cast_failure_codes"],
            "requested_forms": {
                str(spell_id): {"name": FORM_SPELLS[spell_id], "count": count}
                for spell_id, count in sorted(requested_forms.items())
            },
            "auras": _aura_evidence(pov),
        },
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    life = Counter()
    spell_requests = Counter()
    spell_effects = Counter()
    damage_sources: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        life.update(row["life"]["seconds"])
        spell_requests.update(row["spells"]["requests"])
        spell_effects.update(row["spells"]["effects"])
        for source in row["combat"]["damage_sources"]:
            key = (source["guid"], source.get("name") or "unknown")
            aggregate_source = damage_sources.setdefault(
                key,
                {
                    "guid": source["guid"],
                    "entry": source.get("entry"),
                    "name": source.get("name"),
                    "damage": 0,
                    "events": 0,
                },
            )
            aggregate_source["damage"] += source["damage"]
            aggregate_source["events"] += source["event_count"]
    duration = sum(life.values())
    return {
        "replays": len({row["replay"] for row in rows}),
        "members": len(rows),
        "ended_ghost": sum(row["life"]["end"] == "ghost" for row in rows),
        "deaths": sum(len(row["life"]["deaths"]) for row in rows),
        "life_state_seconds": dict(life),
        "ghost_fraction": round(life["ghost"] / duration, 4) if duration else 0.0,
        "stuck_episodes": sum(row["movement"]["stuck_episode_count"] for row in rows),
        "stuck_retry_window_seconds": round(
            sum(
                episode["duration_seconds"]
                for row in rows
                for episode in row["movement"]["stuck_episodes"]
            ),
            2,
        ),
        "stuck_union_seconds": round(
            sum(row["movement"]["stuck_union_seconds"] for row in rows), 2
        ),
        "unstuck_invocations": sum(row["movement"]["unstuck_invocations"] for row in rows),
        "longest_stationary_seconds": max(
            (row["movement"]["longest_stationary_seconds"] for row in rows), default=0.0
        ),
        "damage_in": sum(row["combat"]["damage_in"] for row in rows),
        "damage_out": sum(row["combat"]["damage_out"] for row in rows),
        "attack_packets": sum(row["combat"]["attack_packets"] for row in rows),
        "recovery": {
            "release_spirit": sum(row["recovery"]["release_spirit"] for row in rows),
            "reclaim_corpse": sum(row["recovery"]["reclaim_corpse"] for row in rows),
            "spirit_healer": sum(row["recovery"]["spirit_healer"] for row in rows),
            "spirit_healer_confirmed": sum(
                row["recovery"]["spirit_healer_confirmed"] for row in rows
            ),
            "resurrect_responses": sum(
                row["recovery"]["resurrect_responses"] for row in rows
            ),
        },
        "damage_sources": sorted(
            damage_sources.values(), key=lambda source: source["damage"], reverse=True
        ),
        "spell_requests": dict(spell_requests),
        "spell_effects": dict(spell_effects),
    }


def build_report(replays: list[Path], *, owner_repo: Path) -> dict[str, Any]:
    if not owner_repo.joinpath("observe/inspect_party_wire_replay.nim").is_file():
        raise ValueError(
            f"canonical replay inspector missing under owner repo: {owner_repo}"
        )
    discovered_count = len(replays)
    replays, duplicates = unique_replays(replays)
    rows: list[dict[str, Any]] = []
    for replay in replays:
        diagnostics = inspect_replay(replay, repo_root=owner_repo)
        if not isinstance(diagnostics, PlayerReplayDiagnostics):
            raise ValueError(f"expected one replay report for {replay}, got history")
        payload = diagnostics.model_dump(mode="json")
        metadata = replay_metadata(replay)
        rows.extend(
            profile_pov(pov, replay=replay, metadata=metadata)
            for pov in payload["povs"]
        )
    versions: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        version = row["provenance"].get("policy_version")
        versions.setdefault(str(version) if version is not None else "unknown", []).append(row)
    return {
        "coverage": {
            "discovered_replays": discovered_count,
            "unique_replays": len(replays),
            "duplicate_replays": duplicates,
        },
        "summary": aggregate(rows),
        "by_version": {version: aggregate(group) for version, group in versions.items()},
        "members": rows,
    }


def render(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        (
            f"WoW replay batch: {summary['replays']} replay(s), "
            f"{summary['members']} member stream(s)"
        ),
        (
            f"life: deaths={summary['deaths']} ended_ghost={summary['ended_ghost']} "
            f"ghost={summary['life_state_seconds'].get('ghost', 0):.1f}s/"
            f"{summary['ghost_fraction']:.1%}"
        ),
        (
            f"stuck: episodes={summary['stuck_episodes']} "
            f"retry_window_time={summary['stuck_retry_window_seconds']:.1f}s "
            f"unstuck_invocations={summary['unstuck_invocations']} "
            f"longest_stationary={summary['longest_stationary_seconds']:.1f}s"
        ),
        (
            f"combat: damage_in={summary['damage_in']} "
            f"damage_out={summary['damage_out']} attacks={summary['attack_packets']}"
        ),
        (
            f"recovery: release={summary['recovery']['release_spirit']} "
            f"reclaim={summary['recovery']['reclaim_corpse']} "
            f"spirit_healer={summary['recovery']['spirit_healer']}/"
            f"{summary['recovery']['spirit_healer_confirmed']}confirmed "
            f"resurrect_responses={summary['recovery']['resurrect_responses']}"
        ),
    ]
    for row in report["members"]:
        replay_path = Path(row["replay"])
        replay_label = (
            replay_path.parent.name if replay_path.name == "replay.json" else replay_path.stem
        )
        movement = row["movement"]
        combat = row["combat"]
        life = row["life"]
        lines.append(
            f"{replay_label}/{row['member']}: "
            f"{life['start']}->{life['end']} ghost={life['seconds']['ghost']:.1f}s "
            f"stuck={movement['stuck_episode_count']}/{movement['unstuck_invocations']} "
            f"stationary_max={movement['longest_stationary_seconds']:.1f}s "
            f"damage={combat['damage_in']}in/{combat['damage_out']}out"
        )
        for death in life["deaths"]:
            location = death["location"]
            where = (
                f"({location['x']:.1f},{location['y']:.1f},{location['z']:.1f})"
                if location
                else "unknown"
            )
            lines.append(f"  death @{death['elapsed_seconds']:.1f}s {where}")
        for stuck in movement["stuck_episodes"]:
            location = stuck["location"]
            lines.append(
                f"  stuck {stuck['duration_seconds']:.1f}s "
                f"@({location['x']:.1f},{location['y']:.1f},{location['z']:.1f}) "
                f"invocations={stuck['invocations']} outcomes={stuck['outcomes']}"
            )
        if row["spells"]["requested_forms"]:
            forms = ", ".join(
                f"{item['name']} x{item['count']}"
                for item in row["spells"]["requested_forms"].values()
            )
            lines.append(f"  requested forms: {forms}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--owner-repo", type=Path, default=DEFAULT_OWNER_REPO)
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    parser.add_argument("--json-out", type=Path, help="Also write the full JSON report.")
    args = parser.parse_args(argv)

    try:
        replays = discover_replays(args.inputs)
        if not replays:
            raise ValueError("no replay files found")
        report = build_report(replays, owner_repo=args.owner_repo.expanduser().resolve())
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
