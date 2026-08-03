# paintbot_lab — agent guide

The **Paintbot** corner of player_labs: where we build, evaluate, and improve
**player policies** for Coworld Paintbot. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the
improvement loop, your role in it (speed first), the submission gate, and the
game-agnostic skills. This file is the **Paintbot-specific layer**: the game,
the docs, the practices, and the policy we optimize. When the two disagree, the
root defines *process*; this file defines *Paintbot*.

> **Lab status (2026-08-03): bootstrapped.** `stencil` (Python,
> [`paintbot/stencil/`](paintbot/stencil/)) is implemented + tested, **not yet
> uploaded/evaluated**. The game repo is the SAME clone as CTF's
> (`~/coding/coworlds/coworld-ctf` — paintbot is a second manifest over the
> same binary). Deployed paintbot **0.7.178** at lab creation; the league
> redeploys often — check `uv run coworld list | grep paintbot`. Live state:
> [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).

## What Paintbot is

A 2-or-4-team capture-the-heart paintball shooter on **BitWorld Sprite-v1**,
sharing CTF's engine, mechanics, and protocol. What's different from the CTF
league, and why it reshapes the lab:

- **Procedurally generated maps** (all competitive variants except `default`):
  five size classes, sides/corners/plus layouts, seed never on the wire. **No
  pre-baked navigation, no authored POIs, no battle plans** — every map fact is
  read from the init snapshot (walkability sprite, `game teams` marker,
  `endzone` markers, planted hearts).
- **2-or-4 teams** (red/blue/green/yellow), pure FFA when 4: capturing a heart
  **eliminates** that team; last team standing wins.
- **Pot scoring**: +2/-2 (2-team) or +4/-1/-1/-1 (4-team); timeout draw = -1
  for everyone. Win rate is still the only metric that matters.
- **Variable seating**: 4 variants seat one policy for 4-8 agents; live rounds
  pad with fillers (7+7+2 observed). Never assume you own the whole team.

Full reference: [`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md). The
founding recon (with `file:line` citations into the game repo, metta, and the
live league): [`docs/recon/paintbot-2026-08-03.md`](docs/recon/paintbot-2026-08-03.md).

## The loop, in Paintbot terms

The root loop (evaluate → report → direction → implement → rebuild+reupload →
repeat → human gate → submit) runs **unchanged**. Paintbot-specific instruments:

- **Evaluate** (step 1) — experience requests against the uploaded stencil
  version. Natural cuts: **variant** (default / 2v2 / 4ffa / 4ffa8 — the live
  rotation is ~half `default`), **team color**, **seat**, **win path**
  (capture-elimination vs wipe vs survival vs timeout). Because scoring is
  win-only, win rate per variant is the metric; kills/captures diagnose.
- **Report** (step 2) — pull artifacts with `coworld-episode-artifacts`. There
  is **no paintbot survey/warehouse skill yet**; ctf_lab's `event_warehouse.py`
  re-keying machinery and `analyze_reporter_warehouse.py` pattern are the
  templates when episodes exist (replays carry exact `mapSpec` geometry, so
  per-map analysis is possible post-hoc). Building a paintbot warehouse is the
  highest-leverage tooling investment once we have batches.
- **Implement** (step 4) — change [`paintbot/stencil/`](paintbot/stencil/);
  knobs live in `config.py` (`STENCIL_*` env vars, tunables registry —
  `uv run python -m paintbot.stencil.tuning`) so each iteration is attributable.
- **Rebuild / upload / submit** (steps 5-8) — `tools/build_player.sh stencil`,
  then the game-agnostic skills. The hosted eval is the test; `coworld-local-run`
  is a debugging tool only.

## The player: stencil

A deterministic cyborg forked from ctf_lab's **beacon** (read
[`docs/designs/stencil-v1-design.md`](docs/designs/stencil-v1-design.md) — it
carries the scrap-vs-port ledger). The architecture in one breath: `perception`
reads labels **plus** the walkability sprite pixels and wire markers; the
runtime builds an **episode-scoped `WorldMap`** (eroded nav grid, cover, lazy
per-goal Dijkstra flow fields, derived chokes/rallies/spawn-aim — replacing
beacon's `nav.npz` bake + POIs + plans wholesale); `belief` folds tracks,
danger, hearing, chat, per-color hearts (with retirement + steal-target
choice); `strategy` runs the ladder (carry-home > intercept-thief >
escort-carrier > grenade-clear > items > convert-hunt > role split);
`action` emits the mask (lighthouse sweep, snap/lead aim, fire gate,
friendly-fire guard, peek-fire-duck, grenade overlay). Deliberately **cut from
v1**: posts, battle plans, POIs, anti-turtle (all fixed-arena machinery).

Key invariants to respect when editing:

- **No module-level map caches.** All map state lives on `belief.worldmap`
  (episode-scoped). This was a deliberate fix to a latent beacon bug class.
- **The wire is the only map source.** If you need a map fact, derive it in
  `worldmap.py` from the init snapshot; never constant-ize a generated map.
- **Multi-team throughout**: any code touching "the enemy" must handle 1-3
  enemy colors and hearts leaving play (`belief.hearts_retired`).
- Seat conventions must degrade when we own only part of a team.

## Docs

- [`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md) — game reference. **Start here.**
- [`docs/recon/paintbot-2026-08-03.md`](docs/recon/paintbot-2026-08-03.md) — the founding recon.
- [`docs/designs/stencil-v1-design.md`](docs/designs/stencil-v1-design.md) — stencil architecture.

## Skills

No paintbot-specific skills yet. The loop's **game-agnostic** halves (experience
requests, artifact download, build-and-upload, policy lifecycle, A/B,
hypothesis miner) live at the **lab root** (`../.claude/skills/`, indexed in
[`../AGENTS.md`](../AGENTS.md)). Worth building once episodes exist: a paintbot
**event warehouse + survey** (per-variant win path), then a `compare.py` A/B
metric adapter (pot-scoring aware).

## Testing discipline

Same as ctf_lab: **minimal, tightly-focused tests** — load-bearing invariants
only (the WorldMap build, wire parsers, seat dealing, the end-to-end
synthetic-frame smoke test in `paintbot/stencil/tests/`). The hosted eval is
the test; speed wins. Run: `uv run pytest paintbot_lab/paintbot/stencil/tests`.

## Working context & tentative lessons

Two session-spanning files carry state forward — **read both on startup**:

- **[`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)** — the live, minimal state of
  what we're working on right now. Keep it updated; clear/reseed on a pivot.
- **[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md)** — this session's eager
  candidate-lessons buffer (auto-rotated by `tools/rotate_lessons.sh`, archived
  to [`lessons_archive/`](lessons_archive/); recurring lessons graduate to
  `best_practices.md` via the lessons-review flow).

**Cleanup step when wrapping a thread**: capture lessons; reconcile
WORKING_CONTEXT.

## Deferred tasks

Paintbot-specific parked work lives in the shared [`../TODO.md`](../TODO.md).

## Player policies

- **stencil** *(Python)* — at [`paintbot/stencil/`](paintbot/stencil/), the
  primary (only) Paintbot policy. **Current: unreleased (pre-v1)** — built and
  unit-tested, awaiting first upload + hosted evaluation. Version history:
  [`paintbot/stencil/VERSION_LOG.md`](paintbot/stencil/VERSION_LOG.md).
  Behavior knobs are `STENCIL_*` env vars set at upload time for A/B
  (`uv run python -m paintbot.stencil.tuning secret-env ...`).
  Build: `tools/build_player.sh stencil`.
