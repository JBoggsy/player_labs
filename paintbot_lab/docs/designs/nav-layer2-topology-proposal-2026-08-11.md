# Nav rework Layer 2 — topology & PoIs: worked proposal

**Status: APPROVED 2026-08-11 (James), with two additions now folded in:** an
**offline process-visualization tool** (§7a) that replays the watershed flood,
cover potentials, and anchor selection from an agent-logged clearance map, and
**configurable cover ray count, default 16** (§4). On the open forks James
approved the proposal as presented, so the stated leans are adopted: D1 depth +
ratio, D2 bitmask prefilter, D3(a) swap cover now, D4(b) first-gate-from-home,
D5-1 minimal post scope. Original proposal text below, amended in place.
Layer 2 of the [navigation rework sketch](nav-rework-sketch-2026-08-11.md) (§3.2;
open questions Q4/Q5/Q6). Layer 1 (clearance field) shipped as stencil v61 and is
the substrate: everything below is derived from `WorldMap.clearance` (exact L∞
distance-to-wall) and the pixel wall mask at init, and replaces every authored
anchor. Decision points for James are marked **[D1]**–**[D7]** and summarized at
the end.

## 0. Prior art (research note)

This is a solved problem class: decomposing a 2D game map into regions and
chokepoints from a distance transform. The established approaches are
StarCraft-style terrain analyzers (BWTA/BWEM: pruned medial axis, chokepoints as
clearance minima along it) and, equivalently in image-processing terms,
**watershed segmentation of the distance transform** with persistence-based
merging — regions grow from clearance maxima, chokepoints are the saddles where
regions meet, and shallow saddles are merged away. We hand-roll rather than
depend: the player image carries no external libraries, the corpus is one
clearance field we already own, and every piece must be exactly
property-testable in the scratchpad Nim harness. The algorithm choices below
(priority-flood watershed with a bucket queue, union-find persistence merge,
two-pass CCL) are the standard, simple, O(pixels) formulations of that prior
art, not inventions.

## 1. Two tiers, deliberately decoupled

The sketch's three products have different correctness stakes:

- **Reachability (components)** is *contract-bearing*: Layer 4's "unreachable
  goals never reach the planner" rests on component equality being exact.
- **Rooms/chokepoints and cover potential** are *quality-bearing*: a mediocre
  chokepoint gives a mediocre hold point, not a corrupted invariant.

So components are computed by a standalone, trivially-verifiable pass, and the
watershed *references* component labels but never defines them. A watershed bug
can produce ugly rooms; it cannot corrupt reachability.

## 2. Connected components (reachability tier)

**Definition.** Label the standable-pixel set `{p : clearance[p] > PlayerHalf}`
(≡ `canStand` ≡ engine `canOccupy`) under **4-connectivity**, one label per
pixel, `0` = not standable. Classic two-pass CCL with union-find, O(pixels).

**Why pixels, not cells.** Goals are pixel points and `canStand` is
pixel-exact. Cell-resolution labels would need a nearest-walkable-cell snap for
points whose cell center is unwalkable — reintroducing exactly the snap/bias
problem Layer 1 killed. A `uint16` label array on the 6.2M-px giant is 12.5 MB,
which is cheap next to correctness.

**Why 4-connectivity is engine-exact.** The engine integrates movement per axis
(Y then X, `sim.nim:1898-1899`), so any diagonal step decomposes into axis
steps, each requiring `canOccupy` at an intermediate position; wall-slide also
only composes axis-aligned sub-steps. A fractional position's footprint covers
a strict superset of an adjacent integer position's, so subpixel wiggle cannot
create connectivity integer positions lack. Therefore engine reachability
between standable pixels is exactly 4-connectivity on the `canStand` set —
8-connectivity would over-claim (a diagonal-only pinch is not traversable
without a standable orthogonal intermediate). In practice the generator's
≥26px corridor guarantee (`arena.nim:1245`) makes 4-vs-8 almost moot; 4 is the
one that is *provably* right.

**API.**

```nim
# WorldMap additions
component*: seq[uint16]        # per pixel; 0 = not standable
componentCount*: int

proc componentOf*(map: WorldMap, p: Point): int   # 0 when not standable
proc sameComponent*(map: WorldMap, a, b: Point): bool  # the O(1) query
```

Nothing consumes `sameComponent` until Layer 4; it ships now because the
watershed and the validation harness want it, and because it is the cheapest
part of the layer to get provably right early.

## 3. Rooms and chokepoints (quality tier)

**Algorithm: priority-flood watershed on the clearance field.**

1. **Seeds** = local maxima of clearance over standable pixels, one seed per
   maxima *plateau* (flood-fill each flat maximal region, take one
   deterministic representative — lowest pixel index — as the room's `peak`).
2. **Flood** all standable pixels in decreasing clearance order using a
   256-bucket queue (clearance is `uint8` → exact O(pixels), no heap). Each
   popped pixel takes the room label of the neighbor that enqueued it;
   deterministic FIFO order within a bucket, fixed neighbor order.
3. **Saddles**: when a pixel pops with ≥2 distinct labeled rooms among its
   neighbors, that pixel is a boundary contact. The *first* contact between a
   given room pair in flood order has the highest clearance on their shared
   boundary — that pixel is the pair's **chokepoint** (the widest point of the
   narrowest crossing, i.e. the gate), and its clearance is the gate's L∞
   half-width. Record one saddle per room pair (first contact wins); the pixel
   itself joins the earlier-labeled room so `roomLabel` stays a partition.
4. **Persistence merge**: raw watersheds over-segment (every bump in an open
   hall becomes a "room"). Process saddles in decreasing clearance with
   union-find: merge the pair when
   `min(peakA, peakB) - saddleClearance < mergeDepth` — i.e. the constriction
   is not materially narrower than the smaller room's own width, so it is not
   a real gate. Survivor keeps the higher peak. Surviving saddles are the
   final chokepoints; surviving roots are the final rooms. Working labels are
   `int32` during flood/merge and compact to `uint16` afterwards.

**[D1] Merge criterion & default.** I propose depth-based persistence
(`mergeDepth`, default **4 px**, env `STENCIL_TOPOLOGY_MERGE_DEPTH_PX`) plus a
relative floor (also merge when `saddleClearance >= 0.8 * min(peakA, peakB)` —
env-tunable ratio) — depth catches noise in narrow areas, the ratio catches
"two halves of the same big hall". Both defaults are educated guesses to be
tuned against render overlays across the corpus (§7), not pre-registered
truths. Alternative: depth-only (one knob, simpler story). Your call on
one-knob vs two.

**Flooding respects walls**, so rooms never span components; each room records
its component, and the room adjacency graph (rooms as nodes, chokepoints as
edges) is connected within each component — a property test.

**Data model.**

```nim
type
  Choke* = object
    pos*: Point            # saddle pixel: widest point of the gate
    clearance*: int        # L∞ half-width of the gate
    roomA*, roomB*: int

  Room* = object
    peak*: Point           # clearance local max — the room's PoI point
    peakClearance*: int
    area*: int             # standable pixels
    component*: int
    chokes*: seq[int]      # edge indices

# WorldMap additions
roomLabel*: seq[uint16]    # per pixel; 0 = not standable
rooms*: seq[Room]
chokes*: seq[Choke]
```

Room `peak`s are the sketch's "room/open-area nodes" (local maxima of
clearance); this graph is the future top level if Layer 3 goes hierarchical
(sketch Q1), so `rooms_n`/`chokes_n` land in the trace per episode to build
the node/edge-count table by map size.

Memory: two per-pixel `uint16` arrays (component + roomLabel) ≈ 25 MB on the
giant, next to the existing 6.2 MB clearance and 6.2 MB wall arrays.
Negligible against the image's Python-era footprint, but stated for the
record.

## 4. Cover potential (Q5)

**Definition.** Per walkable 8px cell, an N-sector bitmask (**N configurable,
default 16**, env `STENCIL_COVER_RAYS`, stored as `uint16`, 1–16 rays): bit
*k* set iff a ray from the cell center at angle `k·2π/N` hits a **real,
in-bounds wall pixel** within `coverRayPx`. Two deliberate semantic choices:

- Rays test the **wall mask** (projectile/LOS semantics), not clearance —
  cover is about what blocks *shots*, and shots are points, not footprints.
- **Map-boundary exits do not count as blocked.** No shooter can stand outside
  the map, so edge adjacency is worthless protection — this is precisely the
  "next to an obstacle ≠ cover" review point, encoded. (A one-line caveat: a
  shooter also can't stand *behind* an interior wall that hugs the boundary,
  so a thin border wall still counts as cover here; the situational
  enemy-direction check makes that harmless — no believed enemy will ever be
  in that sector.)

**Resolution & cost.** 8px cells (≤97k on the giant), 16 rays × ~`coverRayPx`/2
samples: low single-digit ms. Cell resolution matches every current cover
consumer; pixel-resolution cover buys nothing because the situational half
(scoring against believed enemy directions) is angular, not positional.

**[D2] Cover ray radius.** Default `coverRayPx = 24` (≈ PlayerHalf ×4: hug
distance at which a wall shadows a usefully wide angular sector), env
`STENCIL_COVER_RAY_PX`. The 8-sector approximation degrades for shooters far
off the sector axis; that is accepted for Layer 2 — posts keep their
sampled-ray scoring (`forwardRayEnds`) for fine work, and Q5's "do posts need
sampled-LOS scoring?" is thereby answered *"they keep it"*: the bitmask is the
cheap precomputed prefilter and the duck/peek/exposure consumers' runtime
check is directional. If you want sampled-LOS cover *fields* instead, that is
a much bigger compute and I recommend against it at this layer.

**[D3] What happens to the old adjacency-cover.** The kill list retires "the
current cover definition" (walkable cell with ≥1 blocked 8-neighbor —
includes map edge). Its consumers today: `nearestCover` (defender hold-point
snap, squad spread, advance-point fallback), `spawnCoverPoint`
(early-defense), and post candidate gating. Options:

- **(a) Swap now** — redefine `cover[cell] = coverDirs[cell] != 0`. Same
  shape (`seq[bool]`), all consumers move together, map-edge fake cover dies
  immediately. One more behavioral delta inside the same A/B version.
- **(b) Keep adjacency-cover for existing consumers** until each dies in
  Layers 3–5; new code only reads `coverDirs`. Zero behavioral risk now, but
  two cover truths coexist and the fake-edge-cover bug lives on.

I recommend **(a)**: the membership change is small (edge-adjacent open cells
drop out; wall-near-but-not-adjacent cells within the ray radius join), it is
exactly the review point this layer exists to fix, and the matched batch
measures it. If you want attribution isolation instead, (a) behind
`STENCIL_COVER_DIRECTIONAL=1` (default on, v59-style confound gate) is the
middle path.

## 5. Replacing the authored anchors

`rallyPoint`/`pastRally`/`axisPoint`: `pastRally` is already dead code and
`rallyPoint` is trace-only — both delete outright (trace drops the field).

`chokePoint(color)` has exactly **one** gameplay consumer:
`holdPointForSeat` (`roles.nim:15`) — the defender hold base, today "45% along
the home→center axis, snapped to adjacency-cover". Its replacement draws from
the real choke list, but *which* choke is a genuine fork:

- **[D4a] Progress-matched (small swing).** Among chokes on the min-detour
  route home→nearest-opponent-home (on-route test via the already-cached home
  Dijkstra fields: `fromHome + toEnemy − direct ≤ ε`), pick the one whose
  route progress is nearest 0.45. Lands defenders roughly where they stand
  today, but snapped to a real gate. **Honesty note: this keeps the authored
  45% alive as a selection heuristic inside a "derived" PoI** — it cuts
  against the kill list's spirit even though the *point* is now map-derived.
- **[D4b] First significant gate from home (fully derived).** The on-route
  choke nearest home outside the home room — "defenders hold the entrance to
  our base region". No authored number survives. Likely a bigger positional
  swing (closer to home than today's 45%), so a bigger behavioral delta to
  eat in one version.

I lean **[D4b]** — the rework's stated point is killing authored anchors, and
the matched batch exists to catch a bad swing — but this is your fork.
(Opponent choice for multi-team: the opponent with the shortest home→home
route distance, i.e. the most immediate approach; 2-team collapses to the
only opponent.)

## 6. Post rebuild scope (Q6)

Menu, smallest to largest:

- **[D5-1] Compute + anchors only (recommended for v62).** Layer 2 lands as
  §2–§5: topology computed, traced, rendered; `chokePoint` consumer swapped;
  cover per [D3]; the post pass keeps its current bespoke scan untouched.
  Surgical diff, clean attribution, posts rebuilt next version once we have
  looked at real overlays of rooms/chokes/cover across the corpus.
- **[D5-2] + re-source post candidates.** *(Ruled GO 2026-08-12 — worked
  plan: [nav-post-resourcing-v63-2026-08-12.md](nav-post-resourcing-v63-2026-08-12.md).)* Keep `PostFront`/`PostCandidate`
  outputs, scoring, dedup, and duck logic identical, but gate candidate
  generation on directional cover facing the enemy approach (instead of
  adjacency cover) and seed candidate buckets from choke/room PoIs near the
  route instead of the full-grid stride scan. Medium diff; posts likely
  improve for free, but attribution muddies.
- **[D5-3] Full rethink** of defender assignment / squad orders consuming the
  PoI graph. **Recommend against now**: squad *decision* logic is an explicit
  rework non-goal, and Layers 3–5 will reshape what posts even feed.

My recommendation: **[D5-1] now**, decide on [D5-2] after corpus inspection —
it stays available as a cheap v63 with the same matched-batch methodology.

## 7. Budget, telemetry, and validation

**Budget — MEASURED (2026-08-11, implemented).** All Layer 2 compute is
init-time and O(pixels): CCL one pass; watershed one bucket-queue pass; merge
saddle-bounded; cover cell-bounded. Uncontended scratchpad benchmark on a
synthetic 6.2M-px giant: component 34 ms, topology 148 ms, cover 36 ms.
Real-corpus numbers under full per-seat process contention (16 seats, or 32
for ffa8), from `self_play --profile-nav-init` — the honest number is ~3× the
original "comparable to clearance" guess, with topology dominating:

| size | px | rooms | chokes | clearance | component | topology | cover | seat total |
|---|---|---|---|---|---|---|---|---|
| small | 588k | 9 | 18 | 27 ms | 9 ms | 38 ms | 13 ms | 113 ms |
| standard | 814k | 10 | 25 | 39 ms | 13 ms | 54 ms | 19 ms | 181 ms |
| large | 1.38M | 16 | 57 | 69 ms | 23 ms | 93 ms | 36 ms | 356 ms |
| huge | 2.64M | 27 | 111 | 133 ms | 45 ms | 197 ms | 69 ms | 869 ms |
| giant 1v1 | 5.5M | 49 | 228 | 283 ms | 102 ms | 435 ms | 153 ms | 2362 ms |
| giant 4ffa8 | 6.2M | 37 | 152 | 321 ms | 115 ms | 475 ms | 194 ms | 5119 ms |

(rooms/chokes = the Q1 node/edge counts; all maps one component. Giant 1v1
seat total grew from v61's ~1.5–1.9 s; 4ffa8-giant's 5.1 s is dominated by
the pre-existing 3-front post pass at 3.9 s. Trace keys `component_ms` /
`topology_ms` / `cover_ms` + `components_n`/`rooms_n`/`chokes_n` ship in
`nav_init`; `self_play.py` plumbed like `clearance_ms`.)

**Property tests (scratchpad Nim harness vs brute force, Layer 1 style).**

1. Component labels ≡ brute-force BFS 4-connectivity on the `canStand` set —
   exhaustive equivalence on randomized small maps (the contract test).
2. `roomLabel` partitions the standable set; every room 4-connected; every
   room's `peak` attains its max clearance; rooms never span components.
3. Every choke's `pos` lies on the boundary of exactly its two rooms;
   `saddleClearance ≤ min(peakA, peakB)`; per surviving room pair the
   recorded saddle has max clearance among their boundary contacts (checked
   brute-force on small maps).
4. Post-merge graph consistency: room adjacency graph connected within each
   component; no choke references a merged-away room.
5. Determinism: same map → identical labels/rooms/chokes across runs.
6. Cover bitmask ≡ brute-force reference rays on random maps, including the
   map-edge-not-cover and boundary-clamp cases.

**Visual QA (the Q4 quality bar).** Extend the `STENCIL_TRACE_NAVIGATION`
payload with rooms (peak, peakClearance, area), chokes (pos, clearance, room
pair), and the cover bitmask grid; extend `tools/render_nav.py` with three
overlays: tinted room regions, choke gates drawn as width-scaled bars, and a
per-cell cover rose. Run `self_play.py --visualize-nav` across all five map
sizes (the corpus procedure Layer 1 used), eyeball chokepoint/room quality,
tune `mergeDepth`/ratio knobs, and record the rooms/chokes counts per size in
the version log.

### 7a. Offline process visualization (James's addition)

Beyond the final-result overlays, an offline tool replays the *process* —
flood fill, merging, cover, anchor selection — from data the agent actually
generated. Architecture (single algorithm source of truth, no Python
reimplementation that could drift):

- **Agent side:** the nav trace logs the clearance field itself, once per
  episode, delta-packed (clearance is 1-Lipschitz along a row, so per-row
  2-bit `{-1,0,+1,escape}` symbols + `std/base64` ≈ 1.5–2 MB on the giant,
  within the existing opt-in `STENCIL_TRACE_NAVIGATION` payload family),
  plus the final rooms/chokes/cover/anchors it computed.
- **Nim debug harness** (`tools/topology_debug.nim`, `expand_replay_json.nim`
  pattern): imports the *same* `worldmap.nim`, reads the logged clearance
  dump, re-runs CCL + watershed + cover + anchor selection, and emits process
  artifacts as JSON: the **pre-merge** label array, the final label array,
  seed list, per-pair saddle contacts with levels, every merge decision
  (pair, saddle clearance, depth, ratio, verdict), per-cell cover bitmask,
  and the anchor scoring table (per-choke fromHome/toEnemy/detour/qualified +
  the chosen gate and fallback path).
- **Key trick — the flood needs no per-pixel event log:** pixels are flooded
  in decreasing clearance order, so a pixel is labeled exactly when its own
  clearance level is reached. Rendering "all pixels with `clearance ≥ L`,
  colored by raw label" as `L` sweeps 255→7 replays the watershed exactly,
  from just the two label arrays.
- **Viewer** (`tools/render_topology.py`): compiles/runs the harness,
  **cross-checks the harness's final rooms/chokes against the agent-traced
  finals** (drift guard: the tool refuses to render a mismatch silently),
  and emits a self-contained HTML page: clearance-level scrubber animating
  the flood with saddle/merge events appearing at their levels, a merged
  vs unmerged room toggle, cover-rose overlay per cell, and the anchor
  selection table with the winning gate highlighted on the map.

**Hosted gate.** Matched vNEW-vs-v61 arms per the Layer-1 methodology: live
round-967-lineage board cells re-resolved at run time, identical pinned
rosters, both seatings, 1v1 giant cell for init-time stress, ops-filter on
error_type/status only, and trace-level behavior diffs (objective mix, micro
mix, duck%, backoff, plus the new phase timings) — not just win rate. With
[D5-1] scope the expected behavioral delta is confined to defender hold
points (+ cover membership if [D3a]), so the trace diff should show exactly
that and nothing else.

## 8. Decision summary

| # | Question | Ruling (2026-08-11) |
|---|---|---|
| D1 | Watershed merge criterion | depth + relative ratio, both env-tunable, corpus-tuned |
| D2 | Cover model | bitmask prefilter, **16 rays default, configurable** (`STENCIL_COVER_RAYS`); posts keep sampled rays |
| D3 | Old adjacency-cover | (a) swap all consumers now |
| D4 | Hold-point choke selection | (b) first significant gate from home (fully derived) |
| D5 | Post rebuild scope | (1) compute + anchors only; revisit (2) after corpus overlays |
| D6 | Component labels | pixel-res 4-connected standalone CCL, as specified |
| D7 | Ship shape | one version (v62), matched-batch gated; plus the §7a offline process visualizer |
