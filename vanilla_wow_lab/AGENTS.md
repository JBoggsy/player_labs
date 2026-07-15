# vanilla_wow_lab — agent guide

The **Vanilla WoW** corner of player_labs: where we build, evaluate, and improve **player
policies** for the Vanilla WoW game. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the improvement loop,
your role in it (speed first), the submission gate, and the game-agnostic skills. This file is
the **Vanilla-WoW-specific layer** on top of it: the game, the docs, the practices, and the
policies we optimize. When the two disagree, the root defines *process*; this file defines
*Vanilla WoW*.

> **Lab status (2026-07-14): `wowborg` v1 (idle-login skeleton) uploaded and hosted
> XP-requests work; the league exists but its scoring is unconfirmed.** The Observatory
> league **"Vanilla Wow"** (division "Leveling Ladder") exists as of 2026-07-12 and the
> deployed game is **v0.1.6**, but the game repo's README badge still reads **"coworld
> verify: not ready"** — the badge and the league's existence disagree, so treat the ladder's
> scoring/retention as unverified. A 4-episode hosted smoke on `orc-fresh-start` completed
> (score 0.0, no crash) though per-agent policy logs weren't retained. **Episode-duration
> trap:** wowborg v1 never self-terminates, so episodes run to the full variant deadline —
> `rfc-five-player-clear` is ~27.8 h/episode; smoke on `orc-fresh-start` (~17 min) or
> override `max_ticks`. Live state + next steps: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).

## What Vanilla WoW is

Vanilla WoW Coworld is **a real World of Warcraft 1.12.1 realm** (backed by VMaNGOS) turned
into a competitive AI benchmark. A player controls one WoW *character* over the real WoW
binary protocol — logging in, moving with genuine physics, fighting, questing, looting,
selling, training, dying/recovering, and grouping. It competes two ways: a **persistent
realm** (ranked by an account's highest-XP character) and **isolated scored episodes** (the
certified surface), where the benchmark **`rfc-five-player-clear`** runs one policy across all
five slots of a party clearing Ragefire Chasm's four bosses, fastest full clear winning.

For the full game — the two game shapes, the RFC episode, the scoring math, and the WoW
mechanics that matter — read [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md)
(the lab's self-contained, WoW-naive-friendly reference). The wire contract and the RFC roles
are split into [`docs/vanilla-wow-player-contract.md`](docs/vanilla-wow-player-contract.md) and
[`docs/vanilla-wow-rfc-roles.md`](docs/vanilla-wow-rfc-roles.md). The game source in the
`coworld-vanilla-wow` repo remains the ultimate authority.

**The one architectural fact that shapes everything here:** unlike the other three labs
(Python SDK players on a sprite/text protocol — crewborg, cady, mentalist), a **Vanilla WoW
player is a Nim, packet-level WoW client** (the headless bot **King Nimrod**, compiled
`-d:noGui`) that plays a *real* VMaNGOS realm through a WebSocket→TCP bridge. It must obey a
strict client-honesty contract — **read a snapshot → queue one typed action → wait for the
settled authoritative result → repeat; "action selected" is not success** — with no teleport,
packet injection, synthetic state, disabled collision, or DB intervention. That makes building
a competitive player heavier here than a prompt swap (see [Player build paths](#player-build-paths)).

## The loop, in Vanilla-WoW terms

The root loop (evaluate → report → direction → implement → rebuild+reupload → repeat → human
gate → submit) runs **unchanged** here *once the game supports it*. Right now it is **blocked**
(see status above): there is no live scored league, and uploading a policy has nothing to
compete in yet. When that clears, the Vanilla-WoW-specific instruments will be:

- **Evaluate** (step 1) — experience requests against the uploaded policy. Two axes matter:
  the **RFC clear** (does the same-brain 5-slot party *fully clear* — all four bosses — and how
  fast?) and, on the persistent realm, **XP accrual** (highest-character total XP over time).
  The competition metric is **clear-then-speed**: a partial run scores < 1.0 regardless of XP,
  so crossing the full-clear threshold comes first (see
  [`docs/vanilla-wow-rfc-roles.md`](docs/vanilla-wow-rfc-roles.md#round-scoring--how-episodes-become-a-ranking)).
- **Report** (step 2) — pull artifacts with the game-agnostic `coworld-episode-artifacts`
  skill, then distill. **There is no Vanilla-WoW report skill yet** (see [Skills](#skills));
  the natural inputs are the reporter's `recap`/`events`/`stats` and the diagnoser's
  `missing_bosses` findings.
- **Implement** (step 4) — change the policy under optimization (see
  [Player build paths](#player-build-paths)); keep tunable knobs (rotation priorities, farm
  thresholds, route choices, party roles) in a config layer separate from logic so each
  iteration is attributable.
- **Rebuild / upload / submit** (steps 5–8) — build the Nim player image (two-stage Docker;
  see [`docs/vanilla-wow-player-contract.md`](docs/vanilla-wow-player-contract.md#the-submittable-image)),
  then the game-agnostic skills + [`../player-build.md`](../player-build.md) for upload/submit.
  The hosted eval is the test; **do not** buy pre-upload confidence with local runs
  (`coworld-local-run` is a debugging tool for a broken artifact, not a gate).

## Player build paths

Because the game ships working reference bots (King Nimrod, King Richard) with a full Nim
behavior stack — perception → navmesh pathfinding → per-class combat rotations →
quest/loot/vendor/train → death recovery → grouping — there are several paths, cheapest
first. **Which one to pursue is a human-direction decision (loop step 3), not a default** —
surface the fork, don't pre-commit.

1. **Tune the bundled policy** — new/better leveling profiles (the authored zone JSONs) or
   sharper class rotations (`player/bots/rotations.nim`) on top of the existing engine.
   Cheapest; tests whether the shipped bots are tuning-limited.
2. **Fork King Nimrod / the shared bot policy** — change the decision layer (farm/follow
   strategy, party coordination for the 5-slot RFC clear) while reusing the perception/
   navigation/action plumbing. Medium lift; where the RFC clear problem likely lives.
3. **The identity-blind general-grinding lane** — build on the experimental `--policy
   general-grinding` (opt-in, default-off) that selects from client-observed affordances
   instead of authored content. Bet on *transfer*; more speculative.
4. **A new player from the protocol up** — only if 1–3 hit a ceiling; this is "write more of a
   WoW client," the heaviest option.

Because the player is **Nim**, every path needs a Nim build path, and any fork of the bundled
engine needs a **pinned game commit** (the `versions.env` pattern from `crewrift_lab/tools/`).
When a path is chosen, vendor the policy under this lab (e.g. `vanilla_wow_lab/<policy>/`),
mirroring `crewrift_lab/crewrift/` / `heartleaf_lab/cady/`, and record a design doc under
[`docs/designs/`](docs/designs/).

## Vanilla WoW lab docs

- **[`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md)** — the self-contained,
  WoW-naive-friendly game reference: the two game shapes (persistent realm + isolated scored
  episodes), the `rfc-five-player-clear` benchmark, the scoring math, and the strategically-
  relevant mechanics (classes, combat, leveling, navigation, the 15 manifest variants).
  **Start here** to build a mental model.
- **[`docs/vanilla-wow-player-contract.md`](docs/vanilla-wow-player-contract.md)** — what any
  player must do over the wire: the `/player` handshake + `wow_session` message, the two
  network planes + `wsproxy` WS→TCP bridge, what a policy observes (TelemetrySnapshot +
  Tensor-Frame-v3), what it emits (the BotAction vocabulary + 64-byte record), the "sent is
  not accepted" integrity rules, and the two-stage submittable image.
- **[`docs/vanilla-wow-protocol.md`](docs/vanilla-wow-protocol.md)** — the **exhaustive
  interface-protocol reference**: every `vanilla_wow.*` message and schema (session/done,
  bot_action + per-kind args + the 64-byte binary record, movement_settlement,
  navmesh_traversal, control_adapter_report), the full `TelemetrySnapshot` field list, the
  Tensor-Frame-v3 + `CWBT` binary layout, the transport/ports contract + the WS↔TCP bridge, and
  the `CWREPLAY` v4 format — verbatim field names + `file:line` citations. Consult this for the
  exact field/byte/opcode; the player-contract doc is the narrative version.
- **[`docs/vanilla-wow-rfc-roles.md`](docs/vanilla-wow-rfc-roles.md)** — the five RFC support
  roles (commissioner/grader/diagnoser/optimizer/reporter): images, env-var contracts,
  outputs, auto-vs-on-demand, and the exact commissioner round-scoring math.
- **[`docs/vanilla-wow-strategy-guide.md`](docs/vanilla-wow-strategy-guide.md)** — **how to
  *play* WoW well**: a beginner's guide (WoW in five minutes), leveling & solo-survival
  fundamentals (XP math, rested XP, pulling, death cost), group play (the holy trinity,
  threat/aggro, coordination failure modes), the seven playable classes, and an RFC-specific
  clear plan — blending cited real-Vanilla-WoW knowledge with engine-grounded facts. Read this
  to reason about *strategy*, once the gameplay/contract docs give you the mechanics.

More docs (a replay-reading guide, a player design doc) get added as the loop generates the
need — mirroring the other labs' `docs/`.

## Skills

**No Vanilla-WoW-specific skills exist yet** beyond the lessons-lifecycle skill
(`/lessons-review`, in `vanilla_wow_lab/.claude/skills/`). The loop's **game-agnostic** halves
(experience requests, artifact download, local run, build-and-upload, policy lifecycle) live at
the **lab root** (`../.claude/skills/`, indexed in [`../AGENTS.md`](../AGENTS.md)) — use those
to *create*, *pull*, and *ship* episodes once the game is live.

Game-specific tooling belongs **here** (`vanilla_wow_lab/.claude/skills/`), not at the root.
The gaps worth filling first (once real episodes exist):

- A **Vanilla-WoW survey/report** skill — turn a batch of RFC episodes into a dense report on
  clear rate, per-boss progress, clear time, wipe locations, and XP accrual (built on the
  reporter's `recap`/`events`/`stats` + the diagnoser's `missing_bosses`), analogous to
  `crewrift-survey`.
- A **replay-reading** helper for the `CWREPLAY` v4 format (the game repo ships expander
  tooling; a lab-side wrapper over it, like `crewrift_lab`'s `expand_replay`, is the natural
  form).

## Vanilla WoW best practices

[`best_practices.md`](best_practices.md) holds Vanilla-WoW-specific practices layered on top of
the root [`../best_practices.md`](../best_practices.md) — things true of *this game's* tooling
and failure modes. It starts near-empty and fills in via the lessons pipeline below. **Read
both**; root first.

## Vanilla WoW user preferences

There is no Vanilla-WoW-specific `user_preferences.md` yet; the root
[`../user_preferences.md`](../user_preferences.md) applies. When the human states a
Vanilla-WoW-specific durable preference, create `user_preferences.md` here and record it
(mirroring the other labs' layering).

## Testing discipline (Vanilla-WoW-specific)

**Do minimal, tightly-focused testing.** Write a test only when it covers something genuinely
*critical* — a load-bearing invariant, a rule the game enforces strictly, or a regression that
would silently lose a clear or crash an episode — and be **sparing** even with those. The
hosted eval is the test; speed wins (root AGENTS.md). No coverage-for-its-own-sake. When
unsure whether a test earns its place, prefer not writing it — or ask. (Note the Nim toolchain
here means "a quick unit test" is more expensive than in the Python labs — bias even harder
toward the hosted eval as the test.)

## Working context & tentative lessons

Two session-spanning files carry state and learning forward between sessions — **read both on
startup** alongside the preferences above:

- **[`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)** — the **live, minimal, high-signal state of
  what we're working on right now**: the current objective plus the few facts worth carrying
  forward (active policy/version, live findings, open threads, the readiness gap). Read it to
  resume, **keep it updated as you learn**, and **clear/reseed it when we pivot**.
- **[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md)** — **this session's** eager, noisy buffer of
  candidate lessons: write here freely, AS YOU GO, the moment something *looks* like a reusable
  lesson. Most entries are noise; the value is the occasional gem. **The lifecycle is
  automated**: a SessionStart hook archives each session's buffer to
  [`lessons_archive/`](lessons_archive/) and creates a fresh one
  (`tools/rotate_lessons.sh`); a Stop hook nudges once if substantive work ends with the buffer
  untouched (`tools/lessons_stop_nudge.sh`); the **`/lessons-review`** skill (≈weekly,
  human-driven) clusters lessons that RECUR across archived sessions and graduates keepers to
  `best_practices.md`. Recurrence across sessions — not in-session hit counts — is the
  graduation signal. (Both hooks are registered in the **root** `.claude/settings.json`,
  alongside the other three labs'.)

**Cleanup step — run when you wrap up a thread (and before you push/land work).**

1. **Capture all tentative lessons** into [`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md) —
   eagerly; an un-recorded lesson is a lost one.
2. **Reconcile working context** — prune completed/stale detail from
   [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md), update the active policy/version, and
   clear/reseed it on a pivot.

## Deferred tasks

Vanilla-WoW-specific parked work lives in the **shared** [`../TODO.md`](../TODO.md) alongside
the rest of the lab's deferred tasks. Check it at the start of focused work.

## Player policies

_(None yet — the lab was just created. A policy directory `vanilla_wow_lab/<policy>/` gets
added when the first policy is built, mirroring `crewrift_lab/crewrift/`, `heartleaf_lab/cady/`,
and `cue_n_woo_lab/mentalist/`.)_
