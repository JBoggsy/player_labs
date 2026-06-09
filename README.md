# player_labs

A **human-in-the-loop lab for making Coworld game-playing agents better.** Coworld
(Softmax's Observatory) runs competitive AI leagues; this repo is where we evaluate a
**player policy**, figure out where it falls short, make a focused improvement, and
measure whether it helped — over and over.

This README is the **front door**: what the lab is, how it's laid out, and how to get
set up. It's written for both the humans working here and the coding agents that do
most of the building.

> **Operating model → [`AGENTS.md`](AGENTS.md).** How the improvement loop actually
> runs (the human sets strategic direction; the agent builds observability, measures,
> and holds the correctness gate), plus the skills index and the two gates. Read that
> before doing optimization work. This README doesn't repeat it.

## How the lab works, in one paragraph

The loop is **evaluate → report → decide → improve → repeat**. You run batches of
hosted games (*experience requests*) against the live roster, pull the replays/logs,
distill them into a dense report of strengths and weaknesses, the human picks a
direction, the agent changes **one** thing and rebuilds, and you re-measure — only
submitting to a league once the player is demonstrably better. The details, the
discipline, and the tooling for each step live in [`AGENTS.md`](AGENTS.md),
[`best_practices.md`](best_practices.md), and the skills.

## Layout

```
player_labs/
  AGENTS.md            operating model: the loop, the agent's role, the skills index
  best_practices.md    battle-tested disciplines for the loop (read on startup)
  user_preferences.md  durable human preferences (read on startup)
  player-build.md      the game-agnostic Coworld player image contract
  TODO.md              deferred tasks
  .claude/skills/      lab-wide, game-agnostic Coworld skills (below)
  crewrift_lab/        first game lab — Crewrift (has its own README + AGENTS)
  pyproject.toml       uv project: coworld[auth] + the pinned players SDK (from git) + deps
```

Each **game** gets its own lab directory (`crewrift_lab/`, …). Anything game-specific
— a player's source, that game's rules, its result analysis — lives under its game
lab; the root stays game-agnostic.

## Skills

Lab-wide, game-agnostic Coworld tooling in [`.claude/skills/`](.claude/skills) — these
drive the mechanical halves of the loop:

- **`coworld-experience-requests`** — create & monitor hosted evaluation batches.
- **`coworld-episode-artifacts`** — download episodes' replays, results, and logs.
- **`coworld-local-run`** — smoke-run your built policy locally (Gate 1).
- **`coworld-policy-lifecycle`** — upload a new version → (gated) submit → monitor.

Game-specific analysis/build skills live in the game labs (e.g. Crewrift's
`crewrift-report`). The index with full descriptions is in [`AGENTS.md`](AGENTS.md).

## Getting started

**New here? Follow the guided onboarding: [`docs/getting-started.md`](docs/getting-started.md)** —
it walks you (and your coding agent) through authentication, picking a player to work
on, your first evaluation, and your first improvement, step by step.

> **Coding agents:** if this is your first time in this repo — or
> [`crewrift_lab/user_preferences.md`](crewrift_lab/user_preferences.md) has **no
> `## Working context` entry naming an active policy** — start with
> [`docs/getting-started.md`](docs/getting-started.md). Step 2 records the chosen policy
> there, so a recorded active policy is the signal that onboarding is already done and
> you should resume the loop (see [`AGENTS.md`](AGENTS.md)) instead.

**Pointing a new user here?** [`docs/starter-prompt.md`](docs/starter-prompt.md) is a
copy-paste prompt they can hand to their own coding agent to clone the repo and run the
guided onboarding.

**Prerequisites:** [`uv`](https://docs.astral.sh/uv/) and (only for *building* player
images) Docker — **no GitHub credentials and no sibling checkouts**; the player SDK and
the Crewrift game repo are public. TL;DR if you just want the commands:

```sh
uv sync                                          # .venv: coworld[auth] + the SDK + deps
uv run softmax login && uv run softmax status    # auth to Observatory — expect "Authenticated"
uv run pytest crewrift_lab/crewrift/crewborg/tests   # verify the install (should pass)
```

The guided onboarding above ([`docs/getting-started.md`](docs/getting-started.md)) takes
you all the way to your first evaluation — authenticate, pick a player, then build →
upload → run an experience request → report + diagnose. After that you're in the
**evaluate → improve** loop; its full model (and the two gates) is in
[`AGENTS.md`](AGENTS.md).

## Ground rules

- **Upload freely, submit rarely** — uploading a policy version is routine; submitting
  to a league is the irreversible, champion-making action (the human's gate).
- **Build `--platform=linux/amd64`** — the cluster is amd64; on Apple Silicon images
  build under emulation (the build tools handle this).
- **The SDK is imported, not vendored** — vendored players are forks *in this repo*,
  free to drift; `players.player_sdk` is imported from the public players repo, which
  **tracks `main`** (`pyproject.toml`). `uv.lock` records the exact commit so clones
  are reproducible; adopt the latest with `uv lock --upgrade-package players` (no
  hand-edited SHAs). The **game** ref (`CREWRIFT_REF`) stays deliberately pinned — it
  must match the deployed league game, not latest (see `crewrift_lab/tools/versions.env`).
- The Coworld platform contract (PLAYER.md/GAME.md, runner) lives in the `metta` repo
  if you need to consult it — **read-only; never write to a `metta` checkout.**

## Where to go next

- [`AGENTS.md`](AGENTS.md) — the operating model and skills index (start here to *work*).
- [`crewrift_lab/`](crewrift_lab/) — the first game lab (its README + AGENTS).
- [`player-build.md`](player-build.md) — what any Coworld player image must be.
- [`TODO.md`](TODO.md) — parked work.
</content>
