# Suspicion-v5 refit (runtime-v116-L2 weights) — pre-registration (2026-07-28, loop-alpha L2)

**Registered BEFORE any arm fired.** Loop 2 of the improvement-loop alpha run.

## Hypothesis

**Crewborg's crew votes under-fire and mis-rank because the vendored v4 weights were fit
on 2,462 rows of v90-era data in which `reported_bodies`/`button_calls_made` were
all-zero (the caller-attribution bug, since fixed) — refitting on v116's own live traces
recovers ranking skill that converts to more correct first-accusations and more
imposter ejections at the shipped decision config.**

L1 closed the "more chat calls" channel: conversion is gated by the FIRST accusation's
quality/timing, i.e., by the ranking (this doc), not by persuasion volume.

## Evidence

- New dataset (train→serve-gap-free, `build_dataset_runtime.py` on L1's 595 v116-lineage
  episodes): 6,686 rows / 419 games / 1,115 crew meetings, `/tmp/loop1/runtime_L1.parquet`.
- Feature health on v116: `reported_bodies` 8.1% nonzero, `button_calls_made` 21.0% —
  the v90-era all-zero bug is gone; both now carry the strongest protective coefficients
  (−3.24, −0.53) in the new fit. The v4 weights were fit when these were broken.
- Fit `runtime-v116-L2`: **CV AUC 0.773** (v4 as vendored: 0.698); W2's measured ML
  ceiling was 0.82.
- OOF decision sim at the SHIPPED config (bar 0.5, lead 0): **imp-hits/meeting 0.414 vs
  the live v4 posterior's 0.292 (+42%), precision 78.4% vs 73.6%** — better on both axes.
- Known optimism: OOF shares the corpus with the fit; the live posterior also layers
  witnessed/HS/chat-evidence terms over the fitted part (identical in both arms — the
  probe changes ONLY the weights file). Hence the live A/B below.

## The change (one lever)

Vendor `suspicion_lab/models/runtime-v116-L2/suspicion_weights.json` as
`crewrift/crewborg/data/suspicion_weights.json` (same schema
`crewborg-suspicion-weights/v1`, same transform contract). No code change. All other
layers (witnessed floor, HS pin, chat evidence + floor, warm anchor, retime, bar 0.5)
identical.

## Design

- **Probe:** `crewborg-suspv5:v1` (probe lineage — NEVER submitted) = v116's code +
  the new weights file; recipe = v116's exact recipe.
- **Cand arms:** 2×100 eps, Thread-1 pinned roster, slot 0, natural roles, fired
  sequentially after loop-2's step-1 batch drains (pacing ≤400 concurrent).
- **Baseline:** loop-2's step-1 batch (3×100, v116, same day/roster/recipe,
  `xreq_f8d90abd`/`xreq_d27cc1fe`/`xreq_1ac203ea`). Ops profiles compared first; a
  materially different ops profile (>10pp) voids the comparison and a fresh baseline
  arm is fired.
- Ops-fail episodes excluded at the game level both sides.

## Pre-registered verdict criteria

Measured identically both sides from warehouses + belief partitions (the L1 verdict.py
instrument, updated `--policy`):

**PRIMARY (both must hold):**
1. **Net correct votes/crew-ep up:** (our ballots on true imposters − ballots on crew)
   per crew episode > baseline's, with hits (on-imposter ballots/crew-ep) up at
   one-sided poisson/fisher p < 0.05. (The refit's claim is more correct rankings over
   the bar — volume × precision, not conversion; conversion was L1's refuted channel.)
2. **Live crew vote precision not worse:** our on-imposter share of player-ballots ≥
   baseline − 5pp (the refit must not buy volume with mis-votes).

**MECHANISM (must fire):**
3. The live posterior distribution shifts: mean bar-clearing (p ≥ 0.5) suspects per
   crew meeting snapshot up vs baseline (the fitted layer is actually loaded — also
   verify the weights file hash/`trained: 2026-07-28` in the image before firing).

**GUARDS (any failure disqualifies):**
4. Crew WR not worse beyond noise (2-sided p < 0.05).
5. Mis-ejections-we-voted-for /crew-ep ≤ 1.5× baseline.
6. Slot-0 vote_timeouts = 0; zero self-votes.
7. Imposter side untouched (WR within noise — the fitted weights also feed the
   imposter's deflection-target pick; watch it explicitly).
8. imp-ejected-in-episode /crew-ep not down beyond noise.

**Decision rule:** all pass → build `crewborg:v117` (v116 recipe + the new vendored
weights), confirmatory A/B vs v116 per the W5 pattern (fresh prereg BEFORE firing),
then STOP AND ASK James with the full gate table. Any PRIMARY/GUARD fail → NO-SHIP,
close in version log, next loop. MECHANISM no-fire → implementation bug (weights not
loading), one diagnose-and-refire allowed.

---

## VERDICT (2026-07-29): **ALL PRE-REGISTERED GATES PASS → proceed to v117 confirmatory**

Cand = `crewborg-suspv5:v1` (`9a6274e0…`, identity verified 200/200 episodes), arms
`xreq_17d5a55b` + `xreq_8945fc9a` (200 eps, 0 ops; 150 crew / 50 imp). Baseline =
loop-2's fresh same-day v116 batch `xreq_f8d90abd`/`xreq_d27cc1fe`/`xreq_1ac203ea`
(300 eps, 0 ops; 230 crew / 70 imp). Ops profiles match (0 vs 0). Analysis
`/tmp/loop2/verdict.py`.

| criterion | cand (suspv5) | base (v116) | verdict |
|---|---|---|---|
| PRIMARY-1 net correct votes/crew-ep | **1.080** (hits 1.420/cep) | 0.774 (hits 1.030/cep) | ✅ hits 1-sided p=0.0004 |
| PRIMARY-2 live precision | **80.7%** | 80.1% | ✅ (bar 75.1%) |
| MECH-3 bar-clearing suspects/snapshot | **1.013**; top-clear 63.2% | 0.589; 45.4% | ✅ FIRED |
| GUARD-4 crew WR | 27.3% | 30.0% | ✅ within noise (p=0.58) |
| GUARD-5 mis-ej-we-voted/cep | 0.133 | 0.096 | ✅ under bar 0.143 (but WATCH: +38% point estimate) |
| GUARD-6 vote_timeouts / self-votes | 0 / 0 | 0 / 0 | ✅ |
| GUARD-7 imposter WR | 74.0% | 68.6% | ✅ noise (p=0.52) |
| GUARD-8 impEj-in-ep/cep | 41.3% | 43.0% | ✅ not down beyond noise (p=0.74) |

Context (not gates): conversion 22.1% vs 24.1% (flat — as expected; conversion is the
L1-closed channel), crew WR dipped directionally (within noise) while vote volume ×
precision moved exactly as the refit predicts. The mis-ejection WATCH (GUARD-5 margin
was thin) carries into the confirmatory read.

**Per the decision rule: build `crewborg:v117` (same code+weights, v116 recipe) and run
the confirmatory A/B — prereg below, registered BEFORE the confirmatory arms fired.**

---

## CONFIRMATORY prereg (v117 vs v116, registered 2026-07-29 BEFORE firing)

- **v117** = byte-identical build lineage to `crewborg-suspv5:v1` (main `32c7b48`)
  uploaded under the `crewborg` name, v116's exact recipe. The confirmatory validates
  the SHIPPING artifact (name/upload/recipe correctness — the v113-orphan class of
  error) and replicates the probe read on fresh arms.
- **Arms:** 2×100 v117, Thread-1 pinned roster, slot 0, natural roles, sequential.
- **Baseline:** the same L2 fresh v116 batch (300 eps, same-day). Ops-profile gate as before.
- **GATES (all must hold, pooled 200 v117 eps):**
  1. Identity: 200/200 episodes seat v117's policy_version_id at slot 0.
  2. Replication: hits/crew-ep > baseline (1-sided p < 0.05) AND net correct votes/crew-ep up.
  3. Precision ≥ baseline − 5pp.
  4. Crew WR and imposter WR each not worse beyond noise (2-sided p < 0.05).
  5. Mis-ejections-we-voted/cep ≤ 1.5× baseline; vote_timeouts 0; self-votes 0.
  6. Mechanism: bar-clearing/snapshot ≥ probe's direction (> baseline).
- **Decision rule:** all pass → STOP AND ASK James for submit approval with the full
  combined gate table (probe + confirmatory). Any fail → NO-SHIP, diagnose.

## CONFIRMATORY VERDICT (2026-07-29): **ALL GATES PASS — submitted to James for approval**

v117 (`54bb6cc5…`) arms `xreq_48f8d06a` + `xreq_2b990201` (200 eps, 0 ops; 155 crew /
45 imp; identity verified 200/200 = `54bb6cc5`, slot-0 artifact present) vs the same
fresh v116 baseline (300 eps). Ops profiles match (0 vs 0).

| gate | v117 | v116 base | verdict |
|---|---|---|---|
| 1. identity | 200/200 `54bb6cc5` slot 0 | — | ✅ |
| 2. replication: hits/crew-ep | **1.335** (net 1.045) | 1.030 (net 0.774) | ✅ p=0.0038 |
| 3. precision | **82.1%** | 80.1% | ✅ (bar 75.1%) |
| 4. crew WR / imposter WR | 32.9% / 73.3% | 30.0% / 68.6% | ✅ both directionally UP, noise |
| 5. mis-ej-we-voted/cep; vt; self-votes | 0.103; 0; 0 | 0.096; 0; 0 | ✅ (bar 0.143; probe's WATCH resolved — 0.133→0.103) |
| 6. mechanism: bar-clearing/snapshot | **1.005**; top-clear 57.6% | 0.589; 45.4% | ✅ |

Directional (not gates): impEj-in-ep/cep **51.6% vs 43.0%** (p=0.098) and conversion
**30.9% vs 24.1%** — the refit's better rankings are pulling the L1-diagnosed
conversion metric with them (more/earlier bar-clearing accusations → piles form on
our targets). Probe + confirmatory replicate on independent arms.

Awaiting James's explicit submit approval (loop-alpha procedure).
