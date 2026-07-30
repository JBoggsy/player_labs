"""Find sustained two-sided firefights in a CTF event warehouse.

A *firefight* here is what you would want to watch: a stretch of ticks where bots on
BOTH teams are shooting, near each other, for long enough to be a real exchange rather
than two passing potshots. Kills alone are a poor index — most kills are one-sided
ambushes, and the interesting failures (fire held, target thrash, mutual blocking) leave
no kill event at all.

Detection, from `replay_events` rows with key='shot' (which carry the shooter's live
x/y/aim, re-keyed to team):

  1. Slide a window of ``--window`` ticks over each episode.
  2. Inside the window, keep shot pairs from OPPOSING teams whose shooters are within
     ``--radius`` px of each other — that is the "exchange" test. The radius is a
     spatial cluster bound too, so two simultaneous fights on opposite sides of the map
     do not merge into one bogus mega-fight.
  3. A tick is *contested* when at least one such opposing pair exists.
  4. Merge contested ticks (bridging gaps up to ``--gap`` ticks, since real firefights
     breathe — reload, duck behind cover, re-peek) and keep segments lasting at least
     ``--min-ticks``.

Segments are ranked by a simple intensity score (shots x both-sides balance x duration)
so the top of the list is dense mutual combat rather than a long standoff with two shots
in it.

Usage:
    uv run python ctf_lab/tools/find_firefights.py ctf_lab/scratch/wh_fight \
        --version 36 --top 15
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib

import duckdb

#: 24 ticks/s (ReplayFps). Defaults below are expressed in ticks but chosen in seconds:
#: a 1s window, a 2s bridgeable lull, a 3s minimum exchange.
TICKS_PER_SEC = 24


def load_shots(db: pathlib.Path, version: int | None, opponent: str | None) -> dict:
    """Shot events grouped by episode: {episode_id: [(tick, team, x, y), ...]}."""
    con = duckdb.connect(str(db / "warehouse.duckdb"), read_only=True)
    where = ["key = 'shot'"]
    if version is not None:
        # Restrict to episodes in which OUR arm played, not to our shots only: the
        # opposing side's fire is exactly what makes a segment an exchange.
        where.append(
            "episode_id IN (SELECT episode_id FROM participants "
            f"WHERE policy_name = 'beacon' AND policy_version = {int(version)})"
        )
    if opponent:
        where.append(
            "episode_id IN (SELECT episode_id FROM participants "
            f"WHERE policy_name = '{opponent}')"
        )
    rows = con.execute(
        f"""
        SELECT episode_id, tick, actor_team,
               CAST(json_extract(value_json, '$.x') AS DOUBLE) AS x,
               CAST(json_extract(value_json, '$.y') AS DOUBLE) AS y
        FROM replay_events
        WHERE {' AND '.join(where)}
        ORDER BY episode_id, tick
        """
    ).fetchall()
    by_ep: dict[str, list] = collections.defaultdict(list)
    for ep, tick, team, x, y in rows:
        if x is None or y is None or team not in ("red", "blue"):
            continue
        by_ep[ep].append((int(tick), team, float(x), float(y)))
    return by_ep


def contested_ticks(
    shots: list[tuple[int, str, float, float]],
    window: int,
    radius: float,
) -> dict[int, tuple[int, int]]:
    """Ticks with an opposing shot pair inside `radius`, -> (red_shots, blue_shots)."""
    if not shots:
        return {}
    out: dict[int, tuple[int, int]] = {}
    lo = 0
    for i, (tick, _team, _x, _y) in enumerate(shots):
        while shots[lo][0] < tick - window:
            lo += 1
        hi = i
        while hi + 1 < len(shots) and shots[hi + 1][0] <= tick + window:
            hi += 1
        near = shots[lo : hi + 1]
        red = [s for s in near if s[1] == "red"]
        blue = [s for s in near if s[1] == "blue"]
        if not red or not blue:
            continue
        engaged = any(
            math.hypot(r[2] - b[2], r[3] - b[3]) <= radius for r in red for b in blue
        )
        if engaged:
            out[tick] = (len(red), len(blue))
    return out


def segments_from(
    ticks: dict[int, tuple[int, int]], gap: int, min_ticks: int
) -> list[dict]:
    """Merge contested ticks into segments, bridging lulls up to `gap`."""
    if not ticks:
        return []
    ordered = sorted(ticks)
    segs: list[list[int]] = [[ordered[0], ordered[0]]]
    for t in ordered[1:]:
        if t - segs[-1][1] <= gap:
            segs[-1][1] = t
        else:
            segs.append([t, t])

    result = []
    for start, end in segs:
        dur = end - start + 1
        if dur < min_ticks:
            continue
        inside = [ticks[t] for t in ordered if start <= t <= end]
        red = sum(r for r, _ in inside)
        blue = sum(b for _, b in inside)
        total = red + blue
        # Balance keeps one-sided suppression from outranking a genuine trade.
        balance = min(red, blue) / max(red, blue) if max(red, blue) else 0.0
        result.append(
            {
                "start_tick": start,
                "end_tick": end,
                "duration_ticks": dur,
                "duration_s": round(dur / TICKS_PER_SEC, 1),
                "red_shot_ticks": red,
                "blue_shot_ticks": blue,
                "balance": round(balance, 2),
                "intensity": round(total * balance * math.log1p(dur), 1),
            }
        )
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("warehouse", type=pathlib.Path)
    ap.add_argument("--version", type=int, help="beacon version (arm) to restrict to")
    ap.add_argument("--opponent", help="opponent policy name to restrict to")
    ap.add_argument("--window", type=int, default=TICKS_PER_SEC)
    ap.add_argument("--radius", type=float, default=320.0)
    ap.add_argument("--gap", type=int, default=2 * TICKS_PER_SEC)
    ap.add_argument("--min-ticks", type=int, default=3 * TICKS_PER_SEC)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--json", type=pathlib.Path)
    args = ap.parse_args()

    by_ep = load_shots(args.warehouse, args.version, args.opponent)
    all_segs = []
    for ep, shots in by_ep.items():
        ticks = contested_ticks(shots, args.window, args.radius)
        for seg in segments_from(ticks, args.gap, args.min_ticks):
            seg["episode_id"] = ep
            all_segs.append(seg)

    all_segs.sort(key=lambda s: -s["intensity"])
    per_ep = collections.Counter(s["episode_id"] for s in all_segs)

    print(
        f"{len(by_ep)} episodes scanned; {len(all_segs)} firefights "
        f">= {args.min_ticks}t ({args.min_ticks / TICKS_PER_SEC:.0f}s), "
        f"radius {args.radius:.0f}px"
    )
    print(f"\nTOP {args.top} FIREFIGHTS BY INTENSITY")
    print(f"{'episode':<40}{'ticks':>14}{'dur':>7}{'red':>6}{'blue':>6}{'bal':>6}{'int':>8}")
    for seg in all_segs[: args.top]:
        span = f"{seg['start_tick']}-{seg['end_tick']}"
        print(
            f"{seg['episode_id'][:38]:<40}{span:>14}{seg['duration_s']:>6}s"
            f"{seg['red_shot_ticks']:>6}{seg['blue_shot_ticks']:>6}"
            f"{seg['balance']:>6}{seg['intensity']:>8}"
        )

    print(f"\nEPISODES WITH THE MOST FIREFIGHTS")
    for ep, n in per_ep.most_common(8):
        tot = sum(s["duration_s"] for s in all_segs if s["episode_id"] == ep)
        print(f"  {ep}  {n:>2} firefights, {tot:>5.0f}s contested")

    if args.json:
        args.json.write_text(json.dumps(all_segs, indent=1))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
