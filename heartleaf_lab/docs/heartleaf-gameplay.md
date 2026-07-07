# Heartleaf — gameplay reference

The self-contained game reference for the Heartleaf lab: rules, the day cycle, the
dinner/scoring mechanics, the wire protocol, the bundled behavior framework, and a
strategy treatment. **Read this to understand Heartleaf without leaving the repo.**

The authoritative source is the **`Metta-AI/coworld-heartleaf`** repo (Nim game server
`src/heartleaf.nim`, protocol helpers `src/heartleaf/`, bundled players `players/`). This
doc distills that plus the game's own docs (`docs/rules.md`, `docs/game_rules.md`,
`docs/play_heartleaf.md`) and the `coworld_manifest.json`.

> **Repo status caveat (2026-07-06).** The game repo is topic `coworld-incomplete`:
> `uv run coworld certify coworld_manifest.json` has **not** passed yet (README badge:
> "coworld verify: failed"). A live Observatory league exists, but treat the game
> version / certification state as something to re-verify before relying on it.

## What Heartleaf is

Heartleaf is a **cozy multiplayer garden dinner game** for up to **9 gnomes** (one per
player). It runs on the **BitWorld Sprite-v1 protocol** — the same sprite-protocol
family as Crewrift — so it is a **gridworld**: the engine streams a labeled sprite scene
and the player emits gamepad input. There is no semantic "collect / host" API at the wire
level; a player decodes the scene and presses buttons.

Each gnome has a **personal house**, a **personal food inventory**, a **dinner history**,
and a **cumulative score**. The loop of a day: **gather food from shared gardens during
the day → decide where to be at dinner (6pm) → score by *hosting* a dinner that other
gnomes attend.** You do **not** score by hoarding food; you score by **feeding guests**.

## The day cycle

- A **round is one in-game day**: **8:00 AM → 10:00 PM**, advancing in 5-minute in-game
  steps. Real duration is set by `daySeconds` (league variant: **100 real seconds/day**;
  manifest default 180).
- **Morning setup:** every gnome starts **inside their own house**; gardens are seeded
  (each garden starts the day with one random vegetable).
- **Daytime:** gnomes leave their houses, roam the shared map, and **gather** — a garden
  holding food shows an exclamation marker; standing near it and interacting moves that
  food into the gnome's inventory. Food **persists in inventory across days** until spent
  as host food.
- **Evening:** the world visibly darkens through five stages (daylight → purple → dark
  blue) as a clock cue.
- **Dinner: displayed 6:00 PM, RESOLVES 6:55 PM** — the scoring tally fires at 6:55 PM
  (`DinnerTallyMinutes`), not at the 6:00 shown on the clock. To score you must be inside
  your own home *at the resolve*, not merely "around dinner." (See Exact timing + Dinner.)
- **End of day: 10:00 PM** — every gnome is teleported home, sees a cumulative-score
  panel (~10s), then the next day begins from morning setup.

The **league variant** runs **9 compressed days** (`maxTicks: 23760`, `maxGames: 1`,
`num_agents: 9`, `daySeconds: 100`) — deliberately enough days that every gnome gets a
hosting turn. `freeplay` (open-ended) and `smoke` (12 ticks) variants also exist.

## Exact timing — the authoritative table (verify code before trusting prose)

**Read this before writing any clock-gated behavior.** All values are from the game source
(`src/heartleaf.nim`, `src/heartleaf/common.nim`) at the pinned ref — cite it, don't infer.
A wrong mental model here silently disabled Cady's whole social phase once (the clock read
as `None` and the "6:00 dinner" was actually resolved at 6:55). Distinguish **displayed** vs
**resolved** times.

### Constants (source of truth)

| Constant | Value | Meaning |
|---|---|---|
| `DayStartMinutes` | `8*60 = 480` | day starts 8:00 AM |
| `DayEndMinutes` | `22*60 = 1320` | day ends 10:00 PM |
| `DayTotalMinutes` | `1320-480 = 840` | game-minutes per day |
| `DayStepMinutes` | `5` | clock advances in 5-min steps (quantized) |
| `DayStepCount` | `840/5 = 168` | number of clock steps in a day |
| `DinnerMinutes` | `18*60 = 1080` | **6:00 PM — the DISPLAYED dinner time** |
| `DinnerTallyMinutes` | `1080+55 = 1135` | **6:55 PM — when dinner actually RESOLVES + scores** |
| `DuskStartMinutes` | `17*60 = 1020` | 5:00 PM — world starts darkening (visual cue) |
| `TicksPerSecond` | `24` | sim tick rate |
| `daySeconds` | league **100** (manifest default 180) | real seconds per in-game day |
| `ScoreScreenTicks` | `10*24 = 240` | end-of-day score panel duration (~10s) |
| `ChatLifetimeTicks` | `5*24 = 120` | a chat bubble lingers ~5s |
| `GardenStartFoodCount` | `1` | each garden reseeds 1 random veggie per day |

### Minute ↔ tick mapping (this is what I got wrong)

- **`dayTicks = daySeconds * TicksPerSecond`.** League: `100*24 = 2400` gameplay ticks/day.
- The clock is **quantized**: `currentDayMinutes = 480 + step*5`, where
  `step = min(168, dayTick * 168 / dayTicks)`. So `game_minute` from a `dayTick`:
  `480 + 5 * floor(dayTick * 168 / dayTicks)`.
- **To convert a target game-minute `M` (absolute, e.g. 1135) to a dayTick** (league,
  dayTicks=2400): `dayTick ≈ (M - 480) / 840 * 2400`.
- **A full day = `dayTicks` gameplay ticks + `ScoreScreenTicks` score screen.** League:
  `2400 + 240 = 2640` ticks/day → 9 days ≈ `23760` (`maxTicks`). ✔ matches.

**Key league dayTicks (daySeconds=100, dayTicks=2400):**

| Event | Game time | dayTick (approx) |
|---|---|---|
| Day start / morning | 8:00 AM (480) | 0 |
| **Invite window opens** (our cutover) | 3:00 PM (900) | ~1200 |
| Dusk begins (visual) | 5:00 PM (1020) | ~1543 |
| **House-enter deadline** (be inside) | 5:00 PM (1020) | ~1543 |
| Dinner displayed | 6:00 PM (1080) | ~1714 |
| **Dinner RESOLVES + scores** | 6:55 PM (1135) | ~1871 |
| Gameplay ends → score screen | 10:00 PM (1320) | 2400 |
| Next day begins | — | 2640 |

> Cady's minute constants are **minutes-since-8AM** (`parse_clock_minutes` subtracts
> `8*60`). So displayed dinner = 600, **dinner-resolve = 655**, day-end = 840.

### The exact per-tick day sequence (from `step`)

Each tick: apply inputs → move players → `updateMessages` → `inc dayTick` → **if
`currentDayMinutes >= DinnerTallyMinutes (6:55) and not dinnerDone`: `startDinnerParties()`**
(this is the single scoring moment — see below) → if `dayTick >= dayTicks`:
`startScoreScreen()` (freezes `dayTick`, sets 240 score-screen ticks, **teleports every
gnome to their own home**, clears dinner records). After the score screen drains,
`startDay()`: `dayNumber++`, `dayTick=0`, **reseed gardens**, players keep inventory + score.

> **Gotcha that caused a false positive:** at the score screen every gnome is teleported
> home. So "inside my own home near the day boundary" is NOT evidence of hosting — it's the
> forced end-of-day teleport. Real hosting is only measurable at the **6:55 PM resolve tick**
> (and confirmed by the host's inventory clearing).

## Dinner — how scoring actually happens

Dinner is the **only** scoring event. It resolves **once**, at **6:55 PM**
(`DinnerTallyMinutes`; the clock shows 6:00 as the dinner *hour*, but the tally fires at
6:55) — `startDinnerParties()`, guarded by `dinnerDone` so it happens exactly once per day:

- A house **hosts a party** iff **its owner is inside it** (`host.mapIndex == its home map`)
  AT THE RESOLVE TICK AND **≥1 visiting gnome is inside the same house**. Multiple parties
  run simultaneously in different houses. Being home *before or after* 6:55 doesn't count —
  only presence at the resolve.
- **Food is multiplicative per guest:** every visitor eats the **full** amount of
  everything the host collected. If the host has {3 apples, 1 pear, 2 potatoes}, *each*
  visitor eats all of that.
- **The host scores:** `total hosted food items × number of visitors`.
  - 1 food item, 3 visitors → **3**. 6 food items, 2 visitors → **12**.
- **Visitors score nothing** for eating. Their upside: they eat for free **and keep their
  own inventory** — so their food survives to fund *their own* future hosting.
- After the party, the **host's hosted food is consumed** (removed); visitors' inventories
  are untouched.
- Score is **cumulative** across the episode's days.

**The strategic core falls straight out of the scoring rule:**

- **Only hosting scores.** A gnome that only ever visits finishes with 0, no matter how
  much it ate. To win you must host, at your own house, with guests present.
- **Guests are a shared, rivalrous resource.** There are 9 gnome-bodies. Every guest at
  *your* table is a guest not at a rival's table — and is themselves not hosting that
  night. Attracting guests is a **competition**, and it's social: a gnome decides whose
  invitation to accept.
- **Two multiplicative levers, both matter:** `food × guests`. High food with zero guests
  = 0. Many guests with one vegetable = weak. The best hosted day pairs a **large haul**
  with a **full table**.
- **Multi-day tension: host vs. visit.** You can't host and visit in the same instant
  (you're in one house at 6pm). Visiting banks free calories and preserves your food for a
  later hosting day; hosting cashes food in now for `food × guests`. Across the ~9 league
  days, sequencing *when* you host (with a big haul and a full table) vs. when you visit
  (to conserve, and to deny rivals a guest by... actually, visiting a rival *gives* them a
  guest) is the game. Note the pull: being someone's guest helps *them* score — so a strong
  policy wants others to guest for *it*, and is reluctant to be a guest unless the day is a
  write-off for its own hosting.
- **Coordination is everything and it runs over chat.** A party needs a host and at least
  one guest to *converge on the same house by 6pm*. Invitations, acceptances, and honoring
  commitments are the mechanism — see the behavior framework below.

## The wire protocol (Sprite-v1) and the bundled behavior framework

Two layers matter, and the distinction is the biggest strategic fact about building a
Heartleaf player:

1. **Sprite-v1 (the actual contract).** Players connect over WebSocket to `/player`; the
   server streams a labeled sprite scene and the player returns gamepad input (a button
   mask each tick — movement + an "A" interact). All game actions (collect from a garden,
   enter/exit a house, stand somewhere) are **emergent from moving the gnome and pressing
   A** — there is no high-level action message. Protocol spec:
   `https://github.com/Metta-AI/bitworld/blob/master/docs/sprite_v1.md`. (This is the same
   protocol family as Crewrift — see `crewrift_lab/docs/crewrift-protocol.md` for the
   sibling treatment.)

2. **`talking_villager` (the bundled Nim framework the shipped players use).** The game
   ships a ~3000-line Nim behavior framework (`players/talking_villager/`) that already
   does the hard sprite-protocol work: it decodes the scene into game state (own gnome,
   houses, gardens, other gnomes, the clock, chat transcript), exposes an **8-verb
   semantic action layer**, converts a chosen verb into low-level movement masks
   (pathfinding), calls an **LLM** for each decision, and manages chat. The bundled
   `shy_/chatty_/friendly_/fatherly_villager` players are each just
   `talkingVillagerMain(name, soul.md)` — i.e. **the same engine driven by a different
   personality prompt** (`soul.md`).

   The **8 semantic actions** (`players/talking_villager/decisions.nim`):
   `keep_gathering_plants`, `find_person`, `find_house`, `go_home`,
   `stand_at_house_garden`, `stand_next_to_person`, `say_to_person`, `go_to_party`.
   The LLM returns one strict JSON object — fields `action`, `targetName`, `houseIndex`
   (1–9), `message`, `commitParty`, `reason`. The framework enforces a **time policy**
   (stop gathering and commit to a party after dinner nears), a **commitment model** (honor
   the party you promised), and **fallback decisions** on any LLM/parse failure — so it
   never stalls. The LLM call is **Bedrock** (`bedrock_auth.nim`) and is **mockable** via
   the `TALKING_VILLAGER_MOCK_REPLY` env var (the manifest sets each bundled player's mock
   to `{"action": "keep_gathering_plants"}`).

**Why this matters for our player.** Unlike Crewrift (where crewborg decodes raw Sprite-v1
itself), Heartleaf hands us a working perception→pathfinding→semantic-action→chat stack for
free. That opens (at least) three build paths, cheapest first:
  - **(a) New `soul.md` on `talking_villager`.** Keep the framework, write a
    stronger personality/strategy prompt. Fastest path to a competitive gnome; tests the
    hypothesis that the shipped players are limited by their prompt, not their engine.
  - **(b) Deterministic decision layer.** Fork the framework and replace the LLM decision
    with rule-based logic (e.g. explicit host-vs-visit scheduling, food-threshold hosting,
    guest-recruitment heuristics) — removes LLM cost/latency/variance, and the scoring rule
    is simple enough that good heuristics may beat a generic prompt.
  - **(c) Raw Sprite-v1 (crewborg-style).** Build from the protocol up in Python via the
    players SDK. Most work; only justified if (a)/(b) hit a ceiling the framework imposes.
  The choice is a **human-direction fork** (AGENTS.md loop step 3), not a default — do not
  pre-commit to one.

## The bundled players (the field we start against)

All four league players are the **same `talking_villager` engine** with different souls:

- **shy_villager** — gathers quietly, speaks softly, honors invitations.
- **chatty_villager** — greets everyone, talks constantly, spreads invitations.
- **friendly_villager** — welcomes everyone, shares food, hosts warm dinners.
- **fatherly_villager** — checks on others, shares food, makes sure nobody dines alone.

The `soul.md` prompts encode a general good-citizen strategy (gather early, stand at your
house from ~3pm, invite friends by ~4pm, stop gathering after 5pm, converge by 6pm, honor
promises). Read `players/friendly_villager/soul.md` in the game repo for a full example —
it's a good baseline of "what a competent generic gnome does," and thus a map of where a
purpose-built policy can beat it.

## Results / how a game is scored out

The episode `results_schema` (per manifest) emits, **per day**: `day`, and length-9
arrays `names` / `usernames` / `playerNames` / `scores` in **score order** — i.e. the
cumulative score of each of the 9 gnomes at each day's end. That's the signal an eval
report is built from: who out-hosted whom, and how the gap evolved across the 9 days.

**Scoring math (verified in `heartleaf.nim`):** per dinner, `score = (host's total food
items) × (number of guests)`, added to the host's cumulative total (`host.score += …`).
Only hosts score; visitors get nothing. Scores are **integers, `minimum: 0`** (results
schema, confirmed identical in the deployed 0.1.10 manifest) — **the game never emits a
negative.**

**⚠️ Failure signal is NOT a −100 score (unlike Crewrift).** The `−100` sentinel is
*Crewrift-game-specific*; the metta episode runner has no −100 — it flags a player that
fails to connect / crashes / times out by **failing the episode** with
`error_type="player_error"|"episode_timeout"` and `failed_policy_index=<slot>`
(`coworld/runner/runner.py`). So a non-connecting gnome's *game score is `0`*, identical to
a gnome that connected but never hosted. **Consequence for eval interpretation: do NOT
apply Crewrift's "drop score ≤ 0 / −100" ops-filter here** — it would discard legitimate
0-score gnomes. Detect our player's failures via **episode status / `failed_policy_index`**,
and read a *completed-episode* score of 0 as "played but never hosted" (a gameplay signal).

**Deployed vs public source:** the live league runs **heartleaf 0.1.10**, but the public
`Metta-AI/coworld-heartleaf` repo master is only **0.1.0** (no 0.1.10 tag/branch — it's a
deployment-only build). `coworld download heartleaf` fetches the deployed **package**
(manifest + image refs, not Nim source). The 0.1.10 manifest matches 0.1.0 on scoring/
protocol; its only roster change is an added base `villager` player.

## Open questions to resolve empirically

- **Exact garden/food economy:** how many gardens, respawn cadence, item variety, and the
  realistic per-day haul ceiling. (`docs/game_rules.md` says "one random vegetable per
  garden at day start" and an exclamation marker; the map is `docs/heartleafMap.png`.)
- **Host-vs-visit equilibrium among 9 gnomes:** with everyone wanting to host, what guest
  distribution actually emerges, and whether a policy can reliably recruit a full table.
- **Chat leverage:** how much invitation quality / commitment-honoring actually moves guest
  counts vs. mere proximity at 6pm.
- **Framework ceiling:** whether the shipped players are prompt-limited (build path a) or
  engine-limited (paths b/c).

These are the first things a survey of real episodes should answer; none should be taken
as settled from this doc alone.
