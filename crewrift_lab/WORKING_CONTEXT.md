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

## 🤖 PARALLEL TRACK — LLM GAMEPLAY COMMANDER (Phase 1 done; both LLMs live in-pod 2026-06-26)
A background LLM steers *gameplay* by writing **priorities** into `belief.commander` that the modes read to
bias execution — never selecting a mode, never blocking a tick. Design:
[`crewrift/crewborg/docs/designs/llm-commander.md`](crewrift/crewborg/docs/designs/llm-commander.md) (design.md §10.6).
**Phase 1 (scaffold + wiring + observability) BUILT & gated-off** — `strategy/commander/`, `belief.commander`,
`CommanderStrategy` on a `CloseAwareSynchronousStrategyRunner`, `apply_inferences`; modes do NOT yet read priorities.
`domain.commander_*` traces (incl. `env_seen`) via `CREWBORG_TRACE_GROUPS=commander`. **Bedrock-in-pod fix (KEY):**
sidecar mode STRIPS `USE_BEDROCK` and injects `AWS_ENDPOINT_URL_BEDROCK_RUNTIME`, so BOTH LLM factories now gate
Bedrock on that **endpoint**, not `USE_BEDROCK` (`strategy/commander/llm.py` + `strategy/meeting/llm.py`).
**Confirmed live in-pod** (Crewrift Prime XP, v64): commander 4637 `commander_call` ok / 0 errors; **meeting LLM
REVIVED** — 290 `meeting_llm_decision`, 0 `_fallback` (was 184/184 disabled). Infra issue:
[`docs/issues/2026-06-26-bedrock-disabled-crewrift-prime-xp.md`](docs/issues/2026-06-26-bedrock-disabled-crewrift-prime-xp.md).
NEXT: **Phase 2** — imposter levers (`hunt_room`/`target_player`/`avoid_room` in `search.py:266`/`recon.py:534`/`hunt.py:612`)
+ danger mode, then A/B. Branch `worktree-labs-work`; uploaded v55–v64, **none submitted**.

## 🎯 OBJECTIVE: crewborg's IMPOSTER KILL EFFICIENCY (the durable gap)

Champion is still **v42** (shipped Prime). Current code lineage = **v54** (= clean HEAD; v50 lineage
+ everything: vantage-SEARCH, Recon, reconnect, LLM meetings). **v61 = v54 code + debug tracing** (the
complete-baseline subject). NOT submitted: v53/v58 (inconclusive A/B arms), v61 (eval only). **Avoid
v59/v60 — separate research thread.**

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
- **`tools/positioning_viz/`** — kill-ready spatial viewer (meeting-aware; see its README).
  Needs a **per-tick** warehouse (`--snapshot-every 1`); one exists at `/tmp/v50_pertick`
  (run #1, 100 eps). `/tmp/v50_warehouse` + `/tmp/v50b_warehouse` are the every-10 combined
  ~127-clean set used for the stats above.
- Analysis scripts in `crewrift_lab/` (kill_latency, visibility_at_ready, aaron_compare,
  prime_summary, suss_rate) — all **meeting-aware** now (count Playing samples, never raw
  tick deltas; see best_practices "meetings are not idle time").

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
  — see `docs/issues/2026-06-26-bedrock-disabled-crewrift-prime-xp.md`.
- **Expander**: `/tmp/expand-043` (master sim `26ee08c`) handles **crewrift_prime
  0.4.3–0.4.7** (the fork's version bumps didn't change the sim). Use
  `CREWRIFT_EXPAND_REPLAY=/tmp/expand-043` for the warehouse.
- **Prime field** (Competition `div_acbde92a-…`): just **Aaron `crewborg-aaln:v17`** +
  **Andre `truecrew:v28`**. Prime league `league_a12f5172-0907-4d04-8bcb-ca02f5360e3a`.
  Evals: fully round-robin, natural roles (no pinning), vs those two. Heavy
  `connect_timeout` ops-failures are platform load, not us — re-run / probe small first.
