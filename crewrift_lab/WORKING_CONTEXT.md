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

Current build **`crewborg:v50`** (uploaded, **NOT submitted**). It carries everything:
vantage-SEARCH + Recon + cooldown fixes, **working LLM meetings** (Bedrock), and the
**mid-game reconnect**. Prime champion is still **v42** (last placed; v49 was *rejected*
from qualifiers, v50 not submitted).

**Clean diagnosis (combined n=127 clean, Prime round-robin vs the field; meeting-aware):**
crewborg imposter **70% win / 1.38 k/g** vs Aaron **86% / 2.01** and Andre **84% / 2.02**.
Crew is ~5% win for *everyone* (imposter-dominated field → crew win-rate is not
discriminating; judge crew by sub-metrics, not the team outcome).

**Root cause = subsequent-kill CONVERSION, driven by post-kill positioning:**
- crewborg gets a **2nd kill only 44%** of the time (vs Aaron/Andre **~83%**), and gets
  **0 kills in 11%** of imposter games (they're 0%). It lands the 1st, then stalls.
- **idle-ready ~2.8× Aaron** (2669 vs 953 ticks/g), and **189 ticks (~8s) since its last
  crew sighting at the moment it's ready** — Aaron is at **0** (a victim is always there).
- So it's not cooldown/dither/witnesses: **we lose crew contact and don't have a victim in
  sight when ready** — first kill *and* every kill after. Lever = stay on / re-approach the
  nearest killable crew through the cooldown. **NOT YET BUILT.**
- ⚠️ One earlier attempt (v46: make SEARCH pick the crew-densest room) **regressed** — the
  random sweep's *mobility* was load-bearing. The fix must be surgical (approach the nearest
  *single* victim), not a rewrite of room-picking.

**Next step:** the spatial pass is half-done — use `tools/positioning_viz/` (web UI +
`render_event.py` PNG) on `/tmp/v50_pertick` to see *where* "ready but no victim in sight /
doesn't commit" happens (hunting-path vs target-selection), then build the surgical
post-kill re-approach and A/B it (crewrift-ab skill). Secondary direction the human raised:
**crew-side — punish aggressive imposters** (detect their relentless proximity/kills to
reduce Aaron/Andre's imposter win and lift our crew win).

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
