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

## 🎯 CURRENT STATE (reseeded 2026-07-03 session end)

**Champion lineage: v91 COMPETING+CHAMPION (rank ~6); v92 and v93 QUALIFYING** (lineage
auto-champion — last to qualify holds the seat). All three = the 2026-07-02 full-stack ship
(James-authorized without pre-A/B): v89 base + **v4 live-fit suspicion weights** + **vote bar
0.6/lead 0.2** + **ready-state re-search** (recon staleness 360 + spent sightings + parked guard +
empirical density prior) + **Honor Society ON** + full tracing (incl. suspicion features).
v92 adds WATCH camouflage (default-on) + HS base64url interop + known-members registry;
v93 adds role-reveal trust (verified member claims pin P(imposter)~0).
Ship recipe: standing LLM + all telemetry + CREWBORG_TRACE_SUSPICION_FEATURES=1 +
CREWBORG_HONOR_SOCIETY=1 + seed + CREWBORG_VOTE_PROBABILITY=0.6 + CREWBORG_VOTE_LEAD=0.2.

**On main, unshipped (rides v94):** role-limbo veto fix (probe forensics); instant-vote knob
(CREWBORG_LLM_SUSS_INSTANT_VOTE, default OFF — A/B episodes on disk, read-out BLOCKED, below).

**Honor Society state:** HS1 spec (Alex Smith) implemented; seed ~/.crewborg/honor_seed.b64
(0600); pubkey Gq5nOr6NdgrRPfi7Ahzm+i9fuMJdHIaNHaDDDUuRhMc=; known-members registry
data/honor_members.json (us + alex-smith); receiver accepts both b64 flavors; PROBE-VERIFIED
live (23 announces/16 eps, mutual trust held; the one bad vote = role-limbo, fixed).
Told Alex: encoding fork + our key. STILL TO TELL: same-key multi-seat collides with
first-poster-wins (distinct key per concurrent seat — crewborg-hs2:v1 pattern, seed /tmp/hs2_seed.b64).

## ✅ RESOLVED (2026-07-03): /jobs/* 403 was metta PR #17028 (opt-in elevation), not an outage

Root cause: Softmax team members are now EXTERNAL-by-default; TEAM_AUTH routes (per-episode job
artifacts for another player's policy — results/replay/policy-logs) need
`X-Use-Elevated-Privileges: true`. Fix: `coworld --elevated ...` (CLI, needs the 0.1.28 pin — see
below) or the header directly. Added `--elevated` to `fetch_artifacts.py`, `xp_dashboard.py`, and
passthrough in `stream_eval.py`/`build_warehouse.py` (crewrift-event-warehouse skill); verified live.
**None of these default it on** — every invocation needs the flag explicitly.
**Unblocks:** instant-vote A/B read-out (/tmp/iv_{cand,base}_eps, 50v50, replays present — results
should now be fetchable with `--elevated`, re-run the fetch to confirm), HS probe telemetry, league
telemetry harvest — all previously blocked by this, now worth re-attempting.

## ⛔ PLATFORM BLOCKER (confirmed 2026-07-03, reproducible 3/3)

**xp-request roster `random`/`top_n` seat-fill 500s** — `eligible_champions` CTE query (joins
policy_versions → league_policy_memberships → … → episode_policy_metrics for a mean_reward-ranked
pool) hits `psycopg.errors.QueryCanceled: canceling statement due to statement timeout`. NOT flaky —
3 back-to-back identical failures. Blocks **true tournament-style requests** (random/top_n opponent
seats — see the new definition in `coworld-experience-requests/SKILL.md`); the "pin explicit
policy_refs" workaround still works but answers a narrower question (a fixed field, not a random
draw from the live pool) and is not a substitute when "tournament-style" is specifically wanted. The
`resolve --division --top N` ranking (division-leaderboard endpoint) is unaffected — only the
xp-request roster-fill path breaks. Worth escalating: may explain why the real tournament/league
looked "broken" too, if the commissioner's own round matchmaking hits the same query.

## 📋 A/B ledger (2026-07-02 evening)

- **Camo: SAFE-POSITIVE** (mechanism p=5.6e-13, primaries right-direction NS, guards pass) — shipped in v92+.
- **Urgency 240→80: NEGATIVE** — 3rd and final witness-gate refutation; contact starvation dominates.
- **Vote-bar sweep: INCONCLUSIVE** — v4 calibration VALIDATED live (86-100% precision at all bars);
  conversion NS; bar60-vs-bar90 200/arm confirmation is the designed follow-up (bar60 shipped anyway
  per James). Next lever = vote COORDINATION (HS trust network fits).
- **Instant-vote: episodes complete, read-out blocked** (above). Prior evidence adverse (22-50%).
- **Ready-search: NEUTRAL-safe** (pathology was partly pre-fixed by v77-80 FSM); shipped as hardening.

## ▶ OPEN LEVERS (week roadmap with evidence: [WEEKLY_CONTEXT.md](WEEKLY_CONTEXT.md))

1. Suspicion detector bug: reported_bodies/button_calls_made ALL-ZERO live (398 meetings) — fix
   before next refit; refit pipeline is fully operational now (runtime features flowing from every
   league round).
2. Vote coordination (the conversion bottleneck; HS trust network is the vehicle).
3. bar60-vs-bar90 200/arm confirmation (if the sweep's p=0.09 ejection gain is real).
4. Movement toolkit (tools/imposter_movement/) + room-density pipeline are reusable measurement infra.

## Load-bearing infra facts

- Player SDK from Metta-AI/coworld-tools tarball (issue #13); coworld CLI 0.1.28 pinned (bumped
  2026-07-03 from 0.1.27 for `--elevated` support — `uv lock --upgrade-package coworld && uv sync`).
- Expander /tmp/expand-043 (= tools/bin/expand_replay-26ee08c) hash-clean through crewrift_prime
  0.4.35, JSONL-capable. Warehouses/duckdb run from tools/event-warehouse/crewrift-event-warehouse.
- Prime field ~11 champions, ships hourly (notsus v168→v174 in one day); server random/top_n pool
  selectors 500 on statement timeout — pin explicit policy_refs.
- fetch_artifacts: --watch dies silently on transient errors + completeness misses results.json —
  ALWAYS verify final on-disk counts; refetch is idempotent.
- Bedrock LLM: sidecar-endpoint gating; meeting LLM verified firing v91 probe (117 decisions/9 fallbacks).
