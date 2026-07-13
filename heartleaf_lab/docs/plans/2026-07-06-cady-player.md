# Cady Player — High-Level Implementation Plan

> **✅ COMPLETE (2026-07-06).** All six phases done — cady v1 is built (26 modules, 31 tests
> passing). Phase 1 by Claude (env-sensitive pin bump); Phases 2–6 by Codex (plan → review →
> implement → verify → commit per phase), one commit each: 3e87ffa, then Phase 2–6. Not yet
> done (the human-gated lab loop, below): docker build, upload, first hosted eval, calibration.
>
> **Execution model:** this was a **high-level, phase-level** plan. Each phase was a unit of
> work delegated to **Codex** (`/codex-task`), which planned the detailed steps and implemented
> them. Claude owned the phase boundaries, interface contracts, acceptance criteria, and the
> between-phase review gate; Codex owned the per-phase detailed plan + code. (This deliberately
> departs from the usual bite-sized-TDD plan format because the human asked for Codex to plan
> and execute each phase.)

**Goal:** Build `cady`, Heartleaf's first player policy — a deterministic cyborg Player-SDK
policy on the SDK's new SpriteV1 bridge that connects, navigates, gathers food, and hosts
dinner at its own house, then exits cleanly. Enough for a first hosted eval.

**Spec (source of record):** [`../designs/cady-player-design.md`](../designs/cady-player-design.md)
(and its HTML render). Read it before any phase. **Game reference:**
[`../heartleaf-gameplay.md`](../heartleaf-gameplay.md).

**Architecture:** The SDK's `players.player_sdk.sprite_bridge.run_sprite_bridge` owns transport
+ raw decode into a `SpriteWorld`; a thin `decide.py` adapter wraps that world in an
`Observation`, calls an `AgentRuntime.step()`, and unpacks the returned `Command` into the
bridge's `(mask, chat)`. Cady is pure game logic: perception (SpriteWorld → HeartleafState),
belief, a clock-driven strategy over Gather/Host/Idle modes, and an action resolver that emits
`Button` masks. No vendored wire layer.

**Tech Stack:** Python 3.12, `players.player_sdk` (from the coworld-tools tarball pin), `pydantic`
(match crewborg's SDK types), `numpy` (available; only if needed), Docker (amd64) for the image.

## Global Constraints (apply to every phase)

- **Package root:** a **flat** package `cady` at `heartleaf_lab/cady/` (i.e.
  `heartleaf_lab/cady/perception.py` is module `cady.perception`). Mirrors how
  `crewrift_lab/crewrift/crewborg/` is vendored: **no own `pyproject.toml`** — the root
  `pyproject.toml` discovers it (`[tool.setuptools.packages.find] where=["…","heartleaf_lab"]
  include=["…","cady*"]`, already wired in Phase 1) and cady's deps live in the root pyproject.
  Run/import as `cady` / `python -m cady`.
- **SDK pin:** must be `e8921a6b18484030d8704277e4c52d3aae5c8917` (coworld-tools main, includes the
  sprite bridge PR #20). The old pin `6dcd022e013febffb0043b5f625f853c5cc36e0f` predates it.
- **No vendored wire layer.** Import `run_sprite_bridge`, `SpriteWorld`, `SpriteObject`,
  `SpriteDef`, `SpriteContext`, `Button`, `env_ws_url` from `players.player_sdk`. Do **not**
  copy crewborg's decoder/scene/encoder.
- **No LLM.** v1 is deterministic. **No chat** emitted in v1 (reserve the seam only).
- **No pixel decoding.** Read `world.objects` + `world.sprites[id].label` only; never touch
  `SpriteDef.data`. (A* over walkability is deferred.)
- **Speed over polish** (lab ethos): minimal, high-value tests only — perception label→state and
  the policy clock threshold. No smoke tests / pre-upload gate. The hosted eval is the test.
- **Exit 0 on close** is the SDK bridge's job — don't add competing exit handling.
- **Env WS URL:** connect via `env_ws_url()` (resolves `COWORLD_PLAYER_WS_URL`), used verbatim.

## Interface contracts (the types every phase shares)

Codex must keep these names/shapes stable across phases (a phase sees only its own task):

```python
# types.py — the six AgentRuntime type parameters
@dataclass(frozen=True)
class Observation:            # SDK world + frame
    world: SpriteWorld
    frame: int

@dataclass(frozen=True)
class HeartleafState:         # == Percept, built by perceive(world)
    ready: bool               # camera/self resolved this frame
    self_xy: tuple[int, int] | None
    time_minutes: int | None  # day-minutes since 8:00 AM, parsed from clock glyphs
    gardens: tuple[Garden, ...]      # Garden(pos: tuple[int,int], has_food: bool)
    gnomes: tuple[Gnome, ...]        # Gnome(index: int, pos: tuple[int,int], facing: str)
    own_house_index: int | None
    houses: tuple[House, ...]        # House(index: int, entrance: tuple[int,int])
    inventory_count: int

class Belief:                 # long-lived; mutated by update_belief(belief, percept)
    own_house_index: int | None
    garden_positions: dict[int, tuple[int,int]]   # learned, cached (static map)
    house_entrances: dict[int, tuple[int,int]]
    last_time_minutes: int | None
    inventory_count: int
    current_target: tuple[int,int] | None

class ActionState:            # nav/press bookkeeping across ticks
    ...

@dataclass(frozen=True)
class Intent:
    kind: str                 # "gather_at" | "navigate_to" | "enter_house" | "hold" | "idle"
    point: tuple[int,int] | None = None
    house_index: int | None = None

@dataclass(frozen=True)
class Command:
    held_mask: int = 0
    chat: str | None = None   # reserved; None in v1

# the pure functions
def perceive(obs: Observation) -> HeartleafState: ...
def update_belief(belief: Belief, percept: HeartleafState) -> None: ...
def resolve_action(intent: Intent, belief: Belief, state: ActionState) -> Command: ...

# the bridge callback (decide.py)
def decide(world: SpriteWorld, ctx: SpriteContext) -> int | tuple[int|None, str|None] | None: ...
```

Exact `HeartleafState`/`Belief`/`ActionState` field sets may be refined by Codex during a
phase, but any change to a name another phase consumes must be reflected back here.

## File structure

Flat package (scaffolded in Phase 1 as stubs with `TODO(phase N)` docstrings):

```
heartleaf_lab/cady/            # package `cady` (discovered by root pyproject; no own pyproject)
  __init__.py                  # (done, Phase 1)
  types.py                     # Phase 3
  perception.py                # Phase 3
  belief.py                    # Phase 3
  action.py                    # Phase 4
  modes/{__init__,gather,host,idle}.py   # Phase 5
  strategy.py                  # Phase 5
  runtime.py                   # Phase 5
  decide.py                    # Phase 5
  main.py                      # Phase 6
  tools/capture_scene.py       # Phase 2
  tests/                       # Phases 3-5 (cady.tests)
  Dockerfile                   # Phase 6
  README.md                    # Phase 6
  VERSION_LOG.md               # Phase 6
```

---

## Phase 1 — SDK pin bump + package scaffold ✅ DONE (Claude, 2026-07-06)

**Result:** pin bumped `6dcd022…→e8921a6…` in `pyproject.toml` + `crewrift_lab/tools/versions.env`
(SHA-pinned) + `uv lock`/`uv sync`; root `[tool.setuptools.packages.find]` extended to
`heartleaf_lab` / `cady*`; flat `heartleaf_lab/cady/` stub package created. Acceptance all green:
SDK sprite-bridge imports OK; **crewborg tests 636 passed / 13 skipped** (no shared-SDK
regression); `import cady` OK. Codex begins at Phase 2.

**Goal:** an importable SpriteV1 bridge and a compiling empty `cady` package.

**Scope:**
- Bump the SDK pin `6dcd022…→e8921a6…` in `pyproject.toml` `[tool.uv.sources]` and in
  `crewrift_lab/tools/versions.env` (`PLAYERS_SDK_REF`); run `uv lock`.
- Create `heartleaf_lab/cady/` package skeleton: `pyproject.toml`, `cady/__init__.py`, empty
  module files (with docstrings + `TODO(phase N)` markers), `tests/` dir.

**Acceptance:**
- `uv run python -c "from players.player_sdk import run_sprite_bridge, SpriteWorld, SpriteObject, SpriteDef, SpriteContext, Button, env_ws_url"` succeeds.
- `uv run pytest crewrift_lab/crewrift/crewborg/tests` passes (shared-SDK regression check).
  If it fails, STOP and report — that's a crewrift concern to resolve before continuing.
- `uv run python -c "import cady"` succeeds.

**Interfaces — Produces:** the SDK imports above; the package skeleton. **Consumes:** nothing.

**Notes:** This phase is env-sensitive (shared SDK, `uv lock`). Claude verifies its acceptance
before delegating Phase 2.

## Phase 2 — Capture probe (scene vocabulary tool)

**Goal:** a tool that dumps the live Heartleaf scene vocabulary, to calibrate perception.

**Scope:** `tools/capture_scene.py` — a `decide(world, ctx)` that, for the first N changed
frames, logs every object (`id`, `x`, `y`, `z`, `layer`, `sprite_id`) joined to its
`world.sprites[sprite_id].label`, plus the world-map object (base `1`) for camera recovery; then
returns `Button(0)`. A `main()` runs it via `run_sprite_bridge(env_ws_url(), decide)`.

**Acceptance:** running it against a Heartleaf stream prints labeled objects; **or**, if no live
Heartleaf server is available to Codex, the tool is written + a unit test drives it over a
synthetic `SpriteWorld` and asserts the dump format. Calibration facts it should surface (record
in a short note): the self/seat rule (camera-center hypothesis — which `"gnome <i>"` is ours),
garden/house entrance positions, and the clock-glyph → time reading.

**Interfaces — Produces:** calibration facts consumed by Phase 3 (self-offset, seat id, clock
parse). **Consumes:** Phase 1 SDK imports.

**Notes:** A live local Heartleaf server is a Nim build — Codex may not be able to run it. If so,
proceed on the **camera-center = self** assumption (crewborg's, documented as such) and treat the
first hosted eval's artifact logs as the calibration; say so explicitly. Do NOT block the build on
perfect local calibration (lab ethos).

## Phase 3 — Perception + types + belief

**Goal:** `SpriteWorld → HeartleafState`, the six types, and belief update, with tests.

**Scope:** `types.py` (the contracts above), `perception.py` (`perceive`), `belief.py`
(`Belief` + `update_belief`). Perception reads labels: gnomes `"gnome <index> <dir>"` (base
1000), gardens `"garden marker"` (base 4000), clock per-glyph `"clock <char>"` (base 7000) —
collect clock-glyph objects, sort by `x`, join chars, parse via the inverse of Heartleaf's
`clockName` (AM/PM → day-minutes since 8:00). Self = camera center (world-map object base `1`).
Own house index from our seat (Phase 2 calibration).

**Acceptance (tests):**
- Synthetic `SpriteWorld` with a `"garden marker"` object → `perceive` returns that garden's
  position + `has_food`.
- Synthetic clock-glyph objects (`"clock 3"`,`"clock :"`,`"clock 0"`,`"clock 0"`,`"clock p"`,
  `"clock m"`) → `time_minutes` parses to the correct day-minute.
- `update_belief` caches garden/house positions across frames (static map).
- Missing camera/clock → `HeartleafState.ready == False` (clean degrade).

**Interfaces — Produces:** `perceive`, `update_belief`, all six types. **Consumes:** Phase 1
imports; Phase 2 calibration.

## Phase 4 — Action resolution

**Goal:** `Intent → Button mask` via a bang-bang movement controller, with tests.

**Scope:** `action.py` (`resolve_action`, `ActionState`). Reimplement crewborg's controller as
an *algorithm* (not vendored code): steer toward a target world point with a release-near-target
deadband and a predictive stop, emitting a `Button` d-pad mask. Intents: `navigate_to` (steer to
point), `gather_at` (navigate to garden, then a fresh **A press** in range — edge-triggered),
`enter_house` (navigate to entrance, then A press), `hold`/`idle` (neutral mask `0`).

**Acceptance (tests):**
- Target strictly to the right of self → mask includes `Button.RIGHT`, excludes LEFT.
- Within arrive-radius of the target → axis released (no d-pad on that axis).
- `gather_at` in range → a fresh `Button.A` press (edge-triggered: releases if held last tick).
- `hold`/`idle` → mask `0`.

**Interfaces — Produces:** `resolve_action`, `ActionState`. **Consumes:** `Intent`, `Belief`,
`HeartleafState` types (Phase 3).

## Phase 5 — Modes + strategy + runtime + decide

**Goal:** assemble the cyborg brain and the bridge adapter, with tests.

**Scope:**
- `modes/gather.py` `GatherMode` (nearest `has_food` garden → `gather_at`), `modes/host.py`
  `HostMode` (own-house entrance → `enter_house`, then `hold` inside), `modes/idle.py`
  `IdleMode` (`idle` when not ready / no garden).
- `strategy.py` — deterministic clock-driven selection: `time_minutes < GATHER_CUTOFF` (config,
  ~5:00 PM = 540 min-since-8AM) → Gather; else → Host; not-ready → Idle. Thresholds in a
  `config.py`-style constants block.
- `runtime.py` `build_runtime(trace_sink, metrics_sink)` — assemble `AgentRuntime` over the six
  types + `ModeRegistry` + `perceive`/`update_belief`/`resolve_action` (crewborg's `build_runtime`
  is the reference template).
- `decide.py` — `decide(world, ctx)`: wrap in `Observation(world, ctx.frame)`, call
  `runtime.step(obs)`, unpack `Command` → `(held_mask, chat)` (or bare mask). Build the runtime
  once (module-level or closure), not per frame.

**Acceptance (tests):**
- Clock before cutoff → strategy selects `GatherMode`; at/after cutoff → `HostMode`;
  not-ready → `IdleMode`.
- `decide` over a synthetic gather-time `SpriteWorld` with one food garden → returns a non-zero
  mask (moves toward the garden); over an empty/not-ready world → returns `0`/`None`.

**Interfaces — Produces:** `build_runtime`, `decide`. **Consumes:** Phases 3–4.

## Phase 6 — Entry point + packaging

**Goal:** a buildable player image with an entry point, docs, and version log.

**Scope:** `main.py` (`asyncio.run(run_sprite_bridge(env_ws_url(), decide, trace_outputs=…))`,
with the trace/metrics wiring pattern from crewborg's `policy_player.py`, falling back to stderr
when no artifact upload URL; `__main__`), `Dockerfile` (`--platform=linux/amd64`, installs the
SDK pin + cady, entrypoint runs `python -m cady`), `README.md` (what cady is, build/run/upload
commands, the design/plan links), `VERSION_LOG.md` (v1 → this design).

**Acceptance:**
- `uv run python -m cady` fails only on the missing WS URL (proves wiring; the SDK raises a clear
  error for the unset env var) — i.e. it imports and reaches the bridge.
- `docker build --platform=linux/amd64` succeeds (image builds; not run here).

**Interfaces — Produces:** the runnable image + entry. **Consumes:** Phase 5 `decide`.

---

## After the plan (the lab loop — Claude + human, not a Codex coding phase)

Build the image and upload a version (`build-and-upload` skill), run a first experience request
against the bundled villager field (`coworld-experience-requests`), pull artifacts + logs
(`coworld-episode-artifacts`) to validate connect→gather→host→exit and calibrate self/seat +
geometry from the real stream. **League submission is the human's gate** — not part of this plan.
Also verify before the first upload: the Python-image upload path for this game, and the league
existence / game version via the Observatory API (design §Risks 5–6).

## Self-review (spec coverage)

- Design §2 (SDK bridge + pin bump) → Phase 1. §7 (label vocabulary, clock glyphs) → Phase 3.
  §Architecture table → Phases 3–6 by file. §Policy (clock-driven modes) → Phase 5. §Action
  resolution → Phase 4. §Testing (perception + policy only) → Phases 3, 5. §Risks: self/seat +
  geometry → Phase 2 + Phase 3 note; shared-SDK bump → Phase 1 acceptance; pixel-decode deferred →
  Global Constraints; league/upload-path → the lab-loop section. No spec section is unassigned.
