# Design: navigation v2 — general navigation + the World Race challenge

**Date:** 2026-07-22. **Status:** proposal for review.
**Goal (James):** high-quality *general* navigation — "navigate literally anywhere we
want" — not the ability to move through specific waypoints. Waypoints are probes.
**Inputs:** the codex audit (14 findings,
[`../recon/nav-audit-codex-2026-07-22.md`](../recon/nav-audit-codex-2026-07-22.md)),
the v5-v20 race campaign lessons, and a new discovery: the game host's
**`/player/navigation` route-planning service** (below).

## The discovery that shapes this design

The 0.1.31 wrapper exports `VANILLA_WOW_NAVMESH_SERVICE_URL` → the game container's
`/player/navigation` endpoint (`navigation_service.py:69-76`), which runs Detour route
queries against the authoritative world data. The pinned SDK ships the full client:
`wow_sdk.navmesh.NavmeshRouteRequest{map_id, source, target, arrival_radius, ...}` →
`NavmeshRoute{waypoints, route_distance, path_type, continuation_target,
jump_segments, projected_source/target distances, ...}`, plus `NavmeshLocalGraph`
(exploration graph), `smooth_navmesh_route`, `stuck_escape_navmesh`,
`random_reachable_navmesh_point`, and rich diagnostics.

Consequences, mapped to the audit's critical findings:

| Audit finding | v2 answer |
|---|---|
| 2D distances lie (stacked floors) | plan in 3D via the service; arrival = 3D distance to the *projected* target; budgets from `route_distance` (true path length), never straight-line |
| No map identity | `WorldPoint{map_id,x,y,z}` everywhere; a route request IS map-scoped; cross-map = journey layer |
| Unreachable targets burn budget | `path_type: partial` + `projected_target_distance` tell us *before walking*; a partial route is either "walk to partial end then re-plan" or "unreachable — report, don't grind" |
| Via-chains = hand-authored topology | intermediate points come from the *planned route's own waypoints*; hand authoring survives only in the world model (transit edges), not in step logic |
| Budgets are Durotar pace constants | budget = `route_distance / measured_pace + slack`, with pace measured *online* per session (a rolling estimate, not a constant) |

## Architecture: three levels + a world model + a nav state machine

James's multi-level intuition, made concrete. Each level has one job and a crisp
contract; higher levels only sequence lower ones.

### L0 — `local_mover` ("somewhere we can see", ≤ ~100 yd, same map)
One factorized `move` to a destination; the executor's Detour does the walking.
Our responsibilities: 3D arrival verification, chunk-settlement progress tracking,
stall/oscillation detection (position-history based — detects A↔B flapping, which the
current displacement check cannot), and the unstick ladder (re-issue → recommended
action → `stuck_escape_navmesh` candidate → report failure upward). This is the
v5-v20 machinery, generalized: all thresholds either derived (pace-relative) or
justified as executor facts (chunk size), never zone calibration.

### L1 — `route_navigator` (same map, any distance)
`navigate_to(WorldPoint) → RouteResult`. Plans via `/player/navigation`; walks the
route as a sequence of L0 hops toward *route waypoints* (coarsened: hop to the
farthest route waypoint within ~60 yd — respects the v19 lesson that the executor
handles distance well; our hops exist for progress measurement, not steering).
Re-plans on: L0 failure, continuation targets, large deviation from the corridor,
or map change. Detects unreachable early (partial path + projection distances).
**Owns the nav state machine** (the audit's core prescription):

```
planning → walking → [combat_paused] → walking → arrived
                   → [dead → recovering(release, corpse-run) → re-planning]
                   → [teleported → re-planning]
                   → failed(reason: unreachable | no_progress | budget | aborted)
```

- `combat_paused`: entered on `in_combat` or combat-interrupted settlements; the
  budget clock STOPS; navigation resumes (with a fresh plan if we moved) when combat
  ends. Nav never fights; it yields to whoever owns combat (T1's arbiter later).
- `recovering`: death pauses everything; after reclaim, position changed → re-plan.
  A graveyard respawn on another map escalates to the journey layer.
- Budgets: `route_distance / pace_estimate * slack + fixed_base`, clock pauses in
  combat/recovery. Hard abort only via the caller's deadline.

### L2 — `journey_planner` (anywhere: cross-zone, cross-map, through gates)
`journey_to(WorldPoint) → sequence of legs`. Plans over the **world model** graph:
nodes = places (zones, instance entrances, transit termini), edges = how you get
between them (walk [an L1 route], instance portal [`area_trigger`], zeppelin/boat
[wait+board], death-warp, hearthstone). Executes leg by leg; a leg's failure triggers
graph re-planning (e.g. portal unusable → alternate route). Cross-map correctness
lives here: L1 refuses any target whose map_id ≠ current map and escalates.

### The world model (data, not code — like the rotation tables)
`world_model.py` (or JSON): the small curated graph of world topology that cannot be
derived from frames — instance entrances (RFC's Cleft of Shadow trigger), meeting
stones, zeppelin/boat routes, graveyard→zone associations, zone adjacency anchors.
Deliberately tiny to start (Durotar + Orgrimmar + RFC + one cross-continent transit);
growing it is data entry, not code change. This is legitimate world knowledge, the
kind the authored profiles also encode — the sin to avoid is knowledge hiding in
*constants*, not knowledge as *declared data*.

### What survives from v1
The bridge (audit-clean) with two small additions: preserve settlement kind + end
position in `ActionOutcome` (audit #3/#11: exact settlement correlation), and a
`plan_route()` call wrapping the navigation service. The race policy becomes a thin
consumer of L1/L2 (course logic only). The current waypoint catalog becomes World
Race course data. `random_walk` gets `random_reachable_navmesh_point` for real
exploration.

## The World Race challenge (the new benchmark)

**Design goal: a challenge that punishes memorization.** Diverse enough that passing
requires general machinery; measured so failures name their layer.

**Course pool** (waypoint stations across the world, each tagged with
`{map_id, point, features}`):

- **Durotar outdoor** (the old catalog survives as stations, incl. the hard tier —
  now legitimate targets since unreachability handling is a *graded behavior*).
- **Orgrimmar city** — gates, streets, the Drag's tunnels, Valley of Wisdom: urban
  topology, narrow corridors, verticality-lite.
- **RFC dungeon** — entrance trigger in the Cleft of Shadow, then in-instance
  stations across the lava cavern's levels: instance entry (journey edge), stacked-z
  arrival, indoor routing. THE gate for T1 group play.
- **The Barrens road** — Crossroads via the long west road: true long-haul (1500+
  yd), zone crossing, gate passage.
- **Tirisfal/Undercity via zeppelin** (stretch tier) — cross-continent transit: the
  journey layer's full test.
- **Adversarial stations**: a deliberately unreachable point (mid-air over lava — the
  correct behavior is *fast, clean failure*), a point requiring a jump-segment route,
  a swim-across point.

**Session shape:** seedable random draw of N stations across ≥3 regions (tier mix
enforced: ≥1 dungeon, ≥1 cross-zone, ≥1 adversarial), visited in drawn order via
`journey_to`. Every leg emits `nav_leg` traces: planned route distance, actual
distance & time, re-plans, combat pauses, deaths, stall events, failure reason.

**Scoring (per batch, via an upgraded `race_report.py`):**
- **Reachability score** — stations correctly reached / reachable stations drawn.
- **Honesty score** — unreachable stations correctly *identified* (fast-fail) vs
  ground away at.
- **Efficiency** — actual/planned distance ratio (path overhead) and pace vs the
  measured executor ceiling; time lost to stalls/re-plans.
- **Robustness** — recovery rate from combat interruptions and deaths (did nav
  resume and still arrive?).

Generality is enforced structurally: the course pool spans regions, the draw is
random, and NO course-specific constant exists to tune — the only tunables are
layer-level (pace slack, stall windows), and a fix that helps one region must not
regress the others in the same batch.

## Honest assessment (James's questions)

- **Will this give good feedback?** Yes — because the diversity makes overfitting
  visible immediately (a Durotar-flavored fix fails the Org/RFC stations in the same
  batch), and the four scores separate "can't plan" / "can't walk" / "can't recover"
  / "can't tell reachable from not". That's the attribution the v5-v20 single-course
  campaign lacked.
- **Can I build this autonomously?** Yes, with the same loop as v5-v20 (upload →
  batch → trace-scored verdict → fix), now with better instruments. Two dependencies
  to de-risk early: (1) the navigation service's availability/latency in hosted
  episodes (probe in the first batch; fallback = executor-only moves with
  frame-observed progress, degraded but functional); (2) instance-entry mechanics
  (area_trigger through the RFC portal — one focused probe). Cross-continent transit
  (zeppelins) is genuinely uncertain — boarding a moving transport may need executor
  support we haven't verified; it's the stretch tier, not the gate.
- **The multi-level split is right** — and the levels are also exactly what combat
  needs: L0 is "close to melee range on this mob", L1 is "get to the grind spot /
  next boss", L2 is "get to RFC". Building nav v2 first gives T1 its movement verbs.

## Build order

1. **Bridge additions** (settlement fidelity, `plan_route()`), + `world_model` seed
   (Durotar/Org/RFC).
2. **L0 rebuild** (3D arrival, oscillation detection, unstick ladder) — validated
   against the old Durotar course (must match v19/v20 results: no regression).
3. **L1** (route walking + nav state machine incl. combat pause) — validated on
   Durotar + Orgrimmar stations.
4. **L2** (journey legs, instance entry) — validated on the RFC + Barrens stations.
5. **World Race full batches** — iterate to the four-score bar: reachability ≥90%,
   honesty 100%, efficiency within 1.3x planned, recovery ≥80%.
6. Then T1 combat proceeds on top (its build order already assumes these verbs).

## Open questions

1. Does the hosted runner's navigation service respond fast enough for per-leg
   planning (vs caching whole routes)? First-batch probe.
2. RFC instance state: does `custom-fresh-start` even allow entering RFC solo at
   level 1? May need the dungeon variant or a level override for dungeon stations —
   worst case the dungeon tier runs on `rfc-five-player-clear`'s variant config.
3. Zeppelin mechanics (stretch): defer until L2 is proven on foot?

## Outcome (2026-07-23, v21→v38 campaign) — SHIPPED, one-shot bar met

Fourteen hosted batches iterated this design to the /goal bar. Final validation: two
consecutive fresh courses shipped as pure data (`--stations` build arg → `WOWBORG_STATIONS`)
with zero code changes — v37: 4/4 episodes at 100% reachability / 100% honesty; v38:
100/67/67/100 where every miss was a session-length deadline (~800yd at the seam's
effective pace vs the station's time share), not a navigation failure.

Key deltas from the design as written (each earned by a hosted failure — see the
lessons buffer and `git log v21..v38` for evidence):

- **L1 does not walk service waypoints.** One direct semantic move per plan; the
  executor's server-side Detour owns locomotion (waypoint micro-hopping marched it into
  "no physically admissible source projection" traps and reset its auto-unstuck).
  The plan supplies reachability verdicts, distance-derived budgets, and partial
  progression targets. HOP_HORIZON is gone.
- **The honesty classifier is subtler than status codes.** Bare no_path ≠ unreachable:
  a here→here self-probe distinguishes a broken planner (degrade) from an off-mesh
  target (fail fast). Empty partials (findPath pool truncation) are stalls, bounded by
  the same-spot replan limit (4), never "unreachable".
- **Staging is a ladder, not a hop policy**: after a stall, stage at corridor 1/2 →
  1/4 → …; reset on any landed leg. Plus the stock Stuck spell (7355) as L0's first
  unstick rung.
- **Combat is run-through by default** (yield at <50% health or combat-stall), and a
  finished fight resumes the same walk without re-planning.
- **The race layer owns time-physics**: nearest-first ordering, world-graph travel
  estimates, `skipped_insufficient_time` for stations that provably can't fit their
  fair share (excluded from reachability), last station gets the remaining session.
- **0.1.31 contract hazards**: the controller emits validation-invalid frames in long
  storms (recommended-vs-mask upstream bug) — survive via a lenient raw-JSON frame
  parse (ALL five status_request fields are required by the Nim server) and the
  state.json TelemetrySnapshot observation fallback.

Open items carried forward: RFC portal edge (area_trigger 2230) unproven hosted —
needs a longer variant than custom-fresh-start (~970s) since the journey routes
~3000yd through Orgrimmar; zeppelins untouched.
