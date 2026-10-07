#!/usr/bin/env python3
"""Evolutionary self-play over SearchBot configs ("genomes"), unattended.

    uv run python webdiplomacy_lab/tools/evolve.py --image webdip-bot:TAG [--generations N]
        [--games 12] [--parallel 3] [--state webdiplomacy_lab/experiments/evolve_state.json]

Each generation seats 6 genomes + the frozen Calhamer anchor in every game (a full
7-seat round robin with random powers), plays `--games` local games, and scores each
genome by power-adjusted score (score minus the generation's mean score at that power).
Fitness is an exponential moving average across the generations a genome survives, so
lucky single generations wash out. Selection: keep the top 3 (elites), refill with
mutants/crossovers of the elites. State is saved after every generation (resumable);
one ledger line per generation goes to experiments/ledger.jsonl.

Genomes are plain config overrides, played as `search:K=V,...` policy strings.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wd  # noqa: E402
from webdip_episodes import load_dirs  # noqa: E402

LAB = Path(__file__).resolve().parents[1]

# name -> (kind, low, high); kind: int | float | choice(list)
SPACE = {
    "SPRING_ATTACK_WEIGHT": ("int", 200, 1000),
    "SPRING_DEFENSE_WEIGHT": ("int", 0, 800),
    "FALL_ATTACK_WEIGHT": ("int", 200, 1000),
    "FALL_DEFENSE_WEIGHT": ("int", 0, 800),
    "STRENGTH_WEIGHT": ("int", 0, 2000),
    "COMPETITION_WEIGHT": ("int", 0, 2000),
    "SEARCH_POS_WEIGHT": ("float", 0.0, 5.0),
    "SEARCH_DISLODGED_WEIGHT": ("float", 0.0, 10.0),
    "SEARCH_OPPONENT_SAMPLES": ("int", 6, 32),
    "SEARCH_RESTARTS": ("int", 1, 3),
    "SEARCH_OBJECTIVE": ("choice", ["sc", "share"]),
    "SEARCH_BUILDS": ("choice", [0, 1]),
    "OPP_MODEL_LEVEL": ("choice", [0, 0, 0, 1]),
    "SEARCH_RISK": ("float", 0.0, 1.0),
    "SEARCH_EVAL": ("choice", ["projected", "projected", "learned"]),
    "SEARCH_LEARNED_WEIGHT": ("float", 0.0, 1.0),
}

SEEDS = {
    "machiavelli-r1": {"SEARCH_RESTARTS": 1},
    "bismarck": {"SPRING_ATTACK_WEIGHT": 900, "SPRING_DEFENSE_WEIGHT": 100, "FALL_ATTACK_WEIGHT": 850,
                 "FALL_DEFENSE_WEIGHT": 150, "SEARCH_DISLODGED_WEIGHT": 0.5, "SEARCH_POS_WEIGHT": 2.0,
                 "SEARCH_RESTARTS": 1},
    "talleyrand": {"SEARCH_OBJECTIVE": "share", "SEARCH_RESTARTS": 1},
    "bismarck-share": {"SPRING_ATTACK_WEIGHT": 900, "SPRING_DEFENSE_WEIGHT": 100, "FALL_ATTACK_WEIGHT": 850,
                       "FALL_DEFENSE_WEIGHT": 150, "SEARCH_DISLODGED_WEIGHT": 0.5, "SEARCH_POS_WEIGHT": 2.0,
                       "SEARCH_OBJECTIVE": "share", "SEARCH_RESTARTS": 1},
    "napoleon-r1": {"SEARCH_ROLLOUT": 1, "SEARCH_RESTARTS": 1},
    "default": {},
}
ANCHOR = "machiavelli"  # the current champion: fitness = beating the best, not the average


def policy_string(genome):
    if not genome:
        return "search"
    return "search:" + ",".join(f"{k}={v}" for k, v in sorted(genome.items()))


def mutate(genome, rng, strength=0.25):
    g = dict(genome)
    for key in rng.sample(sorted(SPACE), k=rng.randint(1, 3)):
        kind, *spec = SPACE[key]
        if kind == "choice":
            g[key] = rng.choice(spec[0])
        else:
            lo, hi = spec
            cur = g.get(key, (lo + hi) / 2)
            val = cur + rng.gauss(0, strength * (hi - lo))
            val = min(hi, max(lo, val))
            g[key] = int(round(val)) if kind == "int" else round(val, 2)
    return g


def play_generation(population, args, gen):
    out = LAB / "local_runs" / f"evolve-g{gen:03d}"
    out.mkdir(parents=True, exist_ok=True)
    manifest = wd._manifest()
    names = list(population)
    py = "/opt/.venv/bin/python"
    rng = random.Random()

    def one(_):
        seating = names + [ANCHOR]
        rng.shuffle(seating)
        d = out / f"g-{uuid.uuid4().hex[:10]}"
        d.mkdir()
        (d / "seating.json").write_text(json.dumps(seating))
        policies = [ANCHOR if s == ANCHOR else policy_string(population[s]["genome"]) for s in seating]
        return wd._run_one(manifest, args.image, [py, "-m", "players.launcher", py, "-m", "webdip_bot.arena", *policies],
                           "classic-gunboat", d)

    with ThreadPoolExecutor(args.parallel) as pool:
        list(pool.map(one, range(args.games)))
    rows = []
    for d in sorted(out.glob("g-*")):
        if not (d / "results.json").exists():
            continue
        seating = json.loads((d / "seating.json").read_text())
        seats, _ = load_dirs([d])
        rows.extend((seating[s.slot], s) for s in seats)
    by_power = defaultdict(list)
    for _, s in rows:
        by_power[s.power].append(s.score)
    pmean = {p: statistics.mean(v) for p, v in by_power.items()}
    scores = defaultdict(list)
    for name, s in rows:
        scores[name].append(s.score - pmean[s.power])
    return out, {n: statistics.mean(v) for n, v in scores.items()}, len({s.episode_id for _, s in rows})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True)
    ap.add_argument("--generations", type=int, default=1000)
    ap.add_argument("--games", type=int, default=12)
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--state", default=str(LAB / "experiments" / "evolve_state.json"))
    args = ap.parse_args()
    wd._require_image(args.image)
    state_path = Path(args.state)
    rng = random.Random()
    if state_path.exists():
        state = json.loads(state_path.read_text())
    else:
        state = {"generation": 0, "population": {n: {"genome": g, "fitness": None, "generations": 0, "parent": None}
                                                 for n, g in SEEDS.items()}}
    for _ in range(args.generations):
        gen = state["generation"]
        pop = state["population"]
        started = time.time()
        out, fit, games = play_generation(pop, args, gen)
        for name, f in fit.items():
            if name == ANCHOR:
                continue
            p = pop[name]
            p["fitness"] = f if p["fitness"] is None else round(0.5 * p["fitness"] + 0.5 * f, 4)
            p["generations"] += 1
            p["last"] = round(f, 4)
        ranked = sorted(pop, key=lambda n: -(pop[n]["fitness"] if pop[n]["fitness"] is not None else -9))
        elites = ranked[:3]
        record = {"date": time.strftime("%Y-%m-%d %H:%M"), "run": out.name, "question": "evolve generation",
                  "image": args.image, "games": games, "anchor_adj": round(fit.get(ANCHOR, 0), 4),
                  "result": {n: {"fitness": pop[n]["fitness"], "last": pop[n].get("last"), "gens": pop[n]["generations"]}
                             for n in ranked},
                  "verdict": f"elites {elites}", "minutes": round((time.time() - started) / 60, 1)}
        with open(LAB / "experiments" / "ledger.jsonl", "a") as f:
            f.write(json.dumps(record) + "\n")
        new_pop = {n: pop[n] for n in elites}
        while len(new_pop) < 6:
            if rng.random() < 0.3:
                a, b = rng.sample(elites, 2)
                child = mutate({**pop[a]["genome"], **{k: v for k, v in pop[b]["genome"].items() if rng.random() < 0.5}}, rng, 0.1)
                parent = f"{a}x{b}"
            else:
                a = rng.choice(elites)
                child = mutate(pop[a]["genome"], rng)
                parent = a
            name = f"g{gen + 1}-{uuid.uuid4().hex[:4]}"
            new_pop[name] = {"genome": child, "fitness": None, "generations": 0, "parent": parent}
        state = {"generation": gen + 1, "population": new_pop,
                 "hall_of_fame": (state.get("hall_of_fame", []) + [{"gen": gen, "name": elites[0], **pop[elites[0]]}])[-20:]}
        state_path.write_text(json.dumps(state, indent=1))
        print(json.dumps({"generation": gen, "games": games, "elites": elites}), flush=True)


if __name__ == "__main__":
    main()
