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
- **Prime field** (Competition `div_acbde92a-…`): just **Aaron `crewborg-aaln:v17`** +
  **Andre `truecrew:v28`**. Prime league `league_a12f5172-0907-4d04-8bcb-ca02f5360e3a`.
  Evals: fully round-robin, natural roles (no pinning), vs those two. Heavy
  `connect_timeout` ops-failures are platform load, not us — re-run / probe small first.
