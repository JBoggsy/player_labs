# What a Gods of the Arena policy can know and do

> **Currency.** Verified at polyworld `7365e4e9` (coworld 2026.9.16.3, 2026-09-16), the
> build the league runs. **Re-verify when** `tools/deployed_ref.py` reports a new
> polyworld commit: diff `examples/gods_of_the_arena/bots.nim` (host surface),
> `observations.nim` (spell visibility), `src/polyworld/basic.nim` (dialect), and the
> `sim.nim` acceptance procedures named below. Rendered report with citations (predates
> `7365e4e9`; its line numbers and §3.6 layout are stale):
> [`docs/reports/gota-policy-capabilities-2026-09-15.html`](../../docs/reports/gota-policy-capabilities-2026-09-15.html).

A complete inventory of the BASIC dialect, every observation a hero script can read,
and every action it can take, with the parameters and semantics of each. Verified
against polyworld `7365e4e9` (2026-09-16). Source files cited are
under `examples/gods_of_the_arena/` unless noted.

Companion pages: [policy and host surface](wiki/policy-and-host-surface.md) (limits,
budgets), [mechanics](wiki/mechanics.md) (rules), [hero statistics](wiki/hero-statistics.md).

## 1. The language, exactly

The compiler is `src/polyworld/basic.nim`. The reserved-word list at lines 551–556 is the
entire grammar surface: `and call dim else end exit false gosub goto if let mod not
or print rem return stop sub then true wend while xor`. `goto` and `gosub` are
reserved but **not implemented** as statements (the dispatcher at lines 1720–1765
has no branch for them). There is no `FOR/NEXT`, `SELECT CASE`, `DO/LOOP`,
`ELSEIF`, single-line `IF`, `FUNCTION`, or any built-in function such as `ABS`,
`MIN`, `MAX`, `SQR`, or `RND`.

| Feature | Behavior | Evidence |
| --- | --- | --- |
| Values | Signed 32-bit integers only, wrapping on overflow. `true`/`false` are constants 1/0. | `basic.nim:1047–1070`, `wrapNegate` at 946 |
| Operators | `+ - * / MOD`, unary minus, `= <> < <= > >=`, `AND OR XOR NOT`. Integer division; division by zero is a runtime error. Both sides of `AND`/`OR` always evaluate. | `parseUnary` 1118, `parseExpression` 1162 |
| Variables | Global scalars, auto-created on first use, start at 0, case-insensitive. Scratch variables written inside a `SUB` are still global. | README table |
| Arrays | `DIM name(N)` at top level only, literal bound, inclusive (`DIM a(9)` is 10 ints). At most 32 arrays and 4,096 total elements. Out-of-range index is a runtime error. | `parseDim` 1174, `bots.nim:82–83` |
| Control flow | Multi-line `IF cond THEN … [ELSE …] END IF` and `WHILE cond … WEND`. `THEN` must end the line. | `parseIf` 1635, `parseWhile` 1669 |
| Subroutines | `SUB name(p1, p2) … END SUB`, invoked as `name(args)` or `CALL name(args)`. Parameters are call-local; up to 16. `RETURN` and `EXIT SUB` leave early. No return values; a sub used in an expression is a compile error. Call depth 16. | `basic.nim:1102–1104`, `bots.nim:88,91` |
| Termination | Falling off the end, `END`, or `STOP` ends **this tick's decision**. The next tick restarts from line one with globals intact. | `bots.nim:564` (`restart`) |
| Logging | `PRINT "text"; expr, expr` (semicolon joins, comma inserts a space, trailing semicolon suppresses newline). 1,024 bytes and 128 print events per decision; output goes to the private player log only. | `parsePrint` 1604 |
| Comments | `'` or `REM` to end of line. | |
| Strings | String literals exist only inside `PRINT`. No string variables or functions. | |

Per-decision budget: 20,000 executed VM instructions and 50,000 work units, then
a runtime error that **permanently disables that hero for the episode**. A
`walkTo` call alone costs 800 work units, so the budget is roughly 60 walks or
12,000 object-field reads per tick, whichever you spend first.

## 2. Execution model

One BASIC file controls one hero. The engine maps one source file to each of the
ten seats (0–4 Red, 5–9 Blue) and gives every seat its own VM with **no shared
memory**. Which files fill a team is a platform setting: in mono-team play all five
seats of your team run your file; in mixed-team play your file shares a team with
other players' files. Either way, the only cross-hero information is what each hero
can observe about the others.

Every simulation tick (24 per simulated second, 28,800 per default 20-minute
match) each living hero's script runs once, in a rotating seat order
(`bots.nim:615–622`). Dead heroes skip their decision. The object list is built
first (`bots.nim:566`; `ensureScriptObjects`, `sim.nim:1473`), then self data is
snapshotted (`bots.nim:567–598`), and both stay frozen for the rest of that
decision, so an action call never changes what you read afterwards. Inventory,
ability, and spell queries read the live world instead.

The engine keeps acting between your decisions. An accepted `attackTarget` makes
the hero chase and auto-attack until the target dies or leaves vision. An idle
hero with no move target also auto-acquires nearby enemy **footmen** on its own (never heroes or structures)
(`acquireRadius`, `sim.nim:2845`): melee heroes within 2.5 tiles, ranged heroes within
their attack range. While in combat, the engine also **auto-casts abilities**
for you: passive first, then the first of ultimate → secondary → primary that is
ready (`tryCombatAbilities`, `sim.nim:2749`). Explicit `castTarget`/`castPoint`
calls run alongside that; there is no way to switch auto-casting off from BASIC.

## 3. Observations

All coordinates are **map tiles** in `0 … mapWidth-1`, origin top-left of the
116×116 default map. World units internally are 60,000 per tile; the host
converts positions for you (`mapCoordinate`, `sim.nim:1375`). Facing, speed, range,
and velocity are reported in world units instead, so divide by `worldScale` for
tiles. The "Y" of every observation is the second horizontal axis (internally
`z`), not height.

### 3.1 Self data (read-only globals, snapshotted at decision start)

| Name | Type / range | What it indicates |
| --- | --- | --- |
| `selfId` | int, nonzero | Your stable object ID. Matches what other heroes see via `objectId`. |
| `selfTeam` | 0 Red, 1 Blue | Your team. Compare with `objectTeam` to classify allies and enemies. |
| `selfClass` | 0–9 | Your hero class (0 Vanguard Knight, 1 Ranger, 2 Arcanist, 3 Druid Warden, 4 Demon Hunter, 5 Death Knight, 6 Crossbowman, 7 Lich, 8 Warlock, 9 Berserker). Blue fields 0–4, Red fields 5–9. Determines attack style, ranges and the four abilities. |
| `selfX`, `selfY` | tile | Your tile position. |
| `selfHp`, `selfMaxHp` | int, ≥0 | Current and maximum HP. Max grows with level and equipment. |
| `selfMana`, `selfMaxMana` | int | Current and maximum mana. Regenerates 1 every 6 ticks (4/s). |
| `selfGold` | int | Gold on hand. Start 150. Not refreshed after `buyItem` within the same decision. |
| `selfLevel` | 1–20 | Your level. XP itself is **not** exposed. |
| `worldTick` | int | Simulation tick since match start. Divide by `tickRate` for seconds; default time limit 28,800. |
| `selfLayer` | 0–3 | Your navigation layer (0 ground, 1 Red fort, 2 Blue fort, 3 water). Used implicitly by the non-`At` terrain queries. |
| `selfMoveSpeed` | world units/tick | Unblocked movement per tick, including level and boots (`heroMoveSpeed`, `sim.nim:757`). |
| `selfAttackRange` | world units | Basic-attack range by class (`heroAttackRange`, `content.nim:771`; no item modifies it). Planar distance between centers; towers and barracks allow at least 105,000 measured from their footprint and forts 255,000 regardless (`TowerSiegeRange`, `sim.nim:267`; `FortRange`, `sim.nim:378`). |
| `selfAttackDamage` | int | Current basic-attack damage including level and equipment (`heroAttackDamage`, `sim.nim:736`): the exact last-hit threshold. |
| `selfTarget` | object ID or 0 | The ordered or auto-acquired attack target. Tells you whether the engine silently dropped your last `attackTarget`. |
| `selfAttackCooldown` | ticks | Ticks until the next basic hit could land if the target stays in range: remaining recovery plus the next windup (45% of the class swing), or the remainder of a windup in progress; an idle hero reports a full windup; 0 while dead (`heroAttackCooldown`, `sim.nim:744`). Separate from ability cooldowns. |
| `selfAttacksLanded` | int | Lifetime count of basic hits that landed, kept across respawns; spells do not count. |
| `mapWidth`, `mapHeight`, `mapLayers` | int | Map dimensions in tiles and layer count. Read these rather than hard-coding 116. |
| `worldScale`, `tickRate` | constants | 60,000 world units per tile and 24 ticks per second (`bots.nim:200–201`). |
| `GroundLayer` … `WaterLayer`, `TerrainNone` … `TerrainWater` | constants | Named constants for layers 0–3 and terrain kinds 0–7. |

Not exposed about yourself: XP, whether a path exists to a destination, and the
death/respawn timer. Class-derived facts that are not listed above must be
table-driven in your script from [hero statistics](wiki/hero-statistics.md).

### 3.2 Visible objects (host functions; 4 work units each unless marked, `objectCount` costs 2)

`objectCount()` returns the number of objects in this hero's **visibility-filtered**
list; `index` runs `0 … objectCount()-1`. The list is ordered forts, towers,
barracks, heroes, footmen (`rawWorldObjectAt`, `sim.nim:1387`) and contains **all
allied objects plus every enemy object standing on a tile your team can currently
see** (`objectVisibleTo`, `sim.nim:1469`). Destroyed towers and barracks leave the
list entirely (`sim.nim:1486`). Indexes are valid for this decision only. Invalid
index returns 0 (or -1 for class, 0 for alive).

| Function | Returns | What it indicates |
| --- | --- | --- |
| `objectId(i)` | int | Stable ID; the handle for `attackTarget` and `castTarget`. |
| `objectKind(i)` | 1 fort, 2 hero, 3 footman, 4 tower, 5 barracks | Object type. Two forts, 18 towers (9 per side, 3 lanes × outer/inner/gate), 12 barracks (2 per lane per side, inside the gates), 10 heroes, and a variable number of footmen. Each living barracks spawns 3 footmen per wave; destroying one stops its footmen. |
| `objectTeam(i)` | 0 Red, 1 Blue | Owner. `<> selfTeam` means enemy. |
| `objectClass(i)` | 0–9 for heroes, -1 otherwise | Enemy hero class, hence its kit and ranges. |
| `objectX(i)`, `objectY(i)` | tile | Position (fort: its center). |
| `objectHp(i)` | int ≥ 0 | Current HP. **Maximum HP is not exposed**; infer from kind (footman 60; towers 950/1,300/1,950 for outer/inner/gate; barracks 950, `sim.nim:259,3527`; fort 400) or hero class + `objectLevel`. |
| `objectAlive(i)` | 0/1 | Heroes/footmen: HP > 0 and not in the death animation. **Towers: HP > 0 and exposed** (outer must fall before inner, inner before gate). **Barracks: HP > 0 and all three of its lane's towers down** (`buildingExposed`, `sim.nim:655`). **Fort: HP > 0 and at least one lane's three towers down** (`fortExposed`, `sim.nim:686`; barracks need not fall). So a live but shielded structure reads 0. Dead heroes remain in the list with alive = 0 until they respawn. |
| `objectLevel(i)` — 16 | 1–20, 0 for non-heroes | Hero level. |
| `objectMana(i)` — 16 | int, 0 for non-heroes | Hero's current mana. |
| `objectItemId(i, slot)`, `objectItemCount(i, slot)` — 16 | item ID / count, 0 for non-heroes or invalid slot | That hero's inventory, slots 0–5, same item IDs as §3.3. |
| `objectFacingX(i)`, `objectFacingY(i)` — 16 | world units | Unit facing, normalized and scaled by `worldScale`: facing +X reads `(60000, 0)`. Works for heroes, footmen, towers, and barracks. |
| `objectTarget(i)` — 16 | object ID or 0 | The object's current attack target, or 0 if it has none, is dead, or the target is not visible to your team. Heroes report their attack target, towers theirs, footmen their footman/hero/building target or the enemy fort when battering it. |
| `objectVelX(i)`, `objectVelY(i)` — 16 | world units | Actual displacement over the last tick, collision included; 0 when stationary (structures always 0). Advancing versus retreating without differencing positions yourself. |

What is **not** in the object list: your own hero *is* included (filter by
`objectId(i) = selfId`); enemy positions outside your team's vision are absent
entirely, not stale; there is no "last seen" memory unless you build it in arrays;
no maximum HP, gold, ability cooldowns, or tower tier / lane label (derive tier and
lane from position).

Vision (`rebuildVision`, `sim.nim:542–607`) is shared per team and terrain-occluded:
each living hero sees radius 10 tiles, each footman 5, each tower its attack range
in whole tiles plus 2 (7/7/8 for outer/inner/gate), each fort 14. Barracks give no
vision. Static terrain never needs vision.

### 3.3 Inventory (4 work units each)

| Function | Returns | What it indicates |
| --- | --- | --- |
| `itemId(slot)` | item ID 0–20 for slot 0–5, 0 if empty/invalid | Which item occupies the slot. IDs: 1 ration, 2 elixir, 3 mana potion, 4 poison, 5 helmet, 6 buckler, 7 gauntlets, 8 boots, 9 amulet, 10 ring, 11 dagger, 12 wand, 13 longsword, 14 bow, 15 pauldrons, 16 armor, 17 staff, 18 axe, 19 crossbow, 20 spellbook. |
| `itemCount(slot)` | 0–8 | Stack count (consumables stack to 8; equipment is always 1). |

### 3.4 Abilities (4 work units each; `slot` 0 passive/Q, 1 primary/W, 2 secondary/E, 3 ultimate/R)

| Function | Returns | What it indicates |
| --- | --- | --- |
| `abilityCharges(slot)` | int ≥ 0 | Charges remaining. Primary strikes for nine classes have 3 charges (`abilitySpec`, `content.nim:625–627`); everything else 1. |
| `abilityCooldown(slot)` | ticks | Ticks until the slot can cast again; 0 means ready (subject to charges and mana). |
| `abilityRecharge(slot)` | ticks | Ticks until the next charge is restored; 0 when full. |

Which ability sits in each slot is fixed by class (`content.nim:138–319`); mana
cost, range, damage and cast delay per ability are in the [game guide](wiki/game-guide.md).
Ranges are in tiles there; internally 60,000 units = 1 tile.

### 3.5 Static terrain (32 work units each; works through fog)

| Function | Arguments | Returns |
| --- | --- | --- |
| `terrainKind(x, y)` / `terrainKindAt(x, y, layer)` | tile, optional layer | 0 none, 1 grass, 2 road, 3 rock, 4 trees, 5 marsh, 6 wall, 7 water. |
| `terrainWalkable(x, y)` / `…At` | | 1 if the tile is walkable on that layer **and** not covered by a building your team believes is standing. Describes terrain plus known building footprints, not occupancy by units or reachability. |
| `terrainHeight(x, y)` / `…At` | | Height in 1/8-tile units. |
| `terrainWaterDepth(x, y)` / `…At` | | Water depth in 1/8-tile units. |

Building footprints: a destroyed tower or barracks frees its tiles, but
`terrainWalkable` reflects an enemy building's destruction only once your team
has seen the site (`knownWalkable`, `sim.nim:1015`; `updateKnownBuildings`,
`sim.nim:1008`; `terrainProc`, `bots.nim:115–126`). Until then the tiles still read
0. Own-team buildings are always current.

Invalid tiles return 0. The map is fixed (seed 54), so a full 116×116 sweep
costs 430,000 work units and cannot fit in one decision; cache what you need in
arrays over several ticks or hard-code lane geometry after inspecting a replay.

### 3.6 Pending spells (`spellCount()` and one-argument queries, 16 work units each)

`spellCount()` returns the number of unresolved casts your team can observe, from
cast start through impact, including projectiles and area warnings, in simulation
order; `index` runs `0 … spellCount()-1`. Allied casts are always listed; an enemy
cast is listed only while its aim tile is visible to your team, the same rule the
viewer uses for warning markers (`spellVisible`, `observations.nim:3–9`). Resolved
casts drop out. The list is read live, not snapshotted, so your own successful cast
appears in it during the same decision.

| Function | Returns | What it indicates |
| --- | --- | --- |
| `spellAbility(i)` | ability enum ID (0-based, `content.nim:35–45`); -1 for an invalid index | Which spell: read damage, radius, and cast delay from the [game guide](wiki/game-guide.md). |
| `spellCasterId(i)` | object ID or 0 | The caster; 0 when the caster is an enemy standing on a tile your team cannot see (`visibleSpellCasterId`, `observations.nim:46–64`). |
| `spellX(i)`, `spellY(i)` | tile | Aim/impact tile or area center. Not the projectile's current flight position. |
| `spellImpactTick(i)` | tick | Absolute tick of impact; `spellImpactTick(i) - worldTick` is the time left to step out. |

## 4. Actions

Every action returns 1 (accepted) or 0 (rejected). Acceptance is checked against
the hero's own state and the target's identity; **it does not guarantee a hit,
arrival, or that the target is currently reachable or visible**. Every call is also
written to the replay before acceptance is evaluated.

| Call | Arguments | Work | Accepted when | Effect and caveats |
| --- | --- | --- | --- | --- |
| `walkTo(x, y)` | tile (clamped to map) | 800 | Hero alive and a path exists (own tile and nearest walkable destination tile resolve; path non-empty, `setHeroDestination`, `sim.nim:1687`). | Engine pathfinds and walks. **Always clears the attack target, attack-move state, and every chase target first**, even if the path fails (`applyWalkTo`, `sim.nim:1786`). While walking with a move target the hero does not auto-acquire enemies. No layer argument; layer transitions are automatic. |
| `attackTarget(id)` | object ID, or 0 | 20 | Target is an enemy footman/hero with HP > 0 and not dying, or an enemy tower/barracks/fort with HP > 0 (`isEnemyTarget`, `sim.nim:1824`). `id = 0` clears the target and is accepted. | Hero approaches and repeats basic attacks; engine auto-casts abilities in combat (`applyAttackTarget`, `sim.nim:1849`). Vision and structure exposure are re-checked every tick afterwards; if the target is unseen or shielded, the engine silently drops it (`selfTarget` reads 0) and the hero idles. Switching targets cancels any walk destination. |
| `buyItem(itemId)` | 1–20 | 20 | Alive, `gold >= cost`, and either an empty slot or a non-full stack of the same consumable (`purchaseReason`, `sim.nim:1867`). Duplicate equipment and a full stack are rejected even with a free slot. | Deducts gold, adds item (`applyBuyItem`, `sim.nim:1893`). Equipment applies stat bonuses immediately (max HP/mana deltas also raise current). **No shop-distance requirement**: buying works anywhere on the map. `selfGold` stays stale until next tick. |
| `useItem(slot)` | 0–5 | 20 | Alive, slot holds a consumable, and: heal when HP < max; mana potion when mana < max; poison only when the current `attackTarget` is within basic-attack range and hittable (visible, exposed; `canHitTarget`, `sim.nim:2280`). | Ration +40 HP, elixir +90 HP, mana potion +60, poison 35 damage to the current target (`applyUseItem`, `sim.nim:2316`). Equipment in the slot is rejected. |
| `castTarget(slot, id)` | ability slot 0–3, object ID | 80 | Alive, cooldown 0, charges > 0, mana ≥ cost, fewer than 512 casts retained (`castAbility`, `sim.nim:2582`). Self-cast heals/restores need HP/mana below max (`id` ignored). Otherwise the target must be alive, visible, in range, and the right team (Strike on enemies, Heal on allies). | Consumes mana, one charge, and starts cooldown at acceptance (`applyCastTarget`, `sim.nim:2664`). Impact resolves later after the cast delay/projectile travel, and only hits what is eligible then. |
| `castPoint(slot, x, y)` | ability slot, tile | 80 | As above, plus `x,y` inside the map and the aim tile visible. A point beyond range is pulled back to max range rather than rejected. | Ground-aimed version (`applyCastPoint`, `sim.nim:2672`). Area spells land at the point (or from the caster for arc/cone/line spells); projectiles fly the aimed direction and hit the first enemy on their path. Melee strikes at empty ground swing into space. |

Not available: attack-move (engine has `applyAttackMove`, `sim.nim:1805`, but it is
not registered to BASIC), selling items, toggling automatic spells, chat or shared
memory between your five heroes, random numbers, and anything about the clock other
than `worldTick`.

## 5. Practical consequences for policy design

- **Memory is the differentiator.** Everything the engine gives you is a snapshot;
  arrays indexed by object ID or class are the only way to remember last-seen enemy
  positions, threat over time, or your own plan state across ticks. `objectVelX/Y`
  and `objectTarget` give you one tick of intent for free, but trends still need
  arrays.
- **Budget one `walkTo` per tick and read the object list once.** Reading the eight
  4-unit fields for ~40 visible objects costs ~1,300 work units; every 16-unit field
  you add costs another ~640 per pass, and a full pass over all 17 fields is ~7,000.
  A naive full-map terrain scan or nested loop over objects × objects can blow the
  20,000 instruction cap and kill the hero for the rest of the match.
- **`attackTarget` is sticky and `walkTo` cancels it.** A retreat is one `walkTo`;
  re-engaging requires calling `attackTarget` again. Don't alternate both every tick.
  Read `selfTarget` to learn whether the engine still holds your order.
- **Structure `objectAlive` is a targeting hint, not a death flag.** Track tower and
  barracks HP directly to know lane state; use `alive` only to decide what is
  attackable now. A destroyed structure disappears from the list, so "absent" plus
  "was in my array last tick" is the death signal.
- **Auto-cast will spend your ultimate on a footman.** If you want to hold the
  ultimate for a hero fight, the only lever is to stay out of engine combat
  (no attack target, no idle auto-acquire) until the moment you want it, then cast
  explicitly before issuing `attackTarget`.
- **Buying is free of positioning**, so gold should never sit idle; the starter
  already buys mid-fight.
- **Team coordination is inferred, not communicated.** Each hero can see its four
  allies' positions, HP, targets, and headings through the object list; formation
  logic has to be written as "where are my allies" rules, not messages.
- **Dodge with the spell list.** `spellImpactTick(i) - worldTick` and `spellX/Y`
  tell you where an area spell lands and how many ticks you have; one `walkTo`
  out of the radius is cheaper than tanking it.
