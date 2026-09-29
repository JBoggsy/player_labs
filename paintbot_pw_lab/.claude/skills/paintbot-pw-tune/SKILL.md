---
name: paintbot-pw-tune
description: "Use when a Paintbot PW BASIC policy has numeric constants worth searching — 'tune these constants', 'what value should kWetCost be', 'search the thresholds', 'optimize the knobs locally'. Marks constants with ' @tune, runs SPSA against a fixed opponent over side-swapped local seeds (tools/pw_tune.py on pw_local; pw.py tune), re-screens on fresh seeds, then hands the result to paintbot-pw-ab. Local screening only, never field evidence. Agent-drivable: `pw.py tune knobs|run|render ... --json`."
---

# Paintbot PW constant tuning

SPSA (simultaneous perturbation) over a few integer constants, scored by the mean ladder Elo
outcome against one opponent file on one seed list, both sides of every seed. It is a cheap
way to propose values. It overfits that opponent and those seeds, so nothing it prints decides
a submission: confirm on fresh seeds, then with a hosted A/B (`paintbot-pw-ab` / `coworld-ab`).
Reference: [docs/tools/pw_tune.md](../../../docs/tools/pw_tune.md). Local harness:
[`paintbot-pw-local`](../paintbot-pw-local/SKILL.md).

## Procedure

Run from the repo root (`personal_labs_paintbot_pw/`). Keep logs and outputs in your scratchpad.

1. **Build once per release** if `uv run python paintbot_pw_lab/tools/pw.py release --require libpw.dylib` exits 3:
   `uv run python paintbot_pw_lab/tools/pw.py build-native` (builds the tag in `tools/release.env`; run
   `uv run python paintbot_pw_lab/tools/pw.py deployed-ref --write` first to keep it on the league's tag, and `uv run python paintbot_pw_lab/tools/pw.py release`
   to print it).

2. **Mark 2–6 knobs** in a copy of the candidate, in the `if started = 0` block, integers only:

   ```basic
   kWetCost = 6 ' @tune 2 12 1
   kRetreatMargin = 1 ' @tune 0 4
   ```

   To tune a literal buried in logic, lift it into a named constant first (same value, so the
   start file plays identically). Check the marks and that it compiles:

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py tune knobs CAND.bas --json
   uv run python paintbot_pw_lab/tools/pw.py local compile CAND.bas --json
   ```

3. **Pick the opponent**: our last accepted version (WORKING_CONTEXT.md), or base.bas until we
   have one. Tuning against base.bas finds counters to base.bas.

4. **Run** (resumable; rerun the same command after an interruption, or with a larger
   `--iterations` to extend). ~22 s per iteration at 8 seeds on 14 cores:

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py tune run CAND.bas OPPONENT.bas --seeds 1-8 --iterations 20 \
       --log <scratch>/tune.jsonl --confirm-seeds 101-124 --out <scratch>/tuned.bas --json
   ```

5. **Read the report.** The `initial` vs `final` numbers on the tuning seeds are biased upward
   (the search selected them). The decision number is `confirm seeds final` vs
   `confirm seeds initial` with its seed-balanced CI. Also check the warning line for candidate
   seats that failed to compile or were disabled.

6. **Re-screen** the tuned file on a third, larger seed list and against a second opponent
   (base.bas and our last version) with `pw.py local screen`. Keep only values that hold up.

7. **Confirm hosted** with `paintbot-pw-ab` (tuned vs untuned, same field, same window). Report:
   "pw_tune: kWetCost 6 -> 4, confirm seeds 0.55 [0.49, 0.61] vs 0.50 (24 seeds, vs base.bas,
   <tag from `pw.py release`>), screening only; hosted A/B: ...".

## Pitfalls

- **Screening only.** Never quote a tuning or confirm number as field performance or use it
  to decide a submission.
- **Keep both sides** (the tool always plays both): the odd-seat side wins far more locally.
- The engine is deterministic: the same values on the same seeds give the same score. Noise
  comes only from the seed list, so more seeds, not repeated runs, reduce it.
- Don't change the file, opponent, seeds or SPSA settings mid-run; the tool refuses a log
  written with different ones. Start a new `--log`.
- Small integer ranges make steps coarse; SPSA perturbs every knob by at least one grid step.
- A knob set outside the `started = 0` block is re-assigned every decision; that is fine for a
  constant, but keep it in the init block so the meaning is clear.
- `jev.bas` has no advisor oracle locally: do not tune the Jev lane here.
- `render --log LOG --out X.bas` rebuilds the tuned file from a log; `--set NAME=V` pins values
  by hand. The `@tune` comments can stay in the uploaded file.

## Autonomous use

- **Preconditions:** `uv run python paintbot_pw_lab/tools/pw.py release --require libpw.dylib paintbot-headless --json` exits 0; the
  candidate has 2–6 valid `' @tune` marks (`tune knobs CAND.bas --json` lists them in
  `result.knobs`) and compiles (`local compile --json` exits 0).
- **Command:** `uv run python paintbot_pw_lab/tools/pw.py tune run CAND.bas OPP.bas --seeds 1-8 --iterations 20 --log <scratch>/tune.jsonl
  --confirm-seeds 101-124 --out <scratch>/tuned.bas --json`. The log is resumable: rerunning the
  same command continues it, a larger `--iterations` extends it.
- **Reading the envelope:** `result.confirm.final` vs `result.confirm.initial` (seed-balanced outcome
  and CI on the fresh seeds) is the decision number; `result.final` on the tuning seeds is biased
  upward. `result.guardrail` repeats that this is screening only. `failures[]` names candidate
  seats that failed to compile or were disabled.
- **Exit codes:** 0 use it. 1 candidate seats failed (fix the file first). 2 bad marks, a missing
  file, bad seeds, or a log written with different settings (start a new `--log`). 3 the library is
  missing or stale: run `next[0]`.
- **Human gates:** none locally. The hosted confirmation (step 7) creates experience requests:
  within lab authorization but it **costs XP credits**. Submitting the tuned version to the league is
  James's gate.
