# CTF tentative lessons — session buffer

**Session started:** 2026-07-21 09:18. This is THIS SESSION's lesson buffer. Write candidate
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

### Reconcile a lessons-buffer merge conflict by COUNT against the session's archive — stragglers hide when most lessons already archived
Evidence: merging origin's ctf buffer (13 lessons) conflicted with the fresh buffer; the same-session archive held only 11 — eyeballing "already archived" would have dropped 2 lessons ("stderr-quiet log is normal", "opponents iterate against you"). `grep -c '^### '` on both sides found the gap mechanically; the fix is append-stragglers-to-the-same-session archive + restore the clean fresh buffer, never merge remote lessons into the new session's buffer.
