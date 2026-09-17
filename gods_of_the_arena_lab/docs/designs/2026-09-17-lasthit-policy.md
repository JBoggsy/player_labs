# Last-hit policy: design

Living design for the first James Botts policy. Goal: a hero script that takes as many
footman last hits as possible, built as a module that a larger policy can wrap.
Engine facts below are read from polyworld `f2ab9598` (coworld 2026.9.16.5, the league's
current release, resolved with `tools/deployed_ref.py` on 2026-09-17).

## Problem

Income in Gods of the Arena is only the killing hit (25 XP and 15 gold per footman). A
hero that attacks continuously hands most kills to its own footmen and towers, because
its hits are not timed to cross zero. The starter policy attacks the nearest enemy and
takes whatever kills fall out.

## Goals and non-goals

Goals:

- Maximize footman last hits per match for one hero, in any of the ten seats.
- Keep the last-hit logic a self-contained module with a small, documented interface, so
  a fighting or sieging policy can call it and override its output.
- Ship activation telemetry so a null result can be attributed.

Non-goals for this iteration: hero fights, sieging, team coordination, spell combos.
The policy only avoids dying and buys damage.

## Engine facts the design rests on

- Tick order (`sim.nim` `tickWorld`): hero scripts decide, then footmen update, then
  towers, then heroes act. A basic hit ordered this tick lands after this tick's footman
  and tower damage.
- Basic hit timing (`updateHero`): when the target is in range the swing starts at 0 and
  the hit lands when `swingTicks >= duration * 45 / 100`; the next swing starts at
  `duration`. Leaving range resets the swing. `selfAttackCooldown` reports the ticks until
  the next landing for an uninterrupted target.
- Footmen swing every 32 ticks for 12 damage, landing at tick 14 of the swing
  (`footmanAttackTicks`, `updateFootman`). A footman targets the nearest visible enemy
  footman or hero within 5 tiles and keeps it while within 8.
- Towers hit every 24 ticks for 18/24/30 (outer/inner/gate). They target the nearest
  footman first and a hero only when no footman is in range.
- Idle heroes with no move target auto-acquire footmen (melee within 2.5 tiles, ranged
  within attack range) and then auto-cast every ready ability on that target. A hero that
  is walking does not auto-acquire. `walkTo` clears the attack target.
- `attackMove(x, y)` exists at this commit (800 work units): it walks and stops for
  enemies in the normal acquisition range.
- The object list is a snapshot per decision. `objectTarget` (16 work units) gives a
  footman's or tower's current target, which is what an attached attacker is.
- Poison potion applies 35 damage to the current attack target immediately when used,
  if the target is within basic-attack range.
- PRINT is limited to 128 events and 1,024 bytes per decision, and every printed item
  costs two events (value plus separator), so about 63 items per decision in total.
  Exceeding it disables the hero for the rest of the match.
- A reported `selfAttackCooldown` of C lands during the hero update C - 1 ticks from now
  (the swing counter increments before the hit check). A zero-delay melee strike cast
  from the script resolves inside the decision, before this tick's creep damage; a
  projectile resolves after the hero updates and travels at least one tick.
- Map (seed 54): Red fort (105,10), spawn (111,4); Blue mirrored at (10,105) and
  (4,111). Lane 0 runs along the north and west edges, lane 1 is the diagonal, lane 2
  runs along the east and south edges. Engine hero lanes by seat within a team are
  `[0, 0, 1, 2, 2]`. A tile's lane: `s = x + y - 115`; `|s| < 15` is the middle lane,
  `s <= -15` the north-west lane, `s >= 15` the south-east lane.

## Architecture

One BASIC file per upload, assembled from module files by `policy/build.py`, which
concatenates `policy/modules/*.bas` in name order into `policy/dist/james_botts.bas`.
BASIC has no include and all variables are global, so each module owns a name prefix.

| Module | Prefix | Responsibility |
| --- | --- | --- |
| `00_config.bas` | `cfg` | Tunable knobs (thresholds, margins, poison policy). No logic. |
| `10_scan.bas` | `sc` | One pass over the object list into arrays: id, kind, team, x, y, hp, alive, target. Derives own fort, enemy fort, lane of each footman. |
| `20_lasthit.bas` | `lh` | The last-hit planner. Reads scan arrays and self data; writes an intent (below). Tracks per-footman HP history for hit prediction. |
| `30_survive.bas` | `sv` | Minimal self-preservation: retreat when low with an enemy hero or tower near, potions. |
| `40_shop.bas` | `sh` | Damage-first purchases, poison stock. |
| `90_main.bas` | `main` | Dispatcher: call the modules, apply the highest-priority intent, emit telemetry. |

### Last-hit module interface

Inputs: scan arrays, `self*` data, `worldTick`, config knobs.

Outputs (globals, rewritten every decision):

| Global | Meaning |
| --- | --- |
| `lhState` | 0 no enemy footmen in play, 1 waiting for a kill window, 2 striking now |
| `lhTargetId` | Footman to order `attackTarget` on now, or 0 |
| `lhSecureSlot` | Ability slot to cast on `lhTargetId` to secure the kill, or -1 |
| `lhUsePoison` | 1 to use a poison potion on the current target this decision |
| `lhHoldX`, `lhHoldY` | Tile to walk toward while waiting (the standoff point) |

The dispatcher applies them in order: secure cast, poison, attack order, else walk to the
hold point. A larger policy calls `lhPlan()` and may ignore or override any of these.

### Hit prediction

For each visible enemy footman `f` the planner estimates its HP at the tick my next hit
would land:

- `landTick = worldTick + selfAttackCooldown` if `f` is already my target and in range,
  otherwise `worldTick + travelTicks + windup` where travel is the tile distance beyond
  my range divided by `selfMoveSpeed`.
- Incoming damage over that horizon: each allied footman whose `objectTarget` is `f`
  contributes 12 per 32 ticks; each allied tower targeting `f` contributes its tier
  damage per 24 ticks. Version 1 uses the expected value rounded up; version 2 will use
  observed HP-drop ticks per footman to phase the swings exactly.

Decision per footman: `predicted = hp - incoming(horizon)`. If `0 < predicted <=
selfAttackDamage`, ordering the attack now converts. If `predicted <= 0` the kill is
lost unless an instant source lands first: poison (35, immediate, needs range) or a
strike ability with zero cast delay. The planner picks the footman with the earliest
converting window, preferring the lowest predicted HP on ties.

Once `selfAttackDamage >= 60` (level 3 to 11 by class) every living footman is a
one-hit kill and the problem reduces to swing cadence: attack the lowest-HP footman
that will still be alive when the hit lands.

### Waiting behaviour

Between windows a hero with real burst (Ranger, Demon Hunter, Crossbowman, Lich,
Arcanist, Berserker) must not be in engine combat, or it auto-attacks and auto-casts on
the nearest footman. The four weak hitters (Vanguard Knight, Druid Warden, Death Knight,
Warlock) do better standing at the standoff point and letting the engine attack, because
their windows are narrow relative to a footman's 12-damage hits (measured locally by
Codex, variant B). The hero holds a walk target every decision (a walking hero never
auto-acquires): the standoff point is the nearest enemy footman's tile pulled back toward
the own fort so the distance equals the attack range minus half a tile, clamped to stay
more than 7 tiles from any visible living enemy tower. With no enemy footman visible the
hero walks to the frontmost allied footman of its lane.

### Lane and positioning

The hero's lane is the engine lane for its seat (`selfId - 100` within team, mapped by
`[0, 0, 1, 2, 2]`). Allied footmen are always visible; their lane is classified from
position. The lane front is the allied footman of that lane nearest the enemy fort.

### Telemetry

Every 240 ticks, one line:

```
LH <tick> <lastHits> <heroKills> <towerKills> <level> <orders> <secures> <poisons> <lost> <deaths> <gold> <early> <missed>
```

`lastHits` and `heroKills` are derived from gold increments (footman 15, hero 100;
purchases are the only decrements and the script knows its own). The module never
attacks structures, so 75 is five footmen from an area spell, not a tower; hero kills
are taken only until the remainder is a multiple of 15. `orders` counts new
`attackTarget` targets, `secures` explicit casts, `lost` ordered targets that vanished
unpaid, `early` basic hits that landed while the target survived, `missed` footmen that
vanished within chase distance while not ordered. `25 * lastHits + 150 * heroKills`
should equal the seat's `total_xp`; the harness checks it and flags the estimate's
ambiguities (300 gold is three heroes or twenty footmen).

## Evaluation

Local: `uv run coworld run-episode <manifest> <ten .bas paths> --variant competition`
runs a full match in about five seconds with per-seat logs. The harness
`tools/lasthit_eval.py` runs N seeds with the candidate in one team's seats and a
reference file in the other, swaps sides, and reports last hits per seat and class with
the XP cross-check. Hosted evaluation follows once the local number is stable: upload
under James Botts and run an experience request against the live roster.

## What the first day of iteration found

Local mirror matches, team last hits out of 1,080 (seeds 2026 / 2027):

| Change | Team last hits | Mean per hero |
| --- | --- | --- |
| First working build | 854 / 688 | 150 |
| Chase cap: only footmen within reach + 3 tiles may be ordered | 984 / 766 | 174 |
| Skip footmen an allied hero is already attacking | 950 / 990 | 192 |
| Review fixes (event merge, landing tick, instant strike), stickiness, scan radius | 1,027 / 996 | 201 |
| Ally-avoid rule off; idle at the standoff point for the four weak classes | 1,052 / 1,043 (seed 2027) | 207 |

Ordering attacks on distant footmen was the largest loss: the hero walked across the
map after a 36-HP footman nobody was hitting. Anchoring (where to stand) and ordering
(what to hit) are now separate decisions with different distance rules. The planner
must also stay under 20,000 instructions per decision in the middle lane, where sixty
footmen can be visible; footmen beyond 20 tiles are not scanned.

## Punish module (first fight behavior, 2026-09-17)

James's direction: exploit opponent boldness. When an enemy hero farms inside our tower's
reach, target it. The signal is an allied tower's `objectTarget` being that hero: towers
shoot footmen first, so a tower firing at a hero means the hero stands in range with no
wave left, taking 18 to 30 damage per second. Distance alone is a false signal: in local
games the starter's heroes sat at 5.4 tiles from our outer tower (range 5) for minutes,
untouched, and a 7-tile distance trigger sent our hero into an even fight it did not win.
`25_punish.bas` enters on tower-fire within 7 tiles of the tower and within 12 tiles of
us at 50 percent HP or more, holds the target until it is 10 tiles from the tower or our
HP falls under 35 percent, and lets the engine auto-cast the kit. Telemetry: punish
starts and ticks on the `LH` line. Evaluated in the one-copy v5 versus v7 A/B.

## Open questions

- Whether holding a walk target every decision costs measurable last hits through
  movement jitter, versus letting melee heroes auto-acquire.
- Whether spending gold on poison for last hits beats buying damage earlier.
- How much attacker-identity phase tracking gains over per-victim drop events (Codex's
  experiment 2).
- Whether holding a walk target beats letting the engine auto-acquire at the standoff
  point (Codex's experiment 1).
