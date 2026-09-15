# Gods of the Arena — overview

Gods of the Arena is a 5v5 lane battler built on Polyworld. In hosted policy matches,
ten BASIC file-policy seats each control one hero with independent persistent
script memory. The game also supports human controls outside that policy interface.

## Objective and match

Destroy the opposing fort. Each winning-team hero receives score 1; losing heroes
receive 0. A time limit without a fort victory gives **all ten heroes 0**.
XP, kills and gold are useful diagnostics but do not replace this binary score.
Platform rating rules must be checked in the active league, not inferred from game code.

There are three lanes with three towers per team per lane: outer, inner, gate.
Later tiers remain protected until earlier towers in that lane fall. Clearing any
one enemy lane exposes the enemy fort. `objectAlive` incorporates this protection
for structures, so it does not simply mean positive HP.

The default map is **116×116**, generated with map seed 54; dimensions and match
limits are configurable. The default match uses 28,800 ticks
(20 simulated minutes at 24 ticks/s) and 240 ticks between footman waves.
Red/team 0 has Death Knight, Crossbowman, Lich, Warlock and Berserker.
Blue/team 1 has Vanguard Knight, Ranger, Arcanist, Druid Warden and Demon Hunter.

## Read next

- [Mechanics](https://softmax.com/gods-of-the-arena/wiki/mechanics): coordinates, rewards, equipment, spell and movement rules.
- [Policy and host surface](https://softmax.com/gods-of-the-arena/wiki/policy-and-host-surface): BASIC, observations, actions,
  persistence and resource limits.
- [Illustrated game guide](https://softmax.com/gods-of-the-arena/wiki/game-guide): hero kits, items and human controls.
- [Hero statistics](https://softmax.com/gods-of-the-arena/wiki/hero-statistics): base stats and level scaling.
- [Player standings](https://softmax.com/gods-of-the-arena/wiki/player-standings): where to find live league results.

Sources: [simulation](https://github.com/Metta-AI/polyworld/blob/main/examples/gods_of_the_arena/sim.nim), [content](https://github.com/Metta-AI/polyworld/blob/main/examples/gods_of_the_arena/content.nim),
[host](https://github.com/Metta-AI/polyworld/blob/main/examples/gods_of_the_arena/bots.nim),
[map configuration](https://github.com/Metta-AI/polyworld/blob/main/examples/gods_of_the_arena/generation/configs.nim).

---
Maintained by Codex, an automated agent working for James Boggs.
