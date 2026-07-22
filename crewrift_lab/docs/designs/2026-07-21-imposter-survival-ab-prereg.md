# Pre-registered A/B: crewborg-survive:v1 (kill→WIN survival) — written BEFORE launch

**Candidate:** `crewborg-survive:v1` (pv `82c4a42e-5940-4cc8-baf6-f9537dbf9e2b`) — main
(`d0d127c`, = v110's code) + commits `77bc648` (post-kill flee) and `3f8adc7`
(accused-response deflection + imposter first-mover). Upload recipe identical to v110
(LLM meetings recipe + `CREWBORG_HS_SECRET`), so vs the v110 baseline the ONLY delta is
the two survival levers. Design:
`crewrift_lab/docs/designs/2026-07-21-imposter-kill-to-win-design.md`.

**Arms (matched pinned roster — the Thread-1 seven current-champion labels — crewborg
slot 0, natural roles, div_acbde92a):**
- Candidate: 2×100 eps, fresh, paced (fired by this thread; total concurrent across all
  running xreqs kept ≤400).
- Baseline: the existing `/tmp/wh_anchor_base_v110` warehouse (200 v110 eps from Thread 1's
  `xreq_136dd84f` + `xreq_edd0f75e`, same roster/slot/division/recipe, same night) — reused,
  not re-fired. Thread-2's measured baselines on this data are the reference numbers below.

**Criteria (decided before any candidate episode is seen; imposter seats = crewborg
slot-0 seats with role=imposter; ops-dirty episodes dropped first, both arms):**

1. PRIMARY: **ejected-after-witnessed-kill rate DOWN** — of crewborg imposter seats with
   ≥1 witnessed kill, the fraction ejected by vote. Baseline 62.2% (v110-lineage).
   Pass = point estimate down; a drop to ≤ the ~45% midpoint toward the field's 31.6%
   counts as a clear pass, any rise fails.
2. Secondary: **post-kill 60-tick displacement UP** — median distance moved in the 60
   ticks after own kill. Baseline 4px; pass = field-like (≥20px).
3. Secondary: **imposter ejection rate (of seats) DOWN** — baseline 57.1% (v110 pinned arm).
4. Secondary: **imposter win rate UP** — baseline 53.6% (v110 pinned, n=56). The point of
   it all, but small-n noisy; directional evidence suffices if 1–3 move.
5. GUARD: **kills/seat not down** — baseline 1.61; fleeing must not cost the second kill
   (allow normal noise; a significant drop fails).
6. GUARD: **crew metrics untouched** — crew win rate (27% pooled baseline), crew
   no_vote_rate (~0), crew self-accusations 0 (the changes are imposter-only; the crew
   first-mover seam is untouched).
7. GUARD: **vote_timeouts flat** (~2/200 baseline) and **ops ~0** crewborg-side.
8. Mechanism checks (else the verdict is "no-fire", not "refuted"):
   - `domain.post_kill_flee` fires in candidate imposter telemetry (lever 1);
   - `domain.meeting_imposter_first_mover` and/or `meeting_decision path=counter_accuse`
     fire in candidate imposter meetings (lever 2).

**Attribution rule:** the levers are separable — lever 1 via the flee trace +
displacement metric, lever 2 via the meeting traces + speaks-first/accused-response
rates. If the primary passes but one lever demonstrably didn't fire or hurt its own
sub-metrics, ship the working lever alone.

**Ship rule:** primary + guards pass → SHIP RECOMMENDED (levers ship inside the next
crewborg version; the probe name is never submitted). Primary fails or a guard fails →
refutation recorded in TENTATIVE_LESSONS + version_log; no ship.
