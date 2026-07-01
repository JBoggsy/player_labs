# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-01 11:30. This is THIS SESSION's lesson buffer. Write candidate
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

### v80 A/B: recon de-freeze + scored PICK_ROOM collapse the idle leak — kills 1.91, win 78%
Evidence: matched 4-way (same fixed roster, crewborg pinned imposter slot0 + v70 partner, 60 eps/arm):
idle&ready 0.68 (v76) → 0.59 (v77) → 0.44 (v79) → **0.10 (v80)**; freezes≥1k 23 → 14 → 9 → **1**;
timeout-draws 0.38 → 0.28 → 0.20 → **0.07**; kills 1.18 → 1.43 → 1.27 → **1.91** (v79→v80 t=3.95,
p<0.001); imposter win 0.42 → 0.42 → 0.63 → **0.78**. The recon-stall fix (pre-ready-only gate +
abandon-stale-target) was the big lever, exactly as the freeze diagnosis predicted. v80 n=55: 5/60
episodes were the KNOWN platform degenerate (all-8-seats-crew, 0 kills, ends tick 3240 — role override
didn't apply); exclude them, don't count as crashes.
