"""Aggregate a beacon eval directory (results.json per episode) into a scoreline.

Usage: uv run python ctf_lab/tools/agg_eval.py <eval_dir> [beacon_team]
Assumes beacon plays the given team (default red). Prints wins / captures / K-D.
"""

from __future__ import annotations

import glob
import json
import sys


def main() -> None:
    d = sys.argv[1]
    beacon_team = sys.argv[2] if len(sys.argv) > 2 else "red"
    other = "blue" if beacon_team == "red" else "red"
    bw = ow = dr = 0
    bc = oc = bk = ok = bd = od = 0
    n = 0
    for rp in sorted(glob.glob(f"{d}/*/results.json")):
        try:
            r = json.load(open(rp))
        except (OSError, ValueError):
            continue
        if "team" not in r:
            continue
        n += 1
        t = r["team"]
        s = r["scores"]
        caps = r.get("captures", [0] * len(t))
        k = r.get("kills", [0] * len(t))
        dd = r.get("deaths", [0] * len(t))

        def team_sum(arr, team):
            return sum(v for v, tt in zip(arr, t) if tt == team)

        bs, os_ = team_sum(s, beacon_team), team_sum(s, other)
        bw += bs > os_
        ow += os_ > bs
        dr += bs == os_
        bc += team_sum(caps, beacon_team)
        oc += team_sum(caps, other)
        bk += team_sum(k, beacon_team)
        ok += team_sum(k, other)
        bd += team_sum(dd, beacon_team)
        od += team_sum(dd, other)
    if not n:
        print(f"{d}: no results yet")
        return
    print(f"{d}")
    print(f"  episodes: {n} | beacon({beacon_team}) wins {bw}  opp wins {ow}  draws {dr}  "
          f"[{100*bw//n}% beacon]")
    print(f"  captures beacon={bc} opp={oc} | kills {bk}/{ok} | "
          f"deaths/game beacon={bd/n:.1f} opp={od/n:.1f}")


if __name__ == "__main__":
    main()
