#!/usr/bin/env python3
"""Paired difference between two agents seated together in every game of a tourney dir.

    uv run python webdiplomacy_lab/tools/paired.py DIR AGENT_A AGENT_B

Per game: (A's score - mean score at A's power) - (B's score - mean at B's power), with the
power means pooled over every seat in DIR. Prints n, mean difference, standard error, z.
"""
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from webdip_episodes import load_dirs  # noqa: E402

root, a, b = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
games = []
for d in sorted(root.glob("g-*")):
    if not (d / "results.json").exists():
        continue
    seating = json.loads((d / "seating.json").read_text())
    seats, _ = load_dirs([d])
    games.append((seating, seats))
pm = defaultdict(list)
for _, seats in games:
    for s in seats:
        pm[s.power].append(s.score)
pm = {p: statistics.mean(v) for p, v in pm.items()}
diffs = []
for seating, seats in games:
    by = {}
    for s in seats:
        by.setdefault(seating[s.slot], s)  # first seat with that name (the fixed candidate)
    if a in by and b in by:
        diffs.append((by[a].score - pm[by[a].power]) - (by[b].score - pm[by[b].power]))
n = len(diffs)
mean = statistics.mean(diffs) if diffs else 0.0
se = statistics.stdev(diffs) / math.sqrt(n) if n > 1 else float("nan")
print(json.dumps({"n": n, "diff": round(mean, 4), "se": round(se, 4), "z": round(mean / se, 2) if se else None}))
