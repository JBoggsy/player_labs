# Smooth movement root-cause preregistration — 2026-08-06

**Frozen before fresh inspection:** 2026-08-06 14:35:43 PDT

## Question

Why do Wowborg replays look choppy—repeated stopping and starting, plus cases where terrain
moves while the character appears stationary? Candidate primary layers are:

> **Resolution (2026-08-08):** the preregistered evidence localized the dominant issue to the
> environment movement owner. Canonical `vanilla-wow:0.1.208` keeps compatible forward control
> through observation horizons and route turns and retains collision-avoidance bearings until
> faced. See the final 0.1.208 follow-up below; the earlier sections remain the frozen evidence
> trail, not current behavior.

1. Wowborg's movement planning/control loop.
2. The `/env` action admission and ordinary-client execution path.
3. Replay-viewer interpolation, animation, or camera presentation.

The investigation may conclude that more than one layer contributes. It must classify world
motion separately from avatar locomotion animation; visual character stillness alone is not
evidence that the authoritative character position stopped.

## Unit of analysis

Audit at least three complete recent Wowborg replays. Within each replay, identify every
visible hitch lasting at least 0.5 simulation seconds while the character is alive, more than
10 yards from its active destination, and not intentionally waiting, interacting, turning in
place, recovering, or fighting. A hitch is either:

- **world-motion hitch:** authoritative horizontal speed falls below 0.5 yd/s and later
  resumes above 3 yd/s; or
- **presentation hitch:** authoritative world position continues changing while the rendered
  avatar's locomotion animation, root pose, or camera-relative presentation appears stopped.

For each hitch, align four timelines where retained evidence permits:

1. policy intent and selected action;
2. `/env` admission, pending action, settlement, and readiness;
3. outgoing movement controls plus authoritative server position;
4. viewer world transform, avatar animation, and camera transform.

## H1 — Wowborg controller is the primary cause

### Evidence predicted

- Policy actions themselves contain matching gaps, short alternating move/wait bursts, repeated
  replans, tiny route chunks, turn/move serialization, or a new action only after the preceding
  action fully settles.
- Each authoritative stop begins after Wowborg stops requesting forward motion or explicitly
  requests wait/turn; `/env` admits and settles those requests without unexplained delay.
- Outgoing client movement packets and server position faithfully reflect the policy's bursty
  command sequence.
- Hitch boundaries align with route-chunk completion, observation polling, settlement waits,
  progress checks, or replanning—not viewer frame cadence.
- Smooth continuous controls through the same `/env` path do not reproduce the hitch pattern.

### Evidence that would falsify H1 as primary

- Wowborg supplies continuous, directionally coherent movement intent across a hitch, yet
  admitted execution or authoritative position pauses.
- Raw server positions are smooth while only animation/camera presentation hitches.
- Hitch timing changes with viewer playback settings while policy/action timestamps are fixed.

## H2 — `/env` admission/execution is the primary cause

### Evidence predicted

- Wowborg requests continuous, coherent forward motion, but actions spend material time pending,
  are rejected, settle early, or encounter `action_ready=false`, `movement_allowed=false`,
  no-progress, blocked, or deadline outcomes.
- There are gaps between admitted intent and outgoing ordinary-client movement controls, or
  outgoing controls continue while authoritative server positions stop unexpectedly.
- Hitch boundaries align with action settlement, frame delivery, clock conversion, duration
  truncation, collision-readiness, or movement-authority transitions rather than route replans.
- The same hitch signature appears for a minimal continuous-movement policy or another policy
  using `/env`, while direct ordinary-client control does not show it.
- A simulation-time/wall-time mismatch is visible: requested movement duration and actual
  displacement disagree by a stable clock factor.

### Evidence that would falsify H2 as primary

- `/env` admits and lowers each request promptly, emits continuous controls, and authoritative
  server motion exactly matches the policy's intentional gaps.
- Raw authoritative motion is smooth through the visible hitch.
- Only Wowborg reproduces the pattern while an equivalent continuous `/env` control does not.

## H3 — replay viewer is the primary cause

### Evidence predicted

- Authoritative replay positions and movement-control cadence are smooth through visible hitches.
- Avatar locomotion animation becomes idle, freezes, or phase-resets while world coordinates
  continue moving.
- Terrain/camera motion diverges from the avatar pose: camera or world transforms advance while
  the avatar root/animation remains visually fixed.
- Hitch boundaries align with replay sample spacing, interpolation-buffer resets, animation-state
  reconstruction, playback speed, seek/chunk boundaries, or render-frame cadence—not actions.
- The live client or an independent replay presentation looks smooth for the same authoritative
  segment, or changing viewer playback rate changes the visible hitch without changing data.

### Evidence that would falsify H3 as primary

- Authoritative positions truly stop at every visible stop and resume at the same boundaries.
- Raw outgoing movement controls are absent during those intervals.
- The same stop-start timing is visible live and in independent presentations.

## Mixed-cause outcomes

- **Controller + viewer:** authoritative motion is bursty, and animation adds extra freezes or
  makes short pauses look longer.
- **Controller + `/env`:** policy leaves some intentional gaps, while additional pauses occur
  despite continuous intent.
- **`/env` + viewer:** authoritative execution pauses despite continuous intent, and the viewer
  introduces additional animation/camera artifacts.

A layer is called the **primary cause** only if at least 80% of classified hitches carry its
predicted signature and its primary falsifier is absent. A layer affecting 20–79% is reported
as a contributor. Below 20% is incidental for this corpus. Unclassifiable hitches remain in
the denominator and are reported explicitly rather than assigned by intuition.

## Evidence order

To avoid presentation bias, inspect in this order:

1. Authoritative position and raw control timelines without watching the viewer.
2. Policy actions and `/env` admission/settlement around detected stops.
3. Viewer animation and camera behavior at the already-pinned timestamps.
4. Only if the retained replay cannot separate controller from `/env`, run the cheapest hosted
   discriminating control: one version that holds a long, coherent move through the same
   interface, with activation tracing. Uploading is routine; league submission remains gated.

## Pre-registered output

Report hitch counts by signature and layer, the first concrete failure window for each replay,
representative aligned timestamps, falsifiers checked, unresolved evidence gaps, and the
smallest reusable fix at the owning layer. Do not recommend waypoint changes as the smoothness
fix unless the evidence specifically shows waypoint selection—not control execution—as causal.

---

## Post-registration results

The frozen hypotheses above were not edited after evidence inspection.

### Corpus and authoritative wire result

The audit covered all six retained v78 replays (one hosted canary and five league runs). The
member streams contain 7,510 outbound movement packets over 23,258.64 yards. They record 701
raw `MSG_MOVE_START_FORWARD` packets, 596 raw `MSG_MOVE_STOP` packets, and 584 stops followed by
a restart with at most one yard of displacement. Every replay reproduces the stop/start pattern:
49–138 boundary-only stops per run.

Treating redundant starts as one held-forward state yields 591 effective stop-to-restart
intervals:

- 478 have no intervening turn packet. Of these, 322 restart at the same simulation timestamp
  and 156 remain stopped for at least 0.5 seconds; none lasts 3 seconds.
- 109 contain explicit start/stop-turn controls. Their median duration is 4.0 seconds, and 81
  last at least 3 seconds.
- Four contain other intervening controls and last 56.3 seconds at the median.

The second category explains the reported presentation where the centered avatar appears
stationary while terrain moves: the ordinary-client wire really stops translation and turns in
place. It is not a camera-only translation artifact. These intentional turn intervals are
excluded from the preregistered strict hitch count, but they are a major part of the broader
choppy-looking symptom the investigation was asked to explain.

### Controller timeline

The exact v78 source (`3e95dcb`) does not emit low-level forward starts or stops. Its local
mover repeatedly submits the same semantic `MoveAction` destination after each bounded
settlement; it requests `Wait` or `Stuck` only after classified stalls. The route layer sends
one direct semantic target per plan instead of replaying the planner's navmesh corners as
policy-level micro-waypoints. Retained v78 artifacts expose no policy log, so individual
submission timestamps cannot be aligned to every stop.

This falsifies the strongest form of H1: the controller is not explicitly scripting the
hundreds of observed low-level stop/start/turn packets. Route choice can determine which
corners the environment pilot encounters, and explicit recovery actions explain isolated long
pauses, but neither accounts for the repeated generic locomotion signature.

### `/env` execution timeline

The current game contains the environment-owned continuation added by game PR #7391. That
mechanism preserves forward across compatible bounded semantic prefixes, but the movement pilot
still deliberately clears forward whenever heading error exceeds 45 degrees, turns in place,
then resumes. The wire's 109 turn-bearing pauses match that rule directly. The remaining 478
direct stop/restart transitions show that forward continuation is also being released or
restarted at movement boundaries more often than the semantic policy intent requires.

The strongest controlled comparison is already retained in the version record: with unchanged
policy behavior, enabling environment-owned continuation in an exact-image local episode cut
forward starts from 239 to 22 and stops from 243 to 25 over a comparable journey. That proves
the physical stop/start lifecycle is owned and materially controlled by `/env`, even though the
current hosted release still emits residual churn.

H2 is therefore the primary supported cause of authoritative choppiness. Exact attribution of
each residual non-turn release to compatibility rejection, action admission deadline, or route
settlement needs host telemetry or a policy log and remains unresolved.

### Replay-viewer timeline

These replays contain no Godview frames; the selected point of view is reconstructed from the
recorded ordinary-client packet stream. The replay path interpolates a recorded movement segment
to its immutable endpoint without predicting beyond it. A raw stop clears translating movement
flags and selects idle or turn-in-place locomotion; a subsequent start opens the next segment.
Consequently the viewer will make the real wire stops and turns visible, including camera/world
rotation around the centered controlled character.

H3 as a primary cause is falsified: authoritative outbound controls already stop and restart at
the relevant boundaries. The viewer may amplify short 0–0.5-second boundaries through animation
phase resets, but retained artifacts contain no rendered avatar/camera transform trace with
which to quantify that secondary effect. No evidence presently supports changing the viewer
before fixing the movement stream.

### Classification and smallest reusable next experiment

- **Primary:** `/env` route steering and residual movement-continuation lifecycle.
- **Contributor:** Wowborg supplies semantic destinations and therefore the route geometry, but
  it does not directly emit the low-level choppy controls.
- **Faithful presentation, possible minor amplifier:** replay viewer.

The reusable fix belongs below waypoint strategy: make semantic `MoveAction` execution steer
smoothly through ordinary path curvature while retaining forward, and release forward only for
arrival, a genuinely incompatible next intent, loss of movement authority, or an unsafe sharp
turn. Before changing behavior, add one hosted movement trace that records continuation retain/
release reasons and heading error at every effective stop. Re-run the same movement report; the
target is to eliminate the 156 non-turn pauses of at least 0.5 seconds and replace avoidable
turn-in-place intervals with continuous forward arcs without increasing collision or no-progress
settlements.

### Policy response-timing follow-up

Wowborg v80 adds the policy-visible half of that trace without changing action selection.
Hosted request `xreq_75c86237-6b7a-4a3a-abe3-cb4b9fd65687` completed five current 0.1.174
runs and recorded 2,561 intents for 2,561 unique offered frames. Thus Wowborg eventually
responds to every offered frame; it does not silently discard them. Response latency is
bimodal:

- 0.548 ms median, 0.810 ms p95, and 4.179 ms p99;
- exactly three responses per run exceed the five-second deadline (15/2,561 total), ranging
  from 7.63 to 17.23 seconds and totaling 151.98 seconds;
- the three sites repeat deterministically: initial navmesh planning, frontier replanning after
  the first guidepoint makes no progress, and ghost recovery planning;
- all 15 stale-frame rejections follow those 15 slow planning responses. There are no locally
  skipped actions. Synchronous `/env` round-trip is normally 381.0 ms median and 487.1 ms p95,
  with two additional outliers above five seconds.

The five corresponding replays contain 717 raw forward stops and 707 boundary-only stops. Only
38 raw stops fall inside the coarse one-second wall-clock windows covering the 15 slow policy
responses. Therefore policy silence exceeding the documented action deadline is confirmed as a
real, repeatable contributor, but it cannot explain the great majority of stop/start churn. The
primary H2 classification stands: exact host `action_stall` counts and attribution of the
remaining environment-owned releases still require host-side continuation telemetry.

### 0.1.178 matched follow-up

Wowborg v85 migrated the unchanged traversal strategy to canonical
`vanilla-wow-episodic 0.1.178`. The migration required removing its auxiliary direct `/player`
progress session: the new host gives each slot one immutable interaction mode, so opening
`/player` first prevented semantic `/env` from attaching. Hosted request
`xreq_4f0dd79f-f7e8-4e61-834c-adaf7d4689ce` then completed five of five episodes.

The five replays contain 500 raw forward stops and 492 boundary-only stops across 17,755.902
trajectory yards, or **27.71 boundary-only stops per 1,000 yards**. The v80 baseline is 707 over
19,089.6 yards, or **37.04 per 1,000 yards**. This is a 25.2% reduction, with zero falling
packets in every new replay, but it misses the preregistered 50% reduction threshold of fewer
than 18.52 stops per 1,000 yards. Verdict: 0.1.178 partially improves continuity but does not fix
the periodic stopping. The remaining churn still needs the host's continuation retain/release
and `action_stall` attribution rather than another hard-coded movement route.

### 0.1.208 resolution

The owner added structured host telemetry and then repaired the environment-owned lifecycle in
three attributable steps: compatible waits and combat preserve continuation, same-target route
turns preserve forward input, and PR #8045 (`b92f4961c`) retains a selected collision-avoidance
bearing until it is faced. This directly addresses the earlier wire-level stop/start and
one-frame turn-pulse evidence without changing Wowborg.

The unchanged `wowborg:v88` owner acceptance request
`xreq_c0649f44-ecca-4f82-bc2a-e1cdf95684b1` on canonical
`vanilla-wow:0.1.208` completed 5/5. Across 17,308.749 trajectory yards it recorded zero
nonterminal boundary stops, host stalls, rejected requests, detached frames, direct left/right
reversals, or instances of the old same-waypoint route-bearing disappearance signature. There
were 11 turn runs lasting at most 100 ms, versus 144 on the 0.1.207 canary. The three raw
boundary stop/restart pairs all occur at final forced-root/scoring logout with no later
observation and are classified as terminal artifacts, not traversal churn.

Verdict: H2 was correct. The authoritative outbound movement stream contained the visible
choppiness, and the defect was in environment-owned continuation/steering rather than Wowborg's
waypoint strategy or the replay viewer. Current analysis must report **nonterminal** stops and
retain terminal scoring artifacts separately.

An independent lab verification, `xreq_cb6f96ae-00d0-40ab-b5a5-d10cb46248e0`, also
completed 5/5. Across 17,352.720 trajectory yards it recorded zero active nonterminal stops,
host stalls/rejections/detached frames, stale-frame rejections, direct reversals, or old
bearing-disappearance signatures. Ten turn runs lasted at most 100 ms. Its four raw stationary
stop/restart pairs are two death/ghost transitions and two final scoring/logout artifacts.
Mean score was 1,607.572. This independently passes the preregistered seamless-movement bar.
