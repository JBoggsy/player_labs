#!/usr/bin/env python3
"""Assemble the James Botts policy from its module files.

BASIC has no include, so the uploadable artifact is the concatenation of
``modules/*.bas`` in file-name order. Each module owns a variable prefix (see
``docs/designs/2026-09-17-lasthit-policy.md``); modules 00-89 contain only DIMs and
SUBs, and ``90_main.bas`` holds the per-tick top-level code.

Usage: ``python3 policy/build.py [--out PATH]`` from the lab directory or the repo
root. Writes ``policy/dist/james_botts.bas`` by default and prints its size.
"""

from __future__ import annotations

import argparse
from pathlib import Path

POLICY_DIR = Path(__file__).resolve().parent
MODULES_DIR = POLICY_DIR
DEFAULT_OUT = POLICY_DIR / "dist.bas"
SOURCE_LIMIT = 64 * 1024


def assemble() -> str:
    parts = []
    for module in sorted(MODULES_DIR.glob("[0-9][0-9]_*.bas")):
        parts.append(f"' ===== module {module.name} =====\n")
        parts.append(module.read_text().rstrip("\n") + "\n\n")
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    source = assemble()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(source)
    size = len(source.encode())
    status = "ok" if size <= SOURCE_LIMIT else "OVER THE 64 KiB SOURCE LIMIT"
    print(f"{args.out}: {size} bytes ({status})")


if __name__ == "__main__":
    main()
