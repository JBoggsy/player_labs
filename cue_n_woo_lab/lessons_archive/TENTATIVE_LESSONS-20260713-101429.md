# Cue-n-Woo tentative lessons — session buffer

**Session started:** 2026-07-10 12:11. This is THIS SESSION's lesson buffer. Write candidate
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

### No Cue-n-Woo lessons this session — work was creating the new heartleaf_lab
Evidence: session scaffolded `heartleaf_lab/` from the crewrift/cue-n-woo template; any
reusable lessons were captured in `heartleaf_lab/TENTATIVE_LESSONS.md`. Nothing touched or
learned about Cue-n-Woo specifically.
