# Vanilla WoW — gameplay reference

The self-contained game reference for the Vanilla WoW lab: what the game *is*, the two
game shapes, how a scored episode works, how scoring is computed, and the
strategically-relevant WoW mechanics — **written to be understandable even if you have
never played World of Warcraft.** Read this to build a mental model without leaving the
repo.

Two companion docs go deeper on the parts this one only summarizes:
- **[`vanilla-wow-player-contract.md`](vanilla-wow-player-contract.md)** — the wire
  contract: how a player connects, what it observes, what it emits, and how it's shipped.
- **[`vanilla-wow-rfc-roles.md`](vanilla-wow-rfc-roles.md)** — the five RFC support roles
  (commissioner/grader/diagnoser/optimizer/reporter) and the exact round-scoring math.

The authoritative source is the **`coworld-vanilla-wow`** repo (currently cloned at
`~/coding/coworlds/coworld-vanilla-wow`): the Python adapter under
`src/vanilla_wow_coworld/`, the Nim player under `player/`, the dungeon definitions under
`dungeons/`, and `coworld_manifest_template.json`. Citations below are `file:line` into
that repo at the state read on 2026-07-13; **re-verify against the code before trusting
prose** — this game is under active development.

> **Readiness caveat (updated 2026-07-14).** The game repo's README badge still reads
> **"coworld verify: not ready"** — the "ready" badge is gated on one *retained* hosted
> commissioner round + one XP-request episode on Kubernetes (`docs/coworld-readiness.md`).
> However, as of 2026-07-12 an Observatory league **"Vanilla Wow"** (division "Leveling
> Ladder") exists, the deployed package is **v0.1.6**, and hosted XP-requests run to
> completion (verified 2026-07-14 with a 4-episode `orc-fresh-start` smoke). The badge and
> the league's existence disagree — treat the ladder's scoring/retention as unverified. See
> [`../WORKING_CONTEXT.md`](../WORKING_CONTEXT.md) for what that means for the lab's loop.

---

## What this game is (the one-paragraph version)

Vanilla WoW Coworld is **a real World of Warcraft 1.12.1 realm turned into a competitive
AI benchmark.** The world is a genuine [VMaNGOS](https://github.com/vmangos/core) server
(the mature open-source emulator of the 1.12.1 "Vanilla" client, build **5875**), not an
abstract gridworld. A "player" is an AI agent that controls one WoW *character*: it logs
in, walks around with real movement physics, fights monsters, completes quests, loots,
sells junk, trains spells, dies and recovers, and groups up — all through the same packet
protocol a human's game client speaks. It competes on **how well it plays actual WoW**:
either how much **experience (XP)** its character accumulates over time, or how fast a
five-character party can **clear a dungeon**. (`README.md:23-28`, `docs/architecture.md:1-6`)

If you've never played WoW, the two facts that matter most:
1. **XP / leveling is the core progression.** A character starts at level 1 and earns XP
   by killing monsters and completing quests. Enough XP → the next level → stronger
   character. "How much XP" is literally the competitive score on the persistent realm.
2. **A "dungeon" is a self-contained instanced area with boss monsters.** The scored
   competition is a five-player party clearing **Ragefire Chasm** (a low-level starter
   dungeon), racing to kill its four bosses fastest.

---

## Two game shapes (this is the biggest structural fact)

The repo runs the *same* WoW engine in two very different modes. Keep them distinct — they
score differently and one of them is what actually gets submitted.

### 1. The persistent tournament realm — the continuous overworld

A single long-lived VMaNGOS realm that runs continuously; think "the shared MMO world."
(`docs/persistent-tournament.md:1-13`)

- **One submitted player → exactly one persistent account** (enforced both directions:
  one entrant ↔ one account) (`docs/persistent-tournament.md:10`, `:227-230`).
- A player may create **any number of characters** on that account
  (`docs/persistent-tournament.md:11`).
- **Leaderboard rank = the highest total XP of any single character on that account**
  — your best character, not a sum (`docs/persistent-tournament.md:12-13`, `:36-39`).
- The Coworld WebSocket only *provisions identity and reports status*; the bot then logs
  **directly** into `realmd` (auth) and `mangosd` (world) over native WoW TCP and plays.
  Coworld owns account assignment, liveness, logs, and score attribution — not the
  gameplay packets (`docs/persistent-tournament.md:19-33`).
- The leaderboard is recomputed on a cadence from the realm database, independent of any
  episode (`docs/persistent-tournament.md:41-47`).

**"Spontaneous practice runs produce no score."** If characters group up and clear a
dungeon *on the live persistent realm*, that run is captured as a replay
(`scope=persistent_realm_session`) for evidence — but it earns **nothing** on the
leaderboard. Only sandboxed, snapshot-backed episodes produce scored results
(`docs/persistent-tournament.md:120-139`).

> **Status:** the persistent-tournament *commissioner*, durable account-mapping storage,
> and a hosted live leaderboard are **designed but not yet implemented** — describe them
> as target shape, not shipped (`docs/persistent-tournament.md:273-284`).

### 2. Isolated, scored RFC episodes — the certified/submitted surface

Scored work never touches the writable persistent realm. Instead it runs on **disposable,
sandboxed VMaNGOS servers** created from a frozen copy of a few characters. This is what
`coworld certify` exercises and what a submission is judged on.

**How a scored episode is born, step by step** (`docs/specs/0001-isolated-rfc-episodes.md`):

1. **Snapshot.** A snapshot exporter selects the **five highest-XP eligible, logged-out**
   characters (level ≥13, non-GM, one per account) plus the account/inventory/pet/corpse
   rows needed to play them, and packs them into a signed, digest-addressed **`CWROSTER`**
   artifact (HMAC-SHA-256; a fixed `CWROSTER` magic + SHA-256 of the compressed payload).
   It deliberately **excludes** groups, guilds, mail, auctions, instance saves, and world
   tables. The persistent DB is read-only to this process; the artifact is *confidential*
   because it contains VMaNGOS auth rows (`0001:41-48`, `:129-151`, `:59-62`).
2. **Spin-up.** An isolated game job **boots a fresh VMaNGOS database**, verifies + imports
   the snapshot *before* `realmd`/`mangosd` start, resets transient online/instance state,
   replaces source usernames with random episode-local `CWR<n>…` aliases (so source
   identity is absent even from auth logs), stages the copies at Ragefire Chasm, and runs
   the five policy slots (`0001:51-53`, `:143-147`).
3. **Play + record.** The episode plays out; a recorder tracks the `(map_id=389,
   instance_id)` session lifecycle: `first_enter` on the first non-empty snapshot, appends
   as membership changes, `all_left` when it empties (or "truncated" on process shutdown).
   VMaNGOS may hand out a different live instance id than reserved, so the recorder's value
   is authoritative and propagates into results + replay (`0001:60-62`, `:195-202`).
4. **Tear-down.** "Its database is discarded after results and replay upload. **Nothing is
   written back.**" No XP, loot, deaths, or any episode mutation ever merges into the
   overworld (`0001:53`, `:118-120`, `:190-191`).

So: a **scored episode** = one disposable server from one immutable five-character
snapshot. An **XP request** creates one or more such episodes directly. A **round** is the
commissioner's collection of episodes — one per entrant (`0001:184-191`).

---

## The RFC benchmark: `rfc-five-player-clear`

This is the first session-shaped Coworld benchmark for the repo, and the scored
competition today (`docs/coworld-rfc-roles.md:3-4`).

**The task.** Five seeded **level-30 Horde** characters start at the entrance of
**Ragefire Chasm** (map **389**) and must kill the four stock bosses
(`docs/coworld-rfc-roles.md:5-7`, `dungeons/example-ragefire.dungeon.json`):

| Boss | Creature entry id |
|---|---|
| Oggleflint | 11517 |
| Taragaman the Hungerer | 11520 |
| Jergosh the Invoker | 11518 |
| Bazzalan | 11519 |

The dungeon definition (`dungeons/example-ragefire.dungeon.json`, format
`coworld-dungeon-v1`, `map_id 389`) declares four `kill` objectives (one per boss, in that
order) plus one `reach` objective co-located with Bazzalan; scoring policy `run_score`
(`example-ragefire.dungeon.json:2-5`, `:126-157`). Note: `dungeons/ragefire-descent.dungeon.json`
is a *different, harder* single-boss variant — **not** the benchmark.

**The party** (from the manifest variant, `coworld_manifest_template.json:522-594`): five
level-30 troll bots — a **warrior tank**, a **priest healer**, a **shaman**, a **rogue**,
and a **mage** — each `driver: "bot"`, 20 gold. Episode budget `max_ticks: 10000`,
`tick_rate: 0.1`.

**The rule that shapes everything: one policy fills all five slots.** The commissioner
schedules one episode per entrant and **repeats that policy across all five slots**
(`RFC_PARTY_SIZE = 5`, `self_play=True`, `policy_version_ids = [entrant] * 5`). So a
leaderboard row measures **one policy's complete party coordination** — tank + healer +
three DPS all being *the same brain* — not five unrelated policies thrown together
(`docs/coworld-rfc-roles.md:29-32`; `src/vanilla_wow_coworld/rfc_commissioner.py:38-39`,
`:113`, `:138-146`).

---

## How scoring works

There are three scoring surfaces. Get the layering right: a **per-slot raw game score**, a
**commissioner round score** (what ranks entrants in a round), and the **persistent XP
metrics** (what ranks the overworld leaderboard).

### The two XP metrics (persistent realm + XP requests)

(`src/vanilla_wow_coworld/constants.py:10-12`)
- **`highest_character_total_xp`** — the leaderboard metric: an account's single
  highest-XP character.
- **`top_character_xp_gained`** — the per-session metric: XP gained during the session.

`total_xp` = the sum of XP-for-all-prior-levels + the character's current XP; accounts rank
by `total_xp DESC, level DESC, xp DESC` (`scoring.py:184-199`, `:305-320`).
`xp_gained = max(0, end.total_xp − start.total_xp)` (`scoring.py:269`).

### The per-slot raw dungeon score

Each slot in a dungeon episode gets a raw score (`dungeon.py:1823-1873`):

```
score = max(0, objectives_completed × 1_000_000
             + bosses_defeated      ×   250_000
             + xp_gained
             − deaths               ×    10_000
             − elapsed_seconds)
```

where `elapsed_seconds = end.played_time − start.played_time`, `xp_gained = max(0, ΔXP)`,
and **`deaths` is currently always 0** — death-counting isn't implemented in v1, the field
is present-and-zero until a counter lands (`dungeon.py:1832-1852`). The huge
objective/boss coefficients make the ordering **lexicographic**: (1) objectives completed,
(2) bosses defeated, (3) XP gained, (4) fewer deaths, (5) lower elapsed time — so every
four-boss clear outranks every partial run, and among clears the faster one wins
(`docs/coworld-rfc-roles.md:14-27`).

**How a boss "death" is detected — and the 7200 number you'll see everywhere.** A kill is
read from VMaNGOS's `creature_respawn` table: a row whose `respawn_time` is still in the
future means that creature is dead, awaiting respawn. The respawn timer is pinned to
**`DUNGEON_LAB_RESPAWN_SECONDS = 7200`** so a killed boss stays *readable as dead* for the
whole run (`dungeon.py:1076`, `:1760-1803`).

> ⚠️ **Do not call 7200 the "episode deadline."** It is the **boss-respawn timer**, not a
> session time limit. The episode's actual wall-clock budget is derived from
> `max_ticks / tick_rate` (RFC: 10000 / 0.1). Some prose in the game repo loosely calls
> 7200 "the single time-based termination boundary" for dungeon *exploration control*
> (`docs/bot-world-state.md:136-137`) — that's about not letting other signals create
> extra stop-gates, not a real 7200s clock. When you write about time, be precise about
> which of these you mean.

### The commissioner round score (what ranks entrants)

For each entrant's episode the commissioner computes one number
(`rfc_commissioner.py:184-192`):

```
full clear:  score = max(1.0, 1_000_000 − clear_seconds)   # faster = higher
partial:     score = bosses_defeated / bosses_total          # a fraction in [0, 1)
```

So **every clear (≥ 1.0) beats every partial (< 1.0)**, and among clears the fastest wins.
A "full clear" means *all four* boss kill objectives complete; only full clears get a
recorded `best_clear_seconds` (`rfc_commissioner.py:160-181`). Round ranking sorts by
`(-score, best_clear_seconds or +inf, policy_version_id)` and attaches metadata:
`full_clear`, `best_clear_seconds`, boss progress, `mean_game_score`, and failure state
(`rfc_commissioner.py:216-246`). Full detail + the five roles that produce/consume these
numbers are in [`vanilla-wow-rfc-roles.md`](vanilla-wow-rfc-roles.md).

### Reading eval results (a caution for later)

There is **no `-100` failure sentinel** here (that's a Crewrift-specific thing). A player
that fails to connect/crashes/times out fails the *episode* through the runner, not via a
sentinel score. So when real episodes exist, detect *our* player's failures via episode
status, and read a completed run's low score as a *gameplay* signal ("played but didn't
clear"), not an ops failure. (This mirrors the lesson learned in
[`../../heartleaf_lab/docs/heartleaf-gameplay.md`](../../heartleaf_lab/docs/heartleaf-gameplay.md).)

---

## The mechanics that matter for strategy

A competitive player has to actually *play WoW well*. Here's the strategically-relevant
surface, explained for a non-WoW-player, with pointers to where the engine implements each.

### The nine classes (and why only seven are playable today)

WoW 1.12 has nine character classes, each with a signature resource/mechanic
(`docs/class-matrix-qa-plan.md:56-88`; class ids in `player/game_client/characters.nim:14-22`):

| Class | Signature mechanic (in plain terms) |
|---|---|
| **Warrior** | **Stances** (Battle/Defensive/Berserker) swap the ability set; **rage** builds up from fighting and fuels attacks. The natural tank. |
| **Paladin** | **Seals** (self-buffs a **Judgement** unleashes onto a target) + **Blessings** (party buffs). *Alliance-only.* |
| **Hunter** | A tamed **pet** that tanks/attacks; exclusive **Aspects** (self-buffs); ranged shots that consume **ammo**. |
| **Rogue** | **Combo points** built on a target, then spent on finishers; **stealth** to open fights unseen. |
| **Priest** | Heals and buffs; **Shadowform** flips it to a shadow-damage caster. The natural healer. |
| **Shaman** | Drops **totems** (ground effects/buffs); strong burst and utility. |
| **Mage** | Ranged/AoE nukes; **Polymorph** turns an enemy into a harmless sheep (crowd control that breaks on damage). |
| **Warlock** | **Soul shards** (a consumable) power demon summons; damage-over-time specialist. |
| **Druid** | **Shapeshift forms** (Bear tank / Cat DPS / Travel / Aquatic), each with its own ability bar. |

**Only seven classes are seedable today.** All character seeding is **Horde-only**, and
`CLASS_SEED_DEFAULTS` maps just seven classes to level-29 twink templates — **no paladin,
no druid** (`class-matrix-qa-plan.md:44-63`; `src/vanilla_wow_coworld/vmangos_character.py:89`):
- **Paladin is structurally unreachable** because it is Alliance-only and seeding only
  makes Horde characters; making it reachable is "the largest structural lane in the plan"
  (`:50-51`, `:58`, `:163-170`).
- **Druid is unseeded** even though the client supports shapeshift — its mechanic is
  "modeled but only synthetically proven" (`:51`, `:63`, `:88`).

The bundled combat AI reflects this exactly: `player/bots/rotations.nim` defines
per-class **`ClassRotation`** rotations for the same seven classes (Shaman, Warrior,
Hunter, Rogue, Warlock, Mage, Priest); paladin and druid fall through to an empty rotation
(`rotations.nim:1208-1224`). A rotation is a prioritized list of ability rows tagged by
role (damage / heal / weapon-buff / self-buff / finisher / interrupt / defensive / pet),
target restriction, resource cost, range, and a trained-rank chain — with a 5-yard melee
band and a `meleeWeave` flag for instant abilities that ride the auto-attack swing
(`rotations.nim:170-244`).

### Combat, briefly

Real Vanilla combat: casts and channels, misses/resists, ammo, auto-attack swings, ability
rank supersession, interrupts. The **Spell Lab** variants exist to test all of this
deterministically against inert **`NullAI` target dummies** (a hostile boar, a neutral
ogre, a friendly orc) with faction overrides, on the flat mob-free GM Island
(`docs/spell-lab.md:10-45`, `:68-76`). One subtlety worth internalizing: a unit's
**reaction color** (hostile/neutral/friendly, from `GetReactionTo`) is **separate** from
whether you can **attack** it — the neutral ogre is attackable despite not being hostile;
the friendly orc can't be attacked; a heal cast at a hostile unit **redirects** to a legal
friendly target (the "friendly-cast target gate") (`docs/spell-lab.md:26-45`;
`docs/specs/0004-general-leveling-experiment.md:68-70`).

### Leveling (the XP engine)

The bundled leveling policy is a single-decision-per-tick loop with a strict priority order
(`player/bots/leveling/planner.nim`, `chooseLevelingDecision`):

1. **Stop** at the profile's target level.
2. **Death recovery** — no server-side repair exists, so a dead character must genuinely
   recover: **release spirit** → run its ghost back to its **corpse** and **reclaim** it (a
   "corpse run"), or, if that keeps failing/is unsafe, **resurrect at the spirit healer**
   (creature 6491, at every graveyard) and eat the XP-loss penalty + wait out Resurrection
   Sickness (`planner.nim:24-118`; `targets_and_recovery.nim:291-355`).
3. **Combat** — emergency heal/potion by health threshold, then engage the nearest target
   melee-or-ranged by distance.
4. **Vendor/maintenance** — repair gear and **sell junk** when needed. Repair is a *client*
   action gated on affordability (you can't repair with no money), not a server-side reset
   (`routing_and_actions.nim:483-494`).
5. **Quests** — accept a quest at its giver; once the server flags it complete, turn it in.
6. **Loot** corpses (unless bags are full), **auto-equip** upgrades and bigger bags.
7. **Train** new spells — level-gated (`shouldTrain`) at the class trainer.
8. **Farm** — travel to a level-appropriate area via authored safe routes and grind.

Three authored starter-zone profiles ship: `durotar-1-10.json`, `mulgore-1-10.json`,
`tirisfal-glades-1-10.json` (the three Horde starting zones), plus a shared
`zone_progression_policy.json` (`player/bots/leveling_profiles/`).

There is also an **experimental "general-grinding" lane** (`docs/specs/0004`): an
*identity-blind* policy that chooses from client-observed *affordances* (action kind,
relation, distance, level delta, reachability) instead of authored creature names or
coordinates — built to prove the strategy *transfers* rather than memorizing content. It is
**opt-in, default-off**, with "bounded live proof pending"; the authored policy remains the
control arm and runtime default (`0004:3`, `:39-50`, `:76-98`).

### Navigation & physics (client-honest, always)

Movement is **real client physics over a Detour navmesh** — the same walkable-polygon mesh
a server-side pathfinder uses. There is **no coordinate teleport, no disabled collision, no
"walk straight to XYZ" fallback** (`docs/bot-world-state.md:41-58`;
`docs/king-richard-three-lane-prompt.md:71-73`). The player observes a radius-bounded local
graph whose nodes are actual polygons and whose edges are actual `dtLink` adjacency, keyed
stably by `map:tile_x:tile_y:layer:poly_index`; an unavailable graph is treated as
**unknown, not empty or walkable** (`bot-world-state.md:15-33`).

Dungeon exploration is a **graph search**: mark the current polygon visited → prefer an
adjacent *unvisited* polygon → when the ring is exhausted, route through the visited
component to the nearest reachable unvisited polygon → **preempt** for combat / death /
required boss sightings → resume from the latest polygon (`bot-world-state.md:59-68`). Boss
entry ids "define completion and discovery order only — they do not select authored boss
coordinates," so the party must *find* the bosses by legal navigation
(`bot-world-state.md:124-126`).

### The breadth: 15 manifest variants

The RFC clear is the scored competition, but the game models a *lot* more, exposed as 15
manifest `variants` (`coworld_manifest_template.json`). They map the engine's full surface:

- **RFC Five-Player Clear** — the scored 5-player Ragefire clear (the competition).
- **Browser Player Session / Manual Real Session** — bring-up paths for the wasm browser
  client and a human-driven native session.
- **Orc Fresh Start** — five level-1 orc-start fixtures (one per valid orc class) with real
  starter gear/spells — true from-scratch leveling.
- **Five Geared Party** — five level-30 trolls staged in the open world near Razor Hill.
- **Tower Climb Solo** — one shaman in a deterministic generated tower-climb run (RFK).
- **Deadmines Party / Dungeon Lab: Example Deadmines** — a level-20 party clears the
  Alliance-zone Deadmines dungeon (map 36); the "Dungeon Lab" variant exercises the authored
  dungeon-definition → world-overlay toolchain.
- **Z7 Class Combat Lab / Z7 Low-Rank Spell Lab** — melee mechanics (Charge, Stealth, Pick
  Pocket/Lock) and low-rank spell visuals on GM Island.
- **Spell Lab: Lightning Bolt / …Resist / …Failure Scenarios / …Family Matrix** — projectile
  visuals, miss/resist wire events, cast-failure codes, and cross-class spell coverage.
- **Mini Auction World** — three characters exercise the economy in Orgrimmar (auction house
  sell/bid, mail, trade).

The point for us: a competitive player must handle real WoW breadth, but the **scored
target today is the RFC clear** (and, on the persistent realm, raw XP).

---

## The baseline players (what "good" looks like)

Two named bots define the reference bar (`docs/bots.md:50-61`;
`player/king_nimrod/`, `player/king_richard/`):

- **King Nimrod** — the **headless, submittable** bot (it's what the player Docker image
  compiles, `-d:noGui`). Authored **farm/follow** behavior (`--mode=farm` / `--mode=follow`)
  with hand-authored Teldrassil farm areas. Its stated end goal (`king_nimrod/plan.md:15-18`)
  is a bot that can level 1→60 with real play — "move like a real player, understand the
  world, fight, quest, loot, sell, repair, train, recover from death, and coordinate" —
  built bottom-up with the rule "don't add higher-level intelligence until the lower-level
  loop is boring."
- **King Richard** — the **direct-protocol control runtime** with a richer Python leveling
  policy and the identity-blind general-grinding lane; drives the persistent character.
  Its **three-lane demo** is the clearest picture of a competitive player
  (`docs/king-richard-three-lane-prompt.md:10-21`): (1) a high-level character *solos* the
  RFC four-boss clear; (2) a **level-20 five-client party** (warrior tank, shaman healer,
  rogue/hunter/warlock DPS) clears RFC with real invite/accept grouping, the tank taking
  first contact, DPS assisting the tank's target, and the healer making resource-aware
  calls from its own party-frame truth; (3) the persistent character levels up through
  ordinary open-world play.

Everything those bots do obeys the client-honesty contract (read a snapshot → queue one
typed action → wait for the *settled* authoritative result → repeat; "action selected" is
not success). That contract is the subject of
[`vanilla-wow-player-contract.md`](vanilla-wow-player-contract.md).

---

## Open questions to resolve empirically (once real episodes exist)

- **Does the "Vanilla Wow" league actually score/retain rounds?** As of 2026-07-14 the
  league + "Leveling Ladder" division exist and hosted XP-requests complete, but the
  readiness badge is still "not ready" and no retained round has been observed
  (`docs/coworld-readiness.md`). Verify a scored round exists before claiming the loop is
  fully runnable.
- **RFC clear difficulty for a self-play party** — how hard is a same-brain 5-slot tank +
  healer + 3 DPS coordination problem in practice? Where do parties wipe?
- **Framework ceiling** — how far do the bundled leveling profiles + class rotations get
  before a purpose-built policy must diverge?
- **Authored vs identity-blind** — does the general-grinding lane actually transfer better
  than authored content, and is it worth the cost?

None of these should be treated as settled from this doc alone.
