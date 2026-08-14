# stencil version log

Read this before assuming what a version contains. Format mirrors
`ctf_lab/ctf/beacon/VERSION_LOG.md`: one entry per uploaded version — what
changed, why, and what the evidence said.

## v68 — the bounded follower & micro (nav rework Layer 5, FINALE), uploaded 2026-08-14

Immutable policy-version UUID: `ffa8e5d2-10f1-4e6c-93f9-4b005a83359a`.
Uploaded with tag `purpose=bounded-follower`. **Not submitted to any
league.** The LAST layer of the navigation rework
([spec](../../docs/designs/nav-layer5-follower-2026-08-14.md);
Codex-implemented under orchestration).

- **Corridor-bounded micro**: perturbation destinations must lie within
  `STENCIL_FOLLOW_CORRIDOR_PX` (default 20 — REVISED at plan review from
  12 after Codex's discrepancy analysis showed the ~16 px separation step
  would have been categorically rejected; the review catch of the layer)
  of the current path polyline; `nudgeClear` remains the acceptance
  predicate (the v60 wall-slide law); Hold-context duck displacement is
  exempt. Rejections fall back to the plain waypoint and count
  (`micro_corridor_rejects`).
- **Watchdog finale**: the 90° steering jitter is DELETED (its job —
  masking beelines — ended in v66). Ladder: progress test → one forced
  replan with a one-cell blocked penalty (×8 cost, 96-tick TTL, per
  agent) → `follow_stuck_bug` loud trace if re-fired within 48 ticks.
  Spinning-diamond staleness moves from masked to visible
  (`follow_replans`/`follow_stuck_events` counters).
- **Follower tightening**: uniform progress accounting with an explicit
  stationary-behavior contract (post holds, fire-windup freeze, barrage
  ring, accepted ducks incl. zero-mask, rejected micro, dead — each with
  a reset-or-not rule); `Intent.arriveRadius` transcribed from the five
  real strategy arrive distances (barrage 80 / hold-family 28 / rejoin
  40 / squad-move-family 56) and consumed by the follower as
  behavior-preserving redundancy.

**Pre-upload evidence:** Codex harness (corridor geometry incl. the 16 px
separation case, watchdog determinism, penalty TTL, arrival parity, all
stationary cases) + committed `tools/nav_v68_properties.nim`; my suites
(planner 8.5k, layer2 1.9M) green; jitter grep gates zero. Live corpus:
**duck 8.1% in the forced-active episode (gate 7-13% — PASSES)**; h2h
duck ~0% is expected (early_defense has excluded peek/duck since v55 —
initially misread as a v60-class regression, then verified against the
makeIntent table and v67's identical local behavior). Micro mix shifted
as designed: total micro 18.5%→16.2%, duck UP 5.0→8.1% (Hold-exempt),
transit peeks 10.2→4.7% (corridor working as specified); combat micro
alive. Corridor rejects are dominated by 3-6-cell transit sidesteps —
expected at any sane width; peek% flagged as the batch watch metric
alongside duck%. 0 unroutable/0 fallback throughout. Built against
0.7.215 / `6c7a4c0e`.

**Hosted validation:** matched v68-vs-v67 batch pending at upload —
trace-diff emphasis (duck%, peek%, stuck/replan counters, micro mix) over
W-L. Verdict appended.

## v67 — the post atlas + conservative re-expressions, uploaded 2026-08-14

Immutable policy-version UUID: `f8289d11-7f88-4502-ad35-2edf4a415264`.
Uploaded with tag `purpose=post-atlas`. **Not submitted to any league.**

James's ruling made structural: **potential posts exist everywhere there is
cover; the situation decides relevance at query time, and it can change on
the fly** ([spec + addendum](../../docs/designs/nav-v67-post-atlas-2026-08-14.md)).
Codex-implemented under orchestration (plan review surfaced six spec-vs-code
discrepancies incl. a consumer my spec missed — `advancePoint` — and a
scale bug in my barrage formula that would have left danger a tie-break;
fixed via normalization).

- **Atlas**: every `coverDirs != 0` cell is an `AtlasPost` with a
  full-gun-range (1300 px, `STENCIL_POST_REACH_CAP_PX`) 16-sector reach
  profile; 64 px spatial index; LAZY duck cache (fields-cache precedent).
  Corridor-era machinery deleted (generateFront, corridor scoring,
  progress buckets, stored PostFronts). Giant atlas: 14,408 posts,
  **179 ms** mean build (gate 250 ms) at the full cap.
- **Selection**: two-phase — cheap reach-toward-bearing/distance/facing
  over all gathered posts, lazy-duck enrichment of the top 8 (bounded
  approximation, property-tested as such) — with a situational `bearing`
  parameter; defenders keep 64 px home-band ordering via expanding
  queries; `advancePoint` queries at stage anchors.
- **early_defense (conservative)**: holds atlas posts covering the home
  room's entrance gates (seat-th gate, bearing outward), endzone-confined,
  spawnCoverPoint fallback; release gate/suppressions unchanged.
- **barrage_center (conservative)**: normalized
  `peakClearance/255 − w·danger/fieldMax` over reachable room peaks
  (`STENCIL_BARRAGE_PEAK_DANGER_WEIGHT`, default 1.0 = co-equal),
  nearestReachable-validated; ring/priority semantics unchanged.
- Trace schema v4: `post_atlas` (pos/max-reach/top-sector), `atlas_ms`,
  `atlas_n`. Viewer migrated (my side): atlas rendering (reach-colored,
  sector ticks) + the selection-simulator mirror rewritten to the
  two-phase utility and re-verified fail-closed on 200 harness samples of
  the real production selection.

**Pre-upload evidence:** Codex harness (atlas completeness/reach
exactness, determinism under reversed lazy-query order, top-8 duck bound,
defender separation, endzone confinement) + my suites (planner props 11k,
layer2 props 2.7M with atlas invariants) all green; 21 modules `nim
check`; corridor grep gates zero. Live corpus: h2h 114 plans / active-ffa
820 plans, 0 unroutable, 1 snapped, 0 fallbacks; ffa atlas 6,639 posts /
86 ms under contention; tick rates normal. Built against 0.7.215 /
`6c7a4c0e`; canonical has advanced to 0.7.229 (`bf0bcc22`) — contract
compatibility assumed per the v60-era lineage argument, sim constants not
re-derived (flagged for the next pin review).

**Hosted validation:** matched v67-vs-v66 batch; also re-tests the v66 h2h
scatter watch-item. (Batch logistics note: the platform introduced
**experience credits** this week — the v66 control arms initially bounced
on HTTP 402 with the v67 arms holding the balance; a watcher posted them
the same day once the holds released, so arms ran hours apart, not
same-hour. Also new: the platform auto-runs a 10-episode field eval on
every fresh upload — `xreq_b05ea5db` (v66), `xreq_7595d11e` (v67); inert
but they share the credit pool. Prereg:
`local_data/episodes/post-atlas-v67-prereg.json`.)

**Hosted verdict (58/58 episodes, 0 ops failures):**

| mode (n/arm) | v67 | v66 (control) |
| --- | --- | --- |
| h2h vs focusfire:v39 (16) | 8W-8L | 9W-7L |
| duo vs swgy+relh (8) | 2W-6L | 3W-5L |
| ffa top-3 field (4) | **4W-0L** | **4W-0L** |
| total (28) | 14W-14L | 16W-12L |

Parity (−2 net, every mode within one game; both arms swept the ffa cell —
its first sweep by any version). The v66 h2h scatter watch-item RESOLVED:
h2h across four same-cell arms in two days reads 13-3 / 9-7 / 9-7 / 8-8 —
the 13-3 was the outlier, ~9-7 is this matchup's level. Contract counters
hosted: 1163 plans / 30 seats at 9.0 ms, **0 unroutable, 0 fallbacks, 3
snapped**. Atlas hosted under contention: 21.6k posts on the giant probes
built in 88-181 ms — the gate holds in production (standard maps ~2.9k
posts / ~10 ms).

**Conclusion: v67 accepted.** Behavior parity at strategy-conservative
scope was the goal ("just make sure everything still works") — achieved
with the atlas substrate live: posts exist everywhere there is cover, and
the future strategy rework selects from them situationally. v58 remains
the live champion; nothing submitted.

## v66 — the Intent & goal contract (nav rework Layer 4), uploaded 2026-08-13

Immutable policy-version UUID: `80e2a0a4-9662-4722-8fe0-e3aa4a57e593`.
Uploaded with tag `purpose=intent-contract`. **Not submitted to any league.**

Layer 4 per the approved split
([design/spec](../../docs/designs/nav-layer4-intent-contract-2026-08-13.md);
v67 will re-express early_defense/barrage_center over PoIs + side-lane
posts). **Codex-implemented under orchestration**; its plan review caught
two transcription errors in MY spec's flag table (formation-bias is a
strict five-reason whitelist; code-truth preserved and the doc corrected),
delivered the honest Q9 census (the 8px grid also feeds peek/duck search,
danger grids, cover/posts, squad canonicalization — grid demotion is bigger
than the sketch implied), and caught a spec gap I endorsed: cached paths
invalidate when the intent's cost profile changes.

- **Typed Intent**: movingGoal/clampToEndzone/suppressFireFreeze/profile/
  micro set replace ALL seven reason-string dispatch lists; one declarative
  makeIntent table in strategy.nim; `intent.reason` is telemetry-only
  (grep-gated: 0 non-telemetry reads; FlowReasons/MovingPlanReasons
  identifiers deleted).
- **Goals validated at selection**: `nearestReachable` (unbiased pixel
  ring, component-gated) at every dirty producer — steal/convert_hunt
  pedestals, grenade evacuation radial, escort extrapolation, spray-flee
  winner, barrage center. Producer fallthrough on none.
- **All five beelines dead + FlowReasons dispatch dead**: every NavigateTo
  routes through the v65 planner; arc pursuit became a strategy-level
  validated moving Hunter intent (shared target selection moved to
  fight.nim so strategy/action cannot drift; firing stays action-owned);
  the unroutable beeline is now hold-in-place + loud `plan_unroutable_bug`
  trace. Flow fields survive only as the Dijkstra oracle
  (flowWaypoint retained solely for forwardRayEnds, documented).
- **Profiles live**: Carrier danger ×2.5, Hunter ×0.25
  (`STENCIL_PROFILE_CARRIER_DANGER`/`_HUNTER_DANGER`); profile change
  invalidates the cached path.

**Pre-upload evidence:** Codex harness green (incl. arc-pursuit
emission/suppression parity, steal rush-exemption, carrier/profile
interaction); grep gates 0/0; 13 modules `nim check` clean; release
compiles. My independent suites: planner props 11k checks / layer2 props
3.3M checks green. Live: h2h corpus episode ran **75 plans where v65 ran
zero** (the flow kill is live; carry/steal movement now planner-routed) at
7.6 ms mean, 0 unroutable/0 snapped; forced-active ffa: 773 plans, 19 ms
mean, **0 unroutable, 2 snapped** (was 9 in v65 — producers now validate),
0 fallbacks, intent mixes normal, 111 ticks/s. Built against 0.7.215 /
`6c7a4c0e`.

**Hosted validation:** matched v66-vs-v65 batch pending at upload. Expected
deltas: carry/steal/hold movement geometry (flow → danger-aware planner
with Carrier evasion — the largest visible behavior change of the rework),
pursuit via strategy intents; watch stuck/backoff rates and tick rate.

**Hosted verdict (58/58 episodes, 0 ops failures; prereg
`local_data/episodes/intent-v66-prereg.json`):**

| mode (n/arm) | v66 | v65 (control) |
| --- | --- | --- |
| h2h vs focusfire:v39 (16) | 9W-7L | 13W-3L |
| duo vs swgy+relh (8) | **4W-4L** | 2W-6L |
| ffa top-3 field (4) | 2W-2L | 3W-1L |
| total (28) | 15W-13L | 18W-10L |

Totals within noise (first batch where the control's total edged the
candidate's; h2h drove it). The obvious suspect — Carrier ×2.5 evasion
slowing capture runs — is DISPROVEN by the traces: neither arm ever
entered carry_home or steal in the h2h episodes (they resolve in
early-defense combat), so the profile never ran there. The h2h control arm
simply ran hot (this cell's control has swung 11-5 → 6-10 across days
before). Meanwhile duo improved to 4W-4L — the best any version has done
against the swgy field. **Contract counters hosted, flawless:** 1482 plans
across 30 seats (≈3× v65's volume — the flow kill is live in competition)
at 8.0 ms mean, **0 unroutable, 0 beeline fallbacks, 5 snapped**; duck
7.1% normal.

**Conclusion: v66 accepted — the contract layer is structural and its
hosted evidence is exactly what it promised.** Flag for the v67 batch:
watch whether the h2h scatter persists on the same cell. v58 remains the
live champion; nothing submitted.

## v65 — the planner (nav rework Layer 3), uploaded 2026-08-13

Immutable policy-version UUID: `d8b5ca59-503f-4f8c-85b8-df052fb38998`.
Uploaded with tag `purpose=layer3-planner`. **Not submitted to any league.**

Layer 3 of the navigation rework per the approved proposal
([HTML](../../docs/designs/nav-layer3-planner-2026-08-12.html), brief +
implementation addenda in `.nav-layer3-planner-brief.md`). **Implementation
was planned and executed by OpenAI Codex CLI under orchestration** (James's
call); three iterations, each gated by independent review: the initial
implementation, a lattice-completeness fix, and an endpoint-snapping fix —
both fixes prompted by findings Codex's own harness missed.

- **The planner** (`planner.nim`): weighted A* on a 4 px pixel lattice
  (`STENCIL_PLAN_STEP_PX`), `canStand` node validity, exact supercover
  edge admission, octile costs × (1 + dangerWeight × DangerField sample at
  edge midpoints), euclidean heuristic + the cached-Dijkstra oracle for
  already-minted stable goals (non-minting `peekRouteDistance`; valve
  `STENCIL_PLAN_ORACLE`), `STENCIL_PLAN_WEIGHT` inflation shelved at 1.0.
  Deterministic (tie-broken queue, fixed orders); reusable
  generation-stamped per-agent workspace, lazily allocated.
- **Completeness cascade** (found by the independent property suite:
  sameComponent pairs could be unroutable when a standable ridge is
  narrower than the lattice): failed searches retry step/2 then 1 px,
  gated on `sameComponent` — a 1 px 8-connected supercover lattice is
  complete w.r.t. engine 4-connectivity, so Layer 4's
  "sameComponent ⇒ planning succeeds" contract holds. `fallback` counted.
- **Endpoint snapping** (found in live play: 27% of plans were unroutable
  because strategy still emits non-standable goals — pedestal targets,
  wall-clipped extrapolations — that the old astar silently snapped):
  non-standable endpoints snap to the nearest standable pixel within 32 px
  (unbiased ring scan, NOT the retired up-left-biased cell snap); the raw
  unreachable goal is not appended. After the fix: unroutable 262 → 0 in
  the same scenario, 7 goals snapped. `plan_goal_snapped` traced — the
  producer-cleanup worklist for Layer 4.
- **DangerField** (`danger_field.nim`): the ruled two-level LOS-exposure
  model — per-source supercover perimeter rays on the 8 px grid with a
  precomputed attenuation kernel (flat to 400 px, 0.6 at 1050 px,
  `STENCIL_DANGER_LOS_*` knobs), non-LOS close-quarters floor (190 px),
  normalization weight; producer standalone behind the heatmap; stored as
  `Belief.planDanger` (the unvalidated legacy `belief.danger` grid is
  deliberately untouched). Rebuilt on the shared 12-tick cadence
  (`STENCIL_PLAN_MOVING_REPLAN_TICKS`, dual-role documented).
- **Integration**: `astarWaypoint` keeps its contract (trailing defaulted
  params; cache/replan semantics; unroutable → existing beeline fallback,
  which SURVIVES v65 by design — goal validation is Layer 4); moving-target
  replan cadence for the five pursuit-class reasons; old 8 px astar
  deleted; `nearestWalkable` snap gone from search. FlowReasons untouched.
  Telemetry: `plan_count/ms_total/expansions_total/unroutable_count/`
  `fallback_count/goal_snapped` snapshot counters.

**Oracle admissibility, measured (D4's caveat closed):** on the three real
batch maps, 240 paired queries (`STENCIL_PLAN_ORACLE` on/off, same binary):
worst path-cost ratio 1.0113, mean ≈1.0015 — vs 1.126 on adversarial
synthetics with sub-cell passages that generator maps (26 px corridor
guarantee) cannot produce. Ships enabled.

**Pre-upload evidence:** independent planner property suite (13k–17k checks
per run over 60–80 random maps: sameComponent ⇔ routable, every edge
segmentClear, start-exclusive/goal-inclusive contract, determinism,
no-minting) + Codex's own harness (lattice-ridge regressions, snapping
cases, LOS producer values, no-mint, 192-query optimality probe); all
locally-checkable modules `nim check` clean; release entrypoint compiles.
Live self-play: opening phases are all flow reasons (zero plans — expected);
with early defense disabled to force A* reasons: 600 plans/16 seats/3000
ticks, ~50 ms per search under 16-way contention (bench-consistent),
0 unroutable, 0 fallback. Viewer gained the planner layer: scenario
routes between capture points with the LOS heatmap — routes visibly thread
obstacle shadows. Built against 0.7.215 / `6c7a4c0e`.

**Hosted validation:** matched v65-vs-v64 batch pending at upload; expected
behavior delta is route GEOMETRY for the ~10 A*-reason intents (danger-
aware shadow-threading detours, unbiased endpoints) plus the moving-target
cadence; flow-reason movement unchanged. Tick-rate compared across arms
(planning sits on the decide path).

**Hosted verdict (58/58 episodes, 0 ops failures; v65 arms
`xreq_6c5253cb`/`xreq_9f4e2b6c` h2h, `xreq_a6cd94a3`/`xreq_f018ce5b` duo,
`xreq_a896458b` ffa; v64 arms `xreq_95c8b41f`/`xreq_b36d3b76`,
`xreq_c5a59bec`/`xreq_916837a7`, `xreq_a24ad8c8`; probes
`xreq_70ce6ea6`/`xreq_419809d3`):**

| mode (n/arm) | v65 | v64 (control) |
| --- | --- | --- |
| h2h vs focusfire:v39 (16) | 10W-6L | 10W-6L |
| duo vs swgy+relh (8) | 2W-6L | 2W-6L |
| ffa top-3 field (4) | 2W-2L | 0W-4L |
| total (28) | **14W-14L** | 12W-16L |

Gameplay parity (h2h and duo identical; +2 in ffa at n=4) — expected: route
quality alone was never the win condition; the cost machinery's value
compounds when Layer 4 gives it validated goals and per-intent profiles.
**The planner infrastructure proved itself hosted:** across 30 sampled v65
competition seats, 925 real searches at **13.5 ms mean** (per-seat
containers), **0 unroutable, 0 beeline fallbacks, 9 endpoint snaps** — the
bridge behaviors work and the Layer 4 worklist counter is live. v65 lost
both n=2 giant probe scores (ops-tier; the probe coin has now landed
differently in three consecutive batches — treat as noise).

**Conclusion: v65 accepted — the Layer 4 baseline.** One planner runs all
A*-reason navigation with danger-aware routing; FlowReasons and the beeline
fallback are the remaining Layer 4 kill-list. v58 remains the live
champion; nothing submitted.

## v64 — wide post pool + Dijkstra-minting fix, uploaded 2026-08-12

Immutable policy-version UUID: `d3504b01-ea7e-46db-9b3d-59a959940752`.
Uploaded with tag `purpose=wide-post-pool`. **Not submitted to any league.**

James's review of v63: too few potential posts — the funnel put the
decision weight at init with zero context, and the belief-scored selection
had almost nothing to choose from. v64
([design](../../docs/designs/nav-wide-post-pool-v64-2026-08-12.md)) widens
the pool and moves all choice to selection:

- Per-bucket retention 6 → 24 (`PostRayCandidatesPerBucket`), shortlist cap
  16 → 256 (`STENCIL_POST_SHORTLIST_COUNT`, now a safety cap): **every**
  retained candidate is ray-scored and duck-paired. Real maps yield
  ~200–250 potential posts per front (vs 16). Pool membership does not
  require a duck (ducklessness costs the 0.15 contrast term); the static
  top-6 "posts" survive only as a no-context default view.
- Defenders select from the wide pool (same 64 px band ordering +
  score/facing, plus a `PostSeparationPx` distinct-position filter so dense
  pools don't stack seats). `orderPost` unchanged — its search space just
  became real.

**The wide pool detonated a latent landmine, now fixed at the root:**
`routeDistance`'s GOAL argument keys the lazy Dijkstra cache, so
`squads.advancePoint`'s `routeDistance(home, candidate.pos)` minted a
full-grid field PER CANDIDATE (the deep-dive's M2 hazard). Episode wall
time exploded ~6×; profiling (`sample` of the one pegged process — the
first sample hit an idle lockstep waiter) showed 1845/1845 samples in
`dijkstra` under `advancePoint`. Fixes: (1) argument-order rule — goal slot
takes stable goals only (homes/capture points); arbitrary points go in the
start slot (undirected grid, same value); applied at `advancePoint` and
`policy.defensivePostForward`; (2) `fieldsFor` returns **`lent
RouteFields`** with expression-form callers — ending the ~1.4 MB-per-call
copy for every caller including per-tick `flowWaypoint` (supersedes v63's
per-front hoist as the root fix).

**Measured (local, batch cells):** giant-probe `post_ms` **18 ms** with the
14× pool (v63: 73 ms; v62: 1528 ms); ffa 35 ms for 3 fronts; giant seat
init ~1.0 s; episode tick rate faster than v63 (the minting fix also
removes mid-episode Dijkstra hitches v63 still had). 5.6M property checks
over 80 maps incl. the new defender-separation invariant; selection mirror
200/200 against the wide pool; corpus renders under
`topology_renders/v64/`. Built against 0.7.215 / `6c7a4c0e`.

**Hosted validation:** matched v64-vs-v63 batch —
same shape, re-resolved board, paired giant probes (v64-vs-v63 in-episode).
Expected behavioral deltas: post/defender positions from the wide pool +
separation filter; intel-reactive squad picks now have real alternatives.

**Hosted verdict (58/58 episodes, 0 ops failures; v64 requests
`xreq_cd382c72`/`xreq_5c7fb816` h2h, `xreq_4f125050`/`xreq_27f6a84f` duo,
`xreq_09b46d69` ffa; v63 arms `xreq_a7f3490d`/`xreq_7e997c25`,
`xreq_8db26322`/`xreq_97ddcfee`, `xreq_d128c0c2`; probes
`xreq_dbd21c9e`/`xreq_dc017eec`):**

| mode (n/arm) | v64 | v63 (control) |
| --- | --- | --- |
| h2h vs focusfire:v39 (16) | 9W-7L | 9W-7L |
| duo vs swgy+relh (8) | 1W-7L | 2W-6L |
| ffa top-3 field (4) | 2W-2L | 3W-1L |
| total (28) | 12W-16L | 14W-14L |

**Gameplay: parity** — h2h dead even, duo/ffa each one game apart, total
-2 net for v64, nowhere near significance at these n. The wide pool did
not (yet) buy wins; its value is as substrate — Layer 4 intent-aware
selection finally has something to select from. **Infra: strictly
better** — hosted paired giant probes: v64 post_ms 22/27 ms and seat init
~0.88 s (fastest of any version; v63 seats 139/267 ms post, up to 2.5 s
total — v63 still carried mid-episode minting hitches that v64's root fix
removed), and v64 won both in-episode giant duels (n=2, ops-tier;
reverses v63's 0-2 vs v62 — treat both as noise).

**Conclusion: v64 accepted as the Layer 3 baseline** on infra grounds with
demonstrated gameplay parity: fastest init, no minting hitches, the
unbounded-Dijkstra hazard closed, and the post pool the later layers need.
v58 remains the live champion; nothing submitted.

## v63 — post candidate re-sourcing + belief-scored facing, uploaded 2026-08-12

Immutable policy-version UUID: `fba7d396-9166-49de-9252-b6bef98b0077`.
Uploaded with tag `purpose=post-resourcing`. **Not submitted to any league.**

Executes the deferred Layer 2 D5-2 option
([design](../../docs/designs/nav-post-resourcing-v63-2026-08-12.md), approved
with the belief-scored facing revision after James killed the static
toward-enemy-home facing filter). Two separable claims — quality and cost:

**Quality (the re-sourcing + situational facing):**
- `generateFront` candidates now come from cover-bearing cells within
  `STENCIL_POST_GATE_VICINITY_PX` (48) of on-route chokes (same
  `detour ≤ PostCorridorPx×3` cap as the old scan), with the legacy
  full-grid scan surviving only as a per-empty-progress-bucket fallback
  (`STENCIL_POST_BUCKET_FALLBACK`, default on). No direction is baked in.
- Facing is situational: new `facingScore` (fraction of believed threat
  positions a cell is covered from — the first per-direction consumer of the
  16-ray bitmask) enters selection utility at weight
  `STENCIL_POST_FACING_WEIGHT` (0.15). `squads.orderPost`'s core is
  extracted to the pure `worldmap.selectRankedPost` (offline harness runs
  the exact production proc); both it and `roles.defensivePostForSeat` take
  believed enemy positions (velocity-projected tracks within
  `TrackTtlTicks`) from the caller's Belief.
- **Expected behavioral deltas, by design:** post positions move to gate
  vicinities (the h2h batch cell's front went 3 → 5 selected posts);
  defender assignment now orders by 64 px distance BANDS with
  score+facing inside a band — intel-free behavior is deliberately NOT
  bit-identical to v62 (within-band reordering); squad post picks react to
  believed enemy bearings.

**Cost (a separate fix the first cut exposed):** re-sourcing alone made
giant `post_ms` WORSE (1528 → 2470 ms local) — the dominant cost was never
the scan shape but `fieldsFor` returning `RouteFields` **by value**: every
per-cell `distanceAt` memcpy'd ~1.4 MB of cached Dijkstra field. Hoisting
the two route fields once per front and reading distances by cell index:
giant-probe `post_ms` 1528 → **73 ms**, duo-cell 2166 → **88 ms**; giant
seat init ~1.0–1.1 s local — below the v61 pre-Layer-2 baseline. Recorded
for Layer 3: every `distanceAt`/`routeDistance`/`flowWaypoint` call still
pays that copy, including per-tick follower lookups — the planner rework
must use borrowed/indexed field access.

**Viewer (James's request):** `render_topology.py` gained the post layer
(front dropdown, score-colored candidates, posts with rays + duck links,
defender assignments) and the **selection simulator** — click to place a
squad directive, shift-click to place believed enemies, rank selector; the
JS mirror of the selection utility is verified fail-closed at load against
200 harness-sampled runs of the real production proc.

**Pre-upload evidence:** 9.2M property checks over 120 random maps (half
4-team) incl. new post invariants (separation, real ducks, routable fronts
non-empty); selection mirror 200/200; corpus before/after renders under
`local_data/.../topology_renders/{before-v63,after-v63}`; same-map local
timings above. `nim check` clean on all touched modules. Built against
0.7.215 / `6c7a4c0e` (pin unchanged).

**Hosted validation:** matched v63-vs-v62 batch pending at upload time —
same 12-request/58-episode shape on the re-resolved live board, paired
giant probes now v63-vs-v62 in-episode (they confirm the post_ms fix under
hosted contention); analysis via the score-sign classifier (the v62
batch's unique-max bug cannot misfile duo team wins as draws). Expected
trace deltas: post positions, defender band ordering, squad picks; duck%
and objective mix should hold; ticks/s compared across arms because the
facing term sits on a per-tick path.

**Hosted verdict (batch complete, 58/58 episodes, 0 ops failures; requests
`xreq_5b1200d8`/`xreq_c2a0784a` (v63 h2h), `xreq_05ccdab7`/`xreq_a4eaace7`
(v63 duo), `xreq_92086ce0` (v63 ffa), `xreq_6b5ffddf`/`xreq_a7ac4ff5`,
`xreq_58c6ccbc`/`xreq_df0fcd60`, `xreq_17c35ded` (v62 arms),
`xreq_e486875d`/`xreq_a2e9fdaa` (giant probes)):**

| mode (n/arm) | v63 | v62 (control) |
| --- | --- | --- |
| h2h vs focusfire:v39 (16) | **11W-5L** | 6W-10L |
| duo vs swgy+relh (8) | 2W-6L | 3W-5L |
| ffa top-3 field (4) | 2W-2L | 1W-3L |
| total (28) | **15W-13L** | 10W-18L |

(Score-sign classifier throughout. Note the control drifted day-to-day:
v62 scored 11W-5L on this same h2h cell in ITS batch yesterday and 6W-10L
today — same-day paired arms are the only comparison that means anything.)
v63 +5 net in h2h, -1 duo, +1 ffa: overall positive, h2h-driven, duo
within matched-arm noise at n=8. h2h duck micro: v63 7.6% vs v62 21.6% —
the low side belongs to the winning arm (opposite of the v60 pathology
signature, where the regressed version ducked more AND lost).

**Giant probes (v63-vs-v62 in-episode, ops evidence):** both completed
clean, and the hosted contended numbers seal the cost claim — **v63
post_ms 128/132 ms vs v62's 3405/2860 ms in the same episodes**; v63 giant
seat init 0.95-0.97 s vs v62's 4.1-4.2 s, i.e. below even v61's 1.9-2.1 s
pre-Layer-2 baseline. For honesty: v63 lost both probe episodes' scores
(n=2, giant-only, excluded from gameplay claims per the preregistration —
worth an eye at the next giant-containing batch).

**Conclusion: v63 accepted — the new nav-rework baseline for Layer 3.**
v58 remains the live champion; nothing submitted.

## v62 — topology & PoIs (nav rework Layer 2), uploaded 2026-08-11

Immutable policy-version UUID: `d415aded-ae80-4140-9f27-ad073718af25`.
Uploaded with tag `purpose=nav-topology`. **Not submitted to any league.**

Layer 2 of the navigation rework
([design](../../docs/designs/nav-layer2-topology-proposal-2026-08-11.md),
approved with James's rulings D1–D7 recorded there). Everything is derived
from the v61 clearance field at init; every authored anchor is gone.

- **Connected components** (`WorldMap.component`, per-pixel `uint16`):
  standalone 4-connected CCL over the canStand set — engine-exact (per-axis
  Y-then-X integration means diagonal steps need a standable orthogonal
  intermediate), deliberately decoupled from the watershed so a room bug
  cannot corrupt reachability. `componentOf`/`sameComponent` are the O(1)
  queries behind the Layer 4 goal contract (no consumer yet).
- **Rooms + chokepoints** (`rooms`, `chokes`, `roomLabel`): priority-flood
  watershed on clearance (256-bucket queue, O(px)) — seeds at clearance-maxima
  plateaus, first-contact saddles between regions are gates (pos = widest
  point, clearance = L∞ half-width), persistence merge (depth
  `STENCIL_TOPOLOGY_MERGE_DEPTH_PX`=4 + ratio
  `STENCIL_TOPOLOGY_MERGE_RATIO`=0.8), spatially-separated multi-gates kept
  (`STENCIL_GATE_SEPARATION_PX`=64).
- **Directional cover** (`coverDirs`, per 8px cell): N-ray blocked-from
  bitmask (`STENCIL_COVER_RAYS`=16, `STENCIL_COVER_RAY_PX`=24) testing the
  wall mask, **map-boundary exits do not count** — the "edge adjacency is not
  cover" review point. `cover` (bool) is now `coverDirs != 0`, so every cover
  consumer moved with it: nearestCover (hold snap, squad spread, advance
  fallback), spawnCoverPoint, and **post candidate gating** — post positions
  will shift even though the post pass itself is otherwise untouched (D5-1).
- **Authored anchors deleted**: `chokePoint` (45% axis fraction) →
  `defenseGate` (first significant on-route gate from home, fully derived,
  `STENCIL_GATE_DETOUR_PX`=48, cached per team; falls back to the home-room
  peak on gateless maps); `rallyPoint`/`pastRally`/`axisPoint` and the
  `STENCIL_CHOKE_FRACTION`/`STENCIL_RALLY_FRACTION` knobs are gone.
- **Tracing**: `nav_init` gains `component_ms`/`topology_ms`/`cover_ms` +
  `components_n`/`rooms_n`/`chokes_n`; `navigation_map` (schema v3) gains
  rooms, chokes, the cover-dirs grid, the topology knob values, and a
  zlib+delta-packed dump of the exact clearance field (~1–2 MB on giant,
  rides the opt-in `STENCIL_TRACE_NAVIGATION=1` payload). `choke`/`rally`
  trace fields are dropped; teams carry `defense_gate`.
- **Offline process visualizer** (James's addition):
  `tools/render_topology.py` + `tools/topology_debug.nim` re-run the exact
  worldmap code on the agent-logged clearance with a process journal and
  render a self-contained HTML viewer — watershed flood scrubber (a pixel is
  labeled exactly at its own clearance level, so no per-pixel event log is
  needed), raw/merged/component views, merge-decision log, cover roses, and
  the defense-gate scoring table. It cross-checks recomputed finals against
  the agent-traced finals and refuses to render silently on drift.

**Pre-upload evidence:** 21.9M scratchpad property checks over 300 random
maps + 2 synthetic scenarios vs brute force (components ≡ BFS 4-connectivity;
roomLabel partition/connectivity/peak invariants; saddle-on-boundary and
width bounds; determinism; cover ≡ reference rays incl. the empty-map
edge-not-cover case). `nim check` clean on all locally-checkable modules.
Real-map corpus (self_play, one episode per size, per-seat contention):

| size | px | rooms | chokes | component | topology | cover | seat init total |
|---|---|---|---|---|---|---|---|
| small | 588k | 9 | 18 | 9 ms | 38 ms | 13 ms | 113 ms |
| standard | 814k | 10 | 25 | 13 ms | 54 ms | 19 ms | 181 ms |
| large | 1.38M | 16 | 57 | 23 ms | 93 ms | 36 ms | 356 ms |
| huge | 2.64M | 27 | 111 | 45 ms | 197 ms | 69 ms | 869 ms |
| giant 1v1 | 5.5M | 49 | 228 | 102 ms | 435 ms | 153 ms | 2362 ms |
| giant 4ffa8 | 6.2M | 37 | 152 | 115 ms | 475 ms | 194 ms | 5119 ms |

**Honest cost note:** giant-1v1 seat init grew to ~2.36 s (from v61's
~1.5–1.9 s) — Layer 2 adds ~690 ms there under 16-way contention. The
4ffa8-giant's 5.1 s total is dominated by the pre-existing 3-front post pass
(3.9 s), with ~784 ms from Layer 2. Init-only; the Dijkstra/post pass remains
the later rework target. The offline visualizer validated zero-drift against
a real agent trace (standard map). Rooms/chokes counts above are the sketch
Q1 node/edge bookkeeping for the hierarchical-planner decision.

**Built against 0.7.215 / `6c7a4c0e` (pin unchanged); deployed canonical
0.7.227.** Note: the campaign board was ROLLED BACK to the pre-migration
10×10 square board (100 cells, null map_size) between this morning's
round-967 re-verification and this upload — the board events feed records
the restore. Hosted validation must target the restored board's live cells.

**Hosted validation (in flight at write time):** matched v62-vs-v61 batch on
the restored board, 12 requests / 58 episodes, seatings verified against the
preregistration on readback. Cells: h2h `1v1`-mode (2,0) ref `1v1` seed
386501705; duo `2v2`-mode (5,0) ref `2v2` seed 306617036; ffa `ffa4` (4,4)
ref `4ffa` seed 350827746 — all with mapSize omitted (cells carry none).
Pinned field: paintbot-focusfire:v39 (h2h + ffa), swgy-paintbot:v22 (duo
opposing captain + ffa), Picasso:v52 (red-side ally), relhalpha:v4
(blue-side ally + ffa). Requests: v62 h2h `xreq_390dff71`/`xreq_16800cc3`,
duo `xreq_ca5192bf`/`xreq_22c073b6`, ffa `xreq_dd592a79`; v61 h2h
`xreq_d8f4ffb8`/`xreq_ed06892a`, duo `xreq_e1120b86`/`xreq_d971a4e4`, ffa
`xreq_ebed31f5`; plus two giant-init DEBUG PROBES (invented mapSize=giant,
v62-vs-v61 in-episode, both seatings: `xreq_a1de40e5`/`xreq_5cb7f255`) —
probes are ops evidence only, excluded from gameplay claims.

**Hosted verdict (batch complete, 58/58 episodes, 0 ops failures):**

| mode (n/arm) | v62 | v61 (control) |
| --- | --- | --- |
| h2h vs focusfire:v39 (16) | **11W-5L** | 6W-10L |
| duo vs swgy+relh (8) | **2W-6L** | 0W-8L |
| ffa top-3 field (4) | 2W-2L | 2W-2L |
| total (28) | **15W-13L** | 8W-20L |

(Classification note: wins/losses are by the subject's own score sign in
team modes — +2/−2, no zero-score episodes occurred — after an initial
unique-max-winner classifier misfiled the two duo team wins as draws; the
subject's ally shares the winning score in duo mode.) v62 ≥ v61 in every
mode on identical cells/opponents/seatings; the h2h swing (+5 net wins) is
the clearest signal (not individually significant at n=16/arm — Fisher
~0.15 — but direction-consistent with the duo wins). The duo cell against
the #2-ranked swgy captain is a hard matchup for both arms; only v62 took
games off it. Behavior diffs at the subject seats:
objective mixes aligned; h2h duck micro 13.4% (v62) vs 11.9% (v61) — no
v60-style duck spike; v62 spends less time dead (27.6% vs 33.3% of h2h
snapshots) and less time in early_defense (19.2% vs 28.9%, coherent with
earlier lives leads releasing the gate).

**Giant-init probes (both seatings, v62-vs-v61 in-episode):** both completed
clean. Paired hosted giant seat init: v62 3.2-4.2 s vs v61 1.9-2.1 s
(rooms 71 / chokes 300 on the probe seed). Breakdown: Layer 2 phases
~640-700 ms, and **post_ms grew ~0.7-1.5 s** because the directional-cover
swap (D3a) admits more post candidate cells than adjacency cover — a real,
disclosed compounding cost on giants and a concrete input to the Q6/D5-2
post-rebuild decision and the later Dijkstra/post init rework.

**Conclusion: Layer 2 accepted.** v62 is the new nav-rework baseline for
Layer 3; v58 remains the live champion (nothing submitted).

## v61 — nudgeClear micro fix (nav rework Layer 1, final), uploaded 2026-08-11

Immutable policy-version UUID: `3380ab6d-5bc8-45b7-9429-ff7b74fc1f85`.
Uploaded with tag `purpose=nav-clearance-nudge`. **Not submitted to any
league.** This is the version that completes Layer 1; v60 is superseded.

v60's matched hosted batch found a real behavioral regression: exact
supercover validation at the four micro-nudge call sites (sidestep, squad
stance, formation bias, hold separation) rejected slightly-clipping peek
nudges that the engine's forgiving wall-slide executes fine — duck micro
time rose from 11.3% to 15.0% of snapshots and v60 went 10W-23L vs paired
v59's 16W-17L (n=33/arm, all three modes leaning negative). v61 adds
`nudgeClear` — `canStand` sampled every 2px, bit-identical acceptance to
the pre-clearance `walkableSegment` (19.2k random-segment property checks)
at ~1/169th the reads — at those call sites plus init duck pairing. Flee
validation keeps the exact `segmentClear` (the intended improvement; it
fired equally in both v60 arms).

**Hosted verdict (round-2 matched batch, 64 episodes, 20 requests, two
cells per mode, both seatings, same pinned opponents):** v61 **13W (+16)**
vs paired v59 **10W (+4)** at n=32/arm; ffa 8/8 sweep; 0 ops failures;
duck micro back to 11.1% (v59 control 13.5%); objective mixes aligned;
grid parity (`walkable_cells`) exact on every map. Combined with round 1,
130/130 episodes completed with zero errors. Layer 1 is done: one
predicate family (`canStand`/`segmentClear`/`nudgeClear` over the L∞
clearance field), erosion deleted, giant-map clearance init 60-100 ms
(one-time; total giant init ~1.5-1.9 s is pre-existing Dijkstra/post cost,
a later rework target).

Wall-slide lesson for the rework (recorded in the nav sketch): micro-nudge
validity must not exceed engine-movement fidelity — the executor's slide
makes near-valid segments practically valid, so exactness at the nudge
layer is a pessimization.

## v60 — L∞ clearance field (nav rework Layer 1), uploaded 2026-08-11

Immutable policy-version UUID: `311a5ef0-928c-4910-9172-881ea81886af`.
Uploaded with tag `purpose=nav-clearance`. **Not submitted to any league.**

First increment of the navigation rework
([`../../docs/designs/nav-rework-sketch-2026-08-11.md`](../../docs/designs/nav-rework-sketch-2026-08-11.md)).
Behavior-preserving in intent; the only deliberate behavioral deltas are the
segment predicates becoming engine-exact at the margins.

- `WorldMap.clearance: seq[uint8]` — exact L∞ (Chebyshev) distance to the
  nearest wall pixel, out-of-bounds counted as wall, clamped at 255. Two-pass
  8-neighbor chamfer (exact for L∞, not an approximation). Because the
  engine's `canOccupy` footprint is a 13×13 square, `clearance[p] > PlayerHalf`
  reproduces it bit-for-bit in one array read.
- `canStand(p)` (engine-exact point walkability) and `segmentClear(a, b)`
  (supercover DDA at pixel resolution, one clearance read per visited pixel)
  replace both `walkableSegment` (pixel-exact, ~length/2 × 169 reads/sample)
  and `walkableNavSegment` (8px-grid conservative). All seven call sites
  updated. A Lipschitz skip-march variant was rejected: property tests caught
  a corner-cut false pass at minimum clearance.
- The 8px nav grid is now derived from clearance via the cell-center test —
  bit-identical to the deleted summed-area erosion. A*, Dijkstra flow fields,
  `nearestWalkable`, and cover are unchanged consumers of the unchanged grid.
- `erodeMs` → `clearanceMs`; trace key `erode_ms` → `clearance_ms`
  (`self_play.py` updated to match).

**Pre-upload evidence:** scratchpad property tests vs brute force on random
maps — 268k exhaustive clearance pixels, bitwise nav-grid parity vs the old
erosion, 9.6k `canStand` points vs footprint scans, 24.6k segments (2,690
walkable) vs an independent supercover reference plus a dense-sampling
cross-check; all passed. `nim check` clean on the touched modules.

**Built against 0.7.215 / `6c7a4c0e` (pin unchanged); deployed canonical is
now 0.7.227.** v58 competes live on 0.7.227 with the same pin lineage, so the
wire contract is compatible; sim-rule constants have not been re-derived
against 0.7.217–0.7.227.

**Hosted validation (running at upload time):** a matched v60-vs-v59
campaign-shaped batch on live round-967 cells — head-to-head `1v1`-mode cell
(4,2) ref `1v1` seed 2106233304 size **giant** (clearance-init stress), 2v2-mode
cell (12,2) ref `default` seed 2008560253 standard with fixed side allies and
swapped captains, and ffa4-mode cell (5,1) ref `4ffa8` seed 1698802266 (32
seats); 22 episodes across 10 requests: `xreq_aef998da`/`xreq_fb8e1b51`
(v60 h2h), `xreq_6cbf9168`/`xreq_c2e6232c` (v59 h2h), `xreq_8a92b769`/
`xreq_7eb275ab` (v60 2v2), `xreq_334b7fd6`/`xreq_c14e122e` (v59 2v2),
`xreq_840186b5` (v60 ffa), `xreq_55098ad0` (v59 ffa). Two earlier duo
seating-2 requests (`xreq_5a432982`, `xreq_748e763d`) were cancelled for
moving allies with captains — the current commissioner keeps allies fixed to
their sides. Note the campaign contract has changed since the docs' round-381
snapshot: 16×16 hex board (round 955 migration), true `1v1` head-to-head mode,
and `_duo_roster` now splits each team **evenly** between captain and ally
(4+4), not 7+1.

## v59 — spray-carrier avoidance, uploaded 2026-08-08

Immutable policy-version UUID: `73caf241-9198-4245-bcf5-e9ddec986311`.
Uploaded with tag `purpose=spray-avoidance`. **Not submitted to any league** —
uploading is inert; submission is the gated human call.

- Parses identity-badge loadouts into visible players and persistent tracks,
  including truthful weapon, grenade, and shield state, plus the existing
  overhead barrier marker. `STENCIL_SHIELD_AWARENESS` gates the three revived
  shield consumers and the flee exemption without hiding state from telemetry.
- Adds the `clear_spray` objective below carry-home, thief interception, and
  grenade clearing. It uses a hysteretic keep-out radius, velocity-projected
  spray tracks, discrete supercover validation, and direct steering along the
  scored segment.
- Scores flee paths for geometric threat clearance, potential allied gun
  coverage, visible-teammate clumping, and conditional barrage centering.
  Coverage is point-wise and memoized by nav cell; barriers remain an explicit
  approximation because deployed barrier pickups are disabled.
- Adds the eight-character `S<team><identity><epoch><cell>` report with a
  dedicated 48-tick cadence and merge rules that preserve same-tick visual
  truth and fields absent from the report. V58 teammates ignore the new prefix.
- Prevents peek-duck, Hold separation, A* replanning, and spray pursuit from
  overriding the flee step. Fire-freeze is suppressed on both hold and trigger
  ticks only when a five-tick pause can enter lethal reach.
- Prioritizes spray carriers in gun target scoring and traces loadout belief,
  track provenance, live flee state, score terms, and the revised potential-gun-
  coverage grid.
- Pins the build to canonical Paintbot 0.7.215 / source
  `6c7a4c0e0be35bdcf738137595ccbcb4b4c79bf9` (GameVersion 41).

**Evidence status: none yet.** `stencil_nim` has no test suite, so seven staged
clean `linux/amd64` compiles are the only pre-upload signal; no runtime behavior
is verified. The first hosted signal is the mechanism probe
`xreq_33b25248-0e6b-4909-b903-fe4300253bb7` (2 episodes, all 16 seats v59,
canonical paintbot 0.7.216) — a **debug probe**, not campaign-shaped, so it is
excluded from gameplay claims by
[`../../docs/tournament-like-experience-requests.md`](../../docs/tournament-like-experience-requests.md).
It exists to answer only whether the mechanism fires: weapon tokens parsing onto
enemies, `shielded` ever becoming true (proving the repaired dead observable),
`clear_spray` activating and agents leaving the disc, no activation while
shielded, and the per-tick cost of coverage plus candidate validation. A matched
campaign-shaped A/B against v58 follows once the mechanism is confirmed.

**Built against 0.7.215 / `6c7a4c0e`, run on 0.7.216.** Canonical advanced during
the session (upstream #259, "Center the planted heart sprite on its grab point" —
sprite geometry only, no spray, movement, or observation change), so the build
pin deliberately lags the canonical version by one sprite-level release.

## v58 — barrage-center evacuation, uploaded 2026-08-07

Immutable policy-version UUID: `1f7f7c75-5edb-4b35-aba8-241264bbd611`.
Uploaded with tag `purpose=barrage-center`. Submitted to Paintbot on
2026-08-07 with auto-champion enabled; submission
`sub_a1298aee-c6d1-4141-bca4-b42133b3058e` was placed into membership
`lpm_c6ccaa63-6a6f-47c0-bea5-2a04ad6454fc`. Live readback showed the membership
competing, active, qualified, and champion; v54 became benched.

- Parses the GV41 `grenade barrage depth … rate … start … sat …` marker and
  folds its current values into belief state.
- Once `depth > 0`, routes each live Stencil agent toward the generated map
  center using the existing walkability-aware flow field and holds on entering
  the configurable 80-pixel central ring. Carry-home, heart-thief interception,
  and immediate grenade warnings retain higher priority.
- Suppresses peek-duck, formation drift, and spray pursuit while evacuating or
  holding, while retaining combat aim and fire. The behavior can be disabled
  with `STENCIL_BARRAGE_CENTERING=0`; its ring radius is controlled by
  `STENCIL_BARRAGE_CENTER_RADIUS_PX`.
- Traces the complete barrage marker and cumulative `barrage_center_ticks`,
  while objective transitions identify each activation.
- Pins the build to canonical Paintbot 0.7.211 / source
  `9dedac0ed6011aeca92bf2c6403b0e70c955f461` (GameVersion 41).

The `linux/amd64` image compiled successfully and was uploaded with
`STENCIL_TRACE_OUTPUTS=jsonl@artifact`, `STENCIL_TRACE_NAVIGATION=1`, and
`STENCIL_DIAG_EVERY_TICKS=1`. A one-episode, full 16-seat v58 mechanism probe
on GV41 `1v1` with a giant generated map completed successfully:
`xreq_34bd90b7-1d97-4dd1-a77f-aa1aabf975a6`, episode
`178292c1-a143-47a7-bdc7-c5fa0a5c985b`. All 16 agents activated
`barrage_center` within ticks 6602–6604 when the marker became positive and
targeted the generated center `[1605,856]`. Twelve reached and held within the
80-pixel ring; the other four resumed the route after each respawn but exhausted
all three lives before arrival. This validates marker consumption and determined
center routing, while leaving individual-grenade evasion as the next capability.
The probe is mechanism evidence only, not a performance comparison.

A 30-episode tournament-like evaluation was launched on 2026-08-07 against the
current Paintbot 0.7.212 campaign field and round-492 board cells. It contains
10 episodes per live map ref: five `1v1` cells with both captain seatings, five
`2v2` cells with both captain seatings, and ten `4ffa` cells with whole-color
Stencil ownership rotated across colors. No synthetic `4ffa8` game was added
because that map ref was absent from the live board. Requests:

All 30 episodes completed without operational failures. V58 finished 22-8:
6-4 on `1v1`, 9-1 on `2v2`, and 7-3 on `4ffa`, with 563 kills and 369 deaths
across its controlled seats. Because v54 was not run on the same cells and
opponents, this is absolute performance evidence rather than a matched A/B.

- `1v1`: `xreq_6605e638-8ea0-4fda-b956-446f4d519ceb`,
  `xreq_205efcb6-42f5-4aa3-b083-2c32ec692f42`,
  `xreq_bba704b5-a106-4456-8b65-eb42e76068fb`,
  `xreq_311a387f-b304-44f5-9f3b-5071ea93cb68`,
  `xreq_97c6da34-b84f-4030-afdf-b1c1b9f5770f`,
  `xreq_0325f0f7-1e9b-428f-9a8b-1e055b8c2240`,
  `xreq_a1b93e8a-f762-4fd0-8279-dc1957b05ea2`,
  `xreq_e6306df6-eb65-4f75-ac89-81f7887e44ff`,
  `xreq_1de5c88b-17ba-45e9-b68e-1e5304a8a3be`, and
  `xreq_95aa66c5-0d40-4773-bb94-22d3a2438b9e`.
- `2v2`: `xreq_d7722dc7-e33d-495e-840d-e0bd413b931f`,
  `xreq_2b739ed8-bcf2-4161-8311-24435fc62d86`,
  `xreq_51b1002d-7ca0-4778-809d-1edb11f3bec1`,
  `xreq_63a67dee-7bba-400a-9d72-ef97414e7f32`,
  `xreq_a6e947ba-e502-4b45-a445-fcc323408d24`,
  `xreq_1c390135-1e85-409f-a732-eedfc095fe95`,
  `xreq_c2c847b1-ea38-486d-a363-f38b6fbbc9e0`,
  `xreq_2543c34e-c4c5-48dc-bef1-80213c9d3d48`,
  `xreq_84ab3e35-54ff-423c-b27a-5107a969c567`, and
  `xreq_d628181a-fc08-4892-8191-c5fb669499b8`.
- `4ffa`: `xreq_251cf413-8842-4447-890d-b26836d674d2`,
  `xreq_ab2ef26c-fd0c-4058-aec0-fbb126f15d2a`,
  `xreq_c54901ae-6167-415f-873e-6dfac0e1c4f3`,
  `xreq_729eeb0e-c88d-4197-811b-94e015931355`,
  `xreq_91c12b52-72f7-40f0-82d6-2f49070b1abf`,
  `xreq_ea4ec521-64e0-42c2-bae8-ea4e879b5ece`,
  `xreq_7084c3bc-9b12-4c2b-abc2-ce80877584c8`,
  `xreq_55065723-f3aa-4895-add3-3ef4403ce99c`,
  `xreq_d2bcc4c8-8084-411a-bf5b-40b634ffa4d9`, and
  `xreq_8c28c84b-3f2b-475d-b60c-33cd3462d0ce`.

## v57 — full engine-rate communication, uploaded 2026-08-07

Immutable policy-version UUID: `c4a663a4-f6d4-4be4-92ca-cfffa891202e`.
Uploaded with tag `purpose=chat-engine-rate`; not submitted to a league.

- Reduces `STENCIL_CHAT_MIN_INTERVAL_TICKS` from 30 to the engine's exact
  24-tick shout cooldown, raising maximum protocol throughput from 0.8 to 1.0
  messages per second and removing up to six ticks of avoidable sender delay.
- Retains the existing message-specific cadences and strict sender priority;
  only the shared transport limiter changed.
- Pins the build to canonical Paintbot 0.7.208 / source
  `871ace1e5bd1a47171451e2ce3dc9004ee0a9c2b` (GameVersion 40). The game update
  adds initialization-time trench bounding-box markers; its shout contract is
  unchanged.

The `linux/amd64` image compiled successfully. Hosted evaluation has not run;
v57 is inert and v54 remains the active champion.

## v56 — restored belief tracing and ally coverage, uploaded 2026-08-06

Immutable policy-version UUID: `e49b4d94-6410-41bb-94c4-8120f05afca6`.
Uploaded with tag `purpose=belief-tracing-covered-heatmap`; not submitted to a
league.

- Restores complete belief snapshots for the replay viewer: enemy and teammate
  tracks, visible players, item and heard-event beliefs, presence ages, paths,
  objectives/orders, lives, and the downsampled danger heatmap.
- Decodes the fuzzed 16-step heading exposed by visible ally sprites and traces
  it with ally tracks.
- Adds a `covered` heatmap derived from currently visible allies' projected
  vision. It uses the conservative guaranteed vision cone and exact pixel-wall
  ray tests, so cover blocks projected line of sight.
- Updates the viewer to render the coverage heatmap, ally headings, and live
  heard-sound beliefs. Replay geometry continues to come from each replay's
  startup walkability map.
- Pins the build to canonical Paintbot 0.7.207 / source
  `c8fa5558fb9a5c83af4cf973da16913d6b06f2e4` (GameVersion 40).

V56 retains v55's rejected early-defense behavior; this upload exists to make
belief diagnosis complete, not as a champion candidate. The `linux/amd64`
image compiled successfully. A one-episode exact-source local diagnostic
confirmed non-empty 32-pixel danger and coverage grids and headed teammate
tracks, but is not gameplay evidence. V54 remains the active champion.

## v55 — covered spawn-box opening, uploaded 2026-08-06

Immutable policy-version UUID: `bc7c1079-5684-47b0-82b2-7d2f69e75089`.
Uploaded with tag `purpose=early-defense`; not submitted to a league.

- Adds a one-way opening phase enabled by `STENCIL_EARLY_DEFENSE=1`.
- Every agent takes a distinct wall-adjacent cover cell inside its exact
  generated endzone and suppresses peek, pursuit, separation, item, squad,
  convert, and steal movement while the phase is active.
- The phase ends permanently for that episode only after every still-live
  enemy team has strictly fewer aggregate lives than our team. Because all
  teams start with equal lives, the fog-independent team-score death counters
  provide the exact comparison without estimating roster size.
- Carry-home, own-heart-thief interception, and nearby-grenade evasion retain
  higher priority. Combat aim and firing remain active from cover, and an
  endzone-boundary clamp prevents combat micro from drifting outside the box.

The release image compiled successfully for `linux/amd64`. Hosted evaluation
against v54 has not run yet, so v55 is an unvalidated candidate and v54 remains
the active champion.

## v54 — GV40 continuous-aim controller, champion 2026-08-06

Immutable policy-version UUID: `cf88a169-2f85-403e-bb54-6b8bdc751ea5`.
Uploaded with tag `purpose=gv40-continuous-aim`.

Submitted to Paintbot with automatic champion promotion:

- submission: `sub_e52dd65c-717f-4aab-b761-d6e83189ccab`;
- membership: `lpm_890ebd66-ad82-48c3-93e4-c0a9d8d85e52`;
- terminal state: `competing`, `active`, and **champion** for James Botts.

- Pins the native build to canonical Paintbot 0.7.206 / source
  `ec244e6b01485e8c7acd7a7929a9268354d50957` (GameVersion 40).
- Replaces the obsolete GV36 32-slot/five-slot solver with signed
  shortest-angle steering at the deployed rate of 5 brads per held tick.
- Stops within a 2-brad deadband, the nearest representable result when a
  five-brad actuator cannot land exactly on an arbitrary integer target.
- Keeps exact `own aim <brads>` resynchronization, but removes the slot-grid
  error state and telemetry that no longer describe the game.
- Retains v52's accepted squad behavior. The controller correction applies to
  combat aim, scanning, spray alignment, and grenade post-input aim.

The previous controller could limit-cycle even on a static target: for example,
from 0 toward 37 brads it predicted 40-brad actions and could alternate around
the target while the real game advanced only 5 brads. The 0.7.206 sim and its
tests establish that every integer heading is legal and B/Select applies ±5.
The release image compiled successfully for `linux/amd64`. A six-episode,
campaign-shaped hosted A/B then placed v54 and v52 in both captain seatings on
round-381 cell `(0,0)` (`1v1`, seed `344807463`), with the live allied policies
held fixed. v54 won all six episodes. Its seven captain seats produced 137
kills / 24 deaths and 436 hits / 565 shots (77.2%), versus v52's 17 / 126 and
87 / 120 (72.5%). Exact-version replay expansion found 42,987 live v54 heading
changes: every one was exactly `+5` or `-5` brads. Immediate direction reversals
fell from 30,382 / 38,838 v52 turn ticks (78.2%) to 3,733 / 42,987 (8.7%). All
565 completed v54 gun actions retained their trigger heading across the
five-tick firing delay. Full evidence and request IDs are in
[`../../docs/reports/stencil-v54-gv40-aim-validation-2026-08-06.md`](../../docs/reports/stencil-v54-gv40-aim-validation-2026-08-06.md).

The controller correction was accepted and v54 replaced v52 as champion.

A subsequent round-383 top-champions field test ran six full-seat episodes on
each current map ref. v54 finished 13 wins / three draws / two losses, scoring
+26 with 351 kills / 214 deaths and 1,121 hits / 1,539 shots (72.8%). It swept
all six `1v1` games, went 4-1-1 on `2v2`, and 3-2-1 on `4ffa`. The sampled
`2v2` result was side-sensitive (3-0 as blue captain, 1-1-1 as red), while the
two FFA fields containing both daveey and relh yielded a draw and a loss. Full
design, exact versions, results, and request IDs are in
[`../../docs/reports/stencil-v54-top-champions-r383-2026-08-06.md`](../../docs/reports/stencil-v54-top-champions-r383-2026-08-06.md).

A larger round-385 field test then ran 60 full-seat episodes in the board's
26/26/48 proportions: 16 `1v1`, 16 `2v2`, and 28 `4ffa`, using all 19 other
active champions. V54 finished **49-3-8** (81.7% wins, 86.7% non-loss), +124,
with 1,283 kills / 513 deaths and 4,057 hits / 5,247 shots (77.3%). It went
14-0-2 on `1v1`, 15-0-1 on `2v2`, and 20-3-5 on `4ffa`. The earlier sampled
red-side weakness did not replicate. The clearest remaining failure was a
paired capture loss against Max Yankov on `1v1` cell `(3,2)` in both colors
despite favorable combat exchanges. Full design, integrity checks, results,
and all request IDs are in
[`../../docs/reports/stencil-v54-large-field-r385-2026-08-06.md`](../../docs/reports/stencil-v54-large-field-r385-2026-08-06.md).

## v53 — refresh regroup targets until contact, uploaded 2026-08-05

Immutable policy-version UUID: `0984111b-1a4a-41cd-9934-d4ebf2a7b6ba`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Retains v52's timeout-triggered rejoin and v51's conflict-free vote lock.
- Refreshes an active rejoin target every tick. Teammate tracks older than the
  existing presence-staleness window are ignored; without a fresh track, the
  agent keeps stepping homeward instead of holding at an obsolete coordinate.

v52 preserved safety and improved the worst live gap from four epochs/1,226
ticks to two epochs/555 ticks, but traces showed agents reaching stale
last-known teammate positions and holding there. v53's attempted target refresh
was rejected: it retained 24/24 adoption and zero conflicts but raised timeouts
from 13 to 36 and produced a four-epoch live gap lasting 967 ticks. The checked-in
source was restored to v52 behavior; v53 remains uploaded and unsubmitted only
as an immutable rejected experiment.

## v52 — regroup after a live consensus timeout, champion 2026-08-06

Immutable policy-version UUID: `409a341b-dfda-4c1c-8f66-01b7ce4eb82c`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`.

Submitted to Paintbot with automatic champion promotion:

- submission: `sub_9795e4b3-2db9-440c-a85e-74886dc442e5`;
- membership: `lpm_5753c1be-67c8-410f-bbce-67e857ec2c66`;
- terminal state: `competing`, `active`, and **champion** for James Botts.

- Retains v51's enforced vote lock and v50's forward-epoch resync.
- When a live member times out forming consensus, it now enters the existing
  bounded rejoin path toward the last observed squad position. Previously only
  respawns rejoined; ordinary shout separation fell through to independent
  role behavior indefinitely.

The v51 stress gate proved safety (24/24 artifacts committed/followed, 159
commits, 13 timeouts, 27 resyncs, zero conflicts) but one live member remained
four epochs behind for 1,226 ticks. Its trace showed the expired order fall
through to independent `to_post`/`hold_post`. v52 changes that timeout recovery
only. Its gate improved but did not bound live isolation. v53's follow-up
regressed that signal, so v52 was selected as the squad champion candidate.

## v51 — enforce the locked vote in quorum counting, uploaded 2026-08-05

Immutable policy-version UUID: `5f70ba1e-d447-4d35-b8d8-2101f3844b06`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Corrects v50's incomplete vote lock: proposal changes no longer replace the
  locked vote in the member's local vote table or quorum count.
- Retains v50's forward-epoch resynchronization and resync counter.

Three fresh giant-4FFA8 v50 episodes made the defect explicit: traces showed a
member record `W`, receive a late proposal, then replace its local table entry
with `M` two ticks later. Four same-epoch conflicts resulted. v51 fixed that
safety defect but was superseded by v52 after its liveness gate found prolonged
spatial isolation.

## v50 — locked votes and epoch resynchronization, uploaded 2026-08-05

Immutable policy-version UUID: `6987403a-ca99-4945-bfce-e83a62fe0490`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Locks each member's first vote for an epoch. Late proposals can no longer
  change a vote and allow overlapping quorums to commit different directives.
- Treats a fresh forward epoch (within half the 36-value wire ring) as evidence
  that a lagging member missed a commit, advances its local epoch, and restarts
  proposal collection there. Delayed older messages cannot move it backward.
- Adds `squad_consensus_resyncs` to artifact snapshots.

The v49 full-seat gate covered six 2v2, two 4FFA, and two 4FFA8 games: all 48
Stencil seats committed and followed orders (272 commits versus 45 timeouts),
but one three-member squad committed both move and watch at epoch 1 and two
isolated 4FFA8 seats ended two epochs behind with seven timeouts each. Those
observations directly motivated this refinement. The matched ten-game gate
removed its original conflict and cut timeouts from 45 to 24, but a subsequent
three-game giant-4FFA8 stress gate found four same-epoch conflicts because
quorum counting still used a freshly recomputed choice. v50 was superseded by
v51.

## v49 — convergent squad commit acknowledgements, uploaded 2026-08-05

Immutable policy-version UUID: `1f6612b0-a16e-4034-8b77-f241a61f3405`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Retains v48's leaderless squad consensus, tactical orders, generated-post
  execution, and cooperation traces.
- Adds a compact `C` commit acknowledgement. A member that observes quorum
  echoes the committed directive for 120 ticks; a peer accepts it only when it
  matches that peer's own vote or independently derived consensus choice.
- Records commit messages sent/heard. This closes the case where one member
  observed all votes and advanced its epoch while a peer missed one vote and
  remained permanently on the old epoch.

The representative v49 mechanic gate is recorded in
`../../docs/reports/stencil-v49-squad-consensus-experiment.html`. It was
refuted by a same-squad/epoch conflict despite universal adoption and was
superseded by v50.

## v48 — leaderless squad consensus and tactical orders, uploaded 2026-08-05

Immutable policy-version UUID: `ca6a5010-6a7e-4f47-b7d9-a0a87e758c98`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Enables tournament-aware squads by default. In 2v2, each Stencil squad pairs
  identities of the same entrant parity, never the allied policy that cannot
  speak Stencil's protocol; four-team games use groups of two or three.
- Removes designated leaders. Every member proposes an `H` (hold), `W`
  (watch), or `M` (move) directive, votes on a deterministic majority/medoid
  choice, and commits only after a quorum of identical votes. Ties prefer the
  safer order kind rather than a privileged sender.
- Advances through map-derived tactical fronts at 22%, 38%, 55%, 70%, and 84%
  route progress, alternating move and watch orders before the final pedestal.
  Missing squad presence proposes a hold/backoff instead of a solo rush.
- Each member selects a distinct generated firing/duck post near the agreed
  point. Existing danger-aware A*, cover movement, formation, combat,
  sightline sweep, and peek/fire/duck micro execute the order; emergency carry,
  theft, escort, grenade, item, and wipe behaviors retain priority.
- Adds compact `Q` proposal and `V` vote shouts plus `squad_consensus`,
  `squad_order`, and `squad_follow` trace events. Snapshots and counters expose
  membership, quorum, proposals, votes, commits/timeouts, chosen posts,
  arrivals, and per-order following time.

This was the first squad branch intended for representative full-seat random-map
play, but it was superseded before evaluation by v49's commit acknowledgement.
It deliberately starts from the checked-in tournament policy rather than
the v23-v47 giant-1v1 experiments, whose transient source and tests are not a
valid tournament baseline. The next test must be a full-seat 2v2/4FFA batch.

## v47 — giant guard Arc acquisition, uploaded 2026-08-05

Immutable policy-version UUID: `5bca7a62-d996-4f58-92eb-915ec7ea5d41`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`. Submitted to
the Paintbot league on 2026-08-05 with auto-champion `always`; placement
`sub_3767de5d-80d1-47c2-8053-a089517581d4` became the active James Botts
champion.

- Restores v26's exact-heart guard strategy and item thresholds.
- Before own-heart theft in giant 1v1, allows a discovered Arc within 500px
  route-to-item to be fetched despite `tactics_not_ready`, using own
  heart/pedestal as item anchor; all other items use existing thresholds.
- Once carrying Arc, suppresses automatic Arc pursuit when intent is
  `guard_heart` or `to_guard_heart`, so Stencil returns to and holds the exact
  heart position and uses the wide spray cone against Daveey's committed close
  pass. Arc pursuit for other intents remains unchanged.
- `STENCIL_GIANT_GUARD_ARC_MAX_ROUTE_PX` controls the acquisition threshold;
  behavior below 2700px map width is unchanged.

The target comes from v31 artifacts: v31 fetched Arc but then auto-pursued it
away from the guard position and went 2/20. This experiment isolates the
stationary wide-cone defense by suppressing pursuit during guard. Daveey's
close passes commit geometry; the wide Arc cone should land more hits than the
narrow gun.

Rejected after a fresh giant-map gate: 2/19 against Daveey v25, with one
episode still non-terminal. Fetching a nearby Arc and holding the heart did not
improve on v26's 6/20 exact-heart guard. Request
`xreq_f610a48b-6524-4b48-9c4e-fea2f00de3ab`.

## v46 — giant guard shield preparation, uploaded 2026-08-05

Immutable policy-version UUID: `6dac0b8a-2f31-4b21-8636-ec3039f4faa8`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart guard strategy and action behavior.
- Before own-heart theft in giant 1v1, allows already-discovered shield spawns
  on routes adding at most 400px versus going directly to the heart (using
  `itemAnchor = guard_heart` with a dedicated threshold).
- `STENCIL_GIANT_GUARD_SHIELD_DETOUR_PX` controls the detour; all other item
  kinds use existing thresholds. Behavior below 2700px map width is unchanged.

The target comes from v26 artifacts: all Daveey damage was exclusively gun;
every shield pickup blocked exactly 3 damage. Shield episodes went 2/4 wins
versus 4/16 without shield (small sample).

Mathematically rejected at 3/15 with five episodes still non-terminal. The
shield preparation hypothesis did not improve on v26's 6/20 baseline; episodes
with shields did not show the expected survival benefit. Request
`xreq_bbe187f1-ec2d-4358-a594-94d8f7d7c9b5`.

## v45 — giant guard combat strafe, uploaded 2026-08-05

Immutable policy-version UUID: `0f6f40ee-ca27-4494-8c09-71ebb96168e3`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart guard position and original `fireGate` (no veto,
  original close-range slack doubling).
- While the giant 1v1 guard has a visible enemy within `FirefightRadiusPx` of
  the heart, strafes on a small orbit (~48px tangent to enemy-to-heart vector,
  alternating sides every ~24 ticks) instead of holding stationary.
- The `guard_strafe` intent retains movement during `fireHoldTicks` (gun windup)
  so Stencil moves while shooting, forcing Daveey to track a moving target.
- `STENCIL_GIANT_GUARD_STRAFE_RADIUS_PX` and
  `STENCIL_GIANT_GUARD_STRAFE_PHASE_TICKS` control the orbit; behavior below
  2700px map width is unchanged.

The target comes from v26 artifacts: Daveey landed 64/82 shots (78%) when
Stencil moved <1px during his five-tick shot window, versus 50-56% when moving.
All Daveey damage was gun-based.

Rejected after a fresh giant-map gate: 5/20 against Daveey v25. The small-orbit
strafe did not reduce Daveey's hit rate enough to improve win rate over v26's
stationary guard. Request
`xreq_5ee32ca8-1e54-4c12-b58e-2ee630e94762`.

## v44 — guard-only close-range slack removal, uploaded 2026-08-05

Immutable policy-version UUID: `a9d45fc1-99b7-4d90-9fb2-326d81069daf`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Retains v43's rear-hemisphere veto and v26's exact-heart guard position.
- While `guard_heart` intent is active, removes the close-range slack doubling
  (uses 1x `FireSlackPx` instead of 2x inside `CloseRangePx`).
- Preserves the 2x close-range slack for all other intents and all Arc behavior.

The target comes from v26 artifacts: while intent was `guard_heart` and Daveey
approached at 150-220px (inside `CloseRangePx`), shots with 3 brads absolute
aim error landed only 2/52 hits because the doubled slack passed marginal aim
that missed at close range.

Rejected after a fresh giant-map gate: 3/20 against Daveey v25. Tightening the
close-range fire gate for the stationary guard reduced wasted shots but did not
improve hit rate enough to win more fights. Request
`xreq_b2d308f3-c9ed-4095-a4c4-4aa4b7d90915`.

## v43 — rear-hemisphere fire veto, uploaded 2026-08-05

Immutable policy-version UUID: `1b22adf4-f3d4-4ef0-8f7f-0dd0e75b8c66`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart guard position.
- Before applying lateral tolerance in `fireGate`, rejects targets outside the
  forward hemisphere (absolute aim error must be ≤64 brads, i.e. ≤90 degrees).
- Does not change strategy positioning, range behavior, Arc logic, or any
  non-gun fire gate.

The target comes from v26 artifacts: 34 shots with absolute aim error 100-128
brads (rear approaches near 180 degrees) landed 0 hits, caused by Daveey close
pass-throughs where the lateral-only geometric gate passed but the target was
effectively behind Stencil.

Rejected after a fresh giant-map gate: 4/20 against Daveey v25. The
rear-hemisphere veto reduced wasted shots but did not improve close-range hit
rate enough to recover wins. Request
`xreq_7cca0046-579c-4bce-a8da-3d17eb5bdeba`.

## v42 — giant close-range fire discipline, uploaded 2026-08-05

Immutable policy-version UUID: `f5930f53-a331-4a4f-9b4e-af25284ab519`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart position and cooldown evasions.
- While the `guard_heart` intent is active, tracks Daveey but withholds normal
  gun fire beyond 700 pixels, preserving cooldown for the close approach.
- `STENCIL_GIANT_GUARD_MAX_FIRE_RANGE_PX=0` disables the cap; `guard_range`
  traces gated shots. Behavior outside the giant guard is unchanged.

The target comes from v26 artifacts: wins landed 54/76 gun shots and losses
66/169; the losing 800-999px band landed only 2/51.

Rejected after a fresh giant-map gate: 3/19 against Daveey v25, with one
episode still non-terminal. Capping fire range beyond 700px did not preserve
enough cooldown to recover the 800-999px miss rate. Request
`xreq_9979aa86-1f18-45c0-8949-175f45e50275`.

## v41 — weakened-team forward guard, uploaded 2026-08-05

Immutable policy-version UUID: `269dda73-111a-4885-8116-e5c78ff65181`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Uses v26's exact-heart guard until Stencil earns the first kill.
- At two or one remaining Daveey lives, shifts the guard 400 pixels toward
  map center to force earlier repeat contact without starting a cross-map hunt.
- `STENCIL_GIANT_WEAKENED_GUARD_FORWARD_PX=0` restores v26's exact-heart
  control; behavior below 2700 pixels of map width is unchanged.

Rejected after a fresh giant-map gate: 3/20 against Daveey v25. Even after the
first kill, shifting 400 pixels forward exposed too much heart space and did
not create enough additional encounters. Request
`xreq_c2e6a3d1-8b19-41e1-a1c5-e06c724b9070`.

## v40 — giant post-first-kill hunt, uploaded 2026-08-05

Immutable policy-version UUID: `6819579e-2fe4-48da-9d56-a4c132f8881a`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart guard while Daveey is at all three lives.
- After Stencil's first kill leaves Daveey at two lives, bypasses the guard
  and reuses `convert_hunt` to pressure the predictable respawn before the
  late-game clock becomes the limiting factor.
- Uses the exact 1v1 scoreboard state rather than the unscaled conversion
  threshold; behavior below 2700 pixels of map width is unchanged.

Rejected after a fresh giant-map gate: 6/20 against Daveey v25. Starting a
cross-map hunt after the first kill recovered no win rate over v26 and conceded
the defensive position that generated its kills. Request
`xreq_256ea522-fd92-4733-a5b2-f2fa28e3097d`.

## v39 — giant exact last-life hunt, uploaded 2026-08-05

Immutable policy-version UUID: `656d85da-a96e-425c-ab10-34b0035811af`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart guard while Daveey has three or two lives.
- When the scoreboard reports exactly one enemy life, bypasses the guard and
  reuses the existing `convert_hunt` objective to pursue the winning third kill.
- Uses `enemyLivesLeft == 1` rather than the unscaled `wipeInReach` threshold;
  behavior below 2700 pixels of map width is unchanged.

Rejected after a fresh giant-map gate: 4/20 against Daveey v25. The hunt did
produce four three-kill wipes, but nine other losses still ended at exactly two
Stencil kills; in most, the second kill arrived around ticks 3500-4800, too
late for a cross-map final-life hunt. Request
`xreq_45a52aa3-444f-4bbd-a6a3-983d215d2c32`.

## v38 — giant final-life hunt, uploaded 2026-08-05

Immutable policy-version UUID: `fce3e2ca-b172-40c4-b2e9-f3e719f1f60d`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart guard and normal cooldown evasions while Daveey
  has more than one life.
- Once a wipe is in reach, lets the existing `convert_hunt` objective take
  precedence over the giant guard so Stencil pursues Daveey's last life.
- The change reuses `wipeInReach` and `convertHuntPoint`; behavior below 2700
  pixels of map width is unchanged.

The causal target came from all 20 v26 giant artifacts: every one of its six
wins was a three-kill wipe with no steal or capture, while the 14 losses
averaged 1.4 kills and frequently stopped at two because the guard suppressed
the existing final-life hunt.

Rejected before accepting hosted evidence: `wipeInReach` uses the unscaled
eight-seat threshold of six lives, so it is already true at all three starting
lives in 1v1. The guard was therefore bypassed from the start rather than only
on Daveey's last life. Request `xreq_31bf2791-fd8b-4719-85d7-dbcdb0e2c0fa`
was already created when the configuration mismatch was found; it subsequently
finished at 6/20, which does not change the causal rejection.

## v37 — giant leashed heart engagement, uploaded 2026-08-05

Immutable policy-version UUID: `1cea1e9b-0a57-4a4c-9af4-d06e3f24e1d2`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's cooldown evasions and exact-heart guard when no opponent is
  near the objective.
- When the visible 1v1 opponent comes within 600 pixels of the heart, engages
  within an 800-pixel leash rather than conceding initiative to the approach.
- `STENCIL_GIANT_GUARD_ENGAGE_RADIUS_PX=0` restores the v26 control;
  `leashed_engage` and `leash_return` trace activation. Behavior below 2700
  pixels of map width is unchanged.

Rejected after a fresh giant-map gate: 4/20 against Daveey v25. Closing on a
visible approach inside the heart leash gave Daveey favorable fights and
regressed below v26's stationary guard. Request
`xreq_bb4057c9-fe5e-48a4-a165-5edee62e46bd`.

## v36 — giant heart stand-ground, uploaded 2026-08-05

Immutable policy-version UUID: `62fc974c-fa52-4f2a-bf02-1a99fe2bbce3`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart guard and normal post-steal pursuit.
- While holding the heart, suppresses peek/duck displacement so Stencil keeps
  occupying Daveey's committed theft route and maintains its firing cycle.
- `STENCIL_GIANT_GUARD_STAND_GROUND=0` restores v26's cooldown evasions.
  Behavior below 2700 pixels of map width is unchanged.

Rejected after a fresh giant-map gate: 5/20 against Daveey v25. Suppressing
cooldown evasions did not improve on v26's 6/20 exact-heart guard; holding
still converted too many slips into lost stationary fights. Request
`xreq_c70ef567-e3ff-4327-9627-9ac99a89a2bb`.

## v35 — covered giant route ambush, uploaded 2026-08-05

Immutable policy-version UUID: `109de140-ce83-4b3e-85a3-0c94e4eec0fc`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores normal post-steal pursuit.
- Before theft, stages about 500 pixels along Daveey's actual approach route
  at cover within four navigation cells, forcing first contact before the
  exposed heart and retaining existing peek/duck micro.
- `STENCIL_GIANT_ROUTE_AMBUSH_PX=0` restores v26's exact-heart control;
  `to_route_ambush` and `route_ambush` trace activation. Sub-2700 behavior is
  unchanged.

Rejected after a fresh giant-map gate: 1/20 against Daveey v25. Leaving the
heart to force earlier corridor contact was substantially worse than guarding
the objective itself. Request `xreq_eec46f58-06ec-40a7-a88c-5f47a641f7d9`.

## v34 — predictive giant carrier intercept, uploaded 2026-08-05

Immutable policy-version UUID: `ed4038c3-9a55-43ce-8c87-5eda71c6176f`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Retains v26's exact-heart guard.
- After a giant 1v1 theft, leads Daveey by up to 600 pixels along his actual
  flow-field path, capped at half the remaining route, rather than chasing
  behind or conceding the capture boundary.
- `STENCIL_GIANT_LEAD_INTERCEPT_PX=0` is the control and
  `lead_intercept_thief` traces activation. Sub-2700 behavior is unchanged.

Rejected after a fresh giant-map gate: 3/19 against Daveey v25, with one
episode still non-terminal. A 600-pixel moving lead did not improve on the
original direct chase. Request `xreq_5ab1aab4-e100-4073-b994-a9e173e41d48`.

## v33 — giant carrier cutoff, uploaded 2026-08-05

Immutable policy-version UUID: `608bd7b6-bc55-4f47-8231-38da1ea66589`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart guard and removes the loadout/timing imitation.
- After Daveey steals on giant 1v1, routes directly to Daveey's fixed capture
  zone instead of trailing his current position, exploiting carrier slowdown
  and the observed 1127-1437 tick return commitment.
- `STENCIL_GIANT_CUTOFF_THIEF` is the control and `cutoff_thief_home` traces
  activation. Sub-2700 behavior remains v22-equivalent.

Rejected after a fresh giant-map gate: 3/19 against Daveey v25, with one
episode still non-terminal. Camping the fixed capture zone conceded too much
route and left a single scoring-boundary engagement. Request
`xreq_6a9be9c4-92d5-4df9-bfa7-915ecd39e84b`.

## v32 — loaded giant-map push, uploaded 2026-08-05

Immutable policy-version UUID: `23ca938d-b9bb-4832-8567-a30127823823`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Retains v31's giant-only spray acquisition and exact-heart staging.
- At tick 1400, explicitly pushes the enemy heart with
  `giant_armed_push`, matching Daveey's observed loadout-then-depart loop.
- `STENCIL_GIANT_ARMED_PUSH_TICK` controls timing. Sub-2700 behavior remains
  v22-equivalent.

Rejected after a fresh giant-map gate: 4/20 against Daveey v25. Combining
spray acquisition with Daveey's observed departure timing improved neither
piece enough to approach the target. Request
`xreq_b82f9db7-af2f-4359-9693-4d26c04ff634`.

## v31 — spray-armed giant heart guard, uploaded 2026-08-05

Immutable policy-version UUID: `c530ef34-034d-4d4e-9116-167c4d54328f`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart giant guard and v22's normal sweep behavior.
- Before guarding in giant 1v1, deliberately fetches a discovered Arc/spray
  weapon within 800 route pixels, matching Daveey's repeated early loadout.
- `STENCIL_GIANT_GUARD_ARC_MAX_ROUTE_PX=0` disables the capability and
  `fetch_giant_guard_arc` traces activation. Sub-2700 behavior is unchanged.

Rejected after a fresh giant-map gate: 2/20 against Daveey v25. Deliberate
spray acquisition alone did not improve the stationary heart guard. Request
`xreq_6f69e5cc-f3af-461f-b7f1-e389057d04a0`.

## v30 — route-aware giant heart guard sweep, uploaded 2026-08-05

Immutable policy-version UUID: `e4cefef5-1981-45b4-857d-58d5d15cc271`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v26's exact-heart giant guard.
- While no enemy is visible, centers the guard's sweep on the first flow-field
  waypoint toward Daveey's pedestal rather than the straight pedestal vector,
  facing the generated map's actual approach corridor.
- `STENCIL_GIANT_GUARD_ROUTE_SWEEP` is the control and `micro=route_sweep`
  traces activation. Behavior below 2700 pixels remains v22-equivalent.

Rejected after a fresh giant-map gate: 3/20 against Daveey v25. Route-facing
changed the pre-contact rotation path but did not improve the heart duel over
v26's straight-axis guard. Request
`xreq_93a79344-5c30-4a50-8326-eb40167f1aa8`.

## v29 — timed giant-map counterpush, uploaded 2026-08-05

Immutable policy-version UUID: `ca4ea1e6-fc24-452f-84b7-7cc6bb5de79d`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- In giant-map 1v1, guards the own heart through tick 1199, then explicitly
  targets the enemy heart with the `giant_early_push` intent.
- The tick-1200 push precedes Daveey's observed station-hold departures and is
  controlled by `STENCIL_GIANT_EARLY_PUSH_TICK`.
- Behavior below 2700 pixels of map width remains v22-equivalent.

Rejected after a fresh giant-map gate: 2/20 against Daveey v25. Explicitly
pushing before Daveey's observed departure window reproduced v22's 10% giant
win rate rather than disrupting Daveey's tempo. Request
`xreq_d9196fcc-ce65-48a0-9502-c35484504d78`.

## v28 — rear giant-map heart guard, uploaded 2026-08-05

Immutable policy-version UUID: `65dba88d-7b7e-49c5-a96e-90fb8aca5849`.
Same image as v27, uploaded with `STENCIL_SOLO_HEART_GUARD_FORWARD_PX=-200`
plus the standard trace settings; not submitted to a league.

- Positions the giant-map solo guard 200 pixels behind the heart, preserving
  heart coverage while extending the trailing-fire window on a retreating
  carrier.
- Behavior below 2700 pixels of map width remains v22-equivalent.

Rejected after a fresh giant-map gate: 5/20 against Daveey v25. The rear offset
did not improve on v26's 6/20 at the heart itself. Request
`xreq_53362eb8-8e7e-4e78-a3c7-de18d8925702`.

## v27 — forward giant-map heart guard, uploaded 2026-08-05

Immutable policy-version UUID: `3d32bab6-91c1-492f-9678-ee1a6523e7d9`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Retains v26's giant-only guard, but moves the guard point 400 pixels forward
  along the home-to-center axis so Stencil can engage before Daveey reaches the
  heart.
- `STENCIL_SOLO_HEART_GUARD_FORWARD_PX` controls the offset. Behavior below
  2700 pixels of map width remains v22-equivalent.

Rejected after a fresh giant-map gate: 5/20 against Daveey v25, down from
v26's 6/20 at the heart itself. Request
`xreq_75ccd6e8-f858-4432-afee-c57885f7004f`.

## v26 — giant-map solo heart guard, uploaded 2026-08-05

Immutable policy-version UUID: `143c88da-5287-4c3a-ab9d-a610036f9232`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v22 behavior unchanged below 2700 pixels of map width.
- On giant geometry, a solo agent guards its currently planted own heart (or
  the own pedestal fallback) instead of crossing the map to hunt. An active
  theft still takes the earlier interception path.
- `STENCIL_SOLO_HEART_GUARD_MIN_MAP_WIDTH` controls the geometry threshold;
  `to_guard_heart` and `guard_heart` intents trace activation.

The change targets the v22 giant baseline, where Stencil stole 5 hearts and
captured 2 while Daveey stole 19 and captured 9. It improved the fresh giant
gate to 6/20, but remained below the 50% acceptance threshold; request
`xreq_ad6e166d-bbb4-4a7d-8899-b8531158db52`.

## v25 — solo defender with heart objective, uploaded 2026-08-05

Immutable policy-version UUID: `94c05f94-e0b9-4c31-8b90-275ac3a5328a`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Keeps the sole 1v1 agent in the defender role, preserving defender-specific
  combat and heart-threat targeting, but bypasses the passive defensive-post
  objective so it advances on the enemy heart.
- Retains v23's roster-scaled conversion threshold and all existing
  own-heart-stolen interception behavior.
- Does not change combat, navigation, items, or multi-seat behavior.

Rejected after a fresh evaluation against Daveey v25: v25 scored 5W/1D/14L
small, 8/20 standard, 6/19 large, 1/19 huge, and 0/19 giant; one episode in
each of the latter three requests remained non-terminal. Keeping defender
targeting while advancing on the enemy heart did not recover the large-map
regression. Request IDs, small through giant:
`xreq_85eee21b-3943-4b08-8c25-87d760e52dcb`,
`xreq_ce2ea110-61fd-4cf7-90d0-aba010dfeacf`,
`xreq_39f5861c-7dc5-41bc-af1c-7eecd7488dab`,
`xreq_74282ccd-eed9-4611-b985-24fd6f79e454`, and
`xreq_b277f7a8-1cce-4116-9276-11838df24368`.

## v24 — solo attacker role, uploaded 2026-08-05

Immutable policy-version UUID: `e8376377-9c9b-4dcf-a6e4-2c8b79b3f954`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Assigns the sole agent on a one-seat team to the attacker role so normal
  objective selection pursues the enemy heart.
- Retains v23's roster-scaled conversion threshold. Own-heart-stolen
  interception still precedes role-specific strategy, so the solo attacker
  continues to defend an active theft.
- Does not change combat, navigation, items, or multi-seat role assignment.

Rejected after a fresh evaluation against Daveey v25: v24 scored 10/20 small,
8/19 standard (one episode remained non-terminal), 7/20 large, 0/20 huge, and
0/20 giant. The offensive role helped on small maps but removed defender combat
and heart-threat behavior, producing complete failure on the two largest map
sizes. Request IDs, small through giant:
`xreq_1b677d35-1aef-4fda-b160-f6aa4a021a42`,
`xreq_a5d36241-84e3-459e-9a75-05d00121f9b8`,
`xreq_b12f6597-6566-428e-800f-42ca1bfa21a4`,
`xreq_e86d942d-1bb3-4e1d-88aa-876dad6734c2`, and
`xreq_1e2254ef-ff22-4fe4-8208-8cf407b28d9d`.

## v23 — roster-scaled conversion threshold, uploaded 2026-08-05

Immutable policy-version UUID: `2683f8b3-0ebd-4cab-999d-b0e11cc9c9cd`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Scales the conversion-hunt threshold from its eight-seat reference instead
  of applying the six-life default unchanged to every roster size. In 1v1,
  conversion now begins with one enemy life remaining rather than at spawn.
- Does not change combat, navigation, roles, items, or the normal heart
  objective.

The pre-change v22 baseline against Daveey v25 was 7/20 small, 11/20 standard,
10/20 large, 11/20 huge, and 2/20 giant. Giant-map telemetry showed
`convert_hunt` active for nearly every live tick because all three starting
enemy lives satisfied the unscaled six-life threshold.

Rejected after a fresh 20-episode-per-size evaluation against Daveey v25: v23
scored 8/20 small, 10/20 standard, 5/20 large, 2/20 huge, and 1/20 giant. The
threshold fix exposed a second root cause: the only 1v1 seat remained a
defender and returned to its post instead of pursuing the enemy heart. Request
IDs, small through giant: `xreq_bf6ba117-b2ff-4f87-bef0-4dbceee1d2b4`,
`xreq_97050d4e-4cbf-4a92-a021-4ac2bdaffc86`,
`xreq_88cda4b2-8c33-41f7-8f6c-589aed07c86e`,
`xreq_67708e8c-bc6d-4264-9680-a10384fc6e50`, and
`xreq_16813a19-89aa-4fc9-be62-a61097fd6876`.

## v22 — exact 32-slot own-aim readback, uploaded 2026-08-04

Immutable policy-version UUID: `74d04f89-43f0-4968-bc94-787e81f982cd`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`.

Submitted to Paintbot on 2026-08-05 with automatic champion promotion:

- submission: `sub_97082b2c-88ab-4fb2-8ae2-63ee17c4402a`;
- membership: `lpm_f0764d92-c162-4a1d-be5e-fb4cf0e9833b`;
- terminal state: `competing`, `active`, and **champion** for James Botts.

- Reads the authoritative Sprite-v1 `own aim <brads>` marker for Stencil's gun
  angle. The prior code inferred aim from the self soldier sprite, which has
  only 16 visual rotations and therefore erased every odd slot from GV36's
  32-slot gun.
- Keeps the sprite-derived angle only as a compatibility fallback. Strategy,
  roles, movement, target selection, lead prediction, and the fire gate are
  unchanged.

The pre-change hosted trace logged about 1,450 aim resyncs in one episode and
reported only multiples of 16 brads despite the live gun's 8-brad slots.

Accepted after a fresh matched 18-episode-per-arm A/B against v21 on six locked
4FFA maps under deployed Paintbot 0.7.186. Replay-expanded gun accuracy rose
from 488/916 (**53.3%**) to 847/1,140 (**74.3%**). Released shots increased
24.5%, kills increased from 177 to 299, and combat deaths fell from 203 to 195.
Every map cleared 70% accuracy (70.1%-80.9%). Wins rose from 3/18 to 7/18.
Across 72 agent traces per arm, cumulative aim resyncs fell from 85,885 to 196.

Request IDs, in small-corners, small-plus, standard-corners, standard-plus,
large-corners, large-plus order:

- v21: `xreq_2479eff3-a2ce-48e0-9c98-8e92c7ece424`,
  `xreq_a5d87427-3d17-4870-bb9a-0ddd8c8b4b98`,
  `xreq_fa1406f4-1550-491b-a55c-1674a0edb230`,
  `xreq_e36fbedd-1e39-4008-8dba-3a1de3bbc1c5`,
  `xreq_922e008a-ae02-4cf7-a498-108bd8ccd792`, and
  `xreq_4ecec622-bbaa-4243-8261-a251c02ef16d`.
- v22: `xreq_3d506be2-cff3-4a12-ba55-2ba2795d3563`,
  `xreq_cbf8d509-5a1e-4feb-87d9-5a3354b057eb`,
  `xreq_ecada834-afb2-4ade-839d-59c7403d9fb7`,
  `xreq_bbce90e2-e355-41ce-8bf9-a66516bbea81`,
  `xreq_770cd6b7-0b82-4971-a166-0aca2392acac`, and
  `xreq_e29d5d6f-0e4f-4885-8924-6d84e3d00025`.

All 36 episodes completed without an episode failure. Full analysis:
`docs/reports/stencil-aim-accuracy-2026-08-04.md`.

## v21 — visible-carrier target override, uploaded 2026-08-04

Immutable policy-version UUID: `da064362-fc5a-4902-9a04-b33b00d9005b`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Retains v20's accepted heart-threat score. Once the heart is stolen, a
  high-confidence, shootable carrier match now overrides competing generic
  targets and bypasses the normal eight-tick target latch.
- `STENCIL_DEFENSIVE_CARRIER_THREAT_MIN` controls the match threshold. End
  counters expose weighted-score overrides and immediate carrier switches.
- Does not change roles, movement, objectives, posts, cover, aim, or the fire
  gate.

Accepted after two independent fresh matched batches against v20 on the same
six locked 4FFA maps, three episodes per map and arm. Both batches improved
from 4W/0D/14L to 5W/0D/13L. Combined, defender kills rose from 4.78 to 6.67
per episode (Welch p=0.024), defender deaths fell from 5.06 to 4.86, replay hit
rate rose from 47.8% to 52.5%, and red-heart steals fell from 51 to 45. The
outcome change from 8W/0D/28L to 10W/0D/26L was directional but not significant
(Fisher p=0.786).

The mechanic activated narrowly and as designed: 77 weighted-score overrides
and 174 immediate carrier switches across 28,168 multi-target defender ticks.
All 26 v21 losses occurred after Stencil had recovered its own heart or never
lost it; the remaining all-map loss mode is third-party FFA capture, outside
this fixed-strategy mechanics iteration.

First-run v20/v21 request IDs, in small-corners, small-plus,
standard-corners, standard-plus, large-corners, large-plus order:

- v20: `xreq_b5fb272e-42ba-4c3d-954c-969d23242d93`,
  `xreq_9f476a6e-a658-4a7b-a7db-1051a2eb6b0f`,
  `xreq_6bb863e7-4cb0-4d1b-9cc2-402a44bbd3dd`,
  `xreq_e411d17f-bf8f-464f-96f6-d251aefa196d`,
  `xreq_afb6c9ec-ead2-4dcd-9550-1adc4befae85`,
  `xreq_ec4701bd-fec5-4279-b66e-1add00caa7c0`.
- v21: `xreq_900110b7-3345-40b6-bda7-89965c414394`,
  `xreq_46ad41e8-c6b4-4e82-8bcb-929f19f93be2`,
  `xreq_768d32da-5c0a-4075-a9c8-daabbe3fe5a0`,
  `xreq_7b028023-d216-4df0-897d-9e291252c4be`,
  `xreq_002bec69-d457-4672-8a70-9e5cba67a4ab`,
  `xreq_832a833a-7667-41fb-a4f3-dbf8baec7633`.

Replication request IDs in the same order:

- v20: `xreq_b45c5327-4f75-45be-8770-dde23293210c`,
  `xreq_f561dfa2-0f54-4d72-83f8-fa45972d0fa6`,
  `xreq_85896369-4933-4f01-ad49-73451299d358`,
  `xreq_12df2f52-436e-45b6-a9e7-13848e055168`,
  `xreq_e8a28dea-3e0b-4497-9924-79dea573a580`,
  `xreq_732201fa-4790-4704-b85c-fa5a81f0b83c`.
- v21: `xreq_216efd5a-dfaf-4602-b7e0-e981c7e695bc`,
  `xreq_bc668bf5-da4c-4142-a14e-71f1e1c21766`,
  `xreq_11e5e195-68cc-4fc9-bebe-2f9276b95c24`,
  `xreq_d5b7d747-a947-4722-9a5e-0afdbd4388bf`,
  `xreq_6a7b32e2-85fb-4e5a-b1cc-df235220567a`,
  `xreq_dd569dba-1b42-43fc-b072-3ffe4e453d48`.

All 72 episodes completed and every artifact bundle was fetched. W/D/L was
computed from the four-team `results.json` win vectors, not the warehouse's
red/blue-only legacy `episodes.winner` projection.

## v20 — defensive heart-threat target selection, uploaded 2026-08-04

Immutable policy-version UUID: `bf6f3048-4fa2-4015-bf75-dc7bf0928149`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Changes only defender gun-target scoring. Before a theft, visible enemies
  receive a bonus that increases with route progress toward Stencil's heart;
  after a theft, the bonus identifies the visible enemy nearest the observed
  thief position. Roles, movement, objectives, post generation/assignment,
  aim, and the fire gate are unchanged.
- `STENCIL_DEFENSIVE_TARGETING`,
  `STENCIL_DEFENSIVE_TARGET_THREAT_WEIGHT`,
  `STENCIL_DEFENSIVE_TARGET_THREAT_RADIUS_PX`, and
  `STENCIL_DEFENSIVE_THIEF_MATCH_PX` isolate the new mechanic.
- Full snapshots expose the selected enemy, team, original generic score,
  defensive threat bonus, and heart distance. End counters record multi-target
  defender ticks and cases where the new term changes the top-scored target.

Accepted after two fresh matched runs on the same six locked 4FFA maps, three
episodes per map and arm. Combined results improved from v19's 2W/1D/33L to
8W/2D/26L (episode-level non-loss Fisher p=0.063). Defender kills rose from
5.11 to 6.42 per episode and team kills from 8.92 to 11.00. The term changed
the generic top target on 1,771 of 26,150 multi-target defender ticks (6.8%).

The tradeoff is lower precision and slightly higher defender mortality: replay
hit rate fell 61.0% to 51.0%, while defender deaths rose 4.36 to 4.97 per
episode. The added volume still produced more hits, kills, wins, and non-losses
in both independent batches. Red-heart steals fell only 43 to 40, so this is a
combat-output improvement rather than a clean theft-prevention result.

First-run v19/v20 request IDs, in small-corners, small-plus,
standard-corners, standard-plus, large-corners, large-plus order:

- v19: `xreq_caa6084e-0177-4011-b694-987ada8f260a`,
  `xreq_48a5714f-f5b9-4b2b-a6a3-185723d28882`,
  `xreq_37ee6e25-7d56-4af5-8cda-88108b02f5e4`,
  `xreq_f381e238-4ce4-41ba-9843-3b7060fc300e`,
  `xreq_e3c0fa37-053d-4a83-8525-b00ab93c1ddc`,
  `xreq_1924b415-3b08-47bd-b365-91956cda8746`.
- v20: `xreq_887e9059-6e79-4bbc-952b-d01ca3935c44`,
  `xreq_c5e35a0c-a62a-4fc6-a486-8c69d6ecec30`,
  `xreq_82acaf8d-9b6d-4d47-9300-bdd597c3e991`,
  `xreq_e651caf9-bebb-4372-8704-d9a6b9ab526d`,
  `xreq_25340901-b7a0-4287-9363-16105087feb5`,
  `xreq_588ca6df-68f4-43a6-817e-445f10e94b21`.

Replication v19/v20 request IDs in the same order:

- v19: `xreq_889e8609-f7d6-46ba-803b-e4673cdc3ce0`,
  `xreq_5dd5b6ac-a6d2-41fb-b8ab-aae8ac585fa8`,
  `xreq_f8e78291-6536-452d-a58c-058892706137`,
  `xreq_5c68f7b0-3423-42f4-bf2f-20a5ed856556`,
  `xreq_e273a730-7ed6-42f8-b185-a3451a80424f`,
  `xreq_aaf8e7f4-53dd-4886-a7ac-fc20f3bae1df`.
- v20: `xreq_689ee7ff-ad50-4a70-a0ce-7939539dc8a8`,
  `xreq_b7e15319-1df6-43b6-b18b-39832d0699b5`,
  `xreq_b1ce8500-e040-4724-a7d9-a985f6b15d52`,
  `xreq_f3841c61-ae75-465e-93eb-e65142b0a0c8`,
  `xreq_4fdbeb86-44c5-4cac-895f-ec26287dd4ab`,
  `xreq_fae640d2-7a52-4bca-ae4f-6eab54343557`.

All 72 episodes completed and all requested artifact bundles were fetched.
The warehouse's legacy `episodes.winner` projection only understands red/blue;
the W/D/L verdict above comes directly from the four-team `results.json` win
vectors.

## v19 — accepted behavior + complete defense diagnostics, uploaded 2026-08-04

Immutable policy-version UUID: `e1b5dfa1-6755-4c4f-99ac-1582dfceec94`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Behavior is identical to v13/v12: accepted five-slot aim, exact homeward post
  ordering, and the existing live-threat cover micro.
- Retains v13's per-tick fire-gate inputs/reason and adds the generated post's
  center sightline point as trace-only `defensive_post_sightline_aim`.
- The navigation viewer now overlays this agent's assigned post, paired duck
  point, and scored sightline axis on the generated map knowledge.
- v14-v18's rejected alignment strafe, wider fire gate, paired-post duck,
  home-banded ranking, and runtime sweep-axis changes are absent.

This is the accepted fully traced inert upload after the mechanics search. It
has not been submitted to a league. Two one-episode runtime probes on canonical
Paintbot 0.7.184 completed with no failed episodes and emitted the new
assignment/sightline fields for both defenders: standard-corners seed 303
(`xreq_6606c47a-731e-4bcc-8153-acaf2127b589`) and large-plus seed 606
(`xreq_4af94dbe-e965-410b-a0d9-a4b7194b336a`). Both episodes were losses to
richard, consistent with the accepted baseline's unresolved 4FFA limit; these
probes validate tracing and rendering, not an outcome improvement.

## v18 — rejected post-corridor sweep axis, uploaded 2026-08-04

Immutable policy-version UUID: `5bef60d2-3c31-4297-87f7-80bcb3b95359`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v13's post assignment, firing, and cover behavior and retains its
  fire-gate diagnostics.
- A posted defender now centers its idle sweep on the middle ray of the
  generated post sightline. Previously generation scored rays along the next
  route waypoint, but runtime aimed directly at the distant opponent pedestal,
  which could point through a bend or wall.
- Adds `defensive_post_aim` to each snapshot so the exact runtime sweep axis is
  visible beside the navigation-map rays.
- Does not change strategy, roles, objective priority, post selection, target
  selection, or active target aiming.

Across the 36 v13 assignments in the locked field, the old runtime axis differed
from the scored center ray by median 9.8 degrees and mean 23.2 degrees; six
assignments exceeded 45 degrees and three were 90 degrees off.

Rejected after the matched 18-episode-per-arm six-map evaluation. Defender hit
rate rose from 51.05% to 55.15% and deaths fell from 5.11 to 4.89 per episode,
but defender kills fell from 6.44 to 4.72 and outcomes fell from 3 to 2 wins
(Fisher p=1.0; defender-kill Welch p=0.194). The runtime sweep change was
removed; the generated center ray remains trace-only navigation knowledge.

## v17 — rejected home-banded post score selection, uploaded 2026-08-04

Immutable policy-version UUID: `d2127c91-28d3-4056-bcb7-d3eca7f13e25`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v13's firing and cover behavior and retains its diagnostic fields.
- Preserves homeward post selection, but groups candidates into 64 px
  home-distance bands and ranks by the generated sightline/corridor/duck score
  within a band. Previously score only broke an exact-distance tie, so the
  generated metric was usually ignored during assignment.
- `STENCIL_POST_HOME_BAND_PX` controls the local band size.
- Does not change strategy, roles, objective priority, target selection, or
  post generation.

Rejected after the matched 18-episode-per-arm six-map evaluation. Assignment
changed on small and standard maps, but the outcome shift from 3 to 4 wins was
noise (Fisher p=0.691), and the defensive mechanism was flat: defender kills
6.44 to 6.22, deaths 5.11 to 5.17, and normalized fire 7.58 to 7.50 per 1,000
alive ticks. The team-kill increase from 10.17 to 11.78 came from attackers,
not the changed posts. Exact homeward ordering was restored.

## v16 — rejected paired post-duck cover, uploaded 2026-08-04

Immutable policy-version UUID: `0db06dde-21c9-45f6-aeac-839297fdcf00`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v13's firing behavior and retains its diagnostic fields.
- When a defender is holding a generated post and its gun is cooling down, it
  uses that post's generated duck point if the point is reachable and blocks
  the current threat ray. Otherwise the existing live-threat cover search
  remains the fallback.
- `micro=post_duck` and `defensive_post_duck_ticks` trace activation.
- Does not change strategy, role assignment, objective priority, post
  selection, target selection, or firing behavior.

Rejected after the matched 18-episode-per-arm six-map evaluation. v16 activated
`post_duck` for 127 defender ticks and increased normalized defender firing
from 7.58 to 8.50 shots per 1,000 alive ticks, but defender hit rate fell from
51.05% to 45.05% and defender kills fell from 6.44 to 4.67 per episode. The
outcome moved from 3 to 4 wins (no draws), which was noise at this sample size;
defender-kill Welch p=0.109. The paired-duck runtime behavior was removed.

## v15 — exact gun-hit corridor, uploaded 2026-08-04

Immutable policy-version UUID: `0f2f918b-504b-4661-8bd1-79e823070eda`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Keeps v13's behavior and fire-gate diagnostics, except that the gun alignment
  gate now uses the live simulation's exact centered-body hit corridor:
  `PlayerHalf` (6 px) + `BulletHalfWidth` (8 px) = 14 px.
- Removes the old guessed split of 8 px beyond 220 px and 16 px within it.
- Does not change strategy, role assignment, post selection, target selection,
  movement, cover use, or objective priority.

Rejected after the matched 18-episode-per-arm six-map evaluation tied v13 at
3 wins / 15 losses. Defender kills fell from 6.44 to 5.44 per episode, while
defender deaths fell from 5.11 to 4.61; neither combat change was significant
(Welch p=0.471 and p=0.384 respectively), and the outcome Fisher p-value was
1.0. The wider gate modestly raised hit rate (52.75% to 54.70%) but lowered
normalized defender firing from 7.58 to 5.83 shots per 1,000 alive ticks. The
fire-gate change was removed; v13's diagnostics remain.

## v14 — rejected cover-preserving discrete-aim alignment, uploaded 2026-08-04

Immutable policy-version UUID: `1706a574-4c47-46d2-860d-3adcbe38c250`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- When a defender holding its assigned post has a ready, unobstructed target
  that no legal aim slot can hit from the current position, it may strafe to
  the nearest walkable cover cell within three nav cells where a legal slot
  intersects that target.
- Does not change strategy, role assignment, post selection, target selection,
  or objective priority. `STENCIL_AIM_ALIGN_STRAFE=0` disables the mechanic.
- `micro=aim_align` and cumulative `aim_alignment_strafe_ticks` trace
  activation. The v13 fire-gate probe motivated the change: aim alignment was
  the dominant visible-target blocker (1,858 ticks), and 943 cases could not
  be solved by rotation alone; at `hold_post`, 173/323 blocked ticks were
  geometrically unshootable from the current point.

Rejected after the encouraging six-game screen failed replication. In the
matched 18-episode-per-arm six-map field, v13 went 3 wins / 15 losses while v14
went 1 win / 17 losses (loss/non-loss Fisher p=0.603); defender kills fell from
6.44 to 5.06 per episode and team deaths rose from 10.78 to 10.94. The candidate did
raise attacker kills and produce four captures, but those are outside the
defensive-mechanics target and did not improve outcomes. Its movement code was
removed before v15.

## v13 — fire-gate diagnostic probe, uploaded 2026-08-04

Immutable policy-version UUID: `46cb093a-5310-4ace-9dcf-6d9d0b88f755`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Behavior is identical to v12.
- Adds per-tick target range, nearest-slot angular/lateral error, fire-ready
  state, ray-clear and teammate-blocked inputs, and a normalized fire-gate
  reason (`cooldown`, `aim_alignment`, `wall`, `teammate`, `fire`, or trigger
  `release`).
- Purpose: distinguish the dominant cause of visible-but-not-firing defender
  ticks before changing aim movement, cover micro, or fire cadence.

## v12 — accepted aim fix + observable homeward posts, uploaded 2026-08-04

Immutable policy-version UUID: `5889dc2e-170a-4082-8f52-b149333d552a`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Preserves v9's strategy and homeward-ranked defensive-post behavior while
  retaining the accepted 32-slot/five-slot aim controller.
- Adds trace-only `defensive_post_heart_distance` and
  `defensive_post_forward` fields so a post selection can be judged directly
  without changing how it is selected.
- Reverts v10/v11's post-ranking experiments after the locked-map A/B showed
  that forcing defenders farther forward reduced combat output.

Two final hosted probes on canonical Paintbot 0.7.184 completed without
failure. On locked small-plus 4FFA seed 202, v12 won `+4` against daveey,
richard, and Andre (`xreq_af902ca9-55b0-4168-94c7-b0f77e9a946a`). On locked
standard-sides 2v2 seed 808, v12 and richard won `+2` against daveey and Andre
(`xreq_4eae7ddd-79dd-40c9-b42f-8769730da1cb`). Defender traces contained
generated post coordinates, associated opponent fronts, score, heart distance,
and forwardness; attacker traces contained no post assignment.

## v11 — rejected forced-forward post ranking, uploaded 2026-08-04

Immutable policy-version UUID: `4b731d4c-2c6c-4b83-a05a-2bed892b7db2`;
never submitted.

- Restricted defender assignments to generated posts forward of the heart and
  within gun range of it, then ranked those candidates by post score.
- Added trace fields for the selected post's heart distance and forwardness.
- Activation was correct: all 12 defender assignments in the locked 4FFA
  matrix reported `defensive_post_forward=true`.

The six-map locked 4FFA A/B rejected the behavior. v9 drew one and lost five;
v11 lost all six. More importantly, v11 fell from 285 shots / 156 hits / 56
kills (54.7% hit rate) to 205 / 90 / 23 (43.9%). Both arms recovered all seven
observed thefts of Stencil's heart, so the forward constraint did not improve
the defense mechanism it was meant to strengthen. In the separate locked
four-map 2v2 matrix both versions won all four, which was insufficient to
rescue the clear 4FFA combat regression.

## v10 — rejected opponent-route post ordering, uploaded 2026-08-04

Immutable policy-version UUID: `284654a3-507d-4504-bd46-0cba8b2bcf29`;
never submitted.

- Assigned distinct opponent fronts and ranked posts by the shortest enemy
  route to the defended heart.
- Initial score comparisons were run with the generic `seed` field. Inspection
  showed that this did not lock Paintbot terrain: reproducibility requires
  `mapSeed`, `mapSize`, and `mapLayout`. Those comparisons were therefore
  discarded rather than treated as evidence, and v11 was evaluated with a
  properly locked matrix.

## v9 — deployed five-slot aim controller, uploaded 2026-08-04

Immutable policy-version UUID: `30ee0431-1f3d-4ecd-9686-208c3894a1f4`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Models the live 0.7.184/GV36 combination exactly: 32 aim slots and the
  variants' explicit `aimTurnRate=5`, yielding a 40-brad jump per held tick.
- Replaces greedy angular-sign turning with modular slot routing. It compares
  the number of +5 and -5 slot commands required to reach the nearest target
  slot, preventing unreachable-angle oscillation.
- Keeps defensive strategy, generated posts, cover decisions, target
  selection, and fire gating unchanged. Full traces retain v8's aim target,
  error, grid error, and authoritative wire resync fields.

Against the current top 4FFA field over eight natural generated maps, v9 won
two, drew one, and lost five versus v7's zero wins, three draws, and five
losses. Replay-derived combat improved from 4.63 to 11.13 kills/episode and
from 20.9% to 51.5% hit rate; deaths fell from 10.13 to 8.50 per episode.
Stencil captured four hearts versus zero for v7. Both arms experienced 1.13
own-heart steals per episode, and all nine v9 thefts were returned before a
capture. Requests: v9 `xreq_c104f2ee-625f-4bbb-a9ee-c245f50e0c86`; v7
`xreq_4d287287-945f-40f8-89a1-ea85a267b746`.

## v8 — rejected incomplete GameVersion 36 compatibility, uploaded 2026-08-04

Immutable policy-version UUID: `c849fad4-645a-44ca-8c7f-32e7f0358525`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Pins canonical Paintbot 0.7.184 at source ref
  `352d0e5408245710874abcfb861ad88491156238` (GameVersion 36).
- Updated Stencil's aim integrator from the removed 5-brad continuous turn to
  an assumed one-slot / 8-brad step and made each wire marker authoritative.
  Live XP episode configuration then showed that 0.7.184's variants still
  explicitly set `aimTurnRate=5`; under GV36 that means five slots / 40 brads.
  v8 was therefore rejected before evaluation.
- Adds per-tick `aim_target_brads`, `aim_error_brads`, and
  `aim_grid_error_brads` tracing. Strategy, roles, objectives, posts, cover,
  target selection, and fire gating are otherwise unchanged.

The v8 request `xreq_1d7e54b5-af94-4a4a-a7da-1b0f81961b08` was cancelled
before any episode completed. Baseline request
`xreq_2833a2c2-2036-4e16-8bf4-427763938bb4` continued for diagnosis.

## v7 — distinct homeward-ranked defensive posts, uploaded 2026-08-04

Immutable policy-version UUID: `91cd9b6d-df02-4887-8ed0-24cc8379030b`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Deduplicates the generated post union and ranks it by Euclidean distance from
  the team's home center, then assigns defender seat N to rank N. This fixes v6's
  duplicate assignment while keeping the behavior explicitly defensive.
- Defenders travel to and hold their assigned post, sweeping toward the
  associated opponent front. Heart-theft interception remains higher priority;
  attackers are unchanged; generic choke cover is the no-post fallback.
- `STENCIL_DEFENSIVE_POSTS=0` disables the behavior. Traces expose assignment,
  duck cell, opponent, score, travel/hold ticks, and fallback count.

Four paired hosted `2v2` episodes used the same standard-sides map (seed 707),
with v7 and v5 each playing both colors. All completed without failures. Across
12 v7 defender-episode assignments, every defender emitted `to_post`, 10 reached
`hold_post`, all assigned positions were distinct within a team, and fallbacks
were zero; all 20 attacker-episode assignments remained unposted. The result
split 2-2 and is too small for a win-rate conclusion.

Requests: red v7 `xreq_688bd557-c881-479d-995e-988e12911cef`; blue v7
`xreq_0e1f7106-58ca-4263-9f7e-4cbea6a97a94`.

## v6 — initial defensive-post assignment, uploaded then rejected 2026-08-04

Immutable policy-version UUID: `794f3db1-f552-43d5-b1a8-f9b7f9ec1a2e`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Each defender attempted to snap its hold target to the generated post nearest
  its old seat-spread lane. If a map produces no usable post,
  that defender falls back to the old geometry-derived choke cover.
- Posted defenders sweep toward the opponent front used to generate their
  position. Heart-carrier return and heart-thief interception remain above the
  posting rung in the objective ladder.
- `STENCIL_DEFENSIVE_POSTS=0` disables the behavior for controlled comparisons.
  Full traces expose the assigned position, duck cell, opponent, post score,
  travel ticks, hold ticks, and fallback count.

Hosted tracing found two problems. `1v1` never reaches the defender rung because
its three enemy lives immediately activate the higher-priority convert hunt, so
its 7-4-1 result against v5 is not post-defense evidence. In paired `2v2`, post
behavior did activate but defender seats 0 and 1 sometimes chose the same point.
v6 was rejected and never submitted. The standard-corners four-team probe did
confirm activation across all eight defenders with zero fallbacks.

Requests: `xreq_4aa4eb07-39a5-4488-8b7f-df9f055be511`,
`xreq_31745e93-1855-4931-b952-b1347a243130`,
`xreq_59840e62-4ca5-40ec-99a5-e876be8d9c7c`, and
`xreq_36ed443a-de7b-41fa-b6e5-c745c505ee4e`.

## v5 — generated own-team post knowledge, uploaded 2026-08-04

Immutable policy-version UUID: `6f571639-7a5b-42b7-bf2e-113be8377602`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Generates post knowledge online from the episode `WorldMap`; no fixed map
  coordinates or authored POIs return.
- For each opponent front belonging to the agent's own team, finds cover near
  the opponent→home shortest-route corridor, distributes candidates across 12
  route-progress buckets, scores nine forward firing rays, pairs the firing
  cell with a nearby reachable duck cell, and retains up to six posts with
  120px spatial separation.
- `navigation_map` schema v2 traces each candidate's combined, sightline,
  corridor, and duck-contrast scores plus selected firing rays and duck cells.
  `tools/render_nav.py` adds a front selector, candidate heat, post labels,
  firing rays, duck links, and hover score inspection.
- Diagnostic only: no gameplay behavior consumes posts in v5.

Five pinned-seed hosted probes on canonical Paintbot 0.7.183 all completed
with zero failed episodes:

| map | XP request | grid | fronts / posts | post pass |
|---|---|---:|---:|---:|
| small sides, seed 101 | `xreq_4c5e4d79-b248-4cbc-8f95-bc7ee428f283` | 131x70 | 1 / 3 | 20.3 ms |
| large sides, seed 202 | `xreq_381f0f56-5fa7-4a81-b9f9-ba7e6ea25a13` | 200x107 | 1 / 4 | 109.0 ms |
| standard corners, seed 303 | `xreq_79e63a93-e2d2-4770-93b8-0023740c5a14` | 120x120 | 3 / 10 | 164.0 ms |
| huge plus, seed 404 | `xreq_e600af70-768a-4d63-948f-379bc9fb5442` | 216x216 | 3 / 15 | 1,157.9 ms |
| giant corners, seed 505 | `xreq_8d02bb4b-29fe-45aa-acf1-911fe083c676` | 312x312 | 3 / 17 | 2,775.6 ms |

The artifact downloader exhausted each otherwise-complete episode because the
separate results artifact and policy-log listing were unavailable, but the
requested navigation ZIPs were present for 2/2, 2/2, 16/16, 16/16, and 15/16
seats respectively; representative traces rendered successfully.

## v4 — bounded duck-ray probe, uploaded then rejected 2026-08-04

Immutable policy-version UUID: `88ccf5d1-45e0-4e59-b257-19b3fa41167f`.
Reduced duck contrast from all nine rays to left/center/right threat rays and
24 shortlisted candidates. Hosted post time improved to 43 ms small, 220 ms
large, 687 ms standard, 4.87 s huge, and 14.0 s giant. Rejected because every
agent still computed all 12 four-team fronts. Never submitted.

## v3 — route-progress candidate bound, uploaded then rejected 2026-08-04

Immutable policy-version UUID: `69d03cb3-cfe2-4a7f-a35b-f88b4e59c75d`.
Bucketed corridor cover by route progress before exact firing-ray evaluation.
This fixed two-team maps but left exact duck testing combinatorial: hosted post
time was 129 ms small, 357 ms large, 1.46 s standard, 18.7 s huge, and 23.9 s
giant. Never submitted.

## v2 — unbounded post-metric probe, uploaded then rejected 2026-08-04

Immutable policy-version UUID: `1ab24204-1582-4cc9-9fdd-26a61432c3f8`.
First complete implementation of the agreed firing/duck metric and viewer.
Hosted tracing exposed the scaling failure: every corridor cover cell was
ray-scored before shortlisting, costing 818 ms standard, 3.72 s huge, and
29.6 s giant. Kept only as diagnostic evidence; never submitted.

## v1 — bootstrap + navigation diagnostics, uploaded 2026-08-04

Immutable policy-version UUID: `8af80cb6-022a-4d1b-b1eb-dfb08374b826`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

Forked from ctf_lab beacon (post-v67 lineage), adapted for Paintbot, then
ported exactly to native Nim:

- **NEW `worldmap.nim`**: episode-scoped world model built online from the
  walkability sprite + `game teams` + `endzone` markers + planted-heart
  sightings. Eroded 8px nav grid (SAT-based footprint erosion), cover cells,
  lazy per-goal Dijkstra flow/route fields, derived tactical anchors
  (choke/rally/spawn-aim/inside-base). Replaces `nav.npz` + `bake_map.py` +
  `poi.py` + `plan.py` + `posts.py` wholesale.
- **Multi-team**: 2-or-4 colors from the wire, slot-mod-teams dealing with
  self-sprite color lock, per-color hearts + retirement tracking, steal target
  = nearest live enemy heart, convert trigger generalized to the weakest enemy
  team. Roster-aware roles/squads start from the minimum muster consistent with
  the seat and grow only from observed identity badges; campaign map size is
  explicitly not used as a muster proxy.
- **Perception**: direct walkability pixel decode (supersnappy raw block),
  wire-marker parsers, all-color players/hearts/shouts/score-chips.
- **Items**: spawn table discovered from sightings (generator placements are
  per-map); seat-keyed fixed assignments removed.
- Ported intact: aim/lead/fire-gate/FF-guard, peek-fire-duck, firefight scoring
  + focus claims, hearing, chat protocol (grid dims from the map), danger field,
  tracing, and all 91 `STENCIL_*` environment variables.
- Cut from v1 (deliberate): posts, battle plans, POIs, anti-turtle; squad
  command remains off by default as in beacon v29+.
- Local-only fast-ready transport is available behind `STENCIL_FAST_READY=1`;
  the native self-play harness enables it to remove the 24 Hz pacing sleep.
- Opt-in `STENCIL_TRACE_NAVIGATION=1` telemetry records the exact eroded nav
  grid, cover, tactical anchors, and every lazily cached Dijkstra distance/hop
  field. `tools/render_nav.py` turns a JSONL trace or hosted artifact ZIP into
  a standalone interactive viewer; `self_play.py --visualize-nav` captures the
  local trace without enlarging routine telemetry.
- Synced against canonical Paintbot 0.7.182 (`3151a47`): the two changes since
  the 0.7.180 parity corpus were replay-viewer hashing and campaign docs, with
  no simulation/wire delta. The audit corrected production facts that do not
  follow engine defaults: deployed gun range is 1300px, campaign cell size can
  override `4ffa8`'s giant default, and absence-based item tracking uses the
  narrowest deployed vision cone (45 degrees).
- v1 release build updated to canonical Paintbot 0.7.183 (`95bb768`), whose
  server optimization retains object placements per viewer and emits only
  changed placements after initialization. Stencil already consumes Sprite-v1
  as retained state; the first hosted XP batch is the runtime contract check.
- Differential replay across six representative configurations matched
  169,235 controller/chat decisions exactly. The legacy Python oracle used for
  that proof is preserved in Git commit `1129931` and was removed from `main`
  after the port was accepted.

Hosted startup proof on canonical Paintbot 0.7.183 (`95bb768`): one bounded,
40-gameplay-tick XP episode each for `default`, `2v2`, `4ffa`, and `4ffa8`.
All four requests completed with zero failed episodes; every Stencil seat
uploaded telemetry, and representative artifacts contained the navigation map,
3/3/6/7 lazy flow fields respectively, plus a snapshot on every observed
policy tick. These deliberate timeout draws validate the upload/runtime,
retained Sprite-v1 stream, map construction, full trace, and artifact-rendering
boundaries—not competitive strength.
