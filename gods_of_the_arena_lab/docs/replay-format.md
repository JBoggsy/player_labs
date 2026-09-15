# Gods of the Arena replay format and expander design

> **Currency.** Format and re-simulation verified against the deployed polyworld `5422fb0c`
> (see the table below) using one downloaded league episode. **Re-verify when** `tools/deployed_ref.py`
> reports a new commit: the replay format version in `replays.nim`, the action record layout, and
> whether a re-simulation at the new commit still reproduces an episode's hash line. Rendered report:
> [`docs/reports/gota-replay-format-2026-09-15.html`](../../docs/reports/gota-replay-format-2026-09-15.html).

Investigation report (2026-09-15). What a hosted GotA replay actually contains,
how it is produced, what can and cannot be recovered from it, and a proposed
`gota_lab` replay expander in the shape of the Crewrift / Heartleaf / CTF tools.

Everything marked **verified** was checked against the polyworld source at the
commit the live game is built from, against a real league replay downloaded from
the Observatory, or both. **Inferred** items are reasoned from source but not
exercised.

| Evidence | Value |
| --- | --- |
| Live game version | `2026.9.15.1` (`GET /v2/coworlds/cow_252fb6a6-…` → `version`) |
| Live source commit | [`5422fb0c`](https://github.com/Metta-AI/polyworld/tree/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena) (`manifest.game.runnable.source_url` on the same endpoint) |
| polyworld `main` at time of writing | `1d7eb723` (2026-09-15T19:23Z) — **diverges** from the live build, see §1.4 |
| Sample episode | `ereq_9aa9fcd9-b288-42aa-bc37-70f9b736e9d9`, Competition division, completed 2026-09-15T19:46Z, time-limit draw, 291,325 recorded actions |

All polyworld links below point at `5422fb0c`. Line numbers are for that commit;
re-check with `grep -n` when the source moves.

---

## 1. Where replays come from and the exact format

### 1.1 Producer (verified)

The hosted game runs the headless polyworld binary compiled with `-d:coworld`.
The runner hands it `COGAME_SAVE_REPLAY_URI`; the game records an in-memory
**action tape** during the match and writes it once at the end:

- Path plumbing: [`src/polyworld/coworld.nim:280`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/src/polyworld/coworld.nim#L280)
  (`replayPath = localPath(getEnv("COGAME_SAVE_REPLAY_URI"))`).
- Recorder created per match: [`examples/gods_of_the_arena/game.nim:144`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/game.nim#L144)
  (`initReplayRecorder(currentSetup(...))`) and the hosted `GotaConfig` is copied
  into the tape at `game.nim:147-149`.
- Written at the end: [`game.nim:229` `saveRecording`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/game.nim#L229)
  → [`replays.nim:285` `saveReplay`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/replays.nim#L285).
- `finishCoworld` refuses to publish results if the replay file does not exist
  ([`coworld.nim:329`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/src/polyworld/coworld.nim#L329)),
  so every completed episode has a replay.

The Observatory serves it two ways (verified on the sample episode):

- `episode.json.replay_url` → `https://softmax-public.s3.amazonaws.com/replays/<job>.replay`
  (public S3, raw bytes). The manifest declares `replay_viewer.replay_compression: "gzip"`,
  and polyworld's own inspector tolerates a gzip prefix
  ([`tools/herostats.nim:162`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/tools/herostats.nim#L162)),
  but the bytes we received were **uncompressed**.
- `/v2/episode-requests/{id}/artifacts/replay`, which is what
  `.claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py` uses. It
  saved 6,119,872 identical bytes as both `replay.json.z` and `replay.json`
  (its zlib attempt fails silently and falls back to the raw blob). **The file
  named `replay.json` is not JSON**; treat it as `replay.bin`.

### 1.2 Container format (verified)

A GotA replay is the generic polyworld tape container
([`src/polyworld/tapes.nim`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/src/polyworld/tapes.nim)):
a tiny hand-written header followed by a [Flatty](https://github.com/treeform/flatty)
(`0.4.0`, `-d:flatty64`) serialization of one Nim object. There is no
compression, no per-tick state, and no event log.

```
offset  size  field                              value in sample
0       15    magic                              "POLYWORLDREPLAY"          tapes.nim:11
15      u16   file format version                1                          tapes.nim:12
17      u16   game version                       33                         replays.nim:15
19      u16   game name length                   17
21      n     game name                          "gods_of_the_arena"        replays.nim:11
21+n    …     Flatty payload: ActionTape[Setup, ReplayAction, ReplayMetrics, GotaConfig]
```

Payload layout (Flatty writes object fields in declaration order; `int` and
`seq` lengths are 8-byte little-endian; enums are 8 bytes; bool is 1 byte;
**a `seq` of a plain-data object is a raw `memcpy` of the Nim struct, padding
included** — `flatty.nim:464-472`):

| Field | Type | Bytes / notes | Source |
| --- | --- | --- | --- |
| `header.formatVersion` | u16 | 5 | [`replays.nim:12`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/replays.nim#L12) |
| `header.gameVersion` | u16 | 33 | `replays.nim:15` |
| `header.createdUnixMs` | i64 | | [`tapes.nim:183`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/src/polyworld/tapes.nim#L183) |
| `header.setup` | `Setup` | `mapSeed i32, mapHash u64, tickRate u16, gridTiles u16, spawnIntervalTicks u32, maximumTicks u32, heroes seq[ReplayHero]` | [`replays.nim:37`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/replays.nim#L37) |
| `ReplayHero` | 8 bytes each | `id i32, team u8, slot u8, lane u8, class u8` | `replays.nim:30` |
| `config` | `GotaConfig` = `MatchConfig[MapConfig]` | `players seq[{name string}], seed i32, maxTicks i32, spawnIntervalTicks i32, playerSlot i32, dayCount i32, mapPreset` | [`configs.nim:16`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/src/polyworld/configs.nim#L16), [`presets.nim:10`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/presets.nim#L10) |
| `MapConfig` | | `mapSize i64, seed i64, lakeCrossings i64, jungleRoads i64, 9 × f32, campsTouchRoads u8` | [`generation/configs.nim:10`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/generation/configs.nim#L10) |
| `actions` | `seq[ReplayAction]` | count i64, then **20 bytes each**: `tick u32 @0, heroId i32 @4, kind u8 @8, 3 pad, first i32 @12, second i32 @16` | [`replays.nim:46`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/replays.nim#L46) |
| `hashes` | `seq[uint64]` | one canonical state hash per completed tick | `tapes.nim:190-193` |
| `metrics` | `ReplayMetrics` | `tickRate i32, interval i32, frames seq[{tick i32, rows seq[{cpu i32}]}], final seq[{cpu i32}]` | [`metrics.nim:27`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/src/polyworld/metrics.nim#L27) |

Action `kind` codes ([`replays.nim:16-23`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/replays.nim#L16)):

| kind | meaning | `first`, `second` |
| --- | --- | --- |
| 1 | `walkTo` | tile x, tile y |
| 2 | `attackTarget` | object id, – |
| 3 | `buyItem` | item id (`Item` enum ordinal, [`content.nim:82`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/content.nim#L82)), – |
| 4 | `useItem` | inventory slot 0–5, – |
| 5 | `attackMove` | tile x, tile y (human/graphical client only; never emitted by BASIC) |
| 6–9 | `castTarget` slot 0–3 | object id, – |
| 10–13 | `castPoint` slot 0–3 | tile x, tile y |
| 14 | `manualSpells` | 1 = human seat (only written when a human plays) |

A pure-Python decoder of this layout parses the sample replay and the in-repo
`examples/gods_of_the_arena/replays/demo.replay` to the exact last byte, and the
last entry of `hashes` (`0x320ad325`) equals the `hash:` line in the episode's
`game_logs.log`. (Prototype: `gota_replay_probe.py` in this session's scratchpad;
about 60 lines of `struct` calls, worth lifting into the lab as-is.)

Decoded sample header for reference:

```
setup:   map_seed 223226943, map_hash 0x29424656, tick_rate 24, grid 116, spawn 240, max 28800
heroes:  id 100-104 team 0 (Red) classes DeathKnight, Crossbowman, Lich, Warlock, Berserker (lanes 0,0,1,2,2)
         id 105-109 team 1 (Blue) classes VanguardKnight, Ranger, Arcanist, DruidWarden, DemonHunter
players: ['Andrew Brower', 'richard', 'Games Bond', 'daveey-2', 'docxology', 'Andrew Brower B', 'relh', 'Andre von Auto', 'daveey', 'Andre von Houck']
actions: 291,325  (attackTarget 180,166 · walkTo 85,632 · useItem 15,371 · buyItem 10,156 · 0 casts)
hashes:  28,800   metrics: 1,201 CPU frames at 24-tick interval + 10 finals
```

Note `config.players[].name` is the **public player display name**, so the
replay itself tells you who sat where (hero id 100 + slot = seat 0..4 Red, 105 +
slot = seat 5..9 Blue; `episode.json.participants[].position` is the same order).

### 1.3 What "replay" means here (verified)

The tape stores only **requests** (each BASIC action call, recorded *before* the
engine accepts or rejects it — [`bots.nim:186-207`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/bots.nim#L186))
plus one hash per tick. Playback **re-runs the full simulation** and re-applies
the recorded requests at their ticks through the same validators
([`sim.nim:2306` `applyReplayAction`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/sim.nim#L2306),
called from [`tickWorld` `sim.nim:2830`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/sim.nim#L2830)),
checking `stateHash` against the recorded hash every tick
([`sim.nim:2692`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/sim.nim#L2692)).
This is the same design as the bitworld `.bitreplay` used by Crewrift/Heartleaf,
so everything in [`crewrift-replays.md`](../../crewrift_lab/docs/crewrift-replays.md)
about version coupling applies.

### 1.4 Version coupling — and how to find the right build (verified)

`ReplayGameVersion` (33) is **not** sufficient to pick a compatible sim. Built at
polyworld `main` (`1d7eb723`, also version 33), the sample replay diverges at
tick 132 (28,669 mismatches) and even the in-repo `demo.replay` diverges at tick
135 — three sim-affecting PRs (tower collision, creep lane resume, creep
upscale) merged after the live build without a version bump. Built at
`5422fb0c`, both replays re-simulate with **zero mismatches** on this arm64 Mac,
and the headless summary reproduces the hosted game log exactly:

```
result: time limit
forts: red 400 hp, blue 400 hp / towers: red 4, blue 5
hash: 00000000320AD325 map 0000000029424656
heroes: red L13 L13 L8 L3 L12, blue L10 L10 L9 L10 L9
economy: red 21200 XP / 635 gold, blue 18950 XP / 680 gold
replay: 291325/291325 actions          (24 s wall clock for 28,800 ticks)
```

Two consequences:

1. **The correct ref is discoverable, not guessed.** `GET /v2/coworlds/{coworld_id}`
   returns `manifest.game.runnable.source_url` =
   `https://github.com/Metta-AI/polyworld/tree/<sha>/coworld/gota`. The build
   script should resolve `GOTA_REF` from that (with `episode.json.coworld_version`
   as the cache key), the way `CREWRIFT_REF`/`HEARTLEAF_REF` are pinned today but
   automatically. Polyworld's own policy is "older replays use their archived
   client; never add compatibility branches" (`replays.nim:13-14`), and the
   `replays.nim` history shows 12 commits in five days, so expect frequent
   re-pins.
2. **arm64 host builds are deterministic enough.** Map generation uses `float32`
   presets, yet the map hash and all 28,800 tick hashes matched. The
   `validateReplayWorld` check ([`sim.nim:1091`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/sim.nim#L1091))
   also passed, so no Docker/amd64 is needed for expansion. (One sample; keep the
   hash check as the guard.)

Build recipe that worked (no credentials; `nim` 2.2.6 and `nimby` already in `~/.local/bin`):

```sh
curl -fsSL https://github.com/Metta-AI/polyworld/archive/$REF.tar.gz | tar xz -C src --strip-components=1
cd src && nimby --global sync nimby.lock          # writes nim.cfg with dependency paths
nim c -d:headless -d:release --out:../gota_headless examples/gods_of_the_arena/gota.nim
../gota_headless --replay replay.bin              # hash-checked; non-zero exit on divergence
```

### 1.5 The other artifacts of an episode (verified)

| File | Content |
| --- | --- |
| `results.json` | `{"scores":[10 × 0/1],"ticks":28800,"seed":…,"outcome":"time_limit" \| "RedTeam" \| "BlueTeam","banked_gold":[],"returned":[],"total_xp":[10 ints]}` — [`gota.nim:9-14`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/gota.nim#L9), [`coworld.nim:41`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/src/polyworld/coworld.nim#L41). `banked_gold`/`returned` are CTA fields, always empty for GotA. |
| `game_logs.log` | Container stdout. The `game` section is the headless summary: `replay saved … (N actions)`, `result`, `forts`, `towers`, `hash`, `heroes` (levels), `economy` (team XP / unspent gold), `scripts: 10/10 active, N decisions` ([`game.nim:243`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/game.nim#L243)). Cheap end-of-game signal without touching the replay; note `scripts: 10/10 active` tells you whether any VM died. |
| Per-seat private log | Only for seats you own. Contains `Player slot N started.`, every BASIC `PRINT`, `BASIC error: …` on VM failure, `Player slot N completed.`; capped at 10 MiB ([`coworld.nim:141-175`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/src/polyworld/coworld.nim#L141)). No tick stamps unless the policy prints `worldTick` itself. Fetch: `/v2/episode-requests/{id}/{policy_version_id}/policy-logs/{position}`. On the sample episode the `games-bond-gota` seat returned `403 You do not own this policy` under the current login — that policy belongs to the "Games Bond" player identity (see the `coworld-player-swap` skill). |
| Player artifact ZIP | Not produced by GotA (`integration.md`: "No player artifact ZIP is produced"). |
| `episode.json` | Discovery row: `participants[] {position, policy_name, version, policy_version_id, player_name, is_filler}`, `participant_scores`, `coworld_version`, `replay_url`, `inspect_url`. |

---

## 2. Inventory: what is recorded and what is recoverable

### 2.1 Directly in the file (no re-simulation)

- **Per action** (every BASIC action call, accepted or not): tick, hero id,
  kind, arguments. That gives command rates, target choices (object ids only —
  no positions), shop requests, item-use requests, cast requests, and the tick
  each hero's VM was still issuing calls (a VM that died stops appearing).
- **Per second, per seat**: CPU% (instructions used / 20,000 budget) in
  `metrics.frames`; lifetime average in `metrics.final`. `-1` = no VM (human seat).
- **Per episode**: seed, map preset, hero roster (id/team/slot/lane/class), player
  display names, recorded duration (`len(hashes)`), creation time.
- **Not in the file**: acceptance of any action, positions, HP, gold, XP, level,
  kills, deaths, damage, item inventories, ability charges, structure HP, fog.

### 2.2 Recoverable by re-simulation (verified reachable in `World`)

Re-running the sim gives complete authoritative state at every tick:

| State | Where | Notes |
| --- | --- | --- |
| Hero position (world units, `WorldScale = 60,000` per tile), facing, nav layer | [`Hero` `sim.nim:90`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/sim.nim#L90) | `mapCoordinate(pos.x)` = tile x as BASIC sees it |
| HP/maxHp, mana/maxMana, level, xp, totalXp, gold | `Hero` | `gold` is unspent; earned gold is `stats.values[slot][GoldMetric]` |
| State (`Marching/Fighting/Dying`), current targets (`targetFootmanId/HeroId/TowerId`, `attackingFort`), `attackObjectId`, move path & target | `Hero` | "what the engine is actually doing" vs. what the script asked |
| Inventory (6 × item enum + counts), ability cooldowns/charges/recharges | `Hero` | |
| Footmen (id, team, lane, position, HP, state, target) | `Footman` `sim.nim:67`; `UnitCap = 120` | |
| Towers (id, team, lane, tier, position, HP, target), forts (HP 400 at start of siege) | `sim.nim:138-154` | |
| Live spell casts (`ability, heroId, targetId, origin, position, started/impact/ends, resolved`) | [`SpellCast` `sim.nim:171`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/sim.nim#L171), `world.casts` | includes the engine's **automatic** casts, which are never in the tape |
| Team vision / explored tiles | `world.teamVisible`, `teamExplored` `sim.nim:204-205`, rebuilt each tick ([`rebuildVision` `sim.nim:509`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/sim.nim#L509)) | lets you say "was the target visible when the script attacked it" |
| Combat counters per seat: gold earned, kills, deaths (`LossesMetric`), assists (10-second damage window) | `world.stats` (`CombatStats`, [`metrics.nim:81` `hitHero`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/src/polyworld/metrics.nim#L81)) | hashed with the world, so guaranteed to match the live game |
| `teamHeroKills`, `teamHeroDeaths`, `gameOver`, `winner` | `World` | |
| Accepted commands per seat (APM) | `game.metrics.command` in `tickWorld` | acceptance is recomputed on playback |

Reward accounting is exact and event-attributable at the hit site
([`applyHeroHit` `sim.nim:1856`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/sim.nim#L1856)):
footman kill +25 XP/+15 gold, hero kill +150/+100, tower kill +100/+75
(`sim.nim:357-362`); fort damage awards nothing. Spell strikes go through the
same proc ([`hitSpellTarget` `sim.nim:2031`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/sim.nim#L2031)),
so spell kills are credited. Tower and footman damage to heroes calls
`hitHero(-1, …)` (`sim.nim:1641`, `1775`) → a death with no killer seat.

### 2.3 Existing prior art in polyworld (verified)

Polyworld already ships a minimal re-sim extractor for its tournament tool:
[`tools/herostats.nim:157` `inspectReplay`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/tools/herostats.nim#L157)
+ [`tools/inspect_players.nim`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/tools/inspect_players.nim).
It replays the tape, refuses any hash mismatch, cross-checks `scores()` against
`participant_scores`, and emits **end-of-game** per-seat JSON: `hero, class,
team, win, draw, level, xp, xp_progress, gold (earned), banked_gold, kills,
deaths, assists`, then derives `tower_kills` and `last_hits` from the exact
reward arithmetic ([`tournaments.nim:265` `objectiveCounts`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/tools/tournaments.nim#L265)).
It is end-state only (no timeline, no positions, no events), and it imports
`curly`/`zippy`/`jsony` for the tournament runner. It is the right thing to
**copy the loop from**, not to depend on.

---

## 3. What is not recorded (gaps that limit analysis)

1. **No per-tick state in the file.** Anything beyond command counts needs the
   version-matched re-sim (§1.4). If a ref cannot be built (e.g. a source commit
   that no longer exists, or a private dependency change), the replay is opaque
   apart from the action stream.
2. **Requests, not effects.** `attackTarget(id)` in the tape does not mean the
   hero hit, or even approached, that target. Acceptance must be recomputed
   (the re-sim does this — `applyReplayAction` returns the accepted flag), and
   *effect* must be read from world state afterwards.
3. **No damage or healing totals.** GotA never writes `DamageMetric`,
   `HealingMetric`, `ArmyMetric`, `BankedMetric` or `StructuresMetric` (grep of
   `examples/gods_of_the_arena/*.nim`; polyworld's own report says "Damage and
   healing totals are not tracked … and are not reported as zero"). They are
   trivially recoverable by hooking `applyHeroHit` in the expander, but nothing
   in the file or the stock tools has them.
4. **No per-hit attribution for tower/creep damage.** `hitHero(-1, …)` records a
   hero death by a non-hero source without saying tower vs footman; the expander
   sees the call site, so it can tag it.
5. **Automatic ability casts are invisible in the tape** (they happen inside
   `updateHero` → `tryCastAbility`). Recoverable from `world.casts` during
   re-sim only.
6. **No policy-side reasoning.** PRINT output is private to the seat owner and
   only for seats you own; other entrants' logic is opaque. For our own seats,
   the private log is the only "why" channel and it has no tick stamps unless
   the policy prints `worldTick`.
7. **No wall-clock or scheduling data** beyond `createdUnixMs`.
8. **Visibility is derivable but not recorded.** Whether an enemy was visible to
   a hero at a tick has to be recomputed from `teamVisible`; nothing in the tape
   says what the script saw.
9. **Tooling mismatch in the shared downloader.** `fetch_artifacts.py` labels the
   binary tape `replay.json`; anything that assumes JSON breaks. A `replay_bytes`
   sniff (magic `POLYWORLDREPLAY`) or a game adapter hook is needed.

---

## 4. Proposed design: `gota_lab` replay expander

### 4.1 Shape — the same three-layer pattern as Crewrift/Heartleaf

```
replay.bin ──(A) Nim expander (re-sim, version-matched)──▶ expanded.jsonl
           ──(B) Python decoder (actions + CPU only, version-free)──▶ actions table
expanded.jsonl ──(C) Python analysis: stats tables, compare.py, features.py, heatmaps
```

Layer **B** exists in prototype form (the 60-line `struct` decoder) and never
needs rebuilding — it is the fallback when a ref will not build, and it is
enough for command-rate, shop and targeting-policy questions. Layer **A** is
where the value is. Layer **C** is plain Python over JSONL/Parquet, matching
how `crewrift-event-warehouse` and `heartleaf_lab/tools/viz_replay.py` work.

Module layout (mirrors `heartleaf_lab/tools/`):

```
gods_of_the_arena_lab/
  tools/
    build_expand_replay.sh      # resolves GOTA_REF from /v2/coworlds/{id} (cache by coworld_version),
                                #   tarball fetch, nimby sync, host-native nim c; caches bin/expand_replay-<ref>
    expand_replay.nim           # OUR file, compiled against the fetched polyworld tree (see 4.2)
    bin/expand_replay-<ref>     # gitignored
    replay_actions.py           # layer B: pure-Python tape decoder (lifted from the prototype)
    replay_stats.py             # layer C: expanded.jsonl -> per-hero / per-team tables (markdown + JSON)
    viz_replay.py               # layer C: paths / heatmaps on the tile grid (Pillow, like heartleaf's)
  .claude/skills/gota-ab/scripts/compare.py                # coworld-ab adapter
  .claude/skills/gota-hypothesis-miner/scripts/features.py # miner adapter
  docs/replay-format.md         # this file; becomes the reference once the tools exist
```

`expand_replay.nim` lives in **our** repo (polyworld has no such tool) and is
compiled with the polyworld source on the `--path`; it imports
`polyworld/[tapes, metrics]` and `examples/gods_of_the_arena/[content, maps,
replays, sim]` exactly as `herostats.nim` does. It stays a ~300-line file: the
`herostats.nim` loop plus per-tick emission plus a few diff-based event
detectors. Because it compiles against whichever ref the build script fetched,
it inherits polyworld's "one client per gameplay version" rule automatically;
if a future polyworld commit renames a field we get a compile error, not silent
wrong data.

### 4.2 Expander core loop (inferred from `herostats.nim`, not yet written)

```nim
let data = decodeReplay(bytes)                       # gzip sniff like herostats
let game = newGame(generateMap(data.config.seed, data.config.mapPreset),
                   data.config.spawnIntervalTicks, 0, true, data)
game.replayPlayer = initReplayPlayer(data); game.historyPlayback = true
emit meta row
while game.world.tick < data.hashes.len:
  snapshot previous world (clone or copy the fields we diff)
  game.tickWorld(nil)                                 # applies tape actions, checks hash
  diff previous vs current -> events; every N ticks -> state rows
require game.hashCheck.mismatches == 0 (else summary.hash_failed = true, exit non-zero)
emit summary row
```

Events derived **by diffing** state between ticks (no engine changes needed):

| Event | Detection | Fields |
| --- | --- | --- |
| `action` | each tape action consumed this tick, with the `applyReplayAction` result | `slot, kind, args, accepted` — requires calling the validators ourselves or re-reading `game.metrics` command delta; simplest is to consume actions in our loop and call `applyReplayAction` directly, mirroring `tickWorld`'s branch |
| `hero_death` / `hero_respawn` | `hp > 0 → ≤ 0` (state `Dying`), then `hp` back > 0 at spawn | `slot, tick, pos, killer_slot` (from `stats.values[KillsMetric]` delta that tick; `-1` if tower/creep) |
| `hero_kill`, `assist` | per-seat `KillsMetric` / `AssistsMetric` delta | |
| `last_hit` (footman), `tower_kill` | XP/gold delta decomposed by the exact reward table (25/15, 150/100, 100/75) — the same arithmetic `objectiveCounts` uses, but per tick so it is unambiguous | `slot, kind, tick` |
| `tower_destroyed`, `fort_damaged`, `fort_destroyed` | tower/fort HP transitions | `team, lane, tier, tick` |
| `level_up` | `level` delta | |
| `gold_spent` / `item_bought` / `item_used` | inventory diff + gold drop on the tick a `buyItem`/`useItem` was accepted | `slot, item, cost` |
| `cast` | new entry in `world.casts` | `slot, ability, slot_index, target/point, auto (not in tape at that tick) vs explicit` |
| `damage` | **Stub until change request 6 lands.** The engine keeps no per-hit record, so per-attacker damage is not diff-derivable and the expander must not patch the simulator to get it. Emit `damage` as a placeholder event type with no rows, documented as blocked on [requested game change 6](requested-game-changes.md) (damage/heal events in the recording). The victim-side `hp` delta per tick is still available through `objective_state`. Fill this row in as soon as the change ships. | `tick, source, target, amount, cause` (reserved) |
| `objective_state` (sampled) | every `--snapshot-every N` ticks: all hero rows (pos, hp, mana, gold, level, state, target ids, inventory, cooldowns), tower/fort HP, footman counts per lane per team | the positions/heatmap feed |
| `visibility` (sampled) | for each hero: count of enemy heroes visible, enemy structures exposed | answers "did it attack something it could see" |

Output contract, one JSON object per line, `type` ∈ `meta | action | event |
state | summary`, all with `tick`; seat-tagged rows carry `slot` (0–9 platform
seat = hero index) and `hero_id`. Positions in **tile units** (`mapCoordinate`)
plus raw world units, so they line up with what BASIC sees and with the
`terrain*` grid. Same conventions as Heartleaf's rows (`meta`/`tick`/`event`/
`summary`), so `viz_replay.py` is a near copy.

### 4.3 Stats tables (layer C)

Per hero (one row per seat per episode) — the columns polyworld's tournament
already defines, plus the timeline-only ones:

`slot, team, class, policy_name, version, player, win, draw, level, total_xp,
gold_earned, gold_unspent, kills, deaths, assists, last_hits, tower_kills,
damage_taken, first_death_tick, time_dead_ticks, first_tower_kill_tick,
first_fort_hit_tick, apm, cpu_pct, vm_failed_tick, actions_by_kind{…},
casts_explicit, casts_auto, items_bought{…}, ticks_in_enemy_half, mean_distance_to_nearest_ally, …`

Per team: `towers_lost_by_lane, fort_hp_min, first_tower_kill_tick,
first_fort_hit_tick, hero_kills, hero_deaths, xp, gold, outcome`.

Per episode: `outcome, ticks, minutes, coworld_version, replay_ref,
hash_verified, seed, map_seed`.

### 4.4 Slotting into the shared adapters

- **`coworld-ab` adapter (`compare.py`)** — needs only `results.json` +
  `episode.json` for the headline metrics and nothing else: `win` (from
  `participant_scores`), `total_xp[position]`, `outcome == time_limit` (draw
  rate). `by_group` should be `{red, blue}` at minimum and probably
  `{class}` — GotA fixes the class per seat (seat 0 is always DeathKnight, etc.),
  so a policy's numbers are confounded by which seats it drew; grouping by class
  is the honest split (`RedHeroClasses`/`BlueHeroClasses`,
  [`content.nim:123`](https://github.com/Metta-AI/polyworld/blob/5422fb0c4b230ca7bfa57a69e450a369da2dabe9/examples/gods_of_the_arena/content.nim#L123)).
  Timeline metrics (`first_tower_kill_tick`, `deaths`, `last_hits`) come from
  `replay_stats.py` output joined on `(episode_id, position)`; the adapter should
  accept an optional `--expanded DIR` and fall back to results-only metrics.
- **`coworld-hypothesis-miner` adapter (`features.py`)** — one row per
  (episode, own seat); features straight from the per-hero table with the
  "never happened = LAST_TICK+1" rule for timings (`first_death_tick`,
  `first_tower_kill_tick`, `first_fort_hit_tick`), presence flags (`bought_X`,
  `cast_ultimate`), counts (`last_hits`, `deaths_to_towers`). Score = the seat's
  `total_xp` minus the time penalty the ladder uses (100 XP per simulated
  minute, per polyworld `USAGE.md`) or plain win, chosen per question.
- **Warehouse** — if we accumulate many episodes, the Crewrift event-warehouse
  pattern (Parquet + DuckDB) applies unchanged; the expander's JSONL is its input.

### 4.5 Cost

Expansion is ~24 s per 20-minute episode on this machine (single-threaded;
the sim runs 49× real time). A 20-episode experience request expands in under
a minute with four workers (the sim has module-level globals — `herostats.nim`
runs one process per replay for this reason; do the same).

---

## 5. Open questions

1. **Ref resolution for old episodes.** `/v2/coworlds/{id}` gives the *current*
   version's source commit. For an episode with an earlier `coworld_version`
   we need a version→commit map; polyworld keeps receipts in
   `coworld/releases/*.json` (`source_commit`), but only for some releases and
   not for `2026.9.15.1` yet. Cache `(coworld_version → sha)` locally as we
   observe them and fail loudly otherwise.
2. **Damage attribution** is blocked on [requested game change 6](requested-game-changes.md): damage and heal events recorded by the engine. Until then `damage` is a stub and `features.py` must not build on "damage dealt".
3. **The Nim expander is required for the first iteration** (decided 2026-09-15). Layer B alone gives aggregates and unaccepted action requests, which is not enough. The expander must also emit, per tick and per bot, what that bot could observe under fog of war (the team visibility map and the visibility-filtered object list) so we can tell what each policy knew when it acted.
4. **Own-seat private logs**: the `games-bond-gota` seat is owned by the
   "Games Bond" player identity; the current `softmax login` is not that
   identity (403 "You do not own this policy"). Confirm which identity owns the
   policy we will iterate on before relying on PRINT traces.
5. **Downloader naming.** Fix `fetch_artifacts.py` to sniff the
   `POLYWORLDREPLAY` magic and save as `replay.bin` (or leave `replay.json` and
   document it). Small, shared-skill change — needs a go-ahead because it
   touches the root tooling.
6. **arm64 determinism** is verified on one episode. Keep the hash check
   mandatory; if a mismatch ever appears with the correct ref, that is the
   signal to fall back to a `linux/amd64` container build.
