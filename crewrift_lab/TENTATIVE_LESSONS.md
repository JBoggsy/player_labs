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
