# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-13 10:14. This is THIS SESSION's lesson buffer. Write candidate
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

### The `pr.merge-conflicts` skill points at a doc that doesn't exist in this repo
Evidence: `Skill(pr.merge-conflicts)` told me to read `docs/ai/onboarding/workflows/pull-request/merge-conflicts.md` as "the single source of truth"; that path does not exist under player_labs (it's a metta-repo path). Had to resolve the conflict from first principles. The skill is metta-oriented; in this repo treat it as advisory, not authoritative.

### TENTATIVE_LESSONS.md conflicts on `git pull` are just clashing session-buffer headers — keep the working-tree (freshest) copy
Evidence: this session's only pull conflict was `crewrift_lab/TENTATIVE_LESSONS.md`; all three merge stages were identical except the "Session started:" timestamp. The SessionStart rotation hook regenerates a fresh buffer each session, so divergence is expected churn. Resolution: verify any real lesson content in the BASE stage is already archived under `lessons_archive/` (it was, in 3 files), then keep the working-tree buffer and complete the merge. Recurs with the [[known]] stale-branch rotation-hook risk already archived.

### WORKING_CONTEXT.md is the load-bearing "where are we" file — read it before proposing a direction
Evidence: it surfaced a CRITICAL handoff fact invisible from git/code alone — all of v101→v105 is UNCOMMITTED working-tree state (last crewborg commit `03fff48` = v100), ~634 tests green, flagged "COMMIT THIS before more churn." Also carries the closed-levers list (don't re-chase crew task-throughput / teammate detection / v102 kill regression) and the current open bet (meeting-persuasion social rework). A primer or plan that skipped this file would have missed all of it.
