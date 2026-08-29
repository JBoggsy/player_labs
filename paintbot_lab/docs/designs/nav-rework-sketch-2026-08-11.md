# Stencil navigation rework — rough sketch

**Status: rough sketch, 2026-08-11.** General shape only; open questions are listed, not
resolved. Inputs: the
[navigation deep-dive report](../reports/stencil-navigation-deep-dive-2026-08-08.md) and
James's 41 review comments on it (2026-08-10/11). This document will graduate into a full
design doc once the open questions below are settled.

> **EXECUTED (final status 2026-08-29): the rework this sketch governs is
> COMPLETE.** All five layers shipped and were accepted on matched hosted
> batches: Layer 1 = v61 (clearance, 2026-08-11), Layer 2 = v62 (topology,
> 08-11), Layer 3 = v65 (planner, 08-13), Layer 4 = v66 (Intent contract,
> 08-13), Layer 5 = v68 (bounded follower, 08-14), with the post work v63/v64
> and the v67 atlas alongside. v68 was submitted 2026-08-14 and is the live
> champion. The §9-series status addenda below run through Layers 3-4; the
> v67/v68 close-out follows them. The sketch never graduated into a separate
> full design doc — the per-layer docs served that role.

## 1. Requirements distilled from the review

Grouped by theme; each traces back to comments on the deep-dive report.

**One planner.** Exactly one route planner for all navigation. Flow fields stop being a
second way to navigate; if they survive at all, they *inform* the single planner (shared
distance oracle / heuristic), they are never followed directly. Direct steering is not a
sanctioned third planner. The `Intent.planner` field proposed in the report's H1 is dropped —
there is nothing to select.

**No beelining, anywhere.** Intent picks the point; nav routes to it. All five direct-steer
paths (§6 inventory below) go through the planner.

**Unreachable goals never reach the planner.** An unroutable goal today either freezes the
agent (flow) or beelines it (A*). Both are symptoms of the same bug: strategy handed nav a
goal nobody validated. Goal selection must emit only walkable, reachable points; the
planner may then treat "no path" as a hard internal error worth loud telemetry, not a
condition to paper over.

**No 8px coarsening for movement.** The eroded 8px grid goes away as the movement
representation. Cell coordinates survive only as the comms/telemetry unit (shout formats,
trace schema). Pathfinding efficiency is bought with better algorithms, not lower
resolution. This also kills the class of problems the coarsening created: the
`nearestWalkable` snap and its up-left bias, and the grid-vs-pixel disagreement between the
two segment predicates.

**Dynamic PoIs, not authored anchors.** All the axis-percentage anchors (`chokePoint` at
45%, `rallyPoint`/`pastRally` at 65%) are stripped. Points of interest — chokepoints, room
centers, cover-rich posts — are computed from the walkability map itself.

**Kill the threat axis.** The concept is outdated; remove it and everything keyed on it.

**Rework cover.** "Walkable cell with ≥1 non-walkable 8-neighbor" is not cover — it is
"next to an obstacle," including the map edge. Cover has a precomputable part (wall
proximity *with direction*) and a situational part (where the believed enemies are).

**Stuck handling: keep, but lightweight.** A perfect nav stack never gets stuck; ours
won't be perfect, so keep a watchdog — but the bigger it gets, the more it hides primary-stack
bugs. Progress test → one replan → loud telemetry. No escalating jitter ladder.

**Movement should be smarter than goal-point + shortest path.** `carry_home` today follows
the flow field with only local micro; interception, escort, and hunt A* straight at their
targets. Evasion, cover, and ally proximity should shape routes — which in a single-planner
world means they live in the cost function, not in per-objective steering hacks.

**belief.danger stays for now.** Reversing the report's H3: what it likely tracks is
*believed enemy locations*, not danger per se. Keep as-is, add a TODO to experimentally
validate the semantics before promoting it into any cost function. The new danger cost term
is specified against believed enemy *tracks* directly, not against this grid.

**WorldMap becomes immutable.** The per-tick pedestal rewrite leaves WorldMap; anything
dynamic (pedestal positions, steal/capture detection inputs) moves to belief state.

**Note the engine invariants.** walkMask/wallMask are written as exact complements but
nothing promises they stay that way — document it where `map.wall` is built. The
spinning-diamond staleness (init-only sprite, live restamps, diamonds unmarked) is accepted
as unfixable client-side with the current wire contract.

## 2. Goals and non-goals

**Goals**

- One planner, one walkability predicate, one authoritative map representation.
- Pixel-exact correctness everywhere; resolution is a performance knob, never a
  correctness compromise.
- Route quality (danger, cover, hazards) expressed as costs in that one planner.
- Strategy emits validated goals; nav trusts its inputs.
- Structured `Intent` type; the seven reason-string lists die.
- Derived, map-driven PoIs replacing all authored anchors.

**Non-goals (this rework)**

- Fire-windup micro cleverness (strafe/aim during windup, trigger-in-cover-then-peek) —
  recorded as a TODO, explicitly out of scope.
- Changing squad *decision* logic (who goes where and why). Squads keep their brains;
  they just express movement through the new goal contract and consume the new PoIs.
- Engine changes (diamond marking, mask invariant enforcement server-side).
- belief.danger semantics validation — separate experiment.
- Strategy-layer improvements flagged in review, deferred: the broader strategy-logic
  look that the `early_defense`/post rework points at, grenade evacuation as a proper
  strategy-or-reaction, smarter escort extrapolated fixes, and moving candidate scoring
  to behavior-trigger time instead of nav time. This rework only changes how those
  behaviors express and validate their goals.

## 3. Architecture sketch

Five layers, strictly ordered: each consumes only the layers below it.

```
strategy / squads / fight        (what to do)
        │  validated Goal + intent profile
        ▼
[4] Intent & goal contract       (typed Intent; goals pre-validated)
        ▼
[3] The planner                  (one weighted A*-family search)
        ▼
[2] Topology & PoI layer         (components, chokepoints, rooms, posts, cover potential)
        ▼
[1] Clearance field              (L∞ distance transform; THE walkability predicate)
        ▼
[0] Pixel wall mask              (decoded once from player init; immutable)
```

### 3.1 Layer 1 — the clearance field (one predicate to rule them all)

The engine's ground truth is `canOccupy(x,y)`: the 13×13 **square** footprint
(half-extent `PlayerHalf = 6`) must be entirely on walkable floor (`sim_state.nim`,
verified against the cached source). A square footprint means the exact analogue is an
**L∞ (Chebyshev) distance transform** of the wall mask, computed once at init:

- `clearance[x,y]` = L∞ distance to the nearest wall pixel (out-of-bounds counts as wall).
- **Point walkability** = `clearance[x,y] > PlayerHalf` — one array read that *is*
  `canOccupy`, bit-for-bit. Not conservative, not approximate.
- **Segment walkability** = DDA over the same field. This single primitive replaces both
  `walkableSegment` (pixel-exact but ~length/2 × 169 reads) and `walkableNavSegment`
  (cheap but conservative): it is as cheap as the DDA *and* as exact as the footprint scan.
  The "they disagree at the margins" problem is not fixed — it is dissolved; there is
  nothing left to disagree.
- `rayClear` (point-sized LOS for aim/vision/throw) stays as-is — the report confirmed all
  12 call sites genuinely want point LOS, and it reads the wall mask, not clearance.

An L∞ transform is O(pixels) (two-pass chamfer-style). Even the 4-team giant (~6.2M px)
should be tens of ms in Nim; see §7 for budgets.

Trenches, puddles, and barriers remain invisible to *walkability* (correct: barriers block
paint, not movement; trenches/puddles are passable) — they enter as **costs**, not walls
(§3.3).

### 3.2 Layer 2 — topology and PoIs, derived from the map

> **Worked proposal (2026-08-11, awaiting ruling):**
> [nav-layer2-topology-proposal-2026-08-11.md](nav-layer2-topology-proposal-2026-08-11.md)
> — resolves Q4 (watershed on clearance + persistence merge, render_nav corpus QA),
> Q5 (8-sector wall-mask bitmask, in-bounds hits only), and frames Q6 as a scope menu.

Everything here is computed from the clearance field at init, replacing every authored
anchor:

- **Connected components** of the walkable region (`clearance > PlayerHalf`), labeled once.
  Reachability between any two points becomes an O(1) label comparison — this is what makes
  the "unreachable goals never reach the planner" contract cheap to enforce.
- **Chokepoints**: local minima of clearance along the walkable region's skeleton/medial
  axis (the ridge of the clearance field). Replaces `chokePoint(color)`.
- **Room/open-area nodes**: local maxima of clearance (large open areas), giving a sparse
  PoI graph: rooms connected through chokepoints. This graph is what hierarchical planning
  (if adopted, §8 Q1) would search at the top level, and what squads draw
  posts/advance/rally points from.
- **Cover potential** (precomputed half): per-cell *directional* wall proximity — an 8-sector
  bitmask of "shots from this direction are blocked by nearby standable-adjacent wall."
  Adjacency alone is explicitly not cover. The situational half — scoring a candidate
  against currently-believed enemy positions — is computed at use time by consumers (post
  selection, duck logic, the cost function's exposure term).
- **Tactical posts**: the firing/duck-post pass gets rebuilt on top of the above (candidate
  posts = cover-potential cells near chokepoints/rooms facing likely approach directions)
  rather than its current bespoke scan. Scope of that rebuild: open question (§8 Q6).

### 3.3 Layer 3 — the planner (the only one)

One planner: **weighted A\* over a uniform lattice on the pixel map**, with:

- **Node validity** from the clearance field (pixel-exact at any lattice step — the lattice
  spacing affects path granularity and search size, never correctness).
- **Cost function** = distance × terrain multiplier + soft penalties:
  - terrain: trench ×5 (matches engine climb-out speed), active puddles (per the GV41
    hazards recon's prescription),
  - danger: proximity to believed enemy tracks (from belief tracks directly — *not* the
    unvalidated danger grid),
  - exposure: sightline exposure to believed enemy positions, using cover potential,
  - cohesion (optional, per-intent): mild discount toward allies/carrier.
- **Per-intent cost profiles**: a small weights bundle on the Intent (carrier: danger high;
  hunter: danger low; default: mostly geometric). This is where "carry_home should evade"
  lives — same planner, different weights, no per-objective steering code.
- **Admissible heuristic**: plain geometric distance always works. For the handful of
  *stable* shared goals (team homes, own capture point, and — once layer 2 exists — the
  derived PoIs, a bounded static set), the existing cached Dijkstra
  fields survive in exactly one role: a **true-distance heuristic / distance oracle**.
  Geometric Dijkstra distance lower-bounds any cost function that only *adds* penalties on
  top of distance, so it is admissible for the weighted search — this is the precise sense
  in which "flow fields inform per-agent A*." They are never followed directly, and they
  are minted only for the fixed goal set at init — the unbounded field-minting problem
  (pedestal-driven, report M2) dies with WorldMap immutability.
- **Replanning**: cached path per agent, invalidated by goal movement or watchdog. Moving
  targets (pursuit, interception) replan on a short cadence rather than steering directly.
  Cadence and whether we need incremental replanning: open question (§8 Q3).

JPS was considered and is likely out: it requires a uniform-cost grid, and the cost terms
above are the point of the rework. Hierarchical A* (PoI graph at the top, lattice
refinement locally) is the fallback if flat weighted A* misses budget on giant maps —
decision deferred to benchmarks (§8 Q1).

### 3.4 Layer 4 — the Intent and goal contract

```nim
Intent = object
  reason: string          # telemetry only; NOTHING dispatches on it
  goal: Vec2              # pre-validated: walkable AND same component as agent
  arriveRadius: float
  costProfile: CostProfile  # per-intent planner weights (§3.3)
  micro: MicroFlags       # typed permissions: sidestep, separation, peekDuck...
  clampToEndzone: bool    # the former reason-string special cases, as fields
```

- **Goal selection is reachability-aware from the start.** Candidate generation filters
  by component label (O(1)) and walkability *before* scoring — validation is part of
  selecting the goal, not a post-hoc snap on the way into nav. Helpers provided to
  strategy: `nearestReachable(p, from)` (true nearest via BFS ring on the clearance
  field, within `from`'s component — unbiased, replacing `nearestWalkable`'s row-major
  up-left bias). Grenade evacuation, escort extrapolation, spray-flee candidates: all
  select this way before becoming an Intent.
- If strategy cannot produce a reachable goal, *strategy* picks a different objective.
  The planner receiving an unreachable goal is a bug and logs as one.
- All seven reason-string lists are deleted; their semantics become the typed fields above.
- `early_defense` is scrapped as a reason: it becomes ordinary post/hold-point logic in
  strategy using layer-2 posts. `barrage_center`'s raw map-center hold likewise becomes a
  scored PoI selection (safest reachable open-area node, not literal center).

### 3.5 Layer 5 — following and micro

- Waypoint follower on the planned path (unchanged in spirit).
- Micro modifiers (separation, sidestep, peek/duck) are **bounded**: they may perturb
  motion within a corridor around the planned path, never replace the route. Sidestep
  validation uses the segment-DDA primitive.
- **Stuck watchdog**: progress test (as today) → single forced replan with a temporary
  cost bump on the blocked edge → if still stuck, loud trace event. No 90° jitter ladder;
  the jitter's real function today is masking beelines and stale-mask collisions, both of
  which this design removes or accepts-with-telemetry (diamonds).

## 4. Kill list

Removed outright: the flow-following planner path and `Objective.flowGoal`; direct/beeline
steering (all sites, §6); `walkableSegment` and `walkableNavSegment` (subsumed by the
clearance DDA); the eroded 8px grid as movement truth; `nearestWalkable` and its snap
(replaced by strategy-side `nearestReachable`); all seven reason-string dispatch lists;
threat axis and everything keyed on it; `chokePoint`/`rallyPoint`/`pastRally` and the
axis-percentage anchor scheme; `early_defense` as an intent reason; the current cover
definition; WorldMap pedestal mutation; dead code from report Appendix B
(`pastRally`, `insideBase`, `walkabilityDecodeMs`, `distanceAt`).

Kept: `rayClear` (all 12 sites); cached Dijkstra fields for the fixed stable-goal set, as
heuristic/oracle only; belief.danger (as-is, pending validation); 8px cells as
comms/telemetry coordinates; the parity corpus idea (needs a rebuilt harness, §8 Q8).

## 5. What happens to each beeline

| today | fate under this design |
| --- | --- |
| Spray (arc) pursuit overwrites movement with a direct octant at the enemy (action.nim:501-506) | pursuit is an Intent with a fast-replan moving goal; planner routes every repath |
| Grenade evacuation emits an unclamped radial point (strategy.nim:242-245) | evacuation candidates filtered through `nearestReachable` + component check before Intent |
| Escort-carrier extrapolated fix (strategy.nim:288-292) | extrapolated point validated the same way; if unreachable, snap to nearest reachable |
| `clear_spray` winner steered directly after grid-validating candidates | candidates scored, winner becomes a validated Intent goal, planner routes |
| Unroutable A* goal → raw-goal beeline + retry every tick | cannot occur: goals are pre-validated; planner failure = logged bug |

## 6. Numbers that will drive the open decisions

Map sizes (report Appendix C, `arena.nim:1350-1375`): 1050×560 to 3211×1713 px (2-team),
up to 2496×2496 (4-team). Lattice node counts by step:

| step | smallest 2-team | largest 2-team | 4-team giant |
| --- | --- | --- | --- |
| 1 px | 588k | 5.50M | 6.23M |
| 2 px | 147k | 1.38M | 1.56M |
| 4 px | 37k | 344k | 390k |
| 8 px (today's grid) | 9.2k | 86k | 97k |

Budgets: the 2026-08-03 init profile (Python-era stencil) measured 453.5 ms worst-case
startup on giant maps, Dijkstra 81.8% of it; the Nim port is far faster but has not been
re-profiled — the rework adds an init distance transform + component labeling + skeleton/PoI
extraction, so a Nim init re-baseline is an early task. Per-tick: today's planner work is
effectively free (cached fields + rare A*); the new steady-state cost is per-agent weighted
A* at replan cadence. A 4px lattice (~390k nodes worst case) with a strong heuristic is very
likely affordable per replan in Nim; 1-2px needs benchmarks or hierarchy. Note 4px is *not*
a return to today's coarsening problem: validity stays pixel-exact via the clearance field —
the step only quantizes waypoint placement.

## 7. Invariants and accepted risks

- **walkMask/wallMask complement invariant**: relied upon (fire gate + LOS share one mask);
  documented with a one-line comment where `map.wall` is built; a cheap init-time assert if
  the wire format ever exposes both.
- **Spinning-diamond staleness**: accepted. Diamonds are not marked in the init sprite and
  restamp the live masks every frame; no client-side fix exists under the current wire
  contract. Mitigation is the stuck watchdog + a trace counter so staleness collisions are
  at least *visible*. (Possible soft mitigation if diamond positions turn out to be
  labeled/observable: small cost bloom around them — open question §8 Q7.)
- **Engine wall-slide physics**: unchanged; the follower still benefits from it but no
  longer depends on it to escape beeline collisions.

## 8. Open questions

1. **Search algorithm & lattice step.** Flat weighted A* at 2-4px with Dijkstra-oracle
   heuristics, vs hierarchical (PoI graph + local refinement)? Needs a Nim microbenchmark
   on the giant map: init transform time, per-replan time at 1/2/4px, memory.
2. **Cost function terms and weights** — and how many per-intent profiles actually earn
   their keep (start with 2-3: default, carrier, hunter?).
3. **Replan cadence for moving goals** (pursuit/interception): fixed N ticks, or
   goal-moved-by-X? Is incremental replanning (D*-lite-style) ever warranted, or is plain
   re-search cheap enough?
4. **PoI extraction method and quality bar**: skeleton/medial-axis vs room-flood
   decomposition; how to validate chokepoint quality across the map corpus (render_nav.py
   overlay is the obvious inspection tool).
5. **Cover model detail**: is the 8-sector precomputed bitmask + runtime enemy-direction
   check enough, or do posts need sampled-LOS scoring? How does this feed duck/peek?
6. **Post-generation rebuild scope**: minimal (same outputs, new inputs) or a real rethink
   of defender assignment/squad orders consuming the PoI graph?
7. **Dynamic overlays**: exact cost shapes for trenches/puddles (bounding-box labels are
   loose), whether barrier belief (v59) should shape *fire-lane* choices, and whether
   diamond regions are identifiable enough to cost-bloom.
8. **Validation harness**: the Python-parity corpus no longer runs (missing engine cache);
   what replaces it — trace-replay behavior diffs? scripted scenario suite? — before we
   trust a rework this large, plus hosted A/B as the final gate.
9. **Comms coupling**: confirm nothing but shout formats and trace schema consumes 8px
   cells once the grid is demoted (grep census before deletion).
10. **belief.danger validation experiment** (separate TODO): does it empirically track
    believed enemy locations? Decides its long-term fate; nothing in this design depends
    on the answer.

## 9. Layer 1 status addendum (2026-08-11)

**Layer 1 is implemented, shipped, and hosted-validated as stencil v61**
(v60 = first cut, superseded; see `VERSION_LOG.md` for full evidence). What
shipped matches §3.1 with one design-relevant amendment:

- The clearance field, `canStand`, and the supercover `segmentClear` landed as
  designed; the nav grid is now derived from clearance (hosted-verified
  bit-identical `walkable_cells` on every map incl. the 5.5M-px giant) and the
  SAT erosion is deleted. Giant-map clearance init: 60–100 ms one-time.
- **Wall-slide amendment (feeds layer 5):** validating the four micro-nudge
  call sites (sidestep, stance, formation bias, separation) with the *exact*
  test regressed gameplay measurably — duck time +3.7pp, 10W–23L vs paired
  v59 — because the engine's forgiving wall-slide executes slightly-clipping
  nudges the exact test rejects. Micro-nudge validity must not exceed
  engine-movement fidelity. v61 restores the old 2px-sampled acceptance
  bit-for-bit via `nudgeClear` (canStand at 2px samples, ~1/169th the old
  cost) and went 13W (+16) vs paired v59's 10W (+4) at n=32/arm, 0 ops
  failures across 130 episodes. Layer 5's follower/micro design should treat
  "engine-executable under slide" — not "footprint-clear along the exact
  line" — as the acceptance bar for bounded micro perturbations.

## 9a. Layer 2 status addendum (2026-08-11, same day)

**Layer 2 is implemented and uploaded as stencil v62** (inert, not
submitted; hosted matched batch vs v61 in flight at write time — see
`VERSION_LOG.md`). Built per the approved
[worked proposal](nav-layer2-topology-proposal-2026-08-11.md) (rulings
D1–D7 recorded there): engine-exact 4-connected pixel components
(reachability tier for the Layer 4 contract), priority-flood watershed
rooms/chokepoints with persistence merging (quality tier, deliberately
decoupled), 16-ray directional cover with map-edge-not-cover semantics
replacing adjacency cover everywhere, and `defenseGate` (first significant
on-route gate) replacing `chokePoint`; rally anchors deleted. Q4 answered
(watershed + render_topology corpus QA), Q5 answered (bitmask prefilter,
posts keep sampled rays), Q6 ruled minimal (D5-1; candidate re-sourcing
deferred until after corpus overlay review). Q1 bookkeeping: rooms/chokes
per size recorded in the proposal's measured-budget table (9–49 rooms /
18–228 chokes small→giant). An offline process visualizer
(`tools/render_topology.py`) replays the flood from the agent-logged
clearance — added at review, now the inspection tool of record for
merge-knob tuning.

**v63 addendum (2026-08-12):** the D5-2 post-candidate re-sourcing shipped
as stencil v63 with James's facing revision — candidates from on-route gate
vicinities, facing scored **situationally at selection time against believed
enemy tracks** (the sketch's cover "situational half", now live), never baked
toward a pedestal at init. A `fieldsFor` by-value copy bug found en route
(~1.4 MB memcpy per `distanceAt` call) was fixed by per-front field hoisting:
giant `post_ms` 1528 → 73 ms, giant seat init now below the v61 baseline.
Layer 3 note: per-tick `flowWaypoint`/`routeDistance` callers still pay that
copy — the planner must use borrowed field access. See
[nav-post-resourcing-v63-2026-08-12.md](nav-post-resourcing-v63-2026-08-12.md).

**Layers 3–4 addendum (2026-08-13):** Layer 3 shipped as v65 (single
weighted-A* planner, 4px lattice, LOS-danger costs, completeness cascade,
endpoint snapping; hosted-proven at 13.5 ms/search, 0 unroutable — see
`VERSION_LOG.md` v65) and Layer 4 shipped as v66 (typed Intent, goals
validated at selection via `nearestReachable`, all five beelines + the
FlowReasons dispatch + the seven reason-string lists DEAD, carrier/hunter
profiles live, unroutable = loud bug signal). Both Codex-implemented under
orchestration. Q9's honest census: the 8px grid still feeds peek/duck
search, danger grids, cover/post generation, and squad canonicalization —
its demotion to a comms unit is larger than §8 implied. Remaining: v67
(early_defense/barrage_center over PoIs, side-lane posts) and Layer 5
(bounded follower/micro, watchdog simplification).

**v67 + Layer 5 close-out addendum (2026-08-29, written at rework
completion):** v67 shipped the post ATLAS (posts everywhere there is cover,
16-sector reach profiles, lazy ducks, two-phase situational selection;
early_defense re-expressed on home-room entrance gates and barrage on
danger-penalized room peaks; the side-lane TODO retired with the corridor
machinery — see
[nav-v67-post-atlas-2026-08-14.md](nav-v67-post-atlas-2026-08-14.md)).
Layer 5 shipped as v68: corridor-bounded micro (20 px default,
`nudgeClear` acceptance, Hold-duck exempt), the 90° jitter deleted, the
penalty-replan watchdog with `follow_replans`/`follow_stuck_events`
visibility, uniform progress accounting, and `Intent.arriveRadius`
transcribed from the five real strategy arrive distances — see
[nav-layer5-follower-2026-08-14.md](nav-layer5-follower-2026-08-14.md) and
`VERSION_LOG.md` v67/v68 for the hosted verdicts. **Kill-list honesty
notes:** the §4 "threat axis" kill only half-landed — movement no longer
keys on it, but `threatAxis`/`sweepTarget` still drive the idle aim sweep
in `action.nim` (carried as strategy-rework input) — **RESOLVED
2026-08-29 (v69): the aim-side keying is now removed too.**
`threatAxis`/`sweepTarget` are deleted; the idle-aim center is a typed
mind product (`Intent.idleAimCenterBrads`, computed in `strategy.nim`
post-ladder, consuming `sectorOffsetBrads` mind-side) with the body
keeping only the sweep oscillator. Bit-identical policy output proven on
a 278k-decision recorded-wire corpus. Design:
[strategy-idle-aim-intent-2026-08-29.md](strategy-idle-aim-intent-2026-08-29.md).
Of the Appendix B dead
code, `flowWaypoint` and the rally/choke anchors are gone, `distanceAt`
was revived as a live `defenseGate` scoring dependency, and
`insideBase`/`walkabilityDecodeMs` remain as vestiges.

## 10. TODOs spawned by the review (out of scope here)

- Fire-windup micro: strafe/aim during windup; trigger from cover then step out to minimize
  exposure time.
- belief.danger semantics validation experiment (Q10).
- Nim init re-baseline profile (supersedes the Python-era numbers in
  `reports/nav-init-profile-2026-08-03.md`).
