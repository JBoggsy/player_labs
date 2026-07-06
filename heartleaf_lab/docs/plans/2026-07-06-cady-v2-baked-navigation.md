# Cady v2 — Baked Navigation (plan)

> **Execution:** high-level phase plan; Codex plans+implements each phase under Claude review
> (as v1). **Spec basis:** the v1 eval showed cady scores 0 because it only Gathers when a food
> garden is *currently perceived*, and it spawns seeing none. Fix: **navigate a fixed, baked map**
> to known gardens instead of reacting to sight. Map reference: [`../heartleaf-map.md`](../heartleaf-map.md).

**Goal:** cady v2 explores the day by walking a pre-computed circuit of the 39 fixed gardens
(JPS-routed over a baked walk grid), harvesting each, then hands off to the existing clock-driven
Host logic. Plus a runtime JPS to move to arbitrary walkable points (future: meet other agents).

**Validated enablers (Claude, before this plan):**
- `map.aseprite` `walkable` layer → **748×941 bool grid, 33.9% walkable** (parse confirmed).
- `map.resource` → 39 garden 9×9 rects + 9 house door rects (already in the map doc).
- Gardens are non-walkable but each has walkable cells within the 40px harvest radius → nav target
  = **nearest walkable approach point** to each garden center.
- Deployed game is internally **0.1.0** (replay header) = our clone, so the map is authoritative.

## Global constraints
- Package `cady` (flat, `heartleaf_lab/cady/`). No new heavy deps (numpy already present; hand-roll
  JPS — the Python JPS libs are thin/unmaintained, and most paths bake offline).
- **Coordinate frame:** baked coords are *map-asset* pixels; cady perceives self as
  `object.screen + camera` (world frame). Bake a single `WORLD_TO_MAP` offset (default identity,
  `(0,0)`), tunable; the first v2 eval / a replay decode confirms it. All nav targets convert
  world↔map through this one constant.
- Keep v1's working parts: perception, belief, the bang-bang action controller, Host/Idle modes,
  the SDK bridge + decide adapter. v2 *adds* baked nav + a gather-circuit mode; it does not rewrite
  the pipeline.
- Minimal tests (per lab ethos): the bake correctness (grid shape, approach points walkable,
  circuit visits all), JPS (finds a path on a tiny grid, respects walls), and the circuit mode
  (advances through gardens, hands off to Host at cutoff).

## Phase 1 — Bake pipeline + baked mapdata
**Deliverable:** `cady/tools/bake_map.py` (offline) + committed `cady/mapdata/` (data) + `cady/mapdata.py` (loader).
- Parse `map.aseprite` walkable layer → 748×941 bool grid (the parser is validated; reuse it).
  Bake **bit-packed** (`numpy.packbits`) to `cady/mapdata/walk.npz` (+ shape).
- Parse `map.resource` → 39 garden rects + 9 house rects. Compute each garden's **approach point**
  = nearest walkable cell to its center (BFS/nearest-true within the 40px radius; assert one exists).
  House target = nearest walkable cell to each house door center.
- Compute the **garden circuit**: order the 39 approach points by nearest-neighbor from a sensible
  start, then 2-opt improve, using **JPS path length** (Phase 2) as the distance (fall back to
  Euclidean if JPS not yet available — but prefer JPS). Bake the ordered index list.
- `cady/mapdata.py` loads and exposes: `WALK_GRID` (bool ndarray), `GARDEN_APPROACHES: list[(x,y)]`,
  `GARDEN_RECTS`, `HOUSE_TARGETS: list[(x,y)]` (index = seat), `HOUSE_RECTS`, `GARDEN_CIRCUIT: list[int]`,
  `WORLD_TO_MAP: tuple[int,int]`.
- **Acceptance:** loader imports; grid shape 941×748; every garden approach point is walkable and
  within 40px of its garden center; circuit is a permutation of all 39.

## Phase 2 — JPS pathfinder (`cady/nav.py`)
**Deliverable:** hand-rolled JPS over the walk grid, used offline (Phase 1 distances/paths) + runtime.
- `jps(grid, start, goal) -> list[(x,y)] | None` — 8-connected uniform-cost JPS (jump horizontally/
  vertically/diagonally, forced-neighbor pruning), returns waypoints (corner points) or None if
  unreachable. `nearest_walkable(grid, p)` helper. Diagonal moves must not cut blocked corners.
- `path_length(grid, a, b)` for the circuit bake (Phase 1 imports this).
- `route(world_xy, goal_world_xy) -> next_waypoint` runtime helper: JPS in map frame (convert via
  `WORLD_TO_MAP`), cache the path, return the current waypoint to steer toward; replan when the goal
  changes or drift exceeds a threshold.
- **Acceptance (tests):** on a small hand-built grid, JPS finds a path around a wall, returns None
  when walled off, never cuts a blocked diagonal corner; `nearest_walkable` returns a walkable cell.

## Phase 3 — Gather-circuit mode + integration
**Deliverable:** `cady/modes/gather.py` rewritten as a **circuit-follower**, wired into the strategy.
- New `GatherMode` (or `GatherCircuitMode`): walks `GARDEN_CIRCUIT`. Belief tracks
  `circuit_index` + `current_garden_target`. It JPS-routes (Phase 2) from `belief.self_xy` to the
  current garden's approach point, emitting `navigate_to(next_waypoint)`; when within the harvest
  radius (≤40px of the garden rect) it emits a fresh **A press** (`gather_at`), then advances
  `circuit_index` to the next garden. Perception still tells it which gardens currently show a food
  marker — use that to **skip gardens with no food** when convenient, but don't depend on seeing one.
- **Strategy:** while `time < GATHER_CUTOFF` → GatherCircuit (was: only if a food garden visible —
  drop that condition; the circuit always has somewhere to go). At/after cutoff → Host (unchanged:
  go to own `HOUSE_TARGETS[seat]`, hold). Idle only before self resolves.
- **Seat/home:** Host currently uses `home_anchor` (recorded morning self). With houses baked, also
  set the home target from `HOUSE_TARGETS[seat]` once seat is known; keep `home_anchor` as fallback.
  (Seat identity is still a calibration item — if unknown, home_anchor covers it.)
- Action: `navigate_to` now consumes JPS waypoints (the controller steers to the waypoint, not the
  final goal). Keep gather-press + hold as-is.
- **Acceptance (tests):** with a stub self position, the mode targets the first circuit garden,
  advances after a simulated harvest, and the strategy flips to Host at the cutoff.

## Phase 4 — build, upload cady:v2, re-eval
Rebuild the image (Dockerfile must include the baked `mapdata/` — check `.dockerignore` doesn't drop
it), upload `cady:v2`, run a 15-episode field eval like v1, and check via the telemetry artifact that
cady now enters GatherCircuit, moves, and harvests (inventory > 0), and whether it scores. Calibrate
`WORLD_TO_MAP` from the eval if nav is offset. (Human-gated: eval is fine to run; league submit is not.)
