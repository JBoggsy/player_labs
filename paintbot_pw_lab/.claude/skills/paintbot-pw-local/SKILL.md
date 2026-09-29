---
name: paintbot-pw-local
description: "Use when a Paintbot PW BASIC candidate needs a fast local check before or alongside hosted evaluation — 'does it compile', 'compile/screen this locally', 'is it obviously worse than base', 'run it against our last version'. Runs tools/pw_local.py (pw.py local) on the native library under the league glory config with side swaps. Screening only, never field evidence. Agent-drivable: `pw.py local compile|match|screen ... --json`."
---

# Paintbot PW local screening

Local matches answer two narrow questions fast: **does the candidate run cleanly** in all 16
seats, and **is it clearly worse than base.bas or our last accepted version** head-to-head. They
say nothing about the league field. Hosted A/B (`coworld-ab`, the lab's `paintbot-pw-ab`) decides.
Per the lab's speed rule this is not a pre-upload gate. Use it when it is the fastest answer to a
question you already have. Reference: [docs/tools/pw_local.md](../../../docs/tools/pw_local.md).

## Procedure

Run from the repo root (`personal_labs_paintbot_pw/`).

1. **Build once per release** (about 30 s if the worktree exists; skip if
   `uv run python paintbot_pw_lab/tools/pw.py release --require libpw.dylib` exits 0). The tag is
   the one in `paintbot_pw_lab/tools/release.env`; `deployed-ref --write` keeps it on the
   league's tag (exit 1 = it just moved, so rebuild):

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py deployed-ref --write
   uv run python paintbot_pw_lab/tools/pw.py build-native          # default: PW_RELEASE_TAG in tools/release.env
   ```

2. **Compile check** (~4 s). Exit 1 means a seat failed to compile or was disabled at runtime;
   the output gives seat, team and error text (with `--json`: one `failures[]` entry per bad seat).

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py local compile CANDIDATE.bas --json
   ```

3. **Screen vs base.bas**, both sides of every seed (~40 s for 28 seeds on 14 cores):

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py local screen CANDIDATE.bas paintbot_pw_lab/reference/base.bas \
       --seeds 1-28 --out <scratch>/screen_vs_base --json
   ```

4. **Screen vs our last accepted version** (its `.bas`, per WORKING_CONTEXT.md; until we have
   one, base.bas is both baselines):

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py local screen CANDIDATE.bas LAST_ACCEPTED.bas \
       --seeds 1-28 --out <scratch>/screen_vs_last --json
   ```

5. **Read the summary**: `seed-balanced` mean A outcome (the ladder's Elo outcome, 0.5 = even) with
   its 95% CI, W/D/L per side, and any `bad_seats` warning (in `--json`: `result.summary.seed_balanced`,
   `result.summary.a_side_0/1`, and a `bad_seats` failure with exit 1). Report it as
   "local screen vs X: seed-balanced outcome 0.61 [0.53, 0.68], 28 seeds, <tag from `pw.py release`>,
   screening only".

6. **Look at a match** when a number surprises you: add `--record <dir> --record-seeds 9` to
   re-run that seed through `paintbot-headless --record` (both sides), then read it like any
   episode: `uv run python paintbot_pw_lab/tools/pw.py episodes <dir> --json` and the `paintbot-pw-replay` skill.

## Pitfalls

- **Local results are screening only, never field evidence.** Do not quote them as a win rate
  against the league, and do not use them to decide a submission.
- **Always keep both sides and read `seed_balanced`.** Base vs itself: the odd-seat team won 10
  of 14 seeds. A one-sided screen measures the side, not the policy.
- The tool refuses to run when the library's `libpw.build.json` does not match the requested tag,
  or when the two parity matches disagree with `paintbot-headless` (exit 3, fix in `next[]`).
  Rebuild with `pw.py build-native <tag>`; do not work around it.
- `jev.bas` has no advisor oracle locally and played hash-identically to base.bas: local
  screening cannot evaluate the Jev lane.
- The short compile run misses errors that only occur later in a match; check `bad_seats` in the
  screen output (a count is printed when any exist).
- Seeds here are not league seeds, and the default map (Heartwick) and glory
  `{"behind_lives":5,"behind_cogs":10}` match the league as of 2026-09-29. Recheck the glory
  config against a fresh league episode after a release (`--glory` overrides it).
- Keep output directories in your scratchpad, not the repo.

## Autonomous use

- **Preconditions:** `uv run python paintbot_pw_lab/tools/pw.py release --require libpw.dylib paintbot-headless --json` exits 0
  (else run `next[]`, i.e. `pw.py build-native`); the candidate and opponent `.bas` files exist.
- **Commands:** `uv run python paintbot_pw_lab/tools/pw.py local compile FILE --json`, then `uv run python paintbot_pw_lab/tools/pw.py local screen A B --seeds 1-28 --out
  <scratch>/screen --json`. The screen is deterministic: the same files, seeds and build give the
  same numbers, so rerun only when a file changed.
- **Reading the envelope:** `result.summary.seed_balanced` (mean A outcome and 95% CI) is the
  number; `result.parity` shows the library matched `paintbot-headless`; `failures[]` lists bad seats
  and recordings whose hash differed.
- **Exit codes:** 0 use it. 1 a seat failed to compile or was disabled (compile), or some matches had
  a bad seat or a recording differed (screen): fix the policy before reading the number. 2 a missing
  `.bas`, bad `--seeds`/`--glory`, or `--record-seeds` outside the batch: fix the arguments. 3 the
  library is missing, stale or disagrees with `paintbot-headless`: run `next[0]` and rerun.
- **Human gates:** none; nothing leaves the machine. A local result never decides an upload or a
  submission (league submission stays James's gate).
