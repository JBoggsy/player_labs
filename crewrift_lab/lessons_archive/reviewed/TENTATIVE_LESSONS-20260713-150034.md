# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-13 14:56. This is THIS SESSION's lesson buffer. Write candidate
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

### No Crewrift-specific lessons — session was repo-level git housekeeping.
Evidence: this session only committed leftover SessionStart-hook lesson rotations and merged origin/main (conflicts were pure session-timestamp churn in TENTATIVE_LESSONS buffers across two machines); no Crewrift gameplay, policy, or tooling was touched. Repo-level observation worth noting somewhere game-agnostic: the lesson-rotation hook commits on each machine independently, so working from two machines reliably produces trivial timestamp merge conflicts in the buffers — resolve by keeping the current session's (later) timestamp.
