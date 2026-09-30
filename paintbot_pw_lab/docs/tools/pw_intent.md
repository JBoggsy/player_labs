# pw_intent.py: intent telemetry, seat-log recording, belief/intent audit

The replay records what every cog **did**. It cannot record what our policy **meant to do**:
which heart it chose, which seat it was shooting at, why it retreated. Our BASIC prints that
as one short `PWI` line per decision. This tool owns the line format, records local episodes
that keep seat logs, and joins the lines to the hash-checked replay to find where intent and
belief disagree with what happened. Index of all tools: [README.md](README.md).

Files: [`reference/intent_telemetry.bas`](../../reference/intent_telemetry.bas) (the SUB our
policy pastes in), [`tools/pw_intent.py`](../../tools/pw_intent.py), tests in
[`tools/tests/test_pw_intent.py`](../../tools/tests/test_pw_intent.py).

## The line (format v1)

```
PWI v=1 t=2453 m=5 h=4 s=11 r=7 e=3 c=1
```

| Key | Meaning |
| --- | --- |
| `v` | format version, 1. The parser rejects other versions. |
| `t` | `worldTick` when the policy decided = the table tick of the world it decided from. Its command is in the `states` row at `t + 1`. |
| `m` | mode: 0 hold, 1 heart, 2 cover, 3 supply, 4 retreat, 5 fight, 6 chase, 7 defend (`MODE_NAMES`) |
| `h` | chosen control heart index (the `hearts[].idx` of the trace meta), -1 none |
| `s` | target seat as the policy observes it (a disguised body answers to its disguise, see Audit rules), -1 none |
| `r` | reason: 0 none, 1 squad pick, 2 avoided unreachable heart, 3 outnumbered, 4 low hp, 5 wanted supply, 6 heard sound, 7 teammate in the line of fire (`REASON_NAMES`) |
| `e` | enemies the policy counted as seen this tick, in observed identities (a disguised teammate counts as an enemy, a disguised enemy as a teammate) |
| `c` | 1 when printed because m/h/s/r changed, 0 for the periodic line |

All values are integers. The mode and reason tables live in two places, the `.bas` comment
and `pw_intent.py`, and a test fails if the mode tables or the printed keys drift apart.

**Emission.** At most one line per decision: on any change of m/h/s/r, and otherwise every
`intentEvery` ticks (default 24 = 1 s). On by default: globals start at 0, so no setup is
needed. `intentOff = 1` in the policy's one-time setup turns it off.

**Budget** (engine limits per decision: 1,024 print bytes and 128 print events; going over
either disables the seat for the rest of the episode):

| | Per line | Share of the per-decision limit |
| --- | --- | --- |
| Print events | 7 texts + 7 values + 1 newline = 15 | 12% of 128 |
| Bytes, worst case (every value 11 digits) | 28 + 77 + 1 = 106 | 10% of 1,024 |
| Bytes, measured (30,395 lines) | 41 max, about 38 typical | 4% |

Log volume: the seat log is cut at 10 MiB (not fatal). Worst case one line every tick for
14,400 ticks = 1.53 MB. Measured: the largest seat log in 20 local matches was 18 KB.

**Not in the line: instruction headroom.** BASIC has no builtin that reads its own
instruction or work count (checked in `bots.nim` host registrations at `570174a2`, and again at
`118e1619`, 0.3.89, whose only new builtin is `rnd`), so the
policy cannot report budget headroom. Measure peaks locally with `PW_BASIC_PEAKS=1` on a
`paintbot-headless` run instead.

## Where seat logs come from

- **Hosted**: `player-N.log` / `policy_agent_N.log` from `coworld-episode-artifacts`, for
  episodes with our policy. Confirmed 2026-09-30 (seed pilot): our XP episodes return
  `logs/policy_agent_<seat>.log` for our seats ([field.md](../field.md#seeds-what-actually-reaches-the-engine)).
  Individual logs can be missing for minutes after completion; refetch with `--force`. PRINT
  output lands in these files (the engine's print callback writes the seat log,
  `src/polyworld/coworld.nim:151-171` at `118e1619`), but no hosted episode has yet run a policy that prints,
  so no `PWI` line has been seen in a hosted log.
- **Local**: `paintbot-headless` and the native library (`pw_local.py`) **discard** PRINT
  output. `pw_intent.py record` runs the release's hosted handoff (`coworld/paintbot/runtime/host.py`
  with the `-d:coworld` engine that `build_tools.sh` leaves in the worktree), which writes one
  log per seat.

## Commands

Run from the repo root. Every subcommand takes `--json` (one envelope on stdout, text on
stderr; the shared contract in `tools/pw_cli.py`) and `--help` (every flag, with examples).

```bash
# Local episodes with seat logs. A on team a_side (0 = even seats), B on the other; both sides by default.
uv run python paintbot_pw_lab/tools/pw_intent.py record A.bas B.bas --seeds 1-4 --json \
    [--sides 0,1] [--out DIR] [--glory '{"behind_lives":5,"behind_cogs":10}'] [--tag TAG] \
    [--ticks 14400] [--port 8390] [--force]

# Intent lines per seat: counts, malformed lines, VM errors, mode shares, heart switches.
uv run python paintbot_pw_lab/tools/pw_intent.py show ROOT [ROOT ...] --json [--tag TAG] [--refresh]

# Belief/intent audit (dense trace: state_every=1, vis_every=1, about 3 s per episode).
uv run python paintbot_pw_lab/tools/pw_intent.py audit ROOT [ROOT ...] --json [--horizon 72] [--out DIR] [--sparse] [--tag TAG] [--refresh]
```

| | Default output | Re-run |
| --- | --- | --- |
| `record` | `paintbot_pw_lab/analysis/pw_intent/episodes/` (gitignored), one directory per episode | a complete recording with the same inputs is reused (`status: cached`); an incomplete one is re-recorded; one with other settings (ticks, glory, tag) is a usage error unless `--force` |
| `show` | nothing written | trace caches reused |
| `audit` | `paintbot_pw_lab/analysis/pw_intent/audit/<first root name>-<hash of roots, horizon, sparse>/` holding `divergences.csv` and `checks.csv` | same directory, overwritten |

`record` names each episode `<A stem>-<A sha256[:8]>_vs_<B stem>-<B sha256[:8]>_s<seed>_a<side>/`,
so an edited policy never reuses an old recording. The directory holds `NAME.replay`,
`NAME.meta.json` (seat → policy file name, team, seed, glory, max ticks, tag, both files'
sha256; written last, so its presence marks the recording complete), `player-N.log`,
`status.json` (per-seat VM status), `coworld_results.json` and the engine's
`config.json`/`seats.json`/`game.log`. The platform's `results.json` is renamed so
`pw_episodes` reads the directory as a local episode with per-seat policy names (a
`results.json` makes it a hosted episode without names). About 6 s per match, sequential.
A player failure (for example a compile error), an early engine exit or a 10-minute timeout
fails that episode (listed in `failures`, exit 1) and the run goes on to the next.

**`--json` results.** `record`: `{out, episodes: [{name, dir, seed, a_side, status
(recorded|cached|failed), replay, ticks, outcome, disabled_seats}]}`, `outputs` = episode
directories, `counts.recorded` / `counts.cached`; a failed match is a `failures[]` entry with
code `player_failure` (compile error), an early engine exit or a timeout. `show`: `{episodes: [{episode_id, seat_logs, seats: [intent_summary rows]}]}`;
an episode without seat logs is counted in `counts.excluded` / `counts.no_seat_logs`.
`audit`: `{out_dir, totals: {rule: {checked, unchecked, skipped_*, divergent}},
consistency_divergences, episodes_audited}`, `outputs` = the two CSVs; an episode without
intent lines is counted in `counts.excluded` / `counts.no_intent_lines`. `next` suggests the
follow-up command (`record` → `show`/`audit`, `show` → `audit`).

**Exit codes.** 0 ok (divergences are findings, not errors); 1 some episodes failed to record
or load (the rest are written, failures listed); 2 usage error: bad `--seeds`/`--sides`
(lists valid values)/`--glory`/`--horizon`, a missing policy file or root, roots with no
episodes, or a recording with other settings; 3 `pw_trace` or the handoff engine is not
built for the tag (the message and `next` give `paintbot_pw_lab/tools/build_tools.sh [TAG]`).

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py intent record|show|audit ... --json` (or the tool
directly). Shared rules (envelope keys, exit codes, selector checks):
[README.md § Agent contract](README.md#agent-contract), implemented in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `record`: two `.bas` files, `--seeds` (default 1), `--sides` (default 0,1), `--glory` (default the league config), `--out`, `--tag`, `--ticks` (default 14400), `--port` (default 8390), `--force`; `show`: roots, `--tag`, `--refresh`; `audit`: roots, `--horizon` (default 72), `--out`, `--sparse`, `--tag`, `--refresh` |
| Outputs | `record`: local episodes with seat logs under `--out` (default `paintbot_pw_lab/analysis/pw_intent/episodes/`); `audit`: `divergences.csv` + `checks.csv` in `--out DIR` (default `paintbot_pw_lab/analysis/pw_intent/audit/<first root name>-<hash>/`) |
| `--json` result | `record`: `{out, episodes}`; `show`: `{episodes: [{episode_id, seat_logs, seats}]}`, seats = `intent_summary` rows (`intent_lines, bad_lines, vm_errors, last_t, mode_share_<mode>, heart_switches`); `audit`: `{out_dir, totals, consistency_divergences, episodes_audited}` (should be 0 consistency divergences; `totals` holds the deception rules `target_is_ally`, `seen_fooled` and `heart_not_approached`) |
| Exit codes | 0 ok; 1 some episodes failed to load/verify or `record` had a failed match; 2 usage error (unknown selector, roots with no episode); 3 binaries not built (`next[0]` gives the build command) |
| Idempotence / cache | `show` reads the default `pw_episodes` cache, `audit` its dense variant (`@se1-ve1`; `--sparse` uses the default), `--refresh` rebuilds; `record` reuses a complete recording with the same inputs, re-records an incomplete one, and refuses (exit 2) one with other settings unless `--force` |
| Typical next step | a non-zero `consistency_divergences` → fix the policy/telemetry; deception or heart findings → a hypothesis for `paintbot-pw-diagnose` |

**Reproducing the baseline audit.** `reference/wire_intent_base.py` writes an intent-instrumented
copy of `reference/base.bas` (it fails loudly if base.bas anchors change):
`uv run python paintbot_pw_lab/reference/wire_intent_base.py paintbot_pw_lab OUT.bas`.

## Python

```python
import pw_intent
frame = pw_intent.intents(ep)            # one row per PWI line; malformed lines kept with parse_error set
summary = pw_intent.intent_summary(ep)   # one row per seat WITH a log; seats without a log are absent
divergences, checks = pw_intent.audit(ep)
pw_intent.parse_line("PWI v=1 t=0 m=1 h=4 s=-1 r=1 e=0 c=1")
```

`intents` columns: `episode_id, seat, policy_key, t, version, mode, mode_name, heart, target,
reason, reason_name, seen, changed, parse_error, file, line_no`. It reads the `policy_log`
table that `pw_episodes.py` fills (see [tables.md](tables.md)); `pw_episodes` tokenizes the
line and this module types and validates it.

## Audit rules

**Alignment rule.** A line's `t` is the `worldTick` of the world the policy decided from. The
`visibility` and `states` rows at table tick `t` describe that same world: both are stamped
with `w.tick` after step `t` (`pw_trace.nim` `visibilityRow`), and `bots.nim` `decide` then
runs on that world, setting `worldTick = w.tick`, to choose the command for step `t + 1`. So
the audit joins a line to rows at the **same** `t`; the command the line explains is in the
`states` row at `t + 1`. Measured on 6 matches (seeds 3-5, both sides, 8,210 lines): joined
at `t`, the three consistency rules find 0; joined at `t - 1` or `t + 1` they find 4,227 and
1,729 `seen_mismatch` divergences. A misaligned join cannot hide.

**Belief rule.** `s` and `e` are in the policy's **observed identities**, what BASIC's
`visible(i)`/`playerX(i)` answer. A disguised body answers to `body xor 1` (a seat of the
other team; moved on by 2 if that is the observer), and of two visible bodies with one
identity the nearer is reported (`sim.nim` `observedSeat`, `seat_view.nim` `bodyForSeat` since
0.3.89, `bots.nim` before; rules ≥ 27, same answers through 0.3.89). `observed_view()` in `pw_intent.py` reproduces this from the
`visibility` table (which is by body) and the `states` `disguised`/`x`/`z` columns. Disguise
fools teammates too: a disguised teammate looks like an enemy to its own team.

Each line is checked only where the replay samples it needs exist. `checks` counts every
line per rule as `checked`, `unchecked` (sample missing) or a named skip, plus `divergent`.

| Rule | Kind | Divergence when | Reads |
| --- | --- | --- | --- |
| `target_not_visible` | consistency | `s ≥ 0` but no body the seat sees answers to identity `s` at `t`: a stale or wrong belief | `visibility`, `states` at `t` |
| `target_dead` | consistency | `s ≥ 0`, `s` is not in view and seat `s` has hp ≤ 0 at `t` (a body in view is alive by definition) | `states` at `t` |
| `seen_mismatch` | consistency | `e` ≠ the enemy-team identities in the seat's observed view at `t` (only meaningful when `e` counts visible enemies, as in the reference wiring) | `visibility`, `states` at `t` |
| `target_is_ally` | deception | `s` is in view, but the body behind it is a disguised teammate: the policy is aiming at its own side | `visibility`, `states` at `t` |
| `seen_fooled` | deception | the enemy-team identities in view ≠ the enemy bodies in view, because of disguises | `visibility`, `states` at `t` |
| `heart_not_approached` | intent vs outcome | mode 1/2/4/7 with `h ≥ 0`, no later line names another heart within the horizon (else `skipped_superseded`), alive for the whole window (else `skipped_died`), farther than 400 units at `t+1` (else `skipped_arrived`), and the distance to the heart fell by less than 100 units by `t + horizon` (72) | `states`, trace meta hearts |

**Reading the result.** Consistency rules should be 0 (`consistency_divergences` in the
`--json` result). A non-zero count means the policy acted on something it could not see or
miscounted what it saw, or the telemetry wiring is wrong: a bug to look at. Deception rules are
genuine belief-vs-truth differences caused by the game, not by our code; they measure how
often disguises fool the policy. `heart_not_approached` is a heuristic (a path around cover
can move away from the heart for a while).

Thresholds are named constants at the top of `pw_intent.py` (`HEART_APPROACH_TICKS`,
`HEART_APPROACH_MIN_GAIN`, `HEART_ARRIVED`).

### Thresholds (checked 2026-09-30)

League episodes have no `PWI` lines, so the check used a proxy: league cogs whose walk goal is
within 140 of a heart, which is the movement a heart intent asks for. Data: the 80
hash-verified main-league episodes at coworld-v0.3.79 in `episode_data/audit-2026-09-29/`
(34,849 72-tick windows, alive throughout). All three constants are kept. Recheck them when
a real policy of ours emits the line.

| Constant | Value | Evidence and rule |
| --- | --- | --- |
| `HEART_APPROACH_TICKS` | 72 (kept) | A free walk closes up to 2,016 units in 72 ticks (28 units/tick). At this window, walkers' goal gain is clearly bimodal (next row), so a shorter or longer window was not needed. |
| `HEART_APPROACH_MIN_GAIN` | 100 (kept) | Goal gain over 72 ticks for walkers with an unchanged goal ≥ 200 away: 5,190 windows in 0-100 (almost all exactly 0: blocked), then ~200 per 100-unit bin. 100 is the break. |
| `HEART_ARRIVED` | 400 (kept) | Share of heart-goal windows gaining < 100 by starting distance: 72% at 140-200, 58% at 200-300, 38% at 300-400, 26% at 400-500, and 13-18% beyond 500. Inside 400, holding at the heart is the usual behavior, so not approaching is not a divergence. |

## Verified

2026-09-29, coworld-v0.3.78, local Nim 2.2.6:

- The module pasted into a scratch copy of `base.bas` (wiring: m/h/s/r set beside each goal
  rule, one call at the end) compiles and runs in all 16 seats (`pw_local.py compile`,
  2,000 ticks). It played the same match as plain `base.bas` (seed 7: 2,453 ticks, same
  result), as it should, since it issues no commands.
- 22 local matches recorded with `record` (instrumented base vs `base.bas` seeds 1-7 and vs a
  one-constant variant seeds 1-4, both sides): 352 seat-episodes, all `Completed`, no
  `BASIC error:`. 30,395 lines, longest 41 bytes, never two lines on one tick, largest seat
  log 18 KB.

2026-09-29, coworld-v0.3.79 (the disguise-aware audit):

- 6 matches, instrumented `base.bas` vs `base.bas`, seeds 3-5, both sides. The first audit
  (identity = body, no disguise model) found 56 `seen_mismatch`, 30 `target_not_visible` and
  10 `target_dead`. Every one of them had a disguised body in the seat's view. With the
  observed-identity model the three consistency rules find 0 in 8,210 / 4,718 / 4,718 checks,
  and the same lines show up as deception: `seen_fooled` 56, `target_is_ally` 35 (seed 3 side 1:
  16, seed 5 side 1: 19; for example seat 15 targeting identity 10, which was its teammate 11
  in disguise, while seat 10 itself was dead). `heart_not_approached` 10 in 814 checks.
- **Finding about base.bas:** it picks targets from observed identities with `i mod 2 <>
  selfTeam`, so it targets disguised teammates (35 of 4,718 target lines here). Friendly fire
  is on (mechanics.md §5). Whether it actually fires on them and how much damage that costs is
  not measured.
- Commands re-run 2026-09-29 at coworld-v0.3.79: `wire_intent_base.py` → `record` (1 match,
  6.3 s, `status: recorded`), the same `record` again (`cached`), with `--ticks 3000` (exit 2,
  "holds a recording with other settings"), `show` (16 seat logs), `audit` (0 consistency
  divergences, 7 `seen_fooled`), and `show` on a `pw_local` recording (no seat logs:
  `counts.no_seat_logs` 1, exit 0).
- Tests: `uv run python -m pytest paintbot_pw_lab/tools/tests/test_pw_intent.py` (typing,
  rejection of malformed lines, module/parser key and mode-table agreement, malformed lines
  kept, "no log" kept apart from "no lines", `observed_view` against `bodyForSeat`'s rules,
  constructed audit cases for disguise, tick alignment and stale targets, CLI exit codes 2 and 3
  with the envelope).

## Not verified / limits

- No real policy of ours emits the line yet. The verification wiring is
  `reference/wire_intent_base.py` (an instrumented copy of `base.bas`). The mode and reason
  codes follow base.bas's modules and should be revised with the first real policy (keep
  `MODE_NAMES`/`REASON_NAMES` in step).
- No hosted episode has yet carried `PWI` lines (the only uploaded policy, `jb-pw-base:v1`, prints
  nothing); hosted seat-log retrieval itself works (see above).
- `record` has no parity guard against `paintbot-headless`. The replay it writes is
  hash-checked by `pw_trace` when loaded, which is the check that matters for analysis.
- `ffa.bas` and `ffa_blind.bas` (now in `reference/heartland/`) target the Heartland coworld
  and do not compile in the teams game (checked again at coworld-v0.3.79), so `record` fails each
  episode with `player_failure` (exit 1) and names the compile error.
- The observed-identity model is for teams matches (seat parity = team). FFA-kin matches are
  not audited.
- The audit thresholds were checked only on league walking behavior, not on intent lines
  (see Thresholds). `seen_mismatch` means nothing for a policy whose `e` counts something else.
