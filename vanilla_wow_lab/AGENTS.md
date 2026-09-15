# vanilla_wow_lab — agent guide

The **Vanilla WoW** corner of player_labs: where we build, evaluate, and improve **player
policies** for the Vanilla WoW game. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the improvement loop,
your role in it (speed first), the submission gate, and the game-agnostic skills. This file is
the **Vanilla-WoW-specific layer** on top of it: the game, the docs, the practices, and the
policies we optimize. When the two disagree, the root defines *process*; this file defines
*Vanilla WoW*.

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

**The one architectural fact that shapes everything here:** a Vanilla WoW policy is now a
synchronous Gymnasium agent. It must obey a strict client-honesty contract — **read the
current `Observation` → submit one typed `Action` → consume the next authoritative
frame → repeat; submission is not success**. The game-owned environment is the sole owner
of the packet-level client and validates all actions. Policies must not add a second client,
projection layer, admission mask, or settlement adapter.

## The loop, in Vanilla-WoW terms

The root loop (evaluate → report → direction → implement → rebuild+reupload → repeat → human
gate → submit) runs **unchanged** here. Direct Coworld experience requests are the normal
evaluation path; league submission remains human-gated. The Vanilla-WoW-specific instruments are:

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
- **Rebuild / upload / submit** (steps 5–8) — build the wowborg Python image with
  `tools/build_player.sh`, then use the game-agnostic skills +
  [`../player-build.md`](../player-build.md) for upload/submit.
  The hosted eval is the test; **do not** buy pre-upload confidence with local runs
  (`coworld-local-run` is a debugging tool for a broken artifact, not a gate).

## Player build paths

**Chosen path: our Python bot uses the owner-provided semantic `/player` contract
directly.** `wowborg/environment.py` is only a bot convenience around
`VanillaWowEnv`; it does not adapt a client protocol. The image copies `environment/`
and `player/sdk/` from the exact **deployed target Coworld** image pinned in
[`tools/versions.env`](tools/versions.env), while the game runs the client.
Each uploaded wowborg version bakes one competition objective selected by the
`--strategy` build flag; shared navigation and recovery stay below that boundary.

## Vanilla WoW lab docs

- **[`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md)** — the self-contained,
  WoW-naive-friendly game reference: the two game shapes (persistent realm + isolated scored
  episodes), the `rfc-five-player-clear` benchmark, the scoring math, and the strategically-
  relevant mechanics (classes, combat, leveling, navigation, the 15 manifest variants).
  **Start here** to build a mental model.
- **[Wowborg](wowborg/README.md)** — the current policy contract,
  semantic-player lifecycle, layout, knobs, validation, and build commands.
- **[`docs/vanilla-wow-player-contract.md`](docs/vanilla-wow-player-contract.md)** — the game-owned environment and policy integration.
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

Game-specific analysis is implemented in [tools](tools/), even where it has no separate skill wrapper:

- [wow_survey.py](tools/wow_survey.py): batch HTML plus machine-readable metrics from episode artifacts and CWREPLAY packets.
- [cwreplay.py](tools/cwreplay.py): replay decoding.
- [movement_report.py](tools/movement_report.py), [nav_report.py](tools/nav_report.py): movement/navigation evidence.
- [wow_batch_profiler.py](tools/wow_batch_profiler.py): batch profiling.

Use each tool's `--help` and match its replay contract to the episode. Packet movement/login metrics are not proof of competitive objective completion. Root skills handle request creation, downloads, upload and separately gated submission; the [capability map](../docs/capabilities.md) connects them.

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

## Working context and guidance

Keep the active objective, scope, unresolved constraints and next decision in
[WORKING_CONTEXT.md](WORKING_CONTEXT.md). Keep testable unresolved ideas in
[TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md); promote supported rules to
best_practices.md and remove resolved claims. Follow the
[shared learning workflow](../docs/learning.md). Update these documents in place;
do not create session archives, version logs or change narratives.

## Deferred tasks

Vanilla-WoW-specific parked work lives in the **shared** [`../TODO.md`](../TODO.md) alongside
the rest of the lab's deferred tasks. Check it at the start of focused work.

## Player policies

- **[`wowborg/`](wowborg/)** — the active Python semantic player. Its README documents the
  uploaded immutable version to its source and evidence.
