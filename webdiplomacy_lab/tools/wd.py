#!/usr/bin/env python3
"""webDiplomacy lab entry point. Run from the repo root:

    uv run python webdiplomacy_lab/tools/wd.py metrics EVIDENCE_DIR... [--policy NAME:vN] [--json]
    uv run python webdiplomacy_lab/tools/wd.py seats EVIDENCE_DIR... [--policy NAME:vN]   # JSONL rows
    uv run python webdiplomacy_lab/tools/wd.py local --image IMG [--episodes N] [--out DIR]
    uv run python webdiplomacy_lab/tools/wd.py arena --candidate POLICY [--field dumbbot_v1] \
        [--episodes N] [--parallel P] [--image IMG] --out DIR
    uv run python webdiplomacy_lab/tools/wd.py metrics DIR --slot 0          # local arena: candidate seat
    uv run python webdiplomacy_lab/tools/wd.py versus ARM_A_DIR ARM_B_DIR     # A/B of arena arms
    uv run python webdiplomacy_lab/tools/wd.py tourney --agents a,b,c --games N --image TAG --out DIR
    uv run python webdiplomacy_lab/tools/wd.py ratings DIR... [--json]        # population leaderboard

`metrics`: per-power results for the target policy's seats next to the FIELD PAR (mean
of every non-target seat at that power in the same directories), plus coverage and our
telemetry (rejected orders, exceptions, activation counters). Without --policy, every
seat is pooled (useful for all-random calibration). Exit code 0 = parsed, 2 = no
target seats found.

`seats`: one JSON row per seat (the miner/A-B input).

`local`: run N local episodes of one image in every seat (own-policy self-play only).

`arena`: LOCAL screening. Slot 0 plays `--candidate`, slots 1-6 play `--field` (policy
names from webdip_bot/bot.py `policy_class`), all inside one image; each episode gets a
fresh random seed and country permutation. Read it with `metrics DIR --slot 0`: par is
then the field's own per-power score, and 1/7 = 0.143 is parity.
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
    if args.slot is not None:
        is_target = lambda s: s.slot == args.slot  # noqa: E731
    else:
        is_target = lambda s: args.policy is None or s.policy == args.policy  # noqa: E731
    target = [s for s in seats if is_target(s)]
    field = [s for s in seats if (args.policy is not None or args.slot is not None) and not is_target(s)]
    if not target:
        print(json.dumps({"error": "no target seats", "policies": sorted({s.policy for s in seats})}))
        return 2
    ours, par = per_power(target), per_power(field) if field else {}
    # Score relative to the same-batch field at the same power: removes most power-strength variance.
    rel = [s.score - par[s.power]["score"] for s in target if par.get(s.power, {}).get("score") is not None]
    logs = [s.log for s in target if s.log]
    report = {
        "game_version": GAME_VERSION,
        "policy": args.policy or (f"slot {args.slot}" if args.slot is not None else "all seats"),
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


# Local arena machines are faster than hosted pods; keep per-phase search time short here.
ARENA_ENV = ["WEBDIP_SEARCH_BUDGET_S=8"]


def cmd_versus(args):
    """Compare local arena arms (slot 0 = candidate in each dir). Prints JSON.

    Power adjustment: each seat's score minus the mean score of ALL candidate seats at that
    power pooled over the arms, so a lucky draw of strong powers does not masquerade as a
    better policy."""
    import math

    arms = {}
    for d in args.dirs:
        seats, _ = load_dirs([Path(d)])
        arms[d] = [s for s in seats if s.slot == 0]
    pooled = defaultdict(list)
    for seats in arms.values():
        for s in seats:
            pooled[s.power].append(s.score)
    power_mean = {p: statistics.mean(v) for p, v in pooled.items()}

    def summary(xs):
        n = len(xs)
        m = statistics.mean(xs) if xs else None
        se = statistics.stdev(xs) / math.sqrt(n) if n > 1 else None
        return {"n": n, "mean": round(m, 4) if m is not None else None, "se": round(se, 4) if se else None}

    out = {"arms": {}}
    for d, seats in arms.items():
        raw = [s.score for s in seats]
        adj = [s.score - power_mean[s.power] for s in seats]
        out["arms"][d] = {"score": summary(raw), "power_adjusted": summary(adj),
                          "solo_rate": round(statistics.mean([s.solo for s in seats]), 3) if seats else None}
    if len(arms) == 2:
        (da, a), (db, b) = arms.items()
        xa = [s.score - power_mean[s.power] for s in a]
        xb = [s.score - power_mean[s.power] for s in b]
        va, vb = statistics.variance(xa) / len(xa), statistics.variance(xb) / len(xb)
        t = (statistics.mean(xb) - statistics.mean(xa)) / math.sqrt(va + vb)
        p = math.erfc(abs(t) / math.sqrt(2))  # normal approximation
        out["diff_b_minus_a_power_adjusted"] = {"diff": round(statistics.mean(xb) - statistics.mean(xa), 4),
                                                "se": round(math.sqrt(va + vb), 4), "z": round(t, 2), "p": round(p, 4)}
    print(json.dumps(out, indent=1))
    return 0


def cmd_tourney(args):
    """Mixed-population self-play: each game seats 7 agents drawn from --agents."""
    import random as _random
    import uuid
    from concurrent.futures import ThreadPoolExecutor

    manifest = _manifest()
    _require_image(args.image)
    agents = args.agents.split(",")
    rng = _random.Random()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    py = "/opt/.venv/bin/python"

    def one(_):
        if args.fixed:
            fixed = args.fixed.split(";")
            k = 7 - len(fixed)
            others = rng.sample(agents, k) if len(agents) >= k else [rng.choice(agents) for _ in range(k)]
            seating = fixed + others
            rng.shuffle(seating)
        else:
            seating = rng.sample(agents, 7) if len(agents) >= 7 else [rng.choice(agents) for _ in range(7)]
        d = out / f"g-{uuid.uuid4().hex[:10]}"
        d.mkdir()
        (d / "seating.json").write_text(json.dumps(seating))
        run = [py, "-m", "players.launcher", py, "-m", "webdip_bot.arena", *seating]
        return _run_one(manifest, args.image, run, args.variant, d)

    with ThreadPoolExecutor(args.parallel) as pool:
        codes = list(pool.map(one, range(args.games)))
    print(json.dumps({"out": str(out), "games": args.games, "failed": sum(c != 0 for c in codes)}))
    return 0


def cmd_ratings(args):
    """Leaderboard over tourney dirs: per agent, power-adjusted mean score (score minus the
    pooled mean score of every seat at that power), raw mean, solo rate, games."""
    import math

    rows = []
    for root in args.dirs:
        for d in sorted(Path(root).glob("g-*")):
            sp = d / "seating.json"
            if not sp.exists() or not (d / "results.json").exists():
                continue
            seating = json.loads(sp.read_text())
            seats, _ = load_dirs([d])
            for s in seats:
                rows.append((seating[s.slot], s))
    by_power = defaultdict(list)
    for _, s in rows:
        by_power[s.power].append(s.score)
    pmean = {p: statistics.mean(v) for p, v in by_power.items()}
    agg = defaultdict(list)
    for agent, s in rows:
        agg[agent].append(s)
    board = []
    for agent, ss in agg.items():
        adj = [s.score - pmean[s.power] for s in ss]
        n = len(ss)
        board.append({
            "agent": agent, "n": n,
            "adj": round(statistics.mean(adj), 4),
            "se": round(statistics.stdev(adj) / math.sqrt(n), 4) if n > 1 else None,
            "score": round(statistics.mean(s.score for s in ss), 4),
            "solo": round(statistics.mean(s.solo for s in ss), 3),
            "centers": round(statistics.mean(s.final_centers or 0 for s in ss), 2),
        })
    board.sort(key=lambda r: -r["adj"])
    if args.json:
        print(json.dumps(board, indent=1))
    else:
        print(f"games: {len({s.episode_id for _, s in rows})}")
        print("| agent | n | adj score | se | raw score | solo | final SCs |\n|---|---|---|---|---|---|---|")
        for r in board:
            print(f"| {r['agent']} | {r['n']} | {r['adj']:+.3f} | {r['se']} | {r['score']:.3f} | {r['solo']} | {r['centers']} |")
    return 0


def _require_image(image):
    """Fail fast if a candidate image is missing (another session's prune deletes tags)."""
    if subprocess.call(["docker", "image", "inspect", image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
        raise SystemExit(f"image {image} is missing locally; rebuild it (docker images get pruned by other sessions)")


def _manifest():
    manifest = next((LAB / "coworld_pkg").glob("cow_*/coworld_manifest.json"), None)
    if manifest is not None:
        _ensure_images(manifest.parent / "coworld_images.json")
    return manifest


def _ensure_images(images_json):
    """Re-pull + re-tag downloaded game/player images if something pruned them.

    Other sessions on this machine prune Docker images to free disk; a missing
    `...:downloaded` tag makes every local episode fail instantly."""
    for img in json.loads(images_json.read_text())["images"]:
        local = img["local_image"]
        if subprocess.call(["docker", "image", "inspect", local], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
            print(f"restoring pruned image {local}", file=sys.stderr)
            subprocess.check_call(["docker", "pull", "--platform", "linux/amd64", img["public_image_uri"]],
                                  stdout=subprocess.DEVNULL)
            subprocess.check_call(["docker", "tag", img["public_image_uri"], local])


def _run_one(manifest, image, run, variant, out, attempts=3):
    """Run one local episode; re-check images first and retry if no results appear.

    Another session's `docker image prune` can delete images mid-batch; the failed
    episode then leaves an empty dir (containers never created)."""
    import shutil

    out = Path(out)
    cmd = ["uv", "run", "coworld", "run-episode", str(manifest), image, "--variant", variant,
           "--output-dir", str(out), "--timeout-seconds", "6000"]
    cmd += [f"--run={token}" for token in run]
    cmd += [f"--secret-env={kv}" for kv in ARENA_ENV]
    env = {**__import__("os").environ, "DOCKER_DEFAULT_PLATFORM": "linux/amd64"}
    code = 1
    for attempt in range(attempts):
        _ensure_images(manifest.parent / "coworld_images.json")
        code = subprocess.call(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if (out / "results.json").exists():
            break
        for child in out.iterdir() if out.exists() else []:
            if child.name != "seating.json":
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    slim_replay(out)
    return code


def slim_replay(episode_dir):
    """Shrink a local replay ~20x: drop map PNGs everywhere, and the cumulative `history`
    and static `variant` from every frame but the last (lab tools read only the last
    frame's history/variant). The disk on this machine runs near full."""
    path = episode_dir / "replay"
    if not path.exists():
        return
    try:
        frames = json.loads(path.read_text())
    except ValueError:
        return
    for f in frames:
        f.pop("map", None)
    for f in frames[:-1]:
        f.pop("history", None)
        f.pop("variant", None)
    path.write_text(json.dumps(frames))


def cmd_arena(args):
    import uuid
    from concurrent.futures import ThreadPoolExecutor

    manifest = _manifest()
    if manifest is None:
        print("run: uv run coworld download webdiplomacy -o webdiplomacy_lab/coworld_pkg", file=sys.stderr)
        return 2
    _require_image(args.image)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    py = "/opt/.venv/bin/python"
    run = [py, "-m", "players.launcher", py, "-m", "webdip_bot.arena", args.candidate, args.field]
    dirs = [out / f"ep-{uuid.uuid4().hex[:10]}" for _ in range(args.episodes)]
    with ThreadPoolExecutor(args.parallel) as pool:
        codes = list(pool.map(lambda d: _run_one(manifest, args.image, run, args.variant, d), dirs))
    print(json.dumps({"out": str(out), "episodes": len(dirs), "failed": sum(c != 0 for c in codes)}))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("metrics")
    m.add_argument("dirs", nargs="+")
    m.add_argument("--policy", help="target policy NAME:vN (hosted); omit to pool all seats")
    m.add_argument("--slot", type=int, help="target seat slot (local arena: 0)")
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
    tr = sub.add_parser("tourney", help="mixed-population local self-play")
    tr.add_argument("--agents", required=True, help="comma-separated personality/policy names")
    tr.add_argument("--fixed", help="league-sim: seat these agents (';'-separated) in every game; the rest come from --agents")
    tr.add_argument("--image", default="webdip-bot:dev")
    tr.add_argument("--variant", default="classic-gunboat")
    tr.add_argument("--games", type=int, default=12)
    tr.add_argument("--parallel", type=int, default=3)
    tr.add_argument("--out", required=True)
    tr.set_defaults(func=cmd_tourney)
    ra = sub.add_parser("ratings", help="leaderboard over tourney dirs")
    ra.add_argument("dirs", nargs="+")
    ra.add_argument("--json", action="store_true")
    ra.set_defaults(func=cmd_ratings)
    sl = sub.add_parser("slim", help="strip map PNGs from local replays under DIRs")
    sl.add_argument("dirs", nargs="+")
    sl.set_defaults(func=lambda a: [slim_replay(p.parent) for d in a.dirs for p in Path(d).rglob("replay")] and 0)
    vs = sub.add_parser("versus", help="compare local arena arms (slot 0)")
    vs.add_argument("dirs", nargs="+")
    vs.set_defaults(func=cmd_versus)
    ar = sub.add_parser("arena")
    ar.add_argument("--candidate", required=True)
    ar.add_argument("--field", default="dumbbot_v1")
    ar.add_argument("--image", default="webdip-bot:dev")
    ar.add_argument("--variant", default="classic-gunboat")
    ar.add_argument("--episodes", type=int, default=8)
    ar.add_argument("--parallel", type=int, default=4)
    ar.add_argument("--out", required=True)
    ar.set_defaults(func=cmd_arena)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
