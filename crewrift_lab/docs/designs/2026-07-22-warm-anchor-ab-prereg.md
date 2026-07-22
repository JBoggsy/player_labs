# Pre-registered A/B: crewborg-warm:v1 (warm first-mover anchor) — written BEFORE launch

**Candidate:** `crewborg-warm:v1` — this branch (= main `1018642`, i.e. v111's exact code)
+ the warm-anchor commit (suspicion.warm_anchor_suspect + attend_meeting warm route +
pile clause). Upload recipe identical to v111 (LLM meetings recipe + `CREWBORG_HS_SECRET`),
so vs the v111 arm the ONLY delta is the warming change. **Both arms carry the hard
first-mover anchor** — the warming lever only matters WITH the anchor present.

**Arms (matched pinned Thread-1 roster, crewborg slot 0, natural roles):**
- Candidate: 2×100 eps, fresh (fired by this thread, paced ≤400 total concurrent
  across all running xreqs).
- Baseline: W1's v111 confirmatory arms (2×100 eps, same roster/slot/recipe,
  fired 2026-07-22 same-day) — reuse their episodes; if the W1 arms are not
  complete/clean when the candidate drains, fire a fresh 2×100 v111 baseline
  with the identical spec instead.
- Ops-fail episodes (connect/disconnect-dead games) excluded both sides.

**Criteria (decided before any candidate episode is seen):**
1. PRIMARY-A (rate): total first-mover fires (`meeting_first_mover_accusation`,
   hard + warm) ≥ 0.26/ep in the candidate (baseline ran ~0.17-0.19/ep; the
   offline replay of the warm rule adds ~0.12/ep). Below 0.22/ep = the lever
   under-fires live; verdict "no-fire", not refuted.
2. PRIMARY-B (conversion not-worse): crewborg crew-accusation → same-meeting
   ejection-of-target conversion not significantly worse than baseline
   (premise-check method: warehouse chat + died events).
3. HARD GUARD (mis-ejection): crewmates ejected in meetings where OUR accusation
   named them — rate per episode NOT up vs baseline (one-sided; a significant
   increase fails regardless of anything else passing).
4. HARD GUARD (crew win): crew win rate not significantly worse than baseline.
5. HARD GUARD (vote precision): crewborg's crew player-votes that hit true
   imposters ≥ 75% in the candidate (v110 lineage measured ~67-100% depending
   on path; the warm route must not drag the pooled precision below 75%).
6. HARD GUARD (vote_timeouts): slot-0 vote_timeout count not up vs baseline
   beyond noise.
7. Mechanism (warm fires): warm-flagged anchors (`warm: true` /
   `meeting_warm_anchor` counter / path `first_mover_accuse_warm`) ≥ 0.06/ep
   AND warm-anchor accuracy (target is a true imposter) ≥ 70% (offline measured
   89.4%; below 70% live = the offline rule didn't transfer — refute even if
   episode metrics pass).
8. Sanity: imposter win / kills per seat unchanged (crew-only change); crew
   self-accusations 0; ops-fail ~0 both arms (materially higher candidate
   ops-fail = invalid run, re-run).

**Ship rule:** 1-8 all pass → SHIP RECOMMENDED for W5's combination build (the
probe name is never submitted). Any hard guard (3-6) fails → REFUTED, record in
TENTATIVE_LESSONS + version_log, no ship. Mechanism-fail (1 or 7) → NO-FIRE /
NO-TRANSFER verdict with numbers, no ship, diagnose before retry.
