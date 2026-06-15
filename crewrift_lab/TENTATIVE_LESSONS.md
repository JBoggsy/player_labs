# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-15 10:05. This is THIS SESSION's lesson buffer. Write candidate
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

### Hook commands in .claude/settings.json must use absolute paths via $CLAUDE_PROJECT_DIR, never repo-root-relative paths
Evidence: All four lesson-lifecycle hooks (SessionStart rotate_lessons.sh ×2, Stop lessons_stop_nudge.sh ×2) used bare relative paths like `crewrift_lab/tools/lessons_stop_nudge.sh`. The Stop hook fired with cwd != repo root and failed `sh: ...: No such file or directory` (exit 127). Claude Code does not guarantee hooks run from the repo root; it injects `CLAUDE_PROJECT_DIR` (absolute, available in SessionStart + Stop) for exactly this. Fix: wrap each command as `"$CLAUDE_PROJECT_DIR/<path>"`. The scripts' own `REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)` then resolves correctly because they receive an absolute argv[0].
Status: Fixed 2026-06-15. SessionStart hooks shared the same latent bug (worked only because cwd happened to be repo root at startup).
