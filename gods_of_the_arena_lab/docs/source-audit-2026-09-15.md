# Gods of the Arena source and wiki audit — 2026-09-15

## Authority and scope

Audited latest fetched `Metta-AI/polyworld/main` at
[`7a7b22c85c1411bc37707a21b2a4a94e1b757fd8`](https://github.com/Metta-AI/polyworld/tree/7a7b22c85c1411bc37707a21b2a4a94e1b757fd8).
A second fetch before publication confirmed the same upstream head. Source was
inspected in a separate clone; no engine or policy behavior was changed.

The downloaded **2026.9.15.1** manifest points to
`5422fb0c4b230ca7bfa57a69e450a369da2dabe9`. Its BASIC interpreter, GotA host,
content and starter match the latest source. The intervening changes affect
`sim.nim` and `graphics.nim`: tower-body separation, footman route resumption and
visual presentation. This does not establish the active league's game/config pin.

Sources read: `src/polyworld/basic.nim` and its tests; GotA `bots.nim`, `sim.nim`,
`content.nim`, terrain queries, map generation/configuration, arena construction;
Coworld compilation, logging and settlement; manifest and unchanged starter.
The audit traces host registration to action implementations and tick order rather
than assuming that an internal engine helper is exposed to policies.

## Corrected discrepancies

| Topic | Previous claim | Verified resolution |
| --- | --- | --- |
| Map | 64×64 or 128×128 fixed arena | Default 116×116; generator accepts even 64–256; host reports actual dimensions |
| Factions | Red living, Blue undead | Red classes 5–9; Blue classes 0–4 |
| Policy ownership | One file controls five heroes | Ten file-policy seats, one independent hero VM per seat |
| Spells | Not scriptable | Target/point casts and availability queries are registered; bot auto-casting also runs |
| Human controls | Self abilities always fire | Casts are attempts subject to resources, cooldowns and full-resource rejection |
| Ranger | 210 initial HP, 932 at level 20 | 200 initial HP, 922 at level 20 |
| Meteor Strike | 50 mana | 53 mana |
| Sanguine Chalice | 26 healing | 28 healing |
| Ice Spear | 6-tile spell range | 380,000 / 60,000 = 6.33 tiles, rounded |
| Shopping | Wording implied level-20 spending; use/equip | Purchases available from level 1 without distance gate; held equipment passive; useItem rejects equipment |
| Failures | Invalid BASIC fails whole team, no distinction | Compile failure fails episode; runtime BasicError disables the affected VM |
| Rating | Elo K=32, initial 1500, mean round score asserted as game contract | Source only establishes binary seat scores and separate XP; platform rating requires separate evidence |

Hero and ability numbers were checked against **effective** `abilitySpec` behavior,
including overrides after `BaseAbilitySpecs`. A targeted extraction compared 331
numeric fields across ten heroes, forty abilities and twenty items. After corrections,
those checks had zero mismatches. This covered hero table values, ability damage/
healing/restoration, mana, charges, cooldowns/recharge, listed cast ranges, and item
prices/equipment bonuses. Shape/cast-delay behavior was inspected in source; the
331-field comparison is not a test of every guide sentence, UI effect or gameplay path.
The duplicated Ranger health summary was corrected too.

## Additional contract details now recorded

- Self data is a start-of-decision snapshot. Inventory and ability queries read
  current state; the object enumeration caches on first query for that hero/tick.
  Several purchases can therefore see the same `selfGold`, while later purchases
  are still validated against actual remaining gold.
- `walkTo` clears combat targeting before pathfinding; rejection does not promise
  that nothing changed. `attackTarget` acceptance alone does not establish visibility,
  objective exposure, or a successful hit; combat applies the later checks.
- Replay commands are recorded before action acceptance. Count requests, accepted
  commands, and actual effects separately.
- Terrain is observable through fog and layer-aware; static walkability does not
  prove a reachable path or absence of a tower body.
- No BASIC registration exists for attack-move, manual-spell-mode, selling items,
  object layer, or maximum object HP, despite some corresponding engine facilities.
- Equipment maximum-stat increases also increase current HP/mana by the delta.
  Consumable stacks cap at eight; a full stack rejects more even with empty slots.
- Death animation plus respawn wait is 24 + 192 ticks after entering Dying.
  Respawn retains inventory/level/gold/VM state and restores resources and ability
  readiness. Living hero updates regenerate one mana each six ticks.
- Game-time timeout is a valid zero-score result for both teams; it must not be
  confused with an infrastructure timeout or replaced with an XP-based victory.

These are version-scoped facts. They are not measured strategy improvements.

## Documentation and publication

Updated the [lab reference](../README.md), [research record](research.md), and four
wiki pages. Exact dated publication bodies are retained here:

- [Overview](wiki/overview.md)
- [Mechanics](wiki/mechanics.md)
- [Policy and host surface](wiki/policy-and-host-surface.md)
- [Illustrated game guide](wiki/game-guide.md)

These are publication snapshots, not an automatically synchronized second wiki.
Future edits must read the server's current revision and reconcile intervening edits.
The illustrated guide preserves its artwork and kit/item sections, with narrow
corrections. The other three pages replace obsolete current-reference prose; prior
revisions remain in Observatory history.

The hero-statistics and player-standings pages were read and left intact: both
explicitly identify historical cohorts and limitations. Their outcomes were not
recomputed from source or relabeled as current. Buff itself and the historical
strategy book are external upstream resources, not edited in this task.

Publication uses the normal user identity through the
[community skill](../../.claude/skills/coworld-community/SKILL.md), with explicit
user authorization, dry runs, original base revisions and fixed idempotency keys.
The publication record below records server readback, not merely request success.

### Verified publication revisions

| Page | Before | Published and read back |
| --- | --- | --- |
| [overview](https://softmax.com/gods-of-the-arena/wiki/overview) | `wrv_77783460-9e16-43d4-9ab4-9b87abc8519e` | `wrv_215f6111-8d38-4dc8-a7db-24fc5df91e17` |
| [mechanics](https://softmax.com/gods-of-the-arena/wiki/mechanics) | `wrv_39da9c4d-d329-4df7-8b78-391944c311b4` | `wrv_95e3ce94-3087-4e76-9bc0-0483418ad5ca` |
| [policy-and-host-surface](https://softmax.com/gods-of-the-arena/wiki/policy-and-host-surface) | `wrv_4e2fe668-5523-452b-84cb-d50eb69c733f` | `wrv_28f66282-a81e-4f3c-94f3-f61195de38ea` |
| [game-guide](https://softmax.com/gods-of-the-arena/wiki/game-guide) | `wrv_baf34c1e-ce44-4bc6-bcf6-58f92284516a` | `wrv_da96d099-ae1b-48b0-bf9f-1ce2355b2701` |

All four saved bodies and titles matched the local publication drafts exactly.
Original base revisions were used, and no concurrent-edit conflict occurred.
No forum posts, policy uploads, evaluations or league submissions were made.

Body SHA-256 values (UTF-8, including final newline):

- `overview`: `223ac4a1cc070f6cbbf3ab82a4ee6b7c2b39ac7b5106f1e098f93894180d75f2`
- `mechanics`: `d7896c9b2c0ad8568acf164da1262dab6381f2b4439a1ff849c25064298901cb`
- `policy-and-host-surface`: `1859ec11d7175ea297ad5e57ec5635243355b0e76dec060adbf57413408f8ee1`
- `game-guide`: `93f3f033d604ae1a8e1e27cb2bb67bc9a1e63b970f68a6f341411ff2869f92bc`
