# Layer 5 (v68) — the bounded follower & micro (rework finale)

**Status: DESIGN/SPEC, 2026-08-14 — James approved proceeding; the corridor
width and blocked-edge mechanism carry stated leans, adjustable at review.**
Governing: sketch §3.5 + the v60/v61 wall-slide lesson (§9). Last layer of
the rework. Codex-orchestrated build.

## Principle

Micro (separation, sidestep/stance/peek displacement, formation bias) may
PERTURB motion within a bounded corridor around the planned path; it may
never replace the route. The stuck watchdog shrinks to: progress test → ONE
forced replan with a blocked-edge penalty → loud telemetry. The 90° jitter
dies (its historical job — masking beelines — ended in v66).

## 1. The corridor bound (action.nim + nav.nim)

New pure check `withinCorridor(state: NavState, point: Point): bool` —
true iff `point` lies within `STENCIL_FOLLOW_CORRIDOR_PX` (default 12 =
1.5 nav cells; lean, tunable) of the CURRENT path segment neighborhood:
distance from `point` to the polyline segment
[path[cursor-1 clamped], path[cursor]] and to segment
[path[cursor], path[cursor+1 clamped]] — min of the two, point-to-segment
distance. Empty path (Hold intents / no route) => corridor check passes
trivially for SHORT nudges (the nudge length itself ≤ corridor width)
and fails for longer ones — Hold micro today only nudges locally, so this
preserves behavior.

Application sites (each keeps its existing trigger logic and its
`nudgeClear` acceptance — the wall-slide bar; the corridor is an ADDED
conjunct, applied to the *destination* of the perturbation):
- hold separation step (action.nim ~452-455)
- formation-bias waypoint blending (the biased waypoint)
- sidestep/stance/peek displacement targets (the micro override family) —
  NOTE: peek/duck pairs come from the atlas duck cache and are typically
  ≤ 3 cells; corridor width must not veto standard ducks: duck targets are
  exempted when the intent kind is Hold (a post-holder ducking is not
  route-following). Only NavigateTo-context micro is corridor-bounded.
- spray-flee/arc-pursuit are NOT micro (they are Intents since v66/earlier)
  — untouched.
Rejected perturbation => fall back to the unperturbed waypoint (not a
freeze). Count rejections: `micro_corridor_rejects` (cumulative, traced
like the plan counters) — the tuning signal for the width knob.

## 2. Watchdog rework (nav.nim, planner.nim)

Today: stuckTicks >= StuckTicks triggers BOTH a replan (nav.nim:41) and
steering jitter (octantToward's 90° rotate, action.nim:448). New ladder:
1. stuckTicks >= StuckTicks: force a replan AND pass the blocked edge to
   the planner as a temporary penalty (below). Reset stuckTicks. Count
   `follow_replans`.
2. If a forced replan happens again within
   `STENCIL_FOLLOW_STUCK_WINDOW_TICKS` (default 48) of the previous one:
   emit `follow_stuck_bug` trace event (once per episode per reason,
   sibling of plan_unroutable_bug) and count `follow_stuck_events`. Keep
   replanning on the same ladder (no escalation, no jitter).
3. `octantToward` loses its jitter parameter entirely; delete the rotate
   branch. (Its only true remaining client — spinning-diamond staleness —
   is served better by the penalty replan; diamonds get VISIBILITY via the
   stuck counters rather than masking.)

Blocked-edge penalty (the lean; simplest mechanism that changes the
replan): NavState gains `blockedPenalty: Option[tuple[pos: Point,
untilTick: int]]` — set to the CURRENT position's cell with TTL
`STENCIL_FOLLOW_BLOCK_TTL_TICKS` (default 96) when the watchdog fires.
planPath gains an optional `avoid: Option[Point]` parameter: edges whose
midpoint cell == avoid's cell get cost × `STENCIL_FOLLOW_BLOCK_FACTOR`
(default 8.0). One cell, one TTL, per agent — deliberately minimal; NOT a
general obstacle layer (diamond staleness is rare and local). Determinism
preserved (tick-driven TTL).

## 3. Follower tightening (nav.nim, action.nim, strategy/types)

- `noteProgress` runs for ALL alive intents with a movement target (today:
  only inside the NavigateTo branch, action.nim:440) — move the call up so
  Hold-with-point intents accumulate stuck ticks too. Hold intents with no
  point skip it (nothing to be stuck relative to). Guard: peek/duck HOLD
  displacement must not count as "progress lost" — reset lastXy when a
  micro override fires so ducks don't accrue stuck ticks.
- `Intent.arriveRadius*: float` (default 0 = today's behavior, NavCell px
  effective): the follower treats distance <= arriveRadius as arrived
  (stops advancing; resolveAction's existing hold logic takes over).
  makeIntent table sets it only where today's code has explicit arrive
  distance checks — transcribe, do not invent. (If no reason has one,
  ship the field consumed-but-default; Layer 6 strategy work will use it.)
- Cursor advance and path-following otherwise unchanged.

## 4. Out of scope

Fire-windup micro (sketch TODO); peek/duck TARGETING (only displacement
bounding); strategy changes; any planner cost change beyond the blocked
penalty; the 8px grid demotion.

## 5. Hard rules

As previous layers: determinism, no minting, lent-only field access, local
nim-checkability, telemetry-only reason strings, house style, no new deps.
nudgeClear (NOT segmentClear) remains the micro acceptance predicate — the
v60 lesson is law here.

## 6. Validation

- Property (harness): corridor invariant (every accepted perturbed
  waypoint within bound of the path polyline OR duck-exempt); watchdog
  determinism; blocked-penalty TTL expiry; octantToward jitter identifiers
  gone (grep gate).
- Live: normal + forced-active corpus episodes; watch stuck rates,
  `micro_corridor_rejects` (high => width too tight), duck% (the v60
  regression signature — MUST stay ~7-13%), separation activity, tick
  rate. Duck% is the primary local gate.
- Hosted: matched v68-vs-v67 batch, standard shape + probes. Trace-diff
  emphasis over W-L: duck%, stuck/replan counters, micro mix.
