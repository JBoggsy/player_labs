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
  pyproject.toml       uv project: coworld[auth] + the editable players SDK + deps
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

## Setup

**Prerequisites:** [`uv`](https://docs.astral.sh/uv/), Docker (for building player
images, `--platform=linux/amd64`), and a **sibling checkout of the players repo** that
supplies the shared player SDK.

```sh
# 1. The players repo — provides `players.player_sdk`, installed editable. Keep this
#    checkout clean/untouched: it is the SDK source of truth for every lab.
git clone https://github.com/Metta-AI/players ~/coding/players

# 2. Lab dependencies (creates .venv with coworld[auth], the editable players SDK, …).
uv sync

# 3. Authenticate to Observatory.
uv run softmax login && uv run softmax status   # expect "Authenticated"
uv run coworld --help                            # leagues / results / submit / replays / ...
```

Building the **Nim** players or the replay reader additionally needs a **GitHub token**
(the Crewrift game repo is private for now): `export GITHUB_PAT=…` or `gh auth login`.
See `crewrift_lab/docs/designs/building_players.md` §Credentials.

## External checkouts

The lab reads from / builds against a few sibling repos (it doesn't re-clone them per
task):

| What | Path | Notes |
| --- | --- | --- |
| **Players repo** — the shared `player_sdk` (+ upstream player sources) | `~/coding/players` | **public**; installed **editable**; the SDK **source of truth** — keep it clean |
| **Crewrift game** — Nim engine, scene vocabulary, `notsus` ref player | `~/coding/coworlds/coworld-crewrift` | **private**; read-only reference; the build tools fetch it by pinned ref |
| **metta** — the Coworld platform contract (PLAYER.md/GAME.md, runner) | `~/coding/metta` | read-only reference — **never write to this checkout** |

The `coworld` CLI itself comes from the `coworld[auth]` pip dependency (no checkout
needed).

## Ground rules

- **Never write to `~/coding/metta`** — it's a primary working checkout; read-only here.
- **Keep `~/coding/players` clean** — it's the editable SDK source of truth; vendored
  players are forks *in this repo*, free to drift, but the SDK is imported, not copied.
- **Build `--platform=linux/amd64`** — the cluster is amd64; the host is Apple Silicon,
  so images are built under emulation (the build tools handle this).
- **Upload freely, submit rarely** — uploading a policy version is routine; submitting
  to a league is the irreversible, champion-making action (the human's gate).

## Where to go next

- [`AGENTS.md`](AGENTS.md) — the operating model and skills index (start here to *work*).
- [`crewrift_lab/`](crewrift_lab/) — the first game lab (its README + AGENTS).
- [`player-build.md`](player-build.md) — what any Coworld player image must be.
- [`TODO.md`](TODO.md) — parked work.
</content>
