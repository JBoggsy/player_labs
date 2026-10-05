# Episode tables and Python API (contract)

The lab's analysis layer and the contract every analysis tool reads: which Parquet tables
exist per episode, every column and its meaning, the tick/team/identity conventions, and the
Python API. `pw_trace` (Nim) re-simulates a tape hash-exactly and writes
events and state; `pw_episodes.py` turns each episode into the Parquet tables below;
`pw_metrics.py` computes every metric from those tables. Part of the lab tool set:
[tool index](README.md). Every later tool (A/B adapter,
miner features, diagrams, match reports, scouting) reads these tables or this API, so a
change to a column or its meaning bumps `TABLES_VERSION` in `pw_episodes.py` and is
recorded here in the same change.

Column lists re-checked 2026-09-29 against build `coworld-v0.3.79` (`d0728ab1`) on the 3
samples plus 8 local `pw_local` recordings: every table below has exactly the listed columns
(`visibility` and `policy_log` were empty there). First verified with build
`coworld-v0.3.78` (`570174a2`) on: the 3 rules-44 samples in
`episode_data/`, 3 local 16-seat recordings with the league glory config, and 2 fresh hosted
0.3.78 league episodes (tape header rules 48, hosted Nim 2.2.10, traced with local Nim 2.2.6:
hash-exact).

## Conventions (read first)

- **Tick.** Every row's `t` is the world tick **after** the step that produced it
  (frame index + 1). This is also the tick the tape stamps shouts with. The state at `t`
  already reflects every event at `t`. `t = 0` is the initial world (initial spawns and
  the first state row). Policies decide tick `t + 1` from the world at `t`.
- **Team.** `team` 0 = Ember (the platform's "red", even seats), 1 = Azure ("blue", odd
  seats). It comes from `episode.json` `game_config.slots` and must equal the engine's seat
  parity or the episode fails (`identity`). Without slots (e.g. a public round-listing row)
  it falls back to parity and `episodes.notes` says `team_from_parity`.
- **Identity.** Seats join by `position`, never array order. `policy_key` is the exact
  `policy_version_id` when the platform gives one, else `local:<policy_name>`.
- **Unit.** One row per (episode, policy) for anything statistical (`pw_metrics.policy_metrics`).
  Seats of one policy in one episode are not independent samples.
- **Nulls.** Unknown is null, never 0. Exact counts that the whole-match trace would
  have seen are 0 when nothing happened. Nullable ints are pandas `Int64`, booleans
  `boolean`, strings `string`, and list columns are Parquet lists.
- **Exact vs inferred.** Columns named `inferred_*`, `aim_target*`, `near_owned_heart`,
  `ambiguous` and the stuck/VM heuristics in `pw_metrics` are inferences; everything else is
  read from the engine during the hash-checked re-simulation.
- **Evidence gate.** A table exists only for an episode whose trace summary says
  `verified: true`: every tick's hash matched, the tape ended when the match did, the glory
  identity held at every tick, and (16-seat matches) kill events match the engine's
  `SeatStats`. `results.json` (or `participant_scores`) must also agree: ticks, engine seed,
  per-seat scores = the seat's team glory, and outcome = winner.

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py episodes ROOT --sql "..." --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| What it is | the table contract; not a CLI. `pw.py episodes` writes these tables |
| Machine access | `--sql` on `pw.py episodes` returns query rows in `result.sql`; in Python, `pw_episodes.load_batch` / `open_duckdb` (see Python API below) |
| Exit codes | those of `pw.py episodes` ([pw_episodes.md](pw_episodes.md)) |
| Typical next step | `pw.py metrics` for the derived numbers |

## Layout on disk

```
<hosted episode dir>/pw_cache/            <local>/NAME.pw_cache/   (for NAME.replay)
<hosted episode dir>/pw_cache@<variant>/  <local>/NAME@<variant>.pw_cache/   (other tag / options)
    trace.jsonl                            pw_trace output (schema: pw_trace.md)
    tables/<table>.parquet                 one file per table below, for this episode
    receipt.json                           {"inputs": signature, "outputs": {file: sha256}}
```

The signature covers sha256 of the tape, `results.json`, `episode.json`, the local
`.meta.json`, the `pw_trace` binary, the trace options, `CACHE_VERSION` and
`TABLES_VERSION`. A cache is used only when the signature matches and every output's
sha256 matches; anything else is rebuilt in a temporary directory and promoted by rename.
`pw_cache/` lives inside `episode_data/`, which is gitignored; local `*.pw_cache/` dirs live
wherever the recordings are. A trace with another release tag, `--binary` or trace options
(`--window`, `--vis-every`, `--state-every`) is a separate variant directory, so it never
replaces the default one; see [pw_episodes.md](pw_episodes.md#cache-variants).

### Local episodes

A local episode is a `NAME.replay` recorded by `paintbot-headless --record`, optionally with
a sidecar `NAME.meta.json` naming the policy on each seat:

```json
{"source": "local",
 "seats": [{"position": 0, "policy_name": "a.bas", "team": 0,
            "policy_version_id": null, "policy_version": null}, ...],
 "glory_config": {"behind_lives": 5, "behind_cogs": 10}, "seed": 11}
```

`pw_local.py --record` writes this sidecar with `"source": "pw_local"` plus `a_side` and
`policies` (`{"A": {path, sha256}, "B": {...}}`); only `seats` is read here.

Only `seats[].position` and `seats[].policy_name` are required. `team`, if present, is
cross-checked against parity. Without a sidecar each seat's policy is its tape name
(`Bot 1` ... `Bot 16`), which is one "policy" per seat. That is fine for looking, not for
statistics, and `episodes.notes` says `anonymous_local`.

## Tables

All tables carry `episode_id` (hosted: `episode.json` `id`, the `ereq_…`; local:
`local:<stem>`).

### `episodes` (1 row per episode)

| Column | Meaning |
| --- | --- |
| `source` | `hosted` or `local` |
| `path` | episode directory (hosted) or tape path (local) |
| `platform_episode_id`, `job_id`, `round_id`, `coworld_version`, `variant_name`, `status`, `cost_usd` | from `episode.json` (null for local) |
| `rules`, `mode`, `map`, `vision` | from the tape (`map` "" = Heartwick; `vision` "" = per-cog) |
| `glory_config` | JSON of the recorded glory awards (engine field names, e.g. `behindCogs`) |
| `seats`, `engine_seed`, `config_seed`, `end_tick` | tape seed = results seed; `config_seed` = `game_config.seed` |
| `ticks`, `winner` | match length; winner 0/1, -2 draw |
| `outcome` | raw `results.json` outcome (null without results) |
| `glory_0`, `glory_1` | final settled glory (= platform score) |
| `glory_initial_*`, `glory_countdown_*`, `glory_unsettled_*` | identity parts: initial + awards − countdown = unsettled; settleGlory zeroes the loser |
| `meter_ticks_*`, `meter_target_ticks`, `tick_rate` | heart meter in tick-points (÷ 24 = points) |
| `hearts`, `hearts_owned_*`, `team_lives_*`, `cogs_out_*` | end state |
| `final_hash`, `engine_release` | last tick's hash; the build that traced it |
| `state_every`, `vis_every` | trace sampling options |
| `results_check` | `results.json`, `participant_scores` or `none` |
| `notes` | `;`-joined flags: `team_from_parity`, `anonymous_local` |

### `seats` (1 row per seat)

Identity: `seat`, `team`, `team_name`, `team_source` (`game_config`/`meta`/`engine_parity`),
`tape_name`, `policy_version_id`, `policy_id`, `policy_name`, `policy_version`, `player_name`,
`is_filler`, `participant_kind`, `policy_key`, `name_matches_tape` (tape names carry " (2)"
suffixes; null when there is no player name), `score` (the seat's reported score = team glory).

Exact per-tick counters from the trace (ticks): `alive_ticks` (hp > 0 after the step),
`water_ticks`, `trench_ticks`, `disguised_ticks`, `heart_reach_ticks` (within 140 units and a
traversable line of any control heart, the engine's capture test), `contested_reach_ticks`,
`own_/enemy_/neutral_territory_ticks` (`territoryOwner` at the cog), `decision_ticks` (alive
before the step, so the policy ran), `idle_ticks` (decision ticks with an all-default
command), `sneak_ticks`, `last_active_command_tick` (-1 never), `final_idle_run_ticks` (empty
commands since then), `captures`, `tags`, `lives_left`.

`ss_*`: the engine's own `SeatStats` telemetry (16-seat matches only, else null):
`ss_kills` (enemy kills), `ss_deaths`, `ss_damageDealtEnemy`, `ss_hitsEnemy`, `ss_gunKills`,
`ss_hitsFromWater`, … (field list: `sim.nim` `SeatStats`).

### `events` (every trace event)

`t`, `kind`, `seat` (actor, may be null), `team`, `data` (JSON of the remaining fields).
The generic fact table: use it for kinds without their own table: `windup`, `spray`,
`grenade_charge`, `grenade_throw`, `grenade_blast` (`victims` list), `disguise_on`,
`disguise_off` (`cause`: attack/death), `enter_water`, `leave_water`, `enter_trench`,
`leave_trench`, `glory_heart_taken`. Field lists per kind: [pw_trace.md](pw_trace.md).

### `shots` (1 row per gun ray fired)

`t`, `seat`, `team`, `origin_x/z` (shooter at release), `end_x/z`, `ray_length` (the ray stops
at the first victim, a blocker or 5,250 units), `gun_aim_x/z` (aimed vector, pre-jitter),
`hit` (exact: a gun damage event from this seat this tick), `victim`, `victim_team`,
`friendly`, `hit_distance` (exact, from the damage event; null on a miss).

Inferred, never counted as hits: `aim_target` (nearest living enemy within 110 units of the
aimed line, `AimTolerance` in `pw_trace.nim`, calibrated 2026-09-30: it matches the real victim on 93.7% of
enemy hits in the 80-episode league audit, vs 91.6% at the old 150, and tags 21% fewer misses with a guessed target; calibration: [pw_metrics.md](pw_metrics.md#thresholds-calibrated-2026-09-30)), `aim_target_distance`
(along the line), `aim_target_across`; and for misses `inferred_shielded`, `inferred_dead`
(ray ended at a spawn-shielded or just-killed cog, which `damage()` ignores silently) and
`inferred_trench_dodge` (a trench cog within `Radius` of the ray: the 70% dodge), as lists
of seats. Exact attribution of those needs an engine hook (`mechanics.nim:712-714`).

### `damage` (1 row per damage event past the shield and life checks)

`t`, `seat` (attacker; null = the map), `team`, `victim`, `victim_team`, `weapon`
(gun/grenade/spray), `hp_removed`, `armor_absorbed` (armor-only hits have hp_removed 0),
`killed`, `friendly`, `self`, `distance`, `attacker_x/z`, `victim_x/z`.

### `kills` (1 row per death by damage)

`t`, `seat` (killer; null = the map), `team`, `victim`, `victim_team`, `weapon`, `friendly`,
`self`, `distance`, `victim_x/z`. Enemy kills (`seat` not null, not friendly, not self)
equal the engine's `SeatStats.kills` sum (checked per episode).

### `spawns`

`t`, `seat`, `team`, `x`, `z`, `lives` (after spawning), `initial` (t = 0),
`near_owned_heart` (inferred: index of an owned heart within 400 units, else null = end-zone
spawn).

### `pickups`

`t`, `seat` (null when no taker could be identified), `team`, `pickup` (index), `pickup_kind`
(grenade/spray/medkit/armor/uniform), `x`, `z`, `ambiguous` (more than one plausible taker; the
first in the tick's seat order was chosen). The pickup itself is exact (its `readyAt` jumped).

### `captures`

`t`, `kind`, `heart`, `team`, `seat`, `previous_owner`, `lost_ticks`, `capture_ticks`:

- `capture_start`: `team` began capturing (`previous_owner` null).
- `capture_complete`: ownership changed to `team`; `seat` = the credited cog; `previous_owner`.
- `capture_reset`: `team` lost its progress (`lost_ticks`) with no owner change.
- `contest_start` / `contest_end`: both teams in reach; `team` = the capturing team or null;
  `capture_ticks` frozen progress.

### `glory` (1 row per award)

`t`, `team`, `glory_kind` (`quiet_supplies`, `friendly_fire`, `glory_heart`, `behind_lives`,
`behind_cogs`), `amount`, `engine_tick` (the engine's own stamp: glory hearts use the
pre-step tick), `seat` (glory hearts only: the taker). Awards are the multiset difference of
the engine's rolling `gloryEvents` window per step, so none is double counted; the
countdown is not an award (see `episodes.glory_countdown_*`).

### `shouts`

`t`, `seat`, `team`, `text`, `bytes`, `heard_by` (seats in earshot: living, within
`Width/5` = 1,280 units of the living sender on the pre-step world, as `deliverSpeech`),
`heard_by_team`, `heard_by_enemy`.

### `states` (sampled: every `state_every` ticks, every tick in `--window`, and the last tick)

`t`, `seat`, `team`, `x`, `z`, `aim_x/z` (aim is a target point), `goal_x/z` (the clamped walk
target), `hp`, `armor`, `lives`, `shield`, `respawn`, `cooldown`, `disguised`, `in_water`,
`trench` (index or -1), `grenade`, `spray_can`, `charge`, `windup`, `burst`, `captures`,
`tags`, `alive`, and the command applied in the step that produced `t`: `cmd_walk`,
`cmd_shoot`, `cmd_direct`, `cmd_sneak`, `cmd_charge`, `cmd_goal_x/z`, `cmd_aim_x/z` (null at
t = 0). Schema 2 adds `cmd_self_destruct` (also null at t = 0), `sniper` (0/1),
`radar_until` and `mister_until` (absolute expiry tick, 0 when absent).

### `team_states` (same sampling)

`t`, `meter_ticks_0/1`, `glory_0/1`, `team_lives_0/1`, `cogs_out_0/1`, `hearts_owned_0/1`,
`winner`.

### `heart_states` (same sampling)

`t`, `heart`, `owner` (-1 neutral), `capture_team` (-1 idle), `capture_ticks`, `contested`.

### `visibility` (only with `--vis-every M`)

`t`, `seat`, `sees` (list of seats this seat can see: the engine's `visible()`, cone + line of
sight or team grid). Cost is ~1 ms per sampled tick. BASIC also sees disguised enemies as
the other team, which `visible()` does not model.

### `policy_log` (our seat logs only)

`seat`, `t`, `line_kind`, `raw`, `fields`, `file`, `line_no`. Read from `*.log` under the
episode directory whose name carries the seat (`policy_agent_N.log`, `player-N.log`,
`seat-N.log`). `line_kind`:

- `log_present`: one marker per parsed file, so "no errors" differs from "no log".
- `intent`: a line starting `PWI ` (intent telemetry; format in [pw_intent.md](pw_intent.md)). Parsed
  as `key=value` tokens into `fields` (JSON); `t` from `t=`.
- `vm_error`: a line containing `BASIC error:` (the seat's VM was disabled).

League episodes without our policy have no seat logs, so `policy_log` is empty.

## Python API

```python
import sys; sys.path.insert(0, "paintbot_pw_lab/tools")
import pw_episodes as pe, pw_metrics as pm

batch = pe.load_batch(Path("paintbot_pw_lab/episode_data/<batch>"))   # -> Batch
batch.episodes            # list[Episode]; Episode["shots"] -> DataFrame, .meta, .summary
batch.failures            # [(path, code, message)]: never silently dropped
batch.exclusions          # Counter of codes: no_replay, bad_tape, trace_failed, identity, results_mismatch
batch.table("damage")     # one table across the batch
ep = pe.load_episode(Path(".../episode_dir"))                           # one episode, raises EpisodeError
con = pe.open_duckdb(batch)          # or roots: views named like the tables, over cached episodes
con.execute("select s.policy_key, count(*) from shots join seats s using (episode_id, seat) group by 1").df()

pm.seat_metrics(ep); pm.policy_metrics(ep); pm.team_metrics(ep)          # DataFrames
pm.batch_metrics(batch)   # {"seat": ..., "policy": ..., "team": ...}
pm.METRICS                # name -> (level, unit, definition, exact|inferred|sampled)
```

Options: `load_batch(roots, binary=None, tag=None, options=pe.TraceOptions(state_every=6,
vis_every=0, window=None), refresh=False, jobs=None)`. The trace build defaults to
`tools/bin/<PW_RELEASE_TAG>/pw_trace` (the tag in `tools/release.env`, via `tools/pw_release.py`); a newer build replays older rules hash-exactly, so the
current tag serves every recording it accepts. A tape newer than the build fails as
`trace_failed`: build the newer tag.

CLI: [pw_episodes.md](pw_episodes.md), [pw_metrics.md](pw_metrics.md).

Rules-49 trace schema 2 / table version 3 distinguish `self_destruct` from `grenade` in
damage/kills and add a `self_destruct` event. New pickup kinds are `mister`, `sniper`,
`radar`. Inferred aim targets/range bins remain uncalibrated under rules 49.
