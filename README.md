# player_labs

A **human-in-the-loop lab for making Coworld game-playing agents better.** Coworld
(Softmax's Observatory) runs competitive AI leagues; this repo is where we evaluate a
**player policy**, figure out where it falls short, make a focused improvement, and
measure whether it helped — over and over.

This README is the **front door**: what the lab is, how it's laid out, and how to get
set up. It's written for both the humans working here and the coding agents that do
most of the building.

> **Platform contracts → [verified reference](docs/platform-reference.md).** Credits, API limits, visibility, completion and runtime facts, with source links.

> **Operating model → [`AGENTS.md`](AGENTS.md).** How the improvement loop actually
> runs (the human sets strategic direction; the agent builds observability, measures,
> and ships iterations fast — speed over caution), plus the skills index and the
> submission gate. Read that before doing optimization work. This README doesn't repeat it.

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
  tools/               shared analysis, current-context hooks and community CLI
  .claude/skills/      lab-wide, game-agnostic Coworld skills (below)
  crewrift_lab/        first game lab — Crewrift (has its own README + AGENTS)
  cue_n_woo_lab/       second game lab — Cue-n-Woo, a text theory-of-mind game (own README)
  heartleaf_lab/       third game lab — Heartleaf, a 9-gnome garden-dinner game (own README)
  ctf_lab/             fourth game lab — CTF, an 8v8 capture-the-flag shooter — inactive
  vanilla_wow_lab/     fifth game lab — Vanilla WoW, a real WoW 1.12.1/VMaNGOS realm (own README)
  paintbot_lab/        sixth game lab — Paintbot, a 2-or-4-team capture-the-heart shooter on procgen maps (README + docs index)
  proxywar_lab/        seventh game lab — Proxy War, an OpenFront-fork RTS territory game with LLM/agent nations (own README)
  emergant_lab/        eighth game lab — Emerg-ant, a 16-agent repeated-food-capture colony shooter
  gods_of_the_arena_lab/ ninth game lab — Gods of the Arena, a BASIC-scripted 5v5 lane battler (knowledge map in docs/research.md)
  sugarscape_lab/      tenth game lab — Sugarscape, a movement-policy lab over coworld-sugarscape (own README)
  pyproject.toml       uv project: coworld[auth] + the pinned players SDK (from git) + deps
```

Each **game** gets its own lab directory (`crewrift_lab/`, …). Anything game-specific
— a player's source, that game's rules, its result analysis — lives under its game
lab; the root stays game-agnostic.

## Skills

Lab-wide, game-agnostic Coworld tooling in [`.claude/skills/`](.claude/skills) — these
drive the mechanical halves of the loop:

- **`coworld-experience-requests`** — create & monitor hosted evaluation batches.
  After `create`, the default is to **stream** the results (below), not wait.
- **`coworld-episode-artifacts`** — download episodes' replays, results, and logs —
  one-shot for finished batches, or **streamed live** (`--watch`) while a batch runs.
- **`coworld-local-run`** — run your built policy locally (focused debugging/mechanism checks and own-policy self-play; no routine upload gate).
- **`coworld-policy-lifecycle`** — (gated) submit an uploaded version → monitor.
- **`build-and-upload`** — build a player image and upload it as a new policy version;
  the routine, inert, every-iteration action. Uploading enters no competition.
- **`coworld-experiment`** — design + run **one** falsifiable hypothesis test (design →
  criticize → cheapest instrument → pre-registered verdict). Game-agnostic method.
- **`coworld-ab`** — decide whether a change actually helped via a matched, fresh A/B. Ships
  the shared stats engine + report renderer; each lab supplies a small `compare.py` metric adapter.
- **`coworld-hypothesis-miner`** — decide *what to change next*: mine a scored batch for the
  behaviors separating the policy's own wins from its losses; ranked hypothesis candidates.
  Shared engine; each lab supplies a small `features.py` adapter.
- **`coworld-community`** — read, search, and (human-gated) write a Coworld's community forum
  and wiki, where other players' agents post write-ups and pact offers; endpoint reference in
  [`docs/coworld-community.md`](docs/coworld-community.md).

Game-specific analysis/build skills — and each lab's `compare.py` metric adapter — live in the
game labs (e.g. Crewrift's `crewrift-survey`, `crewrift-ab`). The index with full descriptions is
in [`AGENTS.md`](AGENTS.md).

## Getting started

**New here? Follow the guided onboarding: [`docs/getting-started.md`](docs/getting-started.md)** —
it walks you (and your coding agent) through authentication, picking a player to work
on, your first evaluation, and your first improvement, step by step.

> **Coding agents:** choose the relevant lab, read its AGENTS and WORKING_CONTEXT, and verify that the recorded objective still applies. The current user request defines the objective. Start onboarding when no current policy/objective has been chosen.

**Pointing a new user here?** [`docs/starter-prompt.md`](docs/starter-prompt.md) is a
copy-paste prompt they can hand to their own coding agent to fork & clone the repo and
run the guided onboarding.

**Prerequisites:** [`uv`](https://docs.astral.sh/uv/) and (only for *building* player
images) Docker — **no GitHub credentials and no sibling checkouts** to build or run; the
player SDK and the Crewrift game repo are public. (A **GitHub account** isn't required to
try the lab, but is recommended so you can **fork** it and keep your own copy to save
work in — the guided onboarding sets that up.) TL;DR if you just want the commands:

```sh
uv sync                                          # .venv: coworld[auth] + the SDK + deps
uv run softmax login && uv run softmax status    # auth to Observatory — expect "Authenticated"
```

The guided onboarding above ([`docs/getting-started.md`](docs/getting-started.md)) takes
you all the way to your first evaluation — authenticate, pick a player, then build →
upload → run an experience request → report + diagnose. After that you're in the
**evaluate → improve** loop; its full model (and the submission gate) is in
[`AGENTS.md`](AGENTS.md).

## Ground rules

- **Upload freely, submit rarely** — uploading a policy version is routine; submitting
  to a league is consequential and requires explicit human authorization.
- **Build `--platform=linux/amd64`** — the cluster is amd64; on Apple Silicon images
  build under emulation (the build tools handle this).
- **Player source and SDK versions have separate ownership.** Vendored players live in their game labs; the shared SDK is imported through [pyproject.toml](pyproject.toml) and locked by `uv.lock`. Per-player images may pin a different SDK in their own build configuration. Inspect both before claiming local/hosted parity; changing a live player's SDK is a separate behavioral validation task.
- The Coworld runtime contract lives in the `Metta-AI/coworld` repository; Observatory backend behavior lives in `Metta-AI/metta`
  when you need implementation evidence. **Do not modify `~/coding/metta`; authorized Metta changes use a separate checkout.**

## Where to go next

- [`AGENTS.md`](AGENTS.md) — the operating model and skills index (start here to *work*).
- [`crewrift_lab/`](crewrift_lab/) — the first game lab (its README + AGENTS).
- [`player-build.md`](player-build.md) — what any Coworld player image must be.
- [`docs/player-engineering.md`](docs/player-engineering.md) — how to design what goes
  *inside* one: architecture selection, robustness, navigation.
- [`TODO.md`](TODO.md) — parked work.

## Tool and learning navigation

- [Capability map](docs/capabilities.md)
- [Choosing/building tools](docs/tooling.md)
- [Learning and experiment records](docs/learning.md)
