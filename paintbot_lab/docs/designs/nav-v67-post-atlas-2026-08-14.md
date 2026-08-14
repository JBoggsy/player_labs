# v67 — the post atlas + conservative strategy re-expressions

**Status: APPROVED (James, 2026-08-14) — "that design all looks good",
with the reach-profile cap EXPANDED to full gun range.** Context: strategy
gets a thorough rework in a future update; v67's re-expressions must keep
behavior semantics intact ("just make sure everything still works").
This doc is the implementation spec (Codex-orchestrated).

## Principle (James's ruling on side-lane coverage)

Potential post locations exist EVERYWHERE there is cover. Generation stores
only orientation-free geometry; the situation and strategy decide relevance
at query time, and the situation can change on the fly. This completes the
generation→selection migration made in v63 (facing) and v64 (choice).

## 1. The atlas (worldmap.nim, init-time)

- `AtlasPost* = object; pos*: Point; reach*: array[16, uint16]` — one entry
  per cell with `coverDirs != 0`. reach[k] = unobstructed fire distance (px)
  from the cell center along sector k (16 sectors, same angle convention as
  coverDirs), rays against the wall mask, capped at
  `STENCIL_POST_REACH_CAP_PX` (default `PostGunRangePx` = 1300 — James
  expanded this from the draft's 520; the knob remains the fallback if the
  measurement gate fails).
- `WorldMap.postAtlas*: seq[AtlasPost]` + a coarse spatial index (bucket =
  8×8 cells / 64 px; `atlasNear(map, point, radiusPx): iterator/seq of
  indices`) so radius queries return a few hundred posts, not the map.
- **Lazy duck cache**: `duckFor`-equivalent computed ON DEMAND per atlas
  post at first need and memoized on WorldMap (Table keyed by cell index —
  same lazy-cache precedent as `fields`). Duck contrast is computed against
  the post's TOP-3 reach sectors (replacing the old oriented-fan ends);
  deterministic. NO up-front duck pass.
- The per-front corridor machinery DIES: `generateFront`'s candidate scan,
  corridor scoring, progress buckets, and `PostFront.candidates`/`posts`
  as populated stores. Keep the `PostFront`/`PostCandidate` TYPES only if
  trace compiles more easily with a stub; otherwise remove and let trace
  emit the atlas (a `post_atlas` summary in navigation_map: pos + max
  reach + top sector, schema bump; the orchestrator will handle the
  viewer side separately — keep the trace change minimal and obvious).
- Timing counter: `atlas_ms` in nav_init (replaces post_ms or alongside;
  keep post_ms reporting 0/absent consistently — document choice).

## 2. Selection over the atlas (worldmap.nim, roles.nim, squads.nim)

`selectRankedPost` and `defensivePostForSeat` query the atlas:

- Gather candidates via `atlasNear(anchor, searchPx)` (searchPx as today:
  SquadPostSearchPx for squads; home-outward banding for defenders).
- Two-phase utility, preserving today's term magnitudes:
  - Phase 1 (cheap, all gathered): `0.65 * reachToward(bearing)/reachCap
    - 0.25 * dist/searchPx + PostFacingWeight * (facingScore - 0.5)`
    where `bearing: Option[float]` is a NEW situational parameter; when
    none, use the post's max reach (neutral quality). reachToward = the
    reach of the sector containing the bearing (nearest-sector, same
    quantization as facingScore).
  - Phase 2 (finalists): enrich the top 8 by phase-1 utility with the lazy
    duck: `+ 0.15 * duckContrast`; re-rank; then the existing separation
    filter and rank/seat pick, semantics unchanged.
- Caller bearings (conservative, matching today's intent):
  - `orderPost`: bearing = directive.pos → homeCenter(directive.opponent).
  - `defensivePostForSeat`: bearing = home → the most-direct opponent's
    home (same opponent choice as defenseGate).
- Contracts preserved: same proc names, params gain trailing defaulted
  `bearing`; same Option/tuple returns; separation and banding semantics
  unchanged. (The full strategy rework comes later — this is a store and
  scoring swap, not a strategy change.)

## 3. early_defense re-plumb (strategy.nim/roles.nim — conservative)

Hold points become atlas posts covering the HOME ROOM's entrance gates:
- Home room = roomLabel at capturePoint(team). Its entrance gates =
  `rooms[homeRoom].chokes`.
- Seat-th early-defense agent takes the seat-th gate (cycled if more seats
  than gates), post = atlas query anchored at that gate's pos with bearing
  = gate → outward (away from homeCenter), CONSTRAINED to posts whose pos
  is inside the team's endzone (`zone.contains`) — early_defense's
  stay-in-the-box semantics and the clampToEndzone flag are UNCHANGED, as
  are the release condition (lives-lead gate) and all suppressions. If no
  endzone-interior post covers a gate, fall back to today's
  spawnCoverPoint result (keep that proc).

## 4. barrage_center re-expression (strategy.nim — conservative)

The goal point becomes: among rooms whose peak is reachable
(sameComponent with self), pick argmax of
`peakClearance - BarragePeakDangerWeight * dangerSample(peak)` (new knob,
default 1.0; dangerSample = planDanger at the peak's cell), validated via
nearestReachable. Ring-hold radius, priority, and suppressions unchanged.
Falls back to map center if the atlas/rooms are empty (degenerate maps).

## 5. Hard rules (as previous layers)

Non-minting goal slots; lent/no grid-seq copies; determinism; WorldMap
lazy caches only (fields precedent); locally nim-checkable modules stay
checkable; trace.nim minimal; house style; `intent.reason` stays
telemetry-only; no new deps.

## 6. Validation gates

- Measure atlas build on the giant corpus map: target ≤ 250 ms at the
  1300 px cap (report the number; if over, report — the cap knob is the
  fallback, do not silently reduce it).
- Property additions (orchestrator runs these too): every atlas post has
  coverDirs != 0; reach[k] ≤ cap and 0 where immediately walled;
  determinism of atlas + lazy ducks; selection with bearing=none equals
  a pure quality/distance ranking; defender seats distinct + separated
  (existing invariant must stay green); early_defense posts inside the
  endzone.
- Live: normal + forced-active corpus episodes; plan counters stay clean
  (0 unroutable/fallback); early-defense agents occupy gate-covering
  posts (visible in viewer); tick rate unchanged.
- Grep gates: corridor-era identifiers (`PostCorridorPx` consumers,
  `generateFront`, progress-bucket code) gone or provably dead.
- Hosted: matched v67-vs-v66 batch, standard shape + giant probes; this
  batch also re-tests the v66 h2h scatter watch-item.
