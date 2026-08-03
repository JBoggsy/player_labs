#!/usr/bin/env python3
"""Turn CTF Round Warehouse outputs into a policy-comparison report.

This consumes the hosted reporter's manifest, events, and player_stats parts.
It does not re-simulate replays or depend on Beacon telemetry, so it is the fast
first pass for every completed league round. Use the local event warehouse only
when a finding needs policy-internal traces or spatial sequence reconstruction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

WAREHOUSE_VERSION = "rv_bf89a010-14be-4c76-a73c-2fd280e83779"
SOFTMAX_API = "https://softmax.com/api"
ACTION_KEYS = {"shot_impact", "grenade_impact", "spray_use"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_columns(path: Path, required: set[str]) -> list[dict[str, Any]]:
    table = pq.read_table(path)
    missing = required - set(table.column_names)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    return table.to_pylist()


def _download_latest(output_dir: Path) -> tuple[Path, Path, Path]:
    token = subprocess.check_output(
        ["softmax", "get-token", "--server", SOFTMAX_API],
        text=True,
    ).strip()

    def get(path: str) -> bytes:
        request = urllib.request.Request(
            f"{SOFTMAX_API}/observatory{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "player-labs/ctf-warehouse-analysis",
            },
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()

    query = urllib.parse.urlencode(
        {"reporter_version_id": WAREHOUSE_VERSION, "status": "completed", "limit": 1}
    )
    runs = json.loads(get(f"/v2/reporters/runs?{query}"))
    if not runs:
        raise ValueError(f"no completed runs for Warehouse {WAREHOUSE_VERSION}")
    run_id = runs[0]["id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "manifest": output_dir / "manifest.json",
        "events": output_dir / "events.parquet",
        "player_stats": output_dir / "player_stats.parquet",
    }
    for name, path in paths.items():
        path.write_bytes(get(f"/v2/reporters/runs/{run_id}/output/{name}"))
    (output_dir / "source.json").write_text(
        json.dumps(
            {
                "reporter_version_id": WAREHOUSE_VERSION,
                "reporter_run_id": run_id,
                "subject": runs[0].get("subject"),
                "completed_at": runs[0].get("completed_at"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return paths["manifest"], paths["events"], paths["player_stats"]


def _event_metrics(events: list[dict[str, Any]]) -> dict[tuple[str, str], Counter]:
    metrics: dict[tuple[str, str], Counter] = defaultdict(Counter)
    spray_actions: dict[tuple[str, str], set[int]] = defaultdict(set)
    spray_enemy_hits: dict[tuple[str, str], set[int]] = defaultdict(set)

    for event in events:
        name = event.get("policy_name")
        version = event.get("policy_version")
        if not name or not version:
            continue
        identity = (name, version)
        key = event["key"]
        metrics[identity][key] += 1
        value = json.loads(event["value"])

        if key == "spray_use" and value.get("action_id") is not None:
            spray_actions[identity].add(value["action_id"])
        if key not in ACTION_KEYS:
            continue

        enemy_damage = 0
        friendly_damage = 0
        for damage in value.get("damages", []):
            amount = int(damage.get("amount", 0))
            if damage.get("team") == event.get("team"):
                friendly_damage += amount
            else:
                enemy_damage += amount
        metrics[identity]["enemy_damage"] += enemy_damage
        metrics[identity]["friendly_damage"] += friendly_damage
        if key == "shot_impact" and enemy_damage:
            metrics[identity]["gun_enemy_hits"] += 1
        elif key == "grenade_impact" and enemy_damage:
            metrics[identity]["grenade_enemy_hits"] += 1
        elif key == "spray_use" and enemy_damage:
            spray_enemy_hits[identity].add(value["action_id"])

    for identity, action_ids in spray_actions.items():
        metrics[identity]["spray_actions"] = len(action_ids)
        metrics[identity]["spray_enemy_hits"] = len(spray_enemy_hits[identity])
    return metrics


def analyze(
    manifest_path: Path,
    events_path: Path,
    player_stats_path: Path,
    focus: str | None,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    stats = _require_columns(
        player_stats_path,
        {
            "episode_id",
            "policy_name",
            "policy_version",
            "won",
            "kills",
            "deaths",
            "flag_steals",
            "deliveries",
            "deaths_while_carrying",
            "first_steal_tick",
            "carry_ticks",
            "ticks_alive",
            "time_in_enemy_half_frac",
        },
    )
    events = _require_columns(
        events_path,
        {"episode_id", "policy_name", "policy_version", "team", "key", "value"},
    )
    event_metrics = _event_metrics(events)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in stats:
        if row["policy_name"] and row["policy_version"]:
            grouped[(row["policy_name"], row["policy_version"])].append(row)

    policies = []
    for identity, rows in grouped.items():
        name, version = identity
        count = len(rows)
        event = event_metrics[identity]
        steals = sum(row["flag_steals"] for row in rows)
        deliveries = sum(row["deliveries"] for row in rows)
        gun_fires = event["gun_fire"]
        first_steals = [row["first_steal_tick"] for row in rows if row["first_steal_tick"] >= 0]
        policies.append(
            {
                "policy_name": name,
                "policy_version": version,
                "player_games": count,
                "episodes": len({row["episode_id"] for row in rows}),
                "win_rate": sum(row["won"] for row in rows) / count,
                "kills_per_player_game": sum(row["kills"] for row in rows) / count,
                "deaths_per_player_game": sum(row["deaths"] for row in rows) / count,
                "gun_fires_per_player_game": gun_fires / count,
                "gun_enemy_hit_rate": event["gun_enemy_hits"] / max(1, gun_fires),
                "enemy_damage_per_player_game": event["enemy_damage"] / count,
                "friendly_damage_per_player_game": event["friendly_damage"] / count,
                "grenade_throws_per_player_game": event["grenade_throw"] / count,
                "grenade_enemy_hit_rate": event["grenade_enemy_hits"] / max(1, event["grenade_impact"]),
                "spray_actions_per_player_game": event["spray_actions"] / count,
                "spray_enemy_hit_rate": event["spray_enemy_hits"] / max(1, event["spray_actions"]),
                "steals": steals,
                "steals_per_player_game": steals / count,
                "deliveries": deliveries,
                "steal_delivery_rate": deliveries / max(1, steals),
                "carrier_deaths": sum(row["deaths_while_carrying"] for row in rows),
                "mean_first_steal_tick": sum(first_steals) / len(first_steals) if first_steals else None,
                "carry_ticks_per_player_game": sum(row["carry_ticks"] for row in rows) / count,
                "ticks_alive_per_player_game": sum(row["ticks_alive"] for row in rows) / count,
                "enemy_half_fraction": sum(row["time_in_enemy_half_frac"] for row in rows) / count,
            }
        )
    policies.sort(key=lambda row: (-row["win_rate"], row["policy_name"]))

    result: dict[str, Any] = {
        "schema_version": "ctf.reporter-warehouse-player-report.v1",
        "warehouse": {
            "reporter_version_id": WAREHOUSE_VERSION,
            "round_id": manifest.get("round_id"),
            "ctf_ref": manifest.get("ctf_ref"),
            "episodes_ok": manifest.get("episodes_ok"),
            "events_written": manifest.get("events_written"),
            "player_stats_rows": manifest.get("player_stats_rows"),
            "manifest_sha256": _sha256(manifest_path),
            "events_sha256": _sha256(events_path),
            "player_stats_sha256": _sha256(player_stats_path),
        },
        "policies": policies,
        "interpretation_limits": [
            "One league round is a screening sample, not a promotion verdict.",
            "Team win rate is composition-dependent; use matched experience requests for causal comparisons.",
            "Warehouse events are ground truth but do not expose a policy's internal belief or decision trace.",
        ],
    }
    if focus:
        matches = [row for row in policies if row["policy_name"].lower() == focus.lower()]
        if not matches:
            raise ValueError(f"focus policy {focus!r} is absent")
        subject = matches[0]
        steal_leader = max(policies, key=lambda row: row["steals_per_player_game"])
        hit_leader = max(policies, key=lambda row: row["gun_enemy_hit_rate"])
        result["focus"] = {
            "policy": subject,
            "comparisons": {
                "steal_rate_vs_leader": subject["steals_per_player_game"]
                / max(steal_leader["steals_per_player_game"], 1e-12),
                "steal_rate_leader": steal_leader["policy_name"],
                "gun_hit_rate_vs_leader": subject["gun_enemy_hit_rate"]
                / max(hit_leader["gun_enemy_hit_rate"], 1e-12),
                "gun_hit_rate_leader": hit_leader["policy_name"],
            },
        }
    return result


def markdown(report: dict[str, Any]) -> str:
    warehouse = report["warehouse"]
    lines = [
        "# CTF Warehouse player comparison",
        "",
        f"Round `{warehouse['round_id']}`; Warehouse `{warehouse['reporter_version_id']}`; "
        f"{warehouse['episodes_ok']} episodes.",
        "",
        "| Policy | Win | K/D | Gun hit | FF dmg/pg | Steals | Deliveries | Delivery | Enemy half |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["policies"]:
        lines.append(
            f"| {row['policy_name']} | {row['win_rate']:.0%} | "
            f"{row['kills_per_player_game']:.2f}/{row['deaths_per_player_game']:.2f} | "
            f"{row['gun_enemy_hit_rate']:.0%} | {row['friendly_damage_per_player_game']:.2f} | "
            f"{row['steals']} | {row['deliveries']} | {row['steal_delivery_rate']:.0%} | "
            f"{row['enemy_half_fraction']:.0%} |"
        )
    lines.extend(["", "## Interpretation limits", ""])
    lines.extend(f"- {limit}" for limit in report["interpretation_limits"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--player-stats", type=Path)
    parser.add_argument(
        "--latest",
        action="store_true",
        help=f"download the latest completed Warehouse {WAREHOUSE_VERSION} run",
    )
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument("--focus")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()

    if args.latest:
        if args.download_dir is None:
            parser.error("--latest requires --download-dir")
        manifest, events, player_stats = _download_latest(args.download_dir)
    else:
        if not (args.manifest and args.events and args.player_stats):
            parser.error("provide --manifest, --events, and --player-stats, or use --latest")
        manifest, events, player_stats = args.manifest, args.events, args.player_stats
    report = analyze(manifest, events, player_stats, args.focus)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(encoded)
    if args.markdown_out:
        args.markdown_out.write_text(markdown(report))
    if not args.json_out and not args.markdown_out:
        print(encoded, end="")


if __name__ == "__main__":
    main()
