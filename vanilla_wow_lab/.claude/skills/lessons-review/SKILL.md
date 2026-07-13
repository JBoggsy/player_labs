---
name: lessons-review
description: "Periodic (≈weekly) review of the Vanilla WoW tentative-lessons archive: cluster RECURRING lessons across archived session buffers, propose promote/keep/cull with recurrence counts, and — on the human's call — graduate keepers to best_practices.md and retire reviewed archives. Triggers: '/lessons-review', 'review the lessons archive', 'which lessons keep reappearing', 'graduate lessons'."
---

# Lessons review

Mine the tentative-lessons archive for the signal it was built to surface:
**lessons that keep reappearing across independent sessions**. Recurrence across
session buffers — not anyone's in-session judgment — is the graduation evidence.

**Announce at start:** "Reviewing the Vanilla WoW lessons archive — clustering
recurring lessons across N session buffers."

## Inputs

- `vanilla_wow_lab/lessons_archive/*.md` — one buffer per past session (rotated
  automatically by the SessionStart hook). `lessons_archive/reviewed/` holds
  already-reviewed buffers — exclude them.
- `vanilla_wow_lab/TENTATIVE_LESSONS.md` — the live buffer; include it read-only
  (it stays in place; it is NOT retired by this review).
- `vanilla_wow_lab/best_practices.md` + root `best_practices.md` — the graduation
  targets; also check a candidate isn't already there.

## Workflow

1. **Collect** every `### ` lesson from unreviewed archives (+ live buffer), keyed
   by (file, title, evidence).
2. **Cluster semantically** — same underlying lesson, differently worded, counts
   as recurrence. Cite which sessions each cluster appeared in.
3. **Propose**, as a table for the human: **promote** (recurred ≥2–3 sessions, or
   single-occurrence but high-stakes and verified), **keep waiting** (plausible,
   1 occurrence), **cull** (contradicted, superseded, or noise). Include the
   one-line lesson, recurrence count + dates, and your recommendation with a
   reason. The human decides — do not graduate without their call.
4. **Apply the decisions:** graduated lessons → `vanilla_wow_lab/best_practices.md`
   (Vanilla WoW-specific) or root `best_practices.md` (game-agnostic), rewritten as
   durable practice prose (not buffer-entry format). Culled lessons just retire
   with their buffer.
5. **Retire reviewed buffers** → `git mv` into `lessons_archive/reviewed/`.
   Waiting lessons stay discoverable there — future reviews count recurrence
   against `reviewed/` too when judging a fresh occurrence.
6. **Commit** with a summary: N buffers reviewed, promoted/waiting/culled counts.

## Discipline

- Recurrence beats eloquence: a boring lesson seen in 3 sessions outranks a
  brilliant one seen once.
- Check graduation targets first — don't re-promote something already practiced.
- A lesson contradicted by later evidence gets culled *with a note* in the commit
  message (negative results are findings).
