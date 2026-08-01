"""Aggregate the firefight ladder: outcomes plus the mechanism traces per arm.

The ladder layers one change per arm (postsonly -> +firefight -> +claims -> +wider
spacing) against three opponents, so every number here is read per (arm, opponent).

Outcome comes from ``episode.json`` scores, joined to our policy via ``participants``:
under GV21 a decisive game scores +1/-1 and a timeout draw pays -1 to BOTH sides, so a
draw is "no positive score" rather than a score value (mirrors the ctf-ab adapter).

Mechanism numbers come from the per-agent ``.jsonl`` snapshots inside each episode's
policy artifact zips. They answer the question outcomes cannot: whether the behavior
actually fired, and whether focus fire bought kills or merely bought held fire.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import zipfile

#: Trace fields summed across an agent-game. friendly_fire_suppressed is the one that
#: separates "focus fire did not help" from "focus fire made us hold fire".
COUNTER_FIELDS = (
    "friendly_fire_suppressed",
    "firefight_ticks_total",
    "firefight_engagements",
    "firefight_target_switches",
    "focus_claims_sent",
    "focus_claims_heard",
    "focus_claims_suppressed",
    "firefight_arc_exempt_ticks",
)


def _our_policy_ids(episode: dict, player: str = "beacon") -> set[str]:
    """Policy version ids belonging to our player in this episode.

    Keyed on ``policy_name`` rather than roster position: the pinned roster does put
    beacon on even positions, but a name match stays correct if a roster is ever
    composed differently, and it fails loudly rather than silently scoring the
    opponent's side.
    """
    return {
        part["policy_version_id"]
        for part in episode.get("participants") or []
        if part.get("policy_name") == player and part.get("policy_version_id")
    }


def outcome_of(episode: dict) -> str | None:
    """``win`` / ``draw`` / ``loss`` for beacon, or None when unscorable."""
    scores = episode.get("scores") or []
    if not scores:
        return None
    ours = _our_policy_ids(episode)
    if not ours:
        return None
    mine = [s["score"] for s in scores if s.get("policy_version_id") in ours]
    if not mine:
        return None
    if max(s["score"] for s in scores) <= 0:
        return "draw"  # nobody scored positive: a timeout draw
    return "win" if max(mine) > 0 else "loss"


def episode_traces(ep_dir: pathlib.Path) -> list[dict]:
    """Final per-agent snapshot dicts for every beacon agent in this episode."""
    finals: list[dict] = []
    art = ep_dir / "artifacts"
    if not art.is_dir():
        return finals
    for zp in sorted(art.glob("*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
        except (zipfile.BadZipFile, OSError):
            continue
        for name in zf.namelist():
            if not name.endswith(".jsonl"):
                continue
            last: dict | None = None
            try:
                text = zf.read(name).decode("utf8", "ignore")
            except (KeyError, OSError):
                continue
            for line in text.splitlines():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("event") == "snapshot":
                    last = rec.get("data") or {}
            if last is not None:
                finals.append(last)
    return finals


def _wilson(k: int, n: int) -> tuple[float, float]:
    """95% Wilson interval — honest at the small n a 30-episode arm gives."""
    if n == 0:
        return (0.0, 0.0)
    z = 1.96
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def summarize_arm(arm_dir: pathlib.Path) -> dict:
    """Outcomes and summed mechanism counters for one (arm, opponent) cell."""
    out = collections.Counter()
    counters = collections.Counter()
    range_bins = collections.Counter()
    agent_games = 0
    episodes = 0

    for ep_dir in sorted(p for p in arm_dir.iterdir() if p.is_dir()):
        ep_file = ep_dir / "episode.json"
        if not ep_file.is_file():
            continue
        try:
            episode = json.loads(ep_file.read_text())
        except json.JSONDecodeError:
            continue
        res = outcome_of(episode)
        if res is None:
            continue
        episodes += 1
        out[res] += 1
        for snap in episode_traces(ep_dir):
            agent_games += 1
            for field in COUNTER_FIELDS:
                val = snap.get(field)
                if isinstance(val, (int, float)):
                    counters[field] += val
            for key, tag in (
                ("firefight_shot_ranges", "shot"),
                ("firefight_target_ranges", "target"),
            ):
                bins = snap.get(key)
                if isinstance(bins, dict):
                    for band, n in bins.items():
                        if isinstance(n, (int, float)):
                            range_bins[f"{tag}:{band}"] += n

    return {
        "episodes": episodes,
        "win": out["win"],
        "draw": out["draw"],
        "loss": out["loss"],
        "agent_games": agent_games,
        "counters": dict(counters),
        "range_bins": dict(range_bins),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=pathlib.Path)
    ap.add_argument("--json", type=pathlib.Path, help="also write the raw summary here")
    args = ap.parse_args()

    cells = {}
    for arm_dir in sorted(p for p in args.root.iterdir() if p.is_dir()):
        cells[arm_dir.name] = summarize_arm(arm_dir)

    print(f"{'arm vs opponent':<28}{'eps':>5}{'W':>4}{'D':>4}{'L':>4}   win%  [95% CI]")
    print("-" * 72)
    for name, c in cells.items():
        n = c["episodes"]
        if not n:
            print(f"{name:<28}{'-':>5}  (no scorable episodes)")
            continue
        lo, hi = _wilson(c["win"], n)
        print(
            f"{name:<28}{n:>5}{c['win']:>4}{c['draw']:>4}{c['loss']:>4}"
            f"{100 * c['win'] / n:>7.0f}%  [{100 * lo:.0f}-{100 * hi:.0f}]"
        )

    print("\nMECHANISM (summed over agent-games; 0 across an arm = the behavior never fired)")
    print(f"{'arm vs opponent':<28}{'agents':>7}" + "".join(f"{f.replace('firefight_', 'ff_')[:13]:>15}" for f in COUNTER_FIELDS[:5]))
    for name, c in cells.items():
        if not c["agent_games"]:
            continue
        row = "".join(f"{c['counters'].get(f, 0):>15.0f}" for f in COUNTER_FIELDS[:5])
        print(f"{name:<28}{c['agent_games']:>7}{row}")

    bands = sorted({b for c in cells.values() for b in c["range_bins"]})
    if bands:
        print("\nRANGE BANDS (shot / selected-target ticks)")
        for name, c in cells.items():
            if not c["range_bins"]:
                continue
            tot = sum(v for k, v in c["range_bins"].items() if k.startswith("shot"))
            parts = [
                f"{b.split(':')[1]}={100 * c['range_bins'][b] / tot:.0f}%"
                for b in bands
                if b.startswith("shot") and b in c["range_bins"] and tot
            ]
            if parts:
                print(f"  {name:<28}{'  '.join(parts)}")

    if args.json:
        args.json.write_text(json.dumps(cells, indent=1))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
