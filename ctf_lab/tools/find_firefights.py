"""Detect human-meaningful CTF firefights from Reporter Lab warehouse events.

The detector works from *unique authoritative combat actions*, not expanded shot
windows. It builds a local spatiotemporal action graph per episode, keeps connected
components with genuine reciprocal fire, and weights each fight by activity,
reciprocity, damage, casualties, participant breadth, and persistence.

Reporter inputs are ``events.parquet`` files emitted by the CTF roundwarehouse
component through ``run_roundwarehouse_local.py``.

Usage:
    uv run python ctf_lab/tools/find_firefights.py \
        ctf_lab/scratch/eval_v39_training/reporter_roundwarehouse \
        --policy beacon --version-id 8c7e... --json fights.json
"""

from __future__ import annotations

import argparse
import collections
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pyarrow.parquet as pq

TICKS_PER_SECOND = 24


@dataclass(frozen=True)
class Action:
    """One released weapon action; gun stages are correlated into one row."""

    episode_id: str
    tick: int
    seq: int
    slot: int
    team: str
    weapon: str
    action_id: int
    origin: tuple[float, float]
    impact: tuple[float, float]
    damages: tuple[dict[str, Any], ...]

    @property
    def victims(self) -> frozenset[int]:
        return frozenset(int(d["slot"]) for d in self.damages)

    @property
    def damage(self) -> float:
        return sum(float(d.get("amount", 0.0)) for d in self.damages)

    @property
    def anchors(self) -> tuple[tuple[float, float], ...]:
        return (self.origin, self.impact)


@dataclass(frozen=True)
class DetectorConfig:
    max_gap_ticks: int = 2 * TICKS_PER_SECOND
    locality_radius: float = 360.0
    threat_radius: float = 110.0
    min_team_actions: int = 2
    min_total_actions: int = 5
    clip_padding_ticks: int = TICKS_PER_SECOND


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def _json_value(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("value", "{}")
    return json.loads(value) if isinstance(value, str) else value


def _point(value: dict[str, Any]) -> tuple[float, float]:
    return float(value["x"]), float(value["y"])


def actions_from_rows(rows: Iterable[dict[str, Any]]) -> list[Action]:
    """Collapse Reporter gun stages and return one row per released weapon action."""
    rows = list(rows)
    gun_origins: dict[tuple[str, int], tuple[float, float]] = {}
    grenade_origins: dict[tuple[str, int], tuple[float, float]] = {}
    for row in rows:
        if row["key"] not in {"gun_fire", "grenade_throw"}:
            continue
        value = _json_value(row)
        key = (row["episode_id"], int(value["action_id"]))
        if row["key"] == "gun_fire":
            gun_origins[key] = _point(value)
        else:
            grenade_origins[key] = _point(value)

    actions: list[Action] = []
    seen: set[tuple[str, str, int, int]] = set()
    for row in rows:
        key_name = row["key"]
        if key_name not in {"shot_impact", "grenade_impact", "spray_use"}:
            continue
        team = row.get("team")
        if team not in {"red", "blue"}:
            continue
        value = _json_value(row)
        action_id = int(value["action_id"])
        dedupe_key = (row["episode_id"], key_name, action_id, int(row["tick"]))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        event_key = (row["episode_id"], action_id)
        impact = _point(value)
        if key_name == "shot_impact":
            origin = gun_origins.get(event_key, impact)
            weapon = "gun"
        elif key_name == "grenade_impact":
            origin = grenade_origins.get(event_key, impact)
            weapon = "grenade"
        else:
            origin = impact
            weapon = "spray"
        actions.append(
            Action(
                episode_id=row["episode_id"],
                tick=int(row["tick"]),
                seq=int(row["seq"]),
                slot=int(row["slot"]),
                team=team,
                weapon=weapon,
                action_id=action_id,
                origin=origin,
                impact=impact,
                damages=tuple(value.get("damages", [])),
            )
        )
    return sorted(actions, key=lambda action: (action.episode_id, action.tick, action.seq))


def _distance(left: tuple[float, float], right: tuple[float, float]) -> float:
    return math.hypot(left[0] - right[0], left[1] - right[1])


def _minimum_anchor_distance(left: Action, right: Action) -> float:
    return min(_distance(a, b) for a in left.anchors for b in right.anchors)


def _directly_opposed(left: Action, right: Action) -> bool:
    return right.slot in left.victims or left.slot in right.victims


def _linked(left: Action, right: Action, config: DetectorConfig) -> bool:
    if right.tick - left.tick > config.max_gap_ticks:
        return False
    if _directly_opposed(left, right):
        return True
    if _distance(left.origin, right.origin) <= config.locality_radius:
        return True
    if left.team != right.team:
        return (
            _distance(left.impact, right.origin) <= config.threat_radius
            or _distance(right.impact, left.origin) <= config.threat_radius
        )
    return _minimum_anchor_distance(left, right) <= config.locality_radius


def action_components(
    actions: list[Action], config: DetectorConfig
) -> tuple[list[list[Action]], dict[int, int]]:
    """Spatiotemporal connected components plus opposing-team edge counts."""
    if not actions:
        return [], {}
    dsu = DisjointSet(len(actions))
    cross_edges: list[tuple[int, int]] = []
    lower = 0
    for right_index, right in enumerate(actions):
        while actions[lower].tick < right.tick - config.max_gap_ticks:
            lower += 1
        for left_index in range(lower, right_index):
            left = actions[left_index]
            if _linked(left, right, config):
                dsu.union(left_index, right_index)
                if left.team != right.team:
                    cross_edges.append((left_index, right_index))

    grouped: dict[int, list[Action]] = collections.defaultdict(list)
    for index, action in enumerate(actions):
        grouped[dsu.find(index)].append(action)
    cross_counts: collections.Counter[int] = collections.Counter()
    for left_index, _right_index in cross_edges:
        cross_counts[dsu.find(left_index)] += 1
    return list(grouped.values()), dict(cross_counts)


def _saturating(value: float, scale: float) -> float:
    return 1.0 - math.exp(-value / scale)


def _fight_metrics(
    actions: list[Action],
    *,
    cross_team_links: int,
    kills: list[dict[str, Any]],
    config: DetectorConfig,
) -> dict[str, Any] | None:
    team_actions = collections.Counter(action.team for action in actions)
    if (
        team_actions["red"] < config.min_team_actions
        or team_actions["blue"] < config.min_team_actions
        or len(actions) < config.min_total_actions
        or cross_team_links == 0
    ):
        return None

    start_tick = min(action.tick for action in actions)
    end_tick = max(action.tick for action in actions)
    duration_ticks = end_tick - start_tick + 1
    team_damage = collections.Counter()
    attackers = {"red": set(), "blue": set()}
    victims = {"red": set(), "blue": set()}
    weapon_counts = collections.Counter()
    damage_events = 0
    for action in actions:
        attackers[action.team].add(action.slot)
        weapon_counts[action.weapon] += 1
        if action.damages:
            damage_events += 1
        team_damage[action.team] += action.damage
        for victim in action.damages:
            victim_team = victim.get("team")
            if victim_team in victims:
                victims[victim_team].add(int(victim["slot"]))

    # Attribute a kill only to the component containing its causal damage action.
    # Merely sharing a tick or actor would double-count kills when two spatially
    # separate fights happen at once.
    relevant_kills = [
        kill
        for kill in kills
        if any(
            action.slot == kill["slot"]
            and action.tick == kill["tick"]
            and kill["victim_slot"] in action.victims
            for action in actions
        )
    ]
    team_kills = collections.Counter(kill["team"] for kill in relevant_kills)
    action_balance = (
        2.0
        * min(team_actions["red"], team_actions["blue"])
        / (team_actions["red"] + team_actions["blue"])
    )
    total_damage = team_damage["red"] + team_damage["blue"]
    damage_balance = (
        2.0 * min(team_damage["red"], team_damage["blue"]) / total_damage
        if total_damage
        else 0.0
    )
    reciprocal_damage = team_damage["red"] > 0 and team_damage["blue"] > 0
    participants = (
        attackers["red"] | attackers["blue"] | victims["red"] | victims["blue"]
    )

    action_score = _saturating(len(actions), 12.0)
    damage_score = _saturating(total_damage, 100.0)
    casualty_score = _saturating(len(relevant_kills), 2.0)
    breadth_score = min(1.0, len(participants) / 8.0)
    duration_score = min(1.0, duration_ticks / (8 * TICKS_PER_SECOND))
    weight = round(
        100
        * (
            0.25 * action_score
            + 0.20 * action_balance
            + 0.20 * damage_score
            + 0.15 * casualty_score
            + 0.10 * breadth_score
            + 0.10 * duration_score
        ),
        1,
    )
    link_score = _saturating(cross_team_links, 6.0)
    evidence_score = min(1.0, damage_events / 3.0)
    confidence = round(
        0.35 * action_balance
        + 0.25 * link_score
        + 0.25 * evidence_score
        + 0.15 * min(1.0, len(actions) / 8.0),
        2,
    )

    mean_x = sum((a.origin[0] + a.impact[0]) / 2 for a in actions) / len(actions)
    mean_y = sum((a.origin[1] + a.impact[1]) / 2 for a in actions) / len(actions)
    if len(attackers["red"]) <= 1 and len(attackers["blue"]) <= 1:
        scale = "duel"
    elif len(participants) >= 8 or len(attackers["red"]) >= 3 or len(attackers["blue"]) >= 3:
        scale = "teamfight"
    else:
        scale = "skirmish"
    if weight >= 70:
        significance = "major"
    elif weight >= 45:
        significance = "standard"
    else:
        significance = "minor"

    return {
        "episode_id": actions[0].episode_id,
        "start_tick": start_tick,
        "end_tick": end_tick,
        "clip_start_tick": max(0, start_tick - config.clip_padding_ticks),
        "clip_end_tick": end_tick + config.clip_padding_ticks,
        "duration_ticks": duration_ticks,
        "duration_s": round(duration_ticks / TICKS_PER_SECOND, 2),
        "scale": scale,
        "significance": significance,
        "weight": weight,
        "confidence": confidence,
        "location": {"x": round(mean_x, 1), "y": round(mean_y, 1)},
        "actions": len(actions),
        "actions_by_team": dict(sorted(team_actions.items())),
        "action_balance": round(action_balance, 2),
        "weapons": dict(sorted(weapon_counts.items())),
        "damage": round(total_damage, 1),
        "damage_by_team": dict(sorted(team_damage.items())),
        "damage_balance": round(damage_balance, 2),
        "reciprocal_damage": reciprocal_damage,
        "kills": len(relevant_kills),
        "kills_by_team": dict(sorted(team_kills.items())),
        "participants": len(participants),
        "attackers_by_team": {
            team: sorted(slots) for team, slots in sorted(attackers.items())
        },
        "victims_by_team": {
            team: sorted(slots) for team, slots in sorted(victims.items())
        },
        "cross_team_links": cross_team_links,
    }


def _kill_rows(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_episode: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        if row["key"] != "kill" or row.get("team") not in {"red", "blue"}:
            continue
        value = _json_value(row)
        by_episode[row["episode_id"]].append(
            {
                "tick": int(row["tick"]),
                "slot": int(row["slot"]),
                "team": row["team"],
                "victim_slot": int(value["victim_slot"]),
            }
        )
    return by_episode


def detect_fights(
    rows: list[dict[str, Any]], config: DetectorConfig
) -> list[dict[str, Any]]:
    actions = actions_from_rows(rows)
    kills = _kill_rows(rows)
    by_episode: dict[str, list[Action]] = collections.defaultdict(list)
    for action in actions:
        by_episode[action.episode_id].append(action)

    fights = []
    for episode_id, episode_actions in sorted(by_episode.items()):
        components, _ = action_components(episode_actions, config)
        for component in components:
            # Recalculate cross-team links inside each final component. This stays
            # deterministic and avoids exposing union-find roots as an API.
            cross_links = sum(
                1
                for index, right in enumerate(component)
                for left in component[:index]
                if left.team != right.team and _linked(left, right, config)
            )
            fight = _fight_metrics(
                component,
                cross_team_links=cross_links,
                kills=kills.get(episode_id, []),
                config=config,
            )
            if fight is not None:
                fights.append(fight)
    return sorted(fights, key=lambda fight: (-fight["weight"], fight["episode_id"], fight["start_tick"]))


def load_rows(
    input_path: Path,
    *,
    policy: str | None,
    version_id: str | None,
    opponent: str | None,
) -> list[dict[str, Any]]:
    parquet_path = input_path / "events.parquet" if input_path.is_dir() else input_path
    if not parquet_path.is_file():
        raise FileNotFoundError(f"Reporter events Parquet not found: {parquet_path}")
    rows = pq.read_table(parquet_path).to_pylist()
    episode_policies: dict[str, set[str]] = collections.defaultdict(set)
    episode_versions: dict[str, set[str]] = collections.defaultdict(set)
    for row in rows:
        if row.get("policy_name"):
            episode_policies[row["episode_id"]].add(row["policy_name"])
        if row.get("policy_version"):
            episode_versions[row["episode_id"]].add(row["policy_version"])
    allowed = {
        episode_id
        for episode_id in episode_policies
        if (policy is None or policy in episode_policies[episode_id])
        and (opponent is None or opponent in episode_policies[episode_id])
        and (version_id is None or version_id in episode_versions[episode_id])
    }
    return [row for row in rows if row["episode_id"] in allowed]


def _document(fights: list[dict[str, Any]], config: DetectorConfig) -> dict[str, Any]:
    return {
        "schema_version": "ctf.replay-firefights.v2",
        "definition": (
            "reciprocal released weapon actions connected in time and space; "
            "counts are unique actions, not expanded window observations"
        ),
        "ticks_per_second": TICKS_PER_SECOND,
        "config": {
            "max_gap_ticks": config.max_gap_ticks,
            "locality_radius": config.locality_radius,
            "threat_radius": config.threat_radius,
            "min_team_actions": config.min_team_actions,
            "min_total_actions": config.min_total_actions,
            "clip_padding_ticks": config.clip_padding_ticks,
        },
        "weight_formula": {
            "action_volume": 0.25,
            "reciprocity": 0.20,
            "damage": 0.20,
            "casualties": 0.15,
            "participant_breadth": 0.10,
            "duration": 0.10,
        },
        "count": len(fights),
        "fights": fights,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path, help="Reporter output dir or events.parquet")
    parser.add_argument("--policy", help="require episodes containing this policy")
    parser.add_argument("--version-id", help="require episodes containing this immutable version")
    parser.add_argument("--opponent", help="require episodes containing this opponent")
    parser.add_argument("--max-gap", type=int, default=2 * TICKS_PER_SECOND)
    parser.add_argument("--radius", type=float, default=360.0)
    parser.add_argument("--threat-radius", type=float, default=110.0)
    parser.add_argument("--min-team-actions", type=int, default=2)
    parser.add_argument("--min-total-actions", type=int, default=5)
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    config = DetectorConfig(
        max_gap_ticks=args.max_gap,
        locality_radius=args.radius,
        threat_radius=args.threat_radius,
        min_team_actions=args.min_team_actions,
        min_total_actions=args.min_total_actions,
    )
    rows = load_rows(
        args.events,
        policy=args.policy,
        version_id=args.version_id,
        opponent=args.opponent,
    )
    fights = detect_fights(rows, config)
    episode_ids = {row["episode_id"] for row in rows}
    print(f"{len(episode_ids)} episodes scanned; {len(fights)} reciprocal firefights")
    print(
        f"{'episode':<30}{'ticks':>15}{'type':>11}{'acts':>6}"
        f"{'dmg':>7}{'K':>4}{'bal':>6}{'weight':>8}{'conf':>7}"
    )
    for fight in fights[: args.top]:
        print(
            f"{fight['episode_id'][:28]:<30}"
            f"{fight['start_tick']}-{fight['end_tick']:>7}"
            f"{fight['scale']:>11}{fight['actions']:>6}"
            f"{fight['damage']:>7.0f}{fight['kills']:>4}"
            f"{fight['action_balance']:>6.2f}{fight['weight']:>8.1f}"
            f"{fight['confidence']:>7.2f}"
        )
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(_document(fights, config), indent=2) + "\n")
        print(f"Wrote {args.json}")


if __name__ == "__main__":
    main()
