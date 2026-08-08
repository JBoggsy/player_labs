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

The exhaustive expert corpus is preprocessing on mettabox1. Its unattended
handoff now converts merged JSONL to memory-mapped Hugging Face Arrow, builds a
250,000-example epoch balanced 50/50 on action transitions and across
GameVersion/expert/world, runs a 1,024-example BF16 canary, then starts a
three-epoch 2e-4 LoRA job. Full training checkpoints every 1,000 optimizer
updates and can resume at the next deterministic batch. These are conservative
initial settings and remain open to later budget and sampling experiments.
The handoff is live under a detached 60-second retry supervisor, with an
`@reboot` crontab recovery entry and the checked-in user service enabled.
Systemd lingering could not be enabled without sudo, so cron—not the user
unit—is the reboot guarantee.

## Current objective

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
  hazard investigation. Current campaign episode rows report **paintbot
  0.7.215**; re-resolve its source and GameVersion before making new mechanic
  claims. GV41 added the endgame grenade barrage (every variant; 0:00 no
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
- Choke/rally fractions (`STENCIL_CHOKE_FRACTION` 0.45 / `RALLY_FRACTION`
  0.65) are educated guesses, not tuned.
- Remaining v1 scope cuts to revisit if evals demand: item-spawn seeding from
  layout rules, battle plans, and third-party FFA reasoning. The latter is now
  the observed limit on an all-map draw-or-win target: own-heart defense cannot
  prevent one opponent from ending 4FFA by capturing another opponent's heart.
- Consider whether the mirrored beacon entrant should be retired now that
  stencil is champion (human call; `coworld-player-swap` if identity matters).
