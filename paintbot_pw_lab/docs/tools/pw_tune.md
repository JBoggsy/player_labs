# pw_tune.py: SPSA tuning of BASIC constants

Part of the [lab tool index](README.md) (dispatcher: `pw.py tune`). Searches named integer
constants in a BASIC policy for a higher mean Elo outcome score against
one fixed opponent file, using local matches in the native library ([pw_local](pw_local.md)).
**Screening only.** It tunes against one opponent on one seed list, so it overfits both by
construction. A tuned file is a hypothesis to re-screen on fresh seeds and then confirm against
the field with a hosted A/B (`paintbot-pw-ab` / `coworld-ab`). Skill:
[`paintbot-pw-tune`](../../.claude/skills/paintbot-pw-tune/SKILL.md).

Files: [`tools/pw_tune.py`](../../tools/pw_tune.py), tests in
[`tools/tests/test_pw_tune.py`](../../tools/tests/test_pw_tune.py).

## The `@tune` convention

Mark a constant on its assignment line with a trailing comment. Integers only (BASIC is int32).

```basic
if started = 0 then
  started = 1
  kWetCost = 6 ' @tune 2 12 1          ' name kWetCost, range [2, 12], step 1
  kRetreatMargin = 1 ' @tune 0 4       ' step defaults to 1
end if
```

- Form: `NAME = INTEGER ' @tune LOW HIGH [STEP]`. The name is the assigned variable; the
  written value is the starting point and must lie on the grid `LOW + k·STEP` in `[LOW, HIGH]`.
- Any line carrying `' @tune` that does not match is an error, never skipped. Duplicate names
  (case-insensitive, as BASIC) are an error.
- Put tunables in the `if started = 0` block so they are set once per cog. `render` rewrites
  only the value; every other byte (including CRLF endings) is unchanged, so the marks can stay
  in the uploaded file (they are comments).

## Commands

Run from the repo root. Needs `tools/build_native.sh` (same build guard as pw_local).

```bash
uv run paintbot_pw_lab/tools/pw_tune.py knobs CANDIDATE.bas

uv run paintbot_pw_lab/tools/pw_tune.py run CANDIDATE.bas OPPONENT.bas --seeds 1-8 --iterations 20 \
    --log <scratch>/tune.jsonl --confirm-seeds 101-124 --out <scratch>/tuned.bas \
    [--a 1.0] [--c 0.2] [--big-a N] [--max-move 0.2] [--rng-seed 0] [--workers N] [--tag] [--glory] [--max-ticks]

uv run paintbot_pw_lab/tools/pw_tune.py render CANDIDATE.bas --log <scratch>/tune.jsonl [--set NAME=V ...] --out X.bas
```

`run`:

1. Checks the build (`libpw.build.json`), then runs pw_local's **parity guard once** (starting
   file vs opponent: library and `paintbot-headless` final hashes must match on two matches,
   one per side). Knob values do not change engine identity, so once per run is enough.
2. Scores the starting values on the tuning seeds (`initial`).
3. Per iteration k: a ±1 perturbation Δ (a pure function of `(rng_seed, k)`), gains
   `a_k = a / (k + 1 + A)^0.602` and `c_k = c / (k + 1)^0.101` (Spall's standard exponents) in
   knob space normalized to [0, 1]. The plus and minus points (each knob perturbed at least one
   grid step) are both played on **every tuning seed on both sides**, the same seeds for both
   (common random numbers), in one batch. Objective = the candidate's mean Elo outcome score
   `clamp(0.5 + (A − B glory)/2000, 0, 1)`. Update: gradient **ascent**, each knob moving at most
   `--max-move` of its range per iteration, clipped to the range, rounded to the grid.
4. Scores the final values on the tuning seeds (`final@N`) and, with `--confirm-seeds`, the
   starting and final values on those fresh seeds (`confirm@N`). Writes `--out`.

Defaults: `a = 1.0`, `c = 0.2`, `A = iterations / 10` (min 1), `max_move = 0.2`, `rng_seed = 0`,
`--workers` all cores; `--tag`, `--glory`, `--max-ticks` as in [pw_local](pw_local.md).
Cost per iteration = 4 × seeds matches (2 points × 2 sides); at ~1.5 matches/s on 14 cores,
8 seeds ≈ 22 s per iteration.

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py tune knobs|run|render ... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `knobs CAND`; `run CAND OPP --seeds --iterations --log FILE [--confirm-seeds] [--out]` plus SPSA settings, `--tag`, `--glory`, `--max-ticks`, `--workers`; `render CAND [--log] [--set N=V] --out` |
| Outputs | `run`: the JSONL log (appended) and `--out` .bas; `render`: the `--out` .bas |
| `--json` result | `knobs`: `{knobs: [{name, line, value, low, high, step}]}` (`line` 0-based; the text output prints it 1-based); `run`: `{guardrail, log, out, initial, final, confirm}` (`initial`/`final` are the log's `eval` records; `confirm` is null without `--confirm-seeds`); `render`: `{out, values}` |
| Exit codes | 0 ok; 1 candidate seats failed to compile or were disabled (failure code `bad_seats`); 2 no or malformed `@tune` marks, a missing file, bad seeds, a log written with other settings, an unknown or non-integer `--set` (`NAME=VALUE`) or a value out of range; 3 the library is missing or stale (`next[0]`) |
| Idempotence / cache | the log makes `run` resumable: the same command continues it, a larger `--iterations` extends it |
| Typical next step | re-screen the tuned file on fresh seeds with `local screen`, then a hosted A/B |

## Log (resumable JSONL)

- `start`: `config` (candidate and opponent path + sha256, knobs, seeds, confirm seeds, build tag
  and commit, glory, max ticks, SPSA settings), the parity checks and `started` (local time).
- `eval` with `label` `initial` or `final@N` (`seeds: "tune"`): `values`, `outcome`, `n`, `wins`/
  `draws`/`losses`, `seed_balanced` (mean and CI), `bad_candidate_seats` (candidate seats that
  failed to compile or were disabled), per-match `hashes`.
- `eval` with `label` `confirm@N` (`seeds: "confirm"`): `initial` and `final`, each with those
  same fields, scored on the confirm seeds.
- `iter`: `k`, `a_k`, `c_k`, `delta`, `u`, `values`, `plus`/`minus` (values + the same fields as
  `eval`), `gradient`, `u_after`, `values_after`, `seconds`.

Rerunning the same command resumes after the last logged iteration; a larger `--iterations`
extends the run (A is taken from the log). A log whose `config` differs (another file, seed
list, build or SPSA setting) is refused: use a new `--log`.

## Verified (2026-09-29, coworld-v0.3.78, 14-core Mac)

Re-checked at coworld-v0.3.79 (2026-09-29): `knobs`, a 1-iteration `run` with `--confirm-seeds`
and `--out` (log records and result keys as above), `render --log … --set kWetCost=8` (one line
changed), and the refusal to resume a log with a changed seed list (exit 2).

- Tiny run: a copy of base.bas with 2 knobs (`kWetCost` 6 in [2, 12]; a new `kRetreatMargin`
  1 in [0, 4] replacing the literal 1 in `foesNear - friendsNear >= 1`) vs base.bas, seeds
  1–6, 3 iterations, confirm seeds 101–112: parity ok; 13.5–16.5 s per iteration (24 matches);
  100 s total. Start values scored exactly 0.500 (a file against its own logic, seed-balanced:
  the free identity check). Perturbed points scored 0.35–0.59 (6 of 8 below 0.5; the best was
  `kWetCost` 4, `kRetreatMargin` 2 at 0.586 on 6 seeds). SPSA ended at `kWetCost` 5,
  `kRetreatMargin` 1, which scored 0.400 on the tuning seeds and 0.435 [0.297, 0.574] on the
  confirm seeds: no improvement found. Three iterations is a demonstration, not a search.
- Resume: rerunning with `--iterations 4` ran only iteration 3 and the new final/confirm
  evals; a changed seed list was refused.
- `render --log ... --set kRetreatMargin=2` changed exactly the two knob lines.
- Determinism: identical values on identical seeds gave identical outcomes (`final@3` =
  `final@4` = 0.3995 for the same values).
- Unit tests: `uv run python -m pytest paintbot_pw_lab/tools/tests/test_pw_tune.py` (parsing,
  malformed marks, render byte-identity, grid rounding, perturbation reproducibility, step
  direction and caps).

Not verified: long runs (20+ iterations) and whether SPSA finds real gains on this game; more
than 2 knobs; a tuned file confirmed by hosted A/B.

## Limits and pitfalls

- **Overfits the seed list.** The engine is deterministic, so the objective is a fixed function
  of the values on those seeds; SPSA will find seed-specific quirks. The tuning-seed `final`
  number is selected and biased upward: read `confirm@N`, then A/B hosted.
- **Overfits the opponent.** Tuning vs base.bas finds counters to base.bas. The league field
  is not base.bas; prefer our last accepted version as the opponent, and never treat the
  result as field evidence.
- Integer knobs with small ranges make SPSA coarse (each perturbation is at least one step).
  Keep ranges meaningful and the knob count small (2–6).
- A candidate seat that fails to compile or is disabled plays empty commands and loses, which
  the objective punishes; `bad_candidate_seats` in the log shows it.
- `jev.bas` cannot be tuned locally (no advisor oracle; see pw_local.md).
