"""Phase-0 study for the button-runner-interception design.

Reads the expanded corpus and answers two questions for the imposter
button-interception idea (docs/designs/button-runner-interception.md):

1. HOW COMMON are crew emergency-button ("reset") calls — per game, and how are
   they spaced in time (do they cluster near the ~500/900-tick cooldown cadence)?
2. WHERE is the best intercept location — i.e. along the runners' approach to the
   bridge button, which cells/rooms do most approaches funnel through, far enough
   from the bridge that a kill there is not at the most-trafficked room, and where
   the runner tends to be isolated. This is the spatial prior Search would bias to.

Pure analysis over `replay_parse.parse_game`; emits a text report (and optional
JSON) to stdout. Run from the repo root:

    uv run python crewrift_lab/suspicion_lab/tools/button_runner_study.py
"""

from __future__ import annotations

import argparse
import glob
import gzip
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import replay_parse as rp

CELL = 32  # px grid, matches agent_tracking.GRID_CELL_SIZE
APPROACH_WINDOW = 250  # ticks before the call we treat as the "approach" (SEARCH_LEAD_TICKS)
ISO_RADIUS = 48  # px, matches opportunity.BASE_ISOLATION_RADIUS (witness clearance)


@dataclass
class MapGeom:
    width: int
    height: int
    rooms: list[dict]
    button_center: tuple[float, float]

    def room_at(self, x: float, y: float) -> str | None:
        for r in self.rooms:
            if r["x"] <= x < r["x"] + r["w"] and r["y"] <= y < r["y"] + r["h"]:
                return r["name"]
        return None


def load_map_geom(path: Path) -> MapGeom | None:
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt") as fh:
        for line in fh:
            d = json.loads(line)
            if d.get("key") == "map_geometry":
                v = d["value"]
                b = v["button"]
                bx = b["x"] + b.get("w", 0) / 2
                by = b["y"] + b.get("h", 0) / 2
                return MapGeom(v["width"], v["height"], v["rooms"], (bx, by))
    return None


def cell_of(x: float, y: float) -> tuple[int, int]:
    return int(x // CELL), int(y // CELL)


def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="crewrift_lab/suspicion_lab/expanded/*.jsonl.gz")
    ap.add_argument("--window", type=int, default=APPROACH_WINDOW)
    ap.add_argument("--limit", type=int, default=0, help="cap episodes (0 = all)")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    files = sorted(Path(p) for p in glob.glob(args.glob))
    if args.limit:
        files = files[: args.limit]

    geom: MapGeom | None = None
    map_names: Counter = Counter()

    # Commonality
    n_games = 0
    games_with_button = 0
    button_calls_per_game: list[int] = []
    crew_calls_per_game: list[int] = []
    caller_role = Counter()
    call_ticks: list[int] = []
    gap_since_prev_meeting: list[int] = []  # any meeting -> any meeting
    gap_button_after_meeting: list[int] = []  # button call gap from prior meeting

    # Spatial: per crew button call, the set of cells its approach passed through
    cell_calls = Counter()  # cell -> number of distinct approaches through it
    cell_room: dict[tuple[int, int], str | None] = {}
    cell_min_other_crew: dict[tuple[int, int], list[int]] = defaultdict(list)  # isolation samples
    room_calls = Counter()  # room -> approaches passing through
    commit_room = Counter()  # room the runner was in W ticks before pressing
    approach_dist_at_window: list[float] = []  # dist from button at window start
    n_crew_calls = 0

    for f in files:
        try:
            g = rp.parse_game(f)
        except Exception:
            continue
        if not g.complete:
            continue
        if geom is None:
            geom = load_map_geom(f)
        mname = None
        # cheap map-name capture for consistency check
        try:
            op = gzip.open if f.suffix == ".gz" else open
            with op(f, "rt") as fh:
                for line in fh:
                    d = json.loads(line)
                    if d.get("key") == "map_geometry":
                        mname = d["value"].get("map_name")
                        break
        except Exception:
            pass
        if mname:
            map_names[mname] += 1

        n_games += 1
        meetings = sorted(g.meetings, key=lambda m: m.call_tick)
        buttons = [m for m in meetings if m.kind == "button"]
        if buttons:
            games_with_button += 1
        button_calls_per_game.append(len(buttons))

        # meeting-to-meeting gaps
        prev = None
        for m in meetings:
            if prev is not None:
                gap_since_prev_meeting.append(m.call_tick - prev)
            if m.kind == "button" and prev is not None:
                gap_button_after_meeting.append(m.call_tick - prev)
            prev = m.call_tick

        crew_count = 0
        for m in buttons:
            role = g.players[m.caller_slot].role if m.caller_slot in g.players else "unknown"
            caller_role[role] += 1
            call_ticks.append(m.call_tick)
            if role != "crew":
                continue
            crew_count += 1
            n_crew_calls += 1

            # Reconstruct approach path of the caller in [call - window, call]
            samples = [
                s
                for s in g.states.get(m.caller_slot, [])
                if m.call_tick - args.window <= s.tick <= m.call_tick and s.alive
            ]
            if not samples:
                continue
            samples.sort(key=lambda s: s.tick)
            if geom is not None:
                approach_dist_at_window.append(dist((samples[0].x, samples[0].y), geom.button_center))
            commit_room[samples[0].room or geom.room_at(samples[0].x, samples[0].y) if geom else samples[0].room] += 1

            seen_cells: set[tuple[int, int]] = set()
            seen_rooms: set[str] = set()
            for s in samples:
                c = cell_of(s.x, s.y)
                seen_cells.add(c)
                if c not in cell_room and geom is not None:
                    cell_room[c] = geom.room_at(s.x, s.y)
                # isolation: other alive crew near the runner at this tick
                others = 0
                for slot, info in g.players.items():
                    if slot == m.caller_slot or info.role != "crew":
                        continue
                    os_ = g.state_at(slot, s.tick)
                    if os_ is not None and os_.alive and dist((os_.x, os_.y), (s.x, s.y)) <= ISO_RADIUS:
                        others += 1
                cell_min_other_crew[c].append(others)
                rm = s.room or (geom.room_at(s.x, s.y) if geom else None)
                if rm:
                    seen_rooms.add(rm)
            for c in seen_cells:
                cell_calls[c] += 1
            for rm in seen_rooms:
                room_calls[rm] += 1
        crew_calls_per_game.append(crew_count)

    # ---- Report ----
    def pct(n, d):
        return f"{100*n/d:.1f}%" if d else "n/a"

    def hist(vals, edges):
        c = Counter()
        for v in vals:
            for e in edges:
                if v < e:
                    c[e] += 1
                    break
            else:
                c[edges[-1] + 1] += 1  # overflow bucket key
        return c

    print("=" * 72)
    print(f"BUTTON-RUNNER STUDY  ({n_games} complete games, window={args.window} ticks)")
    print(f"map(s): {dict(map_names)}")
    print("=" * 72)

    print("\n## 1. How common")
    print(f"games with >=1 button call : {games_with_button}/{n_games}  ({pct(games_with_button, n_games)})")
    if button_calls_per_game:
        bc = button_calls_per_game
        print(f"button calls / game        : mean {sum(bc)/len(bc):.2f}  max {max(bc)}  "
              f"dist {dict(sorted(Counter(bc).items()))}")
    if crew_calls_per_game:
        cc = crew_calls_per_game
        print(f"CREW button calls / game   : mean {sum(cc)/len(cc):.2f}  total {sum(cc)}")
    print(f"caller role split          : {dict(caller_role)}")

    print("\n## 2. Timing")
    edges = [400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000]
    if gap_button_after_meeting:
        h = hist(gap_button_after_meeting, edges)
        print(f"button-call gap from PRIOR meeting (n={len(gap_button_after_meeting)}):")
        for e in edges:
            print(f"   <{e:5d}: {h.get(e,0):4d}  {'#'*(h.get(e,0)*40//max(1,len(gap_button_after_meeting)))}")
        print(f"   >=2000: {h.get(2001,0)}")
        gm = sorted(gap_button_after_meeting)
        print(f"   median gap {gm[len(gm)//2]}  mean {sum(gm)/len(gm):.0f}")
    if call_ticks:
        ct = sorted(call_ticks)
        print(f"absolute call tick: median {ct[len(ct)//2]}  "
              f"p25 {ct[len(ct)//4]}  p75 {ct[3*len(ct)//4]}")

    print("\n## 3. Where to intercept  (crew approaches, n=%d)" % n_crew_calls)
    if approach_dist_at_window:
        ad = sorted(approach_dist_at_window)
        print(f"dist from button {args.window}t before press: median {ad[len(ad)//2]:.0f}px  "
              f"(runner starts this far out and converges)")
    print(f"\ncommit room (where runner was {args.window}t before press), top 8:")
    for rm, n in commit_room.most_common(8):
        print(f"   {n:4d}  {pct(n,n_crew_calls):>6}  {rm}")

    print("\ntop ROOMS by approach pass-through (Search-bias targets):")
    print(f"   {'thru%':>6} {'n':>4}  {'d_btn':>6} {'iso(med#crew)':>13}  room")
    room_rows = []
    for rm, n in room_calls.most_common():
        # mean dist of this room's cells to button, and median crew-near across its cells
        rcells = [c for c, r in cell_room.items() if r == rm]
        if rcells and geom is not None:
            dbtn = sum(dist((c[0]*CELL+CELL/2, c[1]*CELL+CELL/2), geom.button_center) for c in rcells)/len(rcells)
        else:
            dbtn = float("nan")
        isos = [v for c in rcells for v in cell_min_other_crew.get(c, [])]
        med_iso = sorted(isos)[len(isos)//2] if isos else float("nan")
        room_rows.append((rm, n, dbtn, med_iso))
    for rm, n, dbtn, med_iso in room_rows:
        print(f"   {pct(n,n_crew_calls):>6} {n:>4}  {dbtn:6.0f} {med_iso:13.1f}  {rm}")

    print("\ntop CELLS by approach pass-through (chokepoints), top 20:")
    print(f"   {'thru%':>6} {'n':>4}  {'cellctr(x,y)':>14} {'d_btn':>6} {'iso':>5}  room")
    for c, n in cell_calls.most_common(20):
        ctr = (c[0]*CELL+CELL//2, c[1]*CELL+CELL//2)
        dbtn = dist(ctr, geom.button_center) if geom else float("nan")
        isos = cell_min_other_crew.get(c, [])
        med_iso = sorted(isos)[len(isos)//2] if isos else float("nan")
        print(f"   {pct(n,n_crew_calls):>6} {n:>4}  {str(ctr):>14} {dbtn:6.0f} {med_iso:5.1f}  {cell_room.get(c)}")

    # "Best intercept" score: pass-through fraction x in-band distance (not at bridge, not too far) x isolation
    print("\nBEST INTERCEPT CELLS (score = thru-frac x band(d_btn) x isolation), top 15:")
    print(f"   {'score':>6} {'thru%':>6} {'d_btn':>6} {'iso':>5}  cellctr        room")
    scored = []
    for c, n in cell_calls.items():
        if geom is None:
            break
        ctr = (c[0]*CELL+CELL//2, c[1]*CELL+CELL//2)
        dbtn = dist(ctr, geom.button_center)
        # band: prefer 120..320px from button (off the bridge, still close enough to reach in time)
        band = max(0.0, 1.0 - abs(dbtn - 220) / 220)
        isos = cell_min_other_crew.get(c, [])
        med_iso = sorted(isos)[len(isos)//2] if isos else 0
        iso_factor = 1.0 / (1.0 + med_iso)  # more isolated (fewer crew near) -> higher
        thru = n / max(1, n_crew_calls)
        score = thru * band * iso_factor
        scored.append((score, thru, dbtn, med_iso, ctr, cell_room.get(c)))
    for score, thru, dbtn, med_iso, ctr, rm in sorted(scored, reverse=True)[:15]:
        print(f"   {score:6.3f} {100*thru:5.1f}% {dbtn:6.0f} {med_iso:5.1f}  {str(ctr):>14} {rm}")

    if args.json_out:
        out = {
            "n_games": n_games,
            "games_with_button": games_with_button,
            "button_calls_per_game_mean": sum(button_calls_per_game)/len(button_calls_per_game) if button_calls_per_game else 0,
            "caller_role": dict(caller_role),
            "n_crew_calls": n_crew_calls,
            "room_pass_through": {rm: n for rm, n in room_calls.most_common()},
            "top_cells": [
                {"center": [c[0]*CELL+CELL//2, c[1]*CELL+CELL//2], "n": n, "room": cell_room.get(c)}
                for c, n in cell_calls.most_common(40)
            ],
        }
        Path(args.json_out).write_text(json.dumps(out, indent=2))
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
