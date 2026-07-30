"""Infer an opponent's order-like battle plan from CTF replay trajectories.

This is an observational reverse-engineering tool, not a mind reader. It turns
hash-validated simulator positions into evidence-backed hypotheses:

* ``hold`` — a group remains inside a bounded area for most of a time window;
* ``move`` — its median trajectory makes material progress between locations;
* ``maneuver`` — motion is too local or inconsistent for either label;
* ``groups`` — seats remain near one another and, when moving, travel in similar
  directions across repeated episodes.

The method deliberately follows established trajectory-analysis primitives:
diameter + duration stop detection, and persistent proximity/co-motion grouping.
CTF has only eight agents per team and exact simulator coordinates, so the tool
implements those small deterministic calculations directly instead of adding the
GeoPandas/MovingPandas stack or fitting a large clustering model.

All positions are normalized into Red's left-to-right frame. A Blue opponent is
mirrored automatically, making reports comparable across team assignment.

Usage:
    uv run python ctf_lab/tools/infer_battle_plan.py \
      --episodes ctf_lab/scratch/eval_v39_training/episodes_focusfire \
      --policy ctf-focusfire --version 63 \
      --out ctf_lab/scratch/eval_v39_training/focusfire_plan

Writes ``<out>.json`` and ``<out>.md``. The replay reader must match the deployed
game ref; build it with ``ctf_lab/tools/build_expand_replay.sh``.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Iterable

TICKS_PER_SEC = 24
MAP_MAX_X = 1234
LAB_DIR = Path(__file__).resolve().parent.parent
DEFAULT_EXPAND = LAB_DIR / "tools" / "bin" / "expand_replay_json"
POI_PATH = LAB_DIR / "ctf" / "beacon" / "mapdata" / "points_of_interest.json"


@dataclasses.dataclass(frozen=True)
class Point:
    tick: int
    x: float
    y: float


@dataclasses.dataclass
class EpisodeTeam:
    episode_id: str
    team: str
    seats: dict[int, list[Point]]
    end_tick: int


@dataclasses.dataclass(frozen=True)
class SeatWindow:
    episode_id: str
    seat: int
    start: tuple[float, float]
    end: tuple[float, float]
    center: tuple[float, float]
    diameter: float
    path: float
    displacement: float
    kind: str


def log(message: str) -> None:
    print(message, file=sys.stderr)


def median(values: Iterable[float]) -> float:
    values = list(values)
    return float(statistics.median(values)) if values else 0.0


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _episode_dirs(paths: list[Path]) -> list[Path]:
    found: dict[Path, None] = {}
    for path in paths:
        if (path / "episode.json").is_file():
            found[path] = None
            continue
        if not path.exists():
            continue
        for episode_json in path.rglob("episode.json"):
            found[episode_json.parent] = None
    return sorted(found)


def _find_replay(ep_dir: Path) -> Path | None:
    for name in ("replay.json", "replay.bitreplay"):
        path = ep_dir / name
        if path.is_file():
            return path
    return None


def _participants(episode: dict) -> list[dict]:
    participants = episode.get("participants") or []
    if participants:
        return participants
    return [
        {
            "position": agent.get("agent_id"),
            "policy_name": (policy_result.get("policy") or {}).get("name"),
            "version": (policy_result.get("policy") or {}).get("version"),
        }
        for policy_result in episode.get("policy_results") or []
        for agent in policy_result.get("agents") or []
    ]


def _expand(replay: Path, expand_bin: Path, sample_ticks: int) -> tuple[list[dict], dict]:
    try:
        proc = subprocess.run(
            [str(expand_bin), str(replay), str(sample_ticks)],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], {"hash_failed": True, "error": str(exc)}

    rows: list[dict] = []
    meta: dict = {}
    for line in proc.stdout.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("key") == "_meta":
            meta = row.get("value") or {}
        else:
            rows.append(row)
    if proc.returncode or meta.get("hash_failed"):
        meta["hash_failed"] = True
        meta.setdefault("error", proc.stderr.strip())
    return rows, meta


def load_episode_teams(
    episode_dirs: list[Path],
    *,
    policy: str,
    version: int | None,
    expand_bin: Path,
    sample_ticks: int,
) -> tuple[list[EpisodeTeam], list[dict]]:
    loaded: list[EpisodeTeam] = []
    skipped: list[dict] = []

    for ep_dir in episode_dirs:
        episode = json.loads((ep_dir / "episode.json").read_text())
        episode_id = str(episode.get("id") or ep_dir.name)
        target_slots = [
            int(part["position"])
            for part in _participants(episode)
            if part.get("position") is not None
            and part.get("policy_name") == policy
            and (version is None or int(part.get("version", -1)) == version)
        ]
        if not target_slots:
            skipped.append({"episode_id": episode_id, "reason": "policy_not_present"})
            continue
        replay = _find_replay(ep_dir)
        if replay is None:
            skipped.append({"episode_id": episode_id, "reason": "missing_replay"})
            continue

        rows, meta = _expand(replay, expand_bin, sample_ticks)
        if meta.get("hash_failed"):
            skipped.append(
                {
                    "episode_id": episode_id,
                    "reason": "replay_hash_failed",
                    "detail": meta.get("error") or meta.get("fail_tick"),
                }
            )
            continue
        playing_tick = next(
            (
                int(row["ts"])
                for row in rows
                if row.get("key") == "phase"
                and "Playing" in json.dumps(row.get("value"))
            ),
            0,
        )
        by_team: dict[str, dict[int, list[Point]]] = {
            "red": collections.defaultdict(list),
            "blue": collections.defaultdict(list),
        }
        target = set(target_slots)
        for row in rows:
            if row.get("key") != "pos" or row.get("player") not in target:
                continue
            value = row.get("value") or {}
            if not value.get("alive"):
                continue
            slot = int(row["player"])
            team = "red" if slot % 2 == 0 else "blue"
            x = float(value["x"])
            if team == "blue":
                x = MAP_MAX_X - x
            by_team[team][slot // 2].append(
                Point(int(row["ts"]) - playing_tick, x, float(value["y"]))
            )

        for team, seat_points in by_team.items():
            if not seat_points:
                continue
            end_tick = max(point.tick for points in seat_points.values() for point in points)
            loaded.append(
                EpisodeTeam(
                    episode_id=episode_id,
                    team=team,
                    seats={seat: sorted(points, key=lambda p: p.tick) for seat, points in seat_points.items()},
                    end_tick=end_tick,
                )
            )
    return loaded, skipped


def _window_points(points: list[Point], start: int, end: int) -> list[Point]:
    return [point for point in points if start <= point.tick < end]


def _seat_window(
    episode_id: str,
    seat: int,
    points: list[Point],
    *,
    hold_diameter: float,
    move_distance: float,
) -> SeatWindow | None:
    if len(points) < 2:
        return None
    start = (points[0].x, points[0].y)
    end = (points[-1].x, points[-1].y)
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    center = (median(xs), median(ys))
    # Bounding-box diagonal is a conservative, O(n) upper bound on stop diameter.
    diameter = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    path = sum(
        math.hypot(b.x - a.x, b.y - a.y)
        for a, b in zip(points, points[1:], strict=False)
    )
    displacement = distance(start, end)
    if diameter <= hold_diameter:
        kind = "hold"
    elif displacement >= move_distance:
        kind = "move"
    else:
        kind = "maneuver"
    return SeatWindow(
        episode_id=episode_id,
        seat=seat,
        start=start,
        end=end,
        center=center,
        diameter=diameter,
        path=path,
        displacement=displacement,
        kind=kind,
    )


def _paired_points(
    left: list[Point],
    right: list[Point],
    start: int,
    end: int,
) -> list[tuple[Point, Point]]:
    left_by_tick = {point.tick: point for point in left if start <= point.tick < end}
    right_by_tick = {point.tick: point for point in right if start <= point.tick < end}
    return [(left_by_tick[tick], right_by_tick[tick]) for tick in sorted(left_by_tick.keys() & right_by_tick)]


def _pair_affinity(
    episodes: list[EpisodeTeam],
    seat_a: int,
    seat_b: int,
    start: int,
    end: int,
    group_radius: float,
) -> tuple[float, int]:
    scores: list[float] = []
    for episode in episodes:
        pairs = _paired_points(
            episode.seats.get(seat_a, []),
            episode.seats.get(seat_b, []),
            start,
            end,
        )
        if len(pairs) < 2:
            continue
        near = sum(
            distance((a.x, a.y), (b.x, b.y)) <= group_radius for a, b in pairs
        ) / len(pairs)
        a0, b0 = pairs[0]
        a1, b1 = pairs[-1]
        av = (a1.x - a0.x, a1.y - a0.y)
        bv = (b1.x - b0.x, b1.y - b0.y)
        amag = math.hypot(*av)
        bmag = math.hypot(*bv)
        if amag < 20 and bmag < 20:
            direction = 1.0
        elif amag and bmag:
            direction = max(0.0, min(1.0, (av[0] * bv[0] + av[1] * bv[1]) / (amag * bmag)))
        else:
            direction = 0.0
        scores.append(0.75 * near + 0.25 * direction)
    return (median(scores), len(scores))


def _groups(
    seats: list[int],
    affinities: dict[tuple[int, int], float],
    threshold: float,
) -> list[list[int]]:
    """Small complete-link grouping: every member must agree with every other."""
    groups: list[list[int]] = []
    # Start with the most-connected seats so a weak chain cannot merge two groups.
    ordered = sorted(
        seats,
        key=lambda seat: -sum(
            affinities.get(tuple(sorted((seat, other))), 0.0)
            for other in seats
            if other != seat
        ),
    )
    for seat in ordered:
        candidates = [
            group
            for group in groups
            if all(
                affinities.get(tuple(sorted((seat, member))), 0.0) >= threshold
                for member in group
            )
        ]
        if candidates:
            max(candidates, key=len).append(seat)
        else:
            groups.append([seat])
    return sorted((sorted(group) for group in groups), key=lambda group: group[0])


def _load_pois() -> list[tuple[str, float, float]]:
    doc = json.loads(POI_PATH.read_text())
    return [
        (point["name"], float(point["x"]), float(point["y"]))
        for point in doc.get("points") or []
    ] + [
        (area["name"], float(area["cx"]), float(area["cy"]))
        for area in doc.get("areas") or []
    ]


def _nearest_poi(xy: tuple[float, float], pois: list[tuple[str, float, float]]) -> dict:
    name, x, y = min(pois, key=lambda poi: math.hypot(xy[0] - poi[1], xy[1] - poi[2]))
    return {
        "name": name,
        "distance_px": round(distance(xy, (x, y)), 1),
        "x": round(xy[0], 1),
        "y": round(xy[1], 1),
    }


def _group_order(
    group: list[int],
    seat_windows: list[SeatWindow],
    pair_affinities: dict[tuple[int, int], float],
    episode_count: int,
    pois: list[tuple[str, float, float]],
) -> dict:
    members = [window for window in seat_windows if window.seat in group]
    kinds = collections.Counter(window.kind for window in members)
    if not members:
        kind = "unknown"
    else:
        kind, _ = kinds.most_common(1)[0]
    start = (
        median(window.start[0] for window in members),
        median(window.start[1] for window in members),
    )
    end = (
        median(window.end[0] for window in members),
        median(window.end[1] for window in members),
    )
    center = (
        median(window.center[0] for window in members),
        median(window.center[1] for window in members),
    )
    aggregate_displacement = distance(start, end)
    start_poi = _nearest_poi(start, pois)
    end_poi = _nearest_poi(end, pois)
    # A majority of individual trajectories can be moving in incompatible
    # directions (respawn churn / local combat). Do not call that one group MOVE
    # when the aggregate start and destination are effectively unchanged.
    if kind == "move" and (
        aggregate_displacement < 0.5 * median(window.displacement for window in members)
        or start_poi["name"] == end_poi["name"]
    ):
        kind = "maneuver"
    pairs = [
        pair_affinities[tuple(sorted((a, b)))]
        for i, a in enumerate(group)
        for b in group[i + 1 :]
        if tuple(sorted((a, b))) in pair_affinities
    ]
    kind_agreement = kinds[kind] / len(members) if members and kind in kinds else 0.0
    support_episodes = len({window.episode_id for window in members})
    confidence = min(
        support_episodes / max(1, episode_count),
        kind_agreement,
        median(pairs) if pairs else 1.0,
    )
    location = center if kind == "hold" else end
    order = {
        "group": group,
        "kind": kind,
        "at" if kind == "hold" else "to": _nearest_poi(location, pois),
        "confidence": round(confidence, 2),
        "support_episodes": support_episodes,
        "kind_counts": dict(kinds),
        "median_displacement_px": round(median(window.displacement for window in members), 1),
        "median_diameter_px": round(median(window.diameter for window in members), 1),
    }
    if kind == "move":
        order["from"] = start_poi
    return order


def infer(
    episodes: list[EpisodeTeam],
    *,
    window_ticks: int,
    hold_diameter: float,
    move_distance: float,
    group_radius: float,
    group_threshold: float,
    min_support: float,
    max_ticks: int,
) -> list[dict]:
    pois = _load_pois()
    max_tick = max((episode.end_tick for episode in episodes), default=0)
    if max_ticks > 0:
        max_tick = min(max_tick, max_ticks)
    all_seats = sorted({seat for episode in episodes for seat in episode.seats})
    windows: list[dict] = []

    for start in range(0, max_tick, window_ticks):
        end = start + window_ticks
        seat_windows: list[SeatWindow] = []
        for episode in episodes:
            for seat in all_seats:
                feature = _seat_window(
                    episode.episode_id,
                    seat,
                    _window_points(episode.seats.get(seat, []), start, end),
                    hold_diameter=hold_diameter,
                    move_distance=move_distance,
                )
                if feature is not None:
                    seat_windows.append(feature)
        required_support = max(1, math.ceil(len(episodes) * min_support))
        support = len({window.episode_id for window in seat_windows})
        if support < required_support:
            continue
        seat_support = collections.Counter(window.seat for window in seat_windows)
        active_seats = [seat for seat in all_seats if seat_support[seat] >= required_support]
        if not active_seats:
            continue

        affinities: dict[tuple[int, int], float] = {}
        affinity_support: dict[tuple[int, int], int] = {}
        for i, seat_a in enumerate(active_seats):
            for seat_b in active_seats[i + 1 :]:
                key = (seat_a, seat_b)
                affinities[key], affinity_support[key] = _pair_affinity(
                    episodes, seat_a, seat_b, start, end, group_radius
                )
        groups = _groups(active_seats, affinities, group_threshold)
        orders = [
            _group_order(group, seat_windows, affinities, len(episodes), pois)
            for group in groups
        ]
        windows.append(
            {
                "start_tick": start,
                "end_tick": end,
                "start_seconds": round(start / TICKS_PER_SEC, 1),
                "end_seconds": round(end / TICKS_PER_SEC, 1),
                "support_episodes": support,
                "orders": orders,
                "pair_affinity": {
                    f"{a}-{b}": {
                        "score": round(score, 3),
                        "support_episodes": affinity_support[(a, b)],
                    }
                    for (a, b), score in affinities.items()
                },
            }
        )
    return windows


def _markdown(report: dict) -> str:
    target = report["target"]
    version = f":v{target['version']}" if target.get("version") is not None else ""
    lines = [
        f"# Inferred battle plan: `{target['policy']}{version}`",
        "",
        "> Observed order-like behavior inferred from replay trajectories. These are",
        "> hypotheses with confidence/support, not the opponent's literal source orders.",
        "",
        f"- Episodes analyzed: **{report['episodes_analyzed']}**",
        f"- Teams normalized: **{report['team_samples']}**",
        f"- Replay sampling: every **{report['parameters']['sample_ticks']} ticks**",
        f"- Analysis window: **{report['parameters']['window_ticks']} ticks** "
        f"({report['parameters']['window_ticks'] / TICKS_PER_SEC:g}s)",
        "",
        "## Timeline",
        "",
        "| Time | Group | Inferred order | Location | Confidence | Support |",
        "|---|---|---|---|---:|---:|",
    ]
    for window in report["windows"]:
        span = f"{window['start_seconds']:g}-{window['end_seconds']:g}s"
        for order in window["orders"]:
            location = order.get("at") or order.get("to") or {}
            if order["kind"] == "move":
                source = (order.get("from") or {}).get("name", "?")
                description = f"{source} -> {location.get('name', '?')}"
            else:
                description = location.get("name", "?")
            group = ",".join(str(seat) for seat in order["group"])
            lines.append(
                f"| {span} | `{group}` | {order['kind']} | {description} | "
                f"{order['confidence']:.2f} | {order['support_episodes']} |"
            )
    if report["skipped"]:
        reasons = collections.Counter(row["reason"] for row in report["skipped"])
        lines.extend(
            [
                "",
                "## Skipped inputs",
                "",
                *[f"- {reason}: {count}" for reason, count in sorted(reasons.items())],
            ]
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `hold` uses a diameter-and-duration rule; local peeking and ducking can remain a hold.",
            "- `move` requires material net displacement during the window.",
            "- Groups require persistent proximity and compatible motion across repeated episodes.",
            "- Low-confidence or `maneuver` rows should be inspected in the replay viewer before being",
            "  translated into a counter-plan.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episodes", type=Path, action="append", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--version", type=int)
    parser.add_argument("--out", type=Path, required=True, help="output stem (.json/.md are added)")
    parser.add_argument("--expand-replay", type=Path, default=DEFAULT_EXPAND)
    parser.add_argument("--sample-ticks", type=int, default=12, help="position interval (default 0.5s)")
    parser.add_argument("--window-ticks", type=int, default=120, help="inference window (default 5s)")
    parser.add_argument("--hold-diameter", type=float, default=100.0)
    parser.add_argument("--move-distance", type=float, default=80.0)
    parser.add_argument("--group-radius", type=float, default=220.0)
    parser.add_argument("--group-threshold", type=float, default=0.55)
    parser.add_argument("--min-support", type=float, default=0.5)
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=60 * TICKS_PER_SEC,
        help="opening horizon to infer (default 60s; 0 analyzes the full game)",
    )
    args = parser.parse_args()

    if not args.expand_replay.is_file():
        raise SystemExit(
            f"missing replay reader: {args.expand_replay}; run ctf_lab/tools/build_expand_replay.sh"
        )
    episode_dirs = _episode_dirs(args.episodes)
    if not episode_dirs:
        raise SystemExit("no episode.json files found under --episodes paths")
    teams, skipped = load_episode_teams(
        episode_dirs,
        policy=args.policy,
        version=args.version,
        expand_bin=args.expand_replay,
        sample_ticks=args.sample_ticks,
    )
    if not teams:
        raise SystemExit(f"no usable replay teams for {args.policy}")
    windows = infer(
        teams,
        window_ticks=args.window_ticks,
        hold_diameter=args.hold_diameter,
        move_distance=args.move_distance,
        group_radius=args.group_radius,
        group_threshold=args.group_threshold,
        min_support=args.min_support,
        max_ticks=args.max_ticks,
    )
    report = {
        "schema": "ctf.inferred-battle-plan.v1",
        "target": {"policy": args.policy, "version": args.version},
        "episodes_analyzed": len({team.episode_id for team in teams}),
        "team_samples": len(teams),
        "coordinate_frame": "red_attack_left_to_right",
        "parameters": {
            "sample_ticks": args.sample_ticks,
            "window_ticks": args.window_ticks,
            "hold_diameter": args.hold_diameter,
            "move_distance": args.move_distance,
            "group_radius": args.group_radius,
            "group_threshold": args.group_threshold,
            "min_support": args.min_support,
            "max_ticks": args.max_ticks,
        },
        "windows": windows,
        "skipped": skipped,
    }
    json_path = args.out.with_suffix(".json")
    md_path = args.out.with_suffix(".md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(_markdown(report))
    log(
        f"wrote {json_path} and {md_path}: {report['episodes_analyzed']} episodes, "
        f"{len(windows)} windows"
    )


if __name__ == "__main__":
    main()
