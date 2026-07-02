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

## 🎯 CURRENT STATE (reseeded 2026-07-02 session end)

**Champion: `crewborg:v89`** — the full stack: role-latch fix, idle/search FSM + freeze escapes
(kill-press, role-limbo, mid-task wedge/stall), witness posture, call-bar=conviction-bar,
VOTE_TIMER=1200, **async meeting LLM** (worker + 120-tick cadence + 5-call budget + dead-seat mute)
with the **tight vote gate** (fallback votes need witnessed / 0.9-posterior / explicit LLM
submit_vote). Form: at field par in an imposter-favored window (~31% overall, crew ~24% = par;
in favorable windows v87/v88 hit 51-55%, crew 43-46%). Ops pristine: 0 disconnects/timeouts/dead-leaks
across v87-v89. **Judge any form number against the WINDOW'S FIELD PAR** (field crew win oscillates
25-40% with draw rotation / opponent versions / patches — see lessons).

**Version ledger:** v84 (deterministic A/B base, never submit), v85-v89 champions in sequence;
full details in [version_log.md](crewrift/crewborg/version_log.md). Standing rules in
[`user_preferences.md`](../user_preferences.md): submissions ALWAYS LLM-on + all-telemetry;
deterministic uploads are A/B arms only; XP dashboards for >16-ep requests.

**Field velocity (session end):** notsus v168 (was v130 this morning — Andre ships hourly),
aaln v26, rowdaboat v6, forgeling v7, softmaxwell v12 all bumped today. Any absolute numbers here
stale fast; re-survey before acting.

**Warehouse dig (2026-07-02, rounds 391–394, /tmp/prime_wh):** three quantified gaps —
(1) **kill trigger**: isolated+ready conversion 2/5 vs notsus 9/9; longest unready isolation
windows (421-tick mean — no cooldown-timed approach); first kill median tick 3402 = slowest.
(2) **votes**: participation fine (2.9% no-vote) but meeting-1 = 12 skips/5 votes and 47%
accuracy overall vs 68–77% leaders; ejected-as-crew 5× (worst). relhalpha wins crew via 28
button-calls + 83% late-meeting accuracy. (3) **ghosts**: resume tasking at median 964 ticks
post-death vs 111–239 field-best.

**Three tracks opened 2026-07-02 (James):**
1. **Ghost nav shortcut** — BUILT on branch `worktree-agent-ad95c8246d5986371` (commit d28b97c;
   worktree `.claude/worktrees/agent-ad95c8246d5986371`): death already detected via ghost HUD;
   fix = straight-line noclip nav + skip anchor filters (port of parked `worktree-ghost-tasking`
   onto current main). 527 tests pass. Un-merged, un-uploaded. A/B metric must be time-to-first-
   ghost-completion (median 964 → target ~200), NOT completion rate (prior A/B flat on rate).
2. **Imposter kill failure** — INVESTIGATED (no changes): approach is fine (median 23.8px from
   crew when ready; 27.6% of ready ticks truth-inside 20px kill range) but only 19.6% of
   ready+in-range ticks convert (field 84-91%). Ranked: H1 witness-veto starvation (crew pair up;
   BASE_ISOLATION_RADIUS=48=2.4x kill range; URGENCY_FULL_TICKS=240 ramp resets on meetings),
   H2 meeting confiscation (body-reports reset unused cooldown 0→500; vote freeze), H3
   committed-victim mismatch (in range of the WRONG crew = no strike; hunt.py:57), H4 speed-parity
   shadow (47% of ready ticks stuck 20-32px), H5 v82 press-loop bug FIXED since v84. Next: one
   trace-enabled ~20-imposter-ep xreq (hunt reasons + committed victim + urgency) to split H1/H3.
3. **Suspicion evidence renovation (voting)** — corpus PULLED + VERIFIED: /tmp/susp_corpus_eps,
   692 eps across 16 xreqs (v82/v84/v85/v87/v88/v89 + v87-90 probes, crewrift_prime 0.4.31-era);
   artifact zips 691/692; **634 crewborg-slot episodes carry 1,486 per-meeting suspicion
   snapshots** (v82: 186 eps, v84: 179, v89: 47+49probe, v90probe: 50, …) — each ranks ~7
   suspects → ~10k labelable (observer,suspect,meeting) rows once joined to replay roles.
   KEY FINDING: NO upload ever set CREWBORG_TRACE_SUSPICION_FEATURES=1 (TRACE_GROUPS=all does NOT
   imply it — separate env gate, events.py:144), so NO existing episode has ranking[].features;
   build_dataset_runtime.py yields 0 rows on all real data. Snapshots DO carry per-meeting
   posteriors + per-suspect event summaries (kind/dur/target/region/min_dist — verified in live
   zips): 7/19 runtime features reconstructable; observed_samples, follow_death_samples and ALL
   10 social counters (incl tasks_completed_watched, the strongest weight) are NOT. Plan: (a) add
   the flag to the standing upload recipe (needs James OK — user_preferences.md edit), (b) renovate
   build_dataset_runtime for both full + degraded snapshots, (c) calibration analysis of live
   posteriors on the 692 eps now, (d) fresh traced upload + ~200-300 eps → true runtime refit.
   /tmp/expand-043 is JSONL-capable + hash-clean on 0.4.31 (verified) for the label stage.
   fetch_artifacts.py FIXED: --no-logs no longer drops policy-artifact zips (new --no-artifacts).

## ▶ OPEN LEVERS (evidence on file, none in flight)

1. **Evidence warming for the fitted suspicion posterior** — the remaining crew lever
   (train→serve gap; suspicion_lab runtime-feature rework scoped in its docs). Vote-threshold
   levers are REFUTED 4 ways (raise / lower-global / lower-conditional / deadline-passthrough —
   the last for zero channel volume: chats overwrite LLM tentatives 305:47).
2. **Imposter first-kill latency** — RelhAlpha opens ~1290 ticks vs our ~2350; distinct from the
   refuted witness-drop (that was 2nd-kill). Unexplored.
3. **Meeting-LLM latency/quota items** — TODO.md top entries (call-failure tuning at long
   meetings; the shared daily Bedrock quota; per-arm 429 asymmetry in concurrent A/Bs).
4. **Telemetry harvest automation** — league artifacts ephemeral (~1 round); per-round harvest
   loop scripted (session scratchpad pattern) but not made a standing cron/tool. TODO.md.
5. **Parked branches:** `worktree-ghost-tasking` (noclip, A/B-flat, harmless), 
   `worktree-v90-deadline-tentative` (refuted, has useful telemetry events), direction-2
   witnessed-only lever (merged, default-off, A/B-neutral).

## 🤖 Parallel track — LLM gameplay COMMANDER (built, gated OFF, unshipped)

Phases 1-3 done on main: background LLM writes priorities into `belief.commander`, modes read them
(bias-don't-force + strength dial); proven steering both roles in forced runs; commander worker is
the pattern the v87 meeting-LLM async fix copied. Ships behind `CREWBORG_LLM_COMMANDER=1` (+Bedrock).
Never A/B'd for win-rate value. Design: `crewrift/crewborg/docs/commander.md`.

## Tools / data (fresh as of session end)

Warehouses: /tmp/v87_league_wh (40 eps), /tmp/v88_league_wh (35), /tmp/v89_league_wh (36),
A/B pairs v89/v88 + v90/v89. Surveys: /tmp/survey_v8{7,8,9}_league.html. The 2-hour meta-loop
cron was DELETED at session end (James); re-arm with /loop if wanted — the cycle prompt lives in
the loop-skill invocation in this session's history and works well with ~2h cadence.
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
- **Prime field** (Competition `div_acbde92a-…`, league `league_a12f5172-0907-4d04-8bcb-ca02f5360e3a`):
  **11 entrants** as of 2026-07-02 rounds 391–394 (~10-min cadence, 12 eps/round, 8 seats):
  notsus:v168, relhalpha-hunter:v1, jordan-crewborg-aaln:v1, softmaxwell-crewborg:v12,
  rowdaboat-notsus:v6, richard-notsus:v2, crewborg-aaln:v26, forgeling-focusfire:v7,
  crewborg-mv:v1, daveey-prime-notsus:v2, **crewborg:v89 (LAST, 31%; crew 24% vs field-par ~36%;
  imp 57% ≈ par)**. Survey: /tmp/survey_prime_r391_394.html (+ /tmp/prime_r391_394 artifacts).
  Crew wins in this field come from ejections, not tasks — v89's tight vote gate casts 0 votes in
  most crew games. NOTE: the 4-way vote-lever refutations predate this 11-entrant field.
