# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-13 11:04. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### The imposter "kill ceiling" is opponent-relative, NOT structural — weak crew → ~50% more kills
Evidence: random-field run (1,200 eps, natural roles, pooled across v25/v28/v29 to be field-mix-
invariant), imposter kills bucketed by mean opponent leaderboard score: strong(≥55) 1.12 k/g (n=92),
mid(50-55) 1.61 (n=128), weak(<50) 1.90 (n=21); corr(opp_strength,kills) = −0.35. The "~1.27
structural ceiling" claimed across BE_DUMB/kill-sooner/iso-off A/Bs was an ARTIFACT of always
pinning the top-7 (strongest crew = hardest to isolate). Kills aren't cooldown-ceilinged in
absolute terms — they're capped by how well the crew avoids isolation. Implication: imposter kill
levers may still pay off vs the part of the field that ISN'T the top crew (most of it).

### Natural roles can't both confirm an imposter-only effect AND measure blended EV — imposters are ~22% of seats
Evidence: natural-roles A/B (100 eps/arm) of an imposter-only flag gave only 25/18 imposter games per
arm → kills 1.20→1.44 read as noise (p=0.23) despite d=+0.38 matching the pinned weak-crew win
(p=0.016, ~97 imp games). Blended score stayed flat (54.7→54.0) because imposter gains dilute across
78% crew seats. Use natural roles ONLY for crew-regression checks + blended-EV reads; PIN the role to
power any role-specific effect. To estimate blended imposter EV with power, pin imposter AND run more
eps (~300) — or accept the per-role pinned numbers and weight by the ~22% imposter seat frequency.

### no-isolation kill-gate is OPPONENT-CONDITIONAL: no-op vs elite crew, clear WIN vs weak crew
Evidence: pinned 2-imp A/B, CREWBORG_NO_ISOLATION (v29) vs control (v28), 100 eps/arm. Vs top-7
crew: kills 1.27→1.24 (p=0.80, no-op). Vs WEAK crew (ranks 11-16, mean ~47): kills 1.69→1.92
(p=0.016), imp win 59%→73% (p=0.05), score 75.7→92.4, AND ejected 14%→3%. Traces: iso-off lifts
kill attempts 1.65→1.89 (vs beatable crew the witness gate WAS sometimes blocking a strike; vs
top-7 victims are never isolated enough for the gate to bind); ejections DROP because more/faster
kills hit parity before crew can vote (median game 3935→3802t, 3-kill games 6→15). Lesson: test
imposter kill levers against the WEAK majority of the field, not just the top-7 — the top-7 caps
kills regardless of policy and hides real gains. Reverses the premature "kill lever exhausted" call.

### random:true resolves ONCE PER REQUEST → a cross-subject three-way over separate requests is CONFOUNDED by draw
Evidence: ran v25/v28/v29 each as 4×100-ep random-field requests. v25 and v28 are the SAME brain
(v28=v25 code, flags off) yet read IMP kills 1.07 vs 1.47, win 67% vs 47% — impossible for identical
policies; caused by each subject's requests drawing DIFFERENT opponent lineups (v25 drew strong top
crew, v29 drew weak Nishad/Kyle + crewborg-as-teammate). 4 reps didn't average it out. Cross-subject
comparison needs the SAME opponents per episode → pin the roster (or seat all subjects in ONE request
across slots). Random draws are fine for "performance vs the field" of ONE subject, not for A/B deltas.
