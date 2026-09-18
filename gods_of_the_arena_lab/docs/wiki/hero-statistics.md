# Hero statistics

These are the game's character attributes before equipment bonuses. In each
“base + growth” column, the first number is the level-1 value and the second is
the increase per additional level. Maximum level is 20.

| Class ID | Hero | Team | HP: base + growth | Mana: base + growth | Damage: base + growth | Attack range (tiles) | Attacks/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Vanguard Knight | Blue | 330 + 60 | 110 + 8 | 25 + 5 | 1.17 | 1.00 |
| 1 | Ranger | Blue | 200 + 38 | 110 + 8 | 25 + 6 | 5.50 | 1.33 |
| 2 | Arcanist | Blue | 190 + 30 | 180 + 15 | 38 + 8 | 5.00 | 0.80 |
| 3 | Druid Warden | Blue | 250 + 48 | 170 + 14 | 22 + 4 | 4.00 | 0.92 |
| 4 | Demon Hunter | Blue | 220 + 36 | 90 + 7 | 32 + 7 | 1.25 | 1.50 |
| 5 | Death Knight | Red | 350 + 62 | 90 + 8 | 30 + 6 | 1.27 | 0.86 |
| 6 | Crossbowman | Red | 230 + 42 | 80 + 6 | 46 + 9 | 6.50 | 0.67 |
| 7 | Lich | Red | 185 + 28 | 210 + 17 | 36 + 8 | 5.50 | 0.75 |
| 8 | Warlock | Red | 240 + 46 | 190 + 16 | 26 + 5 | 4.50 | 0.86 |
| 9 | Berserker | Red | 300 + 55 | 40 + 4 | 38 + 8 | 1.33 | 1.20 |

For any level, use `base + (level - 1) * growth`. For example, Ranger has
200 HP at level 1 and `200 + 19 * 38 = 922` HP at level 20 before equipment.
Ranges and attack rates are rounded to two decimals. Range here is the basic
attack range; each ability has its own range and resource costs.

See [the game guide](https://softmax.com/gods-of-the-arena/wiki/game-guide) for movement speeds, complete ability kits
and equipment bonuses. Held equipment modifies maximum HP, maximum mana, basic
attack damage and movement as specified by each item.

Team win rate describes a team outcome. Fixed faction lineups mean that shared
wins do not isolate an individual hero's contribution. Evaluate a policy in its
actual seat/team context and count independent games when analyzing team results.

Source: [hero definitions and scaling functions](https://github.com/Metta-AI/polyworld/blob/main/examples/gods_of_the_arena/content.nim).

---
Maintained by Codex, an automated agent working for James Boggs.
