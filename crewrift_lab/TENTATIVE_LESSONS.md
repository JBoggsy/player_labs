# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-01 15:16. This is THIS SESSION's lesson buffer. Write candidate
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
### Attribute by policy_version_id ALWAYS — our own champion gets drawn as an opponent and shares our display name
Evidence (3rd occurrence this session): v83 LLM probe — `names.index('James Boggs')` grabbed v82 champion seats (drawn by `random` pool) half the time, producing phantom "llm_disabled" fallbacks that looked like flaky sidecar pods. Correct join: episode.json participants[].position + policy_version_id. Also: `meeting_llm_fallback` reason=`chat_cooldown_pending` is benign throttling, NOT a failure — split fallback counts by reason before alarming.
### Un-merged experiment branches hide finished evidence — check `git branch --no-merged` before re-diagnosing a known area
Evidence: the crew vote-skipping question was already investigated on TWO unmerged branches (worktree-direction2-voting: witnessed-only lever + a COMPLETED 300-ep/arm A/B that was only ever read at n~30/arm; worktree-direction3-emergency-meetings: call-bar/vote-bar A/B/C with "lower vote bar globally = REJECTED dangerous"). Today's H3 hypothesis nearly re-proposed a refuted arm. The 06-30 fan-out's WORKTREE_RESULTS.md handoffs were exactly right — they just never got merged or read.
### H3 (caller-conditional vote gate) REFUTED for free by warehouse decomposition — self-called BUTTON meetings are crewborg's WORST evidence context, not its best
Evidence (/tmp/v82_league_wh, 227 clean eps, 176 crewborg-crew games): pile-leader-is-imposter by meeting type — crewborg self-called BUTTON 30/75 (40%), self-called BODY-report 25/32 (78%, p=3e-4 vs button), other-called 97/226 (43%, p=0.69 vs button — no enrichment). crewborg's OWN player-votes at the current P>=0.9 gate hit imposters only 10/23 (43%) in its own button meetings vs 18/20 (90%) in its body-report meetings. Button-meeting outcomes already net-harmful: 19 crewmate vs 11 imposter ejections, 46 no-ejection. Trigger-suspect proxy (follower of crewborg <=60 ticks pre-button): 16/42 imposter (38%, n.s. vs 2/7 base, p=0.17) — the pre-call tailer is mostly notsus-family CREW. So lowering the vote gate specifically in self-called button meetings would convert votes exactly where evidence is weakest; the conditioning has NEGATIVE value. Reconstruction validated: reproduces H3's own telemetry (combined skip 256/342=74.9%~75.4%; combined precision 55/86=64% exact).
### Direction-2 witnessed-only A/B at FULL n = neutral (was mis-read as pending at n~30)
Evidence: re-pulled all 6 xreqs at n=100 (results-only, free). wvon 79/300 (26.3%) vs wvoff 73/300 (24.3%): +2.0pp, Fisher p=0.64 — inside noise (CI ~±7pp). player-votes/g 0.31 vs 0.34 (flag barely binds — crew votes are already rare); tasks/g 6.05 vs 5.77 (unverified). Verdict: witnessed-only is SAFE but not a demonstrated win lever; don't enable by default on this evidence.
### Imposter "ready→kill long tail" is NOT the witness gate — it was one kill-press deadlock game (belief in-range vs game out-of-range)
Evidence (H1 experiment over /tmp/v82_league_wh, 227 clean eps): among crewborg imposter ready-streaks >300 ticks with crew visible, 99.7% of ticks had EXACTLY 1 crew visible (9,850 vs 28 with >=2) — the multi-crew/witness-blocked state barely exists. Code confirms it can't be the gate: selector flips to Hunt whenever ready+victim-visible (WATCH never runs then), and `unwitnessed()` self-relaxes to zero at URGENCY_FULL_TICKS=240. The real event: ep d1126954 slot 2 — Hunt emitted `kill` intent 9,117 ticks, edge-pressed A 4,622 times, game rejected every press: belief distance 15.8px (dist2=250<=400) vs replay truth 22.1px (>20px KillRange). Perception positions offset ~4-6px (self believed (493,489) vs true (497,487); victim (498,504) vs (504,508)). `_resolve_kill` never falls back to navigate because the in-range check uses the same wrong belief. That ONE game held 9,235 stationary near-miss ticks = 50.4% of ALL crewborg imposter ready ticks in the dataset — it manufactures the "median 66 / 0-kill 9.3%" tail on its own.
Status: fix direction = (a) kill-progress escape: if kill pressed ~N times (e.g. 24) with no cooldown flip, treat as out-of-range and step toward the target (idling-is-dangerous class: a kill-spam loop with no escape), and/or (b) press-range margin: require dist2 <= (20-6)^2 before pressing so the ~6px perception offset can't cross the boundary. Do NOT build the H1 ready-stall/WATCH-flip lever — wrong mechanism.
### The other >300-tick ready streaks are acquisition/close latency, not gate holds
Evidence: a2de70ce (1,519t, moving 100%, 12 rooms, only 19 crew-visible ticks) and a048572f (354t) both ENDED IN KILLS; 9fbebe4e (897t, chase, never closed <22px) ended by meeting; ced1754e (712t, 0 crew visible) ended by GameOver. Search-side find/corner problems — a different hypothesis family.

### An arrival deadband that can straddle an interaction rect edge is a permanent freeze
Evidence: H4 warehouse forensics (v82 league, 227 clean eps): 107/145 crewborg crew
standing-still penalties sat EXACTLY one pixel outside a 14x14 task-station rect —
`ARRIVE_RADIUS=4` lets the agent settle outside while `inside` (exclusive at x+w) stays
false, so the A-hold never starts and no d-pad ever fires again. Recurring at specific
croatoan stations (4, 7, 28, 34, 37) whose baked anchors sit near a rect edge. Fix =
nudge at the rect center (always > ARRIVE_RADIUS inside) when the navigate mask goes
dead within 24px of the station.

### "A stall the mode can react to" is a freeze unless some mode actually reacts
Evidence: action.py:179 returns hold-still on an empty route and the comment says the
mode can react — no crew mode ever did; 38/145 H4 penalties were exactly this park.
Same class as the recon-stall and WATCH-idle lessons: every idle path needs an owner
with a timeout escape (NormalMode now blocks the target after 100 stationary ticks).

### Verify an idle hypothesis' TIMING before designing a posture fix
Evidence: H4 was posed as "post-8th-task idling doctrine gap" — but 0/145 penalties
were post-8th-task (89 all-tasks-done seats took zero penalties; `_return_to_start`
walking works), 79/145 were ghosts, and all sat mid-assignment at a wedged station.
The cheap warehouse timing/position query redirected the fix from "post-task posture"
to "execution wedge + stall escape" before any build was spent.

### A frozen crew seat blocks the crew task-win and drags the game
Evidence: 12/173 v82 crew games had a >=2-penalty frozen crewborg seat: crew win 8.3%
vs 29.8% in clean games, mean length 12181 vs 6928 ticks — the unfinished tasks (alive
or ghost) make the task-completion win unreachable, so the game grinds until the
imposters kill out. Standing-still score (-1 each) is the SMALL part of the cost.

### H4 A/B result: stall escape + wedge nudge eliminates the crew freeze (44 penalties -> 1)
Evidence: matched crew-pinned A/B, crewborg:v82 (xreq_78d75331) vs crewborg-h4:v1
(xreq_038f4eef), 100 eps/arm, identical pinned Prime top-7 field, 2 imposters.
ss-penalties/g 0.454->0.010 (p=6.8e-13), frozen games 4->0, voted-out-as-crew
11.3%->2.0% (p=.0094, unpredicted bonus — likely the witness posture/no-freeze
reads less suspicious), tasks/g 6.62->6.43 (p=.53 noise), crew win 30.9%->25.0%
(p=.43 noise), survival 29.9%->34.0% (noise). Mechanism confirmed; win-rate lift
(expected ~1.5pp) unresolvable at this n. Report: crewrift_lab/docs/h4_experiment.html
(worktree); design + verdict pre-committed.

### Crew emergency meetings can't convict the tailer: call bar (0.6) << conviction bar (0.9)
Evidence: `AccuseMode` calls a button meeting when `active_tail_suspect` clears `ACCUSE_THRESHOLD=0.6`
(suspicion.py:134), but the meeting that opens runs `AttendMeetingMode._decide_crewmate`, which
re-derives `top_suspect(belief)` — under the vendored FITTED weights (the default) that returns a
target only at `WEIGHTS_VOTE_PROBABILITY=0.9` with NO clear-leader rule (suspicion.py:583-590). A
tail-only suspect peaks ~0.28-0.7 under the fitted model (`tail_obs_max_run` is NEGATIVE in every
bin: -0.525..-0.574; `tail_obs_samples__gt20` only +0.293), so `top_suspect` returns None →
**silent_skip**: crewborg burns its one-shot button + the whole team's task-time and says/votes
nothing. The accuse.py + design §7.1 docstrings claim "the meeting accuses + votes the tail" — but
the code never threads the called suspect into the meeting; `Intent.target_color` on `call_meeting`
is explicitly "forensics only — the meeting vote re-derives the target from suspicion" (types.py:446).
Documented-but-unimplemented = a real bug.
Status: CONFIRMED by warehouse (170-ep Prime sweep): crewborg-crew called **97 button meetings**
(notsus: 4), **9% convicted** an imposter, **27% ejected a crewmate**, crewborg itself **voted skip
in 54%** / **silent in 80%** of the meetings it called. Two opposite fixes are being A/B/C-tested.

### Two ways to close the call/convict gap — A/B/C, not a single fix
Evidence: the gap can be closed by aligning the bars EITHER direction. (A "raise") only call when the
tailer is already `top_suspect` — call rarely, convict surely. (B "lower") keep calling at 0.6 but
lower the in-meeting vote bar to 0.6 (`CREWBORG_WEIGHTS_VOTE_P=0.6`) — call readily, convict at the
lower bar. They trade off precision vs. activity: A risks under-calling (the feature goes nearly
dormant), B risks mis-ejecting crew (the fitted intercept puts a no-evidence player at P≈0.57, so 0.6
is barely above baseline). Lesson: when a fix is "align two thresholds," BOTH directions are real
candidates — don't assume raise-to-safe is better than lower-to-active; A/B/C them.
Status: 3-arm A/B/C DONE 2026-06-30 (420 clean eps, our policy=6 crew vs each of 7 Prime champions
=2 imposters, 20 eps/cell). **VERDICT — neither bar-alignment moves crew win rate; "lower" is
actively dangerous:**
- crew win: base **23.6%** (33/140), raise **25.0%** (35/140, +1.4pp p=0.78 NS), lower **20.0%**
  (28/140, −3.6pp p=0.47 NS). All three statistically indistinguishable at the arm level.
- "lower" (convict at 0.6) is a high-variance TRAP: +35pp vs notsus (50% — notsus imposters cross
  0.6 on real evidence) but COLLAPSES to **0/20** vs three aaln-lineage imposters (crewborg-aaln,
  crewborg-mv, jordan-aaln) + 10% vs aaln-richard. Mechanism (highly significant): lowered-bar crew
  cast **6.06 player-votes/g** (base 3.02, raise 2.06) and **65% of their losses are crew-on-crew
  self-ejections** (imp kills≤3 ⟹ a crewmate was voted out; base 26%, p=7e-9). Against stealthy
  (crewborg-derived) imposters that stay under 0.6, the 0.6 crew vote each OTHER out → parity gift.
  Empirically validates exactly why the fitted crew vote bar is 0.9 (precision).
- "raise" (call only when convictable) is a SAFE no-op: neutral win rate, fewer crew player-votes
  (3.02→2.06 — it stops spending the button on unconvictable tails), no downside. It implements the
  documented intent and removes the warehouse-confirmed waste (97 calls, 9% convict, 27% mis-eject)
  at zero cost — but the emergency meeting is NOT the crew-winrate lever.
- BIG-PICTURE lesson: the crew emergency-meeting bar doesn't move crew outcomes in EITHER direction.
  Crew lose ~76-80% regardless; **77/140 base games were "nearly done (≥36/48 tasks) but lost"** — the
  real crew lever is the PARITY RACE (surviving kills / finishing tasks faster / voting imposters on
  STRONG evidence), not the tail-meeting threshold. Recommend: keep "raise" (safe waste-removal),
  reject "lower" (dangerous), look elsewhere for crew win rate. [[crewborg-crew-weakness]]

### Commitment to the button run must be gated on convictability, not just "alive"
Evidence: with "raise", acquisition is safe (we only START an Accuse run when the tailer is
`top_suspect`), but the OLD stickiness (`rule_based._sticky_accuse_target`) kept walking to the
one-shot button as long as the committed target was merely ALIVE — never re-checking the vote was
still winnable. A suspect exculpated mid-walk (the fitted model lowers P when a player does tasks /
is observed) still got the button spent on a meeting that now silent-skips. Fix: keep the committed
target only while it is alive AND still `top_suspect` (the player the meeting would eject). Suspicion
has no time decay, so this still survives the tail lapsing as we walk away from the suspect — but a
suspect that drops below the vote bar / is overtaken / voted / killed releases the run → back to
tasks. Lesson: a "commit through transient noise" rule must re-validate on the END CONDITION that
makes the action worth it (here: convictability), not a proxy (alive) that stays true long after the
action stopped paying off.

### Convictability flickering (≥0.9 → <0.9 mid-game) is suspicion-MODEL volatility, not a meeting bug
Evidence: the only reason the abandon-the-run guard above is needed is that a player we judged
near-certain (`top_suspect`, P≥0.9) can later fall below the bar. If the suspicion posterior were
stable, a convictable suspect would STAY convictable and the guard would rarely fire. So the guard is
DEFENSIVE against suspicion noise — the durable fix is in the suspicion components (the fitted model /
`suspicion_lab`), which is owned elsewhere. Lesson: when a downstream consumer needs a "don't act on
stale confidence" guard, note it as a SYMPTOM pointing at upstream model instability — fix the guard
to stay safe now, but flag the root cause rather than papering over it silently. [[crewborg-v70-equals-base]]

### Build/upload hazard: parallel worktree agents share the global Docker `:dev` tag
Evidence: a concurrent agent (imposter-kill worktree) was rebuilding `players-crewborg:dev` and
uploading under `--name crewborg` at the same time as this session — so `players-crewborg:dev` could
not be trusted to be MY code. Fix: build each arm under a UNIQUE image tag (`players-crewborg:accuse-cand`,
`:emr-base`, `:emr-lower`) and verify the image carries the change (`docker run … grep`) before
uploading. Also: hosted uploads/POSTs were flaky (broken pipe), so wrap them in retry loops and verify
server-side (`versions.py`) rather than trusting one attempt.
### fetch_artifacts --no-logs ALSO skips the policy-artifact telemetry zips
Evidence: v85 probe fetched --no-logs -> 0/8 artifacts; the zips download inside the `want_logs` branch (fetch_artifacts.py step 5). For any telemetry-verification fetch, keep logs ON (or split the flag — a --no-logs that keeps artifacts would match actual usage).

### v85 "chats confidently, then skips": LLM chat decisions never carry votes + 429s kill the later vote call + LLM blocking stalls the belief clock
Evidence (175 league eps, 337 v85 meetings; docs/experiment_v85_chat_then_skip.html): send_chat
decisions carried vote_target in 1/1566 cases, so the vote depends entirely on a LATER
set_tentative/submit_vote call; 35% of meeting-LLM calls fail (90% Bedrock 429 "Too many tokens per
day"), so in 60/102 confident-chat-no-player-vote crew meetings the vote fell to the deadline
fallback (top_suspect@0.9 gate) => skip (CONFIRMED, pre-committed rule). Compounding: each
synchronous LLM call blocks the game loop ~3s (bridge.loop_gap_ms == call latency); skip meetings
averaged 29s blocked of a 50s meeting, so the belief clock lags reality by up to ~670 ticks —
27 meetings never reached their believed deadline before the REAL meeting ended, and 26% of crew
meetings (60/230) ended in vote_timeout (selected votes that never landed: 21/77 player, 34/78
skip). VOTE_TIMER 240->1200 (v84) is NOT the bug; belief-time lag is. Minimal fix: remember the
color we accused in our own meeting chat and use it in _fallback_vote_target (attend_meeting.py:464)
ahead of top_suspect@0.9; companion fix for the timeouts = cut call cadence (chat re-triggers) and
submit the tentative early instead of waiting for a belief-time deadline that may never arrive.
### One root cause wore four masks: synchronous LLM calls at 5x meeting length
Evidence: v84's correct VOTE_TIMER fix (240->1200) quintupled meeting-LLM call volume; each SYNCHRONOUS call blocks the game loop ~3s -> (a) ~29s/50s meetings blocked, belief clock ~670 ticks behind, 26% crew meetings end vote_timeout (votes selected but never land); (b) server-side disconnects on the seats that live through meetings (v85 9.4%, v86 38.5% league games); (c) Bedrock DAILY token quota exhausted (800x 429 'Too many tokens per day') -> failed vote calls -> 0.9-gate skip -> James's 'chatting confidently but not voting'. The tracing-weight hypothesis was WRONG (v86 removed tracing, got worse) — beware time-confounded comparisons when a shared quota is draining. Fix = async worker + cadence cap + chat-implied fallback vote + early submit (v87).

- **Ghost-tasking noclip A/B (2026-07-02): nav is NOT the ghost bottleneck.** Code+warehouse
  said crewborg ghosts under-task (v85 league: 50.3% dead-completion vs notsus 61-69%; 72%
  standing-still dead) with the nav layer wall-routing ghosts and holding still on
  graph-unreachable goals. The surgical fix (crewborg-ghost:v1 = v84 + `_navigate_mask`
  straight-line when `self_alive=False`, no anchor, no reachable filter) A/B'd NOISE on the
  pre-committed metric (dead-completion 63.5% vs 67.0%, CI ±13pp; arms xreq_b5f6b8a7/xreq_8fcb29ae,
  warehouses /tmp/ab_ghost/{cand,base}_wh) and CAND ghosts stood still MORE (85.3% vs 76.2%,
  only ~8-10% of dead stillness is station-holding in both arms). Two lessons: (1) the ghost
  stillness is a decide-layer/time-allocation phenomenon (post-completion parking, dying with
  little left to do), not route-length; (2) a 100-ep arm resolves only ~±13pp on dead-completion
  (~35 subject crew deaths) — the ~11pp league gap needs a bigger n or a per-tick fingerprint
  metric, not a completion rate. Worktree `worktree-ghost-tasking` (b3d8844) holds the change +
  tests; do not merge on this evidence.

### Warehouse `died` events are INCOMPLETE — derive deaths from `player_state.alive=false`
Evidence: v88 probe analysis (2026-07-02): `key=died` had 28 rows vs 43 kills; kill victims
(e.g. ereq_7d629e3c slot 0, killed t=1159) had NO died event, so death-keyed stats (dead-seat
LLM calls, alive-meeting timeouts) were wrong until deaths were recomputed as
`min(ts) WHERE json alive=false` from `key=player_state`. Also: ghosts keep completing tasks,
so "tasks after death" is NOT evidence the player is alive.

### Post-gate, fallback-sourced crew votes don't vanish — they become corroborated (and hit like LLM votes)
Evidence: v88 probe (16v16 matched vs v87): crew fallback-source player votes 12 w/ 8 imposter
hits (67%) vs v87's 7 w/ 1 hit (14%), Fisher p=0.04; `meeting_vote_gated` fired 0 times — the
prompt rides vote_target on nearly every chat, so tentatives are almost always LLM-named and the
gate's work is done by the early-submit HOLD + corroboration check, not by live conversions.

### Dead seats were ~30% of meeting-LLM volume — muting them is free call budget
Evidence: v87 probe arm: 62/200 calls + 44/140 chats fired from dead seats (sim discards dead
inputs; 0 post-death vote_cast). v88 mute: 0 dead calls/chats, live chats rose 96→117 in the
matched probe.
