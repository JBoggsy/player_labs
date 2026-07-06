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
- **Dinner: 6:00 PM** (see below).
- **End of day: 10:00 PM** — every gnome is teleported home, sees a cumulative-score
  panel (~3s), then the next day begins from morning setup.

The **league variant** runs **9 compressed days** (`maxTicks: 23760`, `maxGames: 1`,
`num_agents: 9`, `daySeconds: 100`) — deliberately enough days that every gnome gets a
hosting turn. `freeplay` (open-ended) and `smoke` (12 ticks) variants also exist.

## Dinner — how scoring actually happens

Dinner is the **only** scoring event. At 6:00 PM:

- A house **hosts a party** iff **its owner is inside it** AND **≥1 visiting gnome is
  inside the same house**. Multiple parties run simultaneously in different houses.
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
