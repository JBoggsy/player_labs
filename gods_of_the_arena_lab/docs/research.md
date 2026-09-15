# Gods of the Arena knowledge map

What the lab knows about the game, where each piece lives, and how to check it is
still true. Start here. Every mechanics document opens with a **Currency** block that
names the polyworld commit it was verified against and the files to diff when the
deployed commit changes. Run the check first:

```sh
.venv/bin/python gods_of_the_arena_lab/tools/deployed_ref.py   # deployed commit vs the docs
```

Every mechanics claim below was verified against polyworld `1d7eb723` and holds at the
deployed `5422fb0c` (checked 2026-09-15). Unless a document says otherwise, the deployed
build is the only one that matters: replays only re-simulate at it, and `main` moves ahead
of it (it already carries a tower rebalance the league does not run).

## What we know, and where

| Topic | What is established | Document | Rendered report |
| --- | --- | --- | --- |
| The policy language | A small structured BASIC: 32-bit ints, `IF`/`WHILE`, `SUB`s without return values, fixed arrays, `PRINT`. No `FOR`, `GOTO`, functions, strings, or randomness. Budgets: 20,000 instructions and 50,000 work units per decision; exhaustion disables the hero for the match. | [policy-capabilities.md](policy-capabilities.md) §1, [wiki/policy-and-host-surface.md](wiki/policy-and-host-surface.md) | [capabilities](../../docs/reports/gota-policy-capabilities-2026-09-15.html) |
| Execution model | One file per seat, one VM per seat, no shared memory. Mono-team or mixed-team rosters are a platform setting. The engine chases targets, auto-acquires footmen, and auto-casts all four ability slots between decisions. | [policy-capabilities.md](policy-capabilities.md) §2 | same |
| Observations | 13 self fields, a per-tick frozen visibility-filtered object list (id, kind, team, class, x, y, hp, alive), inventory, ability charges/cooldowns, static terrain through fog. Tile-grained positions; `selfId` = 100 + seat. Not exposed: XP, others' max HP/level/mana/items/targets, spell projectiles, own target, attack cooldown. | [policy-capabilities.md](policy-capabilities.md) §3 | same |
| Actions | `walkTo`, `attackTarget`, `buyItem`, `useItem`, `castTarget`, `castPoint`; exact acceptance rules and side effects (`walkTo` always clears the target; structure `alive` means exposed). | [policy-capabilities.md](policy-capabilities.md) §4 | same |
| Economy | Income only from a hero's own killing hit: footman 25/15, hero 150/100, tower 100/75, fort 0; flat for the whole match. No assists, passive income, denies, or losses except purchases. Death costs 216 ticks. Shop works anywhere; no upgrades or selling. Creep supply about 18,000 XP per team per match. | [leveling-economy.md](leveling-economy.md) | [economy](../../docs/reports/gota-leveling-economy-2026-09-15.html) |
| Scaling | Only HP, mana, basic damage, and move speed scale (linear per class). Abilities, items, consumables, footmen, towers, rewards are fixed. Duels take the same time at every level; spells fall from 33–53% of an enemy at L1 to 7–12% at L20; three phases keyed to level. **Lab-internal finding; do not post.** | [scaling.md](scaling.md), [tools/scaling/](../tools/scaling/README.md) | [scaling](../../docs/reports/gota-scaling-2026-09-15.html) |
| Hero and item numbers | Base stats and growth per class, kits, item prices and effects. | [wiki/hero-statistics.md](wiki/hero-statistics.md), [wiki/game-guide.md](wiki/game-guide.md), [scaling.md](scaling.md) Appendix A, `tools/scaling/specs.json` | |
| Rules and structures | Map, teams, seats, object kinds, tower exposure order, fort exposure, respawn, mana regen, scoring (1 per winning seat, 0 on timeout for all). Tower HP 1,200/2,400/4,800 at the deployed build. | [wiki/mechanics.md](wiki/mechanics.md), [wiki/overview.md](wiki/overview.md) | |
| Replays | A binary action tape plus per-tick hashes; full state only by re-simulation at the recording commit (resolved from the coworld manifest). Kill, XP, gold, level, purchase events are exact; per-attacker damage and heals are not recoverable without an engine change. Expander design (Nim core, Python decoder, `compare.py`/`features.py` adapters). | [replay-format.md](replay-format.md) | [replay](../../docs/reports/gota-replay-format-2026-09-15.html) |
| Requested engine changes | 15 observation and recording requests with reasons, for the polyworld maintainer. Not yet sent. | [requested-game-changes.md](requested-game-changes.md) | |
| Standings | Where to read league results and what the numbers mean. | [wiki/player-standings.md](wiki/player-standings.md) | |
| The official starter | Nearest-enemy attack, class-based shopping, walk to (64,64). | [../reference/base.bas](../reference/base.bas), [../README.md](../README.md) | |

## How to validate it is still current

1. **Deployed commit.** `tools/deployed_ref.py` reads the coworld manifest's `source_url`. If
   it reports a change, diff the files each document's Currency block names before relying on
   that document. `origin/main` is not the deployed build.
2. **Balance numbers.** Re-dump `tools/scaling/specs.json` per [tools/scaling/README.md](../tools/scaling/README.md)
   and diff it against the committed copy; any change means the hero, ability, or item tables
   in `scaling.md`, `leveling-economy.md`, and the wiki pages need re-reading.
3. **Simulation constants** (rewards, tower HP and damage, footman stats, respawn, regen,
   spawn interval) are hard-coded at the top of `tools/scaling/model.py` with their `sim.nim`
   names; grep those names in the new commit.
4. **Host surface.** `examples/gods_of_the_arena/bots.nim` lists every registered data name
   and function; compare with `policy-capabilities.md` §3–4 and `wiki/policy-and-host-surface.md`.
5. **Replays.** Re-simulate one fresh episode at the deployed commit and confirm the final
   hash matches the game log (`replay-format.md` §1.4).
6. **Platform facts** (identity, seats, credits, submission) live at the root in
   [docs/platform-reference.md](../../docs/platform-reference.md) and the shared skills, not here.

## Source of truth

| Source | Use |
| --- | --- |
| [Polyworld source](https://github.com/Metta-AI/polyworld) (`examples/gods_of_the_arena/`, `src/polyworld/basic.nim`) | Authoritative implementation; cite the deployed commit, not `main` |
| [Coworld manifest](https://softmax.com/api/observatory/v2/coworlds/cow_252fb6a6-cbc3-4d4f-9fa2-8b5250a9d2a2) | Deployed version and `source_url` |
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
with the session's authorization. The tower-HP correction in `mechanics.md` and
`game-guide.md` is not yet published.
