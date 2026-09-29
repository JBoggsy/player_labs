#!/usr/bin/env python3
"""Compose (never create) experience-request bodies for a Paintbot PW A/B (plan §7).

Prints a manifest: every request body the design needs, each with its label, arm, side,
opponent and seed. It makes NO API call. Creating the requests is a separate, human-authorized
step through the shared skill (`experience_request.py create BODY`), one body at a time.

Every body pins all 16 seats with an explicit `policy_ref` and `slot`: our policy on the 8
seats of one side (even = red/Ember, odd = blue/Azure), one opponent policy on the other 8.
Sides are swapped across the batch. Designs:

  paired  each arm vs each --opponent, both sides, one request per seed with
          game_config_overrides.seed = that seed (so the arms pair by (opponent, side, seed)).
  h2h     REFUSED here: candidate vs baseline is two of our own policies, i.e. self-play, and
          hosted XP self-play is not allowed (user_preferences.md). Screen h2h locally with
          `pw.py local screen CANDIDATE.bas BASELINE.bas --record DIR`, then
          `pw.py compare compare DIR --design h2h` on the recordings.
  field   each arm vs each --opponent, both sides; per seed when --seeds is given, else
          one request per (arm, opponent, side) with --episodes episodes. Pass the same policy
          as --baseline and --candidate to evaluate one policy (one arm, no duplicate requests).

Seeds: an explicit seed is repeated by every episode of its request, and the engine is
deterministic, so more than one episode per seed is likely the same game replayed
(compare.py counts those as duplicate_game). Keep --episodes-per-seed 1 unless a pilot showed
hosted games at one seed differ.

Usage (repo root):
  uv run python paintbot_pw_lab/tools/pw_ab_requests.py --design paired \
      --baseline james-pw:v3 --candidate james-pw:v4 --opponent leader-pw:v12 \
      --seeds 1-30 --league-id league_... [--private] [--run-id ID] [--out DIR]
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pw_cli  # noqa: E402
from pw_local import parse_seeds  # noqa: E402

SEATS = 16
SIDES = ("red", "blue")  # side index = the parity of our seats
TOP_LEVEL_FIELDS = {  # V2CreateExperienceRequestRequest (coworld-experience-requests references/api.md)
    "idempotency_key", "private", "llm_routing_override", "coworld_id", "variant_id", "target",
    "game_config_overrides", "game_config_overlay_secret", "state", "roster",
    "included_players", "excluded_players", "num_episodes", "notes", "execution_backend", "reporters"}
TARGET_FIELDS = {"coworld_id", "variant_id", "league_id", "league_name", "division_id", "division_name"}


def roster(ours: str, theirs: str, side: int) -> list[dict]:
    """16 pinned seats: `ours` on the seats whose parity is `side`, `theirs` on the rest."""
    return [{"player": {"policy_ref": ours if slot % 2 == side else theirs}, "slot": slot}
            for slot in range(SEATS)]


def body(target: dict, ours: str, theirs: str, side: int, *, seed: int | None, episodes: int,
         private: bool, key: str, notes: str) -> dict:
    out = {"idempotency_key": key, "private": private, "target": target,
           "roster": roster(ours, theirs, side), "num_episodes": episodes, "notes": notes}
    if seed is not None:
        out["game_config_overrides"] = {"seed": seed}
    validate(out)
    return out


def validate(request: dict) -> None:
    """The checks references/api.md states; the server remains the full validator."""
    unknown = set(request) - TOP_LEVEL_FIELDS
    if unknown:
        raise ValueError(f"unknown request fields {sorted(unknown)}")
    if set(request["target"]) - TARGET_FIELDS or not request["target"]:
        raise ValueError(f"bad target {request['target']}")
    slots = [entry["slot"] for entry in request["roster"]]
    if sorted(slots) != list(range(SEATS)):
        raise ValueError(f"roster must pin slots 0..{SEATS - 1}, got {slots}")
    for entry in request["roster"]:
        if list(entry["player"]) != ["policy_ref"] or not entry["player"]["policy_ref"]:
            raise ValueError(f"each seat needs exactly one explicit policy_ref: {entry}")
    if not 1 <= request["num_episodes"] <= 100:
        raise ValueError("num_episodes must be 1..100")
    if len(request["notes"]) > 1000 or not 5 <= len(request["idempotency_key"]) <= 200:
        raise ValueError("notes <= 1000 chars and idempotency_key 5..200 chars")


SELF_PLAY_REFUSAL = (
    "h2h pits two of our own policies against each other: that is self-play, and hosted XP "
    "self-play is not allowed (user_preferences.md). Screen it locally instead: "
    "uv run python paintbot_pw_lab/tools/pw.py local screen CANDIDATE.bas BASELINE.bas --record DIR, "
    "then pw.py compare compare DIR --design h2h on the recordings. For hosted evidence use --design paired or field.")


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:40]


def compose(design: str, baseline: str, candidate: str, opponents: list[str], seeds: list[int] | None,
            target: dict, *, episodes: int = 1, private: bool = False, run_id: str) -> list[dict]:
    """The list of {label, arm, side, opponent, seed, body} for one A/B run."""
    if design == "paired" and not seeds:
        raise ValueError("the paired design needs --seeds (pairs share a seed)")
    if design in ("paired", "field") and not opponents:
        raise ValueError(f"the {design} design needs at least one --opponent")
    if design == "h2h":
        raise ValueError(SELF_PLAY_REFUSAL)
    else:
        # baseline == candidate means "evaluate one policy": compose its arm once, not twice.
        arms = (("baseline", baseline),) if baseline == candidate else (("baseline", baseline), ("candidate", candidate))
        matchups = [(arm, ours, opponent) for opponent in opponents for arm, ours in arms]
    requests = []
    for arm, ours, theirs in matchups:
        for side in (0, 1):
            for seed in (seeds or [None]):
                label = f"{arm}-vs-{_slug(theirs)}-{SIDES[side]}" + (f"-s{seed}" if seed is not None else "")
                notes = (f"paintbot-pw A/B run {run_id} ({design}): {ours} on {SIDES[side]} vs {theirs}"
                         + (f", seed {seed}" if seed is not None else ""))
                requests.append({"label": label, "arm": arm, "policy": ours, "side": SIDES[side],
                                 "opponent": theirs, "seed": seed,
                                 "body": body(target, ours, theirs, side, seed=seed, episodes=episodes,
                                              private=private, key=f"pwab-{run_id}-{label}", notes=notes)})
    return requests


def build_parser() -> pw_cli.ArgumentParser:
    parser = pw_cli.ArgumentParser("pw_ab_requests", __doc__, examples=[
        "uv run python paintbot_pw_lab/tools/pw_ab_requests.py --design paired --baseline james-pw:v3 "
        "--candidate james-pw:v4 --opponent leader-pw:v12 --seeds 1-30 --league-id league_... --run-id ab1 "
        "--out RUN/requests --json",
        "uv run python paintbot_pw_lab/tools/pw_ab_requests.py --design field --baseline james-pw:v3 "
        "--candidate james-pw:v4 --opponent leader-pw:v12 --episodes 10 --league-id league_..."])
    parser.add_argument("--design", choices=("paired", "h2h", "field"), required=True,
                        help="paired or field (h2h is refused: hosted self-play; see the module doc)")
    parser.add_argument("--baseline", required=True, help="policy_ref: name:vN or a policy_version_id")
    parser.add_argument("--candidate", required=True, help="policy_ref: name:vN or a policy_version_id")
    parser.add_argument("--opponent", action="append", default=[], help="opponent policy_ref (repeat)")
    parser.add_argument("--seeds", help="e.g. 1-30 or 3,5,9 (one request per seed and side)")
    parser.add_argument("--episodes", type=int, default=1,
                        help="episodes per request (per seed when --seeds is given; default %(default)s)")
    parser.add_argument("--league-id", help="target league id, e.g. league_b9458ff8-...")
    parser.add_argument("--division-id", help="target division id")
    parser.add_argument("--coworld-id", help="target coworld id (with --variant-id)")
    parser.add_argument("--variant-id", help="target variant id")
    parser.add_argument("--private", action="store_true", help="private request (explicit opponents may 409)")
    parser.add_argument("--run-id", default=None,
                        help="goes into every idempotency_key and note (default: now, %%Y%%m%%dT%%H%%M%%S). "
                             "Pass a fixed id so a re-run composes identical bodies (same idempotency keys)")
    parser.add_argument("--out", type=Path, help="also write manifest.json and bodies/<label>.json here")
    return parser


def run_cli(args, report: pw_cli.Report) -> dict:
    target = {k: v for k, v in (("league_id", args.league_id), ("division_id", args.division_id),
                                ("coworld_id", args.coworld_id), ("variant_id", args.variant_id)) if v}
    if not target:
        raise pw_cli.UsageError("give a target: --league-id, --division-id, or --coworld-id [--variant-id]")
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%S")
    report.inputs["run_id"] = run_id
    try:
        requests = compose(args.design, args.baseline, args.candidate, args.opponent,
                           parse_seeds(args.seeds) if args.seeds else None, target,
                           episodes=args.episodes, private=args.private, run_id=run_id)
    except ValueError as error:
        raise pw_cli.UsageError(str(error)) from error
    manifest = {"tool": "pw_ab_requests.py", "design": args.design, "run_id": run_id,
                "baseline": args.baseline, "candidate": args.candidate, "opponents": args.opponent,
                "requests": requests}
    if not report.json_mode:
        print(json.dumps(manifest, indent=1))
    total = sum(r["body"]["num_episodes"] for r in requests)
    print(f"{len(requests)} request bodies, {total} episodes in all. Nothing was created.", file=sys.stderr)
    report.counts.update(processed=len(requests), episodes=total)
    if args.out:
        (args.out / "bodies").mkdir(parents=True, exist_ok=True)
        (args.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
        report.output(args.out / "manifest.json")
        for r in requests:
            (args.out / "bodies" / f"{r['label']}.json").write_text(json.dumps(r["body"], indent=1) + "\n")
            report.output(args.out / "bodies" / f"{r['label']}.json")
        print(f"wrote {args.out}/manifest.json and {len(requests)} bodies", file=sys.stderr)
        report.suggest("create each body with the coworld-experience-requests skill "
                       f"(experience_request.py create {args.out}/bodies/<label>.json): costs XP credits")
    return manifest


def main(argv: list[str] | None = None) -> int:
    return pw_cli.run(build_parser(), run_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
