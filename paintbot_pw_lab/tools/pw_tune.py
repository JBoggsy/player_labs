#!/usr/bin/env python3
"""SPSA tuning of named integer constants in a BASIC policy, scored by local matches.

SCREENING ONLY. The objective is the mean Elo outcome score of the candidate against ONE fixed
opponent file over ONE fixed seed list (both sides of every seed), played in the local native
library (tools/pw_local.py). It overfits that seed list and that opponent by construction.
A tuned file is a hypothesis: re-screen it on fresh seeds (--confirm-seeds or pw_local screen)
and confirm it against the field with a hosted A/B (paintbot-pw-ab / coworld-ab) before it
decides anything. See docs/tools/pw_tune.md.

Mark a tunable on its assignment line (integer constants only; BASIC is int32):

    kWetCost = 6 ' @tune 2 12 1          -> name kWetCost, range [2, 12], step 1
    kRetreatMargin = 1 ' @tune 0 3       -> step defaults to 1

    uv run paintbot_pw_lab/tools/pw_tune.py knobs CANDIDATE.bas
    uv run paintbot_pw_lab/tools/pw_tune.py run CANDIDATE.bas OPPONENT.bas --seeds 1-8 \
        --iterations 20 --log DIR/tune.jsonl [--confirm-seeds 101-116]
    uv run paintbot_pw_lab/tools/pw_tune.py render CANDIDATE.bas --log DIR/tune.jsonl --out TUNED.bas

The log is JSONL and the run is resumable: rerun the same `run` command (a larger --iterations
extends it). A log written with a different candidate, opponent, seeds, build or SPSA settings
is refused.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pw_cli  # noqa: E402
import pw_local  # noqa: E402

GUARDRAIL = ("SCREENING ONLY: tuned against one opponent file on one local seed list. Re-screen on "
             "fresh seeds and confirm with a hosted A/B (paintbot-pw-ab) before using it.")

TUNE_MARK = re.compile(r"'\s*@tune\b", re.IGNORECASE)
TUNE_LINE = re.compile(
    r"^(?P<head>\s*(?P<name>[A-Za-z_]\w*)\s*=\s*)(?P<value>-?\d+)"
    r"(?P<tail>\s*'\s*@tune\s+(?P<low>-?\d+)\s+(?P<high>-?\d+)(?:\s+(?P<step>\d+))?\b.*)$",
    re.IGNORECASE)

# SPSA gain schedule (Spall 1998, "Implementation of the simultaneous perturbation algorithm"):
# a_k = a / (k + 1 + A)^ALPHA, c_k = c / (k + 1)^GAMMA, in knob space normalized to [0, 1].
ALPHA = 0.602
GAMMA = 0.101


# ---------------------------------------------------------------------------------------------
# Knobs: parse and render (tested in tools/tests/test_pw_tune.py)

@dataclass
class Knob:
    name: str
    line: int      # 0-based line index in the source
    value: int     # the value written in the file (the starting point)
    low: int
    high: int
    step: int

    def to_value(self, u: float) -> int:
        """Normalized position u in [0, 1] -> the nearest allowed value on the step grid."""
        u = min(1.0, max(0.0, u))
        steps = round(u * (self.high - self.low) / self.step)
        return min(self.high, self.low + steps * self.step)

    def to_unit(self, value: int) -> float:
        return (value - self.low) / (self.high - self.low)


def parse_knobs(text: str) -> list[Knob]:
    """Every `NAME = INT ' @tune LOW HIGH [STEP]` line. A line that carries an @tune mark but
    does not match the convention is an error, never silently skipped."""
    knobs: list[Knob] = []
    for index, line in enumerate(text.splitlines()):
        if not TUNE_MARK.search(line):
            continue
        match = TUNE_LINE.match(line)
        if not match:
            raise ValueError(f"line {index + 1}: @tune needs `NAME = INTEGER ' @tune LOW HIGH [STEP]`: {line.strip()}")
        knob = Knob(match["name"], index, int(match["value"]), int(match["low"]), int(match["high"]),
                    int(match["step"] or 1))
        if knob.step <= 0 or knob.high <= knob.low:
            raise ValueError(f"line {index + 1}: need LOW < HIGH and STEP > 0")
        if not knob.low <= knob.value <= knob.high:
            raise ValueError(f"line {index + 1}: {knob.name} = {knob.value} is outside [{knob.low}, {knob.high}]")
        if (knob.value - knob.low) % knob.step:
            raise ValueError(f"line {index + 1}: {knob.name} = {knob.value} is not on the step grid from {knob.low}")
        if any(k.name.lower() == knob.name.lower() for k in knobs):
            raise ValueError(f"line {index + 1}: {knob.name} is marked @tune twice")
        knobs.append(knob)
    if not knobs:
        raise ValueError("no `' @tune LOW HIGH [STEP]` lines found")
    return knobs


def read_knobs(path_text: str, flag: str = "candidate") -> tuple[str, list[Knob]]:
    """(text, knobs) of a .bas for the CLI: a missing file or bad @tune marks are usage errors."""
    text = pw_local.policy_path(path_text, flag).read_text()
    try:
        return text, parse_knobs(text)
    except ValueError as error:
        raise pw_cli.UsageError(f"{path_text}: {error}") from error


def render(text: str, knobs: list[Knob], values: dict[str, int]) -> str:
    """The source with each knob's assignment set to values[name]; every other byte unchanged."""
    lines = text.split("\n")
    for knob in knobs:
        match = TUNE_LINE.match(lines[knob.line].rstrip("\r"))
        ending = "\r" if lines[knob.line].endswith("\r") else ""
        lines[knob.line] = f"{match['head']}{int(values[knob.name])}{match['tail']}{ending}"
    return "\n".join(lines)


def values_at(knobs: list[Knob], u: np.ndarray) -> dict[str, int]:
    return {k.name: k.to_value(float(x)) for k, x in zip(knobs, u)}


# ---------------------------------------------------------------------------------------------
# SPSA step (pure; tested)

def gains(k: int, settings: dict) -> tuple[float, float]:
    a_k = settings["a"] / (k + 1 + settings["A"]) ** ALPHA
    c_k = settings["c"] / (k + 1) ** GAMMA
    return a_k, c_k


def perturbation(k: int, dimensions: int, rng_seed: int) -> np.ndarray:
    """Rademacher +-1 vector, a pure function of (rng_seed, k) so a resumed run replays it."""
    rng = np.random.default_rng([rng_seed, k])
    return rng.choice([-1.0, 1.0], size=dimensions)


def spsa_points(u: np.ndarray, delta: np.ndarray, c_k: float, knobs: list[Knob]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Plus and minus points. Each knob's perturbation is at least one grid step, otherwise
    rounding could make both points identical and the gradient estimate zero."""
    c_vec = np.array([max(c_k, k.step / (k.high - k.low)) for k in knobs])
    return np.clip(u + c_vec * delta, 0, 1), np.clip(u - c_vec * delta, 0, 1), c_vec


def spsa_update(u: np.ndarray, delta: np.ndarray, c_vec: np.ndarray, y_plus: float, y_minus: float,
                a_k: float, max_move: float) -> tuple[np.ndarray, np.ndarray]:
    """Gradient ASCENT on the outcome (higher is better); each coordinate moves at most max_move."""
    gradient = (y_plus - y_minus) / (2 * c_vec * delta)
    move = np.clip(a_k * gradient, -max_move, max_move)
    return np.clip(u + move, 0, 1), gradient


# ---------------------------------------------------------------------------------------------
# Log

def read_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def append_log(path: Path, record: dict) -> None:
    with path.open("a") as stream:
        stream.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------------------------
# Evaluation on the native library

class Evaluator:
    """One pool of library workers for the whole run; each call plays every seed on both sides."""

    def __init__(self, pool, opponent_src: bytes, max_ticks: int):
        self.pool = pool
        self.opponent_src = opponent_src
        self.max_ticks = max_ticks

    def many(self, candidates: list[bytes], seeds: list[int]) -> list[dict]:
        """Score several candidate sources in one batch (keeps every worker busy)."""
        jobs = [{"seed": s, "a_side": side, "a_src": src, "b_src": self.opponent_src,
                 "max_ticks": self.max_ticks, "arm": i}
                for i, src in enumerate(candidates) for s in seeds for side in (0, 1)]
        rows = self.pool.map(pw_local.run_match, jobs, chunksize=1)
        results = []
        for i in range(len(candidates)):
            arm = [r for r, job in zip(rows, jobs) if job["arm"] == i]
            summary = pw_local.summarize(arm)
            results.append({
                "outcome": summary["all"]["mean_outcome"], "n": len(arm),
                "seed_balanced": summary["seed_balanced"],
                "wins": summary["all"]["wins"], "draws": summary["all"]["draws"],
                "losses": summary["all"]["losses"],
                "bad_candidate_seats": sum(1 for r in arm for b in r["bad_seats"] if b["policy"] == "A"),
                "hashes": [r["final_hash"] for r in arm]})
        return results


def run_config(args, knobs: list[Knob], build: dict, candidate: Path, opponent: Path) -> dict:
    return {
        "candidate": pw_local.policy_info(candidate), "opponent": pw_local.policy_info(opponent),
        "knobs": [asdict(k) for k in knobs], "seeds": pw_local.parse_seeds(args.seeds),
        "confirm_seeds": pw_local.parse_seeds(args.confirm_seeds) if args.confirm_seeds else None,
        "build": {k: build[k] for k in ("tag", "commit")}, "glory": json.loads(args.glory),
        "max_ticks": args.max_ticks,
        "spsa": {"a": args.a, "c": args.c, "A": args.big_a, "alpha": ALPHA, "gamma": GAMMA,
                 "max_move": args.max_move, "rng_seed": args.rng_seed},
    }


def cmd_run(args, report) -> dict:
    candidate = Path(args.candidate)
    text, knobs = read_knobs(args.candidate)
    opponent = pw_local.policy_path(args.opponent, "opponent")
    log = Path(args.log)
    pw_local.parse_seed_list(args.seeds, "--seeds")
    if args.confirm_seeds:
        pw_local.parse_seed_list(args.confirm_seeds, "--confirm-seeds")
    build = pw_local.check_build(args.tag)
    records = read_log(log)
    if args.big_a is None:
        # A resumed run keeps the logged A, so extending --iterations does not change the schedule.
        args.big_a = records[0]["config"]["spsa"]["A"] if records else max(1.0, args.iterations / 10)
    config = json.loads(json.dumps(run_config(args, knobs, build, candidate, opponent)))
    if records:
        if records[0].get("config") != config:
            raise pw_cli.UsageError(f"refusing to resume {log}: it was written with a different candidate, "
                                    "opponent, seeds, build or SPSA settings. Use a new --log.")
        print(f"resuming {log}: {sum(r['kind'] == 'iter' for r in records)} iterations logged", file=sys.stderr)
    log.parent.mkdir(parents=True, exist_ok=True)

    seeds = config["seeds"]
    spsa = config["spsa"]
    u = np.array([k.to_unit(k.value) for k in knobs])
    done = {r["k"]: r for r in records if r["kind"] == "iter"}
    for k in sorted(done):
        u = np.array(done[k]["u_after"])
    evals = {r["label"]: r for r in records if r["kind"] == "eval"}

    glory = config["glory"]
    context = multiprocessing.get_context("spawn")
    workers = max(2, min(args.workers, len(seeds) * 4))
    with context.Pool(workers, initializer=pw_local._init_worker, initargs=(build["lib"], glory)) as pool:
        if not records:
            # Parity guard once per run, on the starting file (engine identity does not depend on
            # the knob values; it proves library == paintbot-headless for this build and seating).
            parity = pw_local.parity_guard(build, pool, candidate, opponent, candidate.read_bytes(),
                                           opponent.read_bytes(), seeds, args.max_ticks, glory)
            append_log(log, {"kind": "start", "config": config, "parity": parity,
                             "started": time.strftime("%Y-%m-%dT%H:%M:%S")})
        evaluator = Evaluator(pool, opponent.read_bytes(), args.max_ticks)

        if "initial" not in evals:
            start_values = {k.name: k.value for k in knobs}
            (result,) = evaluator.many([render(text, knobs, start_values).encode()], seeds)
            evals["initial"] = {"kind": "eval", "label": "initial", "seeds": "tune", "values": start_values, **result}
            append_log(log, evals["initial"])
            print(f"initial {start_values}: outcome {result['outcome']:.4f} (n={result['n']})", file=sys.stderr)

        for k in range(len(done), args.iterations):
            started = time.time()
            a_k, c_k = gains(k, spsa)
            delta = perturbation(k, len(knobs), spsa["rng_seed"])
            u_plus, u_minus, c_vec = spsa_points(u, delta, c_k, knobs)
            v_plus, v_minus = values_at(knobs, u_plus), values_at(knobs, u_minus)
            plus, minus = evaluator.many([render(text, knobs, v_plus).encode(),
                                          render(text, knobs, v_minus).encode()], seeds)
            u_after, gradient = spsa_update(u, delta, c_vec, plus["outcome"], minus["outcome"], a_k, spsa["max_move"])
            record = {"kind": "iter", "k": k, "a_k": a_k, "c_k": c_k, "delta": delta.tolist(),
                      "u": u.tolist(), "values": values_at(knobs, u),
                      "plus": {"values": v_plus, **plus}, "minus": {"values": v_minus, **minus},
                      "gradient": gradient.tolist(), "u_after": u_after.tolist(),
                      "values_after": values_at(knobs, u_after), "seconds": round(time.time() - started, 1)}
            append_log(log, record)
            print(f"iter {k:>3}  +{v_plus} {plus['outcome']:.4f}  -{v_minus} {minus['outcome']:.4f}  "
                  f"-> {record['values_after']}  ({record['seconds']} s)", file=sys.stderr)
            u = u_after

        final_values = values_at(knobs, u)
        label = f"final@{args.iterations}"
        if label not in evals:
            (result,) = evaluator.many([render(text, knobs, final_values).encode()], seeds)
            evals[label] = {"kind": "eval", "label": label, "seeds": "tune", "values": final_values, **result}
            append_log(log, evals[label])
        confirm = config["confirm_seeds"]
        confirm_label = f"confirm@{args.iterations}"
        if confirm and confirm_label not in evals:
            start_values = {k.name: k.value for k in knobs}
            start, final = evaluator.many([render(text, knobs, start_values).encode(),
                                           render(text, knobs, final_values).encode()], confirm)
            evals[confirm_label] = {"kind": "eval", "label": confirm_label, "seeds": "confirm",
                                    "initial": {"values": start_values, **start},
                                    "final": {"values": final_values, **final}}
            append_log(log, evals[confirm_label])

    if args.out:
        Path(args.out).write_text(render(text, knobs, final_values))
        report.output(args.out)
    print_report(knobs, evals, label, confirm_label, args.out)
    report.output(log)
    report.counts["processed"] = args.iterations
    bad = sum(e.get("bad_candidate_seats", 0) for e in (evals["initial"], evals[label]))
    if bad:
        report.fail("candidate", "bad_seats", f"{bad} candidate seats failed to compile or were disabled at runtime")
    report.suggest(f"re-screen the tuned file on fresh seeds: uv run python paintbot_pw_lab/tools/pw.py local screen "
                   f"{args.out or 'TUNED.bas'} {args.opponent} --seeds 201-228 --json")
    return {"guardrail": GUARDRAIL, "log": str(log), "out": args.out, "initial": evals["initial"],
            "final": evals[label], "confirm": evals.get(confirm_label)}


def _ci(result: dict) -> str:
    balanced = result["seed_balanced"]
    if balanced["ci95_low"] is None:
        return ""
    return f" seed-balanced 95% CI [{balanced['ci95_low']:.3f}, {balanced['ci95_high']:.3f}]"


def print_report(knobs, evals, label, confirm_label, out) -> None:
    initial, final = evals["initial"], evals[label]
    print(GUARDRAIL)
    print(f"knobs: {', '.join(f'{k.name} [{k.low},{k.high}] step {k.step}' for k in knobs)}")
    print(f"tune seeds   initial {initial['values']}: outcome {initial['outcome']:.4f} "
          f"(W/D/L {initial['wins']}/{initial['draws']}/{initial['losses']}){_ci(initial)}")
    print(f"tune seeds   final   {final['values']}: outcome {final['outcome']:.4f} "
          f"(W/D/L {final['wins']}/{final['draws']}/{final['losses']}){_ci(final)}")
    print("  (the tune-seed numbers are selected on those seeds: biased upward)")
    if confirm_label in evals:
        c = evals[confirm_label]
        for name in ("initial", "final"):
            r = c[name]
            print(f"confirm seeds {name:<7} {r['values']}: outcome {r['outcome']:.4f} "
                  f"(W/D/L {r['wins']}/{r['draws']}/{r['losses']}){_ci(r)}")
    bad = sum(e.get("bad_candidate_seats", 0) for e in (initial, final))
    if bad:
        print(f"WARNING: {bad} candidate seats failed to compile or were disabled at runtime")
    if out:
        print(f"wrote {out}")


def cmd_knobs(args, report) -> dict:
    _, knobs = read_knobs(args.candidate)
    for knob in knobs:
        print(f"line {knob.line + 1:>5}  {knob.name:<24} = {knob.value:<8} range [{knob.low}, {knob.high}] step {knob.step}")
    report.counts["processed"] = len(knobs)
    return {"knobs": [asdict(k) for k in knobs]}


def cmd_render(args, report) -> dict:
    text, knobs = read_knobs(args.candidate)
    values = {k.name: k.value for k in knobs}
    if args.log:
        iters = [r for r in read_log(Path(args.log)) if r["kind"] == "iter"]
        if not iters:
            raise pw_cli.UsageError(f"{args.log} has no iterations")
        values.update(iters[-1]["values_after"])
    for item in args.set or []:
        name, _, value = item.partition("=")
        if name not in values:
            raise pw_cli.UsageError(f"--set {name}: not a knob in {args.candidate}", sorted(values))
        try:
            values[name] = int(value)
        except ValueError:
            raise pw_cli.UsageError(f"--set {item}: the value must be an integer (NAME=VALUE)") from None
    for knob in knobs:
        if not knob.low <= values[knob.name] <= knob.high:
            raise pw_cli.UsageError(f"{knob.name} = {values[knob.name]} is outside [{knob.low}, {knob.high}]")
    Path(args.out).write_text(render(text, knobs, values))
    print(f"wrote {args.out}: {values}")
    report.output(args.out)
    return {"out": args.out, "values": values}


def main(argv: list[str] | None = None) -> int:
    parser = pw_cli.ArgumentParser("pw_tune", __doc__, examples=[
        "uv run python paintbot_pw_lab/tools/pw_tune.py knobs CANDIDATE.bas --json",
        "uv run python paintbot_pw_lab/tools/pw_tune.py run CANDIDATE.bas paintbot_pw_lab/reference/base.bas "
        "--seeds 1-8 --iterations 20 --log /tmp/tune/tune.jsonl --confirm-seeds 101-116 --json",
        "uv run python paintbot_pw_lab/tools/pw_tune.py render CANDIDATE.bas --log /tmp/tune/tune.jsonl --out TUNED.bas"])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("knobs", help="list the @tune constants in a .bas file")
    p.add_argument("candidate", help=".bas with @tune marks, e.g. CANDIDATE.bas")
    p.set_defaults(func=cmd_knobs)

    p = sub.add_parser("run", help="SPSA over the @tune constants vs a fixed opponent (resumable)")
    p.add_argument("candidate", help=".bas with @tune marks (its written values are the start point)")
    p.add_argument("opponent", help="fixed opponent .bas")
    p.add_argument("--seeds", required=True, help="tuning seeds, each played on both sides, e.g. 1-8")
    p.add_argument("--iterations", type=int, required=True,
                   help="total SPSA iterations (a larger value extends a resumed log), e.g. 20")
    p.add_argument("--log", required=True, help="JSONL log; rerun the same command to resume")
    p.add_argument("--confirm-seeds", help="fresh seeds to score start vs final on at the end, e.g. 101-116")
    p.add_argument("--out", help="write the final .bas here")
    p.add_argument("--a", type=float, default=1.0, help="SPSA step gain a (normalized units; default %(default)s)")
    p.add_argument("--c", type=float, default=0.2, help="SPSA perturbation c (fraction of each range; default %(default)s)")
    p.add_argument("--big-a", type=float, help="SPSA stability constant A (default iterations/10, min 1)")
    p.add_argument("--max-move", type=float, default=0.2, help="cap on one iteration's move per knob (fraction of range)")
    p.add_argument("--rng-seed", type=int, default=0, help="seed of the +-1 perturbation sequence")
    p.add_argument("--tag", default=pw_local.DEFAULT_TAG, help="engine build tag (default %(default)s)")
    p.add_argument("--glory", default=json.dumps(pw_local.LEAGUE_GLORY),
                   help="glory award JSON (default: the league's %(default)s)")
    p.add_argument("--max-ticks", type=int, default=pw_local.MAX_TICKS, help="tick cap (default %(default)s)")
    p.add_argument("--workers", type=int, default=os.cpu_count() or 1, help="processes (default: all cores)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("render", help="write the .bas with values from a log's last iteration and/or --set")
    p.add_argument("candidate", help=".bas with @tune marks")
    p.add_argument("--log", help="tune.jsonl whose last iteration supplies the values")
    p.add_argument("--set", action="append", help="NAME=VALUE (repeatable; applied after --log), e.g. --set kWetCost=8")
    p.add_argument("--out", required=True, help="the .bas to write, e.g. TUNED.bas")
    p.set_defaults(func=cmd_render)

    return pw_cli.run(parser, lambda args, report: args.func(args, report), argv)


if __name__ == "__main__":
    sys.exit(main())
