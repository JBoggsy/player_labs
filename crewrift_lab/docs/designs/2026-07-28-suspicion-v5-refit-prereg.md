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

## VERDICT

*(pending at registration)*
