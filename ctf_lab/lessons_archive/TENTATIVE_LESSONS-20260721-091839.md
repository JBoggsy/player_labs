# CTF tentative lessons — session buffer

**Session started:** 2026-07-15 12:09. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Merge auto-resolution can silently move a whole remote session's lessons into the fresh buffer — check `grep -c '^### '` on every buffer after a lessons-file merge

Evidence: 2026-07-15 pull: the ctf buffer conflict LOOKED timestamp-only (markers wrapped
just the Session-started line) and auto-merge "succeeded" — but the merged file then held
all 11 of the remote 2026-07-14 18:47 session's lessons under TODAY's fresh header, blending
two sessions into one buffer. Caught only by counting `^### ` entries post-merge. Fix:
archived the remote buffer verbatim to lessons_archive/TENTATIVE_LESSONS-20260715-121442.md
and reset the live buffer to the fresh stamped template. After any merge touching
TENTATIVE_LESSONS.md, verify each live buffer has 0 entries (or only this session's).
