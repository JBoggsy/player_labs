# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-01 12:40. This is THIS SESSION's lesson buffer. Write candidate
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
### v80 shipped WITH the role-latch regression — 49% of league crew games end 0-task
Evidence: league tournament survey (196 eps, rounds ~274-278): v80 crew 0-task rate 49% (66/135), field 0-5%; task/g 2.58 vs 5.2-6.5; bimodal (66×0-task vs 20×8-task). Same fingerprint in EVERY xreq population (45-100%). James independently spotted crew-thinks-it's-imposter in replays. v80 descends from the paritypush lineage (1178f31 widened latch) WITHOUT the v75 IMPS-text fix (4e1d7c1). Lesson: any build lineage forked before a critical fix must be checked for that fix before submit — a "0-task crew %" column in the survey would have caught this pre-submission.
