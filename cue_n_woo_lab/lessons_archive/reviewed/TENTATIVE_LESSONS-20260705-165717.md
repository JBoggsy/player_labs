# Cue-n-Woo tentative lessons — session buffer

**Session started:** 2026-07-05 16:49. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`cue_n_woo_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Cue-n-Woo-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### A stalled merge can leave literal conflict markers inside archived (not live) files
Evidence: `cue_n_woo_lab/lessons_archive/TENTATIVE_LESSONS-20260705-164951.md` was
staged with raw `<<<<<<<`/`=======`/`>>>>>>>` markers baked into its text — the
live `TENTATIVE_LESSONS.md` had a real git conflict at session start, and the
rotate-lessons hook appears to have archived that file's on-disk (conflicted)
content verbatim before the buffer got reset to a fresh template. `git status`
showed this archive file as untracked/staged, not `UU`, so a routine
"any `<<<<<<<` left?" grep across the repo (not just `git status`) was needed to
catch it. Worth considering: should `rotate_lessons.sh` refuse to archive a file
that still contains conflict markers, to fail loud instead of silently baking
a corrupted record into history?
