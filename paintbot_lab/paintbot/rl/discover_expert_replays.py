#!/usr/bin/env python3
"""Discover and manifest all replay-bearing CTF/Paintbot expert episodes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from softmax import auth


PAGE_SIZE = 500
SOURCE_COMMIT_PATTERN = re.compile(r"/(?:tree|commit)/([0-9a-f]{40})(?:/|$)")
GAME_VERSION_PATTERN = re.compile(r'^\s*GameVersion\*?\s*=\s*"([0-9]+)"', re.MULTILINE)
GAME_VERSION_PATHS = (
    "src/ctf/sim_types.nim",
    "src/ctf/types.nim",
    "src/ctf/sim.nim",
)


class ObservatoryClient:
    def __init__(self) -> None:
        api_server = auth.get_api_server().rstrip("/")
        token = auth.load_current_token(server=api_server)
        if not token:
            raise RuntimeError("not authenticated; run `uv run softmax login`")
        self.http = httpx.Client(
            base_url=api_server + "/observatory",
            headers={
                "X-Auth-Token": token,
                "X-Use-Elevated-Privileges": "true",
            },
            timeout=120,
            follow_redirects=True,
        )

    def close(self) -> None:
        self.http.close()

    def request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        maximum_attempts = 20
        for attempt in range(1, maximum_attempts + 1):
            try:
                response = self.http.request(method, path, **kwargs)
                if response.status_code not in {429, 502, 503, 504}:
                    response.raise_for_status()
                    return response.json()
            except (httpx.HTTPError, json.JSONDecodeError):
                if attempt == maximum_attempts:
                    raise
            if attempt == maximum_attempts:
                response.raise_for_status()
            time.sleep(min(2**attempt, 30))
        raise AssertionError("retry loop did not return")


def query_path(workspace: Path, expert: dict[str, str], coworld_name: str) -> Path:
    safe_label = re.sub(r"[^a-z0-9]+", "-", expert["label"].lower()).strip("-")
    return workspace / "queries" / f"{safe_label}-{coworld_name}.jsonl"


def discover_query(
    client: ObservatoryClient,
    workspace: Path,
    expert: dict[str, str],
    coworld_name: str,
    max_rows: int | None,
    discovery_not_before: str,
    discovery_window_hours: int,
) -> int:
    output = query_path(workspace, expert, coworld_name)
    state_path = output.with_suffix(".state.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    written = int(state.get("rows", 0))
    if state.get("complete"):
        return written
    not_before = datetime.fromisoformat(
        state.get("not_before", discovery_not_before).replace("Z", "+00:00")
    )
    window_hours = int(state.get("window_hours", discovery_window_hours))
    initial_upper = state.get("window_upper") or state.get("before_created_at")
    window_upper = (
        datetime.fromisoformat(initial_upper.replace("Z", "+00:00"))
        if initial_upper
        else datetime.now(timezone.utc) + timedelta(days=1)
    )
    cursor = state.get("window_cursor")

    def timestamp(value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")

    while (max_rows is None or written < max_rows) and window_upper > not_before:
        window_lower = max(not_before, window_upper - timedelta(hours=window_hours))
        page_upper = cursor or timestamp(window_upper)
        clauses: list[dict[str, Any]] = [
            {"op": "eq", "field": "coworld.name", "value": coworld_name},
            {"op": "exists", "field": "replay_url", "value": True},
            {
                "op": "eq",
                "field": "policy.player_id",
                "value": expert["player_id"],
            },
            {
                "op": "gte",
                "field": "created_at",
                "value": timestamp(window_lower),
            },
            {"op": "lt", "field": "created_at", "value": page_upper},
        ]
        limit = PAGE_SIZE
        if max_rows is not None:
            limit = min(limit, max_rows - written)
        payload = {
            "where": {"op": "and", "clauses": clauses},
            "order_by": "created_at",
            "order_dir": "desc",
            "limit": limit,
            "offset": 0,
        }
        page = client.request_json("POST", "/v2/episodes/search", json=payload)
        entries = page.get("entries") or []
        if not entries:
            window_upper = window_lower
            cursor = None
            complete = window_upper <= not_before
            state = {
                "complete": complete,
                "rows": written,
                "not_before": timestamp(not_before),
                "window_hours": window_hours,
                "window_upper": timestamp(window_upper),
                "window_cursor": None,
            }
            state_path.write_text(json.dumps(state, indent=2) + "\n")
            continue
        with output.open("a") as destination:
            for entry in entries:
                destination.write(json.dumps(entry) + "\n")
        written += len(entries)
        next_cursor = entries[-1]["created_at"]
        if next_cursor == page_upper:
            raise RuntimeError(f"episode search cursor did not advance for {output}")
        cursor = next_cursor
        window_complete = len(entries) < limit
        if window_complete:
            window_upper = window_lower
            cursor = None
        complete = window_upper <= not_before
        state = {
            "complete": complete,
            "rows": written,
            "not_before": timestamp(not_before),
            "window_hours": window_hours,
            "window_upper": timestamp(window_upper),
            "window_cursor": cursor,
        }
        state_path.write_text(json.dumps(state, indent=2) + "\n")
        print(
            f"{expert['label']} {coworld_name}: {written} rows "
            f"(window count {page.get('total_count')})",
            flush=True,
        )
        if complete:
            break
    return written


def discover_query_with_client(
    workspace: Path,
    expert: dict[str, str],
    coworld_name: str,
    max_rows: int | None,
    discovery_not_before: str,
    discovery_window_hours: int,
) -> int:
    client = ObservatoryClient()
    try:
        return discover_query(
            client,
            workspace,
            expert,
            coworld_name,
            max_rows,
            discovery_not_before,
            discovery_window_hours,
        )
    finally:
        client.close()


def read_discovered_rows(workspace: Path, config: dict[str, Any]) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for expert in config["experts"]:
        for coworld_name in config["coworld_names"]:
            path = query_path(workspace, expert, coworld_name)
            if not path.exists():
                continue
            with path.open() as source:
                for line in source:
                    row = json.loads(line)
                    rows[row["episode_id"]] = row
    return rows


def resolve_coworlds(
    client: ObservatoryClient, workspace: Path, rows: dict[str, dict]
) -> tuple[dict[str, dict], dict[str, str]]:
    cache_path = workspace / "coworlds.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    failures: dict[str, str] = {}
    for coworld_id in sorted({row["coworld_id"] for row in rows.values()}):
        if coworld_id in cache:
            continue
        try:
            cache[coworld_id] = client.request_json("GET", f"/v2/coworlds/{coworld_id}")
            cache_path.write_text(json.dumps(cache, indent=2) + "\n")
        except Exception as error:  # Preserve the rest of a very large discovery run.
            failures[coworld_id] = str(error)
    return cache, failures


def source_commit(coworld: dict[str, Any]) -> str:
    source_url = coworld["manifest"]["game"]["runnable"]["source_url"]
    match = SOURCE_COMMIT_PATTERN.search(source_url)
    if match is None:
        raise ValueError(f"source URL is not pinned to a full commit: {source_url}")
    return match.group(1)


def resolve_game_versions(
    commits: set[str], repository: str, workspace: Path
) -> tuple[dict[str, str], dict[str, str]]:
    cache_path = workspace / "game_versions.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    failures: dict[str, str] = {}
    repository = repository.removesuffix(".git")
    raw_root = repository.replace("https://github.com/", "https://raw.githubusercontent.com/")
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for commit in sorted(commits):
            if commit in cache:
                continue
            for path in GAME_VERSION_PATHS:
                response = client.get(f"{raw_root}/{commit}/{path}")
                if response.status_code != 200:
                    continue
                match = GAME_VERSION_PATTERN.search(response.text)
                if match is not None:
                    cache[commit] = match.group(1)
                    cache_path.write_text(json.dumps(cache, indent=2) + "\n")
                    break
            if commit not in cache:
                failures[commit] = "GameVersion constant not found in known source paths"
    return cache, failures


def split_for(episode_id: str, percentages: dict[str, int]) -> str:
    bucket = int.from_bytes(hashlib.sha256(episode_id.encode()).digest()[:8], "big") % 100
    train_end = percentages["train"]
    validation_end = train_end + percentages["validation"]
    if bucket < train_end:
        return "train"
    if bucket < validation_end:
        return "validation"
    return "test"


def write_manifest(
    config: dict[str, Any],
    workspace: Path,
    rows: dict[str, dict],
    coworlds: dict[str, dict],
    game_versions: dict[str, str],
    resolution_failures: dict[str, str],
) -> dict[str, Any]:
    expert_ids = {item["player_id"] for item in config["experts"]}
    episodes = []
    exclusions = Counter()
    for episode_id, row in sorted(rows.items(), key=lambda item: item[1]["created_at"]):
        coworld = coworlds.get(row["coworld_id"])
        if coworld is None:
            exclusions["coworld_unresolved"] += 1
            continue
        try:
            commit = source_commit(coworld)
        except (KeyError, TypeError, ValueError):
            exclusions["source_unpinned"] += 1
            continue
        game_version = game_versions.get(commit)
        if game_version is None:
            exclusions["game_version_unresolved"] += 1
            continue
        policies = [
            policy
            for policy in row.get("policies") or ()
            if policy.get("player_id") in expert_ids
        ]
        version_ids = sorted({policy["policy_version_id"] for policy in policies})
        if not version_ids:
            exclusions["expert_policy_missing"] += 1
            continue
        episodes.append(
            {
                "episode_id": episode_id,
                "game_version": game_version,
                "source_commit": commit,
                "split": split_for(episode_id, config["split_percentages"]),
                "povs": "expert_policies",
                "expert_policy_version_ids": version_ids,
                "max_povs_per_policy": config["max_povs_per_policy"],
                "created_at": row["created_at"],
                "coworld_id": row["coworld_id"],
                "coworld_name": row["coworld_name"],
                "coworld_version": row["coworld_version"],
                "expert_policies": policies,
            }
        )

    manifest = {
        "schema_version": 1,
        "source_repository": config["source_repository"],
        "preparation": config["preparation"],
        "training": config["training"],
        "experts": config["experts"],
        "episodes": episodes,
    }
    manifest_path = workspace / "expert-replay-pool-v1.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    by_version = Counter(episode["game_version"] for episode in episodes)
    by_world = Counter(episode["coworld_name"] for episode in episodes)
    by_split = Counter(episode["split"] for episode in episodes)
    summary = {
        "schema_version": 1,
        "discovered_unique_episodes": len(rows),
        "manifest_episodes": len(episodes),
        "expert_policy_trajectories": sum(
            len(episode["expert_policy_version_ids"]) for episode in episodes
        ),
        "by_game_version": dict(sorted(by_version.items(), key=lambda item: int(item[0]))),
        "by_coworld_name": dict(sorted(by_world.items())),
        "by_split": dict(sorted(by_split.items())),
        "exclusions": dict(sorted(exclusions.items())),
        "resolution_failures": resolution_failures,
        "manifest": str(manifest_path),
    }
    (workspace / "discovery_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--max-episodes-per-expert-world", type=int)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if sum(config["split_percentages"].values()) != 100:
        raise ValueError("split_percentages must sum to 100")
    args.workspace.mkdir(parents=True, exist_ok=True)

    if args.workers <= 0:
        parser.error("--workers must be positive")
    queries = [
        (expert, coworld_name)
        for expert in config["experts"]
        for coworld_name in config["coworld_names"]
    ]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                discover_query_with_client,
                args.workspace,
                expert,
                coworld_name,
                args.max_episodes_per_expert_world,
                config["discovery_not_before"],
                config["discovery_window_hours"],
            )
            for expert, coworld_name in queries
        ]
        for future in futures:
            future.result()

    client = ObservatoryClient()
    try:
        rows = read_discovered_rows(args.workspace, config)
        coworlds, coworld_failures = resolve_coworlds(client, args.workspace, rows)
    finally:
        client.close()

    commits = set()
    source_failures = {}
    for coworld_id, coworld in coworlds.items():
        try:
            commits.add(source_commit(coworld))
        except (KeyError, TypeError, ValueError) as error:
            source_failures[coworld_id] = str(error)
    game_versions, game_version_failures = resolve_game_versions(
        commits, config["source_repository"], args.workspace
    )
    failures = {
        "coworlds": coworld_failures,
        "sources": source_failures,
        "game_versions": game_version_failures,
    }
    write_manifest(config, args.workspace, rows, coworlds, game_versions, failures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
