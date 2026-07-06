#!/usr/bin/env python3
"""Role-conditional ranking of every policy in the clean ranking-eval batch.

For each policy, computes crew win rate and imposter win rate (each from that
policy's own independent games), with Wilson 95% CIs. Ranks by role-conditional
rate; overlapping CIs => statistical tie. Reads the committed clean-game
episode_players table via _data (no raw episodes needed)."""
import math
from collections import defaultdict

from _data import seats_df

def wilson(k, n, z=1.96):
    if n == 0: return (float('nan'),)*3
    p = k/n
    d = 1 + z*z/n
    c = (p + z*z/(2*n))/d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return p, c-h, c+h

# policy -> role -> [wins, games]
stats = defaultdict(lambda: {"crew":[0,0], "imposter":[0,0]})
df = seats_df()
n_games = df.episode_id.nunique()
for _, row in df.iterrows():
    stats[row.policy_name][row.role][1] += 1
    stats[row.policy_name][row.role][0] += int(bool(row.win))

def line(name, role):
    k, n = stats[name][role]
    p, lo, hi = wilson(k, n)
    return f"{p*100:5.1f}% [{lo*100:4.1f},{hi*100:4.1f}] n={n:4d}"

print(f"# {n_games} games with usable seats\n")
for role in ("crew", "imposter"):
    print(f"=== {role.upper()} win rate (ranked) ===")
    ranked = sorted(stats.items(), key=lambda kv: -(kv[1][role][0]/kv[1][role][1] if kv[1][role][1] else 0))
    for name, _ in ranked:
        k, n = stats[name][role]
        if n < 20: continue
        star = "  <-- crewborg" if name == "crewborg" else ""
        print(f"  {name:46s} {line(name, role)}{star}")
    print()
