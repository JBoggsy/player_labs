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

## Setup

**Prerequisites:** [`uv`](https://docs.astral.sh/uv/) and (only for *building* player
images) Docker. **No sibling checkouts to clone** — the shared player SDK is pulled
straight from the public `Metta-AI/players` repo, pinned in `pyproject.toml`.

```sh
uv sync                                          # .venv: coworld[auth] + the SDK + deps
uv run softmax login && uv run softmax status    # auth to Observatory — expect "Authenticated"
uv run pytest crewrift_lab/crewrift/crewborg/tests   # verify the install (should pass)
uv run coworld --help                            # the game-ops CLI (leagues/results/submit/replays/…)
```

(Auth is the `softmax` CLI; game operations are the `coworld` CLI — both come from the
`coworld[auth]` dependency.) Building the **Nim** players (notsus/suspectra) or the
replay reader additionally needs a **GitHub token** for the still-private Crewrift game
repo — `export GITHUB_PAT=…` or `gh auth login`; see
`crewrift_lab/docs/designs/building_players.md` §Credentials. **Building crewborg and
the whole evaluate loop need no token.**

## Quickstart — your first evaluation, then the loop

The goal is to get you (and your user) into the **evaluate → improve** loop fast. The
human stays in the loop the whole way: you bring the signal and options, they pick the
direction.

**1 — Evaluate an existing policy (no upload, no build, no token).** crewborg already
plays in the live league, so you can report on it immediately. Pull a batch of its
recent league games and turn them into a dense, role-split report:

```sh
# pull recent league episodes for a policy (omit --version to take its recent games)
uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py \
  --policy crewborg -n 50 --out /tmp/eps

# distill them into strengths/weaknesses (role-decomposed, flags interesting episodes)
crewrift_lab/.claude/skills/crewrift-report/scripts/report.py /tmp/eps --policy crewborg
```

**2 — Read the report *with your user* and pick a direction.** The report shows where
the policy is strong vs. weak by role (crewmate vs. imposter) and lists the interesting
episodes. Surface the candidate weaknesses and let the human choose which to chase —
this is the human-in-the-loop decision point. Drill into a flagged episode for the
*why* with `crewrift_lab/.claude/skills/crewrift-report/scripts/profile_replay.py`.

**3 — Improve one thing, then re-measure.** Change a single component of crewborg
(`crewrift_lab/crewrift/crewborg/`), rebuild and upload it as *your own* version, then
re-evaluate and compare to the baseline:

```sh
crewrift_lab/tools/build_player.sh crewborg                      # build a linux/amd64 image
uv run coworld upload-policy players-crewborg:dev --name <your-name>   # routine; not a league submit
# then: run an experience request (coworld-experience-requests skill) targeting your
# version → pull its episodes → re-run the report → compare. Repeat until better.
```

**4 — Submit only when it's clearly better, and only with the human's OK** — submitting
to a league is the irreversible, champion-making step (the `coworld-policy-lifecycle`
skill). Uploading new versions along the way is free and routine.

The full model — the two gates, measurement rigor, and which skill drives each step —
is in [`AGENTS.md`](AGENTS.md).

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
