# Paintbot PW mechanics (as deployed)

> **Currency.** Verified 2026-09-29 against Metta-AI/paintbot-pw commit `570174a2` (tag
> `coworld-v0.3.78`), which is coworld `paintbot-pw` 0.3.78
> (`cow_12867c2e-aca8-4755-980b-5ba668a04ad4`), the build both leagues run that day
> (`tools/deployed_ref.py`). Live games record rules **48**; rules 48 changed only FFA-kin fog,
> so the teams game plays rules 47. Line numbers below are at `570174a2`. Previous basis:
> `7b2b19f5` (0.3.65, rules 45); every section was re-checked against the full diff of
> `examples/paintbot`, `src/polyworld`, `coworld/paintbot/guide.md` and the manifest template,
> and the changed facts are marked with the release that introduced them. Re-verify when the
> coworld version changes: diff `examples/paintbot/sim.nim`, `mechanics.nim`, `game.nim`,
> `match_config.nim`, `kinship.nim`, and the manifest template's `variants`.

This is **Paintbot on Polyworld**: a Nim engine where every seat is a BASIC script run inside the
game pod (`player_runtime: game-hosted`). It is not the older Paintbot (Season 1 capture-the-heart
shooter, Season 2 battle royale with WASM plays); nothing here carries over from that lab.

Paths are relative to the repo root. `sim.nim` and `mechanics.nim` are under `examples/paintbot/`
(`mechanics.nim` is `include`d into `sim.nim`, `sim.nim:1474`). The game guide is
`coworld/paintbot/guide.md`; the manifest's `docs.readme` is that guide minus its
`readme:skip` blocks (checked by diff). Companion page: [policy-surface.md](policy-surface.md).

## 1. The one thing to get right: winning, glory, and rank

> **Currency of this section.** Verified 2026-09-29 against paintbot-pw `570174a2` (tag
> `coworld-v0.3.78`, the league's build that day; rules 48, whose only change is FFA-kin fog, so
> the teams game plays rules 47; teams recordings are nevertheless stamped 48, checked on a local
> recording). Line numbers in this document are at `570174a2`. League ranking settings were read live the same day;
> the Elo code is metta `packages/observatory-competitions/src/observatory_competitions/v2/ladders/rankings/elo.py`
> at `49951fd7f6`. This section is the lab's canonical statement of scoring and rank; other docs
> link here instead of restating it.

Three different numbers matter, and only the last one is what the league ranks by:

1. **The heart meter decides who wins the match.**
2. **Glory is the score the platform receives.** The winner keeps its glory; the loser and both
   sides of a draw get 0.
3. **League rank (MMR) moves by the glory margin.** Since 2026-09-28 evening the ladder's Elo
   uses `margin_scale: 1000`, so every point of winning glory moves rank, not just the win.

### 1.1 Heart meter versus glory

| | Heart meter (win condition) | Glory (reported score, teams game) |
| --- | --- | --- |
| Starts at | 0 per team | match length in seconds: `endTick div 24` = 600 for 14,400 ticks (`sim.nim:864-865`) |
| Changes | +1 tick-point per owned control heart per tick | -1 per second, floored at 0, plus the awards in 1.2 (`sim.nim:934-959`) |
| Ends match when | a team reaches `hearts × HeartMeterFillTicks / 2` = 10 × 4,320 / 2 = 21,600 tick-points = 900 points on a ten-heart map (`sim.nim:13`, `912-914`; `mechanics.nim:774-785`; the big maps have 100 and 126 hearts, so their target is 10x and 12.6x larger), a team is eliminated, or tick 14,400 | never ends the match |
| At match end | higher meter wins; equal = draw (`mechanics.nim:786`) | `settleGlory`: loser set to 0; a draw sets **both** to 0 (`sim.nim:1009-1013`, called at `mechanics.nim:787`) |
| Reported as | not reported | `results.scores[i]` = glory of seat i's team (`sim.nim:1015-1024`) |

Every ending (meter full, elimination, time limit) passes through the same winner comparison
and `settleGlory` call (`mechanics.nim:785-787`). Elimination fills the survivor's meter first,
so the survivor wins.

### 1.2 How glory is earned and lost (rules 37-47)

Glory hearts are paid before the tick counter advances (`mechanics.nim:765`); the rest in
`updateGlory` after it (`mechanics.nim:773`). Every award is logged as a `GloryEvent` with a
kind (`sim.nim:142-146`, `916-920`).

| Source | Rule | Kind | Code |
| --- | --- | --- | --- |
| Countdown | every 24 ticks (1 s), each team loses 1, floored at 0 | (not an event) | `sim.nim:943-944` |
| Quiet supplies | when no teammate has **taken** a pickup for `quiet_supplies_seconds`, the team earns `quiet_supplies` and the stretch restarts. A pickup is only taken when useful (a medkit only when hurt, `mechanics.nim:534-549`), so walking over one at full health does not reset it | `gloryQuietSupplies` | `sim.nim:946-949` |
| Behind in lives (rules 39+) | every `behind_lives_seconds`, lives are summed per team (`teamLives`, counts the current life); the team with fewer earns `behind_lives × (enemy lives − own lives)` | `gloryBehindLives` | `sim.nim:922-926`, `950-954` |
| Behind in cogs (rules 47+) | every `behind_cogs_seconds`, count each team's cogs **out of the match** (dead with no lives left, `teamCogsOut`); the team with **more** cogs out earns `behind_cogs × (own cogs out − enemy cogs out)` | `gloryBehindCogs` | `sim.nim:928-932`, `955-959` |
| Glory heart (rules 38+) | the first living cog within 120 units of a glory heart earns `heart` for its team. Hearts spawn in mirrored pairs from 0:20, every 10-20 s (one pair per ten control hearts each time, so 10 pairs on `big-twin-mesas`), live 30 s, on random open dry spots, and are fog-gated for policies | `gloryHeart` | `sim.nim:36-43`, `974-1007` |

Friendly-fire glory existed in rules 37-38 only (`sim.nim:33`).

**Award values.** The config key is `glory` (teams game only; parsed in `match_config.nim:10-39`,
defaults `sim.nim:31-51`, `617-620`):

| Key | Engine default | **League (all 15 teams variants)** | Meaning |
| --- | --- | --- | --- |
| `quiet_supplies` | 10 | 10 | glory per quiet stretch |
| `quiet_supplies_seconds` | 30 | 30 | stretch length |
| `behind_lives` | 1 | **5** | glory per life behind, per period |
| `behind_lives_seconds` | 5 | 5 | period |
| `behind_cogs` | 1 | **10** | glory per extra cog out, per period |
| `behind_cogs_seconds` | 5 | 5 | period |
| `heart` | 20 | 20 | glory per glory heart |

Source for the league column: every teams variant in `coworld/paintbot/coworld_manifest_template.json`
at `570174a2` sets `"glory": {"behind_lives": 5, "behind_cogs": 10}` (read 2026-09-29; the change
to 10 is commit `0ff41d2`, "behind-in-cogs glory 5 -> 10"). **Not yet observed in a live episode's
`game_config`** (the API was rate-limited when this was written); on 2026-09-28 live episodes
showed `{"behind_lives": 5}`, which predates rules 47. Local runs through `local.py` use the engine
defaults; `paintbot-headless` accepts `--glory:<json>` to match the league.

**What a policy can read** (BASIC, teams game; `bots.nim:254-273`): `glory(team)`,
`teamLives(team)`, `teamCogsOut(team)`, and the configured award values `awardBehind`,
`awardBehindSeconds`, `awardBehindCogs`, `awardBehindCogsSeconds`.

### 1.3 How glory becomes league rank

The main league (`league_b9458ff8-…`) ranks by Elo with these live settings (read 2026-09-29):
`k_factor 32`, `initial_rating 1500`, `round_scoring_rule "mean"`, **`margin_scale 1000`**.
For each episode, the two sides' mean scores are compared (`elo.py:181-182`). With
`margin_scale` set, the result credited to our side is the **score margin**, not win/draw/loss
(`elo.py:183-187`):

```
outcome = clamp(0.5 + (our glory − their glory) / (2 × 1000), 0, 1)
```

Because the loser's glory is always 0, this is `0.5 + winning glory / 2000` for a win and
`0.5 − their winning glory / 2000` for a loss:

| Episode result | Outcome for us |
| --- | --- |
| Win with 950 glory | 0.975 |
| Win with 500 glory | 0.75 |
| Win with 300 glory (e.g. a 5:00 win, no awards) | 0.65 |
| Win with 0 glory (a slow win whose glory ran out) | 0.5, a draw |
| Draw (both sides 0) | 0.5 |
| Loss to a 500-glory winner | 0.25 |
| Our policy's episode failure attributed to us | 0 (forfeit; the margin is ignored, `elo.py:174-179`) |

The Elo update is then `K × (outcome − expected)` with K = 32. The wins/draws/losses counters
record which side of 0.5 the outcome fell on. History: the ladder used plain win/draw/loss
until `margin_scale` was set on 2026-09-28 evening (metta commit `6304974ffa`, whose rollout note
names this league); ratings earned before then were built that way. Whether other paintbot-pw
leagues use it is not established.

### 1.4 Practical consequences

Arithmetic from the rules above, not measured:

- **Speed is rank.** Each second of match time costs 1 glory, which is 0.0005 of Elo outcome.
  A win at *t* seconds is worth about `600 − t + awards` glory. League winners scored 428-577 in
  one round on 2026-09-28 and 527-551 in three episodes of one round on 2026-09-29 (public round listing), so
  current wins end in roughly 1-3 minutes.
- **Losing fast costs more than losing slow.** A loss is `0.5 − their glory / 2000`, so delaying
  an opponent's win reduces the rating loss even when the loss is certain.
- **The two "behind" awards pay the team that is losing the fight.** Behind in lives pays 5 per
  life every 5 s; behind in cogs pays 10 per extra cog out every 5 s. A team 3 cogs down for a
  minute earns 12 × 30 = 360 from cogs alone. It is worth anything only if that team still wins
  on the meter. The engine comment states the design intent: glory is "a self-imposed handicap:
  nothing that makes a team more likely to win pays it" (`sim.nim:28-30`).
- **Supplies cost glory.** Every pickup a teammate takes forfeits the running quiet stretch
  (+10 per 30 s).
- **Win rate and glory are different questions.** A policy that wins 60% slowly can rank below
  one that wins 50% fast. The A/B primary metric is therefore the per-episode outcome above (see
  the [tooling plan](designs/2026-09-29-tooling-plan.html), §7).

### 1.5 Re-verifying this section

Run `uv run python paintbot_pw_lab/tools/deployed_ref.py`. If the deployed commit changed, diff
`examples/paintbot/sim.nim` (constants at the top, `updateGlory`, `settleGlory`, `scores`),
`examples/paintbot/match_config.nim` and the manifest template's `variants[].game_config.glory`.
Re-read the league's `settings.ladder.ranking` (the `margin_scale` knob can change without any
game release), and check one fresh league episode's `game_config.glory`.

## 2. Teams, seats, and match flow (teams mode)

- **16 seats. Team = `slot mod 2`**: even = Red (team 0, "Ember"), odd = Blue (team 1, "Azure")
  (`sim.nim:230`; names `game.nim:404`). The manifest's `slots[].team` labels are not read by
  the engine (`applyGameConfig` reads only `mode`, `kin_layout`, `glory`, `game.nim:425-436`,
  parsed in `match_config.nim`; `CoworldConfig` fields are `coworld.nim:16-23`).
- **Seat count is per match since 0.3.75 (rules 46).** The engine takes it from the game
  config's roster, one seat per entry in `tokens` (`game.nim:445-447`), and accepts 2 to 256
  (`kinship.nim:12-30`; the host checks the same range, `host.py:89-90`). The `paintbot-pw`
  config schema still requires exactly 16 `tokens`, so every paintbot-pw match has 16 seats;
  locally `local.py --seats N` and `paintbot-headless --bot FILE:N` play other sizes (a 2-seat
  run was checked). Recordings from rules 46 store the seat count; older ones are 16.
- **Tick rate** 24/s (`sim.nim:10`). **Match length** `min(max_ticks, 14400)` ticks = at most
  10:00 (`sim.nim:12`, `857-858`). Every teams variant sets `max_ticks: 14400`.
- **Ending** (`mechanics.nim:765-788`), checked every tick after scoring:
  1. **Elimination**: a team is out when every cog has `hp <= 0` and `lives == 0`. The survivor's
     meter is raised to full, the match ends, and the higher meter wins, so the survivor wins
     (`mechanics.nim:776-786`). Both out on the same tick: meters as they stand decide.
  2. **Meter full**: either team reaches 21,600 tick-points.
  3. **Time**: `tick >= endTick`; higher meter wins, equal is a draw.
  Simultaneous fills: higher meter wins, equal is a draw (`mechanics.nim:786`).
- **Seat order.** Seats act in slot order, but each even/odd pair is swapped on odd ticks, so
  neither team always moves first (`mechanics.nim:518-525`).

### Result fields

`finishCoworld` writes (`game.nim:562-563`, type `coworld.nim:49-56`, snake_case `coworld.nim:86-105`):

| Field | Value | Notes |
| --- | --- | --- |
| `scores` | one float per seat (16) | teams: team glory per seat (`sim.nim:1023-1024`); FFA-kin: kin-weighted score (section 7) |
| `ticks` | final tick | |
| `seed` | world seed | |
| `outcome` | `"0"` (Red won), `"1"` (Blue won), `"time_limit"`, or `"ended"` (FFA-kin) | `game.nim:541-543` |
| `banked_gold` | always `[]` | shared Polyworld result type; paintbot never fills it |
| `returned` | always `[]` | same |

**Finding: `outcome: "time_limit"` means a draw, not "the clock ran out".** `matchOutcome` returns
`"time_limit"` whenever `winner < 0`, and at rules 47 a teams match always ends with `winner` set
to 0, 1 or -2 (draw) (`mechanics.nim:786`). A match decided on the meter at 10:00 reports `"0"` or
`"1"`; a draw by any route (time, equal meters, mutual elimination) reports `"time_limit"`.

## 3. Hearts and territory (teams mode)

- **10 control hearts** on Heartwick and the ten shipped-size generated maps, all equal income
  (1 tick-point per tick each; big hearts ended at rules 27, `sim.nim:909-910`). Since 0.3.66
  the big maps carry **100** (`big-twin-mesas`) and **126** (`big-deep-forest`) hearts
  (verified with `heartCount()` in a local run); read the count at runtime. Hearts 0 and 1 start owned by Red and Blue; the rest start neutral
  (`mechanics.nim:171`). Base hearts are ordinary hearts and can be captured.
- **Touching** a heart: alive, within 140 units, and a traversable line to it (no height step
  over 25 units per 20-unit sample, `sim.nim:346-356`) (`mechanics.nim:327`).
- **Capture** (`mechanics.nim:329-348`): one team touching and not the owner accumulates 1 tick per
  tick; at 72 ticks (3 s) ownership flips directly to the attacker (no neutral step). Both teams
  touching: progress pauses. Nobody, or only the owner: progress resets. A different attacking
  team starts from 0. More cogs do not speed it up.
- **Territory** is the nearest-heart region (`sim.nim:1370-1378`). In the teams game it is only a
  display; it has no mechanical effect (the boost applies in FFA-kin only, `sim.nim:1385`).
- **Heartwick heart positions** before nudging (`mechanics.nim:168-185`), each odd index the half
  turn of the even one before it about (3200, 2000): 0 red home (960, 2000); 1 blue home
  (5440, 2000); 2 (-3000, 500); 4 (1000, -1600); 6 (-3000, 3500); 8 (3200, 1250) (lake heart).
  Read positions from `controlX/Y` at runtime rather than hard-coding them.

## 4. Lives, spawning, health

| Item | Value | Source |
| --- | --- | --- |
| Base HP | 3 (FFA-kin 10) | `sim.nim:65`, `72`, `298-300` |
| Lives | 4 per cog: the first life plus 3 respawns. `livesLeft` counts the current life | `mechanics.nim:138`, `436` |
| Respawn delay | 72 ticks (3 s) | `sim.nim:23`, `mechanics.nim:439` |
| Spawn protection | 36 ticks; all damage ignored (`shield > 0`) | `sim.nim:782`, `mechanics.nim:363` |
| On death | equipment wiped (grenade, spray, armor, charge), uniform removed | `mechanics.nim:437-438` |

- **Where you spawn** (`sim.nim:740-812`, `mechanics.nim:588-603`): if the team owns any heart,
  within 350 units of an owned heart (wider by the square root of seats/16 in matches over 16
  seats, `sim.nim:768-772`) chosen by a softmax over the summed distance from living
  teammates (temperature 1000, distances quantized to 10). Larger sums (less-covered hearts) are
  favoured. If the team owns no heart, a random point in the team's end zone. Crowded or blocked
  placements retry next tick. Initial spawns use the same heart rule (`sim.nim:902-904`).

## 5. Combat

Units: 1 unit = 1 cm; `Radius` (body) = 55 (`sim.nim:17`).

### Movement

- Speed 28 units/tick (`sim.nim:18`). Sneak halves it (`mechanics.nim:619`). Water quarters it
  (7 units/tick) (`mechanics.nim:620-622`). Leaving a trench (moving away from its centre) is
  slowed 5x per axis (`mechanics.nim:625-631`). Effects stack.
- Bodies are solid to everyone (`sim.nim:731-739`). A blocked cog sidesteps
  (`mechanics.nim:637-650`).
- The engine pathfinds (`waypointFor`, `mechanics.nim:510-516`) on a 1 m grid where a lake cell
  costs 4 (rules 38), and from rules 45 routes into water when the goal itself is wet (lake hearts)
  (`sim.nim:1219-1369`).

### Gun (the default weapon; `mechanics.nim:675-728`)

- `shootAt` with cooldown 0 starts a **5-tick windup**. The aim is locked at the order as a
  vector relative to the shooter; the ray leaves from wherever the shooter stands when the windup
  ends.
- Cooldown 24 ticks (1 shot/s), **tripled to 72** if the shooter has armor or is in a trench
  at the moment of the order (`mechanics.nim:726-728`). The check also reads `carrying`, which
  nothing sets under rules 47.
- Hitscan: samples every 20 units out to 5,250 units (FFA-kin 2,000); stops at cover or the map
  edge; the **first** body within 55 units of the ray with a clear sight line takes 1 damage.
  **Friendly fire is on**: teammates block and take hits (`mechanics.nim:705-715`).
- Trench cover: a victim in a different trench from the shooter is skipped 70% of the time and
  the ray continues (`mechanics.nim:711-713`).
- Spread: small random jitter scaled by height difference, 25% less per metre the shooter stands
  above the target, clamped to 50-150% (`mechanics.nim:60-63`, `683-693`). At 20 m the lateral
  error is at most about 24 units, less than the body radius; the main source of misses is the
  target moving during the windup (**inferred** from the jitter bound).
- All gun targets in a tick are chosen before damage, so mutual kills happen (`mechanics.nim:729-731`).

### Spray can (`mechanics.nim:666-674`, `498-508`, `735-742`)

- A carried can **replaces the gun** and is never used up; you keep it until death.
- `shootAt` with spray cooldown 0 starts a 5-tick burst; next burst 13 ticks later (5 + 8).
- Cone: forward along the aim to 850 (+55) units, half-width `4/5 * along` (+55), clear sight
  line required. Each victim takes 3 damage once per burst. Hits teammates too; spawn-protected
  cogs are skipped.

### Grenade (`mechanics.nim:656-665`, `472-496`)

- Carry one. `chargeGrenade(1)` adds 1 charge per tick, up to 24. The tick you stop charging (charge
  > 0), it is thrown along your aim: range `150 + 1130 * charge / 24` with charge clamped to at least 1, so about 197 to 1,280 units (`mechanics.nim:474-475`).
  It flies over walls and lands 10 ticks later.
- Blast: every body within 360 + 55 units takes 3 damage in the open, 6 if in the trench it
  landed in, 2 if in a different trench. **Includes allies and the thrower.**

### Armor, medkits, pickups (`mechanics.nim:527-553`)

| Kind (`pickupKind`) | Taken when | Effect | Respawn |
| --- | --- | --- | --- |
| 0 grenade | not holding one | carry one grenade | 120 ticks (5 s) |
| 1 spray | not holding one | replaces gun until death | 720 ticks (30 s) |
| 2 medkit | `hp < max` | full HP | 720 |
| 3 armor | armor < 3 | armor = 3, absorbed before HP; **triples gun cooldown** while > 0 | 720 |
| 4 uniform | not disguised, not attacking this tick | disguise (below) | 720 |

Pickup reach is 120 units. On Heartwick the layout is 2 uniforms, 4 grenades, 2 sprays, 2 armors,
6 medkits (the base pair plus two deep-wilderness pairs) and 6 trenches of 280 x 280
(`mechanics.nim:133-185`; the per-kind split is **inferred** from the placement code; the totals,
16 pickups and 6 trenches, were checked with `pickupCount()`/`trenchCount()` in a local run at
`570174a2`). Generated maps place their own items (`mechanics.nim:108-127`): 14 pickups and 6
trenches on the shipped-size maps; since 0.3.66, 140 / 60 on `big-twin-mesas` and 182 / 78 on
`big-deep-forest` (checked the same way).

### Trenches

Walkable pits: slow to leave, triple gun cooldown for occupants, 70% protection from outside
gunfire, heavy grenade damage inside (all covered above). Trench geometry is public.

### Disguise (uniforms, `sim.nim:301-311`)

A disguised cog appears to others as seat `slot xor 1` (a real enemy seat number) and as the
other team. The disguise drops on a gun order, spray burst, grenade release (charging alone keeps
it) or death (`mechanics.nim:660`, `668`, `719`, `438`). Ownership and scoring always use the true
team.

## 6. Vision, hearing, sound

- **Vision** (`sim.nim:704-730`): per cog, a 120-degree cone centred on the cog's current aim
  point, unlimited range, blocked by cover and terrain (eye height 120 over ground). Initial aim is
  the enemy home (`mechanics.nim:139`). Aim persists between ticks; see policy-surface.md for what
  sets it. Dead cogs see nothing.
- **Team vision** (`"vision": "team"`, rules 42) is opt-in; no deployed variant sets it
  (manifest `variants`).
- **Speech**: see policy-surface.md. Radius `Width div 5` = 1,280 units (12.8 m), both teams hear,
  independent of vision (`bots.nim:508-517`).
- **Sound cues** (`mechanics.nim:29-58`): footsteps (every 12 ticks while moving and not
  sneaking, 1,000 units), gunfire (3,500), explosion (5,000), spray (1,800). A cue gives kind,
  one of 8 compass sectors, a distance band (<= 600, <= 1,800, farther) and age; never identity
  or position. Up to 12 per listener; lifetime 24 ticks.

## 7. Modes and config keys

Config keys the engine reads (`coworld.nim:16-23`, `match_config.nim:43-109`, `game.nim:425-449`,
`488-494`):

| Key | Values | Effect |
| --- | --- | --- |
| `tokens` | one per seat | the match's seat count (0.3.75+): 2-256 in the engine, exactly 16 in the paintbot-pw schema |
| `seed` | int32 | world RNG; variants all set 2026 (whether the platform overrides it per episode is an **open question**) |
| `max_ticks` | 1..28,800 | match cap; the engine clamps teams to 14,400 and FFA-kin to 8,640 (`sim.nim:855-859`) |
| `mode` | `teams` (default), `ffa_kin` | game mode |
| `map` | `""` (Heartwick) or one of 12 generated maps | terrain and item layout (`maps.nim:5-8`) |
| `vision` | `""`, `team` | teams only |
| `glory` | object (section 1): 7 keys since rules 47 (`behind_cogs`, `behind_cogs_seconds` added) | teams only; rejected in FFA-kin |
| `kin_layout` | `sampled`, `fours`, `pairs`, `trios_loner`, `cousins`, `strangers`, `clones`, `tribes` (0.3.75+: families of 5) | FFA-kin only |

### Deployed variants (manifest 0.3.78)

| Variant | Config beyond seed/players |
| --- | --- |
| `competition`, `1v1`, `2v2` | `glory: {behind_lives: 5, behind_cogs: 10}`, `max_ticks: 14400`, 16 slots (identical engine config; `1v1`/`2v2` are still 16-seat matches) |
| `map-<name>` x 12 | the same plus `map` |
| certification | no glory key, `max_ticks: 240`, 2 `basic-jev` + 14 `baseline` seats |

The `heartland` and `heartland-big` variants were removed from this manifest in 0.3.71
(commit `b08b6a1`). Heartland is now its own coworld, `heartland` (0.1.9 = `570174a2` on
2026-09-29, tags `heartland-v*`), built from the same engine with `"mode": "ffa_kin"`; its
`heartland-big` variant plays 50 seats in 10 tribes of 5 (guide lines 397-414). The main
`paintbot-pw` league's `variant_rotation` lists only `1v1` ("Two policy teams"; live league
settings read 2026-09-28, [field.md](field.md)); its engine config is identical to
`competition`'s.

### Maps

- **Heartwick** (default): bounds (-4800, -2800) to (11200, 6800), i.e. 160 x 96 m
  (`sim.nim:331-338`), an island with an inland lake, symmetric under a half turn about
  (3200, 2000). The "6400 x 4000 arena" in guide line 100 is the nominal frame (`Width`/`Height`,
  `sim.nim:15-16`), not the playable area.
- **Generated maps** (`maps.nim:5-8`): `twin-mesas`, `archipelago`, `serpent-river`, `crater`,
  `terraces`, `deep-forest`, `badlands`, `atoll`, `highlands`, `delta`, plus `big-twin-mesas` and
  `big-deep-forest` (about 10x the area). Each carries its own bounds, hearts, pickups, trenches
  and cover, all mirrored (`mechanics.nim:108-127`). Since 0.3.66 the big maps scale hearts,
  supplies and trenches with area (100 / 126 hearts; section 3) instead of keeping the
  ten-heart set, and each glory-heart spawn places one pair per ten hearts. Use `mapMinX/Y`, `mapMaxX/Y`, `controlX/Y`,
  `pickupX/Y` instead of Heartwick constants.
- **Big maps and int32:** squared distances on a 50,000-unit map exceed int32 and wrap in BASIC.
  `base.bas`'s `isqrt` comment ("23170^2 exceeds any squared map distance") is false there
  (**inferred** from map size and BASIC's wrapping arithmetic).

### FFA-kin (Heartland) differences (`mechanics.nim:266-318`, `753-764`, `sim.nim:1015-1022`)

Heartland is a separate coworld now (section 7), so this is reference only.

- 16 separate players (50 in Heartland Big); `selfTeam` is the seat. No glory, no meter, no elimination win.
- 10 HP, one life (a dead cog is out; its hearts go neutral at once), gun range 2,000.
- All 10 hearts start neutral. Exactly one cog touching captures in 72 ticks; any second cog
  (kin included) pauses; the owner alone on its heart resets progress. An owned heart pays its
  owner 1 point per second.
- Territory boost: on ground owned by seat j, speed x (100 + b)/100 and gun spread x (100 - b)/100,
  with b = 30 x rPercent(me, j) / 100: 30 own, 15 sibling, 7 cousin (`sim.nim:1379-1394`).
- Two great hearts: 3+ living cogs within 200 units for 120 ticks split 60 points equally
  (integer tenths, remainder dropped), then dormant 60 s; progress decays 1/tick below quorum.
- Ends at 8,640 ticks or when at most one cog is left; `outcome: "ended"`.
- `scores[i]` = sum over j of r(i, j) x s_j, in points (s in tenths / 10), where r is 1 self or
  clone, 1/2 sibling, 1/4 cousin, 0 stranger (`kinship.nim:67-73`).
- **Rules 48 fog of war** (0.3.78): a cog out of view reads -1 from `kin`, `gene`, `seatScore`
  and `seatAlive`, and its ffa.v1 observation row is zeroed (`sim.nim:240-245`,
  `bots.nim:310-327`). Before rules 48 these were public.

## 8. Guide/code disagreements found

| Guide says | Code at `570174a2` says |
| --- | --- |
| "20,000 instructions" / "50,000 work units" budget (guide lines 720, 800; same in `base.bas` and `jev.bas` header comments) | 50,000 instructions and 125,000 work units per decision at 16 seats (`bots.nim:154-155`); guide line 140 has the right numbers |
| `jev.bas` keeps `useRetreat`/`useDial` switched off (guide line 814) | both are `1` in the deployed `jev.bas` (`jev.bas:580-581`, comment "On since 2026-09-23") |
| Spray "roughly 62-degree cone" (guide line 317) | half-width 4/5 of distance at rules 40+, about a 77-degree cone (`mechanics.nim:23-27`); guide line 88 agrees with the code |
| "6400x4000 arena" (guide line 100) | playable Heartwick is 16,000 x 9,600 (`sim.nim:331-338`) |
| `outcome` implied to report time limits | `"time_limit"` means draw; timed-out decisive matches report the winner (section 2) |
| A seat that fails to load forfeits and the episode continues (guide lines 104-108, `host.py:112-124`) | true only for host-side checks (WASM, size, UTF-8, ZIP). A BASIC **compile** error ends the whole episode (see policy-surface.md, section 4) |
| Neural decoder "deterministically selects the largest logit" (guide line 855) | true by default; schema-2 bundles may enable sampling and other decoder options (`neural_basic.md`) |

## 9. Open questions

- Whether the platform overrides `seed` per episode (variants fix 2026).
- Whether live league episodes already carry `glory: {behind_lives: 5, behind_cogs: 10}` (the
  0.3.78 manifest says so; not yet seen in a live `game_config`, section 1.2).
- What the platform does with a `player_failure` file written by `forfeit_seat` when the episode
  still completes and writes results (`host.py:31-40`). The file is overwritten if more than one
  seat forfeits.
