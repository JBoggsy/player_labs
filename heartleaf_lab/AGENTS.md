# heartleaf_lab — agent guide

The **Heartleaf** corner of player_labs: where we build, evaluate, and improve
**player policies** for the Heartleaf game. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the
improvement loop, your role in it (speed first), the submission gate, and the
game-agnostic skills. This file is the **Heartleaf-specific layer** on top of it:
the game, the docs, the practices/preferences, and the policies we optimize. When
the two disagree, the root defines *process*; this file defines *Heartleaf*.

> **Lab status (2026-07-06): just created — scaffolding only, no player yet.** The
> game repo (`Metta-AI/coworld-heartleaf`) is cloned for reference; a live Observatory
> league exists. **No player policy has been built or uploaded.** The immediate next
> step is human-directed: pick a build path (below) and start the loop. Live state:
> [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).

## What Heartleaf is

Heartleaf is a Coworld **9-gnome garden-dinner gridworld** on the **BitWorld Sprite-v1**
protocol (same protocol family as Crewrift). Each gnome gathers food from shared gardens
during a day, then **scores only by *hosting* a dinner** at its own house that other
gnomes attend: **`score = hosted food items × number of guests`**. Visitors eat for free
but score nothing. The meta-game is **social coordination over chat** — recruiting a full
table to your house by 6pm — layered on **efficient gathering**, across ~9 days.

For the full game — rules, day cycle, dinner/scoring math, the wire protocol, the bundled
behavior framework, and strategy — read [`docs/heartleaf-gameplay.md`](docs/heartleaf-gameplay.md)
(the lab's self-contained reference; you rarely need to leave the repo). The game source in
the `Metta-AI/coworld-heartleaf` repo (server `src/heartleaf.nim`, protocol `src/heartleaf/`,
bundled players `players/`) remains the ultimate authority.

**The one architectural fact that shapes everything here:** Heartleaf ships a substantial
Nim behavior framework (`players/talking_villager/`, ~3000 lines) that already does
perception → pathfinding → an 8-verb semantic action layer → LLM decision → chat. The four
league players are that *same engine* driven by different `soul.md` personality prompts.
So "build a player" has cheaper options here than in Crewrift — see
[Player build paths](#player-build-paths) below.

## The loop, in Heartleaf terms

The root loop (evaluate → report → direction → implement → rebuild+reupload → repeat →
human gate → submit) runs **unchanged** here. The Heartleaf-specific instruments:

- **Evaluate** (step 1) — experience requests against the uploaded version of the policy
  under optimization. The game is **9-player and symmetric** (no role split like Crewrift's
  crew/imposter), so the main cuts are **opponent/matchup** and **per-day trajectory** (the
  `results_schema` emits cumulative scores in score-order per day — watch how the gap opens
  across the ~9 days, and whether the policy fails to *host* vs. hosts but attracts no
  guests).
- **Report** (step 2) — pull artifacts with the game-agnostic `coworld-episode-artifacts`
  skill, then distill. **There is no Heartleaf-specific report skill yet** — see
  [Skills](#skills); building one (a per-day host/guest/score survey) is the
  highest-leverage tooling investment for this lab once episodes exist.
- **Implement** (step 4) — change the policy under optimization (see
  [Player build paths](#player-build-paths)); keep tunable knobs (food thresholds, hosting
  schedule, invitation policy) in a config layer separate from logic so each iteration is
  attributable.
- **Rebuild / upload / submit** (steps 5–8) — build the policy image, then the game-agnostic
  skills + [`../player-build.md`](../player-build.md) for the upload/submit flow. The
  hosted eval is the test; **do not** buy pre-upload confidence with local runs (the
  `coworld-local-run` skill is a debugging tool for a broken artifact, not a gate).

## Player build paths

Because the game ships a working `talking_villager` engine, there are three paths, cheapest
first. **Which one to pursue is a human-direction decision (loop step 3), not a default** —
surface the fork, don't pre-commit.

1. **New `soul.md` on `talking_villager`** — keep the framework, write a stronger
   strategy/personality prompt. Fastest to a competitive gnome; tests whether the shipped
   players are prompt-limited.
2. **Deterministic decision layer** — fork the framework, replace the LLM decision with
   rule-based host-vs-visit scheduling and guest-recruitment heuristics. Kills LLM
   cost/latency/variance; the scoring rule is simple enough that good heuristics may win.
3. **Raw Sprite-v1 (crewborg-style)** — build from the protocol up (Python players SDK).
   Most work; only if paths 1–2 hit a framework ceiling.

The rationale for each is in [`docs/heartleaf-gameplay.md`](docs/heartleaf-gameplay.md).
When a path is chosen, vendor the policy under this lab (e.g. `heartleaf_lab/<policy>/`),
mirroring how `crewrift_lab/crewrift/` and `cue_n_woo_lab/mentalist/` vendor theirs, and
record a design doc under `docs/designs/`.

## Heartleaf lab docs

- **[`docs/heartleaf-gameplay.md`](docs/heartleaf-gameplay.md)** — the self-contained game
  reference: rules, day cycle, dinner/scoring math, the Sprite-v1 wire protocol, the
  `talking_villager` framework, the bundled field, and a strategy treatment. **Start here**
  to build a mental model before reasoning about play or setting direction.

More docs (a protocol deep-dive, a player design doc, a replay-reading guide) get added as
the loop generates the need — mirroring `crewrift_lab/docs/`.

## Skills

**No Heartleaf-specific skills exist yet** beyond the lessons-lifecycle skill
(`/lessons-review`, in `heartleaf_lab/.claude/skills/`). The loop's **game-agnostic** halves
(experience requests, artifact download, local run, build-and-upload, policy lifecycle) live
at the **lab root** (`../.claude/skills/`, indexed in [`../AGENTS.md`](../AGENTS.md)) — use
those to *create*, *pull*, and *ship* episodes.

Game-specific tooling belongs **here** (`heartleaf_lab/.claude/skills/`), not at the root.
The gap worth filling first (once real episodes exist):

- A **Heartleaf survey/report** skill — turn a batch of episodes into a dense report on the
  policy's per-day host/guest/score behavior (did it host? how big a table? how did the
  cumulative gap evolve?), analogous to `crewrift-survey`.

## Heartleaf best practices

[`best_practices.md`](best_practices.md) holds Heartleaf-specific practices layered on top
of the root [`../best_practices.md`](../best_practices.md) — things true of *this game's*
tooling and failure modes. It starts near-empty and fills in via the lessons pipeline
below. **Read both**; root first.

## Heartleaf user preferences

There is no Heartleaf-specific `user_preferences.md` yet; the root
[`../user_preferences.md`](../user_preferences.md) applies. When the human states a
Heartleaf-specific durable preference, create `user_preferences.md` here and record it
(mirroring the other labs' layering).

## Testing discipline (Heartleaf-specific)

**Do minimal, tightly-focused testing.** Write a test only when it covers something
genuinely *critical* — a load-bearing invariant, a rule the game enforces strictly, or a
regression that would silently lose points or crash an episode — and be **sparing** even
with those. The hosted eval is the test; speed wins (root AGENTS.md). No coverage-for-its-
own-sake. When unsure whether a test earns its place, prefer not writing it — or ask.

## Working context & tentative lessons

Two session-spanning files carry state and learning forward between sessions — **read
both on startup** alongside the preferences above:

- **[`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)** — the **live, minimal, high-signal state
  of what we're working on right now**: the current objective plus the few facts worth
  carrying forward (active policy/version, the working lens, live findings, open threads).
  Read it to resume, **keep it updated as you learn**, and **clear/reseed it when we pivot**.
- **[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md)** — **this session's** eager, noisy buffer
  of candidate lessons: write here freely, AS YOU GO, the moment something *looks* like a
  reusable lesson. Most entries are noise; the value is the occasional gem. **The lifecycle
  is automated**: a SessionStart hook archives each session's buffer to
  [`lessons_archive/`](lessons_archive/) and creates a fresh one
  (`tools/rotate_lessons.sh`); a Stop hook nudges once if substantive work ends with the
  buffer untouched (`tools/lessons_stop_nudge.sh`); the **`/lessons-review`** skill
  (≈weekly, human-driven) clusters lessons that RECUR across archived sessions and graduates
  keepers to `best_practices.md`. Recurrence across sessions — not in-session hit counts —
  is the graduation signal. (Both hooks are registered in the **root** `.claude/settings.json`,
  alongside crewrift's and cue-n-woo's.)

**Cleanup step — run when you wrap up a thread (and before you push/land work).**

1. **Capture all tentative lessons** into [`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md) —
   eagerly; an un-recorded lesson is a lost one.
2. **Reconcile working context** — prune completed/stale detail from
   [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md), update the active policy/version, and
   clear/reseed it on a pivot.

## Deferred tasks

Heartleaf-specific parked work lives in the **shared** [`../TODO.md`](../TODO.md) alongside
the rest of the lab's deferred tasks. Check it at the start of focused work.

## Player policies

_None yet._ When the first policy is built (see [Player build paths](#player-build-paths)),
index it here with a one-paragraph summary, mirroring how crewrift_lab and cue_n_woo_lab
index theirs.
