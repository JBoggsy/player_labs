# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-02 09:28. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

## 2026-07-02 — prime rounds 391–394 survey
- **The prime field pivoted under us**: from 2 entrants to 11 (mostly notsus/aaln forks by other
  players) between sessions. Any lever verdict measured against the old field (esp. the 4-way
  vote-threshold refutations) needs re-checking before being treated as binding in the new field.
- **In the 11-entrant field, crew wins come from ejections, not tasks**: 5–8 crew hitting 8/8 tasks
  and losing is the modal loss; both of our crew wins-with-few-tasks were vote-driven. v89's tight
  vote gate casts 0 votes in most crew games → we under-participate in the only crew win condition.
  (Survey-level signal, n=32 crewborg games — needs warehouse confirmation.)
- **survey.py tweak**: episodes with human-written reasons now always make the interesting-episodes
  shortlist (cap/per-type limits only govern auto-filled rows). Unflagged-but-interesting episodes
  still can't render — mint their links manually (POST /v2/coworlds/replays/session).

## 2026-07-02 — warehouse deep-dig on rounds 391–394 (/tmp/prime_wh)
- **Kill conversion, refined**: when isolated with a crew target AND kill-ready, notsus converts
  9/9, relhalpha 7/8, crewborg 2/5. Plus we accumulate the longest unready isolation windows
  (mean 421 ticks vs relh 94) — we hang around crew while on cooldown instead of timing approach
  to readiness. First kill median tick 3402 = slowest in field (jordan 1126, notsus 2155).
- **Voting is two problems, not abstention**: participation is fine (2.9% no-vote). (1) Meeting-1
  paralysis: 12 skips vs 5 votes on the first meeting (field leaders skip ~0); (2) accuracy 47%
  overall = bottom tier (mv 75.7%, richard 77.1%, relh 68.1%). Also we get EJECTED as crew 5
  times (most in field, tied) — 20% of crew games we die to votes, not knives.
- **relhalpha's winning crew pattern**: 28 emergency-button calls (10x anyone else) + 83%
  later-meeting vote accuracy + best crew win rate (52%). Proactive meetings dominate this meta.
- **Ghosts do task but resume SLOWLY**: median 964 ticks death→first ghost completion vs 111–239
  for the aaln forks; 5/19 crew deaths yield zero ghost tasks. Mid-field completions/death (2.79).
- **Warehouse mechanics**: /tmp/expand-043 still hash-clean on crewrift_prime 0.4.31 (fork bumps
  remain sim-identical); 2/48 trace warnings. duckdb queries must run from
  crewrift_lab/tools/event-warehouse/crewrift-event-warehouse (root venv lacks duckdb).

## 2026-07-02 — suspicion-data + kill-gate session (three tracks)
- **`CREWBORG_TRACE_GROUPS=all` does NOT enable the suspicion feature trace** —
  `CREWBORG_TRACE_SUSPICION_FEATURES` is a separate env gate (events.py:144). Result: 0 of ~700
  hosted episodes from "all-telemetry" versions carry `ranking[].features`; build_dataset_runtime
  produces 0 rows on every real episode ever played. "All telemetry" should mean ALL — add the
  flag to the standing recipe (pending James OK).
- **fetch_artifacts `--no-logs` silently dropped policy-artifact ZIPS** (they were gated on
  want_logs) — cost a full 692-ep re-pull. Fixed: separate `--no-artifacts` flag + completeness
  check. When a fetch skips a category, verify what else that category gated.
- **v82 lesson "witness gate barely matters (99.7% exactly-1-crew-visible)" did NOT replicate in
  v89 data** — 100% of unconverted ready+in-range ticks had ≥2 crew in rendered view; the field
  now buddies up (11-entrant meta). Window-conditioned lessons rot when the field pivots; recheck
  before reuse (same lesson as the vote-lever refutations).
- **Kill failure is at the strike, not the approach**: ready+truth-in-range converts 19.6% vs
  field 84-91%; the witness veto (isolation radius 48px = 2.4x kill range) + meeting cooldown
  confiscation (body reports reset unused kcd 0→500, vote freeze pauses it) + committed-victim
  mismatch explain it; the v82 near-miss press-loop is FIXED since v84 (kill-press escape).
- **Ghost fix pattern**: death detection already existed (ghost HUD → self_alive flip); the
  latency was nav-shaped (wall-aware A* + hold-still-on-unreachable + anchor filters). The parked
  branch had the full fix; `git branch --no-merged` before re-implementing (2nd occurrence).

## 2026-07-02 — ghost A/B + killtrace verdicts (subagent runs)
- **Ghost straight-line nav REFUTED, and the metric was confounded**: death→first-ghost-completion
  is dominated by MEETING-LOCKED ticks (movement frozen ~1300t/meeting, meetings often start right
  after the kill). On Playing-phase ticks both arms are ~241-250 median — already inside the
  111-239 competitor band; ghosts ALREADY noclip at full speed while Playing. The league "964"
  overstated the gap ~4x. ALWAYS compute ghost latency on Playing-phase ticks. Do not merge/retry
  straight-line ghost nav (100v100, primary reversed p=0.69, conversion 45% vs 68% worse p=0.06).
- **Kill gate: H1 (witness-veto starvation) confirmed 367:2 over H3; H3 also MOOT** — the A-press
  kills the server-nearest in-range crew regardless of Hunt's committed target (replay-verified:
  committed blue, killed purple). But the 19.6% ready+in-range conversion figure did NOT replicate
  (69.7% truth-based in the pinned probe) — the earlier number was contaminated (isolation windows
  spanning vote-freezes). Dominant ready-time cost is CONTACT: 96% of kill-ready ticks have no
  visible victim (recon), median ready→kill 8t once seen. The big lever remains post-kill
  re-approach / victim finding, with URGENCY_FULL_TICKS 240→80 as the designed cheap A/B.
- **hunt_block telemetry** exists on branch worktree-agent-a17e8a614aabde1c4 (commit 1547423) —
  per-ready-tick gate outcome/committed victim/witness geometry; debug-gated, 3 tests. Merge-worthy
  for future kill work even though the A/B lever is a separate decision.
- **coworld CLI 0.1.26 → 0.1.27 required** (manifest 'promo' field rejection on run-episode);
  both subagents hit it independently. Bumped on main.

## 2026-07-02 — suspfit v4 A/B verdict (deterministic arms)
- **A/B NEUTRAL — primary had no headroom in deterministic arms**: crew vote precision 93% (13/14)
  vs 91% (21/23), p=1.0 — the v89 tight gate's deterministic fallback votes are witnessed-dominated
  and were ALREADY precise; the old model's live noise (58-66% precision) shows up in LLM-on play
  and probes, not in the deterministic path. The refit instead REDUCED vote volume (14 vs 23 in
  ~70 crew games; honest 0.9 crossings are rarer), imp-ejections/crew-ep 0.47 vs 0.56, crew win
  18% vs 24% (p=0.41). Timeouts/ops 0 both. NOT shipped on this evidence.
- **The real payoff of honest calibration is the vote-BAR lever it unlocks**: v4's OOF 0.7+lead
  band = 94% precision. The four vote-bar refutations on file were all measured under the OLD
  noisy posterior — with an honest posterior, lowering the crew vote bar to ~0.7+lead is a
  NEW experiment, not a retry. Candidate design: new weights + VOTE_PROBABILITY 0.7 + lead>=0.2
  vs v89 base, primary = imposters-ejected/crew-ep UP + precision >= 75%.
- Curiosities (not pre-registered, treat as hypotheses): cand imposter win 89% vs 67% (p=0.06);
  more crew ejected by the FIELD in cand crew-eps (38 vs 21, p=0.04) — suspicion weights also
  feed the imposter deflection view; worth a look before any ship.
**Implication:** crewborg crew is BOTH passive (over-skip) AND inaccurate. Lowering
the gate adds mis-votes (the prompt's warning, quantified). Next: validate
calibration live via `suspicion_snapshot` traces; study notsus coordination.

**OUTCOME metric (ejections reconstructed from meeting-clustered vote tallies):**
- crewborg-crew: 99 meetings → 14 imposter-ejections, **31 crewmate-ejections**, 54
  no-ejection. Only **13% of crew-side episodes eject ≥1 imposter**. crewborg's
  meetings eject **2.2x more crewmates than imposters** — voting is a NET PARITY GIFT
  to imposters.
- notsus-crew: 47 meetings → 19 imp-ej, 13 crew-ej, 15 no-ej. **37% of episodes eject
  an imposter** (~3x crewborg); net-helps crew (imp-ej > crew-ej).

**The mis-vote problem dominates the skip problem.** Lowering the gate without fixing
accuracy makes it worse. Candidate root causes to validate live: (a) witnessed-kill/vent
DETECTOR misfires latching innocent crewmates at p≈1 (the WITNESSED floor forces p≈1);
(b) fitted model mis-ranks under live perception. Candidate fix with most leverage:
**CREW has ZERO coordination** — `_decide_crewmate` uses only private `top_suspect`,
never reads others' votes/chat (bandwagon logic is imposter-only). notsus's edge may be
vote concentration.

**Coordination opportunity (does field plurality help?):** In crewborg-crew
meetings, the OTHER players' single vote-leader was an imposter in 219 cases vs a
crewmate in 284 cases → **field plurality is only 44% reliable** (imposters vote too,
crew mis-vote). crewborg joins imposter-leads 12% / crew-leads 10% — its private
suspicion does NOT discriminate good field-leads from bad. **Blind bandwagon ≈ 44%
accurate, not a clean win.** Confirms: mechanism (ranking quality) and coordination
are ONE problem. The real bottleneck is the suspicion signal's live ranking (~39-44%
imposter-precision when crewborg commits, vs notsus 61%).

**Pile-reliability (the decisive coordination test):** the meeting's TOP public
player-pile is only **44-50% imposter regardless of pile size (1→6 voters) or margin**
over runner-up. The "wisdom of the crowd" is ABSENT in crewborg's field (2/8 imposters
actively frame crew + crew ~50% accurate → aggregate ≈ coin flip). **Bandwagoning the
pile would NOT beat crewborg's own 39% model.** notsus's coordination edge does NOT
transfer: notsus-crew games have multiple coordinating notsus forming a reliable
consensus; crewborg's field has none. → The fix must target the PRIVATE suspicion
mechanism (ranking/calibration), not coordination.

**notsus crew design (from source study):** vote = deterministic `chooseSocialVote`
(LLM only chats). Edge = (1) NO self-skip path — waits then force-commits to top
suspect near deadline (→4% skip); (2) player-count-scaled gate (90@8alive →60→35→
always-vote@≤4); (3) reads vote-tally as private-sus input (votes-against ×10) AND as
gated bandwagon (join pile only if own-sus clears floor); (4) reporters strongly
cleared (-150). But (3) relies on a reliable field, which crewborg lacks.

**Reframed highest-leverage outcome:** crewborg's 54 no-ejection (skip) meetings are
PROTECTIVE given the bad model; the damage is **31 crew-ejections** (parity gifts).
Reducing crew MIS-ejections (better precision / fix witnessed-detector misfires) likely
beats reducing skips. Pending: live calibration run to find WHY private model is 39-44%
(witnessed-detector false-latch vs fitted mis-rank).

**ROOT CAUSE of the 39% live vote accuracy (fitted coefficient analysis):** To hit
p≥0.9 the fitted logit must clear ~2.4. The dominant EXCULPATORY feature is
`tasks_completed_watched` = **−15.2** (clipped 5) — but it only fires when the observer
actually WITNESSED a task completion (needs LOS at the right moment). The suspicious
features penalize NORMAL crew behavior: `task_site_dwell_gt20` +0.85, `copresence_
killrange_gt20` +0.77, `near_body_bodies` +0.52, `follow_death` +1.9, `accusations_made`
+1.03. `witnessed_kills` +10.1 → p≈1 alone.

**Offline→online collapse:** offline features are computed with FULL observation (the
replay expander sees everything) → exculpation fires reliably → ~100% precision. LIVE,
crewborg sees a fraction, so `tasks_completed_watched` exculpation is usually MISSING
while the suspicious cues still fire on partial observation → innocent crew accumulate
enough to cross 0.9. **The fitted model trained on full-observation features is
mis-applied to partial-observation live belief** — that is why the offline sim's 100%
precision does not transfer. Memory's "weight refits don't move outcomes" now has a
mechanism: a refit can't fix an observation-distribution mismatch.

**LIVE calibration (6 self-play episodes, suspicion_snapshot traces, roles recovered
by ranking-subtraction):**
- Crew would_vote: 81% skip, **80% player-vote accuracy** (16 imp / 4 crew).
- Calibration OK-ish: p≥0.9 → 82% imposter, p≥0.8 → 79%, top-ranked-by-p is imposter
  52%.
- Among p≥0.9 entries: 12 imp-confirmed, 6 imp-graded, **3 crew-CONFIRMED** (witnessed-
  detector misfire ~20%), 1 crew-graded.

**THE KEY: accuracy is opponent-distribution-dependent.** Self-play (crewborg field) =
80% vote accuracy; league (warehouse, real field) = 39%. crewborg's suspicion features +
witnessed-detector work against crewborg-like opponents but mis-fire against the real
league field (different kill/movement patterns trigger the suspicious features;
exculpation `tasks_completed_watched` rarely fires on opponents it can't watch). So a
fix CANNOT be validated in self-play — needs a LEAGUE A/B. The reliable-across-fields
signal is the WITNESSED catch; the graded fitted signal is league-noise.

**Candidate fix:** env-gated crew-vote that trusts only the witnessed near-certainty
(skip graded), eliminating the graded false-positive crew-ejections (the bulk of the
parity gifts), validated by a hosted league A/B on the ejection ledger + crew win.

**FIX BUILT + verified:** `CREWBORG_CREW_VOTE_WITNESSED_ONLY` env flag (default off,
byte-identical base) in `strategy/suspicion.py:top_suspect` — crew votes only a
directly-witnessed killer/venter, else skip. 4 unit tests, full suite 465 passing.
Verified active in the rebuilt image (local self-play, flag on): 7/7 crew player-votes
were witnessed catches, 51 skips. Committed on worktree branch worktree-direction2-voting
(commit 6fd963d). A/B fired: crewborg-wvon:v1 (flag on) vs crewborg-wvoff:v1 (flag off),
same image, crewborg crew slot0 vs Prime top-7, 2 imposters, 300 eps/arm (3 interleaved
requests each). Result pending.

**TOOLING GOTCHAS this session:** (1) experience-request num_episodes caps at 100 (fire
multiple for more). (2) run-episode overrides image CMD with the manifest's player cmd —
MUST pass `--run python --run -m --run crewrift.crewborg.coworld.policy_player`. (3) traces
default to jsonl@artifact (temp file lost locally) — pass `--secret-env
CREWBORG_TRACE_OUTPUTS=jsonl@stderr` to see them in slot logs. (4) `players-crewborg:dev`
is a SHARED docker tag clobbered by parallel worktree agents — build with a UNIQUE
`--tag` and upload from it, else you silently upload another agent's image. (5) env flags
for hosted policies are baked at UPLOAD via `--secret-env`, NOT settable per experience
request — A/B an env flag by uploading the same image twice (flag on / off).


**CORRECTION (root cause):** Earlier I wrote the gap was offline FULL-observation vs
live PARTIAL-observation. That is WRONG — `suspicion_lab/tools/features.py` features are
visibility-clipped + runtime-admissible by design. The real gap is TRAIN→SERVE: the model
scores 94% imposter-precision on held-out OFFLINE rows (README) but ~39% LIVE, because the
offline features are reconstructed from the replay (`game.sees()`) and diverge from what
crewborg's live perception+`event_log` compute at the decision tick. (Plus opponent-
distribution: self-play 80% vs league 39%, same live code → opponent effect; self-play n
is small.) The witnessed-only FIX is unaffected — it rests on the robust 39% live number,
not the mechanism.
### Crewborg's imposter kill→WIN gap is post-kill, not kill-rate; locate it by conditioning win on kill count
Evidence: sweep (`/tmp/sweep_wh`). Imposter win rate conditioned on the SAME kill count: crewborg @1 kill = 0.39, @2 = 0.63; notsus @1 = 1.00, @2 = 1.00; aaln @1 = 0.64, @2 = 0.78. Kills/game are comparable (~1.5), so the win is lost AFTER the kills. Always split imposter analysis by kill count to separate "gets kills" from "converts kills to wins".

### Crewborg often does NOT know its imposter teammate (RoleReveal capture is brittle) — two independent warehouse signals
Evidence: (1) crewborg/-base imposter CAST votes hit a teammate imposter 21–23% of the time; notsus/jordan-aaln/crewborg-mv = 0%. With `teammate_colors` populated there is NO code path to vote a teammate (suspicion `_recompute` skips teammates; bandwagon filters them), so 21–23% ⇒ `teammate_colors` empty in a meaningful fraction of games. (2) crewborg follows its own teammate 46% of follow-intervals / 77% of follow-ticks vs notsus 26%/42% — Search is designed to never follow the teammate, so the high rate ⇒ the teammate filter is frequently inert. Root cause: teammate identity is learned ONLY from the one-shot RoleReveal "IMPS" interstitial (types.py:718-720), which an initial-connect race (design §3.1) can miss entirely. Fix direction: a robust teammate-inference fallback (e.g. latch any color we WITNESS killing/venting — definitional imposter, already tracked by suspicion's witnessed set — into `teammate_colors`), and/or widen the reveal capture.

### Crewborg's imposter meeting play is far more passive than notsus
Evidence: crewborg skips 39% of imposter votes (notsus 5%); notsus casts a non-teammate vote ~95% of meetings (active crew-thinning + blending). crewborg's deterministic imposter meeting path (`modes/attend_meeting.py:_decide_imposter`) only acts on a real top_suspect or an existing heat pile, else skips, and has NO self-defense when crewborg itself is the accused. A meeting that ejects a crewmate is free parity progress.

### Parallel fan-out jobs CLOBBER each other via the shared `players-crewborg:dev` docker tag + shared `--name crewborg` uploads
Evidence: while uploading my candidate, `ps` showed THREE other agents (in sibling worktrees `direction3-emergency-meetings` and `personal_labs` root) concurrently running `build_player.sh crewborg` (→ same global tag `players-crewborg:dev`) and `coworld upload-policy ... --name crewborg`. The docker image tag is host-global (not per-worktree), so a sibling's build silently overwrites the bits your `upload-policy players-crewborg:dev` then pushes — and multiple `--name crewborg` uploads interleave version numbers you can't attribute. **Fix when fanning out:** build to a UNIQUE tag (`build_player.sh crewborg --tag players-crewborg:<slug>`) and upload under a UNIQUE policy name (`--name crewborg-<slug>`). Don't trust `players-crewborg:dev` or `crewborg:vN` to be yours in a parallel session.

### Parity-push A/B VALIDATED: imposter win +14.4pp (p<1e-9), mechanism confirmed, kills flat
Evidence: 6 pinned-champion 1v1 blocks (both imposters=subject, 6-of-each-champion crew), `crewborg-paritypush:v1` vs `crewborg-base`, 80 eps/champion, CLEAN n≈955 imposter-slots/arm (ops-failures dropped symmetric 4 vs 7). **Imposter win 43.7%→58.1% (Δ=+14.4pp, z=+6.3, p<1e-9); kills flat 1.48→1.43 (NOT a kill effect); vote skip-rate 26.3%→23.6% (mechanism firing).** 5/6 champions positive (forgeling +46, jordan-aaln +17, crewborg-mv +15, notsus +13 each significant; aaln +0; softmaxwell −5 noise). IMPORTANT METHOD NOTE: batch-1 alone (n=240) read only +5.9pp p=0.20 (underpowered) — a directional result on a confirmed mechanism is worth POWERING UP, not discarding; adding batch-2 (60/champ) to ~955/arm resolved it to p<1e-9. Also: re-pull with `--force` after arms COMPLETE — pulling mid-run grabbed stale/partial results that showed a fake 10% candidate ops-failure and inflated the delta to +20.8pp until corrected. The win effect is DILUTED across all games (the push only fires in games reaching a 3crew/2imp meeting with a known live teammate); conditional effect is larger. Durable record: `crewrift/crewborg/docs/designs/imposter-parity-meeting.md`.

### Upload the A/B candidate with trace env if you want to confirm a meeting-path change FIRED
Evidence: uploaded `crewborg-paritypush` with the plain entrypoint (no `CREWBORG_TRACE_GROUPS`/`CREWBORG_METRICS`), so the per-agent logs carried only reconnect lines — no `meeting_decision`/`parity_push` traces to confirm the new path engaged. Had to infer the mechanism indirectly from results.json `vote_players`/`vote_skip`. For a behaviour-path A/B, bake the trace env on the candidate upload so the firing is directly observable in the artifact logs.

### The sweep ran the DETERMINISTIC meeting path (LLM off)
Evidence: `meeting_llm_decision`/`meeting_llm_fallback`/`meeting_decision` counts = 0 in `/tmp/sweep_wh` (those are policy-internal emit.event traces, NOT replay events — not captured by the warehouse extractor regardless). Meeting behavior measured in the sweep = the deterministic fallback, not the LLM path.

## Fan-out consolidation — D1/D2/D3 (2026-06-30). D2/D3 code stays on `worktree-direction2-voting` / `worktree-direction3-emergency-meetings` (not merged — both inconclusive/neutral); full docs there; XP data pulled to `/tmp/fanout_xp/`.

### D1 navigation — VERIFIED NEGATIVE: movement is NOT the bottleneck (worktree deleted; finding kept)
crewborg's movement controller is sound — mid-pack-or-better on every quality metric (top travel speed, lowest oscillation rate, closes chase gaps fine), and the sim physics are identical for all players + both roles (diagonal max 995.6, friction only on release). The "can't catch up / can't flee" intuition is real as an OUTCOME but the cause is a missing **crew flee-reaction**, not speed: crewborg-crew die at ~427 speed (mid-stroll, 37% stationary) while forgeling-crew flee flat-out at 625 — crewborg has the full 995 available and isn't using it. **Don't re-investigate the movement controller.** The adjacent lever is a crew flee-to-safety mode (run for dense crew / a LoS-breaking corner when a high-suspicion tail closes) — crew strategy, overlaps the crew direction.

### D2 crew voting — the MECHANISM (training), not the gate or coordination, is the problem
- crewborg's crew vote is **net-harmful**: ejects 2.2× more crew than imposters; ~39% live accuracy (hits a crewmate ~61% when it votes a player); only 13% of its crew episodes eject an imposter (notsus 37%).
- The lever is the suspicion **mechanism**. The fitted model has a **train→serve gap**: ~94% imposter-precision on offline held-out rows but ~39% live, because it trains on the offline replay reconstruction (`game.sees()`) which diverges from crewborg's live perception/`event_log` at the decision tick. **This is why nightly weight refits never moved outcomes** — same offline reconstruction. (→ nightly cron disabled; runtime-feature training rework scoped, not built — `suspicion_lab/docs/runtime-feature-training.md`.)
- **Coordination/bandwagon does NOT transfer** to crewborg's field: the public vote pile is a 44–50% imposter coin-flip; notsus's edge comes from multiple coordinating notsus, which crewborg's field lacks. Don't lower the skip gate without a better signal under it — it only adds mis-votes.
- Fix held on-branch (default-off): `CREWBORG_CREW_VOTE_WITNESSED_ONLY` (vote only a directly-witnessed killer/venter). A/B **INCONCLUSIVE** — under-powered (`fetch_artifacts` `-n 10` default → only ~30/arm pulled; −4.1pp = noise); the 600 hosted eps exist, re-pull at `-n 100` for a verdict.
- Tooling gotchas (cost real time): `run-episode` overrides the image CMD → pass `--run … policy_player`; traces default to `jsonl@artifact` (lost) → pass `CREWBORG_TRACE_OUTPUTS=jsonl@stderr`; `players-crewborg:dev` is a SHARED docker tag clobbered by parallel worktree agents → build with a unique `--tag` + unique `--name`; env flags bake at UPLOAD → A/B a flag by uploading the same image twice (on/off); `num_episodes` caps at 100/request; the crontab spool is OS-locked from the sandbox → disable a cron by neutering its script.

### D3 emergency meetings — call bar (0.6) ≪ conviction bar (0.9); aligning it is at best a safe no-op
- Crew calls a one-shot button meeting when a tail clears `ACCUSE_THRESHOLD=0.6`, but the meeting re-derives `top_suspect` at `WEIGHTS_VOTE_PROBABILITY=0.9` (no clear-leader rule). A tail-only suspect peaks ~0.28–0.7 under the fitted model → `top_suspect`=None → **silent_skip**. The called suspect is **never threaded into the meeting vote** (`Intent.target_color` is forensics-only) — documented-but-unimplemented. Warehouse-confirmed: crew called **97** button meetings (notsus 4), **9% convicted**, **27% ejected a crewmate**, skip in 54% / silent in 80% of the meetings it called.
- A/B/C VERDICT (420 eps, 3 arms): **neither bar-alignment moves crew win rate**; **"lower" (vote at 0.6) is DANGEROUS** — 6.06 player-votes/g (base 3.02), 65% of losses are crew-on-crew self-ejections, collapses to 0/20 vs stealthy aaln-lineage imposters (they stay under 0.6 → crew vote each other out = parity gift). Empirically validates the 0.9 bar. **"raise" (call only when convictable) is a SAFE NO-OP** — neutral win, removes the wasted button calls. Lesson: when a fix is "align two thresholds," A/B/C BOTH directions — don't assume raise-to-safe beats lower-to-active.
- Both D2 and D3 bottom out on the **same root cause** (D2's train→serve suspicion gap) — until the model ranks imposters above crew live, no vote-bar change helps.

## Imposter movement / "can't find victims" deep-dive (worktree-agent, 2026-07-02)

### The warehouse's `player_visible_interval` (rendered_view) is a VIEWPORT basis, not the policy's belief vision — never equate them
Evidence: crewborg-family imposters show ready-tick "crew in rendered view" ~100% (median/game) while crewborg's own telemetry shows mode=recon (belief: no visible victim) at 96% of ready ticks. Both are true: the interval means "in camera viewport", the belief decode is narrower (shadow/decoder). Cross-check any visibility claim against `domain.decision_snapshot.visible_players`/`viewer_frame` before concluding a perception bug.

### Pooled per-tick imposter stats are dominated by a few pathological long ready-windows — analyze per ready-WINDOW, meeting-aware
Evidence: same warehouses gave crewborg 92.6% ready-crew-vis (prime pool) vs 20% (base pool) until re-cut per window: the tail (p99 window 1818t vs notsus 423t) carries ~88% of all ready ticks. `tools/imposter_movement/movement_lib.py` now standardizes the ready-window unit (ends at kill/meeting/death; a post-meeting kill does not convert the window).

### ROOT CAUSE FOUND — imposter ready-state has no search: gate routes ready+no-visible-victim to Recon forever; Recon beelines to a staleness-unbounded last-seen point and has NO arrival fallback
Evidence: `rule_based.py:154` (any crew EVER seen ⇒ recon whenever ready+blind — Search's room-checking FSM structurally unreachable while ready) + `opportunity.py:most_recent_victim` (no staleness bound) + `recon.py` (navigate_to only). Killtrace ereq_95f94487: parked 98.5% of an 8,452-tick ready window on a 9,000-tick-stale point, nearest crew 500px. Killtrace median parked share of blind ready ticks 87% vs notsus 0%. With players around it becomes glimpse-chase circuits passing ~20px (through walls) from sitting crew 3x without entering the room (base_wh ereq_67cf7e43). A textbook "idling is dangerous" instance.

### Imposter handoff/positioning is NOT the problem — stop optimizing it
Evidence: median nearest-crew at the ready moment: crewborg ≈18px, 84% of windows start <60px (best-in-field cooldown same-room 85-95%). The losses are (a) point-blank windows convert 70-77% vs field-best 88-92%, (b) >150px windows take median 519t vs field 91-218t. Also blind-search COVERAGE overlaps crew density MORE than anyone (Bhattacharyya 0.48 vs notsus 0.26) — where it goes is fine; what it does when passing (no room-check, no persistence) is not.

## 2026-07-02 — urgency-ramp A/B verdict
- **URGENCY 240→80 NEGATIVE — third refutation of the witness-gate-relaxation family** (after
  witness-drop and deadline-tentative). The textbook "mechanism moved, outcome didn't": wait_witness
  ticks/ep fell 2.3× (5.57 vs 12.59), strike urgency median 41.5 vs 68 — and kills/g went 1.25 vs
  1.36 (wrong direction), ≥2-kill 34% vs 38%, subject-ejected +7pp. H1 is real but NOT BINDING;
  contact starvation (96% victimless ready ticks) dominates. Stop tuning the witness gate; the
  ready-search build is the lever. Env knob CREWBORG_URGENCY_FULL_TICKS kept on main (inert at 240).
- hunt_block `strike` events re-fire until the server registers the kill — never count strikes as
  kills (452 strikes vs 125 kills in one arm).
