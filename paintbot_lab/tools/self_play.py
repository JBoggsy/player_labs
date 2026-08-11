#!/usr/bin/env python3
"""Run production-faithful Paintbot self-play at compute speed."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import shutil
import socket
import statistics
import subprocess
import sys
import time
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAME_REPO = REPO_ROOT.parent.parent / "coworlds" / "coworld-ctf"
GAME_CACHE = REPO_ROOT / "paintbot_lab" / ".cache" / "coworld-ctf"
CANONICAL_GAME_REMOTES = {
    "git@github.com:Metta-AI/coworld-ctf.git",
    "https://github.com/Metta-AI/coworld-ctf.git",
}
CANONICAL_SOURCE_PREFIX = "https://github.com/Metta-AI/coworld-ctf/tree/"
TEAM_NAMES = ("red", "blue", "green", "yellow")
MAP_SIZES = ("small", "standard", "large", "huge", "giant")


def parse_env(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        name, separator, content = value.partition("=")
        if not separator or not name:
            raise ValueError(f"environment override must be KEY=VALUE, got {value!r}")
        if not name.startswith("STENCIL_"):
            raise ValueError(f"self-play overrides must be STENCIL_* tunables, got {name!r}")
        result[name] = content
    return result


def run_checked(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"command failed ({' '.join(command)}): {detail}")
    return result.stdout


def resolve_live_paintbot() -> dict[str, Any]:
    coworld = Path(sys.executable).parent / "coworld"
    if not coworld.exists():
        resolved = shutil.which("coworld")
        if resolved is None:
            raise RuntimeError("project-local coworld CLI is unavailable; run `uv sync`")
        coworld = Path(resolved)
    output = run_checked([str(coworld), "list", "--json", "--limit", "500"])
    try:
        games = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("coworld list did not return valid JSON") from exc
    matches = [
        game for game in games
        if game.get("name") == "paintbot" and game.get("canonical") is True
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one canonical Paintbot version, found {len(matches)}"
        )
    game = matches[0]
    manifest = game.get("manifest") or {}
    source_url = manifest.get("game", {}).get("runnable", {}).get("source_url")
    match = re.fullmatch(
        re.escape(CANONICAL_SOURCE_PREFIX) + r"([0-9a-fA-F]{40})",
        source_url or "",
    )
    if not match:
        raise RuntimeError(
            f"canonical Paintbot has no full-SHA coworld-ctf source_url: {source_url!r}"
        )
    source_commit = match.group(1)
    return {
        "coworld_id": game["id"],
        "version": game["version"],
        "manifest_hash": game.get("manifest_hash"),
        "manifest": manifest,
        "source_url": source_url,
        "source_commit": source_commit.lower(),
    }


def prepare_game_source(source_repo: Path, source_commit: str) -> Path:
    if not (source_repo / ".git").exists():
        raise RuntimeError(f"game source clone is missing or not a Git repo: {source_repo}")
    origin = run_checked(["git", "remote", "get-url", "origin"], cwd=source_repo).strip()
    if origin not in CANONICAL_GAME_REMOTES:
        raise RuntimeError(f"game source origin is not canonical coworld-ctf: {origin}")
    run_checked(["git", "fetch", "--prune", "origin"], cwd=source_repo)
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
        cwd=source_repo,
        capture_output=True,
    ).returncode == 0
    if not exists:
        run_checked(["git", "fetch", "origin", source_commit], cwd=source_repo)
        run_checked(
            ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
            cwd=source_repo,
        )

    worktree = GAME_CACHE / source_commit
    if not worktree.exists():
        worktree.parent.mkdir(parents=True, exist_ok=True)
        run_checked(
            ["git", "worktree", "add", "--detach", str(worktree), source_commit],
            cwd=source_repo,
        )
    head = run_checked(["git", "rev-parse", "HEAD"], cwd=worktree).strip()
    status = run_checked(["git", "status", "--porcelain"], cwd=worktree).strip()
    if head != source_commit:
        raise RuntimeError(f"managed game worktree is on {head}, expected {source_commit}")
    if status:
        raise RuntimeError(f"managed game worktree is dirty: {worktree}")
    run_checked(["nimby", "sync", "-g", "nimby.lock"], cwd=worktree)
    return worktree


def ensure_game_binary(game_repo: Path, *, rebuild: bool) -> Path:
    binary = game_repo / "bin" / "ctf-selfplay"
    inputs = [game_repo / "nimby.lock", game_repo / "nim.cfg"]
    inputs.extend((game_repo / "src").rglob("*.nim"))
    newest_input = max(path.stat().st_mtime for path in inputs if path.exists())
    if rebuild or not binary.exists() or binary.stat().st_mtime < newest_input:
        binary.parent.mkdir(exist_ok=True)
        subprocess.run(
            ["nim", "c", "-d:release", f"--out:{binary}", "src/ctf.nim"],
            cwd=game_repo,
            check=True,
        )
    return binary


def ensure_stencil_nim_binary(game_repo: Path, source_commit: str, *, rebuild: bool) -> Path:
    """Compile the native stencil candidate against the canonical game's deps."""
    source_dir = REPO_ROOT / "paintbot_lab" / "paintbot" / "stencil_nim"
    sources = sorted(source_dir.rglob("*.nim"))
    if not sources:
        raise RuntimeError(f"native stencil source is missing: {source_dir}")
    binary = REPO_ROOT / "paintbot_lab" / ".cache" / "stencil-nim" / source_commit / "stencil"
    newest_input = max(
        [path.stat().st_mtime for path in sources]
        + [(game_repo / "nim.cfg").stat().st_mtime, (game_repo / "nimby.lock").stat().st_mtime]
    )
    if rebuild or not binary.exists() or binary.stat().st_mtime < newest_input:
        binary.parent.mkdir(parents=True, exist_ok=True)
        nim_paths = [
            line.replace('"', "")
            for line in (game_repo / "nim.cfg").read_text().splitlines()
            if line.startswith("--path:")
        ]
        subprocess.run(
            [
                "nim", "c", *nim_paths, "-d:release", "-d:useMalloc", "--opt:speed",
                "--stackTrace:on",
                f"--out:{binary}", str(source_dir / "stencil.nim"),
            ],
            cwd=game_repo,
            check=True,
        )
    return binary


def load_variant(manifest: dict[str, Any], variant: str) -> dict[str, Any]:
    for entry in manifest["variants"]:
        if entry["id"] == variant:
            return deepcopy(entry["game_config"])
    choices = ", ".join(entry["id"] for entry in manifest["variants"])
    raise ValueError(f"unknown Paintbot variant {variant!r}; choose one of: {choices}")


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_for_server(process: subprocess.Popen[bytes], port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"game server exited during startup with code {process.returncode}")
        with socket.socket() as client:
            client.settimeout(0.1)
            if client.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise TimeoutError(f"game server did not listen on port {port} within {timeout}s")


def team_for_slot(config: dict[str, Any], slot: int) -> str:
    slots = config.get("slots", [])
    if slot < len(slots) and slots[slot].get("team"):
        return str(slots[slot]["team"])
    return TEAM_NAMES[slot % int(config.get("teams", 2))]


def candidate_team_for_episode(config: dict[str, Any], requested: str, index: int) -> str:
    team_count = int(config.get("teams", 2))
    if requested == "rotate":
        return TEAM_NAMES[index % team_count]
    if requested not in TEAM_NAMES[:team_count]:
        raise ValueError(f"candidate team {requested!r} is not active in this variant")
    return requested


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def distribution(values: list[float]) -> dict[str, float | int]:
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values),
    }


def nav_init_summary(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    samples = [sample for result in results for sample in result["nav_init_samples"]]
    if not samples:
        return None
    metrics = (
        "total_ms",
        "decode_ms",
        "base_ms",
        "clearance_ms",
        "cover_ms",
        "dijkstra_total_ms",
    )
    by_map: dict[str, list[dict[str, Any]]] = {}
    for sample in samples:
        key = f"{sample['map_width']}x{sample['map_height']}"
        by_map.setdefault(key, []).append(sample)
    episode_max = [
        max(float(sample["total_ms"]) for sample in result["nav_init_samples"])
        for result in results
        if result["nav_init_samples"]
    ]
    return {
        "seat_samples": len(samples),
        "episodes_profiled": len(episode_max),
        "seat_distributions_ms": {
            metric: distribution([float(sample[metric]) for sample in samples])
            for metric in metrics
        },
        "episode_slowest_seat_total_ms": distribution(episode_max),
        "by_map_size": {
            key: {
                "seat_samples": len(group),
                "grid_cells": sorted({int(sample["grid_cells"]) for sample in group}),
                "total_ms": distribution([float(sample["total_ms"]) for sample in group]),
                "dijkstra_total_ms": distribution(
                    [float(sample["dijkstra_total_ms"]) for sample in group]
                ),
            }
            for key, group in sorted(by_map.items())
        },
    }


def run_episode(spec: dict[str, Any]) -> dict[str, Any]:
    game_repo = Path(spec["game_repo"])
    binary = Path(spec["binary"])
    output_dir = Path(spec["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "players").mkdir()

    config = deepcopy(spec["variant_config"])
    players = list(config["players"])
    seat_count = len(players)
    tokens = [f"selfplay-{spec['index']}-{slot}" for slot in range(seat_count)]
    candidate_team = candidate_team_for_episode(config, spec["candidate_team"], spec["index"])
    config.update(
        seed=spec["seed"],
        tokens=tokens,
        fastMode=True,
        maxGames=1,
        startWaitTicks=0,
        gameOverTicks=1,
    )
    if spec["max_ticks"] is not None:
        config["maxTicks"] = spec["max_ticks"]
    for slot, player in enumerate(players):
        arm = "candidate" if team_for_slot(config, slot) == candidate_team else "control"
        player["name"] = f"{arm}-{team_for_slot(config, slot)}-{slot}"
    config["players"] = players

    config_path = output_dir / "config.json"
    results_path = output_dir / "results.json"
    replay_path = output_dir / "replay"
    events_path = output_dir / "events.jsonl"
    config_path.write_text(json.dumps(config, indent=2) + "\n")

    port = available_port()
    server_env = os.environ.copy()
    server_env.update(
        COGAME_HOST="127.0.0.1",
        COGAME_PORT=str(port),
        COGAME_CONFIG_URI=f"file://{config_path}",
        COGAME_RESULTS_URI=f"file://{results_path}",
        COGAME_SAVE_REPLAY_URI=f"file://{replay_path}",
        COGAME_EVENTS_URI=f"file://{events_path}",
    )

    player_processes: list[tuple[subprocess.Popen[bytes], Any]] = []
    started = time.monotonic()
    server_log_path = output_dir / "game.log"
    with server_log_path.open("wb") as server_log:
        server = subprocess.Popen(
            [str(binary)],
            cwd=game_repo,
            env=server_env,
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )
        try:
            wait_for_server(server, port, spec["startup_timeout"])
            for slot, token in enumerate(tokens):
                player_env = os.environ.copy()
                player_env.update(spec["common_env"])
                if team_for_slot(config, slot) == candidate_team:
                    player_env.update(spec["candidate_env"])
                trace_path = output_dir / "players" / f"slot-{slot:02d}.trace.jsonl"
                player_env.update(
                    COWORLD_PLAYER_WS_URL=(
                        f"ws://127.0.0.1:{port}/player?slot={slot}&token={token}"
                    ),
                    STENCIL_TRACE_OUTPUTS=(
                        ",".join(
                            [
                                *(
                                    [f"jsonl@file:{trace_path}"]
                                    if spec["profile_nav_init"] or spec["visualize_nav"]
                                    else []
                                ),
                                *(["jsonl@artifact"] if spec["player_artifacts"] else []),
                            ]
                        )
                        or "jsonl@file:/dev/null"
                    ),
                )
                if spec["player_artifacts"]:
                    player_env["COWORLD_PLAYER_ARTIFACT_UPLOAD_URL"] = (
                        "file://" + str(
                            output_dir / "players" / f"slot-{slot:02d}.artifact.zip"
                        )
                    )
                if spec["fast_ready"]:
                    player_env["STENCIL_FAST_READY"] = "1"
                if spec["visualize_nav"]:
                    player_env["STENCIL_TRACE_NAVIGATION"] = "1"
                if spec["record_wire"]:
                    player_env["STENCIL_WIRE_RECORD"] = str(
                        output_dir / "players" / f"slot-{slot:02d}.wire.jsonl"
                    )
                log = (output_dir / "players" / f"slot-{slot:02d}.log").open("wb")
                is_candidate = team_for_slot(config, slot) == candidate_team
                if is_candidate and spec["candidate_runtime"] == "docker":
                    container_env = {
                        key: value
                        for key, value in player_env.items()
                        if key.startswith(("COWORLD_", "STENCIL_"))
                    }
                    container_env["COWORLD_PLAYER_WS_URL"] = (
                        f"ws://host.docker.internal:{port}/player?slot={slot}&token={token}"
                    )
                    command = [
                        "docker", "run", "--rm", "--init",
                        "--platform", "linux/amd64",
                        "--user", f"{os.getuid()}:{os.getgid()}",
                        "--volume", f"{output_dir}:{output_dir}",
                    ]
                    for key, value in sorted(container_env.items()):
                        command.extend(("--env", f"{key}={value}"))
                    command.append(spec["candidate_image"])
                else:
                    command = [spec["nim_binary"]]
                process = subprocess.Popen(
                    command,
                    cwd=REPO_ROOT,
                    env=player_env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                player_processes.append((process, log))
            try:
                server_code = server.wait(timeout=spec["timeout"])
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError(f"episode exceeded {spec['timeout']}s") from exc
            if server_code != 0:
                raise RuntimeError(f"game server exited with code {server_code}")
        finally:
            if server.poll() is None:
                server.kill()
                server.wait()
            for process, log in player_processes:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                log.close()

    elapsed = time.monotonic() - started
    if not results_path.exists():
        raise RuntimeError("game exited without results.json")
    results = json.loads(results_path.read_text())
    ticks = None
    if events_path.exists():
        for line in events_path.read_text().splitlines():
            row = json.loads(line)
            if row.get("type") == "summary":
                ticks = int(row["ticks"])
    teams = results.get("team", [])
    wins = results.get("win", [])
    candidate_won = any(
        team == candidate_team and bool(wins[index])
        for index, team in enumerate(teams)
        if index < len(wins)
    )
    nav_init_samples: list[dict[str, Any]] = []
    if spec["profile_nav_init"]:
        for slot in range(seat_count):
            trace_path = output_dir / "players" / f"slot-{slot:02d}.trace.jsonl"
            if not trace_path.exists():
                continue
            for line in trace_path.read_text().splitlines():
                row = json.loads(line)
                if row.get("event") != "worldmap":
                    continue
                worldmap = row["data"]["worldmap"]
                nav_init_samples.append(
                    {
                        "slot": slot,
                        "team": team_for_slot(config, slot),
                        "map_width": worldmap["w"],
                        "map_height": worldmap["h"],
                        **worldmap["nav_init"],
                    }
                )
                break
    return {
        "episode": spec["index"],
        "seed": spec["seed"],
        "candidate_team": candidate_team,
        "candidate_won": candidate_won,
        "elapsed_seconds": elapsed,
        "ticks": ticks,
        "ticks_per_second": ticks / elapsed if ticks is not None else None,
        "output_dir": str(output_dir),
        "nav_init_samples": nav_init_samples,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", default="1v1")
    parser.add_argument("--map-size", choices=MAP_SIZES)
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-ticks", type=int)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--startup-timeout", type=float, default=120)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "paintbot_lab" / "self_play")
    parser.add_argument("--game-repo", type=Path, default=DEFAULT_GAME_REPO)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument(
        "--fast-ready", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--candidate-env", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--candidate-team", default="rotate")
    parser.add_argument(
        "--candidate-runtime", choices=("nim", "docker"), default="nim",
        help="run the candidate team with the local Nim binary or release image",
    )
    parser.add_argument(
        "--candidate-image", default="players-stencil:dev",
        help="image used by --candidate-runtime=docker",
    )
    parser.add_argument("--profile-nav-init", action="store_true")
    parser.add_argument(
        "--visualize-nav", action="store_true",
        help="record navigation-map and flow-field traces for render_nav.py",
    )
    parser.add_argument("--record-wire", action="store_true")
    parser.add_argument("--player-artifacts", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.episodes < 1 or args.workers < 1:
        raise SystemExit("--episodes and --workers must be positive")
    live = resolve_live_paintbot()
    source_repo = args.game_repo.resolve()
    game_repo = prepare_game_source(source_repo, live["source_commit"])
    binary = ensure_game_binary(game_repo, rebuild=args.rebuild)
    nim_binary = ensure_stencil_nim_binary(
        game_repo, live["source_commit"], rebuild=args.rebuild
    )
    variant_config = load_variant(live["manifest"], args.variant)
    if args.map_size is not None:
        variant_config["mapSize"] = args.map_size
    run_dir = args.output_dir.resolve() / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True)
    common = {
        "game_repo": str(game_repo),
        "binary": str(binary),
        "variant_config": variant_config,
        "candidate_team": args.candidate_team,
        "candidate_runtime": args.candidate_runtime,
        "nim_binary": str(nim_binary),
        "candidate_image": args.candidate_image,
        "common_env": parse_env(args.env),
        "candidate_env": parse_env(args.candidate_env),
        "max_ticks": args.max_ticks,
        "timeout": args.timeout,
        "startup_timeout": args.startup_timeout,
        "fast_ready": args.fast_ready,
        "profile_nav_init": args.profile_nav_init,
        "visualize_nav": args.visualize_nav,
        "record_wire": args.record_wire,
        "player_artifacts": args.player_artifacts,
    }
    specs = [
        {
            **common,
            "index": index,
            "seed": args.seed + index,
            "output_dir": str(run_dir / f"episode-{index:04d}"),
        }
        for index in range(args.episodes)
    ]

    print(
        f"Paintbot native self-play: canonical={live['version']} "
        f"source={live['source_commit'][:12]} "
        f"variant={args.variant} "
        f"episodes={args.episodes} workers={min(args.workers, args.episodes)} "
        f"candidate-runtime={args.candidate_runtime} "
        f"fast-ready={int(args.fast_ready)}"
    )
    results: list[dict[str, Any]] = []
    batch_started = time.monotonic()
    with ProcessPoolExecutor(max_workers=min(args.workers, args.episodes)) as executor:
        futures = [executor.submit(run_episode, spec) for spec in specs]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            rate = result["ticks_per_second"]
            rate_text = f"{rate:.1f} ticks/s" if rate is not None else "ticks unavailable"
            print(
                f"episode {result['episode']:04d}: seed={result['seed']} "
                f"candidate={result['candidate_team']} won={result['candidate_won']} "
                f"{result['elapsed_seconds']:.2f}s ({rate_text})"
            )

    results.sort(key=lambda row: row["episode"])
    batch_seconds = time.monotonic() - batch_started
    summary_path = run_dir / "summary.json"
    nav_summary = nav_init_summary(results)
    summary_path.write_text(
        json.dumps(
            {
                "coworld_id": live["coworld_id"],
                "coworld_version": live["version"],
                "manifest_hash": live["manifest_hash"],
                "game_source_url": live["source_url"],
                "game_commit": live["source_commit"],
                "game_source_worktree": str(game_repo),
                "variant": args.variant,
                "map_size": args.map_size,
                "seed": args.seed,
                "max_ticks": args.max_ticks,
                "fast_ready": args.fast_ready,
                "candidate_team": args.candidate_team,
                "candidate_runtime": args.candidate_runtime,
                "env": common["common_env"],
                "candidate_env": common["candidate_env"],
                "nav_init": nav_summary,
                "workers": min(args.workers, args.episodes),
                "batch_seconds": batch_seconds,
                "episodes_per_hour": len(results) * 3600 / batch_seconds,
                "episodes": results,
            },
            indent=2,
        )
        + "\n"
    )
    wins = sum(bool(result["candidate_won"]) for result in results)
    total_seconds = sum(float(result["elapsed_seconds"]) for result in results)
    print(
        f"done: candidate {wins}/{len(results)} wins; "
        f"batch {batch_seconds:.2f}s ({len(results) * 3600 / batch_seconds:.1f} episodes/hour); "
        f"episode compute {total_seconds:.2f}s; artifacts {run_dir}"
    )
    if nav_summary is not None:
        total = nav_summary["seat_distributions_ms"]["total_ms"]
        slowest = nav_summary["episode_slowest_seat_total_ms"]
        print(
            f"nav init: {nav_summary['episodes_profiled']} episodes / "
            f"{nav_summary['seat_samples']} seats; seat total "
            f"mean={total['mean']:.2f}ms p50={total['p50']:.2f}ms "
            f"p95={total['p95']:.2f}ms max={total['max']:.2f}ms; "
            f"episode slowest-seat p95={slowest['p95']:.2f}ms"
        )


if __name__ == "__main__":
    main()
