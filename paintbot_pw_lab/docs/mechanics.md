# Paintbot PW mechanics (as deployed)

> **Currency.** Verified against Metta-AI/paintbot-pw commit `7b2b19f5` (tag
> `coworld-v0.3.65`), which is coworld `paintbot-pw` 0.3.65
> (`cow_5ac64504-6d4e-47c2-8476-9771d2d00cd9`), replay rules version 45. `main` is one commit
> ahead (`b590fc1`, mapgen heart area) and is **not** what the league runs. Line numbers below
> are at `7b2b19f5`. Re-verify when the coworld version changes: diff `examples/paintbot/sim.nim`,
> `mechanics.nim`, `game.nim`, and the deployed manifest's `variants`.

This is **Paintbot on Polyworld**: a Nim engine where every seat is a BASIC script run inside the
game pod (`player_runtime: game-hosted`). It is not the older Paintbot (Season 1 capture-the-heart
shooter, Season 2 battle royale with WASM plays); nothing here carries over from that lab.

Paths are relative to the repo root. `sim.nim` and `mechanics.nim` are under `examples/paintbot/`
(`mechanics.nim` is `include`d into `sim.nim`, `sim.nim:1415`). The game guide is
`coworld/paintbot/guide.md`; the manifest's `docs.readme` is that guide minus its
`readme:skip` blocks (checked by diff). Companion page: [policy-surface.md](policy-surface.md).

## 1. The one thing to get right: winning vs. glory

The **heart meter decides who wins. Glory is the score the platform receives**, and a loser's
glory is set to zero. The ladder therefore sees one number per seat: the winning team's glory, or
0. A win is necessary for any score, and a *fast* win is worth more than a slow one.

| | Heart meter (win condition) | Glory (reported score, teams game) |
| --- | --- | --- |
| Starts at | 0 per team | match length in seconds: `endTick div 24` = 600 for 14,400 ticks (`sim.nim:824-826`) |
| Changes | +1 tick-point per owned control heart per tick (`mechanics.nim:768-769`) | -1 per second, floored at 0 (`sim.nim:891-892`); plus awards below |
| Ends match when | a team reaches `hearts * 4320 / 2` = 21,600 tick-points = 900 points (`sim.nim:873-875`, `mechanics.nim:784`) | never ends the match |
| At match end | higher meter wins; equal = draw (`mechanics.nim:785`) | loser set to 0; draw sets **both** to 0 (`sim.nim:950-954`) |
| Reported as | not reported | `scores[i]` = glory of seat i's team (`sim.nim:964-965`) |

### How glory is computed (rules 37-45, `sim.nim:877-954`)

Each tick, after the tick counter advances (`mechanics.nim:771-772`):

1. **Countdown.** On every tick divisible by 24, each team loses 1 glory, floored at 0
   (`sim.nim:891-892`).
2. **Quiet supplies.** When `tick - lastSupplyTick[team] >= quiet_supplies_seconds * 24`, the team
   earns `quiet_supplies` and the clock restarts (`sim.nim:894-897`). The clock restarts whenever a
   teammate *takes* any pickup: grenade, spray, medkit, armor or uniform (`mechanics.nim:548-549`).
   A pickup is only taken when it is useful (for example a medkit only when hurt,
   `mechanics.nim:534-547`), so walking over a medkit at full health does not reset it.
3. **Behind in lives.** On every tick divisible by `behind_lives_seconds * 24`, lives are summed
   per team (`equipment.lives`, which counts the current life), and the team with fewer lives
   earns `behind_lives * (enemyLives - ownLives)` (`sim.nim:898-903`).
4. **Glory hearts** (before the counter advances, `mechanics.nim:764`): the first living cog within
   120 units of a glory heart earns `heart` glory for its team (`sim.nim:918-948`). Seat order
   alternates each tick for fairness (`sim.nim:932`).

Friendly-fire glory existed in rules 37-38 only; it is gone at rules 45 (`mechanics.nim:371-373`).

Award values (config key `glory`, teams game only, `game.nim:158-188`; defaults `sim.nim:31-47`):

| Key | Engine default | **Deployed teams variants** | Meaning |
| --- | --- | --- | --- |
| `quiet_supplies` | 10 | 10 | glory per quiet stretch |
| `quiet_supplies_seconds` | 30 | 30 | stretch length |
| `behind_lives` | 1 | **5** | glory per life behind, per period |
| `behind_lives_seconds` | 5 | 5 | period |
| `heart` | 20 | 20 | glory per glory heart |

Every teams variant in the 0.3.65 manifest sets `"glory": {"behind_lives": 5}`. The
`certification` config sets no glory key, so it pays the engine default of 1.

**Practical consequences** (arithmetic from the rules above, not measured):

- A win at time *t* seconds is worth about `600 - t + awards`. The guide reports that league
  matches usually end by elimination at roughly a quarter of the clock (guide line 199); that is
  about 450 plus awards. This is a claim from the guide, not verified here.
- Being behind in lives pays heavily at the deployed setting: 5 glory per life behind, every 5
  seconds. Trailing by 8 lives for one minute pays 12 x 40 = 480. That only counts if the team
  still wins.
- Skipping supplies pays +10 per 30 s. Collecting any supply forfeits the running stretch.
- Glory hearts (+20) spawn in mirrored pairs from 0:20, every 10-20 s, live 30 s, on random
  open dry spots (`sim.nim:36-43`, `905-948`). They are fog-gated (see policy-surface.md).
- Mean score and win rate are different questions. A policy that wins 60% slowly can score below
  one that wins 50% fast. The ladder resolves this in favour of glory: since 2026-09-28 its Elo
  uses `margin_scale: 1000`, so each episode counts as `clamp(0.5 + (our glory - their glory) /
  2000, 0, 1)` (metta `elo.py:183-187`; see [field.md](field.md)).

## 2. Teams, seats, and match flow (teams mode)

- **16 seats. Team = `slot mod 2`**: even = Red (team 0, "Ember"), odd = Blue (team 1, "Azure")
  (`sim.nim:9`, `223`; names `game.nim:274`). The manifest's `slots[].team` labels are not read by
  the engine (`applyGameConfig` reads only `mode`, `kin_layout`, `glory`, `game.nim:321-332`;
  `CoworldConfig` fields are `coworld.nim:16-23`).
- **Tick rate** 24/s (`sim.nim:10`). **Match length** `min(max_ticks, 14400)` ticks = at most
  10:00 (`sim.nim:12`, `818-819`). Every teams variant sets `max_ticks: 14400`.
- **Ending** (`mechanics.nim:765-787`), checked every tick after scoring:
  1. **Elimination**: a team is out when every cog has `hp <= 0` and `lives == 0`. The survivor's
     meter is raised to full, the match ends, and the higher meter wins, so the survivor wins
     (`mechanics.nim:775-785`). Both out on the same tick: meters as they stand decide.
  2. **Meter full**: either team reaches 21,600 tick-points.
  3. **Time**: `tick >= endTick`; higher meter wins, equal is a draw.
  Simultaneous fills: higher meter wins, equal is a draw (`mechanics.nim:785`).
- **Seat order.** Seats act in slot order, but each even/odd pair is swapped on odd ticks, so
  neither team always moves first (`mechanics.nim:518-524`).

### Result fields

`finishCoworld` writes (`game.nim:441-442`, type `coworld.nim:49-56`, snake_case `coworld.nim:86-105`):

| Field | Value | Notes |
| --- | --- | --- |
| `scores` | 16 floats | teams: team glory per seat (`sim.nim:964-965`); FFA-kin: kin-weighted score (section 7) |
| `ticks` | final tick | |
| `seed` | world seed | |
| `outcome` | `"0"` (Red won), `"1"` (Blue won), `"time_limit"`, or `"ended"` (FFA-kin) | `game.nim:420-422` |
| `banked_gold` | always `[]` | shared Polyworld result type; paintbot never fills it |
| `returned` | always `[]` | same |

**Finding: `outcome: "time_limit"` means a draw, not "the clock ran out".** `matchOutcome` returns
`"time_limit"` whenever `winner < 0`, and at rules 45 a teams match always ends with `winner` set
to 0, 1 or -2 (draw) (`mechanics.nim:785`). A match decided on the meter at 10:00 reports `"0"` or
`"1"`; a draw by any route (time, equal meters, mutual elimination) reports `"time_limit"`.

## 3. Hearts and territory (teams mode)

- **10 control hearts**, all equal income (1 tick-point per tick each; big hearts ended at rules
  27, `sim.nim:870-871`). Hearts 0 and 1 start owned by Red and Blue; the rest start neutral
  (`mechanics.nim:171`). Base hearts are ordinary hearts and can be captured.
- **Touching** a heart: alive, within 140 units, and a traversable line to it (no height step
  over 25 units per 20-unit sample, `sim.nim:327-337`) (`mechanics.nim:327`).
- **Capture** (`mechanics.nim:329-348`): one team touching and not the owner accumulates 1 tick per
  tick; at 72 ticks (3 s) ownership flips directly to the attacker (no neutral step). Both teams
  touching: progress pauses. Nobody, or only the owner: progress resets. A different attacking
  team starts from 0. More cogs do not speed it up.
- **Territory** is the nearest-heart region (`sim.nim:1311-1319`). In the teams game it is only a
  display; it has no mechanical effect (the boost applies in FFA-kin only, `sim.nim:1326`).
- **Heartwick heart positions** before nudging (`mechanics.nim:168-185`), each odd index the half
  turn of the even one before it about (3200, 2000): 0 red home (960, 2000); 1 blue home
  (5440, 2000); 2 (-3000, 500); 4 (1000, -1600); 6 (-3000, 3500); 8 (3200, 1250) (lake heart).
  Read positions from `controlX/Y` at runtime rather than hard-coding them.

## 4. Lives, spawning, health

| Item | Value | Source |
| --- | --- | --- |
| Base HP | 3 (FFA-kin 10) | `sim.nim:61`, `68`, `279-281` |
| Lives | 4 per cog: the first life plus 3 respawns. `livesLeft` counts the current life | `mechanics.nim:138`, `436` |
| Respawn delay | 72 ticks (3 s) | `sim.nim:23`, `mechanics.nim:439` |
| Spawn protection | 36 ticks; all damage ignored (`shield > 0`) | `sim.nim:754`, `mechanics.nim:363` |
| On death | equipment wiped (grenade, spray, armor, charge), uniform removed | `mechanics.nim:437-438` |

- **Where you spawn** (`sim.nim:718-761`, `mechanics.nim:587-602`): if the team owns any heart,
  within 350 units of an owned heart chosen by a softmax over the summed distance from living
  teammates (temperature 1000, distances quantized to 10). Larger sums (less-covered hearts) are
  favoured. If the team owns no heart, a random point in the team's end zone. Crowded or blocked
  placements retry next tick. Initial spawns use the same heart rule (`sim.nim:863-865`).

## 5. Combat

Units: 1 unit = 1 cm; `Radius` (body) = 55 (`sim.nim:17`).

### Movement

- Speed 28 units/tick (`sim.nim:18`). Sneak halves it (`mechanics.nim:618`). Water quarters it
  (7 units/tick) (`mechanics.nim:619-621`). Leaving a trench (moving away from its centre) is
  slowed 5x per axis (`mechanics.nim:624-630`). Effects stack.
- Bodies are solid to everyone (`sim.nim:709-717`). A blocked cog sidesteps
  (`mechanics.nim:636-649`).
- The engine pathfinds (`waypointFor`, `mechanics.nim:510-516`) on a 1 m grid where a lake cell
  costs 4 (rules 38), and at rules 45 routes into water when the goal itself is wet (lake hearts)
  (`sim.nim:1160-1310`).

### Gun (the default weapon; `mechanics.nim:674-727`)

- `shootAt` with cooldown 0 starts a **5-tick windup**. The aim is locked at the order as a
  vector relative to the shooter; the ray leaves from wherever the shooter stands when the windup
  ends.
- Cooldown 24 ticks (1 shot/s), **tripled to 72** if the shooter has armor or is in a trench
  at the moment of the order (`mechanics.nim:725-727`). The check also reads `carrying`, which
  nothing sets under rules 45.
- Hitscan: samples every 20 units out to 5,250 units (FFA-kin 2,000); stops at cover or the map
  edge; the **first** body within 55 units of the ray with a clear sight line takes 1 damage.
  **Friendly fire is on**: teammates block and take hits (`mechanics.nim:704-714`).
- Trench cover: a victim in a different trench from the shooter is skipped 70% of the time and
  the ray continues (`mechanics.nim:710-712`).
- Spread: small random jitter scaled by height difference, 25% less per metre the shooter stands
  above the target, clamped to 50-150% (`mechanics.nim:60-63`, `682-692`). At 20 m the lateral
  error is at most about 24 units, less than the body radius; the main source of misses is the
  target moving during the windup (**inferred** from the jitter bound).
- All gun targets in a tick are chosen before damage, so mutual kills happen (`mechanics.nim:728-730`).

### Spray can (`mechanics.nim:665-673`, `498-508`, `734-741`)

- A carried can **replaces the gun** and is never used up; you keep it until death.
- `shootAt` with spray cooldown 0 starts a 5-tick burst; next burst 13 ticks later (5 + 8).
- Cone: forward along the aim to 850 (+55) units, half-width `4/5 * along` (+55), clear sight
  line required. Each victim takes 3 damage once per burst. Hits teammates too; spawn-protected
  cogs are skipped.

### Grenade (`mechanics.nim:655-664`, `472-496`)

- Carry one. `chargeGrenade(1)` adds 1 charge per tick, up to 24. The tick you stop charging (charge
  > 0), it is thrown along your aim: range `150 + 1130 * charge / 24` with charge clamped to at least 1, so about 197 to 1,280 units (`mechanics.nim:474-475`).
  It flies over walls and lands 10 ticks later.
- Blast: every body within 360 + 55 units takes 3 damage in the open, 6 if in the trench it
  landed in, 2 if in a different trench. **Includes allies and the thrower.**

### Armor, medkits, pickups (`mechanics.nim:526-552`)

| Kind (`pickupKind`) | Taken when | Effect | Respawn |
| --- | --- | --- | --- |
| 0 grenade | not holding one | carry one grenade | 120 ticks (5 s) |
| 1 spray | not holding one | replaces gun until death | 720 ticks (30 s) |
| 2 medkit | `hp < max` | full HP | 720 |
| 3 armor | armor < 3 | armor = 3, absorbed before HP; **triples gun cooldown** while > 0 | 720 |
| 4 uniform | not disguised, not attacking this tick | disguise (below) | 720 |

Pickup reach is 120 units. On Heartwick the layout is 2 uniforms, 4 grenades, 2 sprays, 2 armors,
6 medkits (the base pair plus two deep-wilderness pairs) and 6 trenches of 280 x 280
(`mechanics.nim:133-185`; count **inferred** by reading the placement code, not run). Generated
maps place their own items (`mechanics.nim:108-127`).

### Trenches

Walkable pits: slow to leave, triple gun cooldown for occupants, 70% protection from outside
gunfire, heavy grenade damage inside (all covered above). Trench geometry is public.

### Disguise (uniforms, `sim.nim:282-292`)

A disguised cog appears to others as seat `slot xor 1` (a real enemy seat number) and as the
other team. The disguise drops on a gun order, spray burst, grenade release (charging alone keeps
it) or death (`mechanics.nim:659`, `667`, `718`, `438`). Ownership and scoring always use the true
team.

## 6. Vision, hearing, sound

- **Vision** (`sim.nim:682-708`): per cog, a 120-degree cone centred on the cog's current aim
  point, unlimited range, blocked by cover and terrain (eye height 120 over ground). Initial aim is
  the enemy home (`mechanics.nim:139`). Aim persists between ticks; see policy-surface.md for what
  sets it. Dead cogs see nothing.
- **Team vision** (`"vision": "team"`, rules 42) is opt-in; no deployed variant sets it
  (manifest `variants`).
- **Speech**: see policy-surface.md. Radius `Width div 5` = 1,280 units (12.8 m), both teams hear,
  independent of vision (`bots.nim:467-476`).
- **Sound cues** (`mechanics.nim:29-58`): footsteps (every 12 ticks while moving and not
  sneaking, 1,000 units), gunfire (3,500), explosion (5,000), spray (1,800). A cue gives kind,
  one of 8 compass sectors, a distance band (<= 600, <= 1,800, farther) and age; never identity
  or position. Up to 12 per listener; lifetime 24 ticks.

## 7. Modes and config keys

Config keys the engine reads (`coworld.nim:16-23`, `game.nim:295-332`, `369-375`):

| Key | Values | Effect |
| --- | --- | --- |
| `seed` | int32 | world RNG; variants all set 2026 (whether the platform overrides it per episode is an **open question**) |
| `max_ticks` | 1..28,800 | match cap; the engine clamps teams to 14,400 and FFA-kin to 8,640 (`sim.nim:816-820`) |
| `mode` | `teams` (default), `ffa_kin` | game mode |
| `map` | `""` (Heartwick) or one of 12 generated maps | terrain and item layout (`maps.nim:5-8`) |
| `vision` | `""`, `team` | teams only |
| `glory` | object (section 1) | teams only; rejected in FFA-kin |
| `kin_layout` | `sampled`, `fours`, `pairs`, `trios_loner`, `cousins`, `strangers`, `clones` | FFA-kin only |

### Deployed variants (manifest 0.3.65)

| Variant | Config beyond seed/players |
| --- | --- |
| `competition`, `1v1`, `2v2` | `glory.behind_lives: 5`, `max_ticks: 14400` (identical engine config) |
| `map-<name>` x 12 | the same plus `map` |
| `heartland` | `mode: ffa_kin`, `kin_layout: cousins`, `max_ticks: 8640` |
| `heartland-big` | `mode: ffa_kin`, `map: big-twin-mesas`, `max_ticks: 8640` (no `kin_layout`: sampled) |
| certification | no glory key, `max_ticks: 240`, 2 `basic-jev` + 14 `baseline` seats |

Which variant the main `paintbot-pw` league runs is not in the repo; the guide says Heartland runs
`heartland` (guide line 391). The main league most likely runs `competition` (**inferred**).

### Maps

- **Heartwick** (default): bounds (-4800, -2800) to (11200, 6800), i.e. 160 x 96 m
  (`sim.nim:312-319`), an island with an inland lake, symmetric under a half turn about
  (3200, 2000). The "6400 x 4000 arena" in guide line 100 is the nominal frame (`Width`/`Height`,
  `sim.nim:15-16`), not the playable area.
- **Generated maps** (`maps.nim:5-8`): `twin-mesas`, `archipelago`, `serpent-river`, `crater`,
  `terraces`, `deep-forest`, `badlands`, `atoll`, `highlands`, `delta`, plus `big-twin-mesas` and
  `big-deep-forest` (about 10x the area). Each carries its own bounds, hearts, pickups, trenches
  and cover, all mirrored (`mechanics.nim:108-127`). Use `mapMinX/Y`, `mapMaxX/Y`, `controlX/Y`,
  `pickupX/Y` instead of Heartwick constants.
- **Big maps and int32:** squared distances on a 50,000-unit map exceed int32 and wrap in BASIC.
  `base.bas`'s `isqrt` comment ("23170^2 exceeds any squared map distance") is false there
  (**inferred** from map size and BASIC's wrapping arithmetic).

### FFA-kin (Heartland) differences (`mechanics.nim:266-318`, `752-763`, `sim.nim:956-963`)

- 16 separate players; `selfTeam` is the seat. No glory, no meter, no elimination win.
- 10 HP, one life (a dead cog is out; its hearts go neutral at once), gun range 2,000.
- All 10 hearts start neutral. Exactly one cog touching captures in 72 ticks; any second cog
  (kin included) pauses; the owner alone on its heart resets progress. An owned heart pays its
  owner 1 point per second.
- Territory boost: on ground owned by seat j, speed x (100 + b)/100 and gun spread x (100 - b)/100,
  with b = 30 x rPercent(me, j) / 100: 30 own, 15 sibling, 7 cousin (`sim.nim:1320-1335`).
- Two great hearts: 3+ living cogs within 200 units for 120 ticks split 60 points equally
  (integer tenths, remainder dropped), then dormant 60 s; progress decays 1/tick below quorum.
- Ends at 8,640 ticks or when at most one cog is left; `outcome: "ended"`.
- `scores[i]` = sum over j of r(i, j) x s_j, in points (s in tenths / 10), where r is 1 self or
  clone, 1/2 sibling, 1/4 cousin, 0 stranger (`kinship.nim:43-49`).

## 8. Guide/code disagreements found

| Guide says | Code at `7b2b19f5` says |
| --- | --- |
| "20,000 instructions" / "50,000 work units" budget (guide lines 678, 758; same in `base.bas` and `jev.bas` header comments) | 50,000 instructions and 125,000 work units per decision (`bots.nim:147-148`); guide line 135 has the right numbers |
| `jev.bas` keeps `useRetreat`/`useDial` switched off (guide line 772) | both are `1` in the deployed `jev.bas` (reference `jev.bas:580-581`, comment "On since 2026-09-23") |
| Spray "roughly 62-degree cone" (guide line 312) | half-width 4/5 of distance at rules 40+, about a 77-degree cone (`mechanics.nim:23-27`); guide line 88 agrees with the code |
| "6400x4000 arena" (guide line 100) | playable Heartwick is 16,000 x 9,600 (`sim.nim:312-319`) |
| `outcome` implied to report time limits | `"time_limit"` means draw; timed-out decisive matches report the winner (section 2) |
| A seat that fails to load forfeits and the episode continues (guide lines 104-108, `host.py:111-123`) | true only for host-side checks (WASM, size, UTF-8, ZIP). A BASIC **compile** error ends the whole episode (see policy-surface.md, section 4) |
| Neural decoder "deterministically selects the largest logit" (guide line 813) | true by default; schema-2 bundles may enable sampling and other decoder options (`neural_basic.md`) |

## 9. Open questions

- Whether the platform overrides `seed` per episode (variants fix 2026).
- Which variant the main league runs (assumed `competition`).
- What the platform does with a `player_failure` file written by `forfeit_seat` when the episode
  still completes and writes results (`host.py:31-40`). The file is overwritten if more than one
  seat forfeits.
