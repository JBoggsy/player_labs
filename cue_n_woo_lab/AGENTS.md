# cue_n_woo_lab — agent guide

The **Cue-n-Woo** corner of player_labs: where we build, evaluate, and improve
**player policies** for the Cue-n-Woo game. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the
improvement loop, your role in it (speed first), the submission gate, and the
game-agnostic skills.
This file is the **Cue-n-Woo-specific layer** on top of it: the game, the docs, the
practices/preferences, and the policies we optimize. When the two disagree, the root
defines *process*; this file defines *Cue-n-Woo*.

## What Cue-n-Woo is

Cue-n-Woo is a Coworld **two-player, text-only, theory-of-mind game** (**not** a
gridworld, despite shipping in the same `cogames` image family as among_them /
cogs_vs_clips). Two players each privately interview a hidden-persona **judge**
(Gemma-2-9B-IT steered via FLAS toward one of **61 publicly-known writing styles**),
then each writes 3 challenge questions with their own answers and blind-answers the
opponent's 3 questions. The steered judge scores each question as a 2-way preference
between the two answers. **You win by modeling the judge's hidden style better than
your opponent** — answering the way the style favors and authoring questions where
your informed answer beats their blind one. Players speak **JSON text over a
WebSocket**; there is no map, no perception, no movement.

For the full game — rules, protocol, scoring math, and strategy — read
[`docs/cue-n-woo-gameplay.md`](docs/cue-n-woo-gameplay.md) (the lab's self-contained
game reference; you rarely need to leave the repo). The game source in the
`Metta-AI/cue-n-woo` repo (referee `v2/coworld/game.py`, baseline player
`v2/coworld/players/baseline.py`, protocol docs `v2/coworld/docs/`) remains the
ultimate authority. The policy we build and optimize is in the
[Player policies](#player-policies) index below.

## The loop, in Cue-n-Woo terms

The root loop (evaluate → report → direction → implement → rebuild+reupload →
repeat → human gate → submit) runs **unchanged** here. The Cue-n-Woo-specific instruments:

- **Evaluate** (step 1) — experience requests against the uploaded version of the
  policy under optimization. The game is symmetric (no role split like Crewrift's
  crew/imposter), so the main cuts are **opponent/matchup** and the **hidden style**
  (the 61-style pool — watch whether one style cluster is systematically lost). The
  **judge worker is publicly callable unsigned** (`cue-n-woo-worker.softmax-research.net`),
  so a true head-to-head self-eval is also possible *locally* without the league
  (see the rebuild/upload bullet below).
- **Report** (step 2) — pull artifacts with the game-agnostic
  `coworld-episode-artifacts` skill, then distill. **There is no Cue-n-Woo-specific
  report skill yet** — see [Skills](#skills); building one (and an artifact-logs
  fetcher) is the highest-leverage tooling investment for this lab.
- **Implement** (step 4) — change the policy under optimization (see
  [Player policies](#player-policies)); keep tunable knobs in `mentalist/config.py`,
  separate from logic, so each iteration is attributable.
- **Rebuild / upload / submit** (steps 5–8) — build the policy's image with
  its own [`mentalist/Dockerfile`](mentalist/Dockerfile) (`docker build
  --platform linux/amd64`; `--run python --run=-m --run mentalist --use-bedrock` is
  **mandatory** on upload AND local runs — see [`mentalist/README.md`](mentalist/README.md)),
  then the game-agnostic skills + [`../player-build.md`](../player-build.md) for the
  upload/submit flow. **Hosted-vs-local gotcha that has already bitten:** the league
  runs `require_signing=true` (exercising a game-side signing-key path that local
  `require_signing=false` runs never touch), so a local run can pass while every league
  episode crashes game-side — one more reason the hosted eval, not a local run, is the
  test — see
  [`docs/league-infra-incident-2026-06-12.md`](docs/league-infra-incident-2026-06-12.md).

## Cue-n-Woo lab docs

- **[`docs/cue-n-woo-gameplay.md`](docs/cue-n-woo-gameplay.md)** — the self-contained
  game reference: rules, roles, phase flow, the wire protocol, the scoring math, the
  full 61-style pool, and a strategy treatment. **Start here** to build a mental model
  before reasoning about play or setting direction.
- **[`docs/probe-findings.md`](docs/probe-findings.md)** — what the live worker-probe
  spike established (the evidence the player design rests on): topicality dominates and
  style is a decisive *tilt*; a cheap no-LLM classifier hits ~96% top-1 with 3
  questions; a pure-style answer path is dead on arrival. The reproducible harness is
  [`probe/`](probe/).
- **[`docs/designs/player-design.md`](docs/designs/player-design.md)** — the player
  architecture + rationale + build order (classifier → Bedrock writer → validator),
  and the open questions. A living doc.
- **[`docs/league-infra-incident-2026-06-12.md`](docs/league-infra-incident-2026-06-12.md)**
  — the league-side IAM bug that disqualified every entrant, how we diagnosed it (game
  container logs via `GET /jobs/{job_id}/artifacts/logs`) and hotfixed it, and the
  **metta Terraform reconciliation still owed**.

The vendored policy also carries its own internal docs — see
[`mentalist/README.md`](mentalist/README.md).

## Skills

**No Cue-n-Woo-specific skills exist yet.** The loop's **game-agnostic** halves
(experience requests, artifact download, local run, policy lifecycle) live at the
**lab root** (`../.claude/skills/`, indexed in [`../AGENTS.md`](../AGENTS.md)) — use
those to *create* and *pull* episodes.

Game-specific tooling belongs **here** (`cue_n_woo_lab/.claude/skills/`), not at the
root. The lessons-lifecycle skill (`lessons-review`, below) already lives here. The
gaps worth filling, in rough priority order (the incident doc flags the first):

- An **artifact-logs fetcher** — `GET /jobs/{job_id}/artifacts/logs` serves the game +
  worker container logs, which the `coworld-episode-artifacts` skill does **not** pull;
  that route is how the IAM incident was diagnosed ("did not qualify" can mean *the
  game crashed*, not *your policy is bad*).
- A **Cue-n-Woo report** skill — turn a batch of episodes into a dense report on the
  player's strengths/weaknesses (per-question scoring, style-cluster losses,
  decline/conflict pathologies).

## Cue-n-Woo best practices

[`best_practices.md`](best_practices.md) holds Cue-n-Woo-specific practices layered on
top of the root [`../best_practices.md`](../best_practices.md) — things that are true
of *this game's* tooling and failure modes. It starts near-empty and fills in via the
lessons pipeline below. **Read both**; root first.

## Cue-n-Woo user preferences

There is no Cue-n-Woo-specific `user_preferences.md` yet; the root
[`../user_preferences.md`](../user_preferences.md) applies. When the human states a
Cue-n-Woo-specific durable preference, create `user_preferences.md` here and record it
(mirroring crewrift's layering).

## Testing discipline (Cue-n-Woo-specific)

**Do minimal, tightly-focused testing.** Write a test only when it covers something
genuinely *critical* — a load-bearing invariant, a rule the game enforces strictly, or
a regression that would silently lose points or crash an episode — and be **sparing**
even with those. Do **not** write tests that aren't critical: no coverage-for-its-own-
sake, no testing trivial glue, no re-asserting what the type system or a one-line
function already guarantees. A small suite of high-value tests that someone will
actually maintain beats a large one that rots. (This deliberately diverges from
crewrift's broad-coverage style; this game's surface is smaller and the cost/benefit
favors restraint.) When unsure whether a test earns its place, prefer not writing it —
or ask.

## Working context & tentative lessons

Two session-spanning files carry state and learning forward between sessions — **read
both on startup** alongside the preferences above:

- **[`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)** — the **live, minimal, high-signal
  state of what we're working on right now**: the current objective plus the few facts
  worth carrying forward (active policy/version, the working lens, live findings, open
  threads). Read it to resume, **keep it updated as you learn**, and **clear/reseed it
  when we pivot to a whole new direction**.
- **[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md)** — **this session's** eager,
  noisy buffer of candidate lessons: write here freely, AS YOU GO, the moment
  something *looks* like a reusable lesson. Most entries are noise; the value is the
  occasional gem. **The lifecycle is automated**: a SessionStart hook archives each
  session's buffer to [`lessons_archive/`](lessons_archive/) and creates a fresh one
  (`tools/rotate_lessons.sh`); a Stop hook nudges once if substantive work ends with
  the buffer untouched (`tools/lessons_stop_nudge.sh`); the **`/lessons-review`** skill
  (≈weekly, human-driven) clusters lessons that RECUR across archived sessions and
  graduates keepers to `best_practices.md`. Recurrence across sessions — not in-session
  hit counts — is the graduation signal. (Both hooks are registered in the **root**
  `.claude/settings.json`, alongside crewrift's.)

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

Cue-n-Woo-specific parked work lives in the **shared** [`../TODO.md`](../TODO.md)
alongside the rest of the lab's deferred tasks (there's no separate Cue-n-Woo TODO).
Check it at the start of focused work.

## Player policies

- **mentalist** *(Python)* — at [`mentalist/`](mentalist/), our Cue-n-Woo player and
  **the primary policy under optimization**. A **cheap local style classifier →
  Bedrock Claude writer**: 3 fixed private questions → TF-IDF nearest-neighbor over a
  shipped 61-style reference library (`data/library.json`) → Claude
  (`us.anthropic.claude-opus-4-8`) writes short, on-topic, in-style proposals and blind
  answers, with deterministic legal fallbacks on any failure. Its internals and
  build/test/ship commands are in [`mentalist/README.md`](mentalist/README.md); the
  design rationale is [`docs/designs/player-design.md`](docs/designs/player-design.md).
  Builds from its own `Dockerfile` (no shared `build_player.sh` — this lab has a single
  Python policy). Version history → change mapping: [`mentalist/VERSION_LOG.md`](mentalist/VERSION_LOG.md).
