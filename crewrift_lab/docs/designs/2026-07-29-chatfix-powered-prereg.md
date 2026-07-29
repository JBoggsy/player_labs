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

## VERDICT (2026-07-29): **ALL CRITERIA PASS — L3's guard trip was sampling noise. Proceed to v118 confirmatory.**

Pooled per the pre-specification: cand = L3's arms + L4's `xreq_b407d0a0` +
`xreq_9ec467d0` (399 eps, 0 ops; 300 crew / 99 imp); base = L3's batch + L4's
`xreq_06c1c5e1` + `xreq_abd91344` (500 eps, 0 ops; 359 crew / 141 imp). All arms
same-day-adjacent, ops profiles uniform (0 everywhere). Analysis `/tmp/loop3/verdict.py`
+ the server-rule acceptance sim.

| criterion | cand (chatfix, pooled) | base (v117, pooled) | verdict |
|---|---|---|---|
| 1. THE QUESTION: mis-ej-we-voted/cep | **0.160** (48/300) | 0.142 (51/359) | ✅ **under the 1.5× bar 0.213**; fisher 2-sided p=0.58. L3's 0.181 regressed toward base — noise confirmed. |
| 2a. accusations accepted (server-rule sim) | **847/847 = 100%** | 921/1121 = 82.2% | ✅ (bar ≥95%) |
| 2b. votes-on-our-imposter-target | **1.16** (n=448) | 0.96 (n=551) | ✅ MW 1-sided p=0.0025 |
| G3. crew WR | 32.3% | 30.1% | ✅ (p=0.53, direction up) |
| G4. imposter WR | 65.7% | 69.5% | ✅ within noise (p=0.53) |
| G5. vote_timeouts / self-votes | 0 / 0 | 0 / 0 | ✅ |
| G6. hits/crew-ep | **1.420** | 1.326 | ✅ not down |
| G7. HS1 accepted / member coverage | 216/216 = 100% | 345/353 = 97.7% | ✅ |

**Per the decision rule: build `crewborg:v118` (v117 recipe + the chat-swallow fix,
main `1a71c6b` lineage) and run the confirmatory A/B — prereg below, registered BEFORE
the confirmatory arms fired.**

---

## CONFIRMATORY prereg (v118 vs v117, registered 2026-07-29 BEFORE firing)

- **v118** = the `crewborg-chatfix:v1` image uploaded under the `crewborg` name,
  v117's exact recipe. Validates the shipping artifact + replicates on fresh arms.
- **Arms:** 2×100 v118, Thread-1 pinned roster, slot 0, natural roles, sequential.
- **Baseline:** the pooled L3+L4 v117 base (500 eps, same-day-adjacent). Ops gate as usual.
- **GATES (all must hold, pooled 200 v118 eps):**
  1. Identity: 200/200 episodes seat v118's policy_version_id at slot 0.
  2. Replication: votes-on-our-imposter-target > baseline (1-sided p < 0.05) AND
     accusations accepted ≥ 95% (server-rule sim).
  3. Crew WR and imposter WR each not worse beyond noise (2-sided p < 0.05).
  4. Mis-ej-we-voted/cep ≤ 1.5× baseline; vote_timeouts 0; self-votes 0.
  5. hits/crew-ep not down (the v117 refit gain must persist through the fix).
- **Decision rule:** all pass → STOP AND ASK James for submit approval with the full
  gate table (powered test + confirmatory). Any fail → NO-SHIP, diagnose.

## CONFIRMATORY VERDICT

*(pending at registration)*
