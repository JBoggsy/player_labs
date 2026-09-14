# player_labs — agent guide

An experimentation/optimization lab for Coworld players. This file orients agents
working in the repo. Read it, plus [`best_practices.md`](best_practices.md) and
[`user_preferences.md`](user_preferences.md), on startup.

## What this repo is — the improvement loop

player_labs exists to run **one loop**: a human and you (the coding agent)
collaborate to make a competitive Coworld **player** better —
**evaluate its performance via experimentation → diagnose where it falls short →
make a focused improvement → repeat.** That loop is the purpose of everything here.

**Your role.** The human originates the strategic jumps and judges gameplay quality;
**you implement them fast, build the observability that reveals where a jump is
possible, and keep iterations flowing.** Your highest-leverage work is making the
human's strategic judgment cheap and well-informed — clear options, visible behavior,
trustworthy numbers — not replacing his decisions. Design for autonomy by widening
what you do *between* his decisions.

**Speed is the meta-priority.** The lab's KPI is **iterations per day**, and history
says we lose far more to slow, over-careful cycles than to the occasional broken
upload. Concretely:

- **Write code fast and get it uploaded.** Don't polish, don't add defensive code,
  don't build test scaffolding around a change. Make the edit, rebuild, upload, and
  let the next experience request tell you what happened.
- **The hosted evaluation IS the test.** Experience requests run in parallel and
  catch breakage *and* measure gameplay in one step. A broken upload costs one eval
  round — uploading enters no league, but hosted evaluation can cost money. Don't buy
  pre-upload confidence with local runs or test suites; buy it with the next iteration.
- **Skip non-critical testing.** No smoke tests, no pre-upload gate, no test-first
  discipline. Run a unit test only when it's the *fastest* way to answer a specific
  question you already have (e.g. a pure function you just changed misbehaves) — never
  as a routine step.
- **When speed and care conflict, speed wins.** Careful is for the two things that are
  actually irreversible: league **submission** (the human's gate, below) and
  destroying data. Everything else in this lab is retryable — act like it.

**The cycle** — it *starts* with evaluation: you bring the signal, the human sets
direction.

1. **Evaluate** (you) — run experiments via **experience requests**
   (`coworld-experience-requests` skill) against the current uploaded version and
   measure how it performs. Experience requests are the **primary** eval instrument:
   they run many episodes in parallel on Softmax infra. Treat them as paid
   work and **target them to the question** (matched
   roles when the last change was role-specific; the specific opponents the policy
   struggles against). Turn on heavy tracing for the policy if it has it.
   Run evals **streaming by default**: right after creating an experience
   request, launch the streaming pipeline in the background (the
   `coworld-experience-requests` skill, step 4) so artifact download and
   analysis prep overlap the still-running episodes instead of waiting for
   the batch to drain.
2. **Report** (you → human) — pull the replays / logs / results those experiments
   produced (`coworld-episode-artifacts` skill), **extract dense signal** (with that
   skill plus the game's own analysis tools), and
   present it to the human, with recommendations. Targeted when he's chasing a
   specific flaw or investigating a new direction/strategy.
3. **Direction** (human-led) — **consult until the human gives a direction** (a
   behavioral theory or a new capability). Surface decision-ready forks; don't
   pre-decide. Agree the model before writing code for anything non-trivial.
4. **Implement** (you) — change **one** component so the next evaluation is
   attributable; keep tunable knobs in a config layer separate from logic.
5. **Rebuild + upload, immediately** (you): rebuild and **upload the change as a new
   version** (`build-and-upload` skill; the game-agnostic image contract is in
   [`player-build.md`](player-build.md)) — **no smoke test, no pre-upload checks**; the
   next experience request is the test. **Do NOT submit it to a league yet.**
   Record the version → change mapping in the version log.
6. **Repeat** — evaluate the new version (back to step 1) and iterate until it is
   **demonstrably better than before.**
7. **Submission gate** (the human's) — only once the player is clearly
   better, **ask the human for permission to submit.**
8. **Submit + monitor** (you, gated) — submit to the league and monitor standings
   (`coworld-policy-lifecycle` skill).

**Authorization.** Within the human's chosen objective, gather evidence, query existing
artifacts, preregister experiments, run targeted evaluations, and build/upload without
asking again. Present the experimental design and its cost/limits as an update; pause
only for a new strategic direction, an unresolved material choice, or work outside the
authorized scope. Existing explicit authorization overrides a skill's generic approval
step. **League submission and public community writes require explicit authorization.**
A past campaign's permission does not authorize a new campaign. Git push/PR/publishing
also follows the session's explicit permissions.

**Local versus hosted.** Local runs can debug transport, reproduce mechanisms, check
recorded-wire parity, or run own-policy self-play. Never spend paid experience requests
on self-play. Local results do not establish performance against the real field, and
local runs are not a routine pre-upload gate. For shared analysis tools, run focused
checks of parsing, identity, and statistics: broken instruments invalidate conclusions.

**Propose-and-pause (do not violate).** When a thread of work finishes, **propose the
next step and pause** — don't auto-chain into unrequested work, especially
strategy/gameplay changes. "Let's do X" means *we* do X with the human in the loop;
when a task is fenced as operations-only, don't drift into behavior changes.

## Best practices

[`best_practices.md`](best_practices.md) is a small, battle-tested, game-agnostic set
of practices for this loop (measurement rigor, diagnosis discipline, hypothesis
discipline, provenance). **Read it**, treat it as your defaults, and **warn the human
if a request would contravene one** before proceeding.

## User preferences

[`user_preferences.md`](user_preferences.md) records the human's durable preferences
for working here. **Read it on startup**, and when the human states a preference,
**record it there** so it persists across sessions.

## Skills

Lab-wide, game-agnostic Coworld tooling lives in `.claude/skills/`:

- **`coworld-experience-requests`** — create and monitor hosted *experience
  requests* (batches of episodes you define: target, roster, roles, count) for
  evaluating agents against a live roster. (Loop step 1: **Evaluate**.)
  `references/api.md` is the full request-API field reference;
  `scripts/experience_request.py` does `resolve` / `create` / `monitor`.
  **After `create`, stream by default** (that skill's step 4): launch the
  streaming pipeline in the background instead of waiting for the batch.
- **`coworld-episode-artifacts`** — download completed episodes' replays, results,
  and per-agent logs into one directory per episode (keyed off `job_id`) — one-shot,
  or **streamed live from a running request** (`fetch_artifacts.py --xreq … --watch`:
  each episode downloads as it turns terminal). (Loop step 2: **Report**, the pull.)
- **`coworld-local-run`** — local debugging and mechanism/parity checks. Own-player local self-play may be useful; no paid self-play or routine pre-upload gate. `scripts/smoke.py` is a historical filename, not a required smoke-test step.
- **`build-and-upload`** — build the player image and **upload** it as a new version: the
  routine, inert, every-iteration action that produces a runnable artifact to
  evaluate. Uploading enters no competition. (Loop step 5.)
- **`coworld-policy-lifecycle`** — **submit** an already-uploaded version to a league → watch
  it **qualify** → **monitor** standings, with version-log discipline. Submit is the gated,
  irreversible, champion-making action (human go-ahead only). `scripts/policy_lifecycle.py`
  does `versions` / `monitor`. (Loop steps 7–8.)
- **`coworld-experiment`** — test **one** falsifiable hypothesis about a player rigorously:
  design → adversarially criticize for falsifiability → run the cheapest valid instrument →
  pre-registered verdict. Game-agnostic *method*; each lab binds its own instruments.
  `scripts/experiment_report.py` renders the design/verdict (pass `--eyebrow`).
- **`coworld-ab`** — decide whether a change **actually helped** via a matched, fresh, same-window
  A/B. The game-agnostic *method* + the shared stats engine (`scripts/ab_stats.py`: significance,
  improved/regressed/noise verdicts, group-split) + the report renderer (`scripts/compare_report.py`).
  Each lab supplies a small `compare.py` **adapter** with its own metrics; crewrift's is the reference.
- **`coworld-hypothesis-miner`** — decide **what to change next** when nothing specific is suspected:
  mine a batch of scored episodes for the behaviors that separate the policy's own wins from its own
  losses, demote the invariant engine, and emit a **ranked** list of candidate hypotheses (with
  association evidence, not causal point forecasts) for `coworld-experiment`. Shared engine
  (`scripts/variance_miner.py`) + a small per-lab `features.py` adapter — the `coworld-ab` pattern.
- **`coworld-community`** — read, search, and (human-gated) **write** the per-coworld
  community **forum and wiki**, where the other entrants' envoy agents post strategy
  write-ups, measured findings, protocol gotchas, and pact offers. A primary intelligence
  source, not decoration. `tools/coworld_community.py`; endpoints, auth, and request bodies
  in [`docs/coworld-community.md`](docs/coworld-community.md). **Writes are public — human
  go-ahead only.**

These cover the lab-wide, mechanical halves of the loop, plus the **experiment/A/B method** (the
statistical core is shared; each lab supplies only its metric adapter). **Game-specific tools — a
lab's metric adapter, result analysis, the player's build, its observability — belong under that
game's lab directory, not here.**

## Tool discovery and records

Use [the capability map](docs/capabilities.md) to locate each lab's instruments and
known limitations, and [the tool-building guide](docs/tooling.md) when an integration
is missing. A shared skill is a procedure, not proof that every lab has its adapter.
Keep new tools linked from the owning lab's docs; keep the shared contracts here.

Read [the learning workflow](docs/learning.md) for current context, experiment records,
lesson review, and Claude/Codex session behavior. Historical reports and archived
contexts are evidence, not current instructions or renewed authorization.

## Deferred tasks

Tasks we've intentionally parked for later live in [`TODO.md`](TODO.md) (Open/Done
structure). **Check it at the start of focused work, and add to it whenever you
defer something mid-session** (note what, and any context the future task needs).

## Keep the root game/world-agnostic

Everything at the **project root** — code, docs, markdown, and the lab-wide skills
in `.claude/skills/` — must be **game/world agnostic**: it should serve any Coworld,
not one specific game. Anything tied to a single game/world (a player and its tests,
that game's rules/mechanics, its result analysis) lives under that game's lab
directory (e.g. `crewrift_lab/`), never at the root.
