#!/usr/bin/env python3
"""Harvest Honor Society liar evidence from telemetry -> vendored distrust list.

The Honor Society ledgers liars in-game (`domain.honor_liar`: a color announced
crew via a verified HS1 signature and was later PROVEN an imposter — witnessed
kill/vent, or our own teammate knowledge) but until this tool nothing consumed
those events across games. This is the missing consumer: it scans harvested
telemetry (crewrift_lab/telemetry_harvest/episodes/*/ — both loose
telemetry.jsonl files and artifacts/policy_artifact_*.zip archives), aggregates
liar evidence per pubkey, and writes the vendored distrust list
crewrift_lab/crewrift/crewborg/data/honor_distrust.json.

GROUND-TRUTH GATE (load-bearing): the in-game witness has false positives —
measured 6/199 episodes (2026-07-22 HS A/B baseline) where crewborg ledgered a
member key whose seat was ACTUALLY crew per results.json (witness misattribution
of a kill/vent). A naive harvest would therefore permanently distrust an honest
member from our own bad eyesight. So each honor_liar event is validated against
the episode's results.json: the accused color maps to a slot (the game palette
is slot-ordered) and only slots that were REALLY imposters count as confirmed
lies; the rest are reported as refuted witness errors and kept OFF the list.
Events with no results.json alongside are "unverifiable" and also excluded
(fail-closed toward trusting members).

The agent-side seam (strategy/honor_society.py `_load_distrust`/`is_distrusted`)
loads that file at runtime: a distrusted key's verified announcements are ignored
— never trusted — from the first meeting of every future game.

Usage:
    uv run python crewrift_lab/tools/harvest_liars.py                 # scan + report, no write
    uv run python crewrift_lab/tools/harvest_liars.py --write         # also update honor_distrust.json
    uv run python crewrift_lab/tools/harvest_liars.py --root DIR ...  # extra scan roots (e.g. an A/B episode dir)

An empty result still (with --write) refreshes the file's scan metadata, so the
vendored list records how much evidence backs "nobody has been caught lying yet".
Run it after (or on the same timer as) harvest_artifacts.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parent.parent          # crewrift_lab/
DEFAULT_SCAN_ROOT = LAB_ROOT / "telemetry_harvest" / "episodes"
DISTRUST_PATH = LAB_ROOT / "crewrift" / "crewborg" / "data" / "honor_distrust.json"
DISTRUST_SCHEMA = "crewborg-honor-distrust/v1"

# The liar event as emitted by strategy/honor_society.py via EventEmitter
# (unqualified names get the ``domain.`` prefix).
LIAR_EVENT = "domain.honor_liar"

# Slot -> color, in game palette order (mirrors crewborg's
# perception/constants.py PLAYER_COLOR_NAMES; current since game commit 1cbd4de,
# 2026-06-24). Used to map an accused color back to a results.json slot.
PALETTE = ("red", "blue", "green", "pink", "orange", "yellow", "purple", "cyan",
           "lime", "brown", "beige", "navy", "teal", "rose", "maroon")


def iter_telemetry_sources(roots: list[Path]):
    """Yield (source_label, line_iterable) for every telemetry.jsonl under roots.

    Covers both loose ``*/telemetry.jsonl`` files and ``policy_artifact_*.zip``
    archives (the harvest layout: episodes/<ts>_<ereq>/artifacts/*.zip). Zips
    without a telemetry.jsonl member (e.g. an opponent artifact that shipped
    other files) are skipped silently.
    """

    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("telemetry.jsonl")):
            yield str(path), path.open("rb")
        for zpath in sorted(root.rglob("policy_artifact_*.zip")):
            try:
                zf = zipfile.ZipFile(zpath)
                member = zf.open("telemetry.jsonl")
            except (zipfile.BadZipFile, KeyError, OSError):
                continue
            yield str(zpath), member


def episode_of(source: str) -> str:
    """The episode directory name a telemetry source belongs to (for dedup/report)."""

    parts = Path(source).parts
    for i, part in enumerate(parts):
        if part == "episodes" and i + 1 < len(parts):
            return parts[i + 1]
    # Fallback: the parent dir chain above artifacts/, else the immediate parent.
    p = Path(source).parent
    if p.name == "artifacts":
        p = p.parent
    return p.name


def _episode_dir_of(source: str) -> Path:
    """The episode directory a telemetry source lives under (for results.json)."""

    p = Path(source)
    parent = p.parent
    if parent.name == "artifacts":
        parent = parent.parent
    return parent


def _accused_was_imposter(episode_dir: Path, color: str) -> bool | None:
    """Ground truth for an accusation: True/False per results.json, None if unknown.

    The game seats slots in palette order, so the accused color names a slot;
    results.json's `imposter` array is the authoritative role. Missing/short
    results, or a color outside the palette, is None (unverifiable).
    """

    rj = episode_dir / "results.json"
    if not rj.exists():
        return None
    try:
        results = json.loads(rj.read_text())
        slot = PALETTE.index(color.lower())
        return bool(results["imposter"][slot])
    except (ValueError, KeyError, IndexError, json.JSONDecodeError, OSError):
        return None


def scan_liars(roots: list[Path]) -> tuple[dict[str, dict], int, int]:
    """Scan telemetry under roots -> (liars_by_pub, sources_scanned, episodes_scanned).

    liars_by_pub: pub_b64 -> {"pub", "events", "episodes": set, "colors": set,
    "refuted": int, "unverified": int}. Only CONFIRMED lies (the accused color's
    seat really was an imposter per results.json) count toward `events`; witness
    errors are tallied in `refuted` and results-less events in `unverified`.
    An honor_liar event repeats every meeting tick after the ledgering (the liar
    sweep re-checks claims), so counts are per distinct (episode, color), not raw
    lines.
    """

    liars: dict[str, dict] = {}
    seen_pairs: set[tuple[str, str, str]] = set()   # (pub, episode, color)
    episodes: set[str] = set()
    sources = 0
    for source, fh in iter_telemetry_sources(roots):
        sources += 1
        episodes.add(episode_of(source))
        with fh:
            for raw in fh:
                if b"honor_liar" not in raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if rec.get("event") != LIAR_EVENT and rec.get("name") != LIAR_EVENT:
                    continue
                data = rec.get("data") or {}
                pub = str(data.get("pub") or "")
                color = str(data.get("color") or "")
                if not pub:
                    continue
                key = (pub, episode_of(source), color)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                entry = liars.setdefault(pub, {
                    "pub": pub, "events": 0, "episodes": set(), "colors": set(),
                    "refuted": 0, "unverified": 0,
                })
                verdict = _accused_was_imposter(_episode_dir_of(source), color)
                if verdict is True:
                    entry["events"] += 1
                    entry["episodes"].add(episode_of(source))
                    entry["colors"].add(color)
                elif verdict is False:
                    entry["refuted"] += 1
                else:
                    entry["unverified"] += 1
    # Keys with only refuted/unverified evidence carry no confirmed lie: keep them
    # in the report (the caller prints them) but they never reach the distrust list.
    return liars, sources, len(episodes)


def render_distrust(liars: dict[str, dict], episodes_scanned: int) -> dict:
    """The honor_distrust.json document for a scan result."""

    return {
        "schema": DISTRUST_SCHEMA,
        "comment": (
            "Cross-game Honor Society distrust list — pubkeys PROVEN to lie "
            "(announced crew while a witnessed imposter). Written by "
            "crewrift_lab/tools/harvest_liars.py from harvested league telemetry "
            "(domain.honor_liar events); vendored into the image so the agent "
            "distrusts known liars from the FIRST meeting of every game. Keys "
            "compare by RAW BYTES (either base64 flavor). Empty is the normal "
            "state: no member has been caught lying yet."
        ),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "episodes_scanned": episodes_scanned,
        "liars": [
            {
                "pub": entry["pub"],
                "lie_events": entry["events"],
                "episodes": sorted(entry["episodes"]),
                "colors": sorted(entry["colors"]),
                "refuted_witness_errors": entry["refuted"],
                "unverified": entry["unverified"],
            }
            for entry in sorted(liars.values(), key=lambda e: (-e["events"], e["pub"]))
            if entry["events"] > 0  # confirmed lies only — witness errors never distrust
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", action="append", type=Path, default=None,
                        help="Scan root(s); default: crewrift_lab/telemetry_harvest/episodes. Repeatable.")
    parser.add_argument("--write", action="store_true",
                        help=f"Update the vendored distrust list ({DISTRUST_PATH.relative_to(LAB_ROOT.parent)}).")
    parser.add_argument("--out", type=Path, default=DISTRUST_PATH,
                        help="Override the output path (with --write).")
    args = parser.parse_args(argv)

    roots = args.root or [DEFAULT_SCAN_ROOT]
    liars, sources, episodes = scan_liars(roots)

    print(f"scanned {sources} telemetry sources across {episodes} episodes under: "
          f"{', '.join(str(r) for r in roots)}")
    confirmed = {pub: e for pub, e in liars.items() if e["events"] > 0}
    suspected_only = {pub: e for pub, e in liars.items() if e["events"] == 0}
    if confirmed:
        print(f"CONFIRMED LIARS: {len(confirmed)} distinct pubkey(s)")
        for entry in sorted(confirmed.values(), key=lambda e: -e["events"]):
            print(f"  {entry['pub']}  lie_events={entry['events']} "
                  f"episodes={len(entry['episodes'])} colors={sorted(entry['colors'])} "
                  f"(refuted={entry['refuted']} unverified={entry['unverified']})")
    if suspected_only:
        print(f"witness errors / unverifiable only (NOT distrusted): {len(suspected_only)} pubkey(s)")
        for entry in suspected_only.values():
            print(f"  {entry['pub']}  refuted={entry['refuted']} unverified={entry['unverified']}")
    if not liars:
        print("no honor_liar events found (nobody has been caught lying yet)")

    if args.write:
        doc = render_distrust(liars, episodes)
        args.out.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"wrote {args.out} ({len(doc['liars'])} liar(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
