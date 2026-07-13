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

## 🎯 OBJECTIVE: v106 SUBMITTED to Crewrift Prime — watch qualification; then read whether it's actually better

**v106 SUBMITTED (James, 2026-07-09)** to Crewrift Prime (`sub_cc707442-849d-4a11-876a-39be36e6cfa6`,
auto-champion=always, policy-version `f8a407c5…`). As of submit it's `status=pending` (commissioner
places it on its ~10-min round cadence). **Qualification poller running:** `.tmp/poll_v106_qualify.py`
→ `.tmp/v106_qualify.log` (tracks OUR submission+membership by pv-id; the skill's `monitor` has a bug —
it terminated on the pre-existing v100 champion's 'competing' status, so use the targeted poller).
Watch for: pending → placed → qualifying → **competing (✅) / disqualified (❌)**. Champion is still
v100 until v106 qualifies. DQ risk to watch: `substatus=crash` = LLM-latency timeout (pull qualifier
episode logs); the residual ~7-9% alive-seat vote_timeout is a latent concern.

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

**Next (post-qualification):** if we want to know v106 vs v105 gameplay, run a PACED matched A/B
(separate 100-ep requests, drained one at a time). Optionally chase the residual alive-seat timeout.

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

## ⚠️ CRITICAL HANDOFF FACT: ALL of v101→v105 is UNCOMMITTED
Last crewborg commit = `03fff48` (= v100 code). Everything since is working-tree only:
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
