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
(Gemma-2-9B-IT steered via FLAS toward a **combination of independent concept axes**),
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
  (the resolved concept configuration). The
  **judge worker is publicly callable unsigned** (`cue-n-woo-fleet.softmax-research.net`),
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
  **mandatory** on upload AND local runs),
  then the game-agnostic skills + [`../player-build.md`](../player-build.md) for the
  upload/submit flow. **Hosted-vs-local gotcha that has already bitten:** the league
  runs `require_signing=true` (exercising a game-side signing-key path that local
  `require_signing=false` runs never touch), so a local run can pass while every league
  episode crashes game-side; verify the selected hosted configuration.

## Cue-n-Woo lab docs

- [Gameplay](docs/cue-n-woo-gameplay.md): phase, observation and scoring contract.
- [Axis-combination concepts](docs/axis-combo-system.md): hidden-concept configuration.
- [Mentalist implementation](mentalist_v4/README.md): policy components and build.


## Skills

**No Cue-n-Woo-specific skills exist yet.** The loop's **game-agnostic** halves
(experience requests, artifact download, local run, policy lifecycle) live at the
**lab root** (`../.claude/skills/`, indexed in [`../AGENTS.md`](../AGENTS.md)) — use
those to *create* and *pull* episodes.

Game-specific tooling belongs **here** (`cue_n_woo_lab/.claude/skills/`), not at the
root. The lessons-lifecycle skill (`lessons-review`, below) already lives here. The
gaps worth filling, in rough priority order (the incident doc flags the first):

- Use the **shared artifact fetcher** for current game logs and owned seat diagnostics.
  It now reads `/v2/episode-requests/{id}/artifacts/logs`; a separate legacy job-log
  fetcher is unnecessary. Worker-specific diagnostics are not guaranteed in that
  artifact. Use the current API and participant access.
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

## Working context and guidance

Keep the active objective, scope, unresolved constraints and next decision in
[WORKING_CONTEXT.md](WORKING_CONTEXT.md). Keep testable unresolved ideas in
[TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md); promote supported rules to
best_practices.md and remove resolved claims. Follow the
[shared learning workflow](../docs/learning.md). Update these documents in place;
do not create session archives, version logs or change narratives.

## Deferred tasks

Cue-n-Woo-specific parked work lives in the **shared** [`../TODO.md`](../TODO.md)
alongside the rest of the lab's deferred tasks (there's no separate Cue-n-Woo TODO).
Check it at the start of focused work.

## Player policies
