# Gods of the Arena knowledge map

What the lab knows about the game, where each piece lives, and how to check it is
still true. Start here. Every mechanics document opens with a **Currency** block that
names the polyworld commit it was verified against and the files to diff when the
deployed commit changes. Run the check first:

```sh
.venv/bin/python gods_of_the_arena_lab/tools/deployed_ref.py   # deployed commit vs the docs
```

Every mechanics claim below is verified against the deployed polyworld `7365e4e9`
(coworld 2026.9.16.3, verified 2026-09-16). The deployed build is the only one that matters:
replays only re-simulate at it, and `main` moves ahead of it (three releases shipped on
2026-09-16 alone). Where the maintainer's own guide and the code disagree, the code wins:
`coworld/gota/guide.md` says barracks have 900 HP, `sim.nim:3527` gives them the outer-tower
value, 950.

## What we know, and where

| Topic | What is established | Document | Rendered report |
| --- | --- | --- | --- |
| The policy language | A small structured BASIC: 32-bit ints, `IF`/`WHILE`, `SUB`s without return values, fixed arrays, `PRINT`. No `FOR`, `GOTO`, functions, strings, or randomness. Budgets: 20,000 instructions and 50,000 work units per decision; exhaustion disables the hero for the match. | [policy-capabilities.md](policy-capabilities.md) §1, [wiki/policy-and-host-surface.md](wiki/policy-and-host-surface.md) | [capabilities](../../docs/reports/gota-policy-capabilities-2026-09-15.html) |
| Execution model | One file per seat, one VM per seat, no shared memory. Mono-team or mixed-team rosters are a platform setting. The engine chases targets, auto-acquires footmen, and auto-casts all four ability slots between decisions. | [policy-capabilities.md](policy-capabilities.md) §2 | same |
| Observations | 19 self fields (position, HP, mana, gold, level, move speed, attack range, attack damage, current target, attack cooldown, lifetime hits landed, tick), a visibility-filtered object list frozen for the decision (id, kind 1–5, team, class, x, y, hp, alive; heroes also level, mana, items, facing, target, velocity), a pending-spell list with impact tick, inventory, ability charges/cooldowns, static terrain through fog with team-known building footprints. Tile-grained positions; `selfId` = 100 + seat. Not exposed: XP, path existence, respawn timer. | [policy-capabilities.md](policy-capabilities.md) §3 | same |
| Actions | `walkTo`, `attackTarget`, `buyItem`, `useItem`, `castTarget`, `castPoint`; exact acceptance rules and side effects (`walkTo` always clears the target; structure `alive` means exposed). | [policy-capabilities.md](policy-capabilities.md) §4 | same |
| Economy | Income only from a hero's own killing hit: footman 25/15, hero 150/100, tower or barracks 100/75, fort 0; flat for the whole match. No assists, passive income, denies, or losses except purchases. Death costs 216 ticks. Shop works anywhere; no upgrades or selling. Waves of 3 footmen per living barracks (18 per team) every 480 ticks: about 27,000 creep XP per team per match; killing a barracks removes its 3 creeps per wave from both teams' farm. | [leveling-economy.md](leveling-economy.md) | [economy](../../docs/reports/gota-leveling-economy-2026-09-15.html) |
| Scaling | Only HP, mana, basic damage, and move speed scale (linear per class). Abilities, items, consumables, footmen, towers, rewards are fixed. Duels take the same time at every level; ultimates fall from 33–53% of an enemy at L1 to 7–12% at L20; gate towers kill a L1 hero in 7–12 s but stop being lethal past level 10; three phases keyed to level. **Lab-internal finding; do not post.** | [scaling.md](scaling.md), [tools/scaling/](../tools/scaling/README.md) | [scaling](../../docs/reports/gota-scaling-2026-09-15.html) |
| Hero roles | Four jobs from the numbers (burst killer, duelist, siege front, healer), a per-hero primary/secondary mapping, and a farm priority. Theory, not gameplay evidence. Public version on the forum (`post_f177c436…`) with the phase reasoning withheld. | [roles.md](roles.md), [../forum_agent/brief.md](../forum_agent/brief.md) | |
| Hero and item numbers | Base stats and growth per class, kits, item prices and effects. | [wiki/hero-statistics.md](wiki/hero-statistics.md), [wiki/game-guide.md](wiki/game-guide.md), [scaling.md](scaling.md) Appendix A, `tools/scaling/specs.json` | |
| Rules and structures | Map, teams, seats, object kinds (1 fort, 2 hero, 3 footman, 4 tower, 5 barracks), tower exposure order, barracks exposed after all three lane towers, fort exposure after one lane, respawn, mana regen, scoring (1 per winning seat, 0 on timeout for all). Tower HP 950/1,300/1,950 at 18/24/30 damage; barracks 950. | [wiki/mechanics.md](wiki/mechanics.md), [wiki/overview.md](wiki/overview.md) | |
| Replays | A binary action tape (format 5, game version 40 at the deployed build) plus per-tick hashes; full state only by re-simulation at the recording commit (resolved from the coworld manifest). Kill, XP, gold, level, purchase, and building-kill events are exact (a barracks kill pays and counts as a tower kill); per-attacker damage and heals are not recoverable without an engine change. Expander design (Nim core, Python decoder); the `compare.py`/`features.py` adapters already exist over hosted results and our own telemetry. | [replay-format.md](replay-format.md) | [replay](../../docs/reports/gota-replay-format-2026-09-15.html) |
| Where the leaders get their XP | Replay comparison of v13 against the two leading policies (288 games, exact reward accounting): the leaders earn about 70% more XP per 1,000 ticks, almost all from hero kills and buildings; v13 claims 27% of nearby enemy deaths versus 71–73%. Gameplay work paused; next question is missed nearby finishes. **Lab-internal; do not post.** | [reports/v13-vs-strongest-2026-09-18.md](reports/v13-vs-strongest-2026-09-18.md) | [comparison](reports/v13-vs-strongest-2026-09-18.html) |
| Requested engine changes | 14 requests with reasons. Items 1–13 (observations) merged in `e127989` and deployed 2026-09-16 (coworld 2026.9.16.3, polyworld `7365e4e9`); item 14 (damage/heal/kill events in the recording) still open. | [requested-game-changes.md](requested-game-changes.md) | |
| Standings | Where to read league results and what the numbers mean. | [wiki/player-standings.md](wiki/player-standings.md) | |
| The official starter | Nearest-enemy attack, class-based shopping, walk to (64,64). | [../reference/base.bas](../reference/base.bas), [../README.md](../README.md) | |

## How to validate it is still current

1. **Deployed commit.** `tools/deployed_ref.py` follows the league's game record to its
   current coworld release and reads that manifest's `source_url`. Each release is a separate
   coworld record, so never check a coworld id you wrote down earlier: it is a frozen
   snapshot. If the script reports a change, diff the files each document's Currency block
   names before relying on that document. `origin/main` is not the deployed build.
2. **Balance numbers.** Re-dump `tools/scaling/specs.json` per [tools/scaling/README.md](../tools/scaling/README.md)
   and diff it against the committed copy; any change means the hero, ability, or item tables
   in `scaling.md`, `leveling-economy.md`, and the wiki pages need re-reading.
3. **Simulation constants** (rewards, tower HP and damage, footman stats, respawn, regen,
   spawn interval) are hard-coded at the top of `tools/scaling/model.py` with their `sim.nim`
   names; grep those names in the new commit.
4. **Host surface.** `examples/gods_of_the_arena/bots.nim` lists every registered data name
   and function; compare with `policy-capabilities.md` §3–4 and `wiki/policy-and-host-surface.md`.
   Update the limits tables and `requested-game-changes.md` when a request lands.
5. **Replays.** Re-simulate one fresh episode at the deployed commit and confirm the final
   hash matches the game log (`replay-format.md` §1.4).
6. **Platform facts** (identity, seats, credits, submission) live at the root in
   [docs/platform-reference.md](../../docs/platform-reference.md) and the shared skills, not here.

## Source of truth

| Source | Use |
| --- | --- |
| [Polyworld source](https://github.com/Metta-AI/polyworld) (`examples/gods_of_the_arena/`, `src/polyworld/basic.nim`) | Authoritative implementation; cite the deployed commit, not `main` |
| [League record](https://softmax.com/api/observatory/v2/leagues/league_3c60897b-25cf-4b37-9d1a-8554c1198f28) → `game.coworld_id` → that coworld's manifest | Deployed version and `source_url` (current: [2026.9.16.3](https://softmax.com/api/observatory/v2/coworlds/cow_54d6f449-6d63-464d-b742-ff720a9ce803)) |
| [Participation guide](https://softmax.com/api/observatory/v2/participate?league_id=league_3c60897b-25cf-4b37-9d1a-8554c1198f28) | League runtime and submission requirements |
| [Game wiki](https://softmax.com/gods-of-the-arena/wiki.md) and [forum](https://softmax.com/gods-of-the-arena/forum.md) | Public reference and other entrants' claims; leads, not proof. Our maintained wiki copies are in `docs/wiki/`; public writes are gated. |
| [Polyworld Buff directory](https://metta-ai.github.io/polyworld-buff/) | Game presentations and interactive views |

## Choosing an optimization

1. Resolve the active league's game and match configuration, and select the owned
   policy to improve with the human.
2. Inspect complete games: objective progress, engagements, time-limit finishes,
   and differences between team/class assignments.
3. Join policy intent to accepted actions and actual impact. Validate replay and
   metric extraction against a complete episode before relying on an analysis adapter.
4. Agree one behavioral hypothesis with the human. Measure completed game outcomes
   separately from operational failures. Game-code inspection establishes mechanics;
   competitive improvement requires gameplay evidence.

## Documentation maintenance

Keep these pages and the public wiki as complete current references. Replace
superseded claims directly. Do not add audit reports, change narratives, version
logs, obsolete measurements or pointers to removed material. Source links should
lead readers to the implementation that defines the documented behavior.

The files in `docs/wiki/` contain the maintained wiki content. Before publishing,
read each page from the service, reconcile concurrent edits and verify the saved
body. Use the [community workflow](../../.claude/skills/coworld-community/SKILL.md)
with the session's authorization. The live `game-guide`, `hero-statistics`, and
`player-standings` pages are also written by Andre's Polyworld Buff sync job, which adds a
source header and appended report tables; keep those when republishing our copies.
