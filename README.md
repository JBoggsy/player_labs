# player_labs

> ## ▶ START HERE: [`docs/player-improvement-loop.md`](docs/player-improvement-loop.md)
>
> **The playbook for how player optimization actually works** — the
> human-in-the-loop iterative improvement loop, measurement rigor, diagnosis, the
> failure-mode taxonomy, and the autonomy boundary (where the human originates the
> big jumps vs. where the agent runs on its own).
>
> **Read it before doing any optimization, evaluation, or diagnosis work in this
> lab.** It is game-agnostic and tool-agnostic by design, and it is the source of
> truth for *process*. Everything else in this repo is in service of it.

A self-contained **experimentation and optimization lab for Coworld players**.

The lab is where we systematically **evaluate/measure** existing players and
**build/iterate** new ones — the harness, experiment configs, and analysis
outputs live here. The players themselves and the games they target live in
their own checkouts (see [External checkouts](#external-checkouts)); this repo
calls the `coworld` CLI / Observatory API and builds player images from those
sources. It does **not** vendor them.

First lab: [`crewrift_lab/`](crewrift_lab/) — the Crewrift social-deduction game.

## What a Coworld player is (the contract)

A player is a short-lived Docker container that is a **WebSocket client**. At
episode time the Coworld runner sets `COWORLD_PLAYER_WS_URL` (slot + token
already encoded); the player connects, speaks the game's protocol for that one
slot, and **exits cleanly on `{"type":"final"}`**. Submitted policy versions
substitute for a manifest's reference players under this identical contract.

**Softmax / Observatory** hosts the competition:
`league → division → round → pool → episode`, with submissions, memberships, and
standings. The optimization loop is: run episodes → inspect replays/logs/results
→ improve the player → resubmit.

## Two core workflows

### A. Evaluate / measure a player
Run hosted **experience-request** batteries against the live roster, break scores
down by role, run significance tests, and triage replays. Store configs +
outputs under the relevant lab. The mature path is the
`crewrift-experience-analysis` skill (role-broken-down stats, Hedges' g, Cliff's
delta, Welch/Mann-Whitney q-values) plus crewborg's own `fetch_episodes` script.

### B. Build / iterate a player
Develop or tune a player, test it locally against a Crewrift dev server / fixture,
build an `amd64` image, then `upload-policy` + `submit` an improved version.
Crewrift's reference target is **crewborg** (Player-SDK agent with a Bayesian
suspicion model); its `design.md §12` tuning parameters explicitly await tuning
against the live server — a natural first optimization surface.

## Setup

```sh
uv sync                 # create .venv with coworld[auth] + analysis deps
uv run softmax login    # auth to Observatory (token cached locally)
uv run softmax status   # confirm: "Authenticated"
uv run coworld --help   # CLI: leagues / divisions / results / submit / replays / ...
```

## External checkouts (read / build from, not vendored)

| What | Path | Repo |
| --- | --- | --- |
| Coworld framework (CLI, manifest schema, runners) | `~/coding/metta/packages/coworld` | Metta-AI/metta — **read-only; never write to this checkout** |
| Crewrift game (Nim engine, `notsus` ref player) | `~/coding/coworlds/coworld-crewrift` | Metta-AI/coworld-crewrift |
| Players repo (`player_sdk`, `crewborg`, …) | `~/coding/players_checkouts/players` | Metta-AI/players |
| Crewrift world manifest (registry entry) | `~/coding/metta/worlds/crewrift` | Metta-AI/metta |

## Gotchas (learned; don't relearn)

- **Always build `--platform=linux/amd64`.** The cluster is amd64; arm64 images
  emulate slowly or fail.
- **Always pass `--run` at `upload-policy`** (and local test), else the runner
  silently falls back to the manifest's reference player.
- **Exit on `{"type":"final"}`**, not `done:true`, or the pod times out.
- **Unique `name=` per slot** in local multi-slot runs, or the engine conflates
  same-named players and stalls in the lobby.
- **Never hardcode league/division/policy IDs** — they rotate. Resolve live IDs
  at runtime via the CLI / API.
- **Certification fixtures are degenerate** (tiny step cap): a score of 0 there
  does not mean the player is broken; test a real variant separately.
- **CLI route drift:** the live server renamed `/v2/episode-request*` →
  `/v2/experience-request*`; older `coworld episodes/replays/episode-logs` can
  404. Prefer the analysis skill / `fetch_episodes` (they call live routes
  directly) and check `<api>/observatory/openapi.json` for current paths.

## Layout

```
player_labs/
  README.md            this file — lab-wide conventions + the player contract
  docs/
    player-improvement-loop.md   the process playbook (START HERE)
  pyproject.toml       uv project: coworld[auth] + analysis deps
  crewrift_lab/        first lab (Crewrift) — see its README
```
