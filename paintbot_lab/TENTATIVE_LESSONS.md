# CTF tentative lessons — session buffer

**Session started:** 2026-08-11 18:42. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Engine reachability between standable pixels is exactly 4-connectivity on the canStand set
Evidence: Layer 2 design derivation — the engine integrates movement per axis
(Y then X, sim.nim:1898-1899), so a diagonal step needs a standable orthogonal
intermediate; wall-slide only composes axis-aligned sub-steps; a fractional
position's footprint strictly contains an adjacent integer position's, so
subpixel wiggle can't add connectivity. 8-connected labels would over-claim at
diagonal pinches. Generator's ≥26px corridor guarantee makes 4-vs-8 nearly moot
in practice, but 4 is the provably correct choice for the O(1) reachability
contract.
Status: to be property-tested vs brute-force BFS before Layer 2 ships.

### Decouple contract-bearing computations from quality-bearing ones even when one could derive the other
Evidence: Layer 2 proposal — component labels (Layer 4's reachability contract
depends on their exactness) could be read off watershed room labels, but a
watershed bug would then silently corrupt reachability. A standalone 20-line
CCL pass is trivially property-testable; rooms reference components, never
define them. Advisor independently flagged the same split.

### When replacing an authored anchor, check the replacement selection heuristic for the same magic number
Evidence: the obvious "derived" hold-point choke = "choke nearest 45% route
progress" quietly keeps the authored ChokeFraction alive as a selection
heuristic. Presenting progress-matched vs fully-derived (first gate from home)
as an explicit fork, with the tension labeled, instead of silently shipping
either.

### The 8px grid cannot route corridors that pixels can walk — remember when authoring synthetic test maps
Evidence: Layer 2 corridor property test used a 16px corridor: standable at
pixel level, but NO 8px cell center admits the 13x13 footprint, so grid
Dijkstra saw the halls as unroutable and defenseGate correctly fell back.
Generator maps guarantee 26px corridors (always grid-routable); synthetic
test maps must respect that or they test a nonexistent regime. Also a
Layer 3 reminder: the planner is still grid-based until then, so any derived
PoI that gates on route distance inherits grid conservatism.

### Watershed flood + "labeled at own clearance level" makes process visualization free
Evidence: no per-pixel event log needed — rendering pixels with clearance >= L
colored by raw label replays the flood exactly as L sweeps down. The
offline viewer animates a 5.5M-px giant from a 976KB HTML (two label arrays
+ events, zlib+b64, DecompressionStream('deflate') in-browser).

### Offline tool + agent share one Nim implementation; cross-check finals to catch version skew
Evidence: render_topology.py re-runs worldmap.nim via tools/topology_debug on
the agent's logged clearance and refuses to render if recomputed
rooms/chokes/cover/gates differ from the agent-traced finals. First real
agent trace (standard map): zero drift. The trace carries the knob values
(merge depth/ratio, cover rays, gate detour) so the harness reproduces the
agent's env exactly.

### Changing a shared gating input (cover) silently rescales downstream passes — measure them too
Evidence: D3a swapped adjacency-cover for directional cover; the post pass
gates candidates on `map.cover`, so giant post_ms grew ~0.7-1.5s hosted (more
wall-near cells qualify at 24px ray reach than at 8px adjacency). The Layer 2
phase timings alone (~690ms) understated the true init delta; the paired
in-episode v62-vs-v61 probe caught it because both versions' nav_init landed
in the same episode's traces.

### The campaign contract can drift twice in one day — re-resolve at request time, not session start
Evidence: round-967 16x16 hex board re-verified in the morning; by evening the
board events feed recorded "RESTORED to the pre-migration 10x10 square board"
(null map_sizes again, fresh unowned cells). The batch was designed against
the evening live read; morning docs were already stale.

### A paired in-episode probe measures both versions' init on the exact same map for free
Evidence: the giant DEBUG probes seated v62-vs-v61 in one episode; each seat's
trace carries its own nav_init, giving a same-map, same-host, same-contention
init comparison from 2 episodes — far cleaner than cross-referencing separate
arms' timings.

### mapSeed alone reproduces 1v1/2v2 maps bit-exact; 4ffa reproduction drifts slightly
Evidence: self_play --map-seed (added 2026-08-12) rebuilt the batch's h2h, duo,
and giant-probe maps with identical rooms/chokes counts vs hosted nav_init;
the 4ffa cell reproduced same dims and rooms (29) but 110 vs 116 chokes, with
identical (mapSeed, seed) and no wall-relevant config diff. Cause unidentified
— something in the 4-team generator (corner/plus/quadmirror pick?) draws from
another source. Open thread before trusting offline 4ffa map precomputation.
