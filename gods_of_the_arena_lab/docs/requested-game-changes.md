# Requested changes to the Gods of the Arena BASIC host

> **Currency.** Host surface verified against polyworld `1d7eb723` (identical at deployed
> `5422fb0c`). **Re-verify when** the deployed commit changes: re-check `bots.nim` registrations
> before sending, since any item the maintainer has already added should be dropped. The status
> line below says whether the list has been sent.

A list of feature requests/changes I'd like you and your agents to make. All but the last of these are just adding more observable information to the agent so that it can make better-informed choices. All of the things I'm requesting are given to players in a real DOTA gaming, which defuses a balance argument (and, to a limited extent, makes an argument for their inclusion here).

## Observations about visible objects

| # | Request | Suggested host function | Reason |
| --- | --- | --- | --- |
| 1 | Level of a visible hero | `objectLevel(i)` | Level sets an enemy's HP, damage, and speed. Without it a policy cannot judge whether a fight is winnable or whether an ally can hold a lane, and the only workaround is a burned-in stat table plus guesswork. |
| 2 | Current mana of a visible hero | `objectMana(i)` | An enemy with no mana cannot cast; an ally with no mana cannot heal. Both change engagement decisions, and neither can be inferred from anything the host shows. |
| 3 | Held items of a visible hero | `objectItemId(i, slot)`, `objectItemCount(i, slot)` | Equipment changes an enemy's real damage and HP by up to a third at low level, and potions in hand change how long a fight lasts. The replay viewer already shows inventories, so this reveals nothing a spectator cannot see. |
| 4 | Facing of a visible object | `objectFacingX(i)`, `objectFacingY(i)` | Arc, cone, and line abilities aim along facing. A policy cannot dodge or predict them, or place its own, without knowing which way units face. |
| 5 | Current attack target of a visible object | `objectTarget(i)` | "Who is that tower or hero attacking" is the single most useful fact for deciding whether to retreat, dive, or peel for an ally. Tower and hero targets are already public in the replay. |
| 6 | Movement vector of a visible object | `objectVelX(i)`, `objectVelY(i)` | Positions are tile-grained and refreshed once per decision, so a policy cannot tell advancing from retreating, or lead a projectile, without differencing across ticks and storing it in its scarce array budget. |
| 7 | Spell projectiles and area warnings in flight | `spellCount()`, `spellAbility(i)`, `spellCasterId(i)`, `spellX(i)`, `spellY(i)`, `spellImpactTick(i)` | The engine draws a warning marker for every area spell so human players can step out of it. BASIC policies cannot see those markers at all, so the one counterplay the game is designed around is impossible for them. |

## Observations about the hero itself

| # | Request | Suggested host data | Reason |
| --- | --- | --- | --- |
| 8 | Own movement speed | `selfMoveSpeed` | Speed depends on class, level, and boots. Without it, range and kiting logic needs a per-class table in every policy, and that table silently breaks whenever the game is rebalanced. |
| 9 | Own basic-attack range | `selfAttackRange` | Deciding whether a target is in range is the core of every attack decision. Today it requires a class table and a guess about the engine's distance rule. |
| 10 | Own basic-attack damage | `selfAttackDamage` | Last hits pay the whole economy, and a last hit is "target HP at or below my damage". The value depends on level and every held item, so a policy reconstructing it will be wrong after each purchase or level-up until it notices. |
| 11 | Own current attack target | `selfTarget` | The engine drops a target silently when it leaves vision or exposure, and re-acquires footmen on its own. A policy that cannot read its own target cannot tell whether its last order is still in effect. |
| 12 | Basic-attack cooldown | `selfAttackCooldown` (ticks until the next swing can land) | Movement cancels a swing in progress. Knowing when the next hit lands lets a policy weave moves between attacks instead of interrupting itself, and lets it time a last hit. |
| 13 | Confirmation that a basic attack landed | `selfAttacksLanded` (lifetime counter) | Action calls only report that a request was accepted. A policy has no way to learn whether it is actually hitting anything, so it cannot detect a stuck chase or measure its own effectiveness. |

## Replay and results recording

| # | Request | Suggested change | Reason |
| --- | --- | --- | --- |
| 14 | Damage, heal, and kill events in the replay or results: tick, source object id, target object id, amount, and cause (basic attack, ability id, item, tower, footman); kill events naming the killer | Append an event stream to the action tape or write a sidecar file at episode end, and fill the existing per-seat damage and healing metrics | The replay records requests and per-tick state hashes only, so per-attacker damage and healing cannot be recovered without patching the simulator at the exact recording commit. Kills on the same tick (an area spell taking several last hits, two heroes killing at once) are ambiguous from state alone. Every analysis of "what worked in that fight" depends on this, and it is data the engine already computes and discards. |

## Notes for the maintainer

- The host limits allow 32 data names and 32 functions, and the current host uses 28 of each. Items 1 to 13 exceed the remaining headroom, so the limits would need to rise or several fields be packed into one call.
- Item 7 should be visibility-filtered like the object list; a projectile or warning inside fog should stay hidden.
- Enemy gold and ability cooldowns are deliberately not requested.
