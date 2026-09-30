# Paintbot PW policy surface: what a script can know and do

> **Currency.** Verified 2026-09-29 against Metta-AI/paintbot-pw commit `d0728ab1` (tag
> `coworld-v0.3.79`), coworld `paintbot-pw` 0.3.79, the build the league runs that day.
> Recordings are stamped rules 48, whose only change is FFA-kin fog, so the teams game plays
> rules 47. Every `file:line` citation is at `d0728ab1`, not `main`, including the neural lane
> (§1, §4, §5.10), which 0.3.79 rewrote (`neural_host.nim`, `neural_contract.nim`,
> `neural_actor.nim`, `neural_package.py`, `neural_basic.md`, `neural_actor.md`; commit
> `5db6058`). The BASIC dialect, host API, limits and oracle did not change in 0.3.79
> (`basic.nim`, `oracle.nim`, `oracle.py`, `game.nim` identical to 0.3.78; `bots.nim` changed
> only `-d:pwTraining` arrays). Re-verify when the coworld version changes (`pw.py
> deployed-ref`): diff `examples/paintbot/bots.nim` (host API and limits),
> `src/polyworld/basic.nim` (dialect), `examples/paintbot/oracle.nim`,
> `examples/paintbot/neural_host.nim` and `neural_contract.nim`,
> `coworld/paintbot/runtime/host.py` and `neural_package.py` (upload staging).

Paths are relative to the repo root; `bots.nim`, `oracle.nim`, `neural_host.nim`,
`neural_contract.nim` and the neural `.md` references are under `examples/paintbot/`, `basic.nim` and `coworld.nim` under `src/polyworld/`, `host.py` and
`neural_package.py` under `coworld/paintbot/runtime/`. Rules and numbers of the game itself are in
[mechanics.md](mechanics.md). Starter policies are in `../reference/` (Heartland's in
`../reference/heartland/`).

## 1. Upload formats

The pod entrypoint is `python /runtime/host.py` (`coworld/paintbot/Dockerfile`). It stages each
seat's file before the engine starts (`host.py:99-124`):

| Format | Detected by | Limits | Staging |
| --- | --- | --- | --- |
| Raw BASIC | anything not a ZIP | UTF-8, at most 128 KiB, not WASM (`host.py:43-53`) | written as the seat's source |
| Neural BASIC ZIP | starts with `PK\x03\x04` | exactly `manifest.json` (8 KiB), `policy.bas` (128 KiB), `model.bin` (16 MiB); no encryption (`neural_package.py:11-13`, `765-781`) | manifest schema `paintbot-neural-basic/1` or `/2`, SHA-256 of both payloads must match, contract hashes, decoder options and user inputs validated, and a PWNET002 model's structure and operation budget checked for the match's seat count (`neural_package.py:782-875`; the host passes the seat count, `host.py:105`). Writes `policy.bas` plus `.model.bin` / `.neural.json` sidecars (`neural_package.py:878-883`) |

WASM is no longer accepted (`host.py:45-46`). There is no other format. Any staging failure,
including a rejected neural package, forfeits only that seat (§4). The host refuses a roster
of fewer than 2 or more than 256 seats (`host.py:89-90`, since 0.3.76); the `paintbot-pw` manifest's config
schema still requires exactly 16 `tokens`, so every paintbot-pw match has 16 seats.

## 2. The BASIC dialect (`basic.nim`)

One file controls one cog. Every seat (16 in paintbot-pw) gets a separate VM with **no shared
memory** (`bots.nim:396-421`). The only cross-seat channel is speech.

| Feature | Behavior | Evidence |
| --- | --- | --- |
| Reserved words | `and call dim else end exit false gosub goto if let mod not or print rem return stop sub then true wend while xor`. `goto`/`gosub` are reserved but not statements. | `basic.nim:551-559`, statement dispatch `1706-1774` |
| Not present | `FOR/NEXT`, `DO/LOOP`, `SELECT`, `ELSEIF`, `FUNCTION`, built-in math (`ABS`, `SQR`, `RND`, `MIN`...). Write loops with `WHILE`, math yourself. | dispatch `1706-1774` |
| Values | signed int32 only; `+ - *` wrap on overflow; `/` and `MOD` truncate toward zero; divide by zero is a **runtime error**. `true`/`false` = 1/0. | `basic.nim:946-986`, `1061-1064` |
| Operators and precedence (low to high) | `OR XOR` < `AND` < `= <> < <= > >=` < `+ -` < `* / MOD` < unary `- + NOT`. Logical ops return 0/1 and always evaluate both sides. **`NOT` binds tighter than `=`**: write `NOT (a = b)`. | `basic.nim:1015-1035`, `1118-1172` |
| Case | Names and keywords are case-insensitive. | `basic.nim:351-353` |
| Separators | Newline or `:` ends a statement. `'` or `REM` starts a comment. | `basic.nim:392-399` |
| Variables | Scalars are global, created on first use, start at 0. Sub parameters are local; anything else assigned inside a `SUB` is global. At most **512 globals**. | `basic.nim:917-936`, `bots.nim:159` |
| Arrays | `DIM name(N)` at top level only, literal bound, inclusive (`DIM a(15)` = 16 cells). At most **4,096 elements in total** (and 256 arrays). Out-of-range index is a runtime error. | `basic.nim:677-706`, `1174-1183`, `bots.nim:159` |
| Control flow | `IF cond THEN` newline ... `[ELSE ...]` `END IF`; `WHILE cond` ... `WEND`. `THEN` must end the statement. | `basic.nim:1635-1687` |
| Subroutines | `SUB name(a, b)` ... `END SUB`, top level only; call as `name(x, y)` or `CALL name(x, y)`. No return values (a sub in an expression is a compile error): return results through globals, as `isqrt` sets `root` in `base.bas`. `RETURN` / `EXIT SUB` leave early. Call depth 16. | `basic.nim:713-779`, `1102-1107`, `1585-1602`, `bots.nim:159` |
| Strings | Literals only as `PRINT` text or as host-call arguments (compiled to a literal id, used by `strNew`). Everything else is int handles into a per-decision string pool (section 5.7). | `basic.nim:1489-1522` |
| Printing | `PRINT "a"; x, y` (`;` joins, `,` adds a space, trailing `;` suppresses the newline). **1,024 bytes and 128 print events per decision**; exceeding either is a runtime error. Output goes to the seat's private log (10 MiB cap per episode). | `basic.nim:1604-1631`, `2423-2430`, `bots.nim:160`, `coworld.nim:7`, `169-179` |
| Host data | Read-only names (section 5.1); assigning one is a compile error. | `basic.nim:1437-1448` |

## 3. Per-tick execution

- Every tick, before the world steps, each **living, non-disabled** seat runs its script once from
  the first line (`bots.nim:464-506`). Dead cogs do not run, so a script sees nothing while
  waiting to respawn.
- `restart()` clears registers and budgets but **keeps globals and arrays** (`basic.nim:2267-2279`).
  Persistent memory = globals and arrays. The idiom is `IF started = 0 THEN started = 1 ... END IF`
  for one-time setup (`base.bas:97-114`).
- The string pool is reset every decision; handles do not survive to the next tick
  (`bots.nim:494`, `basic.nim:2790-2798`).
- All seats decide against the same frozen world, then the world steps once with all commands
  (`game.nim:520-539`). Host reads during a decision never see another seat's action.
- `END`, `STOP` or falling off the end finishes the decision.

### Commands: what persists and what does not

Commands are cleared every tick (`bots.nim:468`), but the engine keeps some state on the cog
(`mechanics.nim:617-621`):

| Call | Persists? |
| --- | --- |
| `walkTo(x, y)` | **Yes**: sets the cog's goal, which it keeps walking to until a new `walkTo` (or a respawn resets goal to the spawn point, `sim.nim:781`). |
| `lookAt(x, y)` / `shootAt(x, y)` | The aim point persists; it is also the centre of the vision cone. A `walkTo` without any aim call this tick turns the aim to the walk goal (`mechanics.nim:619-620`). |
| `shootAt` (the trigger) | No; must be called on the tick you want to fire. |
| `chargeGrenade(1)` | No; charge is kept, but **not calling it (or calling it with 0) releases the grenade** that tick if charge > 0. |
| `sneak(1)` | No; call every tick you want to sneak. |

The aim sentinel is the point (0, 0): `lookAt(0, 0)` does nothing (`mechanics.nim:619`, **inferred**
edge case).

### Budgets per decision (`bots.nim:147-160`)

| Limit | Value |
| --- | --- |
| Source | 128 KiB |
| VM instructions | **50,000** |
| Work units | **125,000** |
| Memory | 2 MiB |
| Array elements (total) | 4,096 |
| Globals | 512 |
| Call depth | 16 |
| Print | 1,024 bytes, 128 events |
| String pool | 1,024 handles, 64 KiB, 1,024 bytes per string (`bots.nim:398-401`, `basic.nim:2745-2749`) |

Work units: most VM ops cost 1-9 (`basic.nim:1776-1809`); each host call costs the value in its
registration (listed in section 5). The budget is checked at the start of each basic block, so a
block that would overrun fails before it runs (`basic.nim:2447-2458`). `PW_BASIC_PEAKS=1` prints
per-seat peaks in a local run (`game.nim:552-557`). Measured at `d0728ab1` over 11 local
seeds: `base.bas` peaks at 9,116 instructions (18% of 50,000) and 15,538 work units (12% of
125,000); `jev.bas` without an oracle at 13,909 / 21,140. The guide's "5,670 / 8,722" (guide line
720) is out of date ([field analysis §8](reports/2026-09-29-league-field-analysis.md)).

Since 0.3.75 the instruction and work budgets scale with the seat count **above 16 seats only**
(`50,000 × seats / 16`, `bots.nim:156-158`), for crowd matches such as Heartland Big. At 16 seats
(every paintbot-pw match) they are exactly the numbers above.

## 4. Failure modes

| Failure | When | Consequence | Evidence |
| --- | --- | --- | --- |
| Host rejects the file (WASM, > 128 KiB, not UTF-8, a neural ZIP that fails its package checks, hash mismatch, failed download) | staging | Seat **forfeits**: replaced by an idle stub (`idle = 1`) for the whole episode; a player-failure record names the slot; the other 15 seats play on and the episode scores normally. | `host.py:96-124`, `31-40` |
| **BASIC compile error** (syntax, unknown name, calling an FFA-only function in the teams game, a limit exceeded at compile) | engine start | The engine writes a player-failure record naming the slot and **stops without writing results**: the whole episode fails for all 16 seats. | `bots.nim:417`, `coworld.nim:215-233` |
| Neural model rejected at load (dimensions, contract mismatch, over the operation budget, observation contract v3 in FFA-kin, or a fixed-width contract in a match that does not have exactly 16 seats) | engine start | Seat is marked failed and **never runs**, not even its BASIC. Its cog stands at spawn all match. | `bots.nim:404-415`, `420`, `neural_host.nim:597-622`, `641-694` |
| **Runtime error**: instruction or work budget exceeded, divide by zero, array index out of range, bad string handle, string pool full, print limit, call depth, a neural host call used wrongly | any tick | Seat is **disabled for the rest of the episode**. The error goes to the seat's log ("BASIC error: ...") and its status becomes "BASIC VM disabled". | `bots.nim:502-504`, `491`, `coworld.nim:181-184`, `197-209` |

What a disabled cog does afterwards (**inferred** from `mechanics.nim:616-623`): it issues no new
commands, but the engine keeps walking it toward its last `walkTo` goal and keeps its last aim. It
never shoots, charges or captures by intent. After its next death it respawns and stands still.
It still counts toward team lives, so it can be farmed for kills.

Practical rules: bound every `WHILE` loop by a constant or by 16 / `heartCount()`; guard every
division; keep `PRINT` to a few lines per tick; never read a string handle from a previous tick;
cap `strNew` and `heardText` use (each distinct `strNew` literal is interned once per tick, but
`heardText`, `strCat` and friends each allocate).

## 5. Host API

All values are int32. Coordinates are world units (1 unit = 1 cm); **"Y" is the second
horizontal axis** (the engine's `z`). Unless noted, a function costs 4 work units. Source:
`bots.nim:161-381`, plus `oracle.nim:247-340`, `basic.nim:3003-3093`, `neural_host.nim:990-1180`.

### 5.1 Read-only data (set before each decision, `bots.nim:146`, `492`)

| Name | Meaning |
| --- | --- |
| `selfId` | seat 0-15 (0 .. seats−1 in a match of another size) |
| `selfTeam` | `selfId mod 2` (FFA-kin: the seat) |
| `selfX`, `selfY`, `selfHp` | position; base HP (0-3, FFA-kin 0-10) |
| `armorHp` | armor 0-3 |
| `livesLeft` | lives including the current one (4 at start) |
| `hasGrenade`, `hasSpray`, `grenadeCharge` | 0/1, 0/1, 0-24 |
| `trenchId` | trench index you stand in, -1 outside |
| `worldTick` | current tick |
| `homeX`, `homeY` | your team's home point (base heart area); FFA-kin: your spawn anchor |
| `heartX`, `heartY`, `ownHeartX`, `ownHeartY`, `ownHeartStolen`, `carrying` | **legacy capture-the-flag fields.** Under rules 47 nothing sets `carrying` (only rules < 13 code does, `mechanics.nim:822`), so these read the enemy home, your home, 0 and 0. Use `control*` instead. |

### 5.2 Players (fog-gated)

Vision is the per-cog cone of mechanics.md section 6. Queries take an **observed identity**: a
disguised enemy answers to the seat it impersonates (`bots.nim:60-72`).

| Function | Returns | Hidden / invalid |
| --- | --- | --- |
| `visible(slot)` | 1 if seen (self is always 1) | 0 |
| `playerX(slot)`, `playerY(slot)` | position | -1 |
| `playerHp(slot)` | base HP | **0** |
| `playerCarrying(slot)` | legacy, always 0 | 0 |
| `playerTeam(slot)` | observed team (FFA-kin: seat) | -1 |
| `nearAgents(radius)` (16 WU) | count of seen agents within radius (clamped to 20,000), nearest first, max 64 | |
| `nearAgentId/X/Y/Hp/Team(k)` | entry k of the last `nearAgents` list | -1 (Hp 0) past the end |
| `hasUniform()` | 1 if **you** are disguised | |

`nearAgents` is cheaper than looping `visible(i)` over 16 seats in large games; `players/nearby.bas`
in the repo is `base.bas` rewritten that way (guide line 129).

### 5.3 Objectives (public, no fog)

| Function | Returns |
| --- | --- |
| `heartCount()` | 10 on Heartwick and the ten shipped-size generated maps; **100** on `big-twin-mesas` and **126** on `big-deep-forest` since 0.3.66 (verified with a local run; the map files are unchanged at `d0728ab1`) |
| `controlX(i)`, `controlY(i)` | heart position |
| `controlOwner(i)` | -1 neutral, 0 Red, 1 Blue (FFA-kin: seat) |
| `controlCaptureTeam(i)` | team (FFA-kin: seat) currently capturing, -1 idle |
| `controlCaptureTicks(i)` | 0-71 |
| `controlContested(i)` | 0/1 |
| `controlPoints(i)` | 1 (big hearts ended at rules 27) |
| `glory(team)` | current glory of team 0 or 1; -1 otherwise |
| `teamLives(team)`, `teamCogsOut(team)` | lives left (summed over the team's cogs) / cogs out of the match (dead, no lives left) for team 0 or 1; -1 for any other team and in FFA-kin (`bots.nim:260-261`, `268-269`). New in 0.3.72 (`teamLives`) and 0.3.75 / rules 47 (`teamCogsOut`); neither is version-gated, but only rules 47+ pays the cogs award |
| `awardBehind()`, `awardBehindSeconds()`, `awardBehindCogs()`, `awardBehindCogsSeconds()` | the match's configured behind-in-lives and behind-in-cogs glory awards and periods (league: 5 / 5 / 10 / 5); -1 in FFA-kin (`bots.nim:262-265`, `270-273`); see [mechanics.md §1.2](mechanics.md) |

Invalid indices return -1 (`bots.nim:285-300`).

### 5.4 Pickups and glory hearts (fog-gated)

| Function | Returns |
| --- | --- |
| `pickupCount()` | number of pickup stations (public) |
| `pickupVisible(id)` | 1 if ready and in view |
| `pickupX/Y(id)`, `pickupKind(id)` | position; 0 grenade, 1 spray, 2 medkit, 3 armor, 4 uniform. -1 if not ready or not in view |
| `gloryHeartCount()` | glory hearts on the field (public) |
| `gloryHeartX/Y(id)`, `gloryHeartTicksLeft(id)` | -1 if not in view |

A pickup that is respawning is indistinguishable from one out of view.

### 5.5 Map geometry (public)

| Function | Cost | Returns |
| --- | --- | --- |
| `mapMinX()`, `mapMinY()`, `mapMaxX()`, `mapMaxY()` | 4 | bounds |
| `terrainHeight(x, y)` | 4 | ground height (cm) |
| `waterAt(x, y)` | 8 | 1 if lake water |
| `trenchAt(x, y)` | 8 | trench index or -1 |
| `trenchCount()`, `trenchX/Y(i)` (centre), `trenchW/H(i)` | 4 | trench geometry |

### 5.6 Actions

| Function | Effect |
| --- | --- |
| `walkTo(x, y)` | set goal; the engine pathfinds (goal clamped 100 inside bounds) |
| `lookAt(x, y)` | set aim / facing (clamped to bounds) |
| `shootAt(x, y)` | set aim and pull the trigger: gun windup, or a spray burst if you hold a can |
| `chargeGrenade(held)` | nonzero = charge this tick; stop to throw along the aim |
| `sneak(on)` | half speed, no footstep sounds, this tick only |

### 5.7 Speech and sound

| Function | Cost | Returns |
| --- | --- | --- |
| `shout(handle)` | 68 | 1 if queued; max 4 per tick (then 0); text truncated to 256 bytes |
| `heardCount()` | 4 | messages heard this tick |
| `heardSlot(i)` | 4 | speaker's **observed** seat (a disguised enemy shows its disguise) |
| `heardX(i)`, `heardY(i)` | 4 | speaker's **exact position** |
| `heardText(i)` | 4 | new string handle (allocates in the pool) |
| `soundCount()` | 4 | cues from the last 24 ticks |
| `soundKind(i)` | 4 | 0 footsteps, 1 gunfire, 2 explosion, 3 spray |
| `soundDirection(i)` | 4 | 0 E, 1 SE, 2 S, 3 SW, 4 W, 5 NW, 6 N, 7 NE |
| `soundDistance(i)` | 4 | 0 <= 6 m, 1 <= 18 m, 2 farther |
| `soundAge(i)` | 4 | ticks |

Shouts are delivered on the **next** tick to every other living cog within 12.8 m, **both teams**,
regardless of vision (`bots.nim:166-168`, `508-517`). A shout therefore reveals your exact
position to any enemy in earshot. `PRINT` is private.

String toolkit (`basic.nim:3003-3093`), cost in work units: `strNew("lit")` 68 (returns the
interned literal), `strLen` 2, `strByte(h, i)` 3, `strAsc` 3, `strChr` 6, `strFromInt` 8,
`strVal`, `strCat`, `strCatInt`, `strMid`, `strEq`, `strCmp`, `strWord`, `strWordCount`,
`strUpper`, `strLower`, `strTrim` 68 each, `strFind` 1,028. Handle 0 is the empty string.

### 5.8 FFA-kin only (Heartland)

Heartland is its own coworld (`heartland`, tags `heartland-v*`) since 2026-09-28; the
`paintbot-pw` manifest no longer ships the `heartland` variants, though its config schema still
accepts `"mode": "ffa_kin"`. It runs the same engine, so this section stays as a reference.

Registered only when `mode` is `ffa_kin` (`bots.nim:310-345`). In the teams game these names do
not exist; a teams script may use them as variables, and **calling one there is a compile error,
which fails the whole episode** (section 4).

`gameMode()` (1), `seatCount()` (new: 16, or 50 in Heartland Big), `kin(slot)` (round(100 r):
100, 50, 25, 0; -1 invalid), `gene(slot, i)`, `seatScore(slot)` (raw score in tenths),
`seatAlive(slot)`, `heartOwner(i)`, `territoryBoost()`, `greatHeartCount()`, `greatHeartX/Y(i)`,
`greatHeartPresent(i)`, `greatHeartProgress(i)` (0-119), `greatHeartDormant(i)`. Before rules 48
all were public with no line of sight. **Rules 48 (FFA-kin fog of war):** `kin`, `gene`,
`seatScore` and `seatAlive` read -1 for any seat other than yourself that you cannot see this
tick (`bots.nim:310-327`, `sim.nim:240-245`); `seatCount`, hearts and great hearts stay public.

### 5.9 Advisor oracle (`oracle.nim`, `runtime/oracle.py`)

A seat can have the host ask an LLM on its behalf. Asking never blocks; answers arrive on a later
tick.

| Function | Cost | Semantics |
| --- | --- | --- |
| `oracleAvailable()` | 4 | 1 if the host has an oracle |
| `oracleReady()` | 4 | 0 = an ask would be accepted; >0 = ticks to wait; -1 = no oracle or a request in flight |
| `oracleState(key, int)`, `oracleStateText(key, text)` | 8 / 16 | add a `state` field (max 256; keys 1-64 bytes; `a.b[0].c` paths build nested JSON) |
| `oracleNote(text)` | 16 | append to `state.notes` (max 16) |
| `oracleQuestion(key, kind, instructions)` | 16 | kind 0 yes/no, 1 score, 2 choice (max 64 questions) |
| `oracleCriterion(key, label, text)`, `oracleCriterionField(key, label, field, text)` | 16 | criteria (max 16 per question) |
| `oracleAsk()` | 68 | returns request id >= 1, or 0 if refused (no oracle, one in flight, fewer than 24 ticks since the last ask, no question, body over 32 KiB). Always clears the draft. |
| `oraclePoll(id)` | 4 | 0 pending, -1 failed or unknown, else number of answers |
| `oracleAnswer(id, key)` | 8 | yes/no: P(true) x 1000; score x 1000; choice: criterion index; -1 missing |
| `oracleConfidence(id, key)`, `oracleProbability(id, key, label)` | 8 | x 1000, -1 missing |

- The draft is cleared at the start of every tick (`oracle.nim:100-103`): build and ask in one
  decision. Store the request id in a global.
- One request in flight per seat; minimum 24 ticks between asks (`oracle.nim:18`, `297-298`);
  the last 4 answers are kept (`oracle.nim:17`, `133`).
- Hosted: the host posts to the platform LLM sidecar (`/v1/systemone`, model
  `typesafe/jev-1.13` per guide lines 743-754), with a 2 s deadline plus grace
  (`oracle.py:52`, `105`). Cost counts against the seat's per-episode LLM spend limit; a seat with
  no budget gets no answers. Whether the `paintbot-pw` leagues grant any spend is an **open
  question**.
- Every ask and answer is journaled to the asking seat's private log (`bots.nim:384-387`,
  `oracle.nim:303-314`).

### 5.10 Neural BASIC (ZIP uploads)

`policy.bas` calls native FP32 inference each tick:

```basic
paintbot_observe(neuralObservation())
run_neural_net(neuralModel(), neuralObservation(), neuralLogits(), neuralState())
paintbot_act(neuralLogits())
```

A secondary lane for this lab (we upload plain BASIC), documented so it can be used or read
correctly. Upstream references: `neural_basic.md` (package, decoder options, BASIC I/O) and
`neural_actor.md` (actor formats, observation and action contracts).

**Per-tick calls.**

- Costs 512, 16 and 128 work units; each at most once per tick, in that order; misuse (a
  repeat, a wrong handle, inference without a fresh observation) is a runtime error that
  disables the seat (`neural_host.nim:787-789`, `997-1031`).
- `paintbot_act` is `neuralDecode()` then `neuralIssue()`: it **replaces the whole command**
  for the tick (`neural_host.nim:1021-1031`, `bots.nim:163`); action calls made before it are
  overwritten, calls after it amend it.
- Recurrent state (and the aim memory used for lead) resets at match start, on death and on
  respawn (`neural_host.nim:730-735`).
- Native inference has its own budget: 4,000,000 counted operations per seat per tick at 16
  seats, scaled by seats/16 above 16 (`neural_host.nim:7-12`), checked once at load against the
  model's published operation count; over budget, the seat is refused at load and its log gets
  a `neural: peak_ops=...` line. Every neural seat logs that line at match end
  (`neural_basic.md` "Native inference").

**Observation contracts** (the actor's embedded hash selects the encoder; the manifest must
name the same hash; `neural_contract.nim:12-15`, `32-33`, `84-85`, `104-105`, `119-120`):

| Contract | Id | Floats | Game |
| --- | --- | --- | --- |
| v1 | `paintbot-pw.rules37.obs.v1.float448` (`ed5d1676…`) | 448 | teams (16 seats) |
| v2 | `paintbot-pw.rules37.obs.v2.float506` (`e0d7b0b9…`) | 506 = v1 + 58-float terrain block | teams (16 seats) |
| v3 | `paintbot-pw.rules43.obs.v3.float514` (`06f16d62…`) | 514 = v2 + 8-float scoreboard (team lives, glory, the configured behind-in-lives award and period, quiet-supplies award, clock) | **teams only**: refused at load in FFA-kin (`neural_host.nim:572-576`) |
| v2u*K*, v3u*K* | `paintbot-pw.rules39.obs.v2u<K>`, `paintbot-pw.rules43.obs.v3u<K>` | 506 + K, 514 + K | as v2 / v3; K user inputs, 1-128, set from BASIC with `neuralInput` (`neural_package.py:53-78`) |
| ffa.v1 | `paintbot-pw.rules40.obs.ffa.v1.float810` (`6b19dc32…`) | 810 | FFA-kin, 16 seats |
| ffa.v2 | `paintbot-pw.rules48.obs.ffa.v2` (`d0a10cee…`) | per match: `24 + (N−1)·44 + H·12 + 24` (828 at 16 seats and 10 hearts) | FFA-kin at any seat count (Heartland, Heartland Big) |

For the teams game the choice is v1, v2, v3 or their user-input forms. The v3 scoreboard does
not include the rules-47 behind-in-cogs award or `teamCogsOut` (columns 506-513,
`neural_actor.md` "v3"); a v3 policy reads those through BASIC (§5.3) and `neuralInput`. The
loader has no mode check for ffa.v1/ffa.v2 (only v3 has one), but they are built for FFA-kin
(kin columns are zero outside it) and are of no use here.

**Seat count.** Every contract except ffa.v2 lays out exactly 16 seats, so a v1/v2/v3/ffa.v1
seat in a match of any other size is refused at load (`neural_host.nim:650-652`). An ffa.v2
bundle is sized against the match at load (`neural_host.nim:593-622`). Every paintbot-pw match
has 16 seats, so this never bites in the teams league.

**Action contracts** (`neural_contract.nim:10-25`):

| Contract | Heads | Identity aim resolves to |
| --- | --- | --- |
| v1 (`55922d42…`) | `[51, 25, 2, 2, 2]` = 82 logits: movement (0 stay, 1-10 hearts, 11-42 visible-pickup slots, 43-50 compass steps, so only hearts 0-9 and pickups 0-31 are addressable; `neural_contract.nim:893-905`), aim (0 keep, 1-16 identities, 17-24 compass), fire, grenade, sneak | the body's current position |
| v2 (`51f602ef…`) | same | the body's lead-compensated point `P + 6u − 5v` (base.bas's rule) |
| ffa.v2 pointer (`068fc981…`) | sized by the match: objective `11 + H`, aim `8 + N`, then 2, 2, 2; the objective and aim heads point at the ffa.v2 observation's rows of the same tick | a seen cog row's lead point; past the seen rows keeps the aim |

ffa.v2 and ffa.v2 pointer must be used together (`neural_host.nim:578-582`,
`neural_package.py:842-844`). A pointer seat accepts only the `sampling` decoder option and
refuses `neuralMask`/`neuralMaskFrom` (`neural_package.py:831-835`).

**Actor formats** (`neural_actor.md`). `PWNET001`: one fixed MinGRU, hidden 64/128/256.
`PWNET002`: a layer stack from a fixed menu (1 DENSE, 2 RMSNORM, 3 MINGRU, 4 RESIDUAL,
5 ENTITY_ATTN, 6 CONCAT_INPUT, 7 TOKEN_MLP, 8 TOKEN_MIX, 9 POINTER, 10 SEGMENT_NEAR,
11 ATTN_POOL, 12 PAD), at most 64 layers, widths up to 4,096, 4,194,304 parameters, 4,096 state
floats (`neural_package.py:363-365`). A PWNET002 structural integer may be a **layout word**
(high 16 bits `0xFFFE`: section, field and addend in the low bits) that the host resolves
against the match's ffa.v2 layout at load, so one `model.bin` serves 16 and 50 seats; staging
checks such a model only up to its first layout word and leaves the rest to the load
(`neural_package.py:356-362`, `416-436`). Layout words matter only under ffa.v2.

**Manifest and decoder options** (schema `paintbot-neural-basic/2`). Default decoding is
headwise argmax. A schema-2 manifest may add `decoder` options, validated identically at
staging and load (`neural_package.py:20-31`, `795-835`; `neural_host.nim:470-540`):
`fire_hold_teammates` (true or `{"radius": 1..2000}`), `sampling` (categorical, temperature
0.01-10, chosen heads; a seat-owned stream seeded from the match seed and slot, so the world
hash is untouched), `forbid_objectives`, `strafe_legs`, `aim_snap`, `steady_shot`,
`aim_retarget`, `shot_gate`, `spray_aim`, `spray_gate`, `joint_sampling`; and `user_inputs`
`{"count": K, "init": [...]}` for v2u*K*/v3u*K* (values ±1,000,000, read by the net as
value/1000 one tick later). Semantics and their fixed order within a decision:
`neural_basic.md` lines 26-197.

**Head-level BASIC API** (`neural_host.nim:1033-1180`; `neural_basic.md` lines 222-300), all
optional: `neuralInput(i, v)`; `neuralObs(i)` (observation × 1000); `neuralMask(h, bits)`,
`neuralMaskFrom(h, first, bits)`, `neuralTemperature(h, milli)` before selection;
`neuralSample()`, `neuralChoice(h)`, `neuralSetChoice(h, i)`; `neuralDecode()` into a command
buffer read with `cmdWalk() … cmdDirect()` and edited with `cmdSet(field, value)`;
`neuralIssue()`; candidate readers `neuralGoalX/Z(m)` (8 WU) and `neuralAimX/Z(k)` (16 WU);
`neuralLayout(i)` (observation layout words 0-15, head sizes 16-20) and `neuralRow(section, k)`
(ffa.v2 only: which seat or heart row k shows this tick).

**Upstream doc/code mismatch:** `neural_basic.md` line 199 says the archive allows "64 KiB
BASIC"; the staging code allows 128 KiB for `policy.bas` (`neural_package.py:12`,
`MAX_SOURCE_BYTES`, "matches maxSourceBytes in bots.nim"). The code wins.

## 6. Starter policies (`../reference/`)

The copies in `../reference/` are the files the league runs: `base.bas`
(`sha256:3679f5bb...`) and `jev.bas` (`sha256:fec43ac7...`) from `coworld/paintbot/players/` at
`d0728ab1` (tag `coworld-v0.3.79`). Their hashes equal the `player[].file` entries of the live
coworld record saved as `../reference/manifest-0.3.80.json` (read 2026-09-29); every line
number below is at `d0728ab1` (re-hashed against the tag). Against the
**0.3.65** files (`sha256:587cbe41...`/`c36db417...`, `../reference/manifest-0.3.65.json`)
they differ only in array sizes and loop caps raised from 16/32 to 64 (`avoidUntil`,
`pickupMemory*`, the heart and pickup loops) so they do not overrun on the big maps' 100+
hearts, on the same lines.

`../reference/heartland/` holds `ffa.bas` and `ffa_blind.bas` from `coworld/heartland/players/`
at `d0728ab1` (932/936 lines, rules-48 fog: remembered kin,
256-seat arrays). They target the separate Heartland coworld and **do not compile in the teams
game** (`pw_local.py compile` at coworld-v0.3.79: `compile_failed` on every seat).

### `base.bas` (manifest `baseline`, 677 lines)

Each cog, every tick:

1. **Scan** all 16 seats: pick the best visible enemy within 52.5 m (nearest, wounded favoured),
   count foes within 26 m and friends within 12 m (`base.bas:142-180`).
2. **Squads**: seats `(selfId / 2) mod 8` split into two squads of four. Each squad picks the
   cheapest heart not owned by us, measured from a reference point above or below home (mirrored
   for Blue), neutral hearts preferred, and hearts it failed to reach in 3 s avoided for 15 s. Two
   members stand in the ring; two cover from outside and step in if nobody is capturing
   (`base.bas:204-298`). No communication: the choice is a pure function of public ownership.
3. **Supplies**: remembers seen pickups for 10 s; detours for a grenade if unarmed, a medkit if
   hurt, armor if at full HP, when no enemy is close (`base.bas:300-344`). It never takes spray or
   uniforms.
4. **Refuse bad fights**: more foes than friends nearby, head for the heart far from them and near
   us (`base.bas:346-370`).
5. **Look**: with no target, sweep in a 4-way cycle, face the latest speaker, or the most recent
   gunfire/explosion sector (`base.bas:372-434`). Routine shouts every 15 s, staggered by seat
   (`base.bas:436-446`).
6. **Footwork**: in contact, random 3-9 tick legs across the line of fire; shots are ordered only at
   the start of a leg long enough to cover the windup (`base.bas:448-493`).
7. **Dry route**: if the straight line to a target over 8 m away crosses water, detour through
   the best of six side points (`base.bas:494-564`).
8. **Aim**: lead the target by 6 ticks of its last motion, subtract its own drift, hold fire if a
   visible teammate is within 95 units of the line; tracks its own cooldown estimate
   (`gunWait`) because BASIC cannot read it (`base.bas:566-622`).
9. **Grenade**: charge to match distance (4-12.5 m) unless a visible teammate is within 4.5 m of
   the target; it does not check its own distance to the blast (`base.bas:634-665`).
10. **Sneak** near the objective when something is heard but nothing seen (`base.bas:667-674`).

It ignores glory entirely: it takes supplies (which resets the quiet-supplies clock), never
seeks glory hearts, and never reads `teamLives`/`teamCogsOut`. Its header comment claims a 20,000-instruction budget (stale; the budget is
50,000).

### `jev.bas` (manifest `basic-jev`, 2,644 lines)

`base.bas` with an advisor layer spliced in by `coworld/paintbot/tools/make_jev_baseline.py`
(`jev.bas:1-8`; the same 64-cap edit as `base.bas`). One cog per squad asks the oracle to choose the squad objective from three
code-ranked capture candidates (or keep current), relays the pick by shout (`"Alpha, push
Forge."`), and squadmates adopt it silently. It carries dozens of switches in its init block
(`jev.bas:570-713`): `useObjective`, `useRetreat`, `useDial`, `useNouls`, `useRelay`,
`useLeader`, `useExamples` and the logging switch `useTrace` (one seat per team logs hearts held
and score once a second, `jev.bas:705-707`) are on and the rest off. With no
oracle every ask is refused and it plays exactly like `base.bas` (guide lines 833-837, not
re-verified by running). Because its
callouts are public within 12.8 m, enemies in earshot can read the squad plan.

### `heartland/ffa.bas` (Heartland baseline, 932 lines) and `heartland/ffa_blind.bas`

FFA-kin only; it calls `kin`, `seatAlive` and other FFA functions, so **uploading it to a teams
league fails the episode at compile**. It never shoots cogs with `kin >= 50` (nor cousins),
prefers strangers seen hurting relatives, splits hearts among siblings by rank so no two stand on
one heart, guards held hearts, joins great hearts when others gather, and late in the match waits
at a great heart or steals a stranger's heart (`ffa.bas:1-22`). Since rules 48 it remembers each
cog's `kin` once seen and treats a never-seen cog as a stranger (guide line 480). Movement, aim, dodge and dry-route
code are `base.bas`'s. `ffa_blind.bas` is a generated control that replaces every `kin(x)` with
"100 for me, 0 for everyone else" (`diff ffa.bas ffa_blind.bas`).
