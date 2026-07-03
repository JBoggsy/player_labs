# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-02 16:19. This is THIS SESSION's lesson buffer. Write candidate
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

### 2026-07-02: Process pivot — Gate 1 / smoke tests removed; speed-first loop is now doctrine
Evidence: James's directive ("we are iterating much too slowly") — commit e967777 rewrote
AGENTS.md/best_practices.md/skills: rebuild → upload immediately, hosted eval is the test,
coworld-local-run demoted to a debugging tool, league submission remains the only gate.
Status: already graduated straight into best_practices.md (root "Speed first" + crewrift
non-negotiable #6) by the same directive, so no re-graduation needed at review — this entry
is the session record. No gameplay lessons this session (docs/process work only).
