# James Botts policy

The Gods of the Arena policy for the James Botts player, built from modules. Its first
capability is footman last-hitting; the module layout is meant to be wrapped by a
larger fighting and sieging policy later. Design and engine evidence:
[docs/designs/2026-09-17-lasthit-policy.md](../docs/designs/2026-09-17-lasthit-policy.md).

## Layout

| Path | Contents |
| --- | --- |
| `modules/00_config.bas` | Tunable knobs (`cfg*`), set every decision by `cfgInit()`, including the per-class chase list (`cfgChaseClass`). No logic. |
| `modules/10_scan.bas` | One pass over the object list into typed arrays (`ef*` enemy footmen, `af*` allied footmen, `at*` allied towers, `et*` enemy towers and barracks with HP, `ah*`/`eh*` heroes, forts). Footmen beyond `cfgScanRadius` are skipped. `lhRingSlot(id)` maps any object id to the shared drop-event ring (footmen, heroes at 448+, structures at 458+). |
| `modules/20_lasthit.bas` | The last-hit planner `lhPlan()`: HP prediction per enemy footman, kill windows, secure casts, poison, standoff point. |
| `modules/22_ksteal.bas` | `ksPlan()`: the finishing blow on enemy heroes and structures that teammates are already fighting; predicts HP at the landing tick of the basic hit and of each ready strike (per-class table) from the shared drop rings; never starts a fight; sets `ksHold` so farming holds spells while an enemy hero is within 10 tiles. |
| `modules/25_punish.bas` | `pnPlan()`: attack an enemy hero that an allied tower is firing at (it is farming inside our tower's reach with no footman left to absorb the shots); enter/exit hysteresis on distance to the tower, HP gates. First fight behavior; the engine auto-casts the kit once the target is set. |
| `modules/30_survive.bas` | `svPlan()`: retreat on an enemy hero or tower threat, or when low with a heal in hand; heal use. |
| `modules/40_shop.bas` | `shScanInventory()` and `shBuy()`: poison while footmen take two hits, heal when hurt, then equipment into every slot but one (damage items first, then HP) so income becomes stats. |
| `modules/90_main.bas` | Per-tick top-level flow: bookkeeping, plans, action priority, telemetry. The only module with top-level statements. |
| `build.py` | Concatenates `modules/*.bas` in name order into `dist/james_botts.bas`. |
| `dist/james_botts.bas` | The uploadable artifact (generated; commit it so uploads are reproducible). |
| `experiments/` | Scratch copies for parallel experiments (for example `experiments/codex/`). Not uploaded. |

BASIC has no include and every variable is global (256 at most), so each module owns a name
prefix, top-level subs share the `o*` scratch names (`oI`, `oJ`, `oDx`, ...) and leaf subs
called from their loops share the `i*` names; never hold an `o*` value across a call into a
sub that uses `o*`, or an `i*` across a call into another leaf.
Modules 00 to 89 contain only `DIM`s and `SUB`s; `90_main.bas` holds the top-level code.
The dialect has no `ELSEIF`, `FOR`, functions, or strings; see
[../README.md](../README.md) and [../docs/policy-capabilities.md](../docs/policy-capabilities.md).

## The last-hit module interface

`lhPlan()` reads the scan arrays and self data and rewrites these globals each decision:

| Global | Meaning |
| --- | --- |
| `lhState` | 0 no enemy footmen in play, 1 waiting for a window, 2 striking now |
| `lhTargetId` | Footman to order `attackTarget` on now, or 0 |
| `lhSecureSlot`, `lhSecureId` | Ability slot and footman for a securing cast, or -1 and 0 |
| `lhPoisonId` | Footman to poison this decision (`attackTarget` it, then `useItem`), or 0 |
| `lhHoldX`, `lhHoldY` | Tile to walk toward while waiting; the standoff point |
| `lhStickId` | Input: the footman ordered last decision, kept while it can still convert |

`90_main.bas` applies them in priority order: retreat, punish target, kill-steal target,
secure cast, poison, attack order, else walk to the hold point. The policy does not push structures (James's
direction, 2026-09-17): the objective is farm, a level and item lead over the enemy heroes,
and punishing tower dives. A larger policy calls `lhPlan()` after `scanObjects()` and
may override any output; the module itself never calls an action.

## Build, evaluate, upload

```sh
python3 gods_of_the_arena_lab/policy/build.py                       # -> dist/james_botts.bas
uv run python gods_of_the_arena_lab/tools/lasthit_eval.py \
  --candidate gods_of_the_arena_lab/policy/dist/james_botts.bas --mirror --episodes 2
uv run python gods_of_the_arena_lab/tools/lasthit_eval.py \
  --candidate gods_of_the_arena_lab/policy/dist/james_botts.bas --episodes 2   # versus base.bas, both sides
uv run coworld upload-policy --file gods_of_the_arena_lab/policy/dist/james_botts.bas --name james-botts-gota
```

A full local match runs in about five seconds. Mirror games (the candidate in all ten
seats) last the full 28,800 ticks; games against the starter end in two to six minutes
because a farm-only team never defends, so compare rates per 1,000 ticks there.

## Telemetry

Every 240 ticks each hero prints one line to its private log:

```
LH tick lastHits heroKills towerKills level orders secures poisons lost deaths gold 0 0 punishStarts punishTicks punishChaseTicks chaseTicks ksHeroWindowTicks ksCasts ksStructWindowTicks ksPrepTicks
```

Income is inferred from gold increments (footman 15, hero 100); the harness checks
`25 * lastHits + 150 * heroKills + 100 * towerKills` against `total_xp`. `lost` counts
ordered targets that vanished unpaid; the two zero fields held `early` and `missed`
counters that were removed to stay under the 256-global limit.
With `cfgDebug = 1` the log also carries `ORD` and `LOST` event lines.

**PRINT budget.** The VM charges two print events per item (value plus separator) against
a limit of 128 events per decision, so a decision may print at most about 63 items in
total across all its `PRINT`s. Exceeding it disables the hero for the rest of the match.
Keep traces sparse and check which lines can coincide on one tick.

## Results so far (2026-09-17)

Local mirror (the policy in all ten seats, seeds 2026 and 2027): about 1,000 to 1,050
team last hits per 28,800-tick match out of 1,080 available, mean 207 per hero. Lane
pairs split unevenly (the ranged partner takes most); the solo middle-lane hero takes
about 340 of its lane's 360.

Hosted. Rows up to v5 used five candidate seats plus five random champions; from the
v5 baseline arm onward every request seats ONE copy of our policy plus nine random
champions, as league games do (James's rule, 2026-09-17). Games last 4,000 to 15,000 ticks:

| Version | Change | Last hits per hero per 1,000 ticks | Deaths per hero-match | Hero-matches |
| --- | --- | ---: | ---: | ---: |
| v1 | first working build | 3.9 | 3.45 | 40 |
| v2 | retreat when an enemy hero targets me; unsafe lane front is not walked to | 3.7 | 1.40 | 80 |
| v3 | ally-avoid rule off; weak classes idle at the standoff point | 4.4 | 1.95 | 80 |
| v3 (A/B baseline arm, same window as v4) | | 4.4 | 1.27 | 80 |
| v4 | hit history reset after any sighting gap | 4.5 | 1.53 | 80 |
| v4 (A/B baseline arm, same window as v5, 32 episodes) | | 4.3 | 1.60 | 160 |
| v5 | every class idles at the standoff point and lets the engine attack | 4.9 | 1.43 | 155 |
| v6 | punish module, distance trigger (superseded before evaluation: heroes farm at the edge of tower range untouched) | | | |
| v5 (one copy per game, baseline arm) | | 5.8 | 2.5 | 96 |
| v7 | punish module: attack the enemy hero an allied tower is firing at | 6.5 | 2.1 | 48 |
| v8 (built on v5, not v7) | chase-attack the anchor footman for the six melee and low-damage classes | 5.9 (v5 arm 5.8) | 2.0 | 48 |
| v7 (three-arm baseline, one copy) | | 6.0 | 4.0 | 48 |
| v9 | v7 plus the v8 chase-attack for melee and low-damage classes | 6.3 | 2.9 | 48 |
| v10 | v9 plus farming beside busy enemy towers and a chase-cost rule for punish | 6.0 | 3.1 | 48 |
| v9 (siege A/B baseline arm) | | 5.4 | 2.6 | 48 |
| v11 | v9 plus a siege module (removed again: took a structure per game but the win rate read 44% to 31%) | 5.5 | 2.2 | 48 |
| v9 (item-shop A/B baseline arm) | | 5.5 | 2.8 | 48 |
| v12 | siege removed; shop converts income into damage then HP across five slots | 5.6 | 1.7 | 48 |
| v12 (kill-steal A/B baseline arm) | | 5.6 | 2.7 | 48 |
| v13 | v12 plus the kill-steal module (heroes and structures); league entry | 6.2 | 1.9 | 48 |
| v13 (structure A/B baseline arm) | | 5.9 | 2.4 | 48 |
| v14 | v13 plus walking in for structure finishing hits behind a footman shield (the window never opened: no behavior change) | 5.8 | 2.1 | 48 |
| v13 (v15 A/B baseline arm) | | 5.7 | 1.7 | 48 |
| v13 (v16 A/B baseline arm) | | 5.4 | 2.6 | 48 |
| v16 | v13 plus area and ring ultimates on still targets (rejected: finishing casts 16 to 44 but hero kills 2.10 to 1.54, XP flat; knob off) | 5.7 | 2.1 | 48 |
| v15 | v13 plus a 12-tile approach toward enemy heroes a teammate is fighting (rejected: hero kills 2.65 to 1.58, deaths 1.73 to 2.42), and standing ready beside a shielded structure predicted to die within 10 s (never fired) | 5.7 | 2.4 | 48 |

The v3 versus v4 A/B (`tools/compare.py`, one observation per episode, 16 per arm) is
inconclusive: last hits per 1,000 ticks 4.40 to 4.54, adjusted p = 1.0. The instrument needs
about 30 episodes per arm for a directional verdict.

**One-copy games, exact replay counts (v5 versus v7, same window, 96 and 48 games):**

| Measure | v5 | v7 (punish) |
| --- | ---: | ---: |
| Our last hits per 1,000 ticks | 5.80 | 6.49 |
| Other seats in the same games | 4.52 | 4.52 |
| Our rank within team (1 = best of 5) | 2.47 | 2.19 |
| Our share of the team's footman last hits | 24% | 26% |
| Hero kills per match | 0.20 | 1.04 (adapter: improved, p = 0.02) |
| Deaths per 1,000 ticks | 0.25 | 0.20 |

With one copy per game the policy farms above the field's mean seat; the five-copy
rosters used earlier had our copies competing for the same footmen and understated it.
The punish module fired 124 times in 48 games (2.6 per game, 198 ticks each on average).

**Three-arm A/B (v7 / v9 / v10, one copy per game, 48 each, exact replay counts):**
last hits per 1,000 ticks 5.97 / 6.28 / 6.04 against 4.5 to 4.6 for the other seats;
rank within team 2.2 / 2.2 / 2.4; top of team 40% / 44% / 29%; hero kills per match
0.94 / 1.10 / 0.79; deaths per 1,000 ticks 0.35 / 0.30 / 0.27. All differences are
inside noise at this size (about ±0.5 per 1,000 ticks between repeats of the same
version). v9 is kept as the best build; v10's tower-adjacent farming and punish
chase-cost rule stay in the code behind knobs, off by default.

**Siege A/B (v9 / v11, one copy per game, 48 each, exact replay counts):** structures
killed per game 0.00 to 0.98 (towers 0.65, barracks 0.33; adapter: improved, p < 0.01),
last hits 5.4 to 5.5, deaths equal, hero kills 0.83 to 0.58, and team win rate 44% to 31%
(inconclusive; the standard error of a win rate at 48 games is about 7 points). The
module fired 3.8 times per game for 640 ticks. The mechanism works; whether pushing
structures with the current gates helps the team win is not yet decided.

**Where the remaining gap is** (time-budget analysis, `../docs/designs/2026-09-17-time-budget-analysis.md`):
presence matches the field; melee and low-damage classes attacked only 19 to 26% of the
ticks a creep was in reach because the standoff walk cancelled the engine's attack, so
v8/v9 chase-attack for those classes (attack fraction 38% to 50%, deaths down a third).
Tower avoidance is the one presence deficit left (11% of ticks near enemy towers versus
15 to 24%).

**Kill-steal A/B (v12 / v13, one copy per game, 48 each, exact replay counts):**

| Measure | v12 | v13 kill steal |
| --- | ---: | ---: |
| XP per 1,000 ticks (enemy mean about 202) | 146 | 183 |
| Hero kills per match | 0.62 | 2.48 |
| Share of enemy deaths within 12 tiles of us that were our kill | 8% | 30% |
| Last hits per 1,000 ticks (other seats 4.6) | 5.57 | 6.24 |
| Deaths per match | 2.67 | 1.90 |
| Level lead over the enemy team's mean hero | -1.09 | -0.06 |
| Team win rate | 35% | 42% |

The module took 22 finishing casts and about 117 hero-window ticks per game; structure
windows never opened in v13 or v14 (the finishing window on a 950-HP structure is about
one second, and the hero was never within reach when it came). v13 is the current league entry, and the league entry (submitted 2026-09-17,
`sub_38be3038-d8d1-4275-91da-557ee52ba109`).

**Level and XP against the enemy heroes (v9 / v12 arms, one copy per game, 48 each):**
our hero ends at level 5.9 / 6.0, 0.7 levels below the enemy team's mean hero and 3.5
below its best. XP per 1,000 ticks, ours 148 / 149 against the enemy mean 200 and the
best enemy 377. The composition explains it:

| XP per 1,000 ticks from | ours (v12) | enemy mean | best enemy |
| --- | ---: | ---: | ---: |
| footman last hits | 141 | 109 | 179 |
| hero kills | 8 | 75 | 160 |
| buildings | 0 | 16 | 37 |

We out-farm every enemy on footmen and lose the level race on hero kills: the field's
heroes kill each other, and a hero kill is worth six last hits. v12's shop and the
removal of siege cut our deaths from 2.8 to 1.7 per match (denying the enemy about 165
XP per game) and left farm unchanged; its level lead moved +0.1, inside noise.

**Against the field (exact, from re-simulated replays; five-copy era).** `tools/expand_replay.nim`
recovers every seat's footman last hits from the reward accounting, so the comparison
no longer depends on our telemetry. Over 72 verified hosted episodes (v1 to v4 batches,
360 of our hero-matches):

| Measure | Value |
| --- | ---: |
| Our rank by last hits within own team (1 = best of 5) | mean 3.1; top of team 19% |
| Our share of the team's footman last hits (even split = 20%) | 19% |
| Our place among the 16 policies seen, by last hits per hero per 1,000 ticks | 11th (4.3) |
| Top farmers in the same games | daf-gota-v1 7.1, black-kite 6.7, the unmodified starter 6.5, aaron 6.2, red-kite 6.1 |

The policies that out-farm us attack continuously; ours waited for predicted kill
windows. The v4 versus v5 A/B (32 episodes per arm, exact replay counts) tested that:
v5 4.88 versus v4 4.31 last hits per hero per 1,000 ticks (+13%), deaths per 1,000 ticks
0.24 versus 0.32, adapter verdict still inconclusive at this size. Rank within the team
stayed at 3.1 of 5 and the other seats in the same games averaged 5.3, so v5 is better
than v4 but still below the field's mean farmer.

Per class in v3 the ranged carries