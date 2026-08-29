# Tentative lessons — current session

Candidate lessons are intentionally eager and noisy. SessionStart archives this file;
recurrence across sessions, not repetition within one session, is the graduation signal.

> The 2026-08-20 entries below describe the retired GV52 investigation. The current
> 2026-08-21 contract is Emerg-ant 0.9.1 / GameVersion 57.

### Bound alarm membership, not just alarm duration

An unbounded danger alarm stopped an all-in queen rush 5–1, but incidental approaches
later recruited 13–15 workers including newly hatched brood and turned ordinary play
into a 2–6, 113–124 delivery regression. Restricting the same alarm to the seven
starting workers retained a 3–3 rush defense while recovering ordinary play to 4–4
and 117–113 deliveries. In a growing colony, responder identity is itself a critical
control knob.

### Prefer damage over opponent-authored intent signals

Using enemy danger pheromones as an attack-intent signal defended the synthetic rush,
but two defensive colonies cross-triggered each other's alarms and the candidate lost
five deliveries to v4. Direct local damage plus a narrow proximity fallback produced
the same 5–1 rush defense and led v4 by seven deliveries. Public communication is
useful evidence, but it is not trustworthy intent and can create feedback loops.

### Queen-defense latency has a narrow cliff

With the same guard, responder set, and damage trigger, a 35 px queen-relative fallback
defended 5–1 while 30 px and 18 px variants each defended only 2–4. Five pixels is not
small when seven workers must receive an environmental alarm, navigate home, and join
contact combat before a three-hit-point queen collapses.

The generic stuck-jink also participates in that latency-sensitive geometry. Disabling
it only during queen defense looked like a clean hold-post fix, but the candidate lost
its first rush episode in both colors and could no longer match 5–1. Random displacement
helps defenders break body contact or re-enter an interception path; stationary intent
does not imply that stationary execution is safe.

Founder productivity also cannot select the guard in isolation. Index 5 had returned
less food than index 7 in two pre-guard control windows, but swapping the permanent
guard to index 5 lost two of its first four rush games and could no longer match 5–1.
Spawn/index geometry and interception timing outweigh the counterfactual forage tally.

Holding index 5 at index 7's exact center post did not rescue the swap: it again lost
the first rush game in both colors. The guard-index effect therefore survives control
for hold-lane geometry and should be treated as an identity/spawn-timing constraint.

### Validate a defense in both quiet and attacked colors

Against the current champion, v5's red colony won 16–9 without ever mobilizing, while
its blue colony won 16–8 after all seven responders answered and the permanent guard
killed both invaders. The color swap showed both halves of the contract: the alarm can
stay dormant during a pure forage race and activate materially under real pressure.

### Fixing state estimation can remove useful accidental behavior

The canonical carried-food marker flickers enough to toggle a carrier between return
and forage objectives many times per trip. Latching carry ownership removed the
oscillation and improved ordinary play to 5–3 and 122–115 against v5, but weakened the
same queen-rush defense from 5–1 to 3–3: marker-off frames had accidentally allowed
carriers to answer the alarm. State correctness must be evaluated against downstream
coordination, not assumed to be an unconditional improvement.

### Control overhead can be behaviorally load-bearing

Removing carrier pheromone changes cut locomotion-pausing command frames by roughly
94% and improved the aggregate forage economy, yet weakened queen-rush defense from
5–1 to 3–3. Even retaining urgent carrier signaling only near the nest recovered just
4–2 and regressed ordinary play. A protocol pause that looks like pure overhead can
change spatial availability and therefore colony coordination; optimize it only with
both throughput and adversarial checks.

The same warning applies outside the explicit alarm radius. Suppressing danger signals
more than 220 pixels from the queen removed 983 traced signal-intent frames but lost
2–6 and 114–124 deliveries. A public mark can still alter enemy-trail erasure, command
pauses, congestion, and later encounters even when this policy has no direct reader at
that location; producer-consumer reachability alone does not prove a signal redundant.

The opposite range change was no better: extending ordinary encounter danger from 80
to 120 pixels lost 3–5 and 118–120 deliveries. The existing 80-pixel boundary balances
the public signal's indirect value against command and trail side effects; neither
removing its far-field portion nor broadening it improved the colony.

Keeping workers at urgent rate 3 halved command frames by eliminating the three-step
carrier-to-scout rate cycle, but yielded only a 4–4, 116–113 ordinary result and then
lost two of its first four rush games, both as blue. Fewer protocol pauses are still
not a monotonic improvement when the retained emission rate changes trail density and
alarm timing; the rate-2 worker baseline remains the safer coupled equilibrium.

### Extend modest tactical wins onto fresh seeds

A late-brood raider appeared useful in the first matched batch: 5–3, a 118–115
delivery edge, and repeated opponent-wide alarm mobilization. A fresh-seed color swap
went 2–6 and 109–118, reversing both outcome and economy. A small tactical batch can
identify a mechanism, but promotion needs an independent seed window when the margin
is modest.

Distance-scaled teammate repulsion produced the same warning in a less tactical
setting. It opened 5–3 with a five-delivery edge and preserved the 5–1 queen-rush
result, but its fresh window was 4–4 and one delivery behind. Even a plausible hot-path
geometry change needs independent replication when the initial effect is this small.

### More delivery lanes are not automatically less congestion

The proven two-lane return path beat the direct route, but expanding it to four lanes
lost 3–5 and trailed 110–122 deliveries. Spreading traffic farther from the shortest
nest approach can cost more path length than it saves in collision avoidance; lane
count and lane offset must be treated as geometry parameters, not monotonic upgrades.

Changing only lane assignment from stable worker parity to the carrier's current side
also lost 3–5 and 113–120 deliveries. A shorter individual approach can make the
colony's traffic less predictable and converge several carriers onto one lane; stable
identity separation is part of the two-lane mechanism, not incidental bookkeeping.

### Target churn can be adaptive rather than waste

V5 changed food targets 1,047 times during continuous forage, which looked like
wasted motion. Yet full commitment lost 3–5 and 107–118 deliveries, while a 50 px
hysteresis only split 4–4 and trailed 114–117. In a replenishing shared resource
field, frequent replanning can be the mechanism that captures newly favorable work;
switch counts alone do not identify waste.

### Precise alarms still need bounded membership

Replacing a broad proximity trigger with direct damage/contact evidence did not make
unbounded response safe. All-worker response matched the seven-founder policy's 5–1
rush defense but lost ordinary play 2–6 and 116–124 deliveries; brood mobilized in
four quiet-match episodes. Signal precision and responder scope solve different
coordination problems, so tightening one does not eliminate the need to bound the other.

### A nearby carried marker does not prove self ownership

V5's permanent guard logged 219 `carry_home` frames without a delivery, suggesting
that marker flicker interrupted a short return. A guard-only carry latch activated in
seven of eight games for 247 frames, yet the guard again delivered nothing and the
candidate lost 2–6 with a 110–123 delivery deficit. The carried-food marker can sit
within the self-radius because another carrier is nearby; persistence amplifies that
false attribution into real movement. Ownership inference needs disambiguation before
it is safe to latch, even for one specialized worker.

### Fix the hot path, not an elegant fallback

The fallback sweep used raw alternating-team slots and therefore repeated phase
offsets within a colony. Phasing by colony index removed that structural collision,
but `forage_sweep` activated for only 349 policy-frames across eight games because a
visible food patch almost always supplied the target. The corrected candidate split
4–4 with deliveries tied 116–116. A genuine bug in a cold fallback can still be the
wrong optimization target; activation volume must precede architectural satisfaction.

### Direct visibility is not path cost

Globally scented food can lie behind walls, but preferring a directly reachable patch
within 120 pixels was not an effective correction. It activated for 414 traced frames,
lost 3–5, and trailed 110–121 deliveries; both high- and low-activation seeds regressed.
A wall-free ray says nothing about the full detour of either candidate route, so future
path-aware food ranking needs comparable navigation costs rather than a binary ray test.

### Static food spreading can lose to a visible dogpile

Assigning every worker across the full food set had already failed. A narrower test
sent only even-index foragers to the second-nearest patch and capped the extra route at
150 pixels. It activated for 19,785 frames, yet lost 2–6 and 114–123 deliveries. What
looks like wasteful convergence can be rapid exploitation of a replenishing nearest
patch; deterministic worker parity is stale coordination when patch value changes
faster than the assignment.

### Raw ownership filtering still changes the defense ecology

Choosing the nearest visible teammate as a carried marker's owner—without any latch—
was a large forage win: 7–1 and 126–104 deliveries after rejecting 3,426 false-nearby
frames. It still weakened queen-rush defense from 5–1 to 3–3, entirely through the
candidate's blue games. Even a more accurate instantaneous state changes which workers
route home, pause for pheromone commands, and become alarm-eligible. Preserve v5's raw
forager behavior unless a narrower specialization proves safe.

The guard-only follow-up did not prove safe or useful: it rejected 91 frames, lost
ordinary play 3–5 and 111–119 deliveries, and defended only 4–2 against the rush.
False carry attribution on the guard is observable, but it is too rare and too coupled
to incidental timing to be a profitable correction in isolation.

### Non-responders can still be load-bearing under attack

Suppressing food-trail changes only for reserve brood cut their command frames from
743 to 24 and improved ordinary play to 5–3 and 121–110 deliveries. It nevertheless
defended only 2–4 against the rush, with candidate blue losing all three games. Alarm
membership describes explicit retasking, not the whole defense ecology: brood routes,
pauses, trails, and bodies still shape what reaches the queen and when.

Narrowing suppression again to only indices 12–15 removed the rush question but also
removed the gain: 3,084 activation frames produced a 4–4 split and 114–117 delivery
deficit. The pheromone-overhead family has no safe monotonic cutoff by colony age.

### A manifest path does not select the local gameplay variant

`coworld run-episode` silently used the certification fixture until
`--variant emerg-ant` was supplied. The invalid fixture had 300 ticks, one hit point,
and forage goal one, so its fast outcomes looked plausible but answered a different
question. Inspect emitted `config.json` before interpreting a new local harness.

### A role name is not evidence of role behavior

The hosted queen-collapse loss showed the worker labeled `HomeDefender` foraging more
than 400 pixels from the queen during the attack. The compact GV57 controller inherited
Stencil's role assignment and logging but did not use worker roles in its objective
selection. Validate claimed specialization from traces and positions, not enums.

### Split terminal mechanisms before interpreting win rate

Stencil and the champion split a two-game color swap, but Stencil's win was a complete
16–13 forage race while its loss ended at 1–3 from the sole death being its queen.
Those episodes motivate queen defense; they do not estimate relative forage strength.

### Resolve the live source before inheriting a fork's identity

Emerg-ant 0.6.0 briefly described a 32-agent neural NAnts game, while canonical 0.6.1
restored the 16-agent pre-NAnts implementation at GameVersion 52. A repo name and recent
history were insufficient to identify the live contract; the canonical manifest, source
URL, and source diff had to be reconciled.

### Reuse a player's substrate separately from its objective model

Paintbot Stencil's Sprite-v1 perception, navigation, and combat are promising because
Emerg-ant shares the engine family. Its permanent heart-retirement and one-shot target
selection are specifically unsafe because Emerg-ant food caches replenish after every
delivery. A compatibility ledger is more reliable than copying the player wholesale.

### Move internal names with the forked contract

Renaming heart/planted/steal state to food/cache/raid before changing behavior exposed
every permanent-retirement dependency across perception, belief, strategy, squads,
action, and trace. The final stale-surface search was empty instead of leaving old
semantics hidden behind code that still compiled.

### A small outward defense shift can suppress opponent throughput

Moving the active queen-defense post from 58 to 68 px preserved the 5–1 local rush
gate. Against the same real champion in the same time window, v6 went 3–1 with a
62–47 delivery edge while exact v5 went 2–2 and 60–55. V6 did not materially add
forage output; it allowed eight fewer opponent deliveries, while traces recorded
13,736 founder alarm-ticks and 246 bites. That is consistent with earlier interception
being the benefit. Four episodes per arm are still too few to call 68 px optimal or
the delta definitive.

The next outward step did not continue the gain. A 78 px post lost 3–5 to exact
v6 in eight matched ordinary games and trailed 114–123 deliveries. The useful
interception band is not monotonic with distance from the queen; 68 px remains the
selected depth rather than the first point in an outward sweep.

Widening the three defender lanes from 34 to 42 px also failed the direct safety
test. The candidate lost its first two blue-seat queen-rush episodes, making v6's
5–1 gate unreachable; the remaining episodes were stopped. Both defense-position
dimensions are sensitive to small changes rather than offering a broad plateau.

Hosted per-index output made final brood index 15 look expendable, but allowing only
that hatch to join the alarm was not safe. It accumulated 838 sampled alarm ticks in
ordinary self-play, lost 3–5, and trailed 116–121 deliveries. A low aggregate delivery
count partly reflects late availability; it does not mean the worker has low marginal
value once alive.

### Require observed activation before promoting a behavioral mechanism

The v7 crowd-scoring candidate nominally beat exact v6 9–7 and 237–220 deliveries
across two local windows, retained the 5–1 rush gate, and later split the real champion
2–2 while leading deliveries 60–48. Yet `forage_crowd_redirect` appeared in zero
sampled frames or objective transitions across all local and hosted artifacts. A
direct head-to-head between effectively identical policies can still produce a
persuasive-looking score through color, seed, and process noise. Activation is a
promotion gate, not just a debugging detail; v7 was rejected and exact v6 source
restored.

The first corrected follow-up also exposed why: `decideEmergAnt` returns before the
generic CTF track update, so inherited `bot.mates` is always empty in Emerg-ant. Using
the live, fog-honest actor list made the rule activate heavily and produced a modest
6–4, 140–137 ordinary edge over ten games. It nevertheless lost the first queen-rush
episode in both colors. Dynamic load spreading joins the broader class of forage
changes that can improve quiet throughput while destabilizing defense through route,
body, pause, and contact timing; it was rejected and not uploaded.

### Stale danger marks are also defensive memory

Across eight real-champion episodes, every v6-behavior loss was a close forage finish
despite a combat edge, and the losing colonies spent thousands of founder ticks in
alarm mode. Capping marker-only response at 360 ticks looked like a direct way to
recover labor, but it lost its first two blue-seat queen-rush games and could no
longer match the 5–1 gate. The 720-tick danger lifetime is not merely post-fight waste:
it preserves distributed threat memory for responders whose local view no longer
contains the attacker. The stale-alarm cap was rejected without upload.

### A subgroup separator is not automatically a repair target

Founder index 2 delivered in every hosted v6-behavior win and in none of the losses,
while still showing carried-marker transitions. A six-tick carry grace scoped to that
worker was therefore plausible and preserved the 5–1 rush gate. It activated 30 times
and nominally won ordinary play 5–3, 116–114, but the target worker delivered only 10
foods versus exact v6's 12. The separator was predictive in the hosted sample without
being causally repaired by carry persistence. The candidate was rejected without
upload rather than promoting an unattributable two-delivery edge.

Releasing only founder index 2 from a marker-only alarm after 360 ticks also failed.
Despite recording zero hosted kills, that worker's persistence was still necessary:
the candidate defended only 3–3, split red 1–2 and blue 2–1. Bite and kill totals are
not a sufficient measure of defensive contribution because positioning and bodies
also shape contact paths. Per-responder stale-alarm release is closed.

Moving only the permanent guard from 68 to 78 px did not rescue the failed global
78 px direction. The scoped guard won its first rush game in both colors but lost the
second in both, capping the result at 4–2. Interception depth is sensitive even for the
dedicated zero-delivery guard; exact 68 px geometry was restored and the 78 px branch
is closed at both colony-wide and guard-only scope.

The stable carrier-lane width has a defense boundary too. Expanding `+/-36` to
`+/-42` improved ordinary play to 5–3 and 117–111 deliveries, but reduced queen-rush
defense to 4–2 entirely through blue's 1–2 result. This is more informative than the
earlier four-lane failure: wider separation can help throughput, but six extra pixels
already perturb nest traffic enough to lose the incumbent safety bar. The candidate
was rejected without upload. The bracketed 39 px midpoint then split 3–3 with perfect
color dependence (red 3–0, blue 0–3), so it too was rejected. Exact 36 px is restored;
the 36..42 px widening interval is closed rather than worth finer tuning against a
strong color-sensitive defense regression.

The first color-scoped composition exposed a flaw in the rush gate itself. Red-only
42 px won its changed red episode, while its exact-v6 blue branch lost two consecutive
games and made the historical 5–1 bar unreachable. Those losses cannot be attributed
to the candidate because blue's code path was unchanged. The candidate was still not
promoted under its preregistered aggregate gate, but future safety claims need a fresh,
same-window exact-v6 rush control; a historical six-game result is too noisy to serve
as a deterministic acceptance test.

A fresh same-window red-side A/B then supplied the missing attribution: red-only
42 px defended 2–2 while exact-v6 36 px defended 4–0. The earlier red sweeps were
sampling noise, not a safe color-specific gain. The carrier-width family is closed;
future rush gates should retain this fresh-control design.

Fresh controls also rejected the 73 px defense-post midpoint. It defended 2–4 while
exact-v6 68 px went 3–3 in the same window; the candidate's final red loss supplied
the delta. With 78 px already losing ordinary play, outward post-depth tuning is
closed and 68 px remains selected.

Moving the direct visible-threat fallback outward from 35 to 40 px looked better in
both its rush A/B (5–1 versus 4–2) and first ordinary window (5–3, deliveries tied).
The independent window reversed to 2–6 and a 106–121 delivery deficit, leaving the
combined ordinary result 7–9 and 218–233. Alarm latency remains seed-sensitive; the
earlier threshold was rejected and exact 35 px restored.

Scoping carried-marker ownership filtering to non-responder brood did not isolate it
from defense. The rule activated for 1,051 sampled ticks and opened 3–1, 62–56 in
ordinary play, but lost all three blue rush games and finished 2–4 versus exact v6's
same-window 3–3. Even when alarm membership is unchanged, brood return routes alter
nest traffic and contact geometry enough to be load-bearing. The candidate was rejected.

Pre-arming the level-triggered bite while defenders tracked an enemy was contract-safe:
movement continued and no cooldown was spent before physical contact. It nevertheless
only tied exact v6 4–2 under rush, then split ordinary play 4–4 with no combat and a
111–120 delivery deficit. A mechanically cleaner input schedule is not an improvement
without outcome activation; exact contact-distance pressing was restored.
