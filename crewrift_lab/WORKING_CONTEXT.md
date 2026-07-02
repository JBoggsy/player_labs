# Crewrift working context

**What this is.** The live, high-signal state of *what we're working on right now* in
the Crewrift lab — the minimal set of cross-session facts worth carrying into the next
session. Read it on startup to resume; **update it as you learn** (keep it tight —
prune anything no longer load-bearing). **Clear and reseed it when we pivot to a whole
new direction**, keeping only the new objective.

This is *not* a log or archive: finished work lives in git history / the
[version log](crewrift/crewborg/version_log.md); durable disciplines live in
[`best_practices.md`](best_practices.md); durable prefs in
[`user_preferences.md`](user_preferences.md). This file is the one-screen "where are we."

> A recorded objective below = onboarding done; resume the loop ([`AGENTS.md`](AGENTS.md)).

---

## 🎯 ACTIVE — imposter IDLE leak (investigated 2026-07-01; v77 ready to ship, v78/H2 replaced by H3)
Warehouse over `xreq_3411a283` (100 eps) found crewborg-v76 imposter spends **~26% of live play idle
while the kill is READY** (vs 1–3% for the aaln forks) — 79% of idle ticks = ready + a crewmate visible
~267px away, standing still. Cause: when no victim is in CURRENT line-of-sight the selector stays in
Search→WATCH, which idles at a vantage instead of closing. Report + tick-by-tick + replay links:
`$CLAUDE_JOB_DIR/tmp/crewborg_idle_report.html` (job-scoped; regen `gen_report.py`).
**Fixes built + A/B'd** (3 matched imposter-pinned arms, 60 eps, crewborg slot0 + v70 partner):
- **v77 = H1 (re-acquire on ready)** in `modes/search.py:_watch` — when ready + recently-seen crew,
  `navigate_to` last-known pos. **WORKS: idle&ready 68%→59%, kills 1.18→1.43 (+21%, p≈0.08), 0-kill
  games 11→5, freezes≥1k 23→14, timeout-draws 38%→28%. Win flat** (kill→win bottleneck + weak v70 partner).
  **→ SHIP v77.** A/B: base `xreq_da7a6fe0` vs v77 `xreq_75af8d5d`.
- **v78 = H1+H2 (env-gated WATCH idle-timeout, `CREWBORG_WATCH_IDLE_TIMEOUT=200`)** — **NO EFFECT**
  (bout histogram == v77). `xreq_e99d7567`.
- **H3 (discovered):** the worst freeze (9,437 ticks, Hydroponics, kill ready, crew 1% in-room) is a
  `_pick_room` "no task rooms" DEAD-END, not WATCH — so the watch-timeout can't catch it.
- **v77 SHIPPED → Prime CHAMPION** (over v70); v78 (watch-timeout) was a no-op (wrong scope).
- **SEARCH REWORK — BUILT + VALIDATED (v79 → v80).** Design = imposter-FSM doc §8
  (`$CLAUDE_JOB_DIR/tmp/crewborg_imposter_fsm.html`; gen `gen_fsm.py`). **v79** = the 5-state FSM
  (PICK_ROOM never idles / GO_TO_ROOM follows any visible crewmate incl. hallway / new SEARCH_ROOM sweep /
  WATCH multi→vantage vs single→approach≈35px / FOLLOW kept). **v80** = v79 + FOLLOW same-room→SEARCH_ROOM
  handoff + **RECON de-freeze** (selector gates recon to strictly-pre-ready; recon abandons reached-stale
  targets, falls back to seeking crew — never idles) + **scored env-tunable PICK_ROOM**
  (`CREWBORG_PICKROOM_W_*`: occupancy 3.0 strongest / unvisited 2.5 grows ~800t / recency −3.0 decays
  ~150t / distance / teammate / task-bonus / soft-commander; hard commander stays hard; new
  `agent_tracking.room_occupancy`). **Matched 4-way A/B (same fixed roster): idle&ready 0.68→0.59→0.44→
  0.10, freezes≥1k 23→14→9→1, timeouts 0.38→0.28→0.20→0.07, kills 1.18→1.43→1.27→1.91 (p<0.001), imposter
  win 0.42→0.42→0.63→0.78.** Recon de-freeze was the big lever. v80 was later SUBMITTED → champion
  but carries the role-latch regression (see the v80 section below); **v81 = this work merged to main
  (`2d46468`) + the v75 latch fix.** The `crewborg-idle-warehouse` worktree is merged and REMOVED
  (branch deleted; code lives on main). Remaining follow-up: optional PICK_ROOM weight sweep.

---

## 🤖 PARALLEL TRACK — LLM GAMEPLAY COMMANDER (Phase 1 done; both LLMs live in-pod 2026-06-26)
A background LLM steers *gameplay* by writing **priorities** into `belief.commander` that the modes read to
bias execution — never selecting a mode, never blocking a tick. Design:
[`crewrift/crewborg/docs/commander.md`](crewrift/crewborg/docs/commander.md) (design.md §10.6).
**Phase 1 (scaffold + wiring + observability) BUILT & gated-off** — `strategy/commander/`, `belief.commander`,
`CommanderStrategy` on a `CloseAwareSynchronousStrategyRunner`, `apply_inferences`; modes do NOT yet read priorities.
`domain.commander_*` traces (incl. `env_seen`) via `CREWBORG_TRACE_GROUPS=commander`. **Bedrock-in-pod fix (KEY):**
sidecar mode STRIPS `USE_BEDROCK` and injects `AWS_ENDPOINT_URL_BEDROCK_RUNTIME`, so BOTH LLM factories now gate
Bedrock on that **endpoint**, not `USE_BEDROCK` (`strategy/commander/llm.py` + `strategy/meeting/llm.py`).
**Confirmed live in-pod** (Crewrift Prime XP, v64): commander 4637 `commander_call` ok / 0 errors; **meeting LLM
REVIVED** — 290 `meeting_llm_decision`, 0 `_fallback` (was 184/184 disabled). Infra issue:
[`docs/coworld-platform.md`](docs/coworld-platform.md).
**Phase 2 DONE** (commits `c2e83e9`..`0e19585`): imposter levers — `hunt_room`/`avoid_room` in Search,
`target_player` in Search-follow/Recon/Hunt (reachability-checked), + **danger mode** (`allow_witnessed_kill`
relaxes Hunt's witness gate; `skip_evade` suppresses post-kill Evade) with `commander_danger` tracing. All
bias-don't-force via `commander_of`/`filter_or_fallback`; disabled path byte-identical; 440 tests green.
**Phase 3 DONE** — crewmate levers (`target_room`/`target_task`/`posture`) in NormalMode + a debug knob
`CREWBORG_COMMANDER_FORCE='{...}'` that seeds `belief.commander` with a fixed sanitized priority each tick
(bypasses LLM/Bedrock) for deterministic control demos. **CONTROL CAPACITY DEMONSTRATED live (both roles)**
via a forced run (v67, 3 Prime eps, `target_room=Reactor`/`hunt_room=Observatory`): imposters → Observatory
is the #1 nav destination (29%, ~13 rooms, chance ~8%); crew → Reactor elevated to #2 (13%, ~1.6× chance) —
weaker because the task-room lever only steers among a crewmate's OWN assigned tasks (bias-don't-force). So the
commander provably drives both roles; the crewmate task lever is gentle by design. **STRENGTH KNOB added** (commits `ad00f1d`..`c22b05a`): `CommanderPriorities.strength` = `soft` (default,
byte-identical bias-with-fallback) | `hard` (stronger override). `hard`: Search targets a distant `hunt_room`
regardless of nearby-N; NormalMode loiters in `target_room` even with no assigned task there (new positioning
intent); `target_player` follow window 120→240 ticks. **Measured (forced Prime, soft→hard):** imposter
`hunt_room` adherence **29%→100%**; crew `target_room` **13%→67%**. So the commander now has a real steering
dial (settable by the LLM or via `CREWBORG_COMMANDER_FORCE`). 460 tests green; soft path byte-identical.
NEXT: tune — (1) imposter A/B (commander LLM on vs off) for kill efficiency, iterate the imposter prompt to emit
useful `hunt_room`/`target_player`/`strength`; (2) Phase 4 EscortMode for crew. Both roles wired + strength dial. Branch `worktree-labs-work`
(merged to origin/main @ `2ec14f9`); uploaded v55–v64, **none submitted**.

## 📊 CYCLE-4 (2026-07-02): v89 KEPT — 'regression' was field-par shift; gate inversion queued

v89 league (36 eps): win 31%, crew 24% — looked bad vs v88's 43% BUT the field's crew-team win fell
37%→25% in the same window (imposter-draw rotation: softmaxwell 13 imp seats vs 1; notsus v159; field
first-kills ~900t faster). v89's crew = field par exactly, and = its own A/B level (p=0.78); v88's 43%
was an above-par-window outlier. LLM healthiest on record in league (9% fallback, 0 quota-429s — the
A/B arms ran quota-drained and UNDERSTATED LLM behavior). Gate cost bounded ≤1-2 wins/29 eps; sharp
inversion found: gated deadline tentatives 50% would-be precision vs early-submit passes 22% (LLM
submit_vote 86%). **QUEUED (next cycle, clean-quota A/B): allow LLM-set tentative at deadline
auto-submit; tighten early-submit corroboration.** attend_meeting.py ~L504/L630. All ops/timeout/
dead-mute checks clean; tasks 7.17/cg all-time best. Survey /tmp/survey_v89_league.html.

## 🔬 CYCLE-2 FINDINGS (2026-07-02): protect the LLM vote path; v88 in flight

Lead drivers (40-ep warehouse `/tmp/v87_league_wh`, survey `/tmp/survey_v87_league.html`): crew 46% is
funded by (1) the **LLM vote path — 68.4% precision, kill-witness→ejection locks** + 0 vote timeouts, and
(2) the **task engine** (6.39/seat, 21% completed dead) + meeting generation (0.86 imposters ejected/ep).
**Fragility: the early-submit fallback vote runs 16.7% precision** (4/24) — 21 crew mis-ejected vs 24
imposters in our crew eps — and **dead seats burn 23% of LLM calls on votes that never count** (0 dead
vote_cast in replays). **v88 in flight (worktree-v88-vote-quality):** (a) confidence-gate fallback-sourced
player votes (witnessed OR 0.9-posterior OR LLM-sourced tentative; else SKIP — auto-submit timing kept),
(b) mute meeting LLM for dead seats. Ghost fingerprint RESOLVED (see TODO): decide layer fine, parking
bounded; noclip stays parked. Meta: notsus v150 = closest crew rival (survival 58.3%, precision 54.8%);
jordan 5/5 imposter wins in batch; aaln v25 weak; daveey collapsed.
## 🧪 v88 PACKAGE BUILT + PROBED (2026-07-02, worktree-v88-vote-quality): fallback-vote gate + dead-seat LLM mute

Cycle-2 follow-up on v87 (`attend_meeting.py`): (1) **confidence gate on fallback-resolved crew
PLAYER votes** — early-submit/auto-submit/chat-implied targets need corroboration (witnessed,
`top_suspect` 0.9, or LLM-named) else SKIP; uncorroborated tentatives are also HELD from early-submit
(deadline auto-submit still fires → timeouts stay 0); imposter + deterministic LLM-off paths exempt.
(2) **dead seats fully mute the meeting-LLM path** (no calls/chats/votes; `meeting_dead_mute` event) —
v87 burned 62/200 probe calls (31%) + 44 chats on dead seats whose inputs the sim discards.
Tests 586+13 (main 579+13; the v86 chat-implied-beats-gate test deliberately reversed). Gate-1 PASS.
**Matched 16-ep probe** (crewborg-v88probe:v1 `xreq_049ffc12` vs crewborg:v87 `xreq_152a59e4`, same
pinned 7-champion field, natural roles, 0 ops both): dead-seat calls **62→0**, fallback crew-vote
precision **1/7 (14%) → 8/12 (67%)** (Fisher p=0.04), overall crew vote precision 50%→67%, vote
timeouts 0→0, live chats 96→117, wins 5/16→9/16 (crew 5/11→6/11, imp 0/5→3/5), 429/fail rate ~14%
flat (both arms shared the same quota window). NOT submitted; branch `worktree-v88-vote-quality`.
⚠️ analysis gotcha recorded in TENTATIVE_LESSONS: warehouse `died` events are INCOMPLETE — derive
deaths from `player_state.alive=false` (the `died` key missed kill victims and skewed dead-seat stats).

## ✅ CYCLE-4 (2026-07-02, worktree-v89-tight-gate): v89 tight gate BUILT + A/B POSITIVE — SHIP RECOMMENDED, awaiting go-ahead

v89 = v88 + the cycle-3 lever, built in `worktree-v89-tight-gate` (`828d8f1`): (1) fallback-vote
corroboration tightened to **witnessed OR 0.9 posterior OR the LLM's OWN submit_vote** —
`_llm_submitted_vote_targets` replaces `_llm_vote_targets` (set_tentative_vote / chat-riding
vote_target / backfill no longer count; uncorroborated = hold at early-submit, SKIP at auto-submit);
(2) **census self-death catch** (`types.py`): our own dead candidate-grid cell clears
`belief.self_alive` — closes the kill→meeting ghost-icon lag leak (ep 422637ce). 523+13 tests.
Uploaded `crewborg-v89probe:v1` (`cc664a1e`, standing LLM probe recipe). **Matched 50v50 A/B**
(`xreq_d947dcf9` v89 / `xreq_23530fff` v88, pinned 7-champ field, natural roles; warehouses
`/tmp/v89_ab_wh` `/tmp/v88_ab_wh`, 0 trace_warnings, 0 ops): gate fires 17 vs 4; crew vote precision
**71% (24/34) vs 36% (19/53), p=0.002**; crew mis-ejections fed **2 vs 7**; imposter-ejections fed
**14 vs 4** (imp-ejected/crew-ep 0.65 vs 0.49 — no loss); crew win 30% vs 21% (NS p=0.44, not worse);
imposter win unchanged; timeouts 0/0; dead-seat calls 0/0. v89 arm ate MORE Bedrock 429s (294 vs 175
failed calls) and still improved — bias against us. **All pre-registered ship criteria met → ship
recommendation stands; NOT submitted** (needs James's explicit go). Merge `worktree-v89-tight-gate`.

## 🔬 CYCLE-3 FINDINGS (2026-07-02): v88 league read — gate inert-but-fine; the leak is the LLM-named clause

v88 league tournament batch: 35 eps (`/tmp/v88_league_eps`, tournament subset symlinked at
`/tmp/v88_league_wh_input`), warehouse `/tmp/v88_league_wh` (35/35 ok, 0 trace_warning,
expand_replay-8710aa6), survey `/tmp/survey_v88_league.html` (31/31 replay links minted — survey.py
fixed: league eps carry coworld_id under `tags`). Crewborg v88: 18/35 (crew 10/23, imp 8/12, 0 ops,
0 vote timeouts, tasks 6.13/cg, kills 1.92/ig). **Q1 (gate):** `meeting_vote_gated` 0/35 (as probe);
dead-mute holds (dead LLM calls 4/260=1.5% vs v87 111/482=23%; one belief-lag leak ep 422637ce); crew
vote precision 18/32 (56%) vs v87 16/42 (38%); imp ejected 0.96/crew-ep (v87 0.86), crew mis-ejected
0.61 (v87 0.75) — BUT the probe's "fallback votes become good" did NOT replicate: LLM-submitted 15/18
(83%) vs early-submit-of-LLM-named-tentative 3/13 (23%); pooled LLM 28/37 vs fallback 7/34, p=4e-6.
All 4 attributable v88 crew mis-ejections we fed were that clause. **Candidate v89 lever (not built):**
drop `_llm_vote_targets` corroboration for early/auto-submit (witnessed OR 0.9 only; LLM counts only
via its own submit_vote). **Q2 (RelhAlpha):** its cumulative lead is the window, not a better crew
game — this batch relh 50% (crew 8/21) vs our 51% (crew 10/23); tasks 3.86/cg vs our 6.13; vote
precision 50% vs our 56%. Real structural edges: first kill ~2× faster (median ~1290 vs ~2350 ticks)
and it wins imposter games on ejections (7/9 with 1.44 k/g, incl. a 0-kill imp win 8a1630fb); heavy
button caller as crew (~1.0/game vs our 0.43) at similar precision — volume, not accuracy.

## ✅ INCIDENT CLOSED (2026-07-02): v87 (async meeting-LLM) is CHAMPION and RANK 1

v87 = v84 code + async LLM worker + cadence cap/budget + chat-implied fallback vote + early submit,
shipped with LLM + full telemetry (tracing exonerated). **League confirmation (40 games): 0 disconnects
(v86 was 38.5%), 0 vote timeouts (was 26% of crew meetings), crew player-votes 1.54/g (was 0.49),
win 55% — crew 46% (!!), imposter 75% @ 2.0 K/g. Leaderboard reset put us RANK 1.** Bedrock daily
quota still part-drained (fallbacks graceful); cadence cap halves burn going forward. Cycle-2 analysis
agent digging lead-drivers + the queued ghost-idle fingerprint. Ghost noclip parked unmerged
(worktree-ghost-tasking, A/B flat). 2-hour meta loop active (cron a3d08900).

## (superseded) 🚨 ACTIVE INCIDENT + FIX IN FLIGHT (2026-07-02 morning): synchronous meeting-LLM blocks the loop

v86 is CHAMPION (LLM on, no tracing) but bleeding: **38.5% league disconnects, 8% win** (v85 was 9.4%).
Root cause UNIFIED (chat-vote agent, 175 eps): the meeting LLM call is SYNCHRONOUS (~3s loop block each);
v84's 1200-tick timer quintupled call volume → belief clock lags ~670 ticks (26% crew meetings end
vote_timeout — votes selected but never land), server disconnect-timeouts on meeting-heavy seats, and the
Bedrock DAILY quota exhausted (800× 429) → failed vote calls → 0.9-gate skips ("chatting confidently but
not voting"). Tracing was exonerated (v86 has none, got worse). **v87 package in flight**
(worktree-v87-async-meeting-llm agent): async worker (commander pattern) + cadence cap 12→120 + per-meeting
call budget + chat-implied fallback vote + early tentative submit. Validation = LLM-on 16-ep probe vs v85
(deterministic A/B can't exercise LLM paths). Ghost-tasking A/B also in flight (crewborg-ghost:v1 vs v84,
dashboards :8791). Ship order: v87 fixes first (incident), fold ghost fix if its A/B is positive.

## 🎯 OBJECTIVE (REFRAMED 2026-06-30): fix crewborg's CREW play (voting-led)

**✅ UPDATE 2026-07-01 — the recent crew "collapse" was mostly a REGRESSION, now FIXED (crewborg:v75).**
Root cause: commit `1178f31`'s "robust teammate latch" made CREW mis-detect their own role as **IMPOSTER**
at RoleReveal (verified 15/15 A/B crew seats) and play the whole game as imposter → **0 tasks**. The crew
role-reveal also renders player icons in the 9500+ range, and the change had dropped the `IMPS`-text gate
that distinguished a crew reveal from an imposter one. **Fixed in v75:** role is now latched positively from
the RoleReveal **text** (`4e1d7c1`), `dead` split from role into a `self_alive` flag (`72a14a0`), and the
0x85 per-tick send reverted (`ab92f3c`, it was a net-harmful aggravator). **Measured (`xreq_300b95e7`, 100 ep
natural-roles vs the Prime field):** crew task completion **2.7 → 5.96** (median 7; 25/68 seats do all 8),
0-task "wanderer" seats **~45% → 4%** (the normal early-death baseline). Direct belief-role telemetry wasn't
captured (v75 was uploaded without trace groups), but task recovery is the definitive downstream proof — a crew
seat completing 6–8 tasks cannot be running imposter play. Memory: `crewborg-role-latch-regression`.
**v75 NOT submitted** — v70 (deployed champion) is PRE-regression / healthy, so the bug never reached the
league; no rollback needed. Crew **win-rate** stays meta-capped (~12%, imposter-favored division), so the
**voting lever below is the real remaining crew front** — now measurable cleanly on a non-regressed build.

**⭐ v80 SUBMITTED → PRIME CHAMPION (2026-07-01).** After the "big imposter fixes" tested well (parallel
session), James gave the go-ahead: `crewborg:v80` (`d85ebab3`) submitted to Crewrift Prime (`sub_3fc853d2`) →
placed into Competition (`lpm_a95f8e29`), **competing + champion** (auto-champion=always; supersedes v77).
Post-submit tournament-style eval **COMPLETE: `xreq_c10927d1`** — 100 eps (100 completed / 0 failed),
natural/random roles, v80 + 7 `random` champion-pool seats, all rotating; dashboard on
http://localhost:8814. Version-log entries for v77–v81 landed with the worktree merge (`2d46468`);
only a v76 entry (the idle-fix A/B baseline build) is still missing.

**🚨 v80 CARRIES THE ROLE-LATCH REGRESSION (found 2026-07-01, league survey + James's replay watch).**
The champion is throwing ~half its crew games: **49% of v80 crew games end 0-task** (66/135 league eps,
field 0-5%; task/g 2.58 vs 5.2-6.5; bimodal 0-vs-8) — the `1178f31` crew-latches-imposter fingerprint,
present in EVERY population (league + all xreqs). Cause verified: v80 was built from the idle-warehouse
worktree, forked before `4e1d7c1`. The "why ~50% not ~100%" is ANSWERED: ~100% of v80 crew mis-latched;
49% counted only the 0-TASK (surviving) half — the dead half ghost-task 8. Survey `/tmp/survey_v80_league.html`;
warehouses `/tmp/v80_league_wh` (484 eps), `/tmp/v81_fp_wh` (30 eps).

**✅ RESOLVED: v82 = merged main `2d46468` (idle fixes + latch fix) + full telemetry → CHAMPION 2026-07-01**
(`sub_cca840cf` → `lpm_2449fb14`, competing/champion, supersedes v80). Fingerprint on v81: 0-task crew 49%→~15-22%.

**🔬 CREW-VOTING ROOT-CAUSE HUNT CLOSED (2026-07-01, agent report):** v80's total vote/chat blackout
(0/440 player votes) was the SAME latch bug one hop deeper — mis-latched crew absorbed reveal icons into
`teammate_colors` → suspicion skips teammates → empty posterior → imposter meeting path finds no target →
silent skip. Fixed by `4e1d7c1`; v81 votes mechanically fine (4/27 player votes, 3/4 correct, 14 chats).
The residual 15%-vs-51% vote-rate drop is the fitted **0.9 gate** (`CREWBORG_WEIGHTS_VOTE_P`,
`suspicion.py:588-595`) over posteriors that **COOLED with the platform bump 0.4.21→0.4.28/29** (inferred
by elimination — weights/LLM/composition/code all refuted; confirm with v82's league telemetry).
**v83 candidates:** (1) vote-P sweep 0.6–0.7 via env + A/B (precision on cold posteriors must be re-measured);
(2) role-limbo escape — ALL 3 frozen v81 crew seats were **slot 4** deterministically (CREWMATE reveal text
never parses there); bounded fallback-to-crew after N ticks in `types.py`; (3) **`VOTE_TIMER_TICKS=240`
stale vs live `voteTimerTicks=1200`** (`strategy/meeting/context.py:18`) — we submit ~16% into the meeting
and stop listening; align before any meeting-coordination work.

**👑 v85 CHAMPION (2026-07-02, ~01:45Z):** v84 (= v82 + ALL fan-out fixes: H4 freeze fixes, direction-3
call-bar, kill-press deadlock escape, slot-4 role-limbo escape, VOTE_TIMER 240→1200) A/B'd POSITIVE vs v82
(natural roles, pinned field, 100/arm: overall +5.8pp, imposter 68% vs 50%, 0-task crew 0%, ss-penalties
−63%); v85 = same image + meeting LLM (per the never-submit-without-LLM rule) verified firing, then
submitted → qualified (new `skill_gate` stage) → CHAMPION, supersedes v82. NB Andre pushed notsus v140/v142
tonight — the field is moving. NEXT: harvest v85's first league rounds promptly (ephemeral artifacts!) to
(1) check the LLM fires in dispatch pods (the historical sidecar gap), (2) confirm the fixes in natural
league play; then the llm_call_failed tuning (TODO top item).

**▶ EXPERIMENT FAN-OUT COMPLETE (2026-07-01 eve) — all 4 hypotheses REFUTED AS POSED, 3 real fixes surfaced:**
H1→ the real imposter blocker is a KILL-PRESS DEADLOCK (belief in-range 15.8px vs sim 22.1px>20 KillRange, ~4-6px perception offset; ep d1126954 pressed kill 4,622x for 9,117 ticks = 50% of ALL our ready ticks; fix specced: press-count escape in action.py:_resolve_kill + press-range margin — NOT YET BUILT). H2→ corpse-avoidance is a NON-problem (linger doesn't predict reports/ejections; don't build). H3→ self-called button meetings are our WORST evidence context (40% imposter piles, 19 crew vs 11 imp ejections) — conditional gate would HARM; vote thresholds now refuted 3 ways; MERGE worktree-direction3-emergency-meetings (call bar=conviction bar, its own A/B/C safe-neutral); direction-2 witnessed-only A/B at full n: +2.0pp p=0.64 neutral. H4→ posed mechanism wrong (0/145 penalties post-tasks) but found TWO mid-task freezes (ARRIVE_RADIUS=4 deadband wedge outside task rect, action.py; unowned no-route hold, action.py:179) — FIX BUILT on worktree-h4-posttask-posture + A/B CONFIRMED (ss-penalties 0.454→0.010 p=7e-13, voted-out-as-crew 11.3%→2.0% p=.0094, tasks/win flat; crewborg-h4:v1, xreqs 78d75331/038f4eef; frozen games had crew win 8.3% vs 29.8%). Report: crewrift_lab/docs/h4_experiment.html (worktree).

(superseded running-note:)  4 agents testing the v82 diagnosis hypotheses
(report `/tmp/v82_diagnosis.html`, warehouse `/tmp/v82_league_wh`): H1 imposter strike-gate starvation
in crowds (priority), H2 post-kill corpse-avoidance, H3 conditional vote gate for SELF-CALLED meetings,
H4 post-task crew posture. Unique tags/policy names crewborg-h{1..4}; no submissions. PRIOR WORK
REDISCOVERED: unmerged branches worktree-direction2-voting (witnessed-only lever + completed-but-underread
300/arm A/B — being re-pulled at full n by H3) and worktree-direction3-emergency-meetings (call/vote-bar
A/B/C: global vote-bar lowering REJECTED-dangerous; convictability guard) — merge decisions owed.
Also: v83 (= v82 + meeting LLM) uploaded + VERIFIED firing in xreq (102 decisions, only benign
cooldown fallbacks); NOT submitted — league sidecar presence unknown.
Also: v80 is the only policy with ops crashes in the league set (6 disconnects) — separate issue.
League form context: lineage rank 9 is historical; v80's first champion round (276) scored 16 (rank 2).
Top of field = RelhAlpha ~15.8/round; league imposter gap vs top: win 73% vs 87-89%, K/g 1.55 vs 1.8+.

**Two active win fronts: CREW (new, primary) + imposter KILL→WIN (kept).** A 170-ep Prime sweep + 4-agent
diagnosis (2026-06-30) added the crew front and refined — NOT replaced — the old "kill→WIN conversion" thread
below (direction 4): crewborg is a **competent imposter (40–70% 1v1 win) and a losing crewmate (0–30%)**; v70 ≈ crewborg-base, so weights don't move outcomes — **change the MODES**. The crew
loss is a **social-deduction / voting failure**, not survival: crew skips ~49% of votes, hits a *crewmate*
~60% of the time it does vote, ejects 0.28 imposters/ep vs notsus's 0.60; notsus dies at the same rate but
WINS by **decisive + coordinated** voting (roster-shrinking bar, bandwagon to quorum, witnessed-tell + trust
signals). Full diagnosis + figures: `/tmp/sweep_report.html`. Memories: `crewborg-crew-weakness`,
`crewborg-v70-equals-base`, `crewrift-imposter-favored-meta`.

### ▶ FOUR FIX DIRECTIONS (set 2026-06-30; about to fan out — NOT yet pursued)
1. **Navigation / maneuver efficiency — CONFIRM FIRST.** James's intuition from watching replays: can
   crewborg move fast enough to catch up to / flee from other players? It is *unconfirmed* — investigate and
   prove it's real before building. A movement/maneuver deficit would underlie BOTH crew (can't flee/regroup)
   and imposter (can't close for the kill), so it's the foundational check.
2. **Voting gating.** Sweep the suspicion vote thresholds (`CREWBORG_WEIGHTS_VOTE_P`, `VOTE_PROBABILITY`,
   `VOTE_LEAD_*`) for the best value; **validate the suspicion mechanism** itself (the fitted crew model is
   miscalibrated live — ~100% precision in held-out sim vs ~40% in real games, a train/serve skew); and
   improve crew voting **coordination** (bandwagon onto the public vote pile; `strategy/meeting/chat_read.py`
   exists but is wired only to the imposter bandwagon path).
3. **Emergency-meeting effectiveness.** When crew calls a meeting after being followed, be **convincing +
   effective** enough to actually convict the chasing imposter — else we waste the meeting (and the team's
   task time) without removing the imp. Today crewborg is **accuse-happy** (6× notsus's button calls, 0.6 tail
   bar `suspicion.py:134`) but **vote-shy** (skips at the 0.9 bar) — it calls meetings it then squanders.
4. **Imposter KILL→WIN conversion (KEPT — also fanning out).** Kills are competitive (1.48 k/g ≈ Aaron's
   1.47, ≥2-kill 50% ≈ his 47%) but our **imposter win lags — 67% vs Aaron 91% / notsus 79%**: we get the kills
   then lose the game (ejected / fail to reach parity / lose the meeting). This session's witness-drop A/B
   confirmed the ejection backlash (dropping the no-witness gate → +13pp ejections, −6pp win, no kill gain).
   Fan out on what converts kills→WINS: imposter **meeting survival** (deflection/defense when accused), pacing
   kills to **reach parity**, and not getting **voted out for witnessed kills**. Detail + tournament table below.

---

### (direction 4 — DETAIL, STILL ACTIVE) imposter KILL→WIN CONVERSION, not kill count

**🏆 TOURNAMENT REALITY CHECK (the headline for the next session).** Ran a proper 100-ep champion
tournament (`xreq_b1f12adf`: 8 `random` Prime champions per episode — the live API redraws per episode —
full round-robin; 78 clean, 22 dropped to platform connect-timeouts). **crewborg v70 came LAST of the 3
Prime champions.** Per-seat-game:

| champion | win% | imposter k/g | ≥2-kill | **imposter win%** | crew win% | tasks |
|---|---|---|---|---|---|---|
| Aaron (crewborg-aaln:v17) | **30%** | 1.47 | 47% | **91%** | 8% | 5.5 |
| notsus v5 | 26% | 1.60 | 65% | 79% | 5% | 5.5 |
| **crewborg v70 (us)** | **19%** | 1.48 | 50% | **67%** | 6% | 5.8 |

**THE NEW LEVER — kill→WIN conversion, not more kills.** Our kills are competitive (1.48 ≈ Aaron's 1.47,
≥2-kill 50% ≈ his 47%), but our imposter **win rate is 67% vs Aaron's 91% / notsus's 79%** — we get the
kills then LOSE the game more. Aaron wins 91% on the SAME kill count. So this whole session's optimization
of *kills* (witness-drop = real +19pp ≥2-kill vs our OLD self, v63 vs v54) closed the kill gap but NOT the
win gap. The actual frontier is **surviving the meeting / reaching parity / not getting voted out for
witnessed kills** — likely the witness-drop's ejection backlash against competent crew (Aaron/notsus vote
well). NB v70 ran with the **meeting LLM ACTIVE** here (xreq=k8s pods) and was still last → the LLM isn't
buying wins in this field. notsus (the "minimal baseline") out-kills us (1.60).

**OPEN THREAD for next session:** pull the replays where crewborg out-kills but LOSES — is it (a) ejection
(witnessed-kill backlash → voted out), (b) failing to reach parity (kills too slow/late), or (c)
meeting/survival? That diagnosis sets the next fix. Re-run the tournament for more power (22% ops-failures
gutted the sample); field is only 3 champions (broaden via `included_players` if wanted). Also still OPEN:
does the meeting LLM fire in LEAGUE (dispatch) rounds (sidecar gap) — v66 fell back; verify on v70's league
rounds.

### ✅ ANSWERED + FIXED (2026-06-30, `worktree-imposter-kill-to-win` — since merged to main, branch deleted): the gap is the MEETING
Warehouse decomposition of the 170-ep sweep (`/tmp/sweep_wh`): conditioning win on the SAME kill count,
crewborg @1 kill wins 0.39 vs notsus 1.00, @2 wins 0.63 vs 1.00 — the win leaks AFTER the kills. Of 39
crewborg imposter LOSSES: **64% = an imposter voted out** (a), the rest **stall at 3-crew/2-imp — one removal
from parity — and never close it** (b). notsus closes via the MEETING (1.10 crew-eject/win vs our ~0.4) and is
NEVER ejected. Code causes: deterministic imposter meeting path **skips** (39% vs notsus 5%) and crewborg
often **doesn't know its teammate** (votes it 21-23%, follows it 46% vs notsus 0%/26%) — RoleReveal capture is
a brittle one-shot.
**FIX (`crewborg-paritypush:v1`, commit `1178f31`):** (1) `parity_closing_vote_target` — one removal from
parity AND known live teammate ⇒ manufacture a coordinated fabricated-accusation+vote on a non-teammate
crewmate instead of skipping (self-gated `alive_imposter_count>=2`; only gap==1). (2) Widened RoleReveal
teammate latch (types.py). 470 tests pass.
**A/B (6 pinned-champion 1v1 blocks, both imposters=subject vs `crewborg-base`, 80 eps/champ, clean n≈955/arm):
imposter win 43.7% → 58.1%, Δ=+14.4pp, p<1e-9; kills flat (1.48→1.43); skip-rate 26.3%→23.6% (mechanism).**
5/6 champions positive (forgeling +46, jordan-aaln +17, crewborg-mv +15, notsus +13, aaln +0, softmaxwell −5
noise). NOT submitted. Next: confirm via ejection-rate decomposition (needs replays + warehouse); upload a
trace-enabled build to log `meeting_decision path=parity_push`; broaden to natural-roles to de-mask.

---
### (prior framing kept for reference) crewborg's IMPOSTER KILL EFFICIENCY
**⭐⭐ `crewborg:v70` is the Crewrift PRIME CHAMPION (2026-06-26)** — the **meeting-LLM-ON** ship
(`lpm_60b71147`, champion=True; supersedes v69). v70 = v69's confirmed imposter combo (witness-drop)
+ meeting LLM turned on (commander OFF), on the merged commander codebase. Meeting LLM verified firing
pre-submit (probe `xreq_bc2878d1`: 22 `meeting_llm_decision`, 0 fallback). **⚠️ OPEN: does the meeting
LLM fire in LEAGUE (dispatch) rounds, or only xreq (k8s)?** — v66 fell back in league; verify once v70's
league rounds run. (v71 = nightly refit, currently `qualifying`.) Prior champion lineage below:
**`crewborg:v69`** was the Crewrift PRIME CHAMPION — the **deterministic** ship:
the confirmed witness-drop-after-1st-kill imposter combo (v63 vs v54 natural roles: +19pp ≥2-kill /
+14pp win / +0.32 kills, p=0.038) + inert 72t Evade re-approach (EVADE_TICKS=72), **LLM OFF** (the
meeting LLM only fires in k8s/xreq pods, never league/dispatch rounds — sidecar not wired there — so an
LLM-on build just adds weight + silent fallback in league). Submission saga: v66 (LLM-on) and the first
v69 tries REJECTED with "league has no submission division" (Prime was missing its Qualifiers staging
division / stale `qualifiers_division_name` config); after a **backend fix**, v69 re-submit placed +
auto-championed. Local↔image SDK parity now done (pyproject installs `players[bedrock]` from the
coworld-tools tarball). Earlier (now-historical) note on the v66 rejection follows:
**⚠️ `crewborg:v66` submitted to Crewrift PRIME 2026-06-26 but REJECTED — `notes="league has no submission
division"` (PLATFORM/league-config issue, NOT our play; same as v49).** Prime was migrated 2026-06-24 to an
among-them-commissioner + "Qualifiers" division flow; direct `coworld submit --league <prime>` now has no
submission division. v42 placed pre-migration; the nightly places in the REGULAR Crewrift league
(`league_605ff338`), not Prime. **v66's placement games were FINE** (mean +8, imposter 1.33 kills/g). ALSO:
in league-round pods the **meeting LLM FELL BACK** (0 decisions vs 17 in the xreq probe) — the Bedrock
sidecar is wired for experience-requests but NOT league rounds, so the LLM-on build plays DETERMINISTICALLY
in league. **The shippable, confirmed gain is the deterministic witness-drop** (v63 vs v54 natural roles:
+19pp ≥2-kill / +14pp win / +0.32 kills, p=0.038). NEXT: resolve Prime submission routing (owner/qualifiers
flow) and/or verify the sidecar in league pods before relying on the LLM. v66 = confirmed imposter combo +
meeting LLM (commander OFF) on the merged codebase. v59/v60/v62/v64 = other worktree's LLM-commander thread;
v61 = v54+debug; v53/v58/v65 = inconclusive/superseded arms.

**✅ CONFIRMED BASELINE — v54, 300 eps, NATURAL ROLES, vs Aaron(v17)+Andre(v28), Prime 0.4.9, meeting-aware
(`/tmp/v54base_wh`; 2026-06-26).** This is the authoritative current diagnosis (the v50 numbers were a
different config; the pinned-2-imp A/Bs MASKED the gap — see lessons).

| imposter | n | win% | kills/g | **≥2-kill** | 0-kill | post-kill in-view@ready | post-kill nearest-crew |
|---|---|---|---|---|---|---|---|
| **crewborg** | 60 | 80% | **1.52** | **52%** | 8% | **47%** | **95px** |
| Aaron | 246 | 86% | 1.97 | 82% | 2% | 76% | 14px |
| Andre | 164 | 92% | 1.97 | 82% | 2% | 81% | 18px |

Crew: crewborg win 3% / tasks **6.0/8 (best tasker)**; Aaron 3%/5.7, Andre 6%/4.5 — crew win ~3-6% for
all (imposter-dominated field, not discriminating).

**Root cause = POST-KILL subsequent-kill CONVERSION (the ~30pp ≥2-kill gap, CONFIRMED real in natural play):**
- crewborg ≥2-kill **52% vs Aaron/Andre 82%**; our **first** kill positioning is fine (first-cd in-view
  73% / 22px) — the fall-off is specifically **post-kill** (in-view 47% / 95px vs their 76-81% / 14-18px).
  Aaron/Andre stay glued (~14-18px) and snowball; we drift to ~95px median.
- Lever (unchanged) = **after a kill, re-establish contact with a killable ISOLATED victim / the cluster
  the victim peeled from, SUSTAINED across the cooldown** — the ~428t of random Search is the bigger
  culprit than Evade's 72t. **NOT solved.**
- ⚠️ v46 (Search → crew-densest room) regressed; v53 (Evade → densest crowd) neutral — **crowd-seeking is
  a dead end** (we kill ISOLATED victims; crowds = witnesses). Target the single lone victim, not density.

**Both prior fixes are INCONCLUSIVE (wrong eval config), NOT neutral** — they were A/B'd pinned-2-imp where
the gap was masked (≥2-kill 69% there vs 52% natural). **Re-test any post-kill fix in NATURAL roles.**

**ATTEMPT 1 (2026-06-26) — Evade → beeline to most-populated area: NEUTRAL.** Built `v53` (Evade
beelines to densest crew area off the occupancy grid) vs `v54` (old flee-Evade); 2× 100-ep
imposter-pinned A/B (P1 fixed-Andre co-imp; RR round-robin co-imp). Fully-clean episodes: kills
1.73→1.74 (P1), 1.71→1.69 (RR); no-kill & ≥2-kill identical. **Dead neutral, safe (0 disconnect
crashes; failures all platform connect_timeouts — recompute on FULLY-clean eps, see lessons).** Why:
we kill ISOLATED victims (~120-170px to next crew even at the kill), so beelining to the densest
CROWD heads into witnesses where Hunt's gate blocks the kill — the **v46 crowd-seeking dead-end,
re-confirmed**. Also Evade is only 72t of the 500t cooldown; Search's random-room wander over the
other ~428t undoes it.

**Next step (refined lever):** the post-kill re-approach must target the **single nearest ISOLATED
victim / the cluster the victim peeled from** (NOT the densest crowd), SUSTAINED across the whole
cooldown — the ~428t of random Search is the bigger culprit than Evade's 72t. Forks: (A) dedicated
re-approach state spanning Evade→Search that shadows the nearest reachable lone crew; (C) strengthen
Recon (longer post-kill window + head to a live/predicted single victim, not a stale last-seen).
Optional confirm: post-kill distance-curve on v53 vs v54 replays (needs a 0.4.9 warehouse — expand-043
covers only 0.4.3-0.4.7). Secondary direction the human raised: **crew-side — punish aggressive
imposters** (detect relentless proximity/kills to cut Aaron/Andre's imposter win, lift our crew win).

## Tools / data ready to use
- **STREAMING eval pipeline is now the default (built + live-validated 2026-07-01):**
  right after `create` returns an `xreq_…`, run `crewrift-event-warehouse` skill's
  `stream_eval.py --xreq … --out <wh> --expand-replay <bin>` in the background — it overlaps
  fetch (`fetch_artifacts.py --watch`, per-episode as each turns terminal) with INCREMENTAL
  warehouse builds (episodes `ok` in the manifest are never re-expanded; `episodes_cached` in
  the manifest counts hits). Validated on `xreq_307f10d6-2a6b-4c23-9be8-567f9a724417` (8 self-play
  eps): first build fired at 4/8 fetched (overlap confirmed), resume-after-completion cached 2+,
  final 8/8 ok. Design: `docs/designs/2026-07-01-streaming-xreq-eval-pipeline-design.md`.
  ⚠️ validation also showed `/tmp/expand-043` is going STALE vs prime 0.4.29 — 6/8 fresh episodes
  trace_warned (partial rows), though it exits 0 on some. Rebuild the expander from the arena's
  current commit before the next warehouse-dependent analysis (versions.env bump signal).
- **`tools/positioning_viz/`** — kill-ready spatial viewer (meeting-aware; see its README).
  Needs a **per-tick** warehouse (`--snapshot-every 1`); one exists at `/tmp/v50_pertick`
  (run #1, 100 eps). `/tmp/v50_warehouse` + `/tmp/v50b_warehouse` are the every-10 combined
  ~127-clean set used for the stats above.
- Behavioural analysis is now the **`crewrift-event-warehouse`** skill (cross-episode SQL over
  expanded replays) + **`tools/behavior_compare.py`** (per-game policy comparison). The old loose
  `crewrift_lab/` scripts (kill_latency, visibility_at_ready, aaron_compare, prime_summary,
  suss_rate) were retired/folded into those — all **meeting-aware** (count Playing samples, never
  raw tick deltas; see best_practices "meetings are not idle time").

## Load-bearing infra facts
- **Player SDK moved to `Metta-AI/coworld-tools`** (the `players` repo is **archived**).
  The build installs it from the coworld-tools **tarball** subdirectory
  (`Dockerfile` + `versions.env`; `main` resolved via `git ls-remote`). **`uv` can't lock
  coworld-tools** (broken `players/users/relh/co-gas` submodule → filed
  **coworld-tools issue #13**), so local `uv.lock` still points at the archived mirror — the
  hosted image is the source of truth for the SDK.
- **LLM meetings/commander on Bedrock**: upload with `--use-bedrock` + `CREWBORG_LLM_MEETINGS=1`
  / `CREWBORG_LLM_COMMANDER=1`. The pod runs a **loopback Bedrock sidecar**; the SDK routes to it via
  `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` (coworld-tools PR #12). **CORRECTION (2026-06-26): sidecar mode
  STRIPS `USE_BEDROCK` from the player container** (treats it like a credential) and injects only the
  endpoint — so the SDK's `bedrock_enabled()` (USE_BEDROCK gate) reported "no LLM backend" in-pod and
  BOTH LLMs were silently disabled (meetings were 184/184 `_fallback`). **Fix:** crewborg now gates Bedrock
  on `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` presence (`strategy/{commander,meeting}/llm.py`). Verify via
  `policy_artifact_<slot>.zip → telemetry.jsonl` (`domain.meeting_llm_decision` + `domain.commander_call`
  `outcome:ok`, not `_fallback` / `env_seen` all-false). Platform fix owed (keep injecting `USE_BEDROCK=true`)
  — see `docs/coworld-platform.md`.
- **Expander**: `/tmp/expand-043` (master sim `26ee08c`) handles **crewrift_prime
  0.4.3–0.4.7** (the fork's version bumps didn't change the sim). Use
  `CREWRIFT_EXPAND_REPLAY=/tmp/expand-043` for the warehouse.
- **Prime field** (Competition `div_acbde92a-…`): just **Aaron `crewborg-aaln:v17`** +
  **Andre `truecrew:v28`**. Prime league `league_a12f5172-0907-4d04-8bcb-ca02f5360e3a`.
  Evals: fully round-robin, natural roles (no pinning), vs those two. Heavy
  `connect_timeout` ops-failures are platform load, not us — re-run / probe small first.
