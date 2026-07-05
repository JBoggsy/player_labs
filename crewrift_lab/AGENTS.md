# crewrift_lab — agent guide

The **Crewrift** corner of player_labs: where we build, evaluate, and improve
**player policies** for the Crewrift game. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the
improvement loop, your role in it (speed first), the submission gate, and the
game-agnostic skills.
This file is the **Crewrift-specific layer** on top of it: the game, the docs, the
practices/preferences, and the policies we optimize. When the two disagree, the root
defines *process*; this file defines *Crewrift*.

## What Crewrift is

Crewrift is a Coworld **social-deduction game** (an *Among Us*–style benchmark):
8–16 players on a 2-D map. Most are **crewmates** completing tasks; a few are
**imposters** who kill crewmates and blend in. Bodies get reported, meetings are
called, players chat and **vote** someone out. Crew win by finishing all tasks or
voting out every imposter; imposters win by killing enough crew. Player policies
speak the binary **Sprite-v1** protocol over a websocket — they receive the rendered
scene and act with a d-pad + A/B, with **no semantic action API**.

For the full game — rules, roles, win conditions, scoring, flow, and strategy from a
**gameplay** perspective — read [`docs/crewrift-gameplay.md`](docs/crewrift-gameplay.md)
(the lab's self-contained game reference; you rarely need to leave the repo). The game
source in the `Metta-AI/coworld-crewrift` repo remains the ultimate authority on rules
and the scene vocabulary. The policies we build and optimize are listed in the
[Player policies](#player-policies) index below.

## The loop, in Crewrift terms

The root loop (evaluate → report → direction → implement → rebuild+reupload →
repeat → human gate → submit) runs **unchanged** here. The Crewrift-specific instruments:

- **Evaluate** (step 1) — experience requests against the uploaded version of the
  policy under optimization. **Decompose by role** (crewmate vs. imposter are
  effectively two different policies; see best practices) and by opponent. To pin your
  policy's role, pin its roster `slot` and set `game_config_overrides.slots` — shape in
  [`docs/crewrift-gameplay.md` → Forcing roles in evaluations](docs/crewrift-gameplay.md).
- **Report** (step 2) — pull artifacts, then turn the batch into a dense report with
  the **`crewrift-survey`** skill (flags the interesting episodes by role, profiles
  them). It builds on the Crewrift readers in
  [`docs/crewrift-replays.md`](docs/crewrift-replays.md): the objective
  `expand_replay` event timeline (version-matched via
  [`tools/build_expand_replay.sh`](tools/build_expand_replay.sh)) **and** the policy's
  own subjective per-tick logs, aligned by tick.
- **Implement** (step 4) — change the policy under optimization (see the
  [Player policies](#player-policies) index; each vendored policy carries its own
  internal docs).
- **Rebuild / upload / submit** (steps 5–8) — build the policy's image
  in-lab with [`tools/build_player.sh <policy>`](tools/build_player.sh) (Docker-only;
  design in [`docs/designs/building_players.md`](docs/designs/building_players.md)), then
  the game-agnostic skills + [`../player-build.md`](../player-build.md) for the
  upload/submit flow. The Crewrift I/O contract any built image must satisfy is
  [`docs/crewrift-protocol.md`](docs/crewrift-protocol.md).

## Crewrift lab docs

- **[`docs/crewrift-gameplay.md`](docs/crewrift-gameplay.md)** — the game itself, from
  a **gameplay** (not implementation) perspective: rules, roles, win/loss, flow,
  mechanics, scoring, and a full strategy treatment. The self-contained game reference
  — start here to build a mental model before reasoning about play or setting direction.
- **[`docs/crewrift-protocol.md`](docs/crewrift-protocol.md)** — what **any** Crewrift
  player policy must do: the Sprite-v1 I/O contract (decode the scene, decide, emit
  buttons/chat), the scene vocabulary, phases, scoring. For building a new policy or
  understanding the contract every policy implements.
- **[`docs/crewrift-replays.md`](docs/crewrift-replays.md)** — reading a *finished*
  Crewrift game: the visual replay, `expand_replay`'s objective event timeline, a
  policy's subjective trace logs, and the `.bitreplay` format. The "Report" step's
  signal-extraction reference.
- **[`docs/designs/building_players.md`](docs/designs/building_players.md)** — how we build
  player images in-lab (Plan A: Docker-only, central game-ref pin). A general-case
  section (for building *any* Crewrift player, vendored or not) followed by the
  per-policy specifics. The build code is `tools/build_player.sh` +
  `tools/versions.env`.

Vendored policies also carry their own internal docs (design/architecture) under
their directory — see the [Player policies](#player-policies) index.

## Skills

Crewrift-specific skills live here in `.claude/skills/`:

- **`crewrift-survey`** — turn a **set** of episodes (an experience request, a policy's
  recent league games, a tournament batch) into a fast, role-decomposed **HTML survey**: a
  per-policy stats table, a policy×policy win heat map, and a short list of the interesting
  episodes (with replay links). Reads `results.json` + `episode.json` only — instant over
  hundreds of episodes. The loop's **Report** step. (Replaces the old `crewrift-report`; the
  *deep* per-episode dissection is the event-warehouse below.)
- **`crewrift-event-warehouse`** — build + query a policy-indexed **DuckDB/Parquet event
  store** from expanded replays, for cross-episode behavioural analysis ("all the data":
  proximity, isolation, follow/chase, kills, votes, chats, per-room time). The deep dig
  behind the survey, and the default cheap experiment. For a **fresh experience request**,
  its `scripts/stream_eval.py` is the default path: it fetches artifacts and builds the
  warehouse **while the episodes are still running** (incremental builds; crash-safe
  rerun), so the warehouse is ready as the request drains. `references/event-catalog.md`
  + `references/recipes.md`.
- **`crewrift-ab`** — **A/B test two policy versions head-to-head**: run both in **matched,
  fresh** experience requests (same roster/roles/count/window — so the delta is attributable,
  not confounded by league drift), then compare hard metrics (`scripts/compare.py` — role-split
  deltas with significance + a regression scan, rendered to an HTML report) **and** investigate
  the two sides' logs/replays. Use whenever you need to know whether one version genuinely beats
  another. (Distinct from `crewrift-survey`, which surveys *one* batch descriptively.)
- **`crewrift-diagnose`** — turn a survey's signals into **evidence-grounded, mechanistic
  improvement hypotheses**: investigate replays/logs/code for *why* a behavior happens (or fails
  to), then **present candidate directions to the human** as options (not directives). An
  optional augmentation of the **direction** step. Pairs with `crewrift-survey` (signals in),
  `crewrift-event-warehouse` (test cheaply), and `crewrift-experiment` (run one).
- **`crewrift-experiment`** — design + run **one** falsifiable experiment for a single
  hypothesis (design ↔ adversarial-critique ↔ run); renders an HTML design report and **gates on
  the human before running**. Usable standalone ("it might be X — let's test it").
- **`lessons-review`** — cluster lessons that RECUR across archived sessions and graduate keepers
  to `best_practices.md` (the ≈weekly, human-driven graduation pass).

The loop's **game-agnostic** halves (experience requests, artifact download, local run,
**build & upload**, policy lifecycle) live at the **lab root** (`../.claude/skills/`, indexed in
[`../AGENTS.md`](../AGENTS.md)) — use those to build/upload a version and create/pull the episodes,
then `crewrift-survey` to analyze them. New Crewrift-specific tooling belongs here, not at the root.

## Crewrift best practices

[`best_practices.md`](best_practices.md) holds Crewrift-specific practices layered on
top of the root [`../best_practices.md`](../best_practices.md) — things that are true
of *this game's* tooling and failure modes (replay version-skew, role decomposition,
trace-level verification). **Read both**; root first.

## Crewrift user preferences

[`user_preferences.md`](user_preferences.md) records the human's durable preferences
**specific to Crewrift work**, layered on the root
[`../user_preferences.md`](../user_preferences.md). **Read both on startup**, and when
the human states a Crewrift-specific preference, record it here.

## Working context & tentative lessons

Two session-spanning files carry state and learning forward between sessions — **read
both on startup** alongside the preferences above:

- **[`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)** — the **live, minimal, high-signal
  state of what we're working on right now**: the current objective plus the few facts
  worth carrying forward (active policy/version, the working lens, live findings, open
  threads). Read it to resume, **keep it updated as you learn**, and **clear/reseed it
  when we pivot to a whole new direction**. A recorded objective there is the
  resume-the-loop signal (it doubles as the onboarding "active policy" marker).
- **[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md)** — **this session's** eager,
  noisy buffer of candidate lessons: write here freely, AS YOU GO, the moment
  something *looks* like a reusable lesson. Most entries are noise; the value is the
  occasional gem. **The lifecycle is automated** (2026-06-12): a SessionStart hook
  archives each session's buffer to [`lessons_archive/`](lessons_archive/) and creates
  a fresh one; a Stop hook nudges once if substantive work ends with the buffer
  untouched; the **`/lessons-review`** skill (≈weekly, human-driven) clusters lessons
  that RECUR across archived sessions and graduates keepers to `best_practices.md`.
  Recurrence across sessions — not in-session hit counts — is the graduation signal.

**Cleanup step — run when you wrap up a thread (and before you push/land work).** Do a
deliberate sweep so nothing learned evaporates:

1. **Capture all tentative lessons.** Re-scan the work you just did for anything that
   *looked* like a reusable lesson — a gotcha, a surprise, a "next time I'd…" — and make
   sure each is written into [`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md). Capturing
   eagerly is the whole point; an un-recorded lesson is a lost one. (The buffer is
   archived automatically at the next session start; graduation happens at
   `/lessons-review`, keyed on cross-session recurrence.)
2. **Reconcile working context.** Prune completed/stale detail from
   [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md) (it's a one-screen state file, not a log —
   finished work lives in git history / the version log), update the active
   policy/version, and **clear/reseed it on a pivot** to a new direction.

## Deferred tasks

Crewrift-specific parked work lives in the **shared** [`../TODO.md`](../TODO.md)
alongside the rest of the lab's deferred tasks (there's no separate Crewrift TODO).
Check it at the start of focused work.

## Player policies

The Crewrift player policies we've vendored, each a drift-able in-lab copy, and each
**buildable in-lab** with `tools/build_player.sh <policy>` (see
[`docs/designs/building_players.md`](docs/designs/building_players.md)). They come in two
flavors: **crewborg is Python** (editable-installed for dev; image installs the SDK +
fork); **notsus and suspectra are Nim** (their image clones the crewrift game at the
pinned `CREWRIFT_REF` and compiles). All repos are public, so **every build is
Docker-only with no credentials**.

- **crewborg** *(Python)* — at [`crewrift/crewborg/`](crewrift/crewborg/) (package
  `crewrift.crewborg`), a drifting fork of upstream `Metta-AI/players`
  (`players/crewrift/crewborg`). A full Python player: `perception/`
  (Sprite-v1 → scene decoder), `strategy/`, `modes/`, `action.py`, `coworld/`
  (the bridge). Imports the shared `players.player_sdk` from the **pinned public
  `players` repo** (`pyproject.toml`; no local checkout). Its own
  [`AGENTS.md`](crewrift/crewborg/AGENTS.md) and
  [`design.md`](crewrift/crewborg/design.md) map its internals. **Currently the
  primary policy under optimization.**
- **notsus** *(Nim)* — at [`crewrift/notsus/`](crewrift/notsus/), the **reference
  baseline** (upstream lives in the game repo,
  `Metta-AI/coworld-crewrift`: `players/notsus/`; public image
  `…/players/notsus:latest`). The minimal Sprite-v1 implementation
  (`notsus.nim` + `notsus/{votereader,protocols}.nim`), with its Dockerfile and
  `coplayer_manifest.json`. Useful as a comparison opponent and a from-scratch
  starting point. (The prebuilt `notsus.out` binary is **not** vendored.)
- **suspectra** *(Nim + Python LLM hook)* — at
  [`crewrift/suspectra/`](crewrift/suspectra/), a fork of notsus
  (`suspectra.nim`) that adds evidence voting and a bounded Bedrock/Anthropic
  **meeting LLM** (`llm_meeting.py`, invoked by path; prompts in `memory/`).
  Upstream: `Metta-AI/players` (`players/crewrift/suspectra`). Builds in-lab via
  `tools/build_player.sh suspectra` (same Nim path as notsus).
</content>
