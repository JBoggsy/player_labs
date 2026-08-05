#!/usr/bin/env python3
"""Report the decision-driving metrics from one hosted Traverse episode.

The episode directory is the layout produced by the artifact fetcher:

* ``episode.json`` supplies the authoritative scored northing and Traverse fixture;
* ``replay.json`` supplies the character's accepted movement and spell casts;
* ``artifacts/policy_artifact_0.zip`` supplies wowborg's ``trace.jsonl``.

Usage:
  uv run python vanilla_wow_lab/tools/traverse_report.py EPISODE_DIR
  uv run python vanilla_wow_lab/tools/traverse_report.py EPISODE_DIR --json
"""

from __future__ import annotations

import argparse
import bisect
import importlib.util
import io
import json
import math
import struct
import sys
import zipfile
from pathlib import Path

TRAVEL_FORM_SPELL_ID = 783
CAST_SPELL_OPCODE = 302
FORWARD_MOVE_FLAG = 0x1

_CWREPLAY_PATH = Path(__file__).resolve().parent / "cwreplay.py"
_SPEC = importlib.util.spec_from_file_location("traverse_report_cwreplay", _CWREPLAY_PATH)
assert _SPEC is not None and _SPEC.loader is not None
cwreplay = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("traverse_report_cwreplay", cwreplay)
_SPEC.loader.exec_module(cwreplay)


def _load_trace(episode_dir: Path) -> list[dict]:
    direct = episode_dir / "trace.jsonl"
    if direct.is_file():
        raw = direct.read_bytes()
    else:
        bundle = episode_dir / "artifacts" / "policy_artifact_0.zip"
        if not bundle.is_file():
            return []
        with zipfile.ZipFile(bundle) as zf:
            try:
                raw = zf.read("trace.jsonl")
            except KeyError:
                return []
    return [json.loads(line) for line in io.BytesIO(raw).read().decode().splitlines() if line]


def _score_metrics(episode: dict) -> dict:
    traversal = episode.get("game_config", {}).get("kalimdor_traversal", {})
    start_world_x = traversal.get("start_world_x")
    goal_world_x = traversal.get("goal_world_x")
    participant_scores = episode.get("participant_scores") or []
    scores = episode.get("scores") or []
    score = (
        participant_scores[0].get("score")
        if participant_scores
        else scores[0].get("score") if scores else None
    )
    full_distance = (
        goal_world_x - start_world_x
        if start_world_x is not None and goal_world_x is not None
        else None
    )
    goal_fraction = (
        min(1.0, score / full_distance)
        if score is not None and full_distance is not None and full_distance > 0
        else None
    )
    return {
        "northing_yards": score,
        "authoritative_world_x": (
            start_world_x + score
            if start_world_x is not None and score is not None
            else None
        ),
        "start_world_x": start_world_x,
        "goal_world_x": goal_world_x,
        "goal_distance_yards": full_distance,
        "goal_fraction": goal_fraction,
        "reached_goal": (
            score >= full_distance
            if score is not None and full_distance is not None
            else None
        ),
    }


def _trace_metrics(events: list[dict]) -> dict:
    observations = sorted(
        (event for event in events if event.get("kind") == "observation"),
        key=lambda event: event.get("ts", 0.0),
    )
    deaths = 0
    prior_dead = False
    ghost_seconds = 0.0
    dead_or_ghost_seconds = 0.0
    for index, observation in enumerate(observations):
        dead = bool(observation.get("is_dead"))
        ghost = bool(observation.get("is_ghost"))
        if dead and not prior_dead:
            deaths += 1
        prior_dead = dead
        if index + 1 >= len(observations):
            continue
        elapsed = max(0.0, observations[index + 1]["ts"] - observation["ts"])
        if ghost:
            ghost_seconds += elapsed
        if dead or ghost:
            dead_or_ghost_seconds += elapsed

    travel_form_events = [
        {
            key: event.get(key)
            for key in ("ts", "activation", "success", "reason", "detail")
            if event.get(key) is not None
        }
        for event in events
        if event.get("kind") == "traverse_travel_form"
    ]
    strategy_end = next(
        (
            event
            for event in reversed(events)
            if event.get("kind") == "strategy_end" and event.get("strategy") == "traverse"
        ),
        {},
    )
    trace_available = bool(events)
    return {
        "available": trace_available,
        "observations": observations,
        "lifecycle": {
            "deaths": deaths if trace_available else None,
            "ghost_seconds": round(ghost_seconds, 1) if trace_available else None,
            "dead_or_ghost_seconds": (
                round(dead_or_ghost_seconds, 1) if trace_available else None
            ),
        },
        "travel_form_events": travel_form_events,
        "frontiers": {
            "attempted": (
                strategy_end.get(
                    "frontiers_attempted",
                    sum(event.get("kind") == "traverse_frontier" for event in events),
                )
                if trace_available
                else None
            ),
            "arrived": strategy_end.get("frontiers_arrived") if trace_available else None,
            "failures": (
                strategy_end.get(
                    "route_failures",
                    sum(
                        event.get("kind") == "traverse_route_failed"
                        for event in events
                    ),
                )
                if trace_available
                else None
            ),
        },
    }


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[int((len(ordered) - 1) * fraction)]


def _was_living(observations: list[dict], observation_times: list[float], when: float) -> bool:
    index = bisect.bisect_right(observation_times, when) - 1
    if index < 0:
        return False
    observation = observations[index]
    return not observation.get("is_dead") and not observation.get("is_ghost")


def _replay_metrics(replay_path: Path, observations: list[dict]) -> dict:
    replay = cwreplay.decode_replay(replay_path)
    if not replay.members:
        return {}
    member = replay.members[0]
    observation_times = [observation["ts"] for observation in observations]
    movement = []
    travel_form_casts = []
    first_server_ms = member.packets[0].server_ms if member.packets else 0
    for packet in member.packets:
        info = cwreplay._movement_info(packet)
        if info is not None:
            movement.append((packet, info))
        if packet.from_client and packet.opcode == CAST_SPELL_OPCODE and len(packet.body) >= 4:
            spell_id = struct.unpack_from("<I", packet.body)[0]
            if spell_id == TRAVEL_FORM_SPELL_ID:
                travel_form_casts.append(
                    round((packet.server_ms - first_server_ms) / 1000.0, 3)
                )

    trajectory_yards = 0.0
    living_speeds = []
    for (first_packet, first), (second_packet, second) in zip(movement, movement[1:]):
        displacement = math.hypot(second["x"] - first["x"], second["y"] - first["y"])
        trajectory_yards += displacement
        elapsed = (second_packet.server_ms - first_packet.server_ms) / 1000.0
        midpoint = (first_packet.unix_seconds + second_packet.unix_seconds) / 2.0
        if (
            0.2 <= elapsed <= 0.8
            and displacement >= 1.0
            and (
                first["move_flags"] & FORWARD_MOVE_FLAG
                or second["move_flags"] & FORWARD_MOVE_FLAG
            )
            and _was_living(observations, observation_times, midpoint)
        ):
            living_speeds.append(displacement / elapsed)

    duration_seconds = (
        (member.packets[-1].server_ms - member.packets[0].server_ms) / 1000.0
        if member.packets
        else 0.0
    )
    return {
        "member": member.name,
        "duration_seconds": round(duration_seconds, 1),
        "movement_packets": sum(
            packet.from_client and packet.opcode in cwreplay.MOVE_OPCODES_CLIENT
            for packet in member.packets
        ),
        "movement_position_samples": len(movement),
        "trajectory_yards": round(trajectory_yards, 1),
        "travel_form_783_casts": {
            "count": len(travel_form_casts),
            "seconds_from_replay_start": travel_form_casts,
        },
        "living_forward_speed_yards_per_second": {
            "samples": len(living_speeds),
            "p25": _rounded(_percentile(living_speeds, 0.25)),
            "median": _rounded(_percentile(living_speeds, 0.50)),
            "p90": _rounded(_percentile(living_speeds, 0.90)),
            "method": (
                "consecutive outbound movement samples; 0.2-0.8s apart; >=1yd "
                "horizontal displacement; forward flag set; trace says alive and non-ghost"
            ),
        },
    }


def _rounded(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def report_episode(episode_dir: Path) -> dict:
    episode_path = episode_dir / "episode.json"
    replay_path = episode_dir / "replay.json"
    if not episode_path.is_file():
        raise ValueError(f"{episode_dir}: missing episode.json")
    if not replay_path.is_file():
        raise ValueError(f"{episode_dir}: missing replay.json")
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    events = _load_trace(episode_dir)
    trace = _trace_metrics(events)
    replay = _replay_metrics(replay_path, trace.pop("observations"))
    participants = episode.get("participants") or []
    participant = participants[0] if participants else {}
    return {
        "episode_dir": str(episode_dir),
        "episode_request_id": episode.get("id"),
        "episode_id": episode.get("episode_id"),
        "job_id": episode.get("job_id"),
        "policy": (
            f"{participant.get('policy_name')}:v{participant.get('version')}"
            if participant.get("policy_name") is not None
            else None
        ),
        "trace_available": trace.pop("available"),
        "score": _score_metrics(episode),
        "travel_form": {
            **replay.pop("travel_form_783_casts", {"count": 0, "seconds_from_replay_start": []}),
            "activation_trace": trace.pop("travel_form_events"),
        },
        "lifecycle": trace.pop("lifecycle"),
        "frontiers": trace.pop("frontiers"),
        "replay": replay,
    }


def _render(report: dict) -> None:
    score = report["score"]
    travel = report["travel_form"]
    lifecycle = report["lifecycle"]
    frontiers = report["frontiers"]
    replay = report["replay"]
    speed = replay.get("living_forward_speed_yards_per_second", {})
    print(f"{report['policy'] or 'unknown policy'}  episode={report['episode_request_id']}")
    print(
        f"northing {score['northing_yards']:.2f} yd  world_x {score['authoritative_world_x']:.2f}  "
        f"goal {score['goal_fraction'] * 100:.2f}%  reached={score['reached_goal']}"
    )
    print(
        f"Travel Form 783: replay casts={travel['count']}  "
        f"trace events={len(travel['activation_trace'])}"
    )
    if report["trace_available"]:
        print(
            f"lifecycle: deaths={lifecycle['deaths']}  "
            f"ghost={lifecycle['ghost_seconds']:.1f}s  "
            f"dead-or-ghost={lifecycle['dead_or_ghost_seconds']:.1f}s"
        )
        print(
            f"frontiers: attempted={frontiers['attempted']}  "
            f"arrived={frontiers['arrived']}  failures={frontiers['failures']}"
        )
    else:
        print("lifecycle: unavailable (policy trace artifact missing)")
        print("frontiers: unavailable (policy trace artifact missing)")
    print(
        f"replay: trajectory={replay['trajectory_yards']:.1f} yd  "
        f"living forward speed p25/median/p90="
        f"{speed.get('p25')}/{speed.get('median')}/{speed.get('p90')} yd/s  "
        f"n={speed.get('samples')}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("episode_dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = report_episode(args.episode_dir)
    except (OSError, ValueError, zipfile.BadZipFile, cwreplay.ReplayError) as exc:
        print(f"traverse_report: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _render(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
