# v63 — post candidate re-sourcing (D5-2) + post viewer extension

**Status: APPROVED (James, 2026-08-12, with the §2a facing revision) and
IMPLEMENTED same day.** Measured outcome (local, same maps, uncontended):
giant-probe `post_ms` 1528 → **73 ms**, duo-cell 2166 → **88 ms**; giant
seat init ~1.0–1.1 s — below the v61 pre-Layer-2 baseline. The decisive fix
was not the re-sourcing alone: the first cut *regressed* giants (+62%)
because `fieldsFor` returns `RouteFields` **by value**, so every
per-cell `distanceAt` call memcpy'd ~1.4 MB of cached Dijkstra field out of
the table — hoisting the two fields once per front and reading distances by
cell index removed the dominant cost. (Implication recorded for Layer 3:
every `distanceAt`/`routeDistance`/`flowWaypoint` call still pays that copy,
including per-tick follower lookups; the planner rework must use borrowed/
indexed field access.) Selection mirror verified fail-closed on 200
harness-sampled real-code cases. Original proposal below. Executes the
deferred D5-2 option from the
[Layer 2 proposal](nav-layer2-topology-proposal-2026-08-11.md) (§6), now that
the corpus overlays exist and the v62 batch measured the motivating cost:
directional cover roughly doubled-to-quadrupled the cover-cell count, and the
post pass — whose candidate stage scans the full grid gated on `cover` — grew
~0.7–1.5 s on giants (hosted, paired in-episode probes). Decision points are
**[P1]–[P5]**.

## 1. Scope

**Changes:** only `generateFront`'s *candidate generation* stage (stage 1 of
4) in `worldmap.nim`, plus the viewer/tooling below. **Explicitly unchanged:**
corridor/progress scoring formulas, bucket caps and separation, the
sightline-ray stage, duck pairing, final selection, `PostFront`/
`PostCandidate` shapes, and every consumer (roles, squads, trace, render_nav).
Squad/defender *decision* logic stays untouched (rework non-goal).

## 2. Candidate re-sourcing

Today: scan all grid cells; keep `cover[cell]` cells on a stride-2 lattice;
compute route detour per cell; bucket by route progress. On the giant that is
~86k cells scanned and (post-v62) thousands passing the cover gate, for 12
buckets × 6 retained candidates.

New: **seed candidates from the topology, where posts actually live** (sketch
§3.2: "candidate posts = cover-potential cells near chokepoints/rooms facing
likely approach directions"):

1. **On-route chokes.** For each choke, compute `detour = fromHome + toEnemy
   − direct` (the same cached-field lookups as today, but ~10²·chokes instead
   of ~10⁵ cells). Keep chokes with `detour ≤ PostCorridorPx × 3` — the same
   cap the per-cell scan uses today, so route coverage matches.
2. **Gate vicinity.** For each on-route choke, candidate cells = walkable
   cells within **[P1]** `PostGateVicinityPx` (default 48 px, env knob) of
   the gate center, with `coverDirs != 0` (any real cover), de-duplicated
   across nearby chokes. **No static facing filter** — see §2a: James's
   review killed the toward-enemy-home orientation (only valid for the
   opening advance; wrong for carry-home where threats are behind you; and
   4-team maps have three enemy pedestals). Generation stays belief-free
   and direction-agnostic; direction is situational.
3. **Downstream identical.** Each surviving cell gets the same corridor score
   (`exp(−detour/PostCorridorPx)` with its own per-cell detour), the same
   12-bucket progress binning, the same per-bucket top-6 with 32 px
   separation — then rays, ducks, and selection run unmodified.
4. **[P3] Empty-bucket fallback.** A route crossing a large open room can
   leave a progress bucket with no gate-vicinity candidate, where today's
   full scan might find a mid-room wall nub. Proposed: for *empty buckets
   only*, run today's scan restricted to that bucket's progress band
   (bounded, rare, preserves "posts along the whole route"). Alternative:
   accept sparser posts (simpler; overlays will show whether it matters).
   I lean fallback-on, knob `STENCIL_POST_BUCKET_FALLBACK=1`.

**Expected budget:** candidate pool drops from thousands of scanned cells to
~(on-route chokes × ~30 vicinity cells) ≈ low hundreds; the full-grid
distance sweep disappears. Ray/duck stages (unchanged) become the dominant
post cost; giant `post_ms` should land *below* v61's level, not just back to
it. Verified by re-running the giant benchmark + a fresh paired hosted probe.

## 2a. Belief-scored facing at selection time (revised per review)

The per-direction bitmask's first real consumer moves from generation to
**selection**, fed by belief — the sketch's "situational half", verbatim.
James's review killed the static toward-enemy-home facing filter: it is only
valid for the opening advance (enemies drift from their home as the game
progresses), it is outright wrong when carrying home (threats are *behind*
you), and 4-team maps have three enemy pedestals, not an "enemy side."

- New pure helper `facingScore(map, cell, bearings: seq[float]): float` —
  the fraction of the given threat bearings whose quantized sector bit is
  set in `coverDirs[cell]` (no bearings → neutral 0.5, so selection without
  intel is unchanged).
- The extracted pure selection core (§3) gains a facing term:
  `utility += PostFacingWeight * (facingScore - 0.5)` — **[P2]**
  `STENCIL_POST_FACING_WEIGHT`, default 0.15, deliberately modest (same
  magnitude as the existing duck-travel penalty).
- Call sites pass **believed enemy track bearings**: fresh enemy tracks
  within the existing `TrackTtlTicks` staleness window from the caller's
  Belief; bearing = track position → candidate cell. Direction-correct
  everywhere the static filter was wrong: carry-home pursuers behind you
  raise posts covered from behind; each 4-team believed track contributes
  its own bearing regardless of pedestal geometry.
- v63 consumers: `orderPost` and `defensivePostForSeat` via the shared pure
  core. Duck logic and the planner exposure term remain future consumers
  (Layers 3–5).

This makes v63 a *runtime behavior* delta (selection reacts to intel), so
the matched batch judges it; generation itself stays belief-free and
parity-checkable.

## 3. Viewer extension (James's request)

Add posts to `render_topology.py`/`topology_debug.nim`:

- **Static layer (belief-free, exact):** the harness already builds the full
  WorldMap, so it serializes `postFronts` — per front (team→opponent
  dropdown): candidate dots colored by score, selected posts numbered with
  firing rays and the duck-pair link. This directly shows old-vs-new
  candidate sourcing on the same map for the QA gate.
- **Selection layer (belief-parameterized, drift-guarded):** post
  *generation* is init-time and belief-free; *selection* depends on runtime
  belief through three small inputs — the opponent/front, the squad
  directive point, the member rank (or defender seat), and now (§2a) the
  **believed enemy positions**. The viewer makes all of them pointable:
  click the map to set a hypothetical directive point; **shift-click to
  place/remove hypothetical believed enemies** (drawn as red markers); pick
  front and rank from controls. Because the enemy set is a free input, the
  whole-map precompute of the earlier draft no longer covers the space, so
  the viewer mirrors the selection utility in JS (it is ~10 lines: score −
  0.25·dist/searchPx + facingWeight·(facingScore−0.5), separation filter,
  rank pick) — and the drift risk is closed mechanically: the harness runs
  the **real extracted production proc** on **[P4]** ~200 randomized sampled
  cases (front × directive × rank × enemy sets) and embeds inputs+answers;
  the viewer re-runs its mirror on every sample at load and refuses the
  overlay on any mismatch (same fail-closed posture as the topology drift
  guard). A seats slider shows `defensivePostForSeat` assignments (pure,
  harness-computed directly — no mirror needed).

## 4. Validation

- Scratchpad property/parity harness: output-shape invariants (separation
  respected, ducks ≠ pos, counts ≤ configured, determinism); with the
  fallback ON and knobs at defaults, assert every non-empty v62 front stays
  non-empty in v63 on random + corpus maps.
- Corpus overlays: v62-vs-v63 candidate/post renders side by side on the five
  sizes + the batch cells (the new viewer layer is built *first* so the
  before/after is inspectable).
- Giant benchmark: `post_ms` before/after; trace keys unchanged.
- **[P5] Hosted gate:** matched v63-vs-v62 batch, same methodology and cells
  as the v62 batch (re-resolved live), including the paired giant probes for
  `post_ms`. Same scale (12 requests / 58 episodes) unless you want it
  trimmed — post positions shift, so I'd keep full scale.

## 5. Decision summary

| # | Question | Options | Lean |
|---|---|---|---|
| P1 | Gate vicinity radius | 48 px default, env knob | 48 px |
| P2 | Facing term (revised) | belief-scored at selection: `STENCIL_POST_FACING_WEIGHT` default 0.15, tracks within `TrackTtlTicks` | as stated |
| P3 | Empty-bucket fallback | banded legacy scan vs accept sparser posts | fallback on, knobbed |
| P4 | Selection drift guard | ~200 harness-sampled real-code cases, viewer fail-closed on mirror mismatch | as stated |
| P5 | Hosted gate scale | full 58-episode repeat vs trimmed | full |

Build order: viewer post layer → re-sourcing → parity/corpus QA → v63 upload
→ matched batch.
