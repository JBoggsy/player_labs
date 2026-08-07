#!/usr/bin/env python3
"""Install and operate the Stencil campaign controller as a user LaunchAgent."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import shutil
import subprocess
from pathlib import Path


LABEL = "com.softmax.paintbot-stencil-campaign-controller"
STATE_DIRECTORY = Path.home() / "Library" / "Application Support" / "Stencil Campaign Controller"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def service_target() -> str:
    return f"gui/{os.getuid()}/{LABEL}"


def run_launchctl(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/launchctl", *arguments],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def atomic_copy(source: Path, destination: Path) -> None:
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    shutil.copyfile(source, temporary)
    os.replace(temporary, destination)


def plist() -> dict[str, object]:
    root = repo_root()
    python = root / ".venv" / "bin" / "python"
    controller = root / "paintbot_lab" / "tools" / "campaign_order_controller.py"
    if not python.is_file() or not controller.is_file():
        raise RuntimeError("checkout or project virtual environment is incomplete")
    return {
        "Label": LABEL,
        "ProgramArguments": [
            str(python),
            str(controller),
            "--poll-seconds",
            "15",
            "--state",
            str(STATE_DIRECTORY / "state.json"),
            "--log",
            str(STATE_DIRECTORY / "events.jsonl"),
        ],
        "WorkingDirectory": str(root),
        "EnvironmentVariables": {"PYTHONUNBUFFERED": "1"},
        "KeepAlive": True,
        "ThrottleInterval": 30,
        "ProcessType": "Background",
        "ExitTimeOut": 10,
        "StandardOutPath": str(STATE_DIRECTORY / "stdout.log"),
        "StandardErrorPath": str(STATE_DIRECTORY / "stderr.log"),
    }


def install(args: argparse.Namespace) -> None:
    STATE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

    if args.migrate_state:
        state = json.loads(args.migrate_state.read_text())
        if not isinstance(state, dict):
            raise RuntimeError("migrated state must contain a JSON object")
        atomic_copy(args.migrate_state, STATE_DIRECTORY / "state.json")
    if args.migrate_events:
        atomic_copy(args.migrate_events, STATE_DIRECTORY / "events.jsonl")

    temporary = PLIST_PATH.with_name(f".{PLIST_PATH.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        plistlib.dump(plist(), handle, sort_keys=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, PLIST_PATH)
    PLIST_PATH.chmod(0o644)

    run_launchctl("bootout", service_target(), check=False)
    run_launchctl("bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH))
    run_launchctl("enable", service_target())
    print(run_launchctl("print", service_target()).stdout, end="")


def status(_: argparse.Namespace) -> None:
    result = run_launchctl("print", service_target(), check=False)
    print(result.stdout, end="")
    if result.returncode:
        raise SystemExit(result.returncode)


def uninstall(_: argparse.Namespace) -> None:
    run_launchctl("bootout", service_target(), check=False)
    PLIST_PATH.unlink(missing_ok=True)
    print(f"Uninstalled {LABEL}; preserved state in {STATE_DIRECTORY}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    install_parser = commands.add_parser("install")
    install_parser.add_argument("--migrate-state", type=Path)
    install_parser.add_argument("--migrate-events", type=Path)
    install_parser.set_defaults(function=install)

    status_parser = commands.add_parser("status")
    status_parser.set_defaults(function=status)

    uninstall_parser = commands.add_parser("uninstall")
    uninstall_parser.set_defaults(function=uninstall)
    return parser.parse_args()


if __name__ == "__main__":
    parsed = parse_args()
    parsed.function(parsed)
