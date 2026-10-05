# pw_trace: hash-checked replay expander

Re-simulates a Paintbot PW tape with the engine's own `step`, checks the recorded state
hash after every tick, and writes every event plus sampled per-tick state as JSONL. It is
the evidence gate under every lab number: a trace is usable only when its `summary` says
`verified`. Most users should call it through `pw_episodes.py`, which caches it and builds
tables ([tables.md](tables.md)). Source: `tools/pw_trace.nim`. Part of the lab tool set:
[tool index](README.md) (`pw.py trace`, built by `pw.py build`).

## Build and run

```bash
paintbot_pw_lab/tools/build_tools.sh                       # default: the tag in tools/release.env
source paintbot_pw_lab/tools/release.env; B=paintbot_pw_lab/tools/bin/$PW_RELEASE_TAG
$B/pw_trace REPLAY OUT.jsonl [--state-every N] [--window A:B] [--vis-every M]
```

- `REPLAY`: a raw `POLYWORLDREPLAY` tape or the gzip one at a public `replay_url`.
- `--state-every N` (default 6 = 4 Hz): state rows every N ticks, plus the last tick.
- `--window A:B`: also a state row at every tick in [A, B].
- `--vis-every M` (a multiple of N; default off): all-pairs visibility rows every M ticks.
- Exit 0 and `verified ticks=… hash=… ms=…` on success; exit 1 with `pw_trace FAILED: …`
  on stderr (and a `summary` row with `verified: false`) on a hash mismatch, frames after
  the match ended, a tape that ends before the match, or a failed identity check; exit 2
  (message on stderr) on bad arguments (missing paths, an unknown `--option`,
  `--state-every` < 1, `--vis-every` not a multiple of `--state-every`) or a non-tape file.

Build notes: `build_tools.sh` copies the file into the release worktree as
`examples/paintbot/lab_pw_trace.nim` and compiles it there with `-d:pwTraining` (for
`damageObserver`/`damageWeapon`/`combatTelemetry`; the per-tick hash check proves it does
not change the simulation). The engine keeps match state in module globals: **one process
per replay**. Seat count is per match (`Seats` is a runtime value); the code uses `seq`
everywhere. The `SeatStats` telemetry (`CombatTelemetry`) is as wide as the build supports:
`MaxSeats` = 256 from coworld-v0.3.79 (`sim.nim:264`, `kinship.nim:12`; same lines at
0.3.89), 16 in older builds. A match wider than that skips it (its `seat_stats` and kill check
are null); from 0.3.79 every match fits.

Terrain cache: since 0.3.89 a fresh `-d:pwTraining` process pays ~18 s filling the terrain
table (#183). `pw_trace` loads the lab's shared terrain file instead when
`PW_TERRAIN_CACHE_DIR` is set, which `pw.py trace` and `pw_episodes.py` do. That brings a tape
down to ~0.3 s, and the first run for a release builds the file (~27 s). The binary run by hand
without the variable is uncached. The stdout line ends with `terrain=loaded|built|rejected|off`.
Output is identical either way. File, bounds and switches (`PW_TERRAIN_CACHE=0`):
[pw_release.md § Terrain cache](pw_release.md#terrain-cache).

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py trace [--tag TAG] REPLAY OUT.jsonl [...]` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | a tape (raw or gzip), the output path, `--state-every`, `--window`, `--vis-every` |
| Outputs | `OUT.jsonl` (meta, events, states, visibility, summary) |
| `--json` | not supported: `pw_trace` is a Nim binary. Its `summary` row (`verified`, `hash`, `ticks`) is the machine-readable result. When the binary is not built, `pw.py trace ... --json` prints a lab envelope with exit 3 and the build command in `next[]` |
| Exit codes | 0 verified; 1 hash mismatch, frames after the end, a short tape or a failed identity check; 2 bad arguments or not a tape; 3 (dispatcher) not built |
| Idempotence / cache | none here; `pw.py episodes` caches traces per episode. Reads (and builds once) the shared [terrain cache](pw_release.md#terrain-cache) |
| Typical next step | use `uv run python paintbot_pw_lab/tools/pw.py episodes` instead unless you need the raw JSONL |

## Output schema (`schema_version` 1)

One JSON object per line, each with `type`:

- `meta` (first line): `schema_version`, `tool`, `engine_release` (the build tag),
  `nim_version`, `replay`, `rules` (tape header), `mode` (`teams`/`ffa_kin`), `map`,
  `bounds` (`minX, minZ, maxX, maxZ`, in centimetres), `vision`, `glory_config` (engine field names), `seats`, `seed`, `end_tick`, `frames`,
  `names`, `tick_rate`, `meter_target_ticks`, `hearts` (`idx`, `pos`, initial `owner`),
  `pickups` (`idx`, `kind`, `pos`), `trenches`, `cover_count`, `homes`, `options`,
  `state_columns`, `heart_columns`.
- `event`: `t` (world tick after the step; see [tables.md](tables.md) conventions), `kind`,
  and per kind:

| kind | fields |
| --- | --- |
| `spawn` | `seat`, `pos`, `lives`, `initial`, `near_owned_heart` (inferred) |
| `shout` | `seat`, `text`, `bytes`, `heard_by` (seats within 1,280 units, both alive, pre-step world) |
| `windup` | `seat`, `aim` (target point), `gun_aim` (vector) |
| `fire` | `seat`, `origin`, `end`, `length`, `gun_aim`, `hit`, `victim`, `aim_target`, `aim_target_distance`, `aim_target_across`, `inferred_shielded`, `inferred_dead`, `inferred_trench_dodge` |
| `damage` | `seat` (attacker, null = map), `victim`, `weapon`, `hp_removed`, `armor_absorbed`, `killed`, `friendly`, `self`, `distance`, `attacker_pos`, `victim_pos` |
| `kill` | `seat`, `victim`, `weapon`, `friendly`, `self`, `victim_pos`, `distance` |
| `spray` | `seat`, `pos`, `spray_aim` (burst start; victims are `damage` rows with weapon spray) |
| `grenade_charge` | `seat` (charge 0 → >0) |
| `grenade_throw` | `seat`, `from`, `to`, `lands_at` (in the `t` convention) |
| `grenade_blast` | `seat`, `pos`, `trench`, `victims` |
| `pickup` | `seat` (null if unidentified), `idx`, `pickup_kind`, `pos`, `ambiguous` |
| `capture_start` / `capture_complete` / `capture_reset` | `heart`, `team`; complete adds `previous_owner`, credited `seat`; reset adds `lost_ticks`; start adds `replaced_team` |
| `contest_start` / `contest_end` | `heart`, `capture_team`, `capture_ticks` |
| `glory` | `team`, `glory_kind`, `amount`, `engine_tick` |
| `glory_heart_taken` | `seat`, `amount`, `pos` |
| `disguise_on` / `disguise_off` | `seat`; off adds `cause` (`attack`/`death`) |
| `enter_water` / `leave_water` / `enter_trench` / `leave_trench` | `seat` (alive on both ticks) |

- `state`: `t`, `seats` (one array per seat in `state_columns` order), `hearts` (one array per
  heart in `heart_columns` order), `meter_ticks`, `glory`, `team_lives`, `cogs_out`, `winner`.
- `visibility`: `t`, `sees` (per seat, the list of seats it can see).
- `summary` (last line): `schema_version`, `verified`, `failure`, `hash_mismatch_tick`, `final_hash`, `ticks`,
  `frames`, `winner`, `glory`, `meter_ticks`, `hearts_owned`, `team_lives`, `cogs_out`,
  `checks` (`glory`: `ok`, `detail`, `initial`, `awards`, `countdown`, `unsettled`, `final`, each
  per team; `kills`: `ok`, `kill_events`, `enemy_kill_events`, `seat_stats_kills`,
  `seat_stats_deaths`, `tags`), `seats` (exact per-tick counters, see `seats` table), `seat_stats` (engine
  `SeatStats` per seat, or null), `elapsed_ms`.

## How each item is derived

- Engine hooks: `observeShot` (ray released), `observeHit` (armor before the hit),
  `damageObserver` + `damageWeapon` (HP removed, killed, weapon), `observeTag` (checked
  against kill events).
- World diffs after each step: windup, spray burst, grenade charge/throw/blast, spawns,
  disguise, water/trench transitions (`inWater`, `trenchAt`), pickups (`readyAt` jumps),
  captures (`heartCaptures`, `controlHearts.owner`, `cogs.captures`), glory (`gloryEvents`
  multiset difference) and glory-heart takers (`gloryPickups`). Shouts come from the tape.
- **Glory identity**, checked every tick: running = initial + new awards − countdown (1 per
  second after heart awards, floored at 0), and `w.glory` must equal it (or 0 for the loser
  once settled). A naive "event tick == now" filter double-counts; the multiset difference
  does not.

## Verified (2026-09-29, Nim 2.2.6, arm64 macOS)

Re-checked with build `coworld-v0.3.89` (2026-09-30, local `inWater`): 11 of 11 tapes verified
(the 3 rules-44 samples, the 4 hosted `seed-pilot-2026-09-30` tapes, 4 local base-vs-base
recordings), the same hashes as the 0.3.80 build where both ran. Uncached, each run takes about
18.5 s, not 0.7 s: 0.3.89's training terrain table fills whole 64 × 64 blocks on first touch
(#183). With the terrain cache (2026-09-30) the same 7 hosted and sample tapes take 0.25-0.38 s
each, with identical rows, summaries and hashes ([pw_release.md § Terrain cache](pw_release.md#terrain-cache)).

Re-checked with build `coworld-v0.3.79`: the `ereq_e7d3e242` sample with `--vis-every 24
--window 100:130` (verified, 4108 ticks; every field list above matches its rows, and
across the 3 samples plus 8 local base-vs-jev recordings every listed event kind occurs), a
local `pw_local screen --record` recording (rules 48), and the exit-2 paths (no arguments, `--bogus`, `results.json` as the
tape). The notes below are from build `coworld-v0.3.78`:

- The 3 rules-44 samples in `episode_data/` (0.6-1.2 s each, 455-664 shots): verified; glory
  identity and kill identity hold; gun hits = gun damage events.
- 3 local 16-seat `paintbot-headless --record` matches with
  `--glory:{"behind_lives":5,"behind_cogs":10}` (tape rules 48; teams play rules 47): verified,
  including `behind_cogs` awards; also with `--vis-every 24 --window 100:130`.
- 2 fresh hosted league episodes from coworld 0.3.78 (round 2371, public `replay_url`, gzip):
  verified hash-exactly. This settles the plan's open question: hosted tapes built with Nim
  2.2.10 re-simulate exactly with local Nim 2.2.6 (2/2 so far; the hash check keeps guarding).
- The inferred `aim_target` equals the actual victim on 210 of 234 hits in `ereq_e7d3e242`.

## Limits

- Shielded-victim and trench-dodge rays look like misses to the engine hooks; they are
  flagged (`inferred_*`) and never counted as hits.
- A shot's intended target is an inference (aim line); only a policy trace knows it.
- VM-disabled tick is not in the tape (see `pw_metrics` heuristic and our seat logs).
- Pickup takers are attributed by state change within 120 units; two same-kind pickups
  taken by nearby seats on one tick are `ambiguous`.
- Not exercised: FFA-kin tapes, generated maps (`map` non-empty), team vision, `vision_range`
  (ranged) tapes, >16 seats (`paintbot-headless` has no seat-count flag; only a coworld config
  sets it).
- `in_water` / water transitions use an `inWater` defined in `pw_trace.nim` itself (as in
  `pw_map.nim`): `visionRulesVersion >= 30 and riverBlend(x, z) > 0 and terrainHeight(x, z) <
  RiverWaterHeight`, the test `mechanics.nim:628-629` uses to slow a wading cog. It was imported
  from `neural_contract` until 0.3.89 removed it (#185); if a future release changes the wading
  rule in `mechanics.nim`, change both copies.

## Rules 49

Schema 2 includes self-destruct commands and sniper/radar/mister state. Self-destruct
damage and events are distinct from grenades. New pickup kinds are supported; taker
attribution remains inferred. Ordinary and sniper reach constrain inferred aim targets,
but the aim corridor is calibrated only for rules 48. See [tables](tables.md) and the
[evidence contract](../evidence-pipeline.md#rules-49-trace-contract). Cache receipts include
the binary hash and table version, so old expansions are rebuilt.

The same owner self-destructing while its earlier lob lands on that tick is verified
against the engine phase order but is not a separate integration fixture. Tests exercise
initial suicides and post-shield blasts that kill enemies and later would-be bombers.
