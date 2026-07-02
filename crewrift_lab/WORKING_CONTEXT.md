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

## ⛔ PLATFORM BLOCKER (since 2026-07-02 ~22:20Z)

**/jobs/* artifact routes 403 "not a softmax team member"** (results/policy-artifact/policy-logs);
/v2/* fine; `softmax login` no-ops; `--force` relogin untried-successfully; NO elevated flag exists.
Blocks: instant-vote A/B read-out (/tmp/iv_{cand,base}_eps, 50v50, replays present, results
missing — synthesizable from replays, camo agent validated the method), HS probe telemetry,
league telemetry harvest. Escalate if relogin doesn't fix.

## 📋 A/B ledger (2026-07-02 evening)

- **Camo: SAFE-POSITIVE** (mechanism p=5.6e-13, primaries right-direction NS, guards pass) — shipped in v92+.
- **Urgency 240→80: NEGATIVE** — 3rd and final witness-gate refutation; contact starvation dominates.
- **Vote-bar sweep: INCONCLUSIVE** — v4 calibration VALIDATED live (86-100% precision at all bars);
  conversion NS; bar60-vs-bar90 200/arm confirmation is the designed follow-up (bar60 shipped anyway
  per James). Next lever = vote COORDINATION (HS trust network fits).
- **Instant-vote: episodes complete, read-out blocked** (above). Prior evidence adverse (22-50%).
- **Ready-search: NEUTRAL-safe** (pathology was partly pre-fixed by v77-80 FSM); shipped as hardening.

## ▶ OPEN LEVERS

1. Suspicion detector bug: reported_bodies/button_calls_made ALL-ZERO live (398 meetings) — fix
   before next refit; refit pipeline is fully operational now (runtime features flowing from every
   league round).
2. Vote coordination (the conversion bottleneck; HS trust network is the vehicle).
3. bar60-vs-bar90 200/arm confirmation (if the sweep's p=0.09 ejection gain is real).
4. Movement toolkit (tools/imposter_movement/) + room-density pipeline are reusable measurement infra.

## Load-bearing infra facts

- Player SDK from Metta-AI/coworld-tools tarball (issue #13); coworld CLI 0.1.27 pinned.
- Expander /tmp/expand-043 (= tools/bin/expand_replay-26ee08c) hash-clean through crewrift_prime
  0.4.35, JSONL-capable. Warehouses/duckdb run from tools/event-warehouse/crewrift-event-warehouse.
- Prime field ~11 champions, ships hourly (notsus v168→v174 in one day); server random/top_n pool
  selectors 500 on statement timeout — pin explicit policy_refs.
- fetch_artifacts: --watch dies silently on transient errors + completeness misses results.json —
  ALWAYS verify final on-disk counts; refetch is idempotent.
- Bedrock LLM: sidecar-endpoint gating; meeting LLM verified firing v91 probe (117 decisions/9 fallbacks).
