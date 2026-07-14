# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-13 16:41. This is THIS SESSION's lesson buffer. Write candidate
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
### The lessons rotation hook re-archives UNCHANGED buffers under new timestamps — dedupe by md5 before counting recurrence
Evidence: during the 2026-07-13 cross-lab lessons review, ctf_lab had 4 byte-identical archived buffers (same md5, same "Session started" header) and heartleaf_lab had 4 more — one session's buffer minted as 4 "independent" sessions. This silently inflates the recurrence signal /lessons-review graduates on. Applies to crewrift's archive too (same rotate_lessons.sh). Fix candidate: rotate_lessons.sh should skip rotation when the buffer is entry-free or identical to the newest archive.
Status: observed in 2 labs this session; hook fix not yet made (parked).

### No gameplay lessons this session — crewrift work was a lessons-archive review (meta), not player/eval work
Evidence: session ran /lessons-review-style sweeps via subagents across all labs; no crewborg code, evals, or diagnosis touched.
