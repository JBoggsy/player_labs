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
unit—is the reboot guarantee. The exhaustive-corpus baseline verdict
(2026-08-14: 59.17% teacher-forced on a now-retired diagnostic index; a
sealed confirmation index and a matched-compute diversity arm were defined)
is in
[`docs/reports/rl-exhaustive-baseline-2026-08-14.md`](docs/reports/rl-exhaustive-baseline-2026-08-14.md);
the mettabox1 run state has not been re-checked since.

## Current objective

**THE STRATEGY-REWORK EPOCH IS OPENING (2026-08-29).** The session focus:
separate the "body" and the "mind" of Stencil — make the action, intent, and
strategy loops separable with clear, well-defined interfaces. Current
verified boundary: `policy.decide` → `perceive` → `updateBeliefCore` →
`strategy.decideObjective` (the ladder, emitting one typed `Intent`) →
`action.resolveAction` (planner-routed movement + combat overlay). The typed
Intent (types.nim) is the mind→body contract since v66. Known boundary leaks
to address (verified in code 2026-08-29): ~~`threatAxis`/`sweepTarget` (idle
aim sweep) read strategy-level state directly inside action.nim~~ **CLOSED
2026-08-29 as v69** — idle-aim center is now the typed
`Intent.idleAimCenterBrads` stamped post-ladder in strategy (dead-tick stamp
in policy.nim; body keeps only the sweep oscillator); bit-identical policy
output proven on a 278k-decision recorded-wire corpus
(design: `docs/designs/strategy-idle-aim-intent-2026-08-29.md`, recon:
`docs/recon/threat-axis-idle-aim-2026-08-29.md`). Hosted parity A/B vs v68
COMPLETE (2026-08-29): 56/56 episodes, 0 ops failures, W-L 6-22 vs 4-24
(+2 net, noise), kills 2.08 vs 2.12/seat (n=176/arm) — PARITY, no red
flag; duck%/peek% hosted instruments underpowered (flaky artifact upload)
with gaps disclosed in VERSION_LOG v69. v69 (6b759380) is uploaded, inert,
NOT submitted; v68 remains the live champion — promotion is James's call. **Strategy-rework worklist** (remaining
items; leak numbers from the Body-and-Mind report §8):

1. **REMOVE roles and role assignment — James-directed 2026-08-29** (widened
   from the original "move roles into strategy" ruling, same date). The
   strategy rework deletes the static Role concept outright: the
   Attacker/Defender enum, `roleForSeat`/`defenderCount`
   (`STENCIL_DEFENDERS`), the seat-arithmetic split, and the whole
   policy.nim:55-98 assignment block (deleted, not relocated). Known
   role-keyed behavior that must be re-expressed or consciously dropped —
   the full consumer census (grep-verified at v69): the Attacker-only
   escort-carrier rung and Defender-only post/hold rung (strategy.nim), the
   Defender-only `defensiveThreatTerm` + stolen-heart carrier-override gate
   (fight.nim:150-160,239,250), role-anchored item-fetch detours, the
   role-keyed idle-aim center (strategy.nim, v69), and the `earlyDefensePoint`
   lazy latch (same frozen pattern; not cleared by re-roles today). How
   attack/defense posture is chosen dynamically instead — per-tick, per-agent,
   from belief — is THE central design question of the rework, not decided
   here. Note the seat-arithmetic side effects that disappear with roles:
   the silent-coordination property (everyone derives the same split without
   comms) and the 2v2 even-split artifact (all defenders captain-side, allies
   field zero) — the replacement must answer how team-wide division of labor
   stays coherent, especially with a foreign ally.
2. **Staleness becomes explicit strategy policy** (with item 1 — applies to
   whatever replaces role posture: post/posture choices still need defined
   re-decision triggers). Today
   staleness ≜ exactly two triggers — WorldMap build/signature change
   (policy.nim:43-47) and grow-only muster-estimate change (policy.nim:51-54,
   belief_update.nim:413-422) — and nothing else invalidates a post.
   Code-verified missing invalidations: enemy-belief drift (post scored once,
   never re-scored); opponent retirement (`mostDirectOpponent` is pure map
   geometry, belief-blind — `heartsRetired` never touches role state, so
   posts/idle aim can stay oriented on an eliminated team); the color-lock
   correction (no re-trigger; frame-ordering window if the map completes
   before the first self sighting); `earlyDefensePoint` surviving re-roles.
   Model to follow: squad-order posts, which re-select on every directive.
   Design the re-selection triggers (opponent-retired, threat-shift/TTL,
   early-defense transition) as tunable `STENCIL_*` policy.
3. Chat shout choice is a side channel in policy.decide (leak #3).
4. Strategy writes telemetry/latch state onto Belief mid-decision (leak #4).
5. WorldMap pedestal mutation per percept in `updateHearts` (leak #5).

A stencil-centered documentation audit (this date)
refreshed README/AGENTS/docs-index/design docs to the post-rework reality.

**Live state re-verified 2026-08-29:** stencil:v68 is the active champion in
the Paintbot league (`lpm_eeac47d3`; v58/v54/v52/v47 benched) **and also
competes in a NEW second league, Elite Paintbot** (`league_15cf0b94`, created
2026-08-19, membership `lpm_243bbc99`) — previously unrecorded; how it was
entered and what it plays is unexamined (TODO). Canonical paintbot has
advanced to **0.7.242** (`coworld deploy-audit`; build pin still
0.7.215/`6c7a4c0e` — game-pin review parked in TODO). Project-local coworld
CLI is now **0.1.39**, and `coworld list` no longer shows games you don't own
— use `coworld deploy-audit` for the canonical-version staleness check.
**The campaign controller is BROKEN**: its LaunchAgent still points at the
pre-rename repo path (`personal_labs_paintbot/`), and it has logged
`FileNotFoundError` every poll since ~2026-08-26 — no orders are being
placed; reinstall from the new path (TODO).

**v68 ACCEPTED (2026-08-14) — THE NAVIGATION REWORK IS COMPLETE.** Batch
58/58, 0 ops: +4 net (12W-16L vs v67 8W-20L; h2h identical, duo 3W-5L
second-best ever vs swgy), v60 signature ABSENT (duck −1.4pp, peek −1.5pp
— corridor softening transit micro as designed), stuck-handling now
visible (32 replans/8 events per 28 seats), contract counters spotless.
All five sketch layers shipped: v61 clearance, v62 topology, v63/64/67
posts→atlas, v65 planner, v66 contract, v68 follower. Next epoch: the
strategy rework (James's future update). **v68 IS THE LIVE CHAMPION** (submitted 2026-08-14 on James's go-ahead:
sub_ecedf891, lpm_eeac47d3 — placed, qualified, competing, champion,
substatus active; v58 benched). The rework commits have since been pushed
and merged to origin/main (2026-08-29 check: only the session's
lesson-rotation commit ahead).** v68 (`ffa8e5d2-10f1-4e6c-93f9-4b005a83359a`, tag
`purpose=bounded-follower`), Codex-implemented: corridor-bounded micro
(20 px default — plan review caught that 12 px would have killed all
on-path separation; nudgeClear stays the acceptance law; Hold ducks
exempt), the 90-degree jitter DELETED, watchdog = one penalty replan +
loud follow_stuck_bug, uniform progress accounting with the stationary-
behavior contract, arriveRadius transcribed (5 real values) and consumed.
Local gates: duck 8.1% forced-active (band 7-13); micro mix shifted as
designed (transit peeks halved, ducks up); h2h duck ~0% is v55-era
early_defense suppression, not a regression. Peek% joins duck% as batch
watch metrics. All rework layers (1-5) are now SHIPPED; the batch verdict
completes the rework.



**Navigation-rework history (v59-v67, compressed 2026-08-29 at epoch
close):** the full per-version story — uploads, matched-batch verdicts,
request IDs, membership IDs — is durable in
[`paintbot/stencil_nim/VERSION_LOG.md`](paintbot/stencil_nim/VERSION_LOG.md)
and the `docs/designs/nav-*` layer docs. One-line arc: v59 spray avoidance →
v60/v61 clearance field + `nudgeClear` (Layer 1) → v62 watershed
topology/PoIs (Layer 2) → v63/v64 post re-sourcing + wide pool (the
`fieldsFor` `lent` fix) → v65 weighted-A* planner (Layer 3) → v66 typed
Intent contract (Layer 4) → v67 post atlas → v68 bounded follower (Layer 5,
champion). Platform constraints found en route: experience credits (2500/wk,
cap 5000, refill Sun) and per-upload auto-evals (10 episodes, sharing the
pool). The campaign board ROLLED BACK to the 10x10 square board late
2026-08-11 after the round-967 hex re-verification — re-resolve the board
live every study; `docs/tournament-like-experience-requests.md` carries the
current seating contract (true `1v1` mode; even captain/ally `2v2` split; the
old 7+7+1+1 is gone — NOTE for James: `user_preferences.md` still cites
7+7+1+1, his text, left untouched). The topology/atlas viewer is era-gated:
pre-v67 traces need `--allow-drift`.

**Pre-rework champion history (v47-v58, compressed):** v54 (GV40 continuous
aim) became champion 2026-08-06 after sweeping its validations and the
60-episode round-385 field test (49-3-8); v58 (GV41 barrage-center
evacuation) reigned 2026-08-07 → 08-14; v55's covered spawn-box opening was
rejected as a general replacement for v54; the v49-v53 leaderless-squad
liveness saga is synthesized in
[`docs/reports/stencil-squad-consensus-retrospective-2026-08-06.md`](docs/reports/stencil-squad-consensus-retrospective-2026-08-06.md).
All submission/membership IDs, request manifests, and batch verdicts are in
`VERSION_LOG.md` and the dated reports.

**Campaign commander/controller:** a deterministic one-round controller
([`tools/campaign_order_controller.py`](tools/campaign_order_controller.py),
runbook in
[`infra/campaign_order_controller/`](infra/campaign_order_controller/))
resolves the active champion every poll, buckets that version's completed
campaign/XP episodes by opponent and exact cell, always orders one unstaked
airdrop, and adds one adjacent staked invasion only above a 75% posterior
predictive double-win probability — running as the macOS LaunchAgent
`com.softmax.paintbot-stencil-campaign-controller`. **Currently BROKEN by
the repo rename (see the 2026-08-29 block above).**

**Hard evaluation rule:** only full-seat, current campaign-shaped scenarios
are performance tests. Reproduce the live cell's campaign **mode** (true
`1v1` head-to-head; `2v2` duo with the even captain/ally split and paired
captain swaps; `ffa4` one policy per color) — mode is independent of the
variant name. Partial-seat, arbitrary-map, stale-game, and local scenarios
remain debug probes. Follow
[`docs/tournament-like-experience-requests.md`](docs/tournament-like-experience-requests.md)
for every gameplay evaluation, and mind the experience-credit budget
(2500/wk, cap 5000, refill Sunday).

Next concrete steps (reseeded 2026-08-29):

1. Repair the campaign controller LaunchAgent (broken by the repo rename —
   see the current-objective block; James's call on when).
2. Investigate the Elite Paintbot league: format, board, how stencil:v68 was
   entered, whether it needs separate steering.
3. Run the game-pin review (0.7.215 build pin vs 0.7.242 canonical; TODO).
4. The strategy rework itself — James has directed item 1 of the worklist
   (REMOVE roles and role assignment entirely) with item 2 (explicit
   staleness/re-decision policy for whatever replaces role posture) riding
   along; threat-axis removal shipped as v69. Other inputs ready: the
   body/mind boundary map above, the v68 verdict's peek%/duck% watch metrics,
   and the corridor `micro_corridor_rejects` tuning corpus.

## Facts worth carrying forward (verified 2026-08-06; restamped 2026-08-29 where noted)

- **The Paintbot league runs the CAMPAIGN round brain, not a ladder**
  (`league_b8fa9b35-ac22-48cf-a03f-07b397aff1c7`; `GET .../campaign` →
  enabled, campaign round 385, 10x10 board, 600s rounds, outcomes=episodes,
  strategist claude-sonnet-5). Campaign rounds stamp `purpose: "ladder"` — do
  not be fooled again. Full model: the recon addendum + gameplay doc. **A
  second league, Elite Paintbot (`league_15cf0b94`), exists since 2026-08-19
  and lists stencil:v68 competing (2026-08-29); unexamined.**
- **Standings = territory.** Historical round-202 snapshot: daveey owned
  80/100 cells, richard 8, and six other owners split the remaining 12. Resolve
  the current board rather than reusing those counts.
- **Every cell permanently owns a map identity**: current variant mix 26x
  `1v1` / 26x `2v2` / 48x `4ffa`; all 100 cells have `map_seed` and previews,
  while all 100 `map_size` values are null. Re-resolve the board before use.
- The board's map refs and campaign modes are separate — and since the
  2026-08-11 commissioner change a cell's **mode is a policy layout chosen
  independently of the variant**: true `1v1` head-to-head cells exist, `2v2`
  duo cells split each team **evenly** between captain and ally (the old
  7+7+1+1 is gone), with a second seating authored captains-swapped; `ffa4`
  is one policy per color. The disabled ladder's equal-block 3:1:1 rotation
  is not the live sampler. Current contract + seating tables:
  `docs/tournament-like-experience-requests.md` (re-verified 2026-08-11 with
  the 10x10 rollback note).
- Barrage implementation baseline **paintbot 0.7.211**
  (`cow_01cb32e5-…`, source
  `9dedac0ed6011aeca92bf2c6403b0e70c955f461`, **GameVersion 41**), used for the
  hazard investigation. **RESOLVED 2026-08-08:** the lab **build pin** is
  **paintbot 0.7.215** (`cow_4be22f60-d630-4816-9931-d872a06ac33f`, source
  `6c7a4c0e0be35bdcf738137595ccbcb4b4c79bf9`, **GameVersion 41**), matched by
  content — that commit's `coworld_manifest_paintbot.json` `config_schema` and
  `variants` are byte-identical to the manifest downloaded from the platform.
  **Canonical has since advanced far past that: 0.7.242 as of 2026-08-29**
  (`cow_ed016cb2`, via `coworld deploy-audit`; it was 0.7.216 at the
  2026-08-08 audit, whose `config_schema`/`variants` were byte-identical to
  0.7.215's, and 0.7.229 at the 2026-08-14 check). The 0.7.216-onward
  byte-compat argument has NOT been re-run against 0.7.242 — the game-pin
  review is parked in `../TODO.md`. 0.7.212-215 added
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
- Project-local `coworld` is at **0.1.39** (2026-08-29; bumped by the
  upstream uv.lock merge), which provides the campaign commands (`board`,
  `history`, `prompt`, `set-prompt`, and related views). Note: `coworld list`
  now shows only your own uploads — use `coworld deploy-audit` to resolve the
  canonical game version.

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
  asleep, shut down, or logged out. **BROKEN since ~2026-08-26 by the repo
  rename** — see the current-objective block and TODO.
- **Per-cell map-knowledge layer** (optional, now possible): the 100
  (variant, map_seed, nullable map_size) tuples are API-readable and the generator is
  deterministic — we could regenerate all cell maps offline, precompute
  walkability/choke data, and ship a map-recognition lookup (keyed by map
  signature) in the image. Decide after first evals whether it beats pure
  online play.
- Navigation startup profiling is complete but PRE-REWORK: 100 maps / 200
  seats, giant p95 419 ms, Dijkstra ~82% of giant startup
  (`docs/reports/nav-init-profile-2026-08-03.md`). Those are Python/v1-era
  numbers; post-rework giant seat init runs ~0.9-1 s with the atlas
  (VERSION_LOG v63-v67), and the sketch §10 carries the re-baseline TODO.
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
