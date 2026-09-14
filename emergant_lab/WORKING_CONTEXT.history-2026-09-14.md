# Emerg-ant working context

Compact current handoff; dated 2026-08-21.

## Live deployment

- Coworld: `emerg-ant` 0.9.1
- Coworld ID: `cow_db246875-b62a-4ac8-ae63-8431dc8c9315`
- Source: `Metta-AI/coworld-emerg-ant@1e0be3f1ecabf2fc70adb8af81818a9947281cc9`
- GameVersion: 57
- Manifest: `sha256:40ac9c373465b19bb96e782cb301ea1e4fa0130471e2f40643c83e5cea6e471c`
- Project-local tools: `coworld 0.1.39`, `softmax-cli 0.26.30`

Re-resolve these before future hosted operations because all are live-state facts.

## Current player

- Account: **James Botts** (`ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce`)
- Policy: `stencil-ant:v6`
- Immutable version ID: `3da684b3-c68a-46c7-9d3a-c25d36a60afe`
- Runtime: `/bin/baseline`
- Submitted to league: **no**
- Source: [`emergant/stencil_ant_gv57_nim/`](emergant/stencil_ant_gv57_nim/)

`v1` and `v2` target the retired GameVersion 52 contract and are incompatible with
the live game. Do not use them as baselines for GV57.

## Rejected v7 experiment

`v7` retains exact v6 defense, alarm, carrier, and pheromone behavior. During forage,
it scores each visible food patch by direct travel distance plus a crowd penalty from
teammates observed during the last 36 ticks and currently within 80 px of that patch.
Each teammate contributes `(80 - crowdDistance) * 0.5`; the lowest-score patch wins.
Telemetry reports `forage_crowd_redirect` when this differs materially from the
Euclidean-nearest patch.

Against exact v6, the first matched four-seed window split 4–4 while v7 led deliveries
115–113. A fresh four-seed window went 5–3 and 122–107, for a nominal combined 9–7
and 237–220 lead. It also retained v6's 5–1 all-in queen-rush result. But the dedicated
objective appeared in zero sampled frames or transitions across all 16 local games,
so this direct head-to-head proves that the mechanism never changed an action.

The uploaded v7 then split paid request
`xreq_29758e26-3c0f-4540-b903-5f6db6126d69` 2–2 against the current #1 real opponent
`emergant-colony:v1`: red swept 2–0, blue lost 0–2, deliveries were 60–48, and kills
were 7–1. Both losses were forage finishes (13–16 and 15–16), not queen deaths. Across
all 64 v7 hosted artifacts, `forage_crowd_redirect` again had zero sampled frames or
transitions.
The request cost $0.064884, contained no self-play, and ran under James Botts. V7 is
therefore rejected as an unvalidated/inert mechanism; exact v6 source was restored.

## v6 behavior

`v6` moves the active queen-defense post 10 px farther outward, from 58 to 68 px.
All other strategy and alarm behavior remains identical to v5. It cleared the local
queen-rush gate 5–1 across both colors, including a 3–0 blue-seat sweep, and was
uploaded inertly for hosted evaluation.

Paid request `xreq_71a6d38c-9128-467c-a844-543802e67ce8` evaluated v6 in four
episodes against the current #1 real opponent `emergant-colony:v1`, with two episodes
per color. V6 won 3–1 (blue 2–0, red 1–1), led deliveries 62–47, and led kills 8–4.
Its sole loss ended 14–16 with a 2–0 kill edge rather than by queen collapse. The
request cost $0.062538.

A same-window four-episode v5 control, request
`xreq_f4b199f9-a3fb-44f9-ab98-c9ec806387a7`, split 2–2 and led deliveries only
60–55. It cost $0.065360. V6 therefore gained one win and reduced champion deliveries
by eight while adding two of its own. The batches are too small for statistical proof,
but they are directionally consistent with the 68 px post improving defense. Both
requests ran under James Botts and contained no self-play. V6 remains unsubmitted.

A later paid refresh, request `xreq_fbf33a18-1731-4b6f-b00d-bfaa8f83f7ab`, again
ran exact v6 against immutable real opponent `emergant-colony:v1`, rotating two games
per color. V6 swept 4–0, led deliveries 64–34, and led kills 7–1. All four episodes
completed under James Botts for $0.112925 total; the opponent seats belonged to Games
Bond. The request contained no self-play. The active league and division currently
returned no memberships/submissions, so this known runnable real policy was resolved
directly rather than inferred from the broken division leaderboard endpoint.

## v5 behavior

`v5` retains v4's defense structure:

- one permanent worker guarding the queen's open-field approach;
- contact interception for enemies within 180 px of the queen;
- an urgent danger pheromone that recruits the seven starting workers while they are
  not carrying food;
- an explicit responder bound that excludes reserve brood from the alarm.

It tightens alarm launch to direct evidence: damage to the queen/guard, an enemy
within 25 px of the queen, or an enemy within 35 px of the queen while visible to a
defender. This replaces v4's 100/180 px proximity alarm.

The retained v3 substrate remains:

- per-frame objective/action/target/carry/stuck/enemy telemetry;
- two deterministic, queen-offset carrier delivery lanes to avoid nest-boundary
  congestion.

Rejected local candidates include distributed food assignment, opportunistic contact
bites, a lone permanent defender, an unbounded alarm that recruited brood, and
four-/six-responder alarm variants.

## Evidence

Matched local play used the exact canonical baseline, seeds 424242–424249, and both
seat orientations for every seed. Stencil went **11–5**, swept both colors on three
seeds while baseline swept none, and led **237–216 deliveries**. The improvement was
therefore promoted and uploaded as v3.

Paid hosted validation was deliberately not self-play. Request
`xreq_e5826219-351f-4b32-84da-07bab81ef8bd` contains two episodes against the current
#1 champion `emergant-colony:v1`, with an explicit 16-versus-16 roster rotating one
seat so each policy played each colony color. It completed without episode failures
for a total cost of **$0.02558**:

- Stencil red: win, 16–13 deliveries, 1–0 kills.
- Stencil blue: loss, 1–3 deliveries, 0–1 kills; the sole death was Stencil's queen,
  collapsing the colony at tick 518.

The 1–1 is too small for a strength claim. It validated connectivity and exposed the
unguarded queen that v4 addresses. The nominal `HomeDefender` worker had been foraging
hundreds of pixels away during the fatal attack because v3 did not implement its role.

The v4 defense was evaluated locally under the explicit `emerg-ant` variant. Against
an all-in queen-rush diagnostic, v3 lost 0–4 and v4 split 3–3 across both colors. In
ordinary matched play against v3, v4 split 4–4 and led aggregate deliveries 117–113.
An unbounded alarm beat the rush 5–1 but lost ordinary play 2–6 (113–124 deliveries)
because 13–15 workers, including brood, answered incidental alarms. Bounding response
to the seven starting workers removed that regression.

v5 then improved rush defense to 5–1 and split ordinary play against v4 4–4 while
leading deliveries 123–116. A hostile-pheromone-gated alternative also defended 5–1,
but trailed v4 115–120 after the two colonies' alarms cross-triggered. An 18 px
contact-only fallback reacted too late and fell to 2–4 against the rush.

Paid request `xreq_5e43440e-ffd2-4e9a-b7db-aa2e40fa001d` then tested v5 against the
current #1 champion `emergant-colony:v1` with 16 copies per colony and one episode per
color. v5 swept 2–0:

- Stencil red: 16–9 deliveries, 0–0 kills; no alarm response.
- Stencil blue: 16–8 deliveries, 2–0 kills; all seven starting workers answered the
  alarm, and the permanent guard at slot 15 made both kills.

Both episodes completed without failure. Actual cost was **$0.017896** ($0.008106 +
$0.009790). This n=2 validates the intended mechanism but is not a precise strength
estimate. No league submission is authorized.

A subsequent local-only candidate let the permanent guard forage visible food within
100 px of the queen while no alarm was active. It split eight ordinary games against
exact v5 4–4 and led deliveries only 118–117; the guard itself delivered no food in
any game. It also slipped from v5's 5–1 queen-rush result to 4–2. The candidate was
rejected and the source restored to exact v5; it was never uploaded.

Trace mining then found that v5's carried-food marker flickers, repeatedly toggling
workers between `carry_home` and `forage`. A latched carry estimate with
nearest-teammate ownership removed that oscillation and beat v5 5–3 with a 122–115
delivery edge, but it defended only 3–3 against the queen-rush probe because true
carriers no longer accidentally joined the alarm during marker-off frames. Letting
latched carriers intercept threats near the queen made defense worse at 1–5. Both
carry candidates were rejected. A six-tick ownership-aware grace also defended only
3–3, while smoothing only the home route and retaining raw alarm eligibility
collapsed to 1–5. The entire carry-smoothing family was rejected and the source
restored to exact v5.

A separate one-ant disruption experiment reassigned the last brood hatch (colony
index 15) to raid the opposing queen. It initially beat v5 5–3 with a 118–115
delivery edge and triggered all seven opposing responders in six of eight games, but
a preregistered fresh-seed extension reversed to 2–6 and 109–118. Combined evidence
was 7–9 with a six-delivery deficit, so the apparent gain was seed noise. The raider
was rejected and never uploaded.

Carrier pheromone churn was then isolated from carry routing. Completely suppressing
the food-trail switch reduced `pheromone_command` frames from 2,336 to 138 in the
first eight-game comparison and beat v5 9–7 with a 234–221 delivery edge across two
independent seed windows. It nevertheless weakened queen-rush defense from 5–1 to
3–3. Keeping the food kind at steady rate still defended only 3–3. A nest-bounded
variant restored urgent rate within 220 px of the queen and recovered to 4–2, but
lost ordinary play 2–6 and 115–121 deliveries. All three variants were rejected and
the source restored to exact v5; none was uploaded.

Expanding v5's two carrier delivery lanes to four (`-54/-18/+18/+54`) then lost
3–5 and trailed 110–122 deliveries in eight matched games. The wider routing cost
more than any congestion relief; it was rejected without upload and exact v5 was
restored again.

Narrowing the original two carrier lanes from `+/-36` to `+/-24` also lost 3–5
and trailed 115–122 deliveries. Exact v5's 36 px offset remains the best tested
lane geometry; the narrower candidate was rejected without upload.

Trace mining then counted 1,047 target changes during continuous v5 forage, 982
while the worker remained more than 50 px from its former target. Full commitment
to a still-live patch activated heavily but lost 3–5 and trailed 107–118 deliveries.
A 50 px retargeting hysteresis split 4–4 and trailed 114–117. Replenishment-driven
nearest-patch switching is therefore useful overall; both commitment variants were
rejected, never uploaded, and the source was restored to exact v5.

Finally, v5's precise damage/contact alarm was opened to all hatched workers to
test whether the old unbounded-alarm failure had been caused only by v4's broad
trigger. The candidate still matched rather than improved rush defense at 5–1,
then lost ordinary play 2–6 and trailed 116–124 deliveries. Reserve brood answered
in four ordinary games (all eight in three), confirming that responder membership
remains the costly control. The candidate was rejected, never uploaded, and exact
v5 was restored.

Worker-level trace mining found 219 raw `carry_home` frames but zero deliveries from
v5's permanent guard across eight ordinary games. A guard-only 180-tick carry latch
tested whether marker flicker stranded food near the nest. Its activation trace fired
in seven of eight matched games for 247 `guard_carry_home` frames, but the guard still
made zero deliveries. The candidate lost 2–6 and trailed 110–123 deliveries: the
carried-food marker's proximity test had attributed nearby teammates' food to the
guard, pulling it away from defense on false ownership. The candidate was rejected,
never uploaded, and exact v5 was restored without a queen-rush run.

The fallback sector sweep was then corrected experimentally to phase workers by
colony index rather than raw alternating-team slot. This removed repeated phase
offsets within each colony, but visible food dominated nearly all decisions: the new
`forage_sweep` trace accumulated only 349 policy-frames across eight games. The
candidate split 4–4 with exact v5 and aggregate deliveries were exactly 116–116, so
the fallback correction was too low-leverage to retain. It was rejected, never
uploaded, and exact v5 was restored.

A final pheromone isolation suppressed food trails only for the last four brood
(indices 12–15). It activated for 3,084 traced carry frames but split ordinary play
4–4 and trailed exact v5 114–117 deliveries, with a red-side gain canceled by a larger
blue-side loss. It did not justify a rush batch, was rejected without upload, and
exact v5 was restored. Scoped food-trail suppression is exhausted.

A bounded hot-path food-spreading candidate then sent even-index foragers to the
second-nearest visible patch only when it cost at most 150 extra pixels. Unlike the
cold fallback sweep, this activated heavily: 19,785 `forage_second` policy-frames
across eight games. It nevertheless lost 2–6 and trailed exact v5 114–123 deliveries.
The full-set distributed assignment had already failed; this bounded variant shows
that even modest static parity spreading loses to nearest-patch replanning in the
replenishing field. It was rejected, never uploaded, and exact v5 was restored.

Filtering raw carried-food markers to the nearest visible teammate then isolated
false ownership without adding persistence. It rejected 3,426 nearby-marker frames,
won ordinary play 7–1, and led exact v5 126–104 deliveries. However, it repeated the
carry-state defense tradeoff: against the queen-rush probe it fell to 3–3 from v5's
5–1, with the filtered candidate losing all three blue games. One timed-out local
episode was rerun at its exact seed with a longer wall-clock allowance and completed
as a loss. The global filter was rejected and never uploaded; a guard-only isolation
is the next experiment.

The guard-only ownership filter rejected just 91 false-nearby frames across eight
ordinary games. It lost 3–5 and trailed exact v5 111–119 deliveries, while queen-rush
defense reached only 4–2. Narrowing the filter removed the global version's forage
gain without fully restoring defense. It was rejected, never uploaded, and exact v5
was restored; the ownership-filter family is closed.

Food-trail suppression was then limited to reserve brood (colony index 8+), leaving
all seven alarm responders on exact v5 behavior. The arm activated for 8,009 brood
carry frames and cut their pheromone-command frames from 743 to 24. It won ordinary
play 5–3 and led 121–110 deliveries, but still collapsed to 2–4 against the queen-rush
probe, with candidate blue losing all three games. Brood need not answer the alarm to
affect nest traffic, contact timing, and defense. The candidate was rejected, never
uploaded, and exact v5 was restored.

Distance-scaled teammate repulsion then reduced the existing forage-spacing force
linearly from 0.7 at contact to zero at the 40-pixel boundary. The first matched
window narrowly favored it 5–3 and 122–117 deliveries, while queen-rush defense held
at v5's 5–1. An independent seed window, however, split every seed by color and
finished 4–4 with the candidate behind 108–109 deliveries. Combined ordinary evidence
was 9–7 but only 230–226 deliveries, too small and non-replicating to distinguish from
seed noise. The candidate was rejected, never uploaded, and exact v5 was restored.

A path-awareness probe preferred the nearest footprint-clear food patch when it was
within 120 pixels of a wall-blocked Euclidean nearest patch. The alternate target
activated for 414 traced policy-frames but lost 3–5 and trailed exact v5 110–121
deliveries. Activation was not a useful separator: the two worst paired seeds had
both high and very low alternate-route counts. A direct-line test is not a reliable
proxy for total navigation cost, so this implementation was rejected, never uploaded,
and exact v5 was restored.

Keeping the proven `+/-36` carrier lanes but assigning each return to the nearer
side of the centerline also regressed. It lost 3–5 and trailed exact v5 113–120
deliveries across both colors. Dynamic approach-side convergence did not compensate
for losing stable worker-level separation, so the candidate was rejected, never
uploaded, and exact v5's identity-based lane assignment was restored.

Suppressing the generic stuck-jink while queen defense was active then failed the
rush gate immediately: the candidate lost its first episode in both colors and could
no longer match v5's 5–1 ceiling, so the remaining four episodes were stopped. The
random movement is not merely erroneous hold-point churn; it helps defenders break
contact geometry or re-enter interception paths. The candidate was rejected without
an ordinary batch or upload, and exact v5 was restored.

Pre-guard v3 controls showed founder index 5 had delivered less than index 7, so a
role-swap candidate made index 5 the permanent guard and restored index 7 to forage.
Defense geometry dominated that apparent opportunity: the candidate lost two of its
first four queen-rush episodes across the color swap and could reach at best 4–2, below
v5's 5–1. The remaining two episodes were stopped, the candidate was rejected without
an ordinary batch or upload, and guard index 7 was restored.

A corrected follow-up kept index 5 on v5's exact center guard post, isolating guard
identity from the earlier off-center lane confound. It still lost its first rush
episode in both colors, making the 5–1 gate unreachable immediately. The runs were
stopped, the candidate was rejected without ordinary play or upload, and index 7 is
now pinned by direct identity-controlled evidence.

Far-field danger signaling was then suppressed outside the 220-pixel queen perimeter,
because v5's alarm responders only consume urgent danger near home. The supposedly
unused branch activated for 983 traced policy-frames, but the candidate lost 2–6 and
trailed exact v5 114–124 deliveries. Public danger marks affect the ecology through
trail erasure, command-pause cadence, and movement timing even when no explicit alarm
consumer reads them. The candidate was rejected without a rush run or upload, and
exact v5 was restored.

Extending the same ordinary encounter signal from 80 to 120 pixels tested the opposite
direction. The added band was low-volume and the candidate lost 3–5 while trailing
118–120 deliveries. Earlier signaling did not compensate for its extra command pauses
or trail interference. The candidate was rejected without a rush run or upload, and
the exact 80-pixel v5 threshold was restored; encounter-signal range is closed.

An urgent-worker candidate kept ordinary scouts and alarm responders at pheromone
rate 3, avoiding the carrier-to-scout `3 -> 0 -> 1 -> 2` command cycle. It halved
command frames (1,194 versus 2,341), split ordinary play 4–4, and led deliveries only
116–113. The defense gate then produced two blue-side losses in its first four games,
making v5's 5–1 unreachable. The remaining rush episodes were stopped; the candidate
was rejected without upload and exact v5 rates were restored.

## Next decision

Treat v6 as the current promoted candidate. V7 showed why a direct head-to-head needs
an activation gate: its nominal 9–7 local result and 2–2 hosted split did not prove a
mechanism whose trace never appeared. Any follow-up crowd rule must first produce
observable redirects in a cheap local batch, then clear ordinary and rush comparisons.
V6's rejected 78 px post, 42 px defender lanes, and final-brood responder experiments
close those immediate defense branches.

A corrected crowd follow-up exposed the root cause: Emerg-ant returns from `decide`
before the inherited CTF track update, so `bot.mates` is empty in this game mode. The
candidate instead used the same live `client.actorsFor(myColor)` seam as existing
forage repulsion, with a 120 px, weight-1 crowd penalty. It activated heavily (409
redirect entries and 292 sampled redirect ticks) and went 5–3 with a narrow 112–109
delivery edge on four fresh seeds; including the activation seed, it went 6–4 and
140–137. It then lost the first queen-rush episode in both colors, making v6's 5–1
gate unreachable. The remaining rush games were stopped, the active crowd candidate
was rejected without upload, and exact v6 source was restored.

The combined eight hosted v6-behavior games (v6 plus behaviorally inert v7) went 5–3
with 122–95 deliveries and 15–5 kills against the champion. All three losses were
close forage finishes despite winning combat, and losing colonies accumulated
2,767–4,525 founder alarm ticks. A stale-alarm candidate therefore ignored marker-only
alarms after 360 ticks unless that worker could currently see an enemy within 180 px
of the queen. It lost its first two blue-seat queen-rush games; its best possible
finish had fallen to 4–2, below v6's 5–1 gate. Remaining games were stopped, the
candidate was rejected without ordinary play or upload, and exact v6 alarm persistence
was restored.

Hosted index-level results then showed founder index 2 delivered at least once in all
five v6-behavior wins and zero in all three losses. Its loss traces still contained
repeated carried-marker transitions, suggesting marker flicker rather than food
discovery. A six-tick carry grace scoped only to index 2 retained the 5–1 queen-rush
gate and activated 30 times in eight fresh ordinary games. It nominally went 5–3 and
116–114, but index 2 itself delivered only 10 foods versus 12 for exact v6. The target
metric regressed, so the win-rate edge was not attributable to the proposed repair.
The candidate was rejected without upload and exact v6 carry handling was restored.

Founder index 2 was then allowed to leave only a marker-only alarm after 360 ticks,
while all six other responders retained exact v6 persistence and index 2 continued
defending whenever it could see a threat within 180 px of the queen. The supposedly
low-contact specialization still defended only 3–3 against the queen-rush probe
(red 1–2, blue 2–1). It was rejected without ordinary play or upload, exact v6 was
restored, and per-responder stale-alarm release is closed.

Because the permanent guard owned 5 of 15 hosted kills and never delivered food, a
guard-only depth experiment moved index 7 from 68 to 78 px while all alarm responders
stayed at 68 px. It won the first rush game in both colors, then lost the second in
both; with a best possible 4–2 finish it was stopped and rejected without ordinary
play or upload. Exact v6 was restored. Both global and guard-scoped 78 px depth are
closed; 68 px remains the only tested post depth that preserves the 5–1 gate.

Widening the stable two carrier lanes from `+/-36` to `+/-42` then went 5–3 with a
117–111 delivery edge across four fresh seeds, but defended only 4–2 against the
queen-rush probe (red 3–0, blue 1–2). It was rejected without upload. Unlike the
previous four-lane and `+/-24` failures, this establishes a local throughput gradient
but brackets the defense boundary between 36 and 42 px; a 39 px midpoint is next.

The bracketed `+/-39` midpoint did not recover the defense margin. It split perfectly
by color against the queen-rush probe: red won 3–0 and blue lost 0–3, for 3–3 overall.
That is materially below exact v6's 5–1 gate, so the candidate was rejected without an
ordinary run or upload and `+/-36` was restored. The `36..42` carrier-width interval
is closed; its apparent throughput benefit is inseparable from unacceptable blue-side
defense sensitivity at the tested integer midpoints.

A color-scoped composition then used `+/-42` only for red and exact v6 `+/-36` for
blue, based on both widened candidates' red 3–0 results. The changed red branch won
its first rush game, but the behaviorally unchanged blue branch lost its first two.
The composed image could no longer reach the preregistered 5–1 aggregate bar, so the
remaining games were stopped and the candidate was not run ordinarily or uploaded.
Because those failures occurred wholly in unchanged v6 behavior, this is also evidence
that a fresh six-game batch is too variable to compare categorically with a historical
5–1. Future defense experiments should run fresh candidate and exact-v6 controls in
the same window and interpret the delta, not historical threshold attainment alone.

That corrected matched test closed the loophole. On a fresh manifest, red-only
`+/-42` went 2–2 against the rush while same-window exact-v6 red went 4–0. The earlier
red sweeps were not stable, and the scoped candidate was rejected again without
ordinary play or upload. All tested carrier-width changes around `+/-36` are closed.

The 73 px midpoint between selected 68 px and rejected 78 px was then evaluated with
fresh same-window controls in both colors. It defended only 2–4 while exact v6 went
3–3, with both arms struggling as blue. The midpoint was rejected without ordinary
play or upload and 68 px was restored; outward defense-depth tuning is closed.

Moving the visible-threat alarm launch from 35 to 40 px beat a same-window rush
control 5–1 versus 4–2 and opened ordinary play 5–3 with deliveries tied 112–112.
An independent seed window reversed sharply to 2–6 and 106–121. Combined ordinary
evidence was 7–9 and 218–233, so the candidate was rejected without upload and the
exact 35 px v6 threshold was restored. Earlier alarm is not a stable improvement.

The prior global carried-marker ownership filter's 7–1 forage signal was then isolated
to reserve brood (indices 8–15), leaving all alarm responders untouched. It activated
for 1,051 sampled frames across 31 artifacts and opened ordinary play 3–1 with a 62–56
delivery edge. Yet it defended only 2–4 against the rush while same-window exact v6
went 3–3, with the candidate losing all three blue games. Brood routes and bodies are
still defense-coupled; the candidate was rejected without upload and exact v6 restored.

Canonical mechanics say A is level-triggered, movement continues while it is held,
and cooldown is spent only on physical contact. A defensive pre-arm candidate therefore
held A whenever the queen or an active defender tracked an enemy, rather than waiting
for a sampled distance of 18 px. It matched exact v6 4–2 in a fresh rush A/B, then
split ordinary play 4–4 with no kills and trailed deliveries 111–120. The candidate
was behaviorally safe but showed no benefit, so it was rejected without upload and
exact v6's contact-distance press was restored.

Do not use a paid experience request for self-play; every paid validation must target
a current real opponent under James Botts. Do not submit without James's explicit
permission.
