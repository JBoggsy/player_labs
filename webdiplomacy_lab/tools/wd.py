#!/usr/bin/env python3
"""webDiplomacy lab entry point. Run from the repo root:

    uv run python webdiplomacy_lab/tools/wd.py metrics EVIDENCE_DIR... [--policy NAME:vN] [--json]
    uv run python webdiplomacy_lab/tools/wd.py seats EVIDENCE_DIR... [--policy NAME:vN]   # JSONL rows
    uv run python webdiplomacy_lab/tools/wd.py local --image IMG [--episodes N] [--out DIR]

`metrics`: per-power results for the target policy's seats next to the FIELD PAR (mean
of every non-target seat at that power in the same directories), plus coverage and our
telemetry (rejected orders, exceptions, activation counters). Without --policy, every
seat is pooled (useful for all-random calibration). Exit code 0 = parsed, 2 = no
target seats found.

`seats`: one JSON row per seat (the miner/A-B input).

`local`: run N local episodes of one image in every seat (own-policy self-play only).
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from webdip_episodes import POWERS, load_dirs  # noqa: E402

LAB = Path(__file__).resolve().parents[1]
GAME_VERSION = "0.7.7"  # deployed webdiplomacy release these tools are verified against


def _mean(xs):
    return round(statistics.mean(xs), 4) if xs else None


def per_power(seats):
    groups = defaultdict(list)
    for s in seats:
        groups[s.power].append(s)
    out = {}
    for power in POWERS.values():
        g = groups.get(power, [])
        out[power] = {
            "n": len(g),
            "score": _mean([s.score for s in g]),
            "final_centers": _mean([s.final_centers for s in g if s.final_centers is not None]),
            "survival": _mean([float(s.survived) for s in g if s.survived is not None]),
            "solo": _mean([float(s.solo) for s in g]),
        }
    return out


def cmd_metrics(args):
    seats, statuses = load_dirs([Path(p) for p in args.dirs])
    target = [s for s in seats if args.policy is None or s.policy == args.policy]
    field = [s for s in seats if args.policy is not None and s.policy != args.policy]
    if not target:
        print(json.dumps({"error": "no target seats", "policies": sorted({s.policy for s in seats})}))
        return 2
    ours, par = per_power(target), per_power(field) if field else {}
    # Score relative to the same-batch field at the same power: removes most power-strength variance.
    rel = [s.score - par[s.power]["score"] for s in target if par.get(s.power, {}).get("score") is not None]
    logs = [s.log for s in target if s.log]
    report = {
        "game_version": GAME_VERSION,
        "policy": args.policy or "all seats",
        "episodes": len(statuses),
        "coverage": {
            "with_results": sum(not st["missing"] or st["missing"] == ["replay"] for st in statuses),
            "missing_results": [st["dir"] for st in statuses if "results" in st["missing"]],
            "missing_replay": [st["dir"] for st in statuses if "replay" in st["missing"]],
            "target_seats_with_log": len(logs),
        },
        "overall": {
            "n": len(target),
            "score": _mean([s.score for s in target]),
            "score_minus_field_par": _mean(rel),
            "final_centers": _mean([s.final_centers for s in target if s.final_centers is not None]),
            "survival": _mean([float(s.survived) for s in target if s.survived is not None]),
            "solo": _mean([float(s.solo) for s in target]),
            "failed_order_rate": _mean([s.orders_failed / s.orders for s in target if s.orders]),
            "outcomes": dict(sorted({o: sum(s.outcome == o for s in target) for o in {s.outcome for s in target}}.items())),
        },
        "per_power": ours,
        "field_par_per_power": par,
        "telemetry": {
            "rejected_orders": sum(lg.get("rejected", 0) for lg in logs),
            "exceptions": sum(lg.get("exceptions", 0) for lg in logs),
            "http_errors": sum(lg.get("http_errors", 0) for lg in logs),
            "max_compute_ms": max((lg["max_compute_ms"] for lg in logs if lg.get("max_compute_ms")), default=None),
            "trace": _sum_traces(logs),
        },
    }
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        print(render(report))
    return 0


def _sum_traces(logs):
    total = defaultdict(int)
    for lg in logs:
        for k, v in (lg.get("trace") or {}).items():
            total[k] += v
    return dict(sorted(total.items()))


def render(r):
    o = r["overall"]
    lines = [
        f"# {r['policy']} — webdiplomacy {r['game_version']}, {r['episodes']} episodes",
        f"coverage: {r['coverage']['with_results']} with results; missing results {len(r['coverage']['missing_results'])}, "
        f"missing replay {len(r['coverage']['missing_replay'])}; seat logs {r['coverage']['target_seats_with_log']}",
        f"overall n={o['n']}: score {o['score']} (vs field par {o['score_minus_field_par']:+}) | final SCs {o['final_centers']}"
        if o["score_minus_field_par"] is not None
        else f"overall n={o['n']}: score {o['score']} | final SCs {o['final_centers']}",
        f"survival {o['survival']} | solo {o['solo']} | failed-order rate {o['failed_order_rate']} | outcomes {o['outcomes']}",
        "",
        "| power | n | score | par score | final SCs | par SCs | survival |",
        "|---|---|---|---|---|---|---|",
    ]
    for power, v in r["per_power"].items():
        p = r["field_par_per_power"].get(power, {})
        lines.append(
            f"| {power} | {v['n']} | {v['score']} | {p.get('score')} | {v['final_centers']} | {p.get('final_centers')} | {v['survival']} |"
        )
    t = r["telemetry"]
    lines += ["", f"telemetry: rejected {t['rejected_orders']}, exceptions {t['exceptions']}, http errors {t['http_errors']}, "
              f"max compute {t['max_compute_ms']} ms", f"trace: {t['trace']}"]
    return "\n".join(lines)


def cmd_seats(args):
    seats, _ = load_dirs([Path(p) for p in args.dirs])
    for s in seats:
        if args.policy is None or s.policy == args.policy:
            print(json.dumps(asdict(s)))
    return 0


def cmd_local(args):
    manifest = next((LAB / "coworld_pkg").glob("cow_*/coworld_manifest.json"), None)
    if manifest is None:
        print("run: uv run coworld download webdiplomacy -o webdiplomacy_lab/coworld_pkg", file=sys.stderr)
        return 2
    run = ["/opt/.venv/bin/python", "-m", "players.launcher", "/opt/.venv/bin/python", "-m", args.module]
    cmd = ["uv", "run", "coworld", "run-episode", str(manifest), args.image, "--variant", args.variant,
           "--episodes", str(args.episodes), "--output-dir", args.out, "--timeout-seconds", "6000"]
    for token in run:
        cmd.append(f"--run={token}")
    return subprocess.call(cmd, env={**__import__("os").environ, "DOCKER_DEFAULT_PLATFORM": "linux/amd64"})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("metrics")
    m.add_argument("dirs", nargs="+")
    m.add_argument("--policy", help="target policy NAME:vN (hosted); omit to pool all seats")
    m.add_argument("--json", action="store_true")
    m.set_defaults(func=cmd_metrics)
    s = sub.add_parser("seats")
    s.add_argument("dirs", nargs="+")
    s.add_argument("--policy")
    s.set_defaults(func=cmd_seats)
    lo = sub.add_parser("local")
    lo.add_argument("--image", required=True)
    lo.add_argument("--module", default="webdip_bot.bot")
    lo.add_argument("--variant", default="classic-gunboat")
    lo.add_argument("--episodes", type=int, default=1)
    lo.add_argument("--out", default=str(LAB / "local_runs" / "latest"))
    lo.set_defaults(func=cmd_local)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
