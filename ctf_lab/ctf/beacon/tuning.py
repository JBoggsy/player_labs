"""Inspect beacon tunables and build validated Coworld upload arguments.

Examples:

  uv run python -m ctf.beacon.tuning dump
  uv run python -m ctf.beacon.tuning secret-env \
    FIREFIGHT=true FOCUS_CLAIMS=true FF_WOUND_WEIGHT=0.6
"""

from __future__ import annotations

import argparse
import json
import shlex

from ctf.beacon.config import (
    TUNABLE_INVARIANTS,
    TUNABLE_REGISTRY,
    TunableSpec,
    TunableValue,
    tunable_spec,
    validate_tunable_values,
)


def registry_payload(family: str | None = None) -> dict[str, object]:
    """Machine-readable registry payload, optionally restricted to one family."""
    specs = [
        spec
        for spec in TUNABLE_REGISTRY.values()
        if family is None or spec.family == family
    ]
    return {
        "schema_version": 1,
        "tunables": [spec.to_dict() for spec in specs],
        "invariants": [
            item.to_dict()
            for item in TUNABLE_INVARIANTS
            if family is None or item.family == family
        ],
    }


def _parse_assignment_items(
    items: list[str],
) -> tuple[dict[str, object], list[TunableSpec]]:
    assignments: dict[str, object] = {}
    ordered_specs: list[TunableSpec] = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"assignment must be NAME=VALUE: {item}")
        key, value = item.split("=", 1)
        if not key or not value:
            raise ValueError(f"assignment must be NAME=VALUE: {item}")
        spec = tunable_spec(key)
        assignments[key] = value
        ordered_specs.append(spec)
    return assignments, ordered_specs


def secret_env_args(items: list[str]) -> list[str]:
    """Validate assignments and return repeated ``--secret-env KEY=VALUE`` args."""
    assignments, ordered_specs = _parse_assignment_items(items)
    values = validate_tunable_values(assignments)
    args: list[str] = []
    emitted: set[str] = set()
    for spec in ordered_specs:
        if spec.name in emitted:
            raise ValueError(f"duplicate assignment for {spec.name}")
        emitted.add(spec.name)
        value: TunableValue = values[spec.name]
        if spec.value_type == "boolean":
            encoded = "1" if value else "0"
        elif spec.value_type == "integer":
            encoded = str(value)
        else:
            encoded = format(float(value), ".15g")
        args.extend(("--secret-env", f"{spec.env_var}={encoded}"))
    return args


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    dump = subparsers.add_parser("dump", help="dump the tunable registry as JSON")
    dump.add_argument(
        "--family",
        choices=sorted({spec.family for spec in TUNABLE_REGISTRY.values()}),
        default=None,
        help="restrict output to one tunable family",
    )

    secret_env = subparsers.add_parser(
        "secret-env",
        help="emit validated Coworld --secret-env arguments",
    )
    secret_env.add_argument(
        "assignments",
        metavar="NAME=VALUE",
        nargs="+",
        help="config names or BEACON_* environment names",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "dump":
            validate_tunable_values()
            print(json.dumps(registry_payload(args.family), indent=2))
        else:
            print(shlex.join(secret_env_args(args.assignments)))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()


__all__ = ["main", "registry_payload", "secret_env_args"]
