# Chat-swallow fix, powered re-test — pre-registration (2026-07-29, loop-alpha L4)

**Registered BEFORE any L4 arm fired.** Loop 4 of the improvement-loop alpha run.

## Question

L3's chat-swallow fix (`crewborg-chatfix:v1`, main `1a71c6b`: client chat cooldown
60→104 + HS1 announce defers to the accusation) PASSED both primaries and five of six
guards, but **GUARD-7 (mis-ejections-we-voted-for/crew-ep ≤ 1.5× baseline) tripped its
point-estimate bar** (0.181 vs bar 0.174; 28/155 vs 25/215 crew-eps; fisher p=0.098) →
honest NO-SHIP per the registered rule. At n=155 crew eps that guard's read is noise-
dominated. This L4 test answers ONE question with adequate power:

**Does the chat-swallow fix genuinely raise our mis-ejection rate beyond 1.5× baseline,
or was L3's guard trip sampling noise?**

## Design (pooling pre-specified)

- **New arms (fired after this doc commits):** cand = 2×100 `crewborg-chatfix:v1`
  (same probe, same recipe); base = 2×100 `crewborg:v117`; all four Thread-1 pinned
  roster, slot 0, natural roles, paced sequentially (≤400 concurrent).
- **Pooled analysis set (pre-specified):** cand = L3's 200 (`xreq_7c2ba7bd`,
  `xreq_5ca6fda7`) + the new 200 → ~400 eps (~300 crew). Base = L3's 300
  (`xreq_302b7740`/`6f72c3dc`/`a00fd378`) + the new 200 → ~500 eps (~370 crew).
  All same-day-adjacent, same roster/recipe. Ops-profile comparison across all arms
  first; any ops-dirty arm (>10pp) is excluded WHOLE (both sides re-balanced by
  excluding its window twin if needed).
- Power: at ~300 vs ~370 crew eps, the mis-ej guard detects a true 1.5× elevation
  (0.116→0.174) with ~80% power at α=0.05 one-sided — adequate for the question.

## Pre-registered verdict criteria (on the POOLED set)

**THE QUESTION (decides ship/no-ship):**
1. Mis-ejections-we-voted-for/crew-ep: cand ≤ 1.5× base (point estimate) OR
   (cand > 1.5× base but fisher 2-sided p ≥ 0.05 AND cand's pooled point estimate
   < L3's 0.181 — i.e., regression toward base confirms L3 noise). If cand's pooled
   mis-ej is BOTH above the 1.5× bar AND p < 0.05 → the fix genuinely trades
   mis-ejections for volume → NO-SHIP, close the lever.
2. Replication of the L3 primaries on the pooled set: accusations accepted ≥ 95%
   (server-rule sim); votes-on-our-imposter-target ≥ base (one-sided p < 0.05).

**GUARDS (pooled, any failure disqualifies):**
3. Crew WR not worse beyond noise (2-sided p < 0.05).
4. Imposter WR within noise.
5. vote_timeouts 0; self-votes 0.
6. hits/crew-ep not down vs base.
7. HS1 announce accepted ≥ 90%; honor_known_member coverage comparable.

**Decision rule:** criteria 1–2 + guards pass → build `crewborg:v118` (v117 recipe +
the fix, main `1a71c6b` lineage), confirmatory A/B vs v117 per the W5 pattern (fresh
prereg BEFORE firing), then STOP AND ASK James with the full gate table. Criterion 1
fails in the "genuine elevation" direction → close the lever (the persuasion win is
not worth the parity gifts at 1.5×). Guards fail → diagnose.

---

## VERDICT

*(pending at registration)*
