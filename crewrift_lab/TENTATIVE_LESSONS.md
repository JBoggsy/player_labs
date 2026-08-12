# Crewrift tentative lessons — session buffer

**Session started:** 2026-08-07 20:29. This is THIS SESSION's lesson buffer. Write candidate
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

### Merging an old experiment branch can silently import tests for behavior main later rejected

Evidence: merging `jboggs/imposter-no-isolation` (June 13) into main (Aug 11) auto-added
`test_button_intercept.py` with no conflict — but 3 of its 8 tests exercised the
CREWBORG_FRONT_BIAS SearchMode wiring that main had since rejected and removed
(version_log v28–v30). The conflict resolver never saw it because the file was
add-only on one side. Only running the full suite caught it (3 failures).
Status: when merging stale branches, run the whole test suite even if every conflict
resolved cleanly to "ours" — clean auto-merges are where the stale content hides.

### The version log is the merge-decision oracle for old branches

Evidence: version_log.md explicitly recorded "Code committed on branch
`jboggs/imposter-no-isolation` (ef6f272)" and the front-bias REJECTED verdict, which
made every conflict resolution (take ours vs theirs) decidable in seconds; likewise
the agricogla lab-removal commit message ("poisoned; rebuild from scratch") was the
sole evidence that saved us from resurrecting 12 commits of scrapped work.
Status: keep writing branch names + ship/reject verdicts into version_log entries —
it paid off directly.
