# Game research — 2026-09-15

This is a source-and-documentation investigation, not a completed gameplay evaluation.
The [language reference](../README.md) distinguishes latest source from the downloaded game and lists BASIC limits.
See the [source and wiki audit](source-audit-2026-09-15.md) for subsequent corrections,
additional execution details and publication evidence.

## Sources inspected

| Resource | What was inspected / how to use it |
| --- | --- |
| [Polyworld Buff directory](https://metta-ai.github.io/polyworld-buff/) | Game index: GotA, Light vs Dark, Call to Adventure |
| [GotA guide](https://metta-ai.github.io/polyworld-buff/GOTA/) | Arena, hero kits, shop, casting and human-control sections; interactive hero/standings links |
| [Polyworld README](https://github.com/Metta-AI/polyworld) | Engine, three games, BASIC policy model, Nim/native/headless/browser setup |
| [Mirrored wiki guide](https://softmax.com/gods-of-the-arena/wiki/game-guide) | Read through its Markdown API page; rules, representative hero/ability details, full item and casting/control sections |
| [Wiki index](https://softmax.com/gods-of-the-arena/wiki.md) | All six listed pages retrieved: guide, hero statistics, player standings, overview, mechanics, policy/host surface |
| [Forum](https://softmax.com/gods-of-the-arena/forum.md) | Both posts returned by the index, full post pages, and the one returned comment |
| [Participation guide](https://softmax.com/api/observatory/v2/participate?league_id=league_3c60897b-25cf-4b37-9d1a-8554c1198f28) | League/division identity, runtime workflow; not independent proof of every generic instruction |
| Downloaded manifest and starter | Version 2026.9.15.1, game-hosted runtime, ten seats, competition config, results schema, starter SHA-256 |
| [Pinned source tree](https://github.com/Metta-AI/polyworld/tree/7a7b22c85c1411bc37707a21b2a4a94e1b757fd8) | BASIC parser/runtime/tests; GotA host, simulation, content, map generation, executable settlement and shared Coworld logging |

The browser search tool could not fetch these sites in this session; ordinary HTTPS
reads and GitHub/git access succeeded. No privileged competitor evidence was used.
The source repository was cloned separately and first read at the manifest's exact
revision, then fetched and audited at latest main. See the source audit for their diff. The local game image was downloaded but no episode was launched.

## Current mechanics established from source

- **Objective:** destroy the enemy fort. Each winning-team hero scores 1; otherwise
  0. Reaching the time limit without a fort victory gives all ten seats zero.
  `total_xp` is separate diagnostic output, not the competition win score.
  See [settlement](https://github.com/Metta-AI/polyworld/blob/7a7b22c85c1411bc37707a21b2a4a94e1b757fd8/examples/gods_of_the_arena/sim.nim).
- **Objective access:** within each of three lanes, earlier tower tiers protect later
  tiers. Clearing every tower in one lane exposes that team's fort. Fort HP is 400.
  The object query's alive flag incorporates structural exposure, not just HP.
  See [exposure rules](https://github.com/Metta-AI/polyworld/blob/7a7b22c85c1411bc37707a21b2a4a94e1b757fd8/examples/gods_of_the_arena/sim.nim).
- **Economy:** start at level 1 with 150 gold; six inventory slots; consumables stack
  to eight; duplicate equipment is rejected. Purchases require being alive, sufficient
  gold and storage, without a shop-distance condition in `purchaseReason`. Held
  equipment applies passive bonuses. XP needed for the next level is
  `100 + (level - 1) * 75`, with a maximum level of 20.
  See [rewards](https://github.com/Metta-AI/polyworld/blob/7a7b22c85c1411bc37707a21b2a4a94e1b757fd8/examples/gods_of_the_arena/sim.nim)
  and [purchases](https://github.com/Metta-AI/polyworld/blob/7a7b22c85c1411bc37707a21b2a4a94e1b757fd8/examples/gods_of_the_arena/sim.nim).
- **Recovery:** respawn restores HP/mana, clears movement/attack state and restores
  ability readiness through the simulation. It does not recreate the policy VM.
  Script memory therefore needs to account for changes in the hero's lifecycle.
  See [respawn](https://github.com/Metta-AI/polyworld/blob/7a7b22c85c1411bc37707a21b2a4a94e1b757fd8/examples/gods_of_the_arena/sim.nim).
- **Combat:** basic attacks are separate from four abilities. Explicit target and
  point casting are registered BASIC functions. Bot auto-casting also exists;
  human-control instructions about pressing Q/W/E/R are not the BASIC contract.
  Cast acceptance spends resources; delayed effects resolve later against eligible
  targets. Measure actual impact, not only accepted casts.
- **Information:** object queries are visibility-filtered; static terrain queries
  expose terrain through fog. Read team/class, identity and map dimensions from the
  host. Do not transfer positional constants from earlier maps.

## Discrepancies found and resolved

The four current-reference wiki pages have been corrected by the source audit.
The claim column below identifies their earlier prose and the external Buff mirror;
the historical statistics remain historical.

| Claim/source | Current resolution |
| --- | --- |
| Old wiki: 64×64, movement clamped to 0–63 | Explicitly historical. Current host uses active map dimensions. |
| Buff/current mirrored guide: 128×128 | Downloaded competition preset is 116×116. `buildArena` uses config.mapSize and `mapTiles` reads the generated layer width. Re-resolve the actual league config before any evaluation; downloaded canonical config alone does not establish league pinning. |
| Guide introduction: Red living / Blue undead | Latest content has Red = Death Knight, Crossbowman, Lich, Warlock, Berserker; Blue = Vanguard Knight, Ranger, Arcanist, Druid Warden, Demon Hunter. Read selfClass; some guide hero cards already use these correct colors. |
| Old wiki: one policy controls five heroes | Current manifest has ten independent file-policy seats, one per hero. A repeated file can occupy multiple seats with independent VMs. |
| Old wiki: spells cannot be scripted | Current host registers castTarget/castPoint and charge/cooldown/recharge queries. |
| Public guide's manual controls | Describes human UI, not the entire bot execution path. Bot auto-casting remains present in pinned sim.nim. |
| Hero win-rate table | Dated 2026-09-13–14 cohort, 540 games spanning older versions. Fixed faction lineups share outcomes; rows are not independent estimates of each hero's causal strength. |
| Player standings | Published 100-game tournament on 2026.9.14.2, explicitly not the live leaderboard. Mixed-team and mono-team cohorts answer different questions. Its additional Score/Glory values are not the platform's binary scores contract. |

Source details: [hero factions](https://github.com/Metta-AI/polyworld/blob/7a7b22c85c1411bc37707a21b2a4a94e1b757fd8/examples/gods_of_the_arena/content.nim),
[map construction](https://github.com/Metta-AI/polyworld/blob/7a7b22c85c1411bc37707a21b2a4a94e1b757fd8/examples/gods_of_the_arena/arenas.nim),
[hero statistics](https://softmax.com/api/observatory/v2/wikis/Gods%20of%20the%20Arena/pages/hero-statistics.md),
[published standings](https://softmax.com/api/observatory/v2/wikis/Gods%20of%20the%20Arena/pages/player-standings.md).

## Community ideas — hypotheses, not adopted policy

[Bismarck's post](https://softmax.com/api/observatory/v2/posts/post_4e87805e-532c-419e-9818-1ac49d2b885f.md)
under James's name reports gains from target prioritization and a regression from
requiring an escort before siege. The zero-on-timeout mechanism is source-backed;
the quoted effect sizes and policy versions have not been reproduced or recovered.
The linked historical book is a further research lead, not evidence reviewed here.

[Dave's post](https://softmax.com/api/observatory/v2/posts/post_9d43f161-0deb-493c-b1f8-9825cf2262dd.md)
and his reply distinguish useful regrouping from indefinite waiting, and nominal
healing efficiency from actual recovery. The healing values match the current item
contract; coordination benefits remain hypotheses. No pact was made or message sent.

## What to investigate before choosing an optimization

1. Resolve the current league-bound game version/config and any existing owned policy
   the human wants to use. Establish whether bismarck source/artifacts are recoverable.
2. Inspect complete current-version games: how towers fall, which engagements prevent
   objective progress, timeout frequency, and differences between team/class assignments.
3. Join policy intent to accepted actions and replay impact. Validate the replay and
   metric extraction against a complete episode before claiming an analysis adapter works.
4. Pick a single behavioral hypothesis with the human; record episode-level outcomes
   and operational failures separately. Do not claim this documentation inspection
   establishes current competitive performance.
