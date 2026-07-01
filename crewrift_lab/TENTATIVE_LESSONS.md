# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-01 11:51. This is THIS SESSION's lesson buffer. Write candidate
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

### Streaming pipeline live validation (2026-07-01) — trace_warning ≠ nonzero exit; and "exit 0 on one replay" ≠ version-matched
Validating stream_eval.py surfaced two subtleties: (1) `/tmp/expand-043` exits 0 with
`trace_complete` on SOME fresh prime-0.4.29 replays but trace_warns on most (6/8) — a
single-replay smoke test of the expander can pass while the binary is effectively stale.
Verify on several fresh replays, or trust only the warehouse's per-episode trace_warning
count. (2) The early first-batch skew alarm in stream_eval.py fired exactly as designed
(2 warned episodes visible at 4/8 fetched, minutes before drain) — the design's "find out
minutes in, not after the whole xreq" payoff is real; keep that alarm when touching the
orchestrator.
