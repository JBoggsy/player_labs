# pw_local.py — local batch harness

Part of the [lab tool index](README.md) (dispatcher: `pw.py local`). Runs BASIC policy A against policy B in the paintbot-pw native training library, many matches in
parallel, under the league's rules and glory config. It is a **screening** tool: compile checks,
mechanism checks, and "is the candidate obviously worse than base.bas or our last accepted
version". It is never evidence about the league field (the local field is only the files we seat,
and local seeds are not the league's engine seeds).

Files: [`tools/pw_local.py`](../../tools/pw_local.py), [`tools/build_native.sh`](../../tools/build_native.sh),
tests in [`tools/tests/test_pw_local.py`](../../tools/tests/test_pw_local.py). Skill:
[`paintbot-pw-local`](../../.claude/skills/paintbot-pw-local/SKILL.md).

## Build

```bash
paintbot_pw_lab/tools/build_native.sh                 # default: PW_RELEASE_TAG in tools/release.env
paintbot_pw_lab/tools/build_native.sh coworld-v0.3.78 # another release
```

It runs `build_tools.sh <tag>` first (release worktree + `paintbot-headless`, the parity
reference), then compiles `examples/paintbot/native_env.nim` with
`--app:lib --mm:arc --threads:on -d:pwTraining -d:headless -d:release` into
`tools/bin/<tag>/libpw.dylib`, and writes `tools/bin/<tag>/libpw.build.json`
(`tag`, `commit`, `nim`, `sha256`). About 30 s when the worktree exists. Everything under
`tools/bin/` and `tools/.cache/` is gitignored.

Terrain cache: every worker process (and `compile`) loads the lab's shared terrain file
right after it creates its handle. Without it, each worker spends ~20 s on its first match filling the
0.3.89 terrain table (#183). The first worker to start builds the file once per release (~27 s)
while the others wait on its lock. Match results are identical either way. `PW_TERRAIN_CACHE=0`
turns it off: [pw_release.md § Terrain cache](pw_release.md#terrain-cache).

## Commands

Run from the repo root with `uv run` (stdlib + numpy only).

```bash
# Compile check: the file in all 16 seats for 720 ticks (30 s of play); per-seat errors. ~4 s.
# --json (every subcommand) prints the agent envelope: see Agent contract below.
uv run paintbot_pw_lab/tools/pw_local.py compile CANDIDATE.bas [--ticks 720] [--seed 7] [--json]

# One match. --a-side 0 = A on the even seats (team 0), 1 = odd seats (team 1).
# --record DIR alone records this match (its --record-seeds defaults to --seed).
uv run paintbot_pw_lab/tools/pw_local.py match A.bas B.bas --seed 7 --a-side 0 [--out DIR] [--record DIR]

# Screen: every seed played twice, A on the even seats then on the odd seats.
uv run paintbot_pw_lab/tools/pw_local.py screen A.bas B.bas --seeds 1-28 --out DIR \
    [--workers 14] [--record DIR --record-seeds 3,9]
```

For `screen`, `--record DIR` needs `--record-seeds` (which seeds to replay-record, both sides
each; exit 2 without it, and exit 2 when a listed seed is not in `--seeds`). A typical
record-everything screen is `screen A.bas B.bas --seeds 1-4 --record DIR --record-seeds 1-4`.

Shared options: `--tag` (default: `PW_RELEASE_TAG` in `tools/release.env`; print it with
`uv run python paintbot_pw_lab/tools/pw_release.py`), `--glory JSON` (default the league's
`{"behind_lives":5,"behind_cogs":10}`); `match`/`screen` also take `--max-ticks` (default 14400),
`--workers` (default: all cores), `--out`, `--record`, `--record-seeds`; `compile` takes
`--seed` (default 7) and `--ticks` (default 720). Seeds: `1-28`, `7,8,9`,
`1-10,20` (int32, no duplicates).

`compile` exits 1 if any seat failed to compile (`compile_failed`, with line and column) or was
disabled by a runtime error such as the instruction limit (`disabled`). A runtime error that only
happens later in a match is not caught by the short run; `match`/`screen` report those per match
in `bad_seats`.

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py local compile|match|screen ... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `compile FILE`; `match A B --seed S [--a-side 0\|1]`; `screen A B --seeds LIST`; shared `--tag`, `--glory`, `--max-ticks`, `--workers`, `--out DIR`, `--record DIR`, `--record-seeds` |
| Outputs | `--out DIR`: `matches.jsonl`, `summary.json` (overwritten); `--record DIR`: `NAME.replay` + `NAME.meta.json` per recorded match |
| `--json` result | `compile`: `{build, rules, policy: {path, sha256}, seed, ticks, ok, seats: [{seat, team, set_script, status, message}]}`; `match`/`screen`: the `summary.json` object (build, parity, `summary.{all, a_side_0, a_side_1, seed_balanced}`, recorded, ...) |
| Exit codes | 0 ok; 1 a seat failed to compile or was disabled (one `failures[]` entry per seat, code `compile_failed` or `disabled`), some matches had a bad seat (code `bad_seats`), or a recording's hash differed (code `record_hash_mismatch`); 2 a missing `.bas`, bad `--seeds` or `--glory`, `screen --record` without `--record-seeds`, `--record-seeds` outside the batch (code `usage_error`); 3 the library or `paintbot-headless` is missing, stale, or disagrees with the library on the parity matches (`next[0]` = `paintbot_pw_lab/tools/build_native.sh`) |
| Idempotence / cache | deterministic: the same files, seeds, glory and build give the same rows. Reads (and builds once) the shared [terrain cache](pw_release.md#terrain-cache) |
| Typical next step | `uv run python paintbot_pw_lab/tools/pw.py episodes <record dir> --json` to read a recorded match |

## Guards (the tool refuses to run)

1. **Build identity.** `libpw.build.json` must exist, name the requested tag, name the commit
   the tag resolves to in `tools/.cache/<tag>/` (`$PW_CACHE_DIR/<tag>/` when set; a missing
   worktree is exit 3 with the build command), and match the library's current sha256. The
   library has no call that reports its own build ref, so this sidecar is the check.
2. **Parity with `paintbot-headless`** (`match` and `screen`). Before the batch, two matches
   run through both the library and `tools/bin/<tag>/paintbot-headless` with the same bots,
   seed and glory: the first seed with A on the even seats and the second seed with A on the odd
   seats. Final state hashes must be identical, otherwise the run stops. Because A and B differ,
   this also proves the seat-to-team mapping (seat `s` plays team `s % 2`, `sim.nim` `team`, and
   `--bot FILE:1` flags fill seats in order).
3. `--record` re-runs the chosen seeds (both sides) through `paintbot-headless --record` and
   reports whether each recording's final hash equals the library's row.

## Outputs (`--out DIR`)

`matches.jsonl`, one row per match (written as matches finish; unordered):

| Field | Meaning |
| --- | --- |
| `seed`, `a_side`, `a_seats` | engine seed; team A plays (0/1); `even`/`odd` |
| `tick` | final tick (`pw_results[0]`) |
| `winner`, `winner_policy`, `result_a` | winning team (null on a draw), `A`/`B`/null, `win`/`draw`/`loss` for A |
| `glory0`, `glory1`, `a_glory`, `b_glory` | **settled** glory: the loser and both sides of a draw hold 0 (docs/mechanics.md §1.1) |
| `meter0`, `meter1`, `hearts0`, `hearts1` | heart meter (float32 from the engine) and control hearts held at the end |
| `a_outcome` | A's Elo outcome score, `clamp(0.5 + (a_glory − b_glory)/2000, 0, 1)` (docs/mechanics.md §1.3) |
| `final_hash`, `rules` | engine state hash at the end; rules version the handle played |
| `bad_seats` | seats whose script failed to compile or was disabled at runtime: `seat`, `policy`, `status`, `message`. Empty when all 16 ran to the end |
| `seat_stats` | 16 rows from `pw_seat_stats` (cumulative for the match): `damage_dealt_enemy`, `damage_dealt_team`, `hits_enemy`, `hits_taken`, `kills`, `deaths`, `captures`, `first_friendly_fire_tick` (−1 = never), plus `seat`, `team`, `policy` |
| `seconds` | wall time of that match in its worker |

`summary.json`: `screening_only` (a reminder string), build (tag, commit, nim), `rules` (a list), glory, max ticks, map, both policies' paths and
sha256, seeds, sides, the parity checks, `matches_with_bad_seats`, wall time, workers,
matches/s, `recorded` replays, and `summary`:

- `all`, `a_side_0`, `a_side_1`: `n`, `wins`, `draws`, `losses`, `win_rate`, `mean_outcome`
  (A's mean Elo outcome score), `ci95_low`/`ci95_high` (normal approximation, mean ± 1.96·sd/√n; rough
  below ~20 matches; null with fewer than 2).
- `seed_balanced`: each seed's two sides averaged first, then mean ± CI over seeds. This is the
  number to read: it cancels the side advantage (below). A policy against itself scores exactly
  0.5 per seed here, a free identity check.

`identical_play` (top level of `summary.json` and of the `--json` result): `true` when every
seed was played on both sides and each seed's two final state hashes are equal, so A-vs-B
equals B-vs-A game for game and the two files played move for move identically. `screen` then
prints a WARNING on stderr and adds it to `next`. Seen with `reference/jev.bas` vs
`reference/base.bas`: jev's differences sit behind the advisor oracle, which is off locally,
so the screen's W/D/L says nothing about jev vs base. Always `false` for `match` (one side).

stderr prints one line per match and the parity lines; stdout prints the summary.

## Verified (2026-09-29, coworld-v0.3.78, local Nim 2.2.6, 14-core M-series Mac: 10 P + 4 E)

Re-checked at coworld-v0.3.89 (2026-09-30): `compile` base.bas ok (rules 48); `x = rnd(10)` ok and
`rnd = 3` `compile_failed` (exit 1); `screen` base vs base seeds 1-4 with `--record-seeds 1,2`
(8 matches, parity hashes match, 4 replays that `pw_trace` verifies). Uncached, throughput
dropped (16 matches at 0.51 matches/s versus 0.98 for the 0.3.80 build back to back) because
each worker process fills whole terrain blocks on first touch (#183). With the
[terrain cache](pw_release.md#terrain-cache) (2026-09-30), a 16-match base-vs-base screen
(seeds 1-8) takes 10.6 s end to end (match phase 3.9 matches/s). The run that builds the file
takes 33.0 s, and 50.5 s uncached (0.56 matches/s). The 16 final hashes are the same in all three.
`compile` takes 3.6 s (19.5 s uncached).

Re-checked at coworld-v0.3.79 (2026-09-29): `compile` on base.bas (ok) and on a one-line syntax
error (`compile_failed` per seat, exit 1), `match … --record DIR` (records the match seed, hash
matches the library, `rules` [48]), `screen --seeds 1-4 --record DIR --record-seeds 1-4` (8
replays + sidecars, `identical_play` true for base vs jev), `screen --record` without
`--record-seeds` (exit 2).

- Compile mode catches a syntax error (`compile_failed: line 1, column 1: …`) and an instruction
  limit overrun (`disabled: BASIC instruction limit exceeded`) per seat; base.bas is clean.
- Parity: base.bas vs a one-constant variant, seed 7, both sides: library and headless hashes
  identical (1536731673 A-even, 1693985547 A-odd). The `--record` replay replays hash-exactly
  under `paintbot-headless --replay`.
- Determinism: the same 56-match screen at 14 and 10 workers produced identical per-match hashes
  and summaries.
- Build-identity refusal: a missing library and a tag-mismatched sidecar both stop the run.
- **Throughput:** 56 matches (28 seeds × 2 sides, mean 2,457 ticks) in 36.5 s at 14 workers
  = **1.54 matches/s** (~5,500/hour); 1.42 matches/s at 10 workers; 28 matches (base vs base)
  1.30 matches/s (fewer matches, more tail). Per-match time under load 6.5–8.5 s versus ~5.4 s
  alone. Add ~6 s per run for the parity guard and process start. The plan's 2.5 matches/s
  estimate was too high.
- Unit tests: `uv run python -m pytest paintbot_pw_lab/tools/tests/test_pw_local.py` (seeds,
  seat/team mapping, outcome score, row mapping, draw handling, summary).

Not verified: the parity-mismatch refusal path (no mismatching build to hand); hosted Nim 2.2.10
builds (the per-tick hash check in pw_trace is the guard for hosted replays); maps other than
Heartwick (the tool has no `--map`; the league plays Heartwick).

## Limits and pitfalls

- **Side is a large local effect.** base.bas vs itself, seeds 1–14: the odd-seat team won 10 of
  14 (71%). That is a mirror-match effect of the local screen: the league shows no side advantage (odd seats won 43 of 80 hash-verified 0.3.79 episodes, Wilson 95% 43–64%).
  Always read `seed_balanced`, never one side, and keep both sides in every screen.
- `rules` reads **48**, `pw_rules_latest()` at this tag. Rules 48 changes only FFA-kin fog, so
  the teams game plays rules-47 behaviour, as the league does.
- `jev.bas` has no advisor oracle locally: base.bas vs jev.bas on seed 7 gave the same final hash
  as base.bas vs base.bas. Local screening cannot test the Jev lane.
- One match per process at a time (the interpreter and world use module globals); the pool uses
  `spawn`. Do not run two handles in one process.
- The library cannot record; replays come from `paintbot-headless --record` (feed them to
  `pw_trace`). Recording costs one extra match per recorded (seed, side). Each recording is
  `DIR/<A stem>_vs_<B stem>_s<seed>_a<even|odd>.replay` plus a `.meta.json` sidecar naming the
  file on each seat (A and B are prefixed `A:`/`B:` when both files share a name), so
  pw_episodes, compare.py and `--policy` filters see `local:<file name>` identities.
- Screening results are not field evidence: use hosted A/B (`paintbot-pw-ab` / `coworld-ab`)
  for anything that decides a submission.
- **`compile` answers for the pinned build, not the league's.** Keep the pin on the league's
  build (`pw.py deployed-ref`); when they differ, new or removed host names compile differently.
  At the 0.3.89 pin (2026-09-30) `compile` accepts `x = rnd(10)` and rejects `rnd = 3` ("host
  function cannot be assigned"), as the league does; a name used as a variable fails every hosted
  episode it plays. The same holds for the neural builtin `neuralLogit`; the neural names 0.3.89
  removed (`paintbot_act`, `neuralDecode`, `neuralIssue`, `cmd*`, `neuralGoalX/Z`,
  `neuralAimX/Z`) are free names again ([policy-surface.md](../policy-surface.md)).
