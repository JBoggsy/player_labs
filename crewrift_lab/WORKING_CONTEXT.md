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

## 🔧 SIDE-THREAD (2026-07-21, merged to main): Honor Society was DEAD in live play — FIXED + verified (crewborg:v109, NOT submitted)

Discovered the HS was a **no-op in every real game**: our code used a LEGACY 5-token `HS1` form,
but live members (sasmith-crewborg-hs1:v15) use the **compact** `HS1 <sig>` (sig over
`HS1|<ts5>|<color>`, ts5=(unix//5)*5, unpadded b64url; brute-force verify over ledger keys × a
{now5,-5,-10,+5} window; no first-poster-wins). `parse()` returned None on every real line. ALSO
found `PLAYER_COLOR_NAMES` stale since the game's 2026-06-24 palette change (`1cbd4de`) — slots ≥1
all wrong, corrupting v106's slot-seed self_color for non-slot-0 seats (latent bug beyond HS). Fixed
both; `CREWBORG_HONOR_SOCIETY` now **defaults ON**. Proved the compact spec by verifying 17/17 live
captured sigs vs sasmith's registered key. Uploaded **crewborg:v109** (traced) and verified END-TO-END
via `xreq_25bb7e0f` (v109 crew + sasmith crew): crewborg's trace shows `society: crew announce` +
`honor_claim`/`honor_known_member {label:alex-smith}` — we now send, verify, and register real HS1.
641 tests green; committed on the branch. **NOT submitted** (James's gate). Next if pursued: measure
whether HS actually helps (it's never been A/B'd in isolation), then the coordinated-vote-piling
direction (WEEKLY_CONTEXT Direction 1). Full detail: version_log v109.

## 🎯 OBJECTIVE: v107 QUALIFIED & CHAMPION 👑 — watch league standings recover, then pick the next lever

**v107 is `competing/active` and CHAMPION** in Crewrift Prime (qualified in ~5 min,
2026-07-15 17:10Z; membership `lpm_fd1323fc…`, Competition division). v106 is
`competing/benched` (no longer champion, benched by supersession). v107 = v106's fixes +
the self-hunt fix, A/B-verified (imposter restored to v100 level; see below). Standings
inherited from the damaged-v106 era: ~rank 14/16 — **watch whether rank/score climb over the
next ~50-100 rounds now the imposter actually kills opponents instead of itself.**

**2026-07-21 LIVE-ROUND AUDIT (10 rounds, 199 eps, warehouse /tmp/wh10, survey /tmp/survey10.html):**
v107 is rank **14/18** (52.4% WR; leader 60.8%). Role split in the sample: crew 27% (11/41, field
median ~32%), imposter 41% (7/17, field ~55-77%). Three mechanistic findings:
1. **SELF-ACCUSATION BUG (new, smoking gun):** crewborg *as crew* chats "orange sus: lurking on a
   vent, they were tailing me. vote orange" — its OWN color — 5 msgs / 2 eps
   (ereq_94c9f0fc: field then ejected it; ereq_e502d991). The deterministic accusation template can
   select self as suss target (self_color missing from the candidate filter — same class as the
   v106 self-hunt bug, but in the meeting/accusation path). It skip-votes while doing it, so the
   vote self-exclusion works; the CHAT target pool doesn't exclude self.
2. **Imposter too conspicuous + too timid:** ejected 53% of imposter seats (field median ~31%,
   best 0-20%); votes-received/seat 2.47; kills/seat 1.29 (top: 1.9); isolated-with-crew kill
   conversion 19% vs 34-50% for winners (e.g. 1410-tick isolated interval unconverted in
   ereq_1cd1f049). Opponents' "X was tailing me" detectors fire on its follow-heavy stalking.
3. **Crew draws suspicion:** votes-received/seat 1.37 as crew (2nd-worst), 15% of crew seats
   ejected — opponents (and framing imposters) cite "tailing me / lurking on a vent", i.e. its
   crew movement pattern trips the same detectors.
   Also: league telemetry shows LLM fired only ~38% (154 decision / 248 fallback, 236 Bedrock
   throttle lines over 58 eps) — production meetings mostly run the deterministic path.

**Next-lever candidates (from the 2026-07-15 session):** (1) residual ~7-9% alive-seat
vote_timeout (cheap telemetry dig, never done); (2) the social-rework crew-win question is
STILL open — every A/B so far under-fired the LLM (~19-27% vs the 60% gate; shared Bedrock
pool contention) — needs either low-contention timing or the quota fix; (3) mine v107's live
rounds with coworld-hypothesis-miner / the top-3 advantage methodology
(docs/top3-advantage-reporter-guidance.md).

**What v106 is (the fix):** kills the v105 `no_vote`/vote_timeout regression. Root cause (replay-
confirmed): v105's `self_alive` went **falsely False** — the one-shot self_color latch stuck a
neighbour's colour pre-meeting; the census self-death check (types.py:776) flipped self_alive off when
that neighbour died; dead-mute then idled a LIVE meeting → game's "-10 for failing to vote" (19/200 v105,
0/200 v106). 3-layer fix (638 tests green): (1) seed self_color from runner `?slot=` (zero-CV — slot IS
colour, like suspectra); (2) self_color source hierarchy (marker/slot latches hard, corrects a
provisional sprite guess once — keeps v102 anti-drift); (3) dead-mute still SKIPs at the deadline
([[crewborg-idling-is-dangerous]]). version_log v106 has the detail.

**Validation state (honest):** v106 is SOUND but NOT proven better than v105.
- ✅ dead-mute vote_timeout fixed: 0/172 matched A/B (v105 8.6%).
- ✅ sound at ≤100-concurrent: 0% dead-game, LLM 73%, crew win 29% / imposter 56% (`.tmp/v106_field/eps100`).
- ⚠️ the matched v106-vs-v105 A/B win-rate is CONTAMINATED — fired 4×100=400 at once → opponent pods
  connect-timed-out → 76% dead games (ZERO at ≤100). LESSON: pace arms as separate ≤100-ep requests.
- ⚠️ residual ~7-9% alive-seat vote_timeout remains (separate, pre-existing; NOT the dead-mute path).

**🚨 A/B VERDICT (2026-07-15): v106 imposter SELF-HUNT BUG — the CHAMPION is hunting its own
sprite.** The paced v106-vs-v100 A/B (200 cand / 100 base eps; stopped early — verdict decisive;
round-3 xreq cancelled) found: imposter win 71%→35% (p=0.005), kills 1.58→0.58, zero-kill imposter
games 4%→44%. Root cause (telemetry-confirmed, 45/53 cand imposter eps, 0/50 base):
`visible_victims()` (strategy/opportunity.py:147) filters only `teammate_colors` and NEVER excluded
`self_color` — in v100 self was accidentally protected because reveal ingestion put OUR OWN color
into teammate_colors; v106's ingest-time self-exclusion (types.py:868-871, the correct v102-fix)
removed that shield, and select_victim's most-isolated heuristic now locks onto the self sprite
(always visible, dist ~6.3, 111,568 self-strikes vs 24 real). Crew metrics unchanged; LLM fired
27%/19% (<60% gate) so the social rework is STILL untested. Artifacts: `.tmp/ab_v106_v100/`
(diff.json, ab.html, finding.md, compare.md; arms in cand/ + base/).

**v107 SHIPPED + A/B VERIFIED (2026-07-15, commit `6cfdffb`, pv `5a4e0eae…`) — the self-hunt fix
works.** Fix: new `opportunity.is_live_opponent` (not self / not teammate / not dead) at every
roster-derived imposter pool; 7 regression tests; 645 green. **A/B verdict (196 v107 / 100 v100
matched eps):** self-strikes 0/36 imposter eps (v106: 45/53); kills 1.67 vs 1.28 (v106: 0.58);
zero-kill 3% vs 11% (v106: 44%); imposter win 64% vs 61% (v106: 35%); crew all noise. Pure-bug-fix
profile: no regression anywhere. Artifacts: `.tmp/ab_v107_v100/` (diff.json, ab.html, finding.md).
Caveat (same as v106 A/B): LLM fired ~19-27% both arms → deterministic path compared; fine, the fix
is deterministic-only. NOTE: mid-A/B the platform 500'd on GET/POST /v2/experience-requests
("Coworld Manifest tags Field required", ~15:55-16:45Z) then recovered; babysitter drained the
stuck batches.

**v107 SUBMITTED (James's go-ahead) + QUALIFIED + CHAMPION (2026-07-15 17:10Z, ~5 min
qualifier):** `sub_acd40308…`, membership `lpm_fd1323fc…` `competing/active` champ=True;
v106 → `competing/benched`. (Ops note for next submit: the skill's `monitor --watch` again
terminated on the OLD champion's 'competing' — use a targeted by-pv-id poller,
`.tmp/poll_v107_qualify.py` is the template.)

**Next action: when the 4 watchers drain (~10-15 min), (1) confirm vote_timeout→~0 on v106; (2) run
compare.py role-split. If clean, the v105 social rework (minus this bug) is worth a powered ~300/arm
A/B vs v100 to settle the crew-win signal (was 15%→22%, p=0.11, underpowered). Do NOT submit yet.**

<details><summary>The v105-vs-v100 social-rework A/B result (2026-07-09, the run that surfaced the bug)</summary>

400 eps, paced, LLM GATE PASSED (v105 71.6% / v100 81.9% seat-0 decision rate — first clean test of
the rework vs all the throttled historical data). crew win 15%→22% (p=0.11, underpowered ~160 crew /
~40 imposter per arm); imposter 57%→59% (p=0.86, flat); **the no_vote_rate regression** 0%→9% crew /
0%→14% imposter that v106 now fixes. Artifacts: `.tmp/ab_v105_v100/` (diff.json, ab.html, finding.md).</details>

<details><summary>Prior objective (done): run the paced A/B so the LLM fires</summary>

The chat-persuasion social rework is built + uploaded (v105) but had **never been cleanly
A/B-tested** — every attempt was starved by Bedrock throttling until we fixed the token cost.
Ran it paced at ≤400 concurrent; LLM fired reliably; see result above. First tried mining
historical episodes via the episode-search API (`POST /v2/episodes/search`) to avoid a fresh
run — but "LLM fired" and "roster matched" are anti-correlated in the archived data (throttled
matched-roster runs, random-field fired runs), so a fresh paced A/B was unavoidable.
</details>

- **Champion in the league: still v100** (last submitted). v101-v105 are UPLOADED (inert), NOT submitted.
- **crewborg on the live commissioner board sits ~#12/12** — but that's largely the imposter-favored
  meta (crew wins ~18% field-wide, imposter ~82%); crewborg is strong imposter (~87% win, 3rd/8),
  mid-field crew. There is NO clean mechanistic crew lever left (see "closed levers"). The social
  rework targets meeting *persuasion* (both roles) — the current open bet.

## ~~CRITICAL HANDOFF FACT~~ RESOLVED: v101→v106 is COMMITTED
`db3b1ae` (v101-v105 social rework) + `94888ef` (v106 self-ID/dead-mute fix) + `6735493` (docs/infra).
The list below is what those commits contain (kept for orientation):
- `events.py` — teammate-belief trace (`role_resolved` enriched + new `teammate_belief_changed`).
- `types.py` — teammate self-dedup fix + **self_color one-shot latch** (was re-derived every tick,
  drifted onto teammates → the v102 kill regression; now latched once).
- `strategy/meeting/context.py` — `recent_events` compressed + **`players` rendered as terse PROSE**
  not JSON (context 2490→~1340 tk/call; this is what got the LLM firing).
- `strategy/meeting/spend.py` (NEW) + `attend_meeting.py` — read sidecar `GET /spend`, gate
  FOLLOW-UP LLM calls on remaining per-episode budget (1st call always allowed); traces `meeting_spend`.
- `strategy/meeting/accusation.py` — deterministic accusations close with ". vote <color>".
- `memory/imposter.md` + `memory/crewmate.md` — persuasion doctrine from the chat_study.
- `crewrift_lab/chat_study/` (NEW, untracked) — the vote-persuasion study pipeline.
- **634 tests green.** **COMMIT THIS before more churn** (it's a lot of validated work at risk).

## ▶ NEXT ACTION: the v105-vs-v100 A/B (paced)
- Matched: crewborg pinned seat 0 + the **same 7 fixed champions both arms** (relhalpha:v1,
  notsus:v130, scott-hs1:v2, forgeling:v5, softmaxwell:v25, sasmith-hs1:v1, crewborg-aaln:v25),
  natural roles. ~300 eps/arm for power.
- **PACE IT: ≤400 episodes running concurrently** (fire ≤4×100 at once, let them drain, then more).
  Firing 6-8×100 at once self-throttles the shared Bedrock pool → LLM collapses to ~6%. (Rule now in
  best_practices.md.)
- **Fetch `--no-replay`** (telemetry.jsonl is all the measurement needs) and **delete each batch's
  episode dir after measuring** — fetching replays for big batches filled the disk (deadlocked a
  session). `--watch` is BROKEN on crewrift_prime 0.4.52 (reports 0 completed) — use one-shot
  `-n 100` fetch and poll.
- **GATE before trusting the compare: verify cand LLM-decision rate ≥60%** (count
  `domain.meeting_llm_decision` vs `_fallback` in crewborg's `artifacts/policy_artifact_*.zip`
  telemetry.jsonl). If low, the A/B only tested the deterministic path — the rework wasn't exercised.
- Then: `crewrift-ab/scripts/compare.py` role-split (target win_rate); build warehouses from a
  replay-fetched subset for ejection accuracy BY crewborg role — **imposter voted-out DOWN =
  deflection working; crew imposter-ejection UP = persuasion working**. Drop ops-fail episodes first.
- Ship v105 only if the LLM fired AND the social metrics move the right way (else the kill fix alone
  in v103+ is still a real, shippable improvement over v100).

## Chat-persuasion study findings (the social rework is built FROM these)
`crewrift_lab/chat_study/` (851 eps / 2450 meetings / 6757 NL chats; labels = REAL vote movement):
1. **Concrete evidence is the top persuasion lever, esp. imposter** — accusations WITH a cue land
   64% vs 43% without. crewborg's `fabricate_accusation` already makes cues; fire it, never bare-accuse.
2. Explicit "vote X"/"X sus" phrasing persuades; asking questions does NOT (defers).
3. Bandwagoning a live pile > opening a fresh accusation.
4. Self-referential defensiveness ("not me / I was doing tasks") DRAWS suspicion — don't self-defend unprompted.

## Bedrock LLM throttling — the hard-won operational truth
- The 429 "Too many tokens per day" is **shared-capacity ThrottlingException on the TOURNAMENT
  account `583928386201`** (`role/episode-runner-bedrock`), NOT our per-account quota (ours =
  714M/day, barely used) and NOT (for xreqs) the per-episode sidecar spend limit (xreqs have none set).
- It's **load contention** on the shared pool — worsens under concurrency. **Self-inflicted above
  ~400 concurrent episodes** (binary search: 100/200/400 hold LLM ≥60%, zero 429s; 800 → 52% + throttles).
- Token cost per call was the multiplier: prose-players compression cut context 2490→1340 tk, which
  is what moved LLM-use 2%→67% at equal load. `claude-haiku-4-5`, max_tokens 512.
- Latency median 2.6s / max 10s vs `CREWBORG_LLM_TIMEOUT_SECONDS=3.0` → some calls time out at scale;
  consider raising the eval timeout.
- I can't read `583928386201`'s quota directly (my SSO grants sandbox/prod/infra/staging only, not
  tournament). A quota increase there is the durable fix if throttling keeps blocking evals.

## CLOSED levers (don't re-chase — verified dead this session)
- **Wanderer / crew task-throughput bug** — GONE. crewborg crew 0% zero-task, 6.36 tasks ≈ notsus.
  The [[crewborg-crew-weakness]] 06-30 diagnosis is STALE (fixed by v77-80 FSM).
- **Teammate detection "broken"** — REFUTED by belief trace (0/24 failures; the "2 colors" was self
  inclusion, benign). Then the self-dedup FIX for that briefly caused the v102 kill regression — now
  fixed (latch). Detection is fine.
- **v102 kill regression (1.86→0.97)** — root-caused to the per-tick self-dedup deleting drifting-
  self-colored teammates; FIXED (v103+, confirmed 1.76→1.58 ~flat, no-kills 3%→3%).

## Platform / infra facts (load-bearing)
- xreq `top_n`/`random` seat-fill 500 is FIXED + deployed (metta #17288 + #17294; pool now ranks by
  the division's commissioner leaderboard). Both metta branches cleaned up.
- Event warehouse: `build_warehouse.py` now points at `replay.json` (platform serves replays
  UNCOMPRESSED — raw `CREWRIFT` magic, not zlib). Correct expander binary = `expand_replay-34a97a3`
  (NOT the `d9f6b30` in versions.env). Pass expander an ABSOLUTE path. Vote targets live in
  `vote_cast.value.target_slot`/`target_label` (`.target` is skip-only).
- fetch_artifacts/stream_eval/build_warehouse/xp_dashboard need `--elevated` for opponents' artifacts.
- Meeting LLM recipe: `--use-bedrock --bedrock-model us.anthropic.claude-haiku-4-5-20251001-v1:0
  --secret-env CREWBORG_LLM_MEETINGS=1 CREWBORG_CHAT_NLP=1 CREWBORG_METRICS=1 CREWBORG_TRACE_GROUPS=all
  CREWBORG_TRACE_SUSPICION_FEATURES=1`.
- Player SDK from Metta-AI/coworld-tools tarball (issue #13); coworld CLI pinned.
- /tmp fully cleaned of eval artifacts this session; everything re-fetches fresh.

## Reusable infra built this session
- `chat_study/` — merges any vote-target warehouses (`--warehouses`/`--glob-dir`) + LLM-labels chat;
  the persuasion/suspicion labels + readable-logit fit are the template for future social studies.
- Belief trace (`teammate_belief_changed`) — per-game teammate-belief queryable from policy artifacts.
