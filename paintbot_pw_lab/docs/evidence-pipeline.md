# Paintbot PW evidence pipeline

> **Currency.** Investigated 2026-09-28 against paintbot-pw tag `coworld-v0.3.65` =
> `7b2b19f5abd5a13b4c691a3435fab31ca88df59b` (rules 45) with Nim 2.2.6 on arm64 macOS,
> `coworld` CLI 0.1.54 (latest on the index) and `softmax-cli` 0.26.38. The sample
> episodes were recorded by coworld **0.3.64** (`ed2a395`, rules 44): the main league's
> newest completed round (2237, 21:44Z) had not moved to 0.3.65 yet.
> **Re-verify when** a new `coworld-vX` tag appears: the accepted rules list in
> `game.nim` `loadRecording`, and a hash-checked re-simulation of one fresh league replay.
>
> **Update 2026-09-29 (0.3.78).** The leagues now run tag `coworld-v0.3.78` = `570174a2`
> (recordings stamped rules 48; the teams game plays rules 47). Line references below were
> moved to `570174a2`, and the facts that changed are marked. What changed for this pipeline:
> the seat count is per match (0.3.75, rules 46), so a replay's frames hold one command per
> seat and its `Recording` carries `seats`; the glory config gained `behind_cogs` /
> `behind_cogs_seconds` (rules 47) and the league variants set `behind_cogs: 10` (0.3.77);
> the appendix probe no longer compiles (see the appendix). The findings measured on the
> rules-44 samples (sections 2, 4.1, 5) were not re-run at 0.3.78 except where marked. Checked
> with the 0.3.78 build: the three rules-44 samples still re-simulate with no hash mismatch
> (tick counts equal `results.json`; `ereq_e97afe98` ends on the same hash 3587158643 as in
> section 3.3), and a local rules-48 recording with the league glory config replays clean.

Line references are to `570174a2` in `~/coding/coworlds/paintbot-pw` (abbreviated
`pw:`) unless marked `7b2b19f5`. **Verified** means exercised on the sample episodes or a local run in this
investigation; **inferred** means read from source but not exercised.

This is *not* the Season 1/2 Paintbot in `paintbot_lab/`. Different engine (Polyworld
Nim), different replay container, different tools. Do not reuse `paintbot_lab/tools/`.

## 1. Summary

| Question | Answer |
| --- | --- |
| Replay format | Polyworld `POLYWORLDREPLAY` tape: every seat's command every tick plus a per-tick state hash. **Verified.** |
| Re-simulation constraint | **Unlike Gods of the Arena, one build replays many versions.** The header's `gameVersion` is the rules number and the sim keeps every old rules path. The `7b2b19f5` build (rules 45) re-simulated three rules-44 league replays with **zero hash mismatches**; forcing the same replays to play under rules 45 diverged at ticks 26–269. **Verified.** |
| Per-seat stats | Not provided by the repo's tools for teams replays (`replay_stats.nim` is per-team and does not check hashes). A ~70-line probe against the engine's own `SeatStats` telemetry gave kills, deaths, damage, weapon kills, water/high-ground hits, pickups, glory hearts, shots, time alive and time wading per seat, hash-checked. **Verified at 0.3.65; superseded by `tools/pw_trace`** (plan T1), because the probe does not compile from 0.3.75 on (appendix). |
| Local runs | `coworld/paintbot/local.py` (the exact hosted handoff, per-seat logs) and the native headless binary (`--bot FILE:N --record`) both work, ~4 s for a 2,100-tick match, with the same final hash for the same seed. Only `paintbot-headless` can set the league's glory config (`--glory:<json>`). **Verified** (0.3.65; the headless path re-checked at 0.3.78). |
| Seat logs | Returned only for episodes you have a policy in. League episodes without one of our policies return 403. **Verified.** |

## 2. Artifact inventory (verified)

Sample: main league `league_b9458ff8-…`, Competition division, round 2237
(`round_f5c18f3c-8834-47e7-a542-f2511c083578`, 12 episodes), variant
"Two policy teams", `coworld_id` `cow_35f32fb7-…` (0.3.64). Downloaded with
`fetch_artifacts.py --ereq …` into `paintbot_pw_lab/episode_data/`.

| Episode | Even seats (Ember) | Odd seats (Azure) | Ticks | Result |
| --- | --- | --- | --- | --- |
| `ereq_e97afe98-a60d-…` | relh-paintbot-pw v1 | daveey-pw-neural v23 | 2219 | Azure 548 |
| `ereq_5092af64-d37e-…` | richard-paintbot-pw | daveey-pw-neural v23 | 1649 | Azure 542 |
| `ereq_e7d3e242-4d4e-…` | aaron-paintbot-pw | aaron-coplay-coach | 4108 | Azure 639 |

All three ended by elimination at 11–28% of the 14,400-tick limit, which fits the guide's
"elimination race" observation (`pw:coworld/paintbot/guide.md:201-205`).

### 2.1 `episode.json` (Observatory row)

- `participants[]` with explicit `position` 0–15, `policy_name`, `version`,
  `player_name`, `is_filler`. Each policy fills 8 seats. The first seat of each is
  `is_filler: false` and the other 7 are fillers. Seat parity is the team: even = Red/Ember,
  odd = Blue/Azure.
- `coworld_version`, `coworld_id`, `variant_name`, `job_id`, `job_index`.
- `game_config`: `seed: 2026`, `max_ticks: 14400`, `glory: {"behind_lives": 5}`
  (the league pays **5** glory per trailing life, not the default 1), 16 `slots` with
  teams, placeholder `players` names. From 0.3.77 the manifest's variants set
  `glory: {"behind_lives": 5, "behind_cogs": 10}`; not yet seen in a live episode. No `map` or `vision`, so the matches use the Heartwick island with per-cog vision.
- `participant_scores[]` by position, and `scores[]` deduplicated by policy. Join by
  position, never by array order.
- `replay_url`: public S3 `…/replays/<job_id>.replay`, **gzip** (`1f 8b`).

### 2.2 `results.json`

`{"scores": [16 floats], "ticks", "seed", "outcome", "banked_gold": [], "returned": []}`.

- `scores[i]` is the team's glory, repeated on every seat of that team. The loser is
  zeroed at the end (`pw:examples/paintbot/sim.nim:1009` `settleGlory`).
- `seed` is the **engine seed**, not `game_config.seed`. It equals the replay's seed.
  The three samples were 1327528888/…889/…890 for `job_index` 9/10/11, so the runner
  appears to derive it per job (inferred).
- `outcome`: `"0"`/`"1"` = winning side, `"time_limit"` when there is no winner, `"ended"` in FFA
  (`pw:examples/paintbot/game.nim:541-543`). A local 1,200-tick time-limit run reported
  `"0"`: at the limit the glory leader is the winner (verified locally; the settle path
  itself was not traced).
- `banked_gold` / `returned` are empty, vestigial fields of the shared results type
  (`pw:src/polyworld/coworld.nim:53-55`).

### 2.3 Replay

- Container (`pw:src/polyworld/tapes.nim:8-9`): `POLYWORLDREPLAY`, u16 file format 1,
  u16 **gameVersion = rules number** (44 in the samples; 1000+rules for FFA-kin),
  u16 name length, `paintbot_pw`, then a Flatty `Recording`
  (`pw:examples/paintbot/game.nim:94-105`): `seed`, `frames` (one per tick: one
  `Command{walk, shoot, direct, goal, aim, chargeGrenade, sneak}` per seat + `hash u32`),
  `names`, `communications` (every `shout` with tick, slot and **text**), `endTick`,
  `map`, `vision`, `glory` config, and from rules 46 `seats`. Rules 43–45 store exactly 16
  commands and names in fixed arrays (`Recording43`); rules 46 stores sequences plus the seat
  count with the 5-key glory config (`Recording46`); rules 47–48 add the two behind-in-cogs
  glory keys (`pw:game.nim:61-105`, loader `:322-396`). The loader checks every frame has
  `seats` commands.
- Unlike GotA, this is **every seat's executed command every tick**, not a request log
  (`pw:game.nim:540`, ~389 bytes per tick at 16 seats; 0.64–0.86 MB per league match uncompressed).
- `names[i]` holds the **player display name**, deduplicated with " (2)"…" (8)". It matched
  `participants[i].player_name` for all 48 seats. Use `episode.json` as the join key and
  the names only as a cross-check: one owner can run two players (Alpha and Beta are both daveey's).
- Where it comes from: the fetcher's `/artifacts/replay` route returned the **decompressed**
  tape. It saved identical bytes as both `replay.json` and `replay.json.z`, and neither
  is JSON or zlib (the root `TODO.md` item). The public `replay_url` is gzip, and
  `gunzip -c` of it is byte-identical to the fetched file.
- Transient gap: the first fetch of `ereq_e7d3e242` returned `results: unavailable`,
  `replay: unavailable` about 12 minutes after completion. A `--force` refetch minutes later got
  both. Treat a missing artifact as "retry", not "absent".

### 2.4 Logs

- **Per-seat logs** (`coworld episode-logs <ereq>`, or the fetcher's policy-logs routes):
  **403 for league episodes we have no policy in.** The Softmax account has no
  membership in this league yet. `--elevated` is not for lab use. Inferred: our own seats'
  logs come back in xp-requests and league rounds we play in (the guide's workflow,
  `pw:guide.md:198-200`).
- Log content, verified locally: `Player slot N started.`, then BASIC `print` output
  verbatim, one line per print, then `Player slot N completed.`. Advisor oracle
  journal lines and neural telemetry also go here (`pw:examples/paintbot/bots.nim:387,413`).
- **Runtime BASIC errors** (instruction limit and so on) disable that seat for the rest of the
  match: it sends empty commands, the error goes to its log, and `status.json` records
  `exit_code 1, reason "BASIC VM disabled"` (`pw:bots.nim:502-504`,
  `pw:src/polyworld/coworld.nim:198-208`). The match continues.
- **Compile errors fail the whole episode.** Verified locally: a seat with a syntax error
  wrote `failure.json` `{"message":"BASIC compilation failed for player slot 1",
  "failed_policy_index":1}` and no `results.json`. The engine parks in
  `waitForCollection` (`pw:coworld.nim:214-233`), so `local.py` hangs until its
  10-minute deadline. Compare **staging** failures (a WASM upload, a hash mismatch),
  which forfeit only that seat and put an idle stub in its place
  (`pw:coworld/paintbot/runtime/host.py:111-124`). A hosted compile failure shows up
  as failed episodes; treat that as the signal (see the lab AGENTS rules).
- Combined game log: "optional, unavailable" for these episodes. The local `game.log`
  holds `ticks=… captures=[…] hash=…` and, with `PW_BASIC_PEAKS=1`, per-seat peak
  instructions, work units, strings and neural ops (`pw:game.nim:550-557`).

## 3. Re-simulation

### 3.1 Why one build replays many versions (verified)

`loadRecording` reads the header version, sets `replayRulesVersion` and
`visionRulesVersion` to it, and decodes the matching historical layout
(`pw:game.nim:322-396`; rules 43–45 share a layout, `:363`; rules 47–48 share one, `:379`).
The sim branches on those variables throughout (for example `stateHash` `pw:sim.nim:1034`,
glory `pw:sim.nim:916-1013`, lives `pw:mechanics.nim:138,436`). The guide states the policy:
"Earlier replay versions retain their original rules and hashes" (`pw:guide.md:142-148`).

Evidence:

- The `7b2b19f5` build (default rules 45) re-simulated all three rules-44 league replays
  with no mismatch on any of 1,649 + 4,108 + 2,219 ticks, and the final glory equalled
  `results.json` in each.
- Negative control: patching byte 17 from 44 to 45 (same layout, rules-45 routing)
  diverged at tick 30, 269 and 26, and `paintbot-headless --replay` raised
  `Replay hash mismatch at 26`. The hash check does catch a rules mismatch.

Consequence: build the **newest** deployed tag, not the recording commit. That is the
opposite of GotA. The guard is still the per-tick hash: if a future PR changes behaviour
without bumping the rules number, old replays will diverge. Keep the check in every tool.
Map deployed version to source with the tag `coworld-v<coworld_version>`. `coworld show
<cow_id> --json` gives `source_url: https://github.com/Metta-AI/paintbot-pw` with **no
commit**, unlike polyworld's GotA manifest, so GotA's `deployed_ref.py` does not carry over.

### 3.2 Build (verified, about 1 minute cold, no credentials)

```sh
paintbot_pw_lab/tools/build_tools.sh                   # the tag in tools/release.env (deployed_ref.py --write moves it)
source paintbot_pw_lab/tools/release.env; B=paintbot_pw_lab/tools/bin/$PW_RELEASE_TAG   # paintbot-headless, replay_stats
```

The script fetches tags in `~/coding/coworlds/paintbot-pw` (cloning it if missing), adds a
detached worktree at `paintbot_pw_lab/tools/.cache/<tag>/` (never changing the clone's own
checkout), pins dependencies with `coworld/tools/sync_dependencies.py` into the worktree's
`tmp/coworld/deps` (read through `POLYWORLD_DEPS`, `config.nims:4-17`), and builds
`paintbot-headless` (`-d:headless`), `replay_stats`, and the `-d:coworld` engine
`tmp/paintbot-coworld` that `local.py` needs. Both output directories are gitignored.

The hosted image builds with Nim 2.2.10 on linux/amd64 (`pw:coworld/paintbot/Dockerfile`;
CI pinned 2.2.10 too from 0.3.69). Nim 2.2.6 on arm64 reproduced every hosted hash at 0.3.65,
so no Docker is needed (3 rules-44 replays; not yet re-checked on a hosted rules-47/48
replay; the hash check remains the guard). Warnings are only style (`Spacing`).

### 3.3 Commands that work (verified)

```sh
# Hash-checked validation: prints ticks, captures, final hash; raises on any mismatch.
$B/paintbot-headless --replay episode_data/<dir>/replay.json
#   ticks=2219 captures=[3, 2] hash=3587158643

# The repo's per-team summary (NOT hash-checked; see 4.1).
$B/replay_stats episode_data/<dir>/replay.json [more ...]
#   replay.json: 2219 of 14400 ticks (15% of the limit), winner Azure
#     Ember/even  glory 0  lives 0  standing 0  captures 3  heart-ticks 6272 ahead 1766 friendly-fire 0 (+0) quiet-supplies 20 (+875)
#     Azure/odd   glory 548 lives 15 standing 8 captures 2  heart-ticks 2723 ahead 0    friendly-fire 0 (+0) quiet-supplies 3 (+40)

# From a public replay_url instead of the fetcher:
curl -sS "$REPLAY_URL" | gunzip -c > match.raw
```

Each takes under 1 s per league match.

## 4. What the repo's tools do

### 4.1 `examples/paintbot/replay_stats.nim` (verified)

Per **team** only (`pw:replay_stats.nim:32-67`): glory, lives left, cogs standing,
"captures", heart-ticks, ticks ahead on heart count, and friendly-fire / "quiet-supplies"
glory. It handles FFA-kin replays per seat (`:20-30`). Three pitfalls:

1. **No hash check.** It calls `w.step` directly (`:41-42`) and never compares
   `f.hash`. A replay from a build that does not reproduce it would give plausible,
   wrong numbers. Run `paintbot-headless --replay` first, or use a checked tool. The
   guide's "60 hosted games … state hash checked every tick" study (`pw:guide.md:252-256`)
   used a tool that is not in the repo.
2. **"captures" is hearts held at the end, not captures made.** `w.captures` is
   recounted from heart owners every tick (`pw:mechanics.nim:350-351`) and starts at
   `[1,1]` (`:124`). Cumulative per-seat flips are `cogs[i].captures`
   (`pw:mechanics.nim:288,346`).
3. **"quiet-supplies" is every award except friendly fire** (`:55-56`). Broken down by
   `GloryKind` (`pw:sim.nim:142-143`; `gloryBehindCogs` added at rules 47), the samples' loser "+875" was 835 behind-lives + 40
   glory-heart awards, with no quiet-supplies at all. Under the league's `behind_lives: 5`,
   behind-lives dominates the losing side's pre-settle glory.

### 4.2 `examples/paintbot/analysis.nim` (read, not run standalone)

`indexReplay` (`pw:analysis.nim:169`) is the viewer's indexer. It works over the
global `world`/`recording`, advances with `advance()`, which **is** hash-checked
(`pw:game.nim:511-518`), and emits per-seat `CombatStats{shots, hits}` per tick plus a
`Moment` event feed: tag, hit, down, heal, grenade/spray/shield pickup, spray,
grenade throw and blast, territory flip, heart drop/return (`:100-166`; the file was
refactored between 0.3.65 and 0.3.78 and not re-read in depth). This is the
right base for timelines and events, but it keeps a full per-tick array and 240-tick
checkpoints in memory, which is more than batch stats need.

### 4.3 `examples/paintbot/inspect_replay.nim`

A 13-line debug stub: per-seat move and shot counts and final positions. No hash check.

### 4.4 Engine telemetry: `SeatStats` under `-d:pwTraining` (verified)

`sim.nim:250-263` defines per-seat `SeatStats`: damage dealt to enemies and to teammates,
enemy hits, hits taken, kills, deaths, first friendly-fire tick, spray damage and kills,
gun/grenade/spray kills, and hits from and to water, high ground and trenches.
`mechanics.nim:380-417` fills it inside `damage()` whenever `combatTelemetry` is set.
It is outside `World` and the hash. The native training library sets it per step
(`pw:native_env.nim:906-910`). A replay tool can point it at a local array while it steps,
which is what the probe in the appendix did. `CombatTelemetry` is now
`array[LegacySeats, SeatStats]` (16 entries, `pw:sim.nim:264`), so it only covers 16-seat
matches, which every paintbot-pw match is.

`tools/kin_replay_counters.nim` + `tools/kin_replay_stats.py` are the repo's own
hash-checked, native-ABI re-simulators, but **FFA-kin only**, and on the Heartwick island only
(`pw:tools/kin_replay_counters.nim:1-22`). They serve the Heartland league, not the main
league.

## 5. Per-seat metrics (verified unless marked)

From one hash-checked pass of the probe (appendix), per seat:

| Metric | Source | Note |
| --- | --- | --- |
| kills, deaths | `SeatStats.kills/deaths` | Kills count enemy victims only. `cogs[i].tags` also counts teammate kills (the samples: tags 16 vs kills 14 on one side). |
| enemy hits / hits taken / damage dealt (enemy, team) | `SeatStats` | Damage is health removed after armor. |
| gun / grenade / spray kills | `SeatStats` | Every sample kill was a gun kill. |
| hits from/to water, from high ground, from trench | `SeatStats` | Hit-location mix, for the guide's lake finding. |
| first friendly-fire tick | `SeatStats` | -1 = never. |
| lives left, alive at end | `equipment[i].lives`, `cogs[i].hp` | 4 lives per seat, 32 per team (`pw:mechanics.nim:138`). |
| downs, first-down tick | `hp` 1→0 transitions | Downs equalled deaths on every sample seat. |
| alive ticks, wet ticks (wading) | per tick, `neural_contract.inWater` (`:283`) | The same predicate the speed penalty uses. |
| shots | `observeShot` hook (`pw:sim.nim:1077`) | |
| heart captures credited | `cogs[i].captures` | Team sums differ by 0–2 from the end-held count, as expected. |
| grenade / spray / shield pickups | equipment transitions | Same rule as `analysis.nim`'s pickup moments. Medkit pickups are not counted (they could come from `hp` rises). |
| glory hearts taken | `w.gloryPickups[].seat` | Deduplicated, because it is a rolling window. |
| shouts, and their text | `recording.communications` | Opponents' shout text is in the replay. |
| glory by kind, per team | `w.gloryEvents` | Glory is team-level. There is no per-seat glory beyond glory hearts. |

**Not in the replay:** BASIC `print` output, the advisor oracle's questions and answers, and why a
seat was disabled. Those live only in seat logs, which we can only get for our own seats.
Per-seat commands are in the replay, so "did seat i try X at tick t" is answerable.

## 6. Local runs (verified)

Hosted path. It builds the `-d:coworld` engine into the worktree's `tmp/paintbot-coworld`
first, runs `runtime/host.py` with stdlib Python only, and writes `results.json`, `replay.bin`,
`player-N.log`, `status.json` and `game.log`:

```sh
source paintbot_pw_lab/tools/release.env; cd paintbot_pw_lab/tools/.cache/$PW_RELEASE_TAG   # after build_tools.sh
PW_BASIC_PEAKS=1 python3 coworld/paintbot/local.py --output /tmp/pw-run1 --ticks 2400 \
    --policy path/to/base.bas                      # one file = all 16 seats
# or exactly 16 --policy flags, in seat order (even = Red, odd = Blue)
```

At 0.3.65: `base.bas` ×16, seed 2026, 2,400 ticks: 4.5 s wall, ended by elimination at tick
2123, `hash=1400215181`. Options: `--seed`, `--mode ffa_kin`, `--kin-layout`, and from 0.3.75
`--seats N` (2-256) and `--map` (`pw:coworld/paintbot/local.py:11-24`). It still **cannot**
set `vision` or `glory`, so `local.py` runs use the engine defaults (`behind_lives` 1,
`behind_cogs` 1) where the league uses 5 and 10 (checked at 0.3.78: `awardBehindCogs()` reads
1 in a `local.py` run).

Native path (no host, no seat logs). **BASIC `print` output is discarded here**, not written
to stdout: the headless build gives the VM no print handler (`pw:bots.nim:421`,
`pw:src/polyworld/basic.nim:2696-2711`; checked at 0.3.78). Use `local.py` when you need a
seat's prints. The headless binary does take the league's match config on the command line:
`--glory:<json>`, `--map:<name>`, `--vision:team` and (0.3.75+) `--mode:ffa_kin`,
`--kin-layout:<name>` (`pw:game.nim:450-471`); `--glory` already existed at 0.3.65.

```sh
paintbot-headless --bot a.bas:16 --seed 2026 --ticks 2400 \
    '--glory:{"behind_lives":5,"behind_cogs":10}' --record out.replay
```

At 0.3.65 the same seed and file gave the **identical** hash 1400215181 on both paths, so
they are equivalent. At 0.3.78 with the league glory config: `base.bas` ×16, seed 2026,
2,400 ticks ended by elimination at tick 2123, `hash=276551954`, 4.7 s; the recording is
stamped rules 48 and `paintbot-headless --replay` reproduced it. `--bot FILE:N` fills seats
**in order**, and the seat count is the sum of the `N`s (`pw:bots.nim:388-395`,
`pw:game.nim:472-476`):
`--bot a.bas:8 --bot b.bas:8` puts `a` on seats 0–7, which mixes both teams. For A vs B,
pass 16 alternating `--bot` flags or use `local.py`.

Local runs are for mechanism checks and compile checks. The local field is not the league field.

## 7. The guide's comparison workflow (`pw:guide.md:151-210`)

- It covers xp-requests over a pinned coworld with all 16 seats in the roster. `policy_ref` must be bare
  `name:vN` or a UUID, and `variant_id` goes in `target` **or** at the top level, not both.
  Advised builds need `episode_player_llm_spend_limit_usd`, or they silently play the baseline.
- Statistics: the loser's glory is zeroed, so the score gap is one bit. Use **mean
  winning glory** against an opponent the arm almost always beats, and **win rate** between close
  arms. Swap sides in equal halves (noise alone produced 35/60 Red). About 250 episodes are
  needed to tell 0.62 from 0.50. Fix the stopping rule before looking at results.
- Check seat logs for failures and peaks before trusting a score. Read the replay and derive
  sides from `policy_version_ids` zipped with slots. Never assume even seats are "us".
- `coworld/paintbot/tools/jev_experiment.py` / `jev_results.py` do this for the Jev
  baseline's switches only (not read in depth here).

## 8. The tools built on this pipeline

The recommendations that used to be here are implemented (tooling plan T1-T15). The tools and
their agent contract are indexed in [docs/tools/README.md](tools/README.md): `pw_trace`
(hash-checked expansion, replacing the appendix probe), `pw_episodes` (reader, signed cache,
Parquet tables, DuckDB), `pw_metrics`, `compare` (coworld-ab adapter), `features`/`miner_rows`
(miner adapter), `pw_local`, `pw_viz`, `pw_match_report`, `pw_fights`, `pw_flags`, `pw_scout`,
`pw_intent`, `pw_winprob`, `pw_tune`. `fetch_artifacts.py` still saves the raw tape as
`replay.json`/`replay.json.z`; `pw_episodes` sniffs the bytes, so the names do not matter.

## 9. Open items and risks

- **League version lag**: round 2237 still ran 0.3.64. Record `coworld_version` per
  episode, and never pool games of different rules in one comparison without a version
  split. Rules 45 changed routing to wet goals, which is exactly the lake behaviour the
  guide says decides games; rules 47 added behind-in-cogs glory, which changes the glory
  (and so the rank outcome) of any match with a cog eliminated.
- **Episode seeds**: the league's `game_config.seed` is a constant 2026, but engine seeds
  differ per job (inferred: base + `job_index`). Check that a round's episodes are not
  near-duplicates before treating them as independent (GotA saw identical games across seeds).
- **Seat logs for our own policies** in hosted runs: inferred, not yet exercised. We have no
  membership in this league.
- **Nim version**: local 2.2.6 vs hosted 2.2.10. It reproduced on 3 replays; the hash
  check is the standing guard.
- **Missing `.gitignore` coverage**: the root `.gitignore` already ignores every `episode_data/`,
  so `episode_data/README.md` is untracked unless the root adds a
  `!paintbot_pw_lab/episode_data/` exception.

## Appendix: the verified probe (`lab_seat_probe.nim`) — superseded

> **Superseded by `tools/pw_trace`** (plan T1, `docs/tools/pw_trace.md`). This probe was
> verified at `7b2b19f5` (0.3.65) only. It **does not compile from 0.3.75 on**: `Seats` became
> a per-match runtime value (`kinship.nim:28-30`), so `array[Seats, …]` fails with "cannot
> evaluate at compile time: seatCount" (checked by compiling this code against the 0.3.78
> worktree). Kept as a record of what was verified, not as code to copy.

Built inside the `7b2b19f5` worktree as `examples/paintbot/lab_seat_probe.nim`:

```sh
nim c --mm:arc --threads:on -d:pwTraining -d:headless -o:seat_probe examples/paintbot/lab_seat_probe.nim
seat_probe REPLAY [...]   # one JSON line each
```

```nim
import std/[os, json]
import game, sim, neural_contract

proc probe(path: string): JsonNode =
  let r = loadRecording(path)             # sets rules/vision/map/glory from the header
  var w = newWorld(r.seed, r.endTick)
  var stats: CombatTelemetry              # the engine's own SeatStats, outside World/hash
  for i in 0..<Seats: stats[i].firstFriendlyFireTick = -1
  var shots, aliveTicks, wetTicks, downs, grenades, sprays, shields, gloryHearts: array[Seats, int]
  var firstDown: array[Seats, int]
  for i in 0..<Seats: firstDown[i] = -1
  var seenGlory, seenAward: seq[string]
  var gloryByKind: array[2, array[GloryKind, int]]
  observeShot = proc(tick: int32, slot: int) = inc shots[slot]
  var mismatch = -1
  for f in r.frames:
    let prev = w.cogs
    let eq = w.equipment
    combatTelemetry = addr stats
    w.step(f.commands, replayRulesVersion)
    combatTelemetry = nil
    if w.stateHash() != f.hash and mismatch < 0: mismatch = w.tick
    for i in 0..<Seats:
      if w.cogs[i].hp > 0:
        inc aliveTicks[i]
        if inWater(w.cogs[i].pos): inc wetTicks[i]
      if w.cogs[i].hp == 0 and prev[i].hp > 0:
        inc downs[i]
        if firstDown[i] < 0: firstDown[i] = w.tick
      if w.equipment[i].grenade and not eq[i].grenade: inc grenades[i]
      if w.equipment[i].sprayCan and not eq[i].sprayCan: inc sprays[i]
      if w.equipment[i].armor > eq[i].armor: inc shields[i]
    for e in w.gloryEvents:                # rolling window: dedupe
      let k = $e.tick & ":" & $e.team & ":" & $e.kind & ":" & $e.amount
      if k notin seenAward:
        seenAward.add k
        gloryByKind[e.team][e.kind] += e.amount
    for p in w.gloryPickups:
      let key = $p.tick & ":" & $p.seat
      if key notin seenGlory:
        seenGlory.add key
        inc gloryHearts[p.seat]
  observeShot = nil
  # ... emit {rules, map, vision, seed, end_tick, frames, hash_mismatch_tick, final_hash,
  #      winner, glory, glory_awards, captures, names, seats: [per-seat fields of section 5]}
```

Sample output (seat 3, `ereq_5092af64`): `kills 7, deaths 2, hits_enemy 16,
hits_taken 6, damage_enemy 16, damage_team 1, shots 39, alive_ticks 1505, wet_ticks 0,
hits_from_high 2, first_ff_tick 79, lives_left 2`.
