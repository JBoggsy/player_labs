#!/usr/bin/env python3
"""Replay Python Stencil wire captures through Nim and require exact decisions."""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "paintbot_lab" / "paintbot" / "stencil_nim"
DEFAULT_GAME_CACHE = REPO_ROOT / "paintbot_lab" / ".cache" / "coworld-ctf"
VERSIONS_FILE = REPO_ROOT / "paintbot_lab" / "tools" / "versions.env"
SLOT_RE = re.compile(r"slot-(\d+)\.wire\.jsonl$")


def default_game_repo() -> Path:
    for line in VERSIONS_FILE.read_text().splitlines():
        if line.startswith("PAINTBOT_GAME_REF="):
            repo = DEFAULT_GAME_CACHE / line.partition("=")[2].strip()
            if not (repo / "nim.cfg").exists():
                raise RuntimeError(f"pinned game cache is missing: {repo}")
            return repo
    raise RuntimeError(f"PAINTBOT_GAME_REF is missing from {VERSIONS_FILE}")


def compile_replay(game_repo: Path) -> Path:
    binary = REPO_ROOT / "paintbot_lab" / ".cache" / "stencil-nim" / "replay"
    sources = sorted(SOURCE_DIR.glob("*.nim"))
    newest_input = max(
        [path.stat().st_mtime for path in sources]
        + [(game_repo / "nim.cfg").stat().st_mtime]
    )
    if not binary.exists() or binary.stat().st_mtime < newest_input:
        binary.parent.mkdir(parents=True, exist_ok=True)
        nim_paths = [
            line.replace('"', "")
            for line in (game_repo / "nim.cfg").read_text().splitlines()
            if line.startswith("--path:")
        ]
        subprocess.run(
            [
                "nim", "c", *nim_paths, "-d:release", "-d:useMalloc", "--opt:speed",
                f"--out:{binary}", str(SOURCE_DIR / "replay.nim"),
            ],
            cwd=game_repo,
            check=True,
        )
    return binary


def python_decisions(path: Path) -> list[dict[str, int | str | None]]:
    decisions: list[dict[str, int | str | None]] = []
    current: dict[str, int | str | None] | None = None
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event["type"] != "binary":
            continue
        packet = base64.b64decode(event["data"])
        if event["direction"] == "in":
            if current is not None:
                decisions.append(current)
            current = {"mask": None, "chat": ""}
        elif current is not None and packet[:1] == b"\x84":
            current["mask"] = packet[1]
        elif current is not None and packet[:1] == b"\x81":
            size = int.from_bytes(packet[1:3], "little")
            current["chat"] = packet[3 : 3 + size].decode("ascii")
    if current is not None:
        decisions.append(current)
    return decisions


def nim_decisions(binary: Path, path: Path, slot: int) -> list[dict[str, object]]:
    result = subprocess.run(
        [str(binary), str(path), str(slot)],
        env=os.environ.copy(),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return [json.loads(line) for line in result.stdout.splitlines()]


def compare(binary: Path, path: Path) -> tuple[int, list[str]]:
    match = SLOT_RE.search(path.name)
    if match is None:
        raise ValueError(f"cannot infer slot from wire filename: {path}")
    expected = python_decisions(path)
    actual = nim_decisions(binary, path, int(match.group(1)))
    errors: list[str] = []
    if len(expected) != len(actual):
        errors.append(f"decision count: python={len(expected)} nim={len(actual)}")
    for tick, (python, nim) in enumerate(zip(expected, actual), 1):
        if python["mask"] != nim["mask"] or python["chat"] != nim["chat"]:
            errors.append(f"tick {tick}: python={python} nim={nim}")
            if len(errors) >= 20:
                break
    return len(actual), errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wire", nargs="+", type=Path)
    parser.add_argument("--game-repo", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    game_repo = args.game_repo or default_game_repo()
    binary = compile_replay(game_repo)
    total = 0
    failed = False
    with ThreadPoolExecutor(max_workers=min(args.workers, len(args.wire))) as executor:
        comparisons = executor.map(lambda path: compare(binary, path), args.wire)
        for path, (decisions, errors) in zip(args.wire, comparisons, strict=True):
            total += decisions
            if errors:
                failed = True
                print(f"FAIL {path} ({decisions} decisions)")
                print(*(f"  {error}" for error in errors), sep="\n")
            else:
                print(f"PASS {path} ({decisions} exact decisions)")
    print(f"{'FAIL' if failed else 'PASS'} total={total} decisions files={len(args.wire)}")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
