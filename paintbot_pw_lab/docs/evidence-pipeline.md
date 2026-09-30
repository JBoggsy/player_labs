# Paintbot PW evidence pipeline

> **Currency.** Verified 2026-09-30 against paintbot-pw tag `coworld-v0.3.89` = `118e1619`
> (recordings stamped rules 48; the teams game plays rules 47). Re-simulation at 0.3.89 was
> checked with `paintbot-headless` and the lab's `pw_trace` built from that tag by local Nim
> 2.2.6 on arm64 macOS; the tools are pinned to 0.3.89 (`pw_trace.nim` and `pw_map.nim` define
> the wading test locally since 0.3.89 removed `neural_contract.inWater`,
> [pw_trace.md](tools/pw_trace.md)).
> Measurements come from 80 hosted main-league episodes of 0.3.79 (rounds 2382-2388,
> `episode_data/audit-2026-09-29/`) and the three rules-44 samples of 2026-09-28
> (`episode_data/20260928T214433_*`), all loaded with `pw.py episodes` / `pw.py metrics`, plus
> 12 hosted 0.3.89 episodes of rounds 2509-2510 (`pw.py scout fetch`, 2026-09-30) for the
> format checks. **Re-verify when** a new `coworld-vX` tag appears:
> `pw.py deployed-ref`, the accepted rules list in `game.nim` `loadRecording`, and a
> hash-checked re-simulation of fresh league tapes (`pw.py episodes <dir> --json`).

Line references are to `118e1619` in `~/coding/coworlds/paintbot-pw` (abbreviated `pw:`).
**Verified** means exercised on the episodes above or a local run; **inferred** means read from
source but not exercised.

This is *not* the Season 1/2 Paintbot in `paintbot_lab/`. Different engine (Polyworld
Nim), different replay container, different tools. Do not reuse `paintbot_lab/tools/`.

The lab's tools built on this pipeline are indexed in [docs/tools/README.md](tools/README.md):
`pw_trace` (hash-checked expansion), `pw_episodes` (reader, cache, Parquet tables:
[tables.md](tools/tables.md)), `pw_metrics`, `pw_local` and the analysis tools on top. This page
is the reference for the artifacts and the re-simulation they rest on.

## 1. Summary

| Question | Answer |
| --- | --- |
| Replay format | Polyworld `POLYWORLDREPLAY` tape: every seat's command every tick plus a per-tick state hash. **Verified.** |
| Re-simulation | **One build replays many versions.** The header's version is the rules number and the sim keeps every old rules path. The 0.3.89 build re-simulated all 80 hosted 0.3.79 tapes, the three rules-44 samples and 12 hosted 0.3.89 tapes with **no hash mismatch**. **Verified.** |
| Hosted vs local build | Hosted images build with Nim 2.2.10 on linux/amd64; local Nim 2.2.6 on arm64 reproduces every hosted hash checked so far (95 tapes). The per-tick hash check stays the guard. **Verified.** |
| Per-seat stats | `pw_trace` expands a tape into events and per-seat counters, hash-checked; `pw_episodes` turns them into tables and `pw_metrics` into per-seat, per-policy and per-team metrics (section 5). The repo's own `replay_stats.nim` is per-team and not hash-checked (section 4). |
| Local runs | `pw.py local` (native library, league glory config by default), `paintbot-headless --record`, and the repo's `local.py` (the exact hosted handoff, per-seat logs, engine-default glory only). Section 6. |
| Seat logs | Returned only for episodes you have a policy in; league episodes without one of our policies return 403. **Verified.** |

## 2. Artifact inventory

Two ways to get an episode, with different files:

| Source | Files | Notes |
| --- | --- | --- |
| Shared fetcher (`.claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py --ereq …`) | `episode.json` (with `game_config`), `results.json`, `replay.json` + `replay.json.z`, `download.json`, seat logs when ours | The two replay files are the **same raw tape** under misleading names; neither is JSON or zlib. |
| Public round listing + `replay_url` (how `audit-2026-09-29/` was built) | `episode.json` (the listing row: no `game_config`, no `results.json`), `replay.gz` | `pw_episodes` takes team from seat parity and checks scores against `participant_scores`. |

`pw_episodes` sniffs tape bytes (raw, gzip or zlib), so file names do not matter.

### 2.1 `episode.json`

- `participants[]` with explicit `position` 0-15, `policy_name`, `version`, `player_name`,
  `is_filler`. Each policy fills 8 seats (one `is_filler: false`, seven fillers). Seat parity is
  the team: even = Red/Ember, odd = Blue/Azure.
- `coworld_version`, `coworld_id`, `variant_name` ("Two policy teams" on every 0.3.79 and
  0.3.89 league episode checked), `job_index`, `round_id`, `round_number`.
- `game_config` (fetcher rows only): `seed: 2026`, `max_ticks: 14400`, `glory:
  {"behind_lives": 5, "behind_cogs": 10}`, 16 `slots`, placeholder `players`. No `map` or
  `vision`: Heartwick with per-cog vision. **`seed` is a stored placeholder**, not the seed the
  engine plays; see [field.md](field.md) for how episode seeds are derived. The glory config
  the engine actually played is in the tape header (section 2.3): all 80 0.3.79 tapes carry
  behind_lives 5 and behind_cogs 10 with the other keys at their defaults.
- `participant_scores[]` by position, and `scores[]` deduplicated by policy. Join by
  position, never by array order.
- `replay_url`: public S3 `…/replays/<id>.replay`, **gzip** (`1f 8b`).

### 2.2 `results.json`

`{"scores": [16 floats], "ticks", "seed", "outcome", "banked_gold": [], "returned": []}`.

- `scores[i]` is the team's settled glory, repeated on every seat of that team; the loser and
  both sides of a draw hold 0 (`pw:examples/paintbot/sim.nim:1071-1086`,
  [mechanics.md §1](mechanics.md)).
- `seed` is the **engine seed** and equals the tape's (checked on the three rules-44 samples),
  not `game_config.seed`.
- `outcome`: `"0"`/`"1"` = winning side, `"time_limit"` when there is no winner (a draw by any
  route), `"ended"` in FFA-kin (`pw:examples/paintbot/game.nim:604-606`). A match decided on
  the meter at the time limit reports the **meter** leader, not `"time_limit"`
  ([mechanics.md §2](mechanics.md)).
- `banked_gold` / `returned` are always empty, fields of the shared results type
  (`pw:src/polyworld/coworld.nim:55-56`).

### 2.3 Replay

- Container (`pw:src/polyworld/tapes.nim:8-9`): `POLYWORLDREPLAY`, u16 file format 1,
  u16 **gameVersion = rules number** (48 on 0.3.79 and 0.3.89 teams tapes; 1000 + rules for
  FFA-kin; plus 2000 when the match set `vision_range`, below),
  u16 name length, `paintbot_pw`, then a Flatty `Recording`
  (`pw:examples/paintbot/game.nim:94-105`): `seed`, `frames` (one per tick: one
  `Command{walk, shoot, direct, goal, aim, chargeGrenade, sneak}` per seat + `hash u32`),
  `names`, `communications` (every `shout` with tick, slot and **text**), `endTick`, `map`,
  `vision`, `glory` config, and from rules 46 `seats`. Rules 43-45 store exactly 16 commands and
  names in fixed arrays; rules 46 stores sequences plus the seat count with the 5-key glory
  config; rules 47-48 add the two behind-in-cogs keys (`pw:game.nim:61-105`, loader
  `:358-448`). The loader checks every frame has `seats` commands.
- **Ranged recordings (0.3.88+).** A match played with the opt-in `"vision_range"` config is
  stamped 2000 above its usual version (2048 teams, 3048 FFA-kin) and appends the range as an
  int32 in metres after the usual payload (`RecordingRanged`, `pw:game.nim:147-156`,
  `216-221`, `230-233`); loading one binds the range for the re-simulation. Only rules 48 may
  carry a range. A match without the key saves exactly as before, so builds before 0.3.88
  cannot read ranged tapes but older tapes are unaffected. No league variant sets it: all 12
  hosted 0.3.89 tapes checked carry 48. **Verified** (source; headers).
- It holds **every seat's executed command every tick**, not a request log (`pw:game.nim:603`):
  about 400 bytes per tick at 16 seats; 0.54-2.0 MB uncompressed per 0.3.79 league match
  (80 tapes).
- `names[i]` holds the name the platform sent for the seat (`config.players[i].name`,
  `pw:game.nim:566-567`), deduplicated with " (2)"…" (8)". On 0.3.79 tapes it was the player
  display name, which usually equals `participants[i].player_name` but not always (one player's
  8 seats were recorded as "Baseline" while `episode.json` names the player
  `paintbot-pw-basic-r22`, 160 of 1,280 seats). **On 0.3.89 tapes (2026-09-30) it is
  "player (owner)"**, e.g. "Andrew Brower B (Andrew B)" and "Andrew Brower B (Andrew B) (2)";
  0.3.89 also added an optional `owner` field to the config's `players[]`
  (`pw:src/polyworld/coworld.nim:14-16`). Join by `episode.json` position; use names only as a
  cross-check, and do not parse them.
- A freshly completed episode can briefly report `results`/`replay` unavailable; a `--force`
  refetch minutes later gets them. Treat a missing artifact as "retry", not "absent".

### 2.4 Logs

- **Per-seat logs** (`coworld episode-logs <ereq>`, or the fetcher's policy-logs routes):
  **403 for league episodes we have no policy in.** `--elevated` is not for lab use.
- Log content, verified locally: `Player slot N started.`, then BASIC `print` output
  verbatim, then `Player slot N completed.`. Advisor oracle journal lines and neural telemetry
  also go here (`pw:examples/paintbot/bots.nim:163`, `189`; `pw:game.nim:621-624`).
- **Runtime BASIC errors** (instruction limit and so on) disable that seat for the rest of the
  match: it sends empty commands, the error goes to its log, and `status.json` records
  `exit_code 1, reason "BASIC VM disabled"` (`pw:bots.nim:263-266`,
  `pw:src/polyworld/coworld.nim:182-210`). The match continues.
- **Compile errors fail the whole episode.** Verified locally: a seat with a syntax error
  wrote `failure.json` `{"message":"BASIC compilation failed for player slot 1",
  "failed_policy_index":1}` and no `results.json`. The engine parks in `waitForCollection`
  (`pw:coworld.nim:212-234`), so `local.py` hangs until its 10-minute deadline. **Staging**
  failures (a WASM upload, a hash mismatch, a rejected neural package) put an idle stub in that
  seat so the engine plays on (`pw:coworld/paintbot/runtime/host.py:99-124`), but the platform
  still records the episode as `failed` (`error_type: player_error`, "Policy initialization
  failed: <type>", no scores, no replay; live 2026-09-30, round 2510). Either kind of hosted
  failure shows up as failed episodes; treat that as the signal (lab AGENTS rules).
- Combined game log: optional and usually unavailable. The local `game.log` holds
  `ticks=… captures=[…] hash=…` and, with `PW_BASIC_PEAKS=1`, per-seat peak instructions, work
  units, strings and neural ops (`pw:game.nim:613-620`).

## 3. Re-simulation

### 3.1 Why one build replays many versions

`loadRecording` reads the header version, sets `replayRulesVersion` and `visionRulesVersion`
to it, and decodes the matching historical layout (`pw:game.nim:358-448`; rules 43-45 share a
layout, `:413`; rules 47-48 share one, `:429`; ranged tapes `:373-382`). The sim branches on
those variables throughout (for example `stateHash` `pw:sim.nim:1096`, glory
`pw:sim.nim:978-1075`, lives `pw:mechanics.nim:146,444`). The guide states the policy: "Earlier
replay versions retain their original rules and hashes" (`pw:guide.md:147-153`).

Evidence:

- The 0.3.79 build re-simulates all 80 hosted rules-48 tapes (rounds 2382-2388) and the three
  rules-44 samples with no mismatch; every final glory equals the episode's scores
  (`pw.py episodes --json`: `results_check` `participant_scores` / `results.json`). The
  rules-44 sample `ereq_e97afe98` ends on hash 3587158643 at tick 2219 under the 0.3.65, 0.3.78,
  0.3.79 and 0.3.89 builds.
- The 0.3.89 build (`paintbot-headless --replay`, 2026-09-30) re-simulates the same 80 0.3.79
  tapes, the three rules-44 samples and 12 hosted 0.3.89 tapes (rounds 2509-2510) with no
  mismatch; a `pw_trace` built at 0.3.89 verified a 0.3.79 and a 0.3.89 tape end to end.
- Negative control (run at 0.3.65): patching the header's rules byte from 44 to 45 on the
  rules-44 samples diverged at ticks 26-269, and `paintbot-headless --replay` raised
  `Replay hash mismatch at 26`; a tape with one flipped byte fails `pw_trace` the same way
  ([pw_episodes.md](tools/pw_episodes.md)). The hash check catches a rules mismatch.

Consequence: build the **newest** deployed tag, not the recording commit. The guard is the
per-tick hash: if a future release changed behaviour without bumping the rules number, old
tapes would diverge, so every lab tool keeps the check. Map a deployed version to source with
the tag `coworld-v<coworld_version>` (`pw.py deployed-ref`); the manifest's `source_url` carries
no commit.

### 3.2 Build (about 1 minute cold, no credentials)

```sh
paintbot_pw_lab/tools/build_tools.sh                   # the tag in tools/release.env
source paintbot_pw_lab/tools/release.env; B=paintbot_pw_lab/tools/bin/$PW_RELEASE_TAG   # paintbot-headless, pw_trace, pw_map, replay_stats
```

The script fetches tags in `~/coding/coworlds/paintbot-pw` (cloning it if missing), adds a
detached worktree at `paintbot_pw_lab/tools/.cache/<tag>/` (never changing the clone's own
checkout), pins dependencies with `coworld/tools/sync_dependencies.py` into the worktree's
`tmp/coworld/deps` (read through `POLYWORLD_DEPS`, `config.nims:4-17`), and builds the binaries
and the `-d:coworld` engine `tmp/paintbot-coworld` that `local.py` needs. Both output
directories are gitignored. `build_native.sh` builds the native library `pw.py local` uses.

### 3.3 Commands

```sh
# The lab path: trace, verify and tabulate every episode under a directory (cached).
uv run python paintbot_pw_lab/tools/pw.py episodes paintbot_pw_lab/episode_data/<batch> --json

# Hash-checked validation with the engine alone: raises on any mismatch.
$B/paintbot-headless --replay episode_data/<dir>/replay.json
#   ticks=2219 captures=[3, 2] hash=3587158643

# From a public replay_url instead of the fetcher:
curl -sS "$REPLAY_URL" | gunzip -c > match.raw
```

Each takes about 1 s per league match; a cached `pw.py episodes` rerun over 80 episodes takes
under 3 s.

## 4. What the repo's own tools do

Prefer the lab tools (section 5). The repo's tools are useful to know because the guide cites
them.

### 4.1 `examples/paintbot/replay_stats.nim`

Per **team** only (`pw:replay_stats.nim:32-67`): glory, lives left, cogs standing, "captures",
heart-ticks, ticks ahead on heart count, and friendly-fire / "quiet-supplies" glory. It handles
FFA-kin tapes per seat (`:20-30`). Three pitfalls:

1. **No hash check.** It calls `w.step` directly (`:41-42`) and never compares `f.hash`. A tape
   from a build that does not reproduce it would give plausible, wrong numbers.
2. **"captures" is hearts held at the end, not captures made.** `w.captures` is recounted from
   heart owners every tick (`pw:mechanics.nim:357-359`). Cumulative per-seat flips are
   `cogs[i].captures` (`pw:mechanics.nim:354`).
3. **"quiet-supplies" is every award except friendly fire** (`:55-56`), so it lumps
   behind-in-lives, behind-in-cogs and glory hearts together. On current tapes that total is
   mostly the losing side's behind awards: in the 0.3.79 sample the losers' pre-settle awards
   averaged 518 (behind in lives) + 294 (behind in cogs) + 10 (glory hearts) + 2 (quiet
   supplies). Use `pw.py metrics` for the breakdown by kind.

### 4.2 `examples/paintbot/analysis.nim`

`indexReplay` is the viewer's indexer. It advances with `advance()`, which **is** hash-checked
(`pw:game.nim:574-581`), and emits per-seat shot/hit counts and a `Moment` event feed (tag,
hit, down, heal, pickups, spray, grenade throw and blast, territory flip). It keeps a full
per-tick array and 240-tick checkpoints in memory; `pw_trace` covers the same ground for batch
work (read, not run standalone).

### 4.3 `examples/paintbot/inspect_replay.nim`

A 13-line debug stub: per-seat move and shot counts and final positions. No hash check.

### 4.4 Engine telemetry: `SeatStats` under `-d:pwTraining`

`pw:sim.nim:250-264` defines per-seat `SeatStats`: damage dealt to enemies and to teammates,
enemy hits, hits taken, kills, deaths, first friendly-fire tick, spray damage and kills,
gun/grenade/spray kills, and hits from and to water, high ground and trenches.
`pw:mechanics.nim:388-425` fills it inside `damage()` whenever `combatTelemetry` is set. It is
outside `World` and the hash. `CombatTelemetry` is `array[MaxSeats, SeatStats]` (256 entries,
`pw:sim.nim:264`; 16 before 0.3.79). The native training library points it at its own array
per step (`pw:native_env.nim:943-947`); `pw_trace` does the same and cross-checks its kill
events against it.

`tools/kin_replay_counters.nim` + `tools/kin_replay_stats.py` are the repo's own hash-checked
re-simulators for **FFA-kin** tapes on the Heartwick island only; they serve Heartland, not
this league.

## 5. Per-seat and per-team facts from a tape

Everything below comes from one hash-checked `pw_trace` pass per tape. The table contract
(columns, units, conventions) is [tables.md](tools/tables.md); metric definitions are
[pw_metrics.md](tools/pw_metrics.md).

| Available | From | Notes |
| --- | --- | --- |
| kills, deaths, teammate kills, self-kills, by weapon | damage events (`damage`, `kills` tables) | `pw_metrics` `kills` counts enemy victims; friendly and self kills are separate |
| hits, damage dealt and taken, armor absorbed | damage events | damage is health removed after armor |
| shots, gun accuracy, distance bands, inferred blocked shots | `shots` table | a shot's intended target is inferred from the aim line |
| alive, water, trench, heart-reach, territory ticks | per-tick counters | water uses the same predicate as the speed penalty |
| captures started, completed, reset; contests | capture events | per heart and per credited seat |
| pickups by kind, glory hearts taken | pickup and glory-heart events | two same-kind pickups taken by nearby seats on one tick are `ambiguous` |
| glory by kind, per team | `glory` table | glory is team-level; per-seat glory exists only for glory hearts |
| shouts and their text, who heard them | tape `communications` + earshot recompute | opponents' shout text is in the tape |
| idle / possibly VM-disabled seats | empty commands | inferred; the disable reason is only in that seat's log |

**Not in the tape:** BASIC `print` output, the advisor oracle's questions and answers, and why
a seat was disabled. Those live only in seat logs, which we get only for our own seats. Per-seat
commands are in the tape, so "did seat i try X at tick t" is answerable.

**Measured on the 0.3.79 league sample** (80 episodes, 8 policies, 1,280 seats; `pw.py metrics
--csv`, damage table):

| Measure | Value |
| --- | --- |
| Match length | 1,354-5,034 ticks, median 1,965 (82 s), 10th-90th percentile 64-124 s |
| Ending | 78 by elimination, 2 by a full meter, 0 at the time limit |
| Winning glory | 458-996, median 544 |
| Deaths | 4,187: 3,828 enemy kills (gun 3,621 = 95%, grenade 164, spray 43), 259 teammate kills (gun 210, grenade 39, spray 10), 100 self-kills (all grenade) |
| Gun | 36,108 rays; 12,961 enemy hits (36%); 949 teammate hits (2.6% of rays) |
| Pickups | 1,650 grenades, 576 medkits, 400 armor, 252 sprays, 144 uniforms; 101 glory hearts |
| Grenades and sprays used | 407 grenade throws, 75 spray bursts |
| Water / trench | 7.2% / 1.9% of alive time |
| Shouts | 13,936, in every episode |
| Suspected VM-disabled seats | 0 |

## 6. Local runs

Local runs are for mechanism checks, compile checks and screening. The local field is not the
league field.

- **`pw.py local`** ([pw_local.md](tools/pw_local.md)): compile checks, single matches and
  paired screens on the native library, with the league's glory config by default, and
  `--record` to write tapes `pw.py episodes` reads. The lab's default local path.
- **`paintbot-headless`** (no host, no seat logs): takes the league's match config on the
  command line, `--glory:<json>`, `--map:<name>`, `--vision:team`, `--vision-range:<metres>`
  (0.3.88+), `--mode:ffa_kin`, `--kin-layout:<name>` (`pw:game.nim:505-532`). **BASIC `print`
  output is discarded** (the headless build gives the VM no print handler, `pw:bots.nim:198`).
  `--bot FILE:N` fills seats **in order** and the seat count is the sum of the `N`s
  (`pw:bots.nim:164-171`, `pw:game.nim:533-537`): `--bot a.bas:8 --bot b.bas:8` puts `a` on seats 0-7, which mixes
  both teams; for A vs B pass 16 alternating `--bot` flags or use `pw.py local`.

  ```sh
  $B/paintbot-headless --bot paintbot_pw_lab/reference/base.bas:16 --seed 2026 --ticks 2400 \
      '--glory:{"behind_lives":5,"behind_cogs":10}' --record out.replay
  #   ticks=2123 captures=[3, 5] hash=276551954   (4.4 s; the same hash under 0.3.78, 0.3.79 and 0.3.89)
  $B/paintbot-headless --replay out.replay          # reproduces it; the tape is stamped rules 48
  ```

- **The repo's `local.py`** (the exact hosted handoff): builds on the `-d:coworld` engine in the
  worktree, runs `runtime/host.py` with stdlib Python, and writes `results.json`, `replay.bin`,
  `player-N.log`, `status.json` and `game.log`. Use it when you need a seat's prints or the
  host's staging path. Options: `--policy` (one file = all seats, or one flag per seat in seat
  order), `--ticks`, `--seed`, `--mode`, `--seats N` (2-256), `--map`
  (`pw:coworld/paintbot/local.py:11-24`). It **cannot** set `vision` or `glory`, so its matches
  use the engine defaults (`behind_lives` 1, `behind_cogs` 1) where the league uses 5 and 10.

  ```sh
  source paintbot_pw_lab/tools/release.env; cd paintbot_pw_lab/tools/.cache/$PW_RELEASE_TAG
  PW_BASIC_PEAKS=1 python3 coworld/paintbot/local.py --output /tmp/pw-run1 --ticks 2400 \
      --policy path/to/base.bas
  ```

## 7. The guide's comparison workflow (`pw:guide.md:156-215`)

- It covers xp-requests over a pinned coworld with all 16 seats in the roster. `policy_ref` must
  be bare `name:vN` or a UUID, and `variant_id` goes in `target` **or** at the top level, not
  both. Advised builds need `episode_player_llm_spend_limit_usd`, or they silently play the
  baseline.
- Its statistics predate the ladder's margin scoring: it treats the score gap as one bit and
  recommends mean winning glory or win rate. The lab's A/B metric is the per-episode Elo
  outcome ([mechanics.md §1.3](mechanics.md), [compare.md](tools/compare.md)). Its advice to
  swap sides in equal halves and fix the stopping rule first still applies.
- Check seat logs for failures and peaks before trusting a score. Derive sides from
  `policy_version_ids` zipped with slots; never assume even seats are "us".
- `coworld/paintbot/tools/jev_experiment.py` / `jev_results.py` do this for the Jev baseline's
  switches only (not read in depth here).

## 8. Open items and risks

- **Version mixing**: record `coworld_version` per episode and never pool games of different
  rules in one comparison without a version split. `pw_episodes` reports `rules` per episode.
- **Episode seeds** are derived per episode by the platform, not `game_config.seed`
  ([field.md](field.md)). Consecutive jobs of a round get consecutive seeds; check a round's
  episodes are not near-duplicates before treating them as independent.
- **Nim version**: local 2.2.6 vs hosted 2.2.10. 95 hosted tapes reproduced; the hash check is
  the standing guard.
- **`.gitignore` coverage**: the root `.gitignore` ignores every `episode_data/`, so
  `episode_data/README.md` is untracked unless the root adds a
  `!paintbot_pw_lab/episode_data/` exception.
