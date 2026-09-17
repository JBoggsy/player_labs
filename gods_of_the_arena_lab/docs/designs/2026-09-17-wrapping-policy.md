# Wrapping policy: design

Living design for the policy that wraps the last-hit and punish modules. Engine facts are
from polyworld `f2ab9598` (league release 2026.9.16.5).

## Objective

James's direction (2026-09-17): the policy does not push structures. It keeps its farm up,
holds a level and item lead over the enemy heroes, and punishes them when they dive our
towers. Farm and kills are the means; the measurable objective is the gap in level, XP
and items between our hero and the enemy heroes in the same game, with last hits and
deaths as guard rails.

Why no pushing: a siege module was built and measured (one copy per game, 48 games per
arm). It took 0.98 structures per game with farm and deaths unchanged, but hero kills
fell and the team win rate read 44% to 31%; a lone push pulled the hero out of the fights
that decide games. The engine facts it rested on are in [replay-format.md](../replay-format.md)
and [policy-capabilities.md](../policy-capabilities.md) if pushing is revisited with
allied heroes present.

## Priority stack

One decision per tick, first matching layer acts; every layer is a module with a
`xxPlan()` that writes an intent and never calls an action. `90_main.bas` applies the
highest-priority intent.

| Order | Module | Fires when | Action |
| --- | --- | --- | --- |
| 1 | survive (`30_survive.bas`) | enemy hero targeting me within 8 tiles, enemy tower firing at me, or low HP with a heal in hand | walk toward own god, drink |
| 2 | punish (`25_punish.bas`) | an allied tower is firing at an enemy hero within 7 tiles of it and 12 of me, HP above 50 percent | attack that hero; the engine auto-casts the kit |
| 3 | last hit (`20_lasthit.bas`) | enemy footmen in play | window strike, chase-attack (melee and low-damage classes) or idle at the standoff point |
| 4 | lane (`90_main.bas`) | nothing else | walk to the lane front |

Shopping (`40_shop.bas`) runs every tick after the action; it is not a layer.

## Level and item lead

Income is footman last hits (25 XP, 15 gold) and hero kills (150, 100). Levels come
from XP alone; items come from gold, and the shop has no upgrades or selling, so six
inventory slots cap what gold can become. The shop rule:

- Poison (a guaranteed last hit for 40 gold) is stocked only while basic damage is below
  60, the footman's HP; after that the slot is worth more as equipment.
- A heal is bought and drunk when HP is below 55 percent; one slot stays free for it.
- Equipment fills the other slots: Leather Gauntlets early (+4 damage while under level
  4), then Battle Axe and Rune Crossbow (+14 each), Arcane Spellbook (+12), Sunsteel
  Longsword (+10), Knight Armor (+120 HP), Ranger Bow, Ironbark Pauldrons, and the rest.
  Five damage and HP items cost about 860 gold, which a hero farming at the field's
  rate reaches by mid game; gold beyond that has no sink except heals.

Measured with the replay expander per game: our level and XP against the mean and the
best enemy hero, and the tick at which our hero reaches levels 5 and 10.

## Punish

The trigger is an allied tower's `objectTarget` being an enemy hero: towers shoot
footmen first, so a tower firing at a hero means it stands in range with no wave left,
taking 18 to 30 damage per second. Distance alone is a false signal (heroes farm at the
edge of tower range untouched). Exit when the target is 10 tiles from the tower or our
HP is under 35 percent. A chase-cost rule (expected time to kill from the target's HP
over our DPS plus an adjacent teammate's, only if we are not slower unless already in
range, within 15 tiles) exists behind `cfgPunishChase` and is off: it fired for 74 ticks
in 48 games and showed no gain.

## When to switch to aggression: the curves say "from minute one, opportunistically"

Level by minute over 96 one-copy games (v9 and v12 arms; the game count falls as games
end, half are over by minute 6):

| Minute | Games | Our level | Enemy mean | Best enemy | Hero kills per game, all ten seats | Enemy deaths within 12 tiles of us |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 96 | 1.8 | 2.0 | 3.2 | 3.7 | 0.42 |
| 2 | 95 | 3.0 | 3.3 | 5.0 | 6.9 | 0.93 |
| 4 | 73 | 4.6 | 5.0 | 7.2 | 7.9 | 0.85 |
| 6 | 51 | 5.7 | 6.3 | 9.0 | 8.6 | 0.76 |
| 8 | 33 | 7.1 | 7.4 | 10.1 | 8.2 | 1.03 |
| 10 | 20 | 7.8 | 8.3 | 11.5 | 9.8 | 0.60 |
| 12 | 14 | 9.1 | 9.0 | 13.0 | 8.5 | 0.93 |

There is no quiet farming phase to wait out: the field fights from the first minute
(3.7 hero kills per game-minute in minute 1, 7 to 10 afterwards) and the best enemy is
1.4 levels ahead at minute 1 and 3 levels ahead by minute 5. Our level only passes the
enemy mean after minute 11, and only in the games that last that long. So the switch
is not a clock: it is opportunity. Of 2,580 enemy hero deaths, 524 (20%, about 5.5 per
game) happened within 12 tiles of our living hero, and we took the kill on 54 of them
(10%). Taking half of those would add about two hero kills (300 XP) per game, a third
of our XP. That is the target of the kill-steal module: the share of nearby enemy deaths
whose killing blow is ours, without pushing and without dying.

## Kill-steal module (heroes and towers), the next increment

James's rules (2026-09-17): never aggressive alone; join a teammate's fight or push if
it comes to us (they cross the river while we farm near it); return to farming as soon
as the fight ends; hit a tower only while farming near it with teammates hitting it;
the point of joining a fight is to take the kill.

Mechanism, reusing the footman last-hit machinery on hero and structure targets:

- Track HP-drop events per visible enemy hero (ten slots by hero id) and per visible
  enemy structure, and predict HP at the tick my basic hit or a chosen spell would land
  (basic: cooldown or travel plus windup; melee strike: this decision; projectile: at
  least one tick of travel; area spells: their cast delay).
- A hero window opens when an allied hero is engaged on the target (its `objectTarget`
  is the enemy, or the enemy's HP is dropping) within `cfgKsAllyKu` of it, the target is
  within my spell or attack reach, and predicted HP at landing is in (0, damage] for the
  basic hit or one ready spell. Then: cast that spell or order the attack. No window: do
  not engage; farm.
- Hold spells for kills: while any enemy hero is visible within `cfgKsHoldKu` (10
  tiles), the farm layer uses window-only last hits (no engine idle attack), because the
  engine auto-casts every ready ability on whatever the hero is attacking. Elsewhere the
  idle farm stays (it is worth +13 percent farm).
- Structure window: an exposed enemy structure within reach whose HP is dropping
  (allied footmen or heroes hitting it) and whose predicted HP at my landing is in
  (0, damage]: order the attack for that hit only, then return to farm. Never attack a
  structure otherwise.
- Return to farm: the module outputs a target only for an open window; every other
  tick the last-hit layer acts.
- Telemetry: `ksHeroWindows`, `ksHeroCasts`, `ksStructWindows` on the `LH` line; hero
  and structure kills and the nearby-death share from the replay expander.

## Roles (next increment)

The four jobs of [roles.md](../roles.md) become per-class knobs on these modules, one
A/B each: burst killers hold the ultimate for the punish target and raise the engage
range; duelists keep the farm priorities and take even fights only with a level lead;
the healer casts its ally heals in survive. Siege-front behaviour is not used.

## Evaluation

One copy per game, matched same-window arms, 48 games each, scored by the replay
expander (`tools/replay_stats.py`) and `tools/compare.py`. Headline: level and XP lead
over the enemy heroes in the same games; guard rails: last hits per 1,000 ticks, deaths,
hero kills.
