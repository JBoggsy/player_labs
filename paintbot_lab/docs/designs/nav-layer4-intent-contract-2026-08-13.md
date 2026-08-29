# Layer 4 (v66) — the Intent & goal contract

**Status: DESIGN, 2026-08-13. Approved scope: James ruled the split — v66 =
this contract; v67 = early_defense/barrage_center re-expression + side-lane
posts.** Governing: sketch §3.4 + kill list + §5 beeline table. This doc is
also the implementation spec (Codex-orchestrated build).

## What Layer 4 is

Strategy stops handing nav unvalidated points and stops steering directly;
nav stops dispatching on strings. One typed Intent carries a PRE-VALIDATED
goal plus typed permissions; every movement routes through the v65 planner;
an unroutable goal becomes a loud bug signal instead of a beeline.

Everything below was staged: `sameComponent` is O(1) and the v65 cascade
guarantees `sameComponent ⇒ routable`; `plan_goal_snapped` telemetry already
fingered the dirty producers (pedestal-class goals); the `PlanCostProfile`
seam awaits carrier/hunter; flow fields already serve as the oracle.

## 1. The Intent type (types.nim, extending the existing object)

```nim
CostProfileKind* = enum ProfileDefault, ProfileCarrier, ProfileHunter
MicroFlag* = enum
  MicroPeekDuck,        # peek/duck cycle allowed at holds
  MicroSeparation,      # hold separation nudges allowed
  MicroFormationBias,   # squad formation-bias waypoint blending allowed
  MicroSprayPursuit,    # arc-range pursuit override allowed
  MicroStealRushExempt  # steal's near-goal peek/duck exemption allowed

Intent* = object
  kind*: IntentKind            # existing
  point*: Option[Point]        # existing — now ALWAYS pre-validated when set
  reason*: string              # existing — TELEMETRY ONLY after this layer
  movingGoal*: bool            # replaces MovingPlanReasons list
  clampToEndzone*: bool        # replaces the early_defense clamp check
  suppressFireFreeze*: bool    # replaces the clear_spray fire-freeze check
  profile*: CostProfileKind
  micro*: set[MicroFlag]
```

Construction: ONE helper in strategy.nim (`makeIntent(kind, point, reason)`)
plus a declarative per-reason table mapping reason → (movingGoal,
clampToEndzone, suppressFireFreeze, profile, micro set). The table IS the
old seven lists, made visible in one place; strategy call sites switch to
the helper. `resolveAction` and the micro overrides read ONLY the typed
fields. Grep-gate at the end: `intent.reason` may appear only in trace/
telemetry code.

Flag table (transcribing today's behavior exactly — no behavioral change
from the flags themselves):

| reason | micro excludes | other |
| --- | --- | --- |
| carry_home | peekDuck off | profile=Carrier |
| steal | (peekDuck rush-exempt within PeekDuckRushExemptPx stays as an arriveRadius-style distance check in the override, gated on MicroStealRushExempt) | formationBias on |
| clear_grenade, clear_spray, fetch_medkit, intercept_thief(_heard) | peekDuck off | clear_spray: separation off, sprayPursuit off, suppressFireFreeze per today's L450 condition; intercepts: movingGoal, profile=Hunter |
| early_defense, barrage_center | peekDuck off, separation off, sprayPursuit off | early_defense: clampToEndzone (both keep their target logic — re-expression is v67) |
| convert_hunt, escort_carrier(_heard) | — | movingGoal; convert_hunt profile=Hunter; escort profile=Carrier |
| to_hold, squad_move/squad_to_watch/squad_to_hold | — | formationBias on |
| everything else | peekDuck, separation, sprayPursuit on; formationBias and stealRushExempt off | profile=Default |

**Implementation correction:** the pre-v66 code is the behavioral source of
truth for this transcription. Formation bias's strict whitelist is `steal`,
`to_hold`, `squad_move`, `squad_to_hold`, and `squad_to_watch`. The original
table incorrectly included `to_post` and abbreviated `squad_to_watch` as
`to_watch`; neither spelling matched the dispatch code.

## 2. Goal validation at selection (worldmap + strategy)

New `nearestReachable*(map, point, fromPoint, maxRadiusPx = 32*NavCell):
Option[Point]` in worldmap.nim: nearest standable pixel to `point` within
`fromPoint`'s component — deterministic expanding pixel-ring, squared-
distance then row-major tie-break (the same discipline as the planner's
endpoint snap; NOT the retired biased cell snap). Returns none if nothing
qualifies in radius.

Producers that must validate through it before constructing an Intent (the
v65 snap telemetry + sketch §5 census):
- steal / convert_hunt goals (pedestal positions — the known snapped class);
- grenade evacuation's radial point (strategy.nim ~242-245);
- escort-carrier's extrapolated fix (strategy.nim ~288-292);
- clear_spray's winning flee candidate (already grid-validated; route it
  through nearestReachable for the same guarantee, then PLAN to it — the
  direct octant steer dies);
- barrage_center's center point (target logic unchanged in v66; validated).
If nearestReachable returns none, the producer falls through to its next
objective (each site's natural fallback: skip the candidate / next rung).

## 3. The kills (action.nim, nav.nim, strategy.nim)

- **FlowReasons dispatch dies**: the `flowWaypoint` branch in resolveAction
  is deleted; every NavigateTo intent calls `astarWaypoint` (v65 planner)
  with `intent.movingGoal` and the profile's weights. Flow fields remain
  ONLY as the init-minted oracle (do not delete flowWaypoint/fields — squads
  advancePoint & trace still read routeDistance; flowWaypoint itself becomes
  dead for movement — delete it if truly no caller remains, else leave with
  a comment).
- **clear_spray raw-point steer dies** (action.nim ~461): planner routes to
  the validated flee point. Keep the flee point's own fast re-scoring cadence
  (movingGoal=true).
- **Arc/spray pursuit override dies** (action.nim ~508-511, the direct
  octant): replaced by a strategy-level moving Intent — when the arc-pursuit
  condition holds (iHaveArc, enemy in (ArcIdealRangePx, ArcPursuitRangePx],
  not carrying, micro allows), strategy emits reason="arc_pursuit" with the
  enemy's projected position as a movingGoal Intent (profile=Hunter,
  validated via nearestReachable). The MicroSprayPursuit flag gates whether
  the objective may fire at all (same suppression semantics as today).
- **The unroutable beeline dies** (nav.nim `return goal` on empty path):
  unroutable now returns `selfXy` (hold in place), increments the existing
  `plan_unroutable_count`, and emits a once-per-episode-per-reason loud
  trace event `plan_unroutable_bug` — under the new contract this indicates
  a producer bug, exactly as the sketch specifies. The planner's own 32px
  endpoint snap REMAINS as defense-in-depth (snaps keep being counted; the
  goal after this layer is that both counters sit at zero).
- **MovingPlanReasons / FlowReasons / the inline suppression lists die** —
  subsumed by Intent fields.

## 4. Profiles live (planner.nim, nav.nim plumbing)

`PlanCostProfile` gains construction from `CostProfileKind`:
Default danger 1.0; Carrier danger 2.5 (evade); Hunter danger 0.25 (accept
risk). Knobs `STENCIL_PROFILE_CARRIER_DANGER` / `_HUNTER_DANGER` (floats).
astarWaypoint passes the intent's profile through. (Exposure was dissolved
into LOS danger in Layer 3; there is no second term to weight.)

The cached path's profile is part of its identity. A profile change for an
otherwise unchanged goal invalidates the cache and replans immediately; this
closes the implementation-spec gap where a carrier/hunter transition could
otherwise keep following a path priced with the previous danger weight.

## 5. Explicitly out of scope (v67+)

early_defense/barrage_center re-expression over Layer 2 PoIs; side-lane
post coverage (TODO.md); follower/micro corridor bounding (Layer 5);
deleting the 8px grid (still consumed by oracle/posts/comms — Q9 census is
a v66 VERIFICATION step, not a code change: grep-confirm only shouts,
trace schema, and the oracle consume cell coordinates).

## 6. Validation

- Property: planner suites unchanged (must stay green). New: strategy-level
  intent construction is pure enough to unit-probe? (If awkward, skip —
  live checks below carry it.)
- Live self-play, forced-active (STENCIL_EARLY_DEFENSE=0) and normal, all
  three corpus maps: `plan_goal_snapped` and `plan_unroutable_count`
  expected ≈ 0 (the producers are clean now); objective mixes broadly
  stable; NO movement stalls (watch stuck-watchdog rates).
- Grep gates: `intent.reason` outside trace/telemetry = 0 hits;
  FlowReasons/MovingPlanReasons identifiers = 0 hits.
- Hosted: matched v66-vs-v65 batch, standard shape + paired giant probes.
  Expected deltas: carry/steal movement (flow→planner is the biggest
  visible change — carriers now evade via the Carrier profile), pursuit
  behavior (strategy-level moving intents), duck%/backoff stable.

## Ship

v66, tag `purpose=intent-contract`. VERSION_LOG entry, docs updated
(sketch §9-series addendum), matched batch, verdict.

## Implementation verification addendum

**Q9 8 px grid consumer census:** the grid has more runtime consumers than the
original shorthand (“shouts, trace schema, and oracle”) implied. Movement
planning no longer consumes it as route truth, but it remains live for:

- the stable-goal Dijkstra oracle and its consumers (`routeDistance`,
  `peekRouteDistance`, `distanceAt`, and oracle-only `flowWaypoint` used by
  `forwardRayEnds`);
- directional cover masks, post generation/scoring, home capture snapping,
  and squad order point quantization;
- danger-field construction/sampling and the legacy belief-danger diffusion
  grid;
- chat position encoding/decoding and trace navigation-map/flow schemas;
- local micro geometry (sidestep candidate cells, formation/separation step
  scales), role band sizing, and configuration values expressed in cell units.

This is the fuller v66 grep census result. It confirms the grid cannot be
deleted yet; Layer 4 only removes it from movement dispatch and path choice.
