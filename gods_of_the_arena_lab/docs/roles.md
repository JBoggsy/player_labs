# Hero roles in Gods of the Arena

> **Currency.** Derived from [scaling.md](scaling.md) and [leveling-economy.md](leveling-economy.md)
> (polyworld `1d7eb723`, holding at the deployed `5422fb0c`). **Re-verify when** those documents
> change. The role model is theory from the engine's numbers, not gameplay evidence; each row is
> a hypothesis until an A/B on the live roster confirms it. The public version of this table is
> the forum thread named at the end; the phase reasoning below depends on the lab-internal spell
> scaling finding and stays here.

## Why the MOBA role set does not transfer

The DOTA/LoL roles (late carry, early carry, tank/initiator, hard and soft support) assume a
draft, crowd control, buffs, and superlinear scaling. Gods of the Arena has none of them:

- **No draft, fixed rosters.** Red always fields Death Knight, Crossbowman, Lich, Warlock,
  Berserker; Blue always fields Vanguard Knight, Ranger, Arcanist, Druid Warden, Demon Hunter.
  A role is not a pick decision. It is the per-class branch written in one BASIC file, and in
  mixed-team play it is what we hope a teammate's file also does with that class.
- **No crowd control, buffs, debuffs, or auras.** Every ability is flat damage (single or area)
  or a heal (self, or ally-area for Druid Warden and Vanguard Knight). "Initiator" in the
  blink-stun sense does not exist. "Support" reduces to "has an ally heal".
- **Nothing scales superlinearly.** Only HP, mana, basic damage, and move speed grow with level,
  linearly; abilities, items, attack speed, and range are fixed. There are no item recipes. The
  basic DPS ordering is the same at level 1 and level 20, and the basic-attack time-to-kill
  matrix is nearly level-invariant ([scaling.md](scaling.md) §4).
- **The early/late axis belongs to the clock, not the hero.** What changes over a match is that
  spells fade relative to HP: an ultimate is 33–53% of an enemy at level 1 and 15–19% at level
  10. "Early carry" therefore means "large kit burst", "late carry" means "large HP × basic DPS
  product"; those are different stats on the same fixed roster.

## What structure the numbers impose

Three hero properties drive different jobs:

1. **Kit burst and the mana to pay for it.** Levels 1 to about 5, where a full rotation kills an
   enemy from full and a hero kill is worth a level or more.
2. **HP × basic DPS.** Level 10 and up, where fights are basic-attack races and the only edges
   are HP, numbers, or a tower.
3. **Raw HP and self-centered effects.** The siege, which is the win condition: a timeout scores
   zero for all ten seats, and gate towers kill any hero in 6–14 seconds, so someone must stand
   in tower range after the wave dies.

Ally healing is a fourth, minor axis available to two heroes.

## The four roles

| Role | Job | Rule of thumb for the script |
| --- | --- | --- |
| Burst killer | Convert the ultimate into hero kills while it is still a third to half of an enemy | Avoid engine combat until an enemy hero is in ultimate range, then open with the full rotation |
| Duelist | Win basic-attack races; take the lane's last hits | Buy damage first; engage when own HP × DPS exceeds the target's; farm the lane it is assigned |
| Siege front | Lead the push and absorb tower fire after the wave dies | Buy HP; attack the tower only with a footman in front, and be the closest hero to it |
| Healer | Keep allies alive with the only ally heals in the game | Stand inside the group; cast heals on the lowest visible ally; low farm priority |

## Hero mapping

Every hero has a burst-phase job and an attrition-phase job. Level-1 rotation is the
ten-second kit burst with every charge and mana ignored; rotation mana is the cost of one cast
of every strike. HP and DPS are level 1 → level 20 (Appendix A of [scaling.md](scaling.md)).

| Hero | Team | Burst phase | Attrition phase | HP | Basic DPS | L1 rotation (mana) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Berserker | Red | Burst killer | Duelist / siege front | 300 → 1,345 | 42 → 202 | 275 (36) | Molten Fist is free; the whole kit fits a 40-mana pool. Strongest hero on paper. |
| Demon Hunter | Blue | Burst killer | Duelist | 220 → 904 | 48 → 248 | 266 (109) | Highest DPS and fastest mover at every level; mid HP. |
| Death Knight | Red | Burst killer | Siege front | 350 → 1,528 | 26 → 123 | 296 (134) | Highest HP; self-centered 110 ring ultimate; one rotation then mana-starved. |
| Vanguard Knight | Blue | Frontline | Siege front | 330 → 1,470 | 25 → 120 | 210 (90) | Second-highest HP; 50 HP ally heal circle; self-centered 90 sector ultimate. |
| Lich | Red | Burst killer (best) | Ranged poke | 185 → 717 | 27 → 141 | 337 (188) | 125 ultimate, largest mana pool, lowest HP in the game. |
| Crossbowman | Red | Burst killer | Ranged last-hitter | 230 → 1,028 | 29 → 130 | 353 (132) | Largest rotation; 6.5-tile range; 80-mana pool buys one rotation. |
| Arcanist | Blue | Burst killer | Ranged poke | 190 → 760 | 30 → 152 | 316 (181) | 120 ultimate; second-lowest HP. |
| Ranger | Blue | Ranged poke | Duelist (ranged) | 200 → 922 | 33 → 185 | 255 (130) | Best growth ratio of any hero (HP × DPS grows 26× against 20–22×); 5.5-tile range. |
| Warlock | Red | Ranged poke | Filler | 240 → 1,114 | 22 → 104 | 271 (156) | No standout stat; no job the numbers single it out for. |
| Druid Warden | Blue | Healer | Healer / body | 250 → 1,162 | 20 → 91 | 85 (75) | 55 + 80 ally heals (about 7 HP/s on regeneration); worst DPS and burst; fourth-best HP. |

Farm priority that follows from the table, highest first: Duelists (Berserker, Demon Hunter,
Ranger), then burst killers who need levels for HP (Lich, Arcanist, Crossbowman), then the
siege fronts (Death Knight, Vanguard Knight), then Warlock, then Druid Warden.

## Open questions

- **Funneling may be inefficient.** XP to reach a level grows quadratically, so level is about
  the square root of XP and team totals of HP and DPS are maximized by an even split. Funneling
  buys one hero that wins duels and survives towers longer, which is what sieging needs. Whether
  concentrating levels in the siege front beats spreading them is an A/B, not a theory answer.
- **Mono-team versus mixed-team** decides whether a team plan exists. In mixed-team play our
  file runs one seat beside other entrants' files; the roles are then a convention we publish
  and hope teammates' scripts also follow (see the forum thread below).
- **Roles are lane and target assignments.** With no communication between seats, the only
  coordination is each seat reading allies' positions and applying the same rule. In the script
  a role concretely means: which lane the class walks to, which enemy classes it engages and
  avoids, what it buys first, and whether it holds its ultimate.

## Public discussion

The public version of this table (without the phase reasoning) is the forum thread "Proposed
hero roles and farm priority, for teammates who read this" in the Gods of the Arena forum. Other
entrants' agents are invited to amend the assignments; agreed changes are recorded back here.
Post id `post_f177c436-fd32-4923-bac9-56595a5142f9`. The standing forum agent
([`../forum_agent/brief.md`](../forum_agent/brief.md)) watches the thread, replies when there is a
reason, and records amendments here.

### Amendments proposed by other entrants

None yet.
