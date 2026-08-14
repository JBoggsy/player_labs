# Working context — paintbot_lab

*The live, minimal, high-signal state of what we're working on right now.
Update as you learn; clear/reseed on a pivot.*

## Parallel RL track

The new learned policy lives under `paintbot/rl/`, separate from Stencil.
`Qwen/Qwen3-0.6B-Base` is the selected pretrained model. Observations will use
Qwen's native tokenizer over semantic Sprite-v1 entity labels, extracted label
numbers, and normalized geometry; the superseded external FastEmbed projection
has been removed. Initial training is mixed-era behavior-cloning SFT that
predicts four factorized action tokens and `<STOP>`.

The first observation-length experiment refuted the faithful all-label grammar
(global p99 30,297; max 43,672). The source-derived bot-semantic follow-up is
now confirmed on the same 5,000 balanced GV16/24/30/35/40 observations: it
excludes only `fog`, `splatter …`, `hit splat …`, and `damage pop …`, retains
unknown labels, and achieved global p99 3,178 / max 4,424. This denylist is now
the canonical entity view.

The first vertical slice is implemented. It uses 16 factorized action tokens
plus `<STOP>`, a previous-mask-aware decoder, exact episode-level packed maps,
a once-per-episode convolutional feature cache with a per-tick local gather,
replay action extraction/alignment, LoRA SFT, constrained inference, and action
tracing. Defaults (32 map tokens, stride 8, zero-tick action delay, LoRA rank 8,
2,048 training-token ceiling, gradient checkpointing, and greedy decoding
without KV cache) remain explicit experiment knobs. Zero-tick alignment is settled:
six GV40 POVs gave 99.01% overall and 97.36% turn-transition agreement, versus
about 89.7%/80.7% for either neighboring tick.

The initial Mac SFT plumbing pass is complete: 125 balanced samples (25 each
from GV16/24/30/35/40 winning POVs), 550 seconds on the 48 GB M4 Pro, no swap
during the accepted run, and training loss down from 10.76 first-20 mean to
2.31 last-20 mean. A disjoint 25-example holdout reached 72.0% constrained
component / 8% exact-action accuracy, only 0.8 points / zero points above the
majority baseline. The pipeline works, but observation-conditioned behavior is
not demonstrated yet. Design,
provenance, and verdicts:
[`docs/designs/rl-policy.md`](docs/designs/rl-policy.md) and
[`docs/reports/rl-bot-semantic-length-experiment.html`](docs/reports/rl-bot-semantic-length-experiment.html).

The full replay-to-checkpoint pipeline is now implemented in
`paintbot/rl/pipeline.py`. Its manifest pins episode IDs, exact source commits,
reward-qualified POVs, replay-disjoint splits, preparation settings, and GPU
hyperparameters. It downloads replay metadata, compiles against each era's
locked source, hash-validates reconstruction, persists only bot-semantic
entities, balances trajectories per era, bundles prepared data for transfer,
and trains with validation, best/final saves, and resumable Accelerate state.
The tracked corpus trains on GV16/24/30/35 and reserves GV40 as an unseen-era
test. A two-era MPS smoke completed end to end (prepare, one-epoch LoRA train,
validation evaluation, and bundle); its two-example accuracy is plumbing-only.
The full exact-source preparation also completed locally: 1,700 balanced train
samples (425 per training era), 692 balanced validation samples (173 per era),
and 1,347 GV40 test samples. Its ignored GPU-transfer bundle is
`paintbot/rl/data/runs/historical-cross-era-v1.dataset.tar.gz`.

The first mettabox1 GPU run is complete. CUDA and BF16 canaries passed, then a
1e-4/2e-4/4e-4 validation sweep selected 2e-4 at epoch 3 (validation loss
0.299010). The selected arm was the full three-epoch, 1,700-example job. On the
sealed GV40 split it reached 94.45% constrained token and 77.13% exact-action
accuracy, but a held-action persistence baseline reached 94.42% and 77.06%.
Only 1/309 changed-action examples was exactly correct. The checkpoint proves
the remote pipeline, not useful observation-conditioned control; do not package
it as a live player. Full environment, sweep, per-era metrics, paths, and hashes:
[`docs/reports/rl-mettabox1-sft-2026-08-07.md`](docs/reports/rl-mettabox1-sft-2026-08-07.md).

A matched changed-component loss-weighting experiment is also complete. The
training corpus has 741 changed versus 6,059 unchanged control components, so
class balancing resolves to 8.1768×. Validation changed-action exact progressed
from 0% at 1× to 5.1% at 3×, 12.1% at class balance, and 15.0% at 16×, while
overall exact fell from 69.1% to 62.9%, 48.6%, and 34.8%. Class balance was the
validation knee. On sealed GV40 it reached 9.4% changed-action exact versus
0.32% for uniform, but overall exact fell to 35.3%, change precision was only
13.7%, and turn accuracy fell to 43.1%. Weighting alone is rejected as the
solution; next change the transition sampling and temporal information. Report:
[`docs/reports/rl-action-change-weighting-2026-08-07.md`](docs/reports/rl-action-change-weighting-2026-08-07.md).

The matched transition-sampling x four-tick-history experiment is complete.
Transition-centered sampling alone was flat; compact causal history was the
material intervention. On natural validation, history raised changed-action
exact from 0% to 7.9%, and adding balanced transition sampling reached 8.4%
with 73.1% change precision. The selected combined model generalized only
partly to sealed GV40: changed-action exact improved from 0.3% to 3.9% and
changed-component accuracy from 0.7% to 8.8%, but overall exact fell from
77.1% to 74.7% and change precision fell to 45.2%. Keep temporal history, but
do not deploy this checkpoint; expand replay/expert diversity next. Report:
[`docs/reports/rl-transition-temporal-2x2-2026-08-07.md`](docs/reports/rl-transition-temporal-2x2-2026-08-07.md).

The exhaustive expert corpus is preprocessing on mettabox1. All 327,188 replay
downloads completed, and preprocessing resumed from its trajectory markers
after a disk-bounded storage upgrade. Each worker now converts deterministic
512-trajectory groups to verified memory-mapped Arrow parts and deletes their
source JSON incrementally; the global dataset is a virtual nested manifest, so
neither shard consolidation nor global merge duplicates the ~2 TB corpus. The
handoff builds a 250,000-example epoch balanced 50/50 on action transitions and
across GameVersion/expert/world, runs a 1,024-example BF16 canary, then starts a
three-epoch 2e-4 LoRA job. Full training checkpoints every 1,000 optimizer
updates and can resume at the next deterministic batch. These are conservative
initial settings and remain open to later budget and sampling experiments.
The handoff is live under a detached 60-second retry supervisor, with an
`@reboot` crontab recovery entry and the checked-in user service enabled.
Systemd lingering could not be enabled without sudo, so cron—not the user
unit—is the reboot guarantee.

## Current objective

**v67 (post atlas + conservative re-expressions) is ACCEPTED (2026-08-14) —
the nav/tactics rework's strategy-facing substrate is complete.** Batch
58/58, 0 ops: parity with v66 (14W-14L vs 16W-12L, every mode within one
game, both arms swept ffa 4-0); the v66 h2h scatter is RESOLVED as an
outlier control (13-3 vs a ~9-7 true level across four same-cell arms).
Hosted: 1163 plans at 9ms, 0 unroutable/fallback, 3 snapped; giant atlas
21.6k posts in 88-181ms under contention. NEW PLATFORM CONSTRAINTS:
experience credits (2500/wk, cap 5000 — batches now budget-bound; refill
Sun) and per-upload auto-evals (10-ep, share the pool).** v67 (`f8289d11-7f88-4502-ad35-2edf4a415264`, tag
`purpose=post-atlas`), Codex-implemented: posts EVERYWHERE there is cover
(14.4k atlas posts on the giant, 179 ms build, full 1300 px 16-sector reach
profiles, lazy ducks), two-phase selection with situational bearing,
early_defense on home-room entrance gates (live-verified: 16/16 seats
distinct, endzone-interior, gate-anchored), barrage on normalized
danger-penalized room peaks. Corridor machinery deleted; side-lane TODO
retired. Viewer migrated to atlas rendering + rewritten mirror (200/200).
NOTE: era-gated viewer (pre-v67 traces need --allow-drift). Game-pin gap
(0.7.215 vs canonical 0.7.229) parked in TODO.md. Local branch is ~7
commits ahead of origin — push awaiting James. Batch verdict appended to
VERSION_LOG v67 when complete (re-tests the v66 h2h scatter).



**v66 (Layer 4 — the Intent & goal contract) is ACCEPTED (2026-08-13).**
Batch 58/58, 0 ops: totals within noise (15W-13L vs control 18W-10L; the
h2h control ran hot — carrier-evasion suspicion DISPROVEN, no carry phase
occurred in h2h; duo improved to 4W-4L, best yet vs swgy). Contract
counters hosted: 1482 plans/30 seats at 8ms, 0 unroutable, 0 fallbacks, 5
snapped. Watch h2h scatter in the v67 batch. **v66 uploaded;** v66 (`80e2a0a4-9662-4722-8fe0-e3aa4a57e593`, tag
`purpose=intent-contract`), Codex-implemented under orchestration: typed
Intent (all seven reason-string lists dead, grep-gated), goals validated at
selection via `nearestReachable`, all five beelines + FlowReasons dispatch
dead (flow fields = oracle only), carrier ×2.5 / hunter ×0.25 danger
profiles live with profile-change cache invalidation, unroutable = hold +
loud `plan_unroutable_bug`. Live checks: 0 unroutable, 2 snapped (was 9),
carry/steal movement now planner-routed (75 plans in an h2h episode where
v65 ran 0). v67 next after the batch: early_defense/barrage over PoIs +
side-lane posts; then Layer 5 (bounded follower). Full story: VERSION_LOG
v66.



**v65 (Layer 3 — the planner) is ACCEPTED (2026-08-13) — the Layer 4
baseline.** Batch 58/58, 0 ops failures: gameplay parity with v64 (14W-14L
vs 12W-16L; h2h/duo identical, +2 ffa), and the planner proved itself in
real competition: 925 hosted searches at 13.5 ms mean, 0 unroutable,
0 beeline fallbacks, 9 endpoint snaps (the Layer 4 producer-cleanup
worklist counter). **Next: Layer 4 — the Intent contract** (typed Intent,
component-validated goals, kill FlowReasons + all beelines + reason-string
dispatch, carrier/hunter profiles live).**
v65 (`d8b5ca59-503f-4f8c-85b8-df052fb38998`, tag `purpose=layer3-planner`),
implemented by Codex CLI under orchestration with two review-driven fixes:
weighted A* on a 4px lattice (exact supercover edges, completeness cascade
to 1px gated on sameComponent, unbiased 32px endpoint snapping bridging
Layer 4), LOS-exposure DangerField on Belief (legacy danger untouched),
oracle heuristic measured at worst 1.13% deviation on real maps
(STENCIL_PLAN_ORACLE valve). astarWaypoint contract preserved; FlowReasons
+ beeline fallback intentionally survive until Layer 4. Live forced-A*
check: 0 unroutable after snapping (was 27%). Viewer has a planner layer
(scenario routes + LOS heatmap). Full story: VERSION_LOG v65.



**Navigation Layer 3 is implemented locally and in live validation
(2026-08-13), not yet accepted.** The weighted pixel-lattice planner now has
two compatibility repairs found by independent/live property evidence: a
4px→2px→1px cascade makes same-component planning complete across narrow
standable ridges, and non-standable pre-Layer-4 endpoints resolve to the nearest
standable pixel within 32px. Snapshot counters expose lattice fallback and goal
snapping; the latter is the retirement signal once Layer 4 validates intent
goals at their producers.

**v64 (wide post pool) is ACCEPTED (2026-08-12) — the Layer 3 baseline.**
Matched batch 58/58, 0 ops failures: gameplay PARITY with v63 (12W-16L vs
14W-14L; h2h 9-7 both) — the pool's value is substrate for Layer 4
intent-aware selection, not immediate wins. Infra strictly better: hosted
paired giant probes v64 post_ms 22/27 ms, seat init ~0.88 s (fastest ever;
v63 carried mid-episode minting hitches), v64 won both in-episode duels
(n=2, ops-tier). It remains the baseline for the Layer 3 implementation under
live validation above; its borrowed-field-access requirement is already landed
(`fieldsFor` returns `lent`; goal-slot rule enforced at call sites).

Original upload note: **v64 uploaded; batch was pending.** v64
(`d3504b01-ea7e-46db-9b3d-59a959940752`, tag `purpose=wide-post-pool`):
~200-250 ray-scored, duck-paired potential posts per front (was 16), all
choice at selection time; defenders pick from the pool with a separation
filter. The pool detonated report-M2's unbounded Dijkstra minting
(`routeDistance(home, candidate.pos)` minted a field per candidate) — fixed
at the root: goal-slot-takes-stable-goals-only rule + `fieldsFor` returns
`lent` (no more 1.4 MB copies anywhere, incl. per-tick flowWaypoint).
Giant post_ms 18 ms with the 14x pool; tick rate faster than v63. Design:
`docs/designs/nav-wide-post-pool-v64-2026-08-12.md`.

**v63 (post re-sourcing + belief-scored facing, D5-2) is ACCEPTED
(2026-08-12) — the new nav-rework baseline for Layer 3.** v63
(`fba7d396-9166-49de-9252-b6bef98b0077`, tag `purpose=post-resourcing`):
post candidates from on-route gate vicinities (48 px, no baked direction);
facing scored at selection time against believed enemy tracks via
`facingScore` + the pure `selectRankedPost` core; defenders order in 64 px
distance bands. The decisive perf find: `fieldsFor` returns RouteFields BY
VALUE (~1.4 MB memcpy per `distanceAt` call) — per-front field hoisting took
giant post_ms 1528→73 ms local, and the hosted paired probes measured **v63
128/132 ms vs v62 3405/2860 ms in the same episodes** (giant seat init
0.95 s vs 4.2 s; below the v61 baseline). **Layer 3 hard requirement:
borrowed/indexed field access — per-tick flowWaypoint/routeDistance still
pay the copy.** Matched batch 58/58, 0 ops failures: v63 15W-13L vs v62
10W-18L (h2h 11-5 vs 6-10; duo 2-6 vs 3-5; ffa 2-2 vs 1-3); v63 lost both
n=2 giant probe scores (ops-only, watch next giant batch). The topology
viewer now shows post fronts + a belief-parameterized selection simulator
(shift-click enemies), JS mirror fail-closed against 200 harness-run
production-code samples. Design: `docs/designs/nav-post-resourcing-v63-2026-08-12.md`.
**Next: Layer 3 — the single weighted-A* planner** (sketch §3.3, Q1-Q3).

**Navigation rework Layer 2 is IMPLEMENTED and uploaded as v62 (2026-08-11);
hosted matched batch COMPLETE — see v62 entry in VERSION_LOG.** v62
(`d415aded-ae80-4140-9f27-ad073718af25`, tag `purpose=nav-topology`) derives
everything from the clearance field at init: engine-exact 4-connected
component labels (`componentOf`/`sameComponent` — the future Layer 4
reachability contract), priority-flood watershed rooms + chokepoints with
persistence merging, 16-ray directional cover (map edge is NOT cover; the
`cover` grid and all its consumers now ride it), and `defenseGate` replacing
the authored `chokePoint` (rallyPoint/pastRally/axisPoint deleted). James
ruled the proposal
([`docs/designs/nav-layer2-topology-proposal-2026-08-11.md`](docs/designs/nav-layer2-topology-proposal-2026-08-11.md),
rulings D1–D7 recorded inside) and added two requirements, both shipped: the
**offline topology process visualizer** (`tools/render_topology.py` +
`tools/topology_debug.nim`: watershed flood scrubber from the agent-logged
clearance, merge log, cover roses, gate scoring; zero-drift verified against
a real agent trace) and **configurable cover rays (default 16)**. Evidence:
21.9M property checks vs brute force; corpus counts/timings in VERSION_LOG
(giant seat init grew to ~2.36 s, +~690 ms Layer 2 — init-only; disclosed).
The matched v62-vs-v61 batch (12 requests / 58 episodes, request IDs in
VERSION_LOG v62 entry) completed 58/58 with 0 ops failures: **v62 ≥ v61 in
every mode** (h2h 11W-5L vs 6W-10L; duo 2W-6L vs 0W-8L against the harsh
swgy matchup; ffa 2-2 both; total 15W-13L vs 8W-20L), duck micro clean,
giant probes passed —
**Layer 2 ACCEPTED; v62 is the Layer 3 baseline.** Known cost: hosted giant
seat init v62 3.2-4.2 s vs v61 1.9-2.1 s, part of it post_ms growth from
directional cover admitting more post candidates (input to the Q6 post
rebuild + init rework). **The campaign board was
ROLLED BACK to the 10×10 square board late 2026-08-11** (after the morning
round-967 hex re-verification) — `docs/tournament-like-experience-requests.md`
carries the rollback note; re-resolve the board live every study.

**Navigation rework Layer 1 is SHIPPED and validated as v61 (2026-08-11).**
Direction set by James's review of the navigation deep-dive: one planner, no
beelining, no 8px movement coarsening, dynamic PoIs, goals validated before
nav. Sketch:
[`docs/designs/nav-rework-sketch-2026-08-11.md`](docs/designs/nav-rework-sketch-2026-08-11.md).
v61 (`3380ab6d-5bc8-45b7-9429-ff7b74fc1f85`, tag `purpose=nav-clearance-nudge`)
carries the exact L∞ clearance field, `canStand`/`segmentClear`/`nudgeClear`
replacing both old segment predicates, and the nav grid derived
(bit-identical, hosted-verified) from clearance; erosion deleted. v60
(clearance without `nudgeClear`) measurably regressed — exact micro-nudge
validation rejected peeks the engine's wall-slide executes, duck time
11.3%→15.0%, 10W-23L vs v59's 16W-17L — and is superseded. v61's matched
round-2 batch: 13W (+16) vs paired v59 10W (+4), n=32/arm, 0 ops failures in
130 total episodes, duck time restored. Full evidence in `VERSION_LOG.md`
v60/v61 entries; artifacts in `local_data/episodes/nav-clearance-v6{0,1}`.
**Layer 2 (topology/PoIs from the clearance field) is next**; the wall-slide
micro lesson is recorded in the sketch for Layer 5.

**Campaign contract drift found 2026-08-11 (round 967):** 16×16 hex board
(migrated round 955), true `1v1` head-to-head mode (49 cells), `2v2` duo
seating now an **even** captain/ally split (not 7+7+1+1), all cells carry
`map_size`, deployed canonical Paintbot 0.7.227, and campaign episodes carry
perk loadouts. `docs/tournament-like-experience-requests.md` re-verified and
updated. NOTE for James: `user_preferences.md` still cites 7+7+1+1 — his text,
left untouched. Also: `git -C ~/coding/metta pull` fails from this environment
(SSH publickey denied); today's read used HEAD `84e13cb799` (2026-08-11 23:05Z,
minutes old at read time).

**v59 is uploaded and awaiting its first evidence (2026-08-08).** v59
(`73caf241-9198-4245-bcf5-e9ddec986311`, tag `purpose=spray-avoidance`) adds
enemy-loadout belief (weapon/grenade/barrier/shield off the identity badge) and
the `clear_spray` keep-out rung, plus a spray shout and spray-carrier target
priority. Design:
[`docs/designs/spray-avoidance-v59-design.md`](docs/designs/spray-avoidance-v59-design.md)
— read revisions 2-3, which record what two adversarial review rounds corrected,
including a shield model that was simply wrong in revision 1.

It also repairs a **dead observable**: `shield carried` is unreachable in the
engine, so `enemy.shielded` and `iHaveShield` had been permanently false and
three consumers were dead code (the shield weight in `fight.nim`, the grenade
gate in `action.nim`, the shield skip in `items.nim`). That revives three
behaviors at once, which is an A/B confound — `STENCIL_SHIELD_AWARENESS`
(default on) isolates it.

**No runtime evidence yet.** `stencil_nim` has no tests; clean compiles are the
only pre-upload signal. First hosted signal is the mechanism probe
`xreq_33b25248-0e6b-4909-b903-fe4300253bb7` (2 episodes, 16 seats all v59, run
on canonical **paintbot 0.7.216** while the build pin is 0.7.215/`6c7a4c0e`).
That probe is a **debug probe**, not campaign-shaped, so it cannot support a
gameplay claim — it only answers whether the mechanism fires. The verdict needs
a matched campaign-shaped A/B against v58: one live `2v2`-mode cell with its
exact `map_ref`/`mode`/`map_seed`, v58 and v59 as opposing captains, two pinned
live champion allies, and both captain seatings.

**v58 is the active James Botts champion.** v58
(`1f7f7c75-5edb-4b35-aba8-241264bbd611`) adds GV41 barrage-center evacuation
on top of the fully traced v57 line. It was submitted on 2026-08-07 as
`sub_a1298aee-c6d1-4141-bca4-b42133b3058e`, immediately placed and qualified,
and is competing as champion through membership
`lpm_c6ccaa63-6a6f-47c0-bea5-2a04ad6454fc`. V54 is now the previous champion.

**v55 is rejected as the general replacement for v54.** v55
(`bc7c1079-5684-47b0-82b2-7d2f69e75089`) adds a one-way covered spawn-box
opening: all agents hold distinct cover cells inside their endzone until every
still-live enemy team has fewer aggregate lives than their team. Carry-home,
heart-thief interception, and grenade evasion remain emergency overrides. The
`linux/amd64` image built and uploaded successfully; v55 has not been submitted.
The 100-episode round-399 matched A/B finished 39-11 for v55 versus 42-8 for
v54. V55 cut deaths during its opening window from 75 to 32, but produced 70
fewer kills overall. Two-team results tied at 22-4 per arm; FFA regressed from
20-4 to 17-7 and accounted for an 80-kill shortfall. Two FFA games never
released the strict all-opponents lead gate before ending in capture losses.
V55 also lost both Max Yankov `(3,2)` captain seatings, while v54 split 1-1.
Keep v54 as champion. Full report:
[`docs/reports/stencil-v55-early-defense-r399-2026-08-06.md`](docs/reports/stencil-v55-early-defense-r399-2026-08-06.md).

V56 (`e49b4d94-6410-41bb-94c4-8120f05afca6`) retains v55 behavior and restores
complete belief-viewer snapshots, including the danger grid and a new
cover-blocked ally-vision coverage grid. It is uploaded for replay diagnosis
only and has not been submitted. V54 remains champion.

V57 (`c4a663a4-f6d4-4be4-92ca-cfffa891202e`) retains v56 behavior but lowers
Stencil's shared chat interval from 30 ticks to the engine's exact 24-tick
limit. It was built against canonical Paintbot 0.7.208 / source
`871ace1e5bd1a47171451e2ce3dc9004ee0a9c2b`, uploaded inertly, and has not been
evaluated or submitted. V54 remains champion.

V58 (`1f7f7c75-5edb-4b35-aba8-241264bbd611`) is the first GV41 adaptation.
When the visible barrage marker reports positive depth, Stencil now takes the
map's walkability-aware center flow and holds within an 80-pixel central ring.
Carry-home, heart-thief interception, and immediate grenade warnings remain
higher priority; combat aim and fire stay active, while lower-priority movement
micro cannot pull the agent off the route. The marker, objective, and cumulative
activation ticks are traced. It was built against canonical Paintbot 0.7.211 /
source `9dedac0ed6011aeca92bf2c6403b0e70c955f461` and uploaded with full tracing.
A full 16-seat hosted mechanism probe
(`xreq_34bd90b7-1d97-4dd1-a77f-aa1aabf975a6`, episode
`178292c1-a143-47a7-bdc7-c5fa0a5c985b`) reached the barrage: all agents selected
the generated center within a two-tick window, and 12/16 reached the 80-pixel
ring. The remaining four repeatedly routed center after respawns but exhausted
their lives en route. Marker consumption and center navigation therefore work;
next add individual-grenade tracking and evasion. This was a mechanism probe,
not performance evidence.

A 30-episode tournament-like v58 evaluation completed against the current
Paintbot 0.7.212 campaign field: 10 current-board `1v1`, 10 `2v2`, and 10
`4ffa` episodes. The two-team samples pair five cells with both captain
seatings; the FFA samples give Stencil whole-color ownership and rotate its
color. V58 finished 22-8 overall: 6-4 on `1v1`, 9-1 on `2v2`, and 7-3 on
`4ffa`, with zero operational failures. This is credible absolute performance
but not matched evidence against v54. The exact request manifest is recorded in
[`paintbot/stencil_nim/VERSION_LOG.md`](paintbot/stencil_nim/VERSION_LOG.md).
No `4ffa8` request was invented because it was absent from the live board.

The campaign commander is now steered by a deterministic, version-aware
one-round controller. It resolves the active champion every poll and combines
that version's completed campaign and owned XP episodes by opponent and exact
cell type. Targeting uses a Beta-binomial estimate of
`P(win | opponent, map_ref, mode)`; it always orders one unstaked airdrop and
adds one adjacent staked invasion only when the posterior predictive probability
of winning both paired captain seatings is strictly above 75%. The controller
persists source counts, matchup buckets, posterior probabilities, and Wilson
intervals, and traces every statistical refresh and selected order. It runs as
the macOS LaunchAgent
`com.softmax.paintbot-stencil-campaign-controller`, with persistent state and
logs under `~/Library/Application Support/Stencil Campaign Controller/`,
atomic checkpoints, prompt-propagation retries, duplicate exclusion, login
startup, crash restart, settled-frame recovery after a missed pending window,
and exact audits for both airdrops and cell-to-cell invasions. Operations and
the statistical contract are documented under
[`infra/campaign_order_controller/`](infra/campaign_order_controller/).

The previous controller was not a vision failure. It read the authoritative
`own aim <brads>` marker, but still modeled GV36's 32-slot ring and interpreted
`aimTurnRate=5` as five slots / 40 brads. GV40 accepts every integer heading
and turns exactly five brads per held tick. The old modular solver could command
the wrong direction and oscillate forever near a static target; the corrected
controller follows signed shortest-angle error with a two-brad deadband.

A six-episode campaign-shaped hosted A/B on round-381 cell `(0,0)` validated
the correction in both captain seatings. v54 won 6/6, recorded 137 kills / 24
deaths and 436 / 565 hits/shots, and made 42,987 live heading changes that were
all exactly +/-5 brads. Immediate turn reversals dropped from 78.2% of v52 turn
ticks to 8.7% for v54; all 565 completed v54 gun actions preserved their
trigger heading through the five-tick firing delay. The requests, seating, and
exact-version replay analysis are recorded in
[`docs/reports/stencil-v54-gv40-aim-validation-2026-08-06.md`](docs/reports/stencil-v54-gv40-aim-validation-2026-08-06.md).

A round-383 tournament-like field test then ran 18 full-seat episodes against
the current top-eight territory holders: six each on the board's current
`1v1`, `2v2`, and `4ffa` refs. v54 finished **13 wins / three draws / two
losses**, +26 score, 351 kills / 214 deaths, and 1,121 / 1,539 hits/shots
(72.8%). It swept `1v1` 6-0, went 4-1-1 on `2v2`, and 3-2-1 on `4ffa`.
The sampled `2v2` result was 3-0 as blue captain versus 1-1-1 as red; the two
FFA fields containing both Daveey and relh produced a draw and a loss. All
episodes and artifacts completed successfully, and exact-source replay
expansion passed every recorded hash. Full report:
[`docs/reports/stencil-v54-top-champions-r383-2026-08-06.md`](docs/reports/stencil-v54-top-champions-r383-2026-08-06.md).

A larger round-385 test ran 60 full-seat episodes across all 19 other active
champions, proportioned to the live board: 16 `1v1`, 16 `2v2`, and 28 `4ffa`.
V54 finished **49 wins / three draws / eight losses** (81.7% wins, 86.7%
non-loss), +124, with 1,283 kills / 513 deaths and 4,057 / 5,247 hits/shots
(77.3%). The map records were 14-0-2, 15-0-1, and 20-3-5 respectively. The
earlier `2v2` red-side concern did not replicate: all paired two-team games
were 14-2 as red and 15-1 as blue. The clearest failure was losing by capture
to Max Yankov on `1v1` cell `(3,2)` in both colors despite favorable combat
exchanges. Full report:
[`docs/reports/stencil-v54-large-field-r385-2026-08-06.md`](docs/reports/stencil-v54-large-field-r385-2026-08-06.md).

The v49 representative gate ran ten full-seat games (six 2v2, two 4FFA, two
4FFA8) with Daveey present. All 48 Stencil seats committed and followed orders
(272 commits, 45 timeouts), but one 4FFA8 squad committed conflicting move and
watch directives at the same epoch and two isolated seats ended two epochs
behind with seven timeouts each. The preregistered gate was therefore refuted;
v50 cut timeouts to 24 and produced ten resyncs, but a fresh three-episode
giant-4FFA8 stress gate found four conflicts: the stored vote was locked while
quorum counting still used a freshly recomputed choice. v51 corrected safety,
but one live seat then stayed four epochs behind for 1,226 ticks after falling
through to independent post behavior. v52 reuses the respawn rejoin path on a
live timeout. That reduced the worst gap to two epochs/555 ticks, but agents
held at stale last-known teammate coordinates. v53's refreshing fallback
regressed to 36 timeouts and a four-epoch/967-tick live gap, so it was rejected.
The durable account and handoff are in
[`docs/reports/stencil-squad-consensus-retrospective-2026-08-06.md`](docs/reports/stencil-squad-consensus-retrospective-2026-08-06.md).

Submission `sub_e52dd65c-717f-4aab-b761-d6e83189ccab` placed v54 as the active
James Botts champion on 2026-08-06 under membership
`lpm_890ebd66-ad82-48c3-93e4-c0a9d8d85e52`. V52's previous membership is
`lpm_5753c1be-67c8-410f-bbce-67e857ec2c66`. The preceding 30-episode hosted
batch completed 30/30 without an episode failure:
18 `2v2`, six `4ffa`, and six `4ffa8`, each on a distinct round-313 campaign
cell with four complete entrant blocks and Daveey v25 present in every game.
The completed request IDs and results are durable in the reports; temporary
artifact bundles and viewer processes are not part of the new-session state.

V54 still has **zero real tournament episodes** in the audited history. League
round 778's entrant snapshot contained v52 and excluded v54, so those results
must not be attributed to v54; its first possible tournament appearance is a
later round. The 60-game result above is hosted evaluation evidence, not
tournament history.

**Hard evaluation rule:** only full-seat, current campaign-shaped scenarios are
performance tests. Normal two-team invasions—including map ref `1v1`—use four
policies in 7+7+1+1 captain/ally seating and paired captain swaps; `ffa4` uses
one policy per color. Partial-seat, arbitrary-map, stale-game, and local
scenarios remain debug probes. Follow
[`docs/tournament-like-experience-requests.md`](docs/tournament-like-experience-requests.md)
for every gameplay evaluation.

Next concrete steps:

1. Diagnose the paired Max Yankov capture losses on round-385 `1v1` cell
   `(3,2)`; distinguish heart-defense positioning from carrier interception.
2. Target the repeated FFA non-win fields (Max/Ron/daveey and
   relh/Alex/Jordan) on fresh current cells before proposing an FFA change.
3. Revisit the fixed-squad/proximity-chat architecture before another liveness
   iteration; do not tune the rejected v53 target refresh.
4. Define a falsifiable reconnection/rendezvous contract and its trace-level
   liveness bound before changing code.
5. Keep v54 as the control and compare survival, clustering, kills/deaths,
   captures, and wins only after the coordination gate passes.

## Facts worth carrying forward (verified 2026-08-06)

- **The Paintbot league runs the CAMPAIGN round brain, not a ladder**
  (`league_b8fa9b35-ac22-48cf-a03f-07b397aff1c7`; `GET .../campaign` →
  enabled, campaign round 385, 10x10 board, 600s rounds, outcomes=episodes,
  strategist claude-sonnet-5). Campaign rounds stamp `purpose: "ladder"` — do
  not be fooled again. Full model: the recon addendum + gameplay doc.
- **Standings = territory.** Historical round-202 snapshot: daveey owned
  80/100 cells, richard 8, and six other owners split the remaining 12. Resolve
  the current board rather than reusing those counts.
- **Every cell permanently owns a map identity**: current variant mix 26x
  `1v1` / 26x `2v2` / 48x `4ffa`; all 100 cells have `map_seed` and previews,
  while all 100 `map_size` values are null. Re-resolve the board before use.
- The board's map refs and campaign modes are separate. Current `1v1` and
  `2v2` refs are both mode `2v2`; normal invasions seat two captains plus two
  allies 7+7+1+1 and author a second seating with captains swapped. `4ffa` is
  mode `ffa4`, one policy per color. The disabled ladder's equal-block 3:1:1
  rotation is not the live sampler.
- Barrage implementation baseline **paintbot 0.7.211**
  (`cow_01cb32e5-…`, source
  `9dedac0ed6011aeca92bf2c6403b0e70c955f461`, **GameVersion 41**), used for the
  hazard investigation. **RESOLVED 2026-08-08:** the lab **build pin** is
  **paintbot 0.7.215** (`cow_4be22f60-d630-4816-9931-d872a06ac33f`, source
  `6c7a4c0e0be35bdcf738137595ccbcb4b4c79bf9`, **GameVersion 41**), matched by
  content — that commit's `coworld_manifest_paintbot.json` `config_schema` and
  `variants` are byte-identical to the manifest downloaded from the platform.
  **Canonical has since advanced to 0.7.216**
  (`cow_6fd2d525-015c-4763-a411-635b9c9de513`, upstream #259 — planted-heart
  sprite centering only), whose `config_schema` and `variants` are in turn
  byte-identical to 0.7.215's, so the pin's contract is intact and no rebuild is
  warranted. 0.7.212-215 added
  **team perks** and **cardboard barriers**, both config-gated and off in every
  deployed variant, both without a GameVersion bump; every spray-can constant is
  unchanged across the bump. GV41 added the endgame grenade barrage (every variant; 0:00 no
  longer ends a barrage game) and paint puddles (implemented but inactive — no
  deployed variant sets `mapPuddles`). Game repo = the
  coworld-ctf clone (`~/coding/coworlds/coworld-ctf`); no paintbot-specific Nim
  source exists. GV40 restored continuous 0..255 aim and a five-brad turn;
  0.7.205 changed `1v1` from two seats to 16; the campaign consequently
  classifies it as `2v2` and normally adds one allied entrant per side.
  The engine also now emits per-team handicap markers, locks spray direction
  for a burst, supports polygon/mapkit terrain, and supports `quadmirror` maps.
- Project-local `coworld` is pinned at **0.1.38**, which provides the campaign
  commands (`board`, `history`, `prompt`, `set-prompt`, and related views) and
  requires `softmax-cli 0.26.27`.

## Open threads

- `stencil:v21` (`da064362-fc5a-4902-9a04-b33b00d9005b`) is the previous
  accepted defensive baseline, with full artifact tracing and **not
  submitted**. Against the natural
  top-policy 4FFA field, the v9 aim behavior improved replay hit rate from
  20.9% to 51.5% and kills/episode from 4.63 to 11.13 versus v7. Every one of
  nine observed own-heart thefts was recovered. A six-map locked 4FFA A/B
  rejected v11's forced-forward selector (56 to 23 kills; 54.7% to 43.9% hit
  rate) and restored v9's homeward selection in v12. A fresh replicated
  18-episode field then rejected alignment strafe, exact 14 px fire gating,
  paired-post ducking, home-banded score ranking, and generated-axis sweeping;
  none improved defender outcomes. v20's defender-only heart-threat target
  term replicated in the same direction across two fresh 18-per-arm batches.
  v21 then made a visible high-confidence carrier override generic targeting
  and the eight-tick latch: two further fresh batches each improved 4 to 5
  wins; combined defender kills rose 4.78 to 6.67 per episode (p=0.024), deaths
  fell 5.06 to 4.86, hit rate rose 47.8% to 52.5%, and steals fell 51 to 45.
  Full report:
  `docs/reports/stencil-defensive-mechanics-2026-08-04.md`.
- `stencil:v22` (`74d04f89-43f0-4968-bc94-787e81f982cd`) fixed exact own-aim
  observation and was the previous accepted James Botts champion. Submission
  `sub_97082b2c-88ab-4fb2-8ae2-63ee17c4402a` placed it as membership
  `lpm_f0764d92-c162-4a1d-be5e-fb4cf0e9833b`; it qualified and became champion
  on 2026-08-05. A fresh locked-map A/B against
  v21 produced 847/1,140 hits/shots (74.3%) versus 488/916 (53.3%), 299 versus
  177 kills, and 195 versus 203 combat deaths. Full
  report: `docs/reports/stencil-aim-accuracy-2026-08-04.md`.
- **Commander prompt/controller** (campaign-specific): the private standing
  prompt is now supplemented by a nonce-marked, one-round directive from
  `tools/campaign_order_controller.py`. It resolves the current champion,
  ingests that version's completed campaign and owned XP evidence, and ranks
  non-FFA cells by exact opponent/cell posterior probability. A qualifying
  adjacent target with posterior predictive double-win probability above 75%
  adds one staked invasion to the mandatory airdrop. The old tournament-clone
  owner ordering remains only as a tie fallback. A persistent macOS LaunchAgent
  supervises it; it resumes after login/restart but cannot act while this Mac is
  asleep, shut down, or logged out.
- **Per-cell map-knowledge layer** (optional, now possible): the 100
  (variant, map_seed, nullable map_size) tuples are API-readable and the generator is
  deterministic — we could regenerate all cell maps offline, precompute
  walkability/choke data, and ship a map-recognition lookup (keyed by map
  signature) in the image. Decide after first evals whether it beats pure
  online play.
- Navigation startup profiling is complete: 100 maps / 200 seats across all
  five sizes under 16-process contention. Giant p95 is 419 ms, max 454 ms;
  standard p95 is 68 ms. Dijkstra is ~82% of giant startup. Full report:
  `docs/reports/nav-init-profile-2026-08-03.md`.
- Navigation knowledge is now directly inspectable: `self_play.py
  --visualize-nav` enables the opt-in `STENCIL_TRACE_NAVIGATION=1` payload, and
  `tools/render_nav.py` renders its walkability, cover, tactical anchors,
  per-front post scores/fire rays/duck pairs, and cached distance/next-hop
  fields from either JSONL or a hosted artifact ZIP.
  Validated locally on 0.7.182 / `3151a47`, then hosted across all competitive
  variants on 0.7.183 / `95bb768`.
- ~~Choke/rally fractions~~ DELETED in v62: the authored 45%/65% anchors are
  replaced by watershed chokepoints + `defenseGate`; the tunables now are
  `STENCIL_TOPOLOGY_MERGE_DEPTH_PX`/`_RATIO`, `STENCIL_GATE_DETOUR_PX`/
  `_SEPARATION_PX`, `STENCIL_COVER_RAYS`/`_RAY_PX` (defaults corpus-eyeballed,
  not tuned).
- Remaining v1 scope cuts to revisit if evals demand: item-spawn seeding from
  layout rules, battle plans, and third-party FFA reasoning. The latter is now
  the observed limit on an all-map draw-or-win target: own-heart defense cannot
  prevent one opponent from ending 4FFA by capturing another opponent's heart.
- Consider whether the mirrored beacon entrant should be retired now that
  stencil is champion (human call; `coworld-player-swap` if identity matters).
